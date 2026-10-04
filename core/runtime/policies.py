"""Reference-blind, offline policy alternatives. No provider imports."""
import copy
import importlib.util
from pathlib import Path
import unicodedata

RUNTIME = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

original = load('baseline_original_policy', RUNTIME / 'policy.py')
literal = load('baseline_original_literal', RUNTIME / 'literal.py')


def norm(s):
    return ' '.join(unicodedata.normalize('NFC', s).casefold().split())


def key(f):
    return (norm(f['subject']), f['relation'], norm(f['value']), f['time'])


def normalized_agree(packet, extraction, final):
    """Only support equality changes; raw decisions and exact target IDs stay intact."""
    protocol = original.protocol
    gated, audit = protocol.apply_gate(final, {'beliefs': extraction['beliefs']}, packet)
    try:
        protocol.validate_beliefs({'beliefs': extraction['beliefs']}, packet)
        sets = [{key(f) for f in b['facts']} for b in extraction['beliefs']]
        shared = set.intersection(*sets) if sets else set()
    except protocol.ProtocolError:
        shared = set()
    committed = {key(f) for f in packet['db_snapshot']['facts']}
    for i, (d, a) in enumerate(zip(final['memory_decisions'], audit, strict=True)):
        if d['operation'] not in {'CORRECT', 'APPEND'} or d['fact'] is None:
            continue
        if a['after_operation'] != 'HOLD':
            continue
        if key(d['fact']) in shared or key(d['fact']) in committed:
            gated['memory_decisions'][i] = copy.deepcopy(d)
            a.update(after_operation=d['operation'], reason='NORMALIZED_TUPLE_SUPPORT')
    return gated, audit


def normalized_literal_reason(packet, decision):
    # Run all original checks on originals. Only the final lexical containment
    # predicate may change; no output, identity, polarity or reference is repaired.
    reason = literal.e_text_reason(packet, decision)
    if reason != 'VALUE_NOT_LITERAL_IN_ALL_ALTERNATIVES':
        return reason
    value = norm(decision['fact']['value'])
    if value and all(value in norm(a) for a in packet['alternatives']):
        return 'PASS'
    return reason


def normalized_literal(packet, extraction, final):
    gated, audit = original.protocol.apply_gate(final, {'beliefs': extraction['beliefs']}, packet)
    for i in literal.h_indices({'gate_audit': audit}):
        reason = normalized_literal_reason(packet, final['memory_decisions'][i])
        audit[i]['normalized_literal_reason'] = reason
        if reason == 'PASS':
            gated['memory_decisions'][i] = copy.deepcopy(final['memory_decisions'][i])
            audit[i].update(after_operation='CORRECT', reason='NORMALIZED_LITERAL_EXCEPTION')
    return gated, audit


def gate(condition, packet, extraction, final):
    if condition == 'N_AGREE':
        return normalized_agree(packet, extraction, final)
    if condition == 'N_LITERAL':
        return normalized_literal(packet, extraction, final)
    if condition in {'EXACT_LITERAL', 'R_LITERAL'}:
        g, a, _ = literal.apply_text(packet, extraction, final, original)
        return g, a
    if condition == 'R_WITNESS':
        return original._gated_final(packet, extraction, final, 'C')
    raise ValueError(condition)
