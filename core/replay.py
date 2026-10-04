#!/usr/bin/env python3
"""Replay archived synthetic episodes without a model, provider or network.

Scores are evaluated only in this portable copy. The archived expected rows
are immutable comparison targets, never regenerated or updated by this tool.
"""
from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'runtime'))
import policies
import allow
import evaluate


def no_network(event, args):
    if event in {'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.bind'}:
        raise RuntimeError('Offline replay forbids network access: ' + event)


sys.addaudithook(no_network)


def read_gzip(name):
    with gzip.open(ROOT / 'data' / name, 'rt', encoding='utf-8') as f:
        return json.load(f)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def check_package():
    manifest = json.loads((ROOT / 'PACKAGE_MANIFEST.json').read_text())
    errors = []
    for name, expected in manifest['sha256'].items():
        path = ROOT / name
        if not path.is_file() or digest(path) != expected:
            errors.append(name)
    if errors:
        raise RuntimeError('Package hash verification failed: ' + ', '.join(errors))
    return manifest


def packet(row):
    pk = copy.deepcopy(row['packet'])
    encoded = json.dumps([row['case_id'], row['split']], ensure_ascii=False,
                         sort_keys=True, separators=(',', ':')).encode()
    pk['episode_id'] = 'episode-' + hashlib.sha256(encoded).hexdigest()[:16]
    return pk


def extraction(episode, pk, raw):
    value = raw[episode['responses']['candidate_F']]
    errors = []
    f = None
    try:
        f = policies.original.parse_extraction(value['record'][value['text_field']], pk)
        policies.original.protocol.validate_beliefs({'beliefs': f['beliefs']}, pk)
    except (policies.original.protocol.ProtocolError, KeyError, TypeError) as exc:
        errors.append(str(exc))
        f = None
    if f != episode['parsed_extraction'] or errors != episode['extraction_parse_errors']:
        raise RuntimeError('Exported extraction parse drift for ' + str(episode_key(episode)))
    return f, errors


def episode_key(e):
    return e['model_alias'], e['case_id'], e['repeat']


def gate(condition, pk, f, q):
    if condition in {'B', 'C', 'R', 'CR'}:
        return policies.original._gated_final(pk, f, q, condition)
    if condition == 'R_AGREE':
        return policies.original._gated_final(pk, f, q, 'B')
    if condition == 'R_ALLOW':
        return allow.apply_exception(pk, f, q)
    return policies.gate(condition, pk, f, q)


def replay_output(e, condition, pk, f, ferr, db):
    original_conditions = {'D', 'G', 'SR1', 'B', 'C', 'R', 'CR'}
    # Original scored records preserve the archived failures and diagnostics.
    # Their proposed decisions are executed afresh; their archived states and
    # receipts are never fed into the executor or used to determine the result.
    if condition in original_conditions:
        o = copy.deepcopy(e['outputs'][condition])
        q = o['final_proposal']
        valid = bool(o['generation_valid'])
        if condition in {'B', 'C', 'R', 'CR'}:
            valid = bool(valid and q is not None and f is not None)
        o['generation_valid'] = valid
    else:
        source = e['outputs']['G' if condition.startswith('R_') else 'B']
        q = copy.deepcopy(source['final_proposal'])
        valid = bool(q is not None and f is not None and source['generation_valid'])
        calls = list(source['upstream_call_ids'])
        if condition.startswith('R_'):
            calls += e['outputs']['B']['upstream_call_ids'][:1]
        o = {**{k: e[k] for k in ['model_alias', 'case_id', 'repeat']},
             'condition': condition, 'split': 'test', 'upstream_call_ids': calls,
             'generation_valid': valid,
             'parse_errors': list(source.get('parse_errors', [])) + ferr,
             'final_proposal': q, 'raw_reply': q.get('reply') if q else None}
    o.update(final_snapshot=policies.original.store.init_db(db, pk['db_snapshot']),
             receipt=None, delivered_text=None, gate_audit=[])
    if not valid:
        return o
    if condition in {'D', 'G', 'SR1'}:
        g, audit = q, []
    else:
        g, audit = gate(condition, pk, f, q)
    receipt = policies.original.store.execute(db, g, pk)
    if receipt['status'] == 'ALREADY_APPLIED':
        raise RuntimeError('Replay state was not isolated')
    delivery = policies.original.render_receipt_reply(receipt, q['action']) if condition in {'R', 'CR'} else q['reply']
    o.update(gated_proposal=g, gate_audit=audit, receipt=receipt,
             final_snapshot=receipt['after'], delivered_text=delivery)
    return o


def compare(actual, expected):
    return {k: {'expected': expected.get(k), 'actual': actual.get(k)}
            for k in evaluate.SCORE_FIELDS if actual.get(k) != expected.get(k)}


def aggregate(scores):
    metrics = [name for name in evaluate.SCORE_FIELDS if name not in {
        'model_alias', 'split', 'case_id', 'family', 'repeat', 'condition', 'upstream_call_ids'}]
    groups = {}
    for score in scores:
        for model in [score['model_alias'], 'ALL21']:
            key = (model, score['condition'])
            row = groups.setdefault(key, {'model_alias': model, 'condition': score['condition'],
                                          'episodes': 0, **{m: 0 for m in metrics}})
            row['episodes'] += 1
            for metric in metrics:
                row[metric] += int(score[metric])
    return [groups[k] for k in sorted(groups)]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path,
                        help='New results directory outside the immutable core package.')
    parser.add_argument('--limit', type=int, default=None,
                        help='Optional small smoke run; full verification requires no limit.')
    parser.add_argument('--write-replayed-outputs', action='store_true',
                        help='Also write fresh replay states/receipts as compressed JSONL.')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error('--output-dir must be outside the immutable core package')
    if output.exists():
        parser.error('--output-dir must not already exist')
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    package = check_package()
    output.mkdir(parents=True)
    started = time.monotonic()
    cohort = json.loads((ROOT / 'data/cohort.json').read_text())
    cases, episodes, raw = read_gzip('cases.json.gz'), read_gzip('episodes.json.gz'), read_gzip('raw_responses.json.gz')
    conditions = cohort['original_conditions'] + cohort['saved_alternative_conditions']
    expected_episodes = cohort['episodes']
    if args.limit is None and len(episodes) != expected_episodes:
        raise RuntimeError('Cohort cardinality mismatch')
    selected = episodes[:args.limit] if args.limit is not None else episodes
    scores, differences = [], []
    snapshot_matches = gate_audit_matches = executed = invalid = 0
    replayed = gzip.open(output / 'replayed_outputs.jsonl.gz', 'wt', encoding='utf-8') if args.write_replayed_outputs else None
    try:
        with tempfile.TemporaryDirectory(prefix='sorieum-offline-') as td:
            db = Path(td) / 'state.sqlite'
            for index, e in enumerate(selected):
                row = cases['public_rows'][e['public_row_id']]
                ref = cases['references'][e['reference_id']]
                pk = packet(row)
                f, ferr = extraction(e, pk, raw)
                for condition in conditions:
                    if db.exists():
                        db.unlink()
                    o = replay_output(e, condition, pk, f, ferr, db)
                    score = evaluate.score_output(o, row, ref)
                    scores.append(score)
                    delta = compare(score, e['expected_scores'][condition])
                    if delta:
                        differences.append({'episode': episode_key(e), 'condition': condition, 'score_differences': delta})
                    snapshot_matches += o['final_snapshot'] == e['outputs'][condition]['final_snapshot']
                    gate_audit_matches += o['gate_audit'] == e['outputs'][condition].get('gate_audit', [])
                    executed += o['receipt'] is not None
                    invalid += not o['generation_valid']
                    if replayed is not None:
                        replayed.write(json.dumps(o, ensure_ascii=False) + '\n')
                if (index + 1) % 500 == 0:
                    print('Replayed', index + 1, 'episodes', flush=True)
    finally:
        if replayed is not None:
            replayed.close()
    check_package()
    write_csv(output / 'scores.csv', scores)
    write_csv(output / 'condition_totals.csv', aggregate(scores))
    write_json(output / 'differences.json', differences)
    report = {
        'schema': 'offline-replay-verification-v1',
        'status': 'PASS' if not differences else 'FAIL',
        'complete_cohort': len(selected) == expected_episodes,
        'episodes': len(selected), 'conditions': conditions, 'scored_rows': len(scores),
        'score_fields_checked_per_row': len(evaluate.SCORE_FIELDS),
        'exact_score_row_matches': len(scores) - len(differences),
        'score_row_mismatches': len(differences), 'exact_final_snapshot_matches': snapshot_matches,
        'exact_gate_audit_matches': gate_audit_matches,
        'sqlite_executions': executed, 'preserved_invalid_generations': invalid,
        'raw_extraction_parse_rechecked': len(selected),
        'model_calls': 0, 'provider_calls': 0, 'network_calls': 0,
        'network_audit_guard_enabled': True, 'original_workspace_access': False,
        'package_hashes_verified_before_and_after': len(package['sha256']),
        'python_version': sys.version.split()[0], 'elapsed_seconds': round(time.monotonic() - started, 3),
        'reference_role': cohort['reference_role'],
        'limits': ['Saved-generation deterministic replay, not independent regeneration or human efficacy evidence.',
                   'Configuration labels are archived aliases; provider availability is not checked.',
                   'Point estimates/counts reproduced. Bootstrap confidence intervals are archived separately, not recomputed by this standard-library runner.'],
    }
    write_json(output / 'verification.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if differences:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
