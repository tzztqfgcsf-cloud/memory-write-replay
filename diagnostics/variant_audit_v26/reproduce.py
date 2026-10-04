#!/usr/bin/env python3
"""Mechanical v26 Appendix I.1 audit; archived-score inspection, no rescoring."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIELDS = ("subject", "relation", "value", "time")
COMPONENTS = ("required_present", "forbidden_absent", "preserve_ids_exact",
              "remove_ids_absent", "no_extra_facts", "obsolete_versions_absent")
# These numbers validate the published table, never choose an observation/class.
EXPECTED = {
    "avoided_observations": 82, "append_holds": 71, "variant_observations": 52,
    "variant_cases": 9, "other_append_holds": 19, "correction_holds": 11,
    "variant_required_absent_both": 52,
    "class_counts": {"subject_label": 29, "spacing": 6, "value_form": 17,
                     "append_unlisted": 17, "append_forbidden": 2,
                     "correct_forbidden": 11},
    "class_case_counts": {
        "subject_label/CT13": 10, "subject_label/CT14": 3,
        "subject_label/CT15": 7, "subject_label/CT16": 8,
        "subject_label/CT27": 1, "spacing/CT20": 6,
        "value_form/CT31": 11, "value_form/CT44": 5, "value_form/CT26": 1,
        "append_forbidden/CT23": 2,
    },
}


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tuple_of(fact):
    return tuple(fact[field] for field in FIELDS)


def fact_of(value):
    return dict(zip(FIELDS, value))


def normalize(text):
    """The printed NFC / case-fold / whitespace-removal rule."""
    return "".join(unicodedata.normalize("NFC", text).casefold().split())


def subjects_match(left, right):
    left, right = normalize(left), normalize(right)
    return (left == right or left in right or right in left
            or {left, right} <= {"participant", "p1"})


def variant_class(held, required):
    # Relation and time must be the same; only subject/value surface forms vary.
    if (held["relation"], held["time"]) != (required["relation"], required["time"]):
        return None
    hs, hv = normalize(held["subject"]), normalize(held["value"])
    rs, rv = normalize(required["subject"]), normalize(required["value"])
    if hs == rs and hv == rv and (held["subject"], held["value"]) != (
            required["subject"], required["value"]):
        return "spacing"
    if hv == rv and subjects_match(held["subject"], required["subject"]):
        return "subject_label"
    if subjects_match(held["subject"], required["subject"]) and (hv in rv or rv in hv):
        return "value_form"
    return None


def audit(episodes, cases):
    # New facts are derived from every included condition's archived conforming
    # state, not from a hand-authored CTxx-to-required-fact lookup table.
    new_facts = defaultdict(set)
    conforming = defaultdict(list)
    for index, episode in enumerate(episodes):
        public = cases["public_rows"][episode["public_row_id"]]
        initial = {tuple_of(f) for f in public["packet"]["db_snapshot"]["facts"]}
        for condition, output in episode["outputs"].items():
            if episode["expected_scores"][condition]["whole_state_compliance"]:
                added = {tuple_of(f) for f in output["final_snapshot"]["facts"]} - initial
                new_facts[episode["case_id"]].update(added)
                conforming[episode["case_id"]].append({
                    "episode_index": index, "condition": condition,
                    "new_facts": [fact_of(f) for f in sorted(added)]})

    rows, issues = [], []
    variants = {"spacing", "subject_label", "value_form"}
    for index, episode in enumerate(episodes):
        review = episode["expected_scores"]["G"]
        hybrid = episode["expected_scores"]["R_WITNESS"]
        if not (review["harmful_write"] and not hybrid["harmful_write"]):
            continue
        output = episode["outputs"]["R_WITNESS"]
        held = [g for g in output["gate_audit"] if g["after_operation"] == "HOLD"
                and g["before_operation"] in {"APPEND", "CORRECT"}]
        if len(held) != 1:
            issues.append({"episode_index": index, "held_operations": len(held)})
        for gate in held:
            matches = []
            decision = output["final_proposal"]["memory_decisions"][gate["index"]]
            review_decision = episode["outputs"]["G"]["final_proposal"]["memory_decisions"][gate["index"]]
            if decision != review_decision:
                issues.append({"episode_index": index, "review_hybrid_proposal_difference": True})
            fact = decision["fact"]
            if gate["before_operation"] == "APPEND":
                for required in sorted(new_facts[episode["case_id"]]):
                    label = variant_class(fact, fact_of(required))
                    if label:
                        matches.append((label, fact_of(required)))
            if len(matches) > 1:
                issues.append({"episode_index": index, "ambiguous_variant_matches": matches})
            label, required = matches[0] if matches else (None, None)
            if label is None:
                prefix = "append" if gate["before_operation"] == "APPEND" else "correct"
                label = prefix + ("_forbidden" if not review["forbidden_absent"] else "_unlisted")
            if gate["before_operation"] == "APPEND" and review["forbidden_absent"]:
                if review["no_extra_facts"] or not all(review[c] for c in
                        ("preserve_ids_exact", "remove_ids_absent", "obsolete_versions_absent")):
                    issues.append({"episode_index": index, "append_not_only_unlisted_violation": True})
            if label in variants:
                union = new_facts[episode["case_id"]]
                if len(union) != 1 or any(len(c["new_facts"]) != 1
                                         for c in conforming[episode["case_id"]]):
                    issues.append({"case_id": episode["case_id"],
                                   "conforming_states_do_not_share_one_new_fact": True})
                if required not in cases["references"][episode["reference_id"]]["required_facts"]:
                    issues.append({"episode_index": index, "new_fact_not_required": required})
            prefix = f"/{index}"
            rows.append({
                "observation_id": f'{episode["model_alias"]}/{episode["case_id"]}/r{episode["repeat"]}',
                "episode_index": index, "model_alias": episode["model_alias"],
                "case_id": episode["case_id"], "repeat": episode["repeat"],
                "class": label, "held_operation": gate["before_operation"],
                "held_tuple": compact({k: fact[k] for k in FIELDS}),
                "required_new_fact": compact(required),
                "review_failed_reference_components": compact([c for c in COMPONENTS if not review[c]]),
                "review_harmful_write": review["harmful_write"],
                "hybrid_harmful_write": hybrid["harmful_write"],
                "review_required_present": review["required_present"],
                "hybrid_required_present": hybrid["required_present"],
                "review_positive_joint": review["positive_joint"],
                "hybrid_positive_joint": hybrid["positive_joint"],
                "saved_gate": compact(gate),
                "saved_review_score_pointer": prefix + "/expected_scores/G",
                "saved_hybrid_score_pointer": prefix + "/expected_scores/R_WITNESS",
                "held_decision_pointer": prefix + f'/outputs/R_WITNESS/final_proposal/memory_decisions/{gate["index"]}',
                "gate_pointer": prefix + f'/outputs/R_WITNESS/gate_audit/{output["gate_audit"].index(gate)}',
                "review_snapshot_pointer": prefix + "/outputs/G/final_snapshot",
                "hybrid_snapshot_pointer": prefix + "/outputs/R_WITNESS/final_snapshot",
                "public_row_id": episode["public_row_id"], "reference_id": episode["reference_id"],
                "raw_review_response_id": episode["responses"].get("review_Q"),
                "source_provenance": compact(episode["provenance"]),
            })
    counts = Counter(r["class"] for r in rows)
    variant_rows = [r for r in rows if r["class"] in variants]
    actual = {
            "avoided_observations": len(rows),
        "append_holds": sum(r["held_operation"] == "APPEND" for r in rows),
        "variant_observations": len(variant_rows),
        "variant_cases": len({r["case_id"] for r in variant_rows}),
        "other_append_holds": sum(r["held_operation"] == "APPEND" and r["class"] not in variants for r in rows),
        "correction_holds": sum(r["held_operation"] == "CORRECT" for r in rows),
        "variant_required_absent_both": sum(not r["review_required_present"] and
                                             not r["hybrid_required_present"] for r in variant_rows),
        "class_counts": dict(sorted(counts.items())),
        "class_case_counts": dict(sorted(Counter(f'{r["class"]}/{r["case_id"]}' for r in rows).items())),
    }
    mismatches = {}
    for key, published in EXPECTED.items():
        # Table I9 lists individual counts for variants and CT23; its unlisted
        # append/correction rows give grouped counts only. Other case counts
        # remain derived output, never labelled as published expectations.
        reproduced = ({name: actual[key].get(name, 0) for name in published}
                      if key == "class_case_counts" else actual[key])
        if published != reproduced:
            mismatches[key] = {"published": published, "reproduced": reproduced}
    selected_cases = sorted({r["case_id"] for r in rows})
    required_trace = {case: {"new_facts_in_conforming_states": [fact_of(f) for f in sorted(new_facts[case])],
                             "conforming_observations": conforming[case]} for case in selected_cases}
    summary = {
        "schema": "v26-variant-audit-1", "status": "PASS" if not mismatches and not issues else "MISMATCH",
        "comparison": "saved G (Review) vs saved R_WITNESS (Review+Witness)",
        "selection": "G.harmful_write=true and R_WITNESS.harmful_write=false in saved expected_scores",
        "input_episodes": len(episodes), "input_cases": len(cases["public_rows"]),
        "conditions_used_for_conforming_states": sorted(episodes[0]["outputs"]),
        "actual": actual, "published": EXPECTED, "mismatches": mismatches, "structural_issues": issues,
        "derived_case_count_note": "actual.class_case_counts includes additional per-case breakdowns of the grouped unlisted-append and forbidden-correction rows; these breakdowns are not individual published Table I9 counts.",
        "variant_case_ids": sorted({r["case_id"] for r in variant_rows}),
        "new_model_calls": 0, "new_score_evaluations": 0,
        "reference_role": "AUTHORED_REFERENCE_NOT_INDEPENDENT_HUMAN_GOLD",
        "rule_origin": "New portable transcription of printed v26 Appendix I.1 rule; original audit code not recovered",
        "limitations": ["Post hoc mechanical representation audit, not semantic adjudication.",
                        "No translation, subject-role restructuring, or semantic synonym inference.",
                        "Only the saved 21-configuration, three-repetition, 48-case cohort is inspected.",
                        "Archived scores and proposal/state/gate artifacts are never rewritten or rescored."],
    }
    return rows, required_trace, summary


def input_hashes():
    expected = json.loads((HERE / "SOURCE_HASHES.json").read_text(encoding="utf-8"))["files"]
    actual = {path: sha(ROOT / path) for path in expected}
    if actual != expected:
        raise ValueError("Input hashes differ from SOURCE_HASHES.json")
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="New directory outside core and this diagnostic")
    parser.add_argument("--verify-archived", action="store_true",
                        help="Also require byte-identical results to this folder's analysis/")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() or output.is_relative_to(HERE) or output.is_relative_to(ROOT / "core"):
        parser.error("Output must be new and outside core/ and diagnostics/variant_audit_v26/")
    before = input_hashes()
    with gzip.open(ROOT / "core/data/episodes.json.gz", "rt", encoding="utf-8") as stream:
        episodes = json.load(stream)
    with gzip.open(ROOT / "core/data/cases.json.gz", "rt", encoding="utf-8") as stream:
        cases = json.load(stream)
    rows, required, summary = audit(episodes, cases)
    output.mkdir(parents=True)
    with (output / "rows.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_json(output / "required_fact_trace.json", required)
    write_json(output / "summary.json", summary)
    write_json(output / "input_hashes.json", before)
    if input_hashes() != before:
        raise ValueError("Inputs changed during the audit")
    if args.verify_archived:
        for name in ("rows.csv", "required_fact_trace.json", "summary.json", "input_hashes.json"):
            if sha(output / name) != sha(HERE / "analysis" / name):
                raise ValueError(f"Archived audit mismatch: {name}")
    print(compact({"status": summary["status"], "counts": summary["actual"],
                   "archived_results_verified": args.verify_archived}))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
