"""Exact frozen apply_exception function, with portable dependencies."""
import copy
from policies import original
protocol = original.protocol

def apply_exception(packet,extraction,final):
    """E only bypasses B's support-intersection block on CORRECT.
    Same coverage check and identical executor/permissions remain.
    No witness, reference, case label or expected state is inspected.
    """
    out,audit=protocol.apply_gate(final,{'beliefs':extraction['beliefs']},packet)
    for original,decision,row in zip(final['memory_decisions'],out['memory_decisions'],audit,strict=True):
        if (original['operation']=='CORRECT' and decision['operation']=='HOLD'
            and row['reason']=='NOT_SUPPORTED_BY_ALL_CANDIDATES'
            and row.get('candidate_coverage_valid')):
            decision.clear(); decision.update(copy.deepcopy(original))
            row.update(after_operation='CORRECT',reason='SIMPLE_CORRECTION_EXCEPTION')
    return out,audit
