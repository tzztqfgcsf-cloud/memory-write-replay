"""Fixed simple E_text rule, ported unchanged from the post-hoc diagnostic.
New local runs freeze this rule before generation; no reference or witness use.
"""
import copy

def h_indices(row):
    return [a['index'] for a in row.get('gate_audit',[]) if a.get('before_operation')=='CORRECT' and a.get('after_operation')=='HOLD' and a.get('reason')=='NOT_SUPPORTED_BY_ALL_CANDIDATES' and a.get('candidate_coverage_valid') is True]

def e_text_reason(packet,decision):
    """Reference-blind fixed text check. Return first failed check or PASS."""
    fact=decision.get('fact'); target=decision.get('target_fact_id')
    if not isinstance(fact,dict) or not isinstance(target,str) or not target:return 'MISSING_PROPOSAL_OR_TARGET'
    matched=[f for f in packet['db_snapshot']['facts'] if f['fact_id']==target]
    if len(matched)!=1:return 'TARGET_NOT_UNIQUE_OR_MISSING'
    old=matched[0]
    if any(old[k]!=fact[k] for k in ('subject','relation','time')):return 'TARGET_IDENTITY_OR_TIME_CHANGED'
    if old['value']==fact['value']:return 'VALUE_UNCHANGED'
    turn=packet['turn_id']
    if turn not in fact['source_turns'] or turn not in decision['source_turns']:return 'CURRENT_SOURCE_NOT_CITED'
    if not all(fact['value'] in alternative for alternative in packet['alternatives']):return 'VALUE_NOT_LITERAL_IN_ALL_ALTERNATIVES'
    return 'PASS'

def apply_text(packet,extraction,final,policy):
    gated,audit=policy.protocol.apply_gate(final,{'beliefs':extraction['beliefs']},packet)
    traces=[]
    for i in h_indices({'gate_audit':audit}):
        decision=final['memory_decisions'][i]
        reason=e_text_reason(packet,decision)
        traces.append((i,reason))
        if reason=='PASS':
            gated['memory_decisions'][i]=copy.deepcopy(decision)
            audit[i]['after_operation']='CORRECT';audit[i]['reason']='E_TEXT_LITERAL_EXCEPTION'
        else:audit[i]['e_text_fallback']=reason
    return gated,audit,traces

