"""Prospectively frozen H-only E_text saved-proposal replay; no inference."""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PAPER=HERE.parents[1]
PRIOR=HERE.parent/'saved_output_E_comparison'
CH=PAPER/'correction_specificity_20260927'
CONDITIONAL=PAPER/'conditional_method_extension_20260927'
MAIN=CONDITIONAL/'amendments/main_execution_v2'
FREEZE=HERE/'FREEZE_V2.json'
CONTRACT=HERE/'CONTRACT.json'
sys.path.insert(0,str(PRIOR))
import replay_e as prior

def stable(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,obj):
    with path.open('x',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
def lines(path): return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()]
def h_indices(row):
    return [a['index'] for a in row.get('gate_audit',[]) if a.get('before_operation')=='CORRECT' and a.get('after_operation')=='HOLD' and a.get('reason')=='NOT_SUPPORTED_BY_ALL_CANDIDATES' and a.get('candidate_coverage_valid') is True]

def input_paths():
    paths=[HERE/'task.json',CONTRACT,HERE/'replay_e_text_v2.py',PRIOR/'FREEZE.json',PRIOR/'CONTRACT.json',PRIOR/'result/E_outputs.jsonl',PRIOR/'result/E_scores.csv',PRIOR/'result/exposure.csv',
           MAIN/'data/public.json',MAIN/'evaluation_inputs/corrected_test_reference.json',MAIN/'runner.py',CONDITIONAL/'runtime/policy.py',
           PAPER/'paper_finalization_20260926/experiment_v3/protocol.py',PAPER/'paper_finalization_20260926/experiment_v3/store.py',
           CONDITIONAL/'amendments/evaluation_v2/evaluate.py',CH/'data/public.json',CH/'data/reference.json',CH/'collection/outputs.jsonl',CH/'analysis/scores.csv',CH/'runtime/common.py',CH/'runtime/analyze.py']
    for lane in prior.selected():
        f=prior.lane_files(lane)
        paths.extend([f['outputs'],f['scores'],f['result'],f['public'],f['reference']])
    return sorted(set(paths))

def load_main():
    out={}
    for lane in prior.selected():
        alias=lane['alias']; f=prior.lane_files(lane)
        out[alias]=prior.load_outputs(f['outputs'],alias)
    return out

def load_challenge():
    out={}
    for x in lines(CH/'collection/outputs.jsonl'):
        key=(x['case_id'],x['condition'])
        if key in out: raise RuntimeError('CH_DUPLICATE')
        out[key]=x
    return out

def roster(main,ch):
    units=[]
    for lane in prior.selected():
        alias=lane['alias']; x=main[alias]
        for case_id,rep,condition in sorted(x):
            if condition=='B' and h_indices(x[(case_id,rep,'B')]):
                units.append({'study':'main','alias':alias,'case_id':case_id,'repeat':rep,'indices':h_indices(x[(case_id,rep,'B')])})
    for (case_id,condition),row in sorted(ch.items()):
        if condition=='B' and h_indices(row):
            units.append({'study':'challenge','alias':'gemini_flash','case_id':case_id,'repeat':1,'indices':h_indices(row)})
    return units

def freeze():
    if FREEZE.exists(): raise FileExistsError('FREEZE_ALREADY_EXISTS')
    main=load_main();ch=load_challenge();units=roster(main,ch)
    if len(units)!=24 or sum(u['study']=='main' for u in units)!=18:raise RuntimeError('H_ROSTER_UNEXPECTED')
    paths=input_paths()
    if not all(p.is_file() for p in paths):raise RuntimeError('INPUT_MISSING')
    hashes={str(p.relative_to(PAPER)):digest(p) for p in paths}
    save(FREEZE,{'schema':'e-text-freeze-v1','contract_sha256':digest(CONTRACT),'input_count':len(paths),
                 'inputs_sha256':hashes,'H_roster':units,'H_units':24,'outside_H_units':720,
                 'main_units':720,'challenge_units':24,'new_model_attempts':0})
    print(stable({'status':'FROZEN','inputs':len(paths),'H':len(units)}))

def verify():
    f=read(FREEZE)
    if f['contract_sha256']!=digest(CONTRACT):raise RuntimeError('CONTRACT_DRIFT')
    paths=input_paths()
    if set(f['inputs_sha256'])!={str(p.relative_to(PAPER)) for p in paths}:raise RuntimeError('INPUT_SET_DRIFT')
    for p in paths:
        if digest(p)!=f['inputs_sha256'][str(p.relative_to(PAPER))]:raise RuntimeError('INPUT_DRIFT:'+str(p))
    return f

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

def score_csv(path,key_fields):
    out={}
    with path.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            key=tuple(row[k] for k in key_fields)
            if key in out:raise RuntimeError('DUP_SCORE')
            out[key]=row
    return out

def state_hash(state):return hashlib.sha256(stable(state).encode()).hexdigest()

def run(out):
    freeze=verify()
    if out.exists():raise FileExistsError('OUTPUT_EXISTS')
    main=load_main();ch=load_challenge()
    units=roster(main,ch)
    if units!=freeze['H_roster']:raise RuntimeError('H_DRIFT')
    out.mkdir(parents=True);(out/'db').mkdir()
    runner,policy,common,evaluator=prior.load_runtime()
    spec=importlib.util.spec_from_file_location('challenge_analyze_e_text',CH/'runtime/analyze.py')
    analyze=importlib.util.module_from_spec(spec);spec.loader.exec_module(analyze)
    public_main={x['case_id']:x for x in read(MAIN/'data/public.json')['packets'] if x['split']=='test'}
    ref_main={x['case_id']:x for x in read(MAIN/'evaluation_inputs/corrected_test_reference.json')['references']}
    public_ch={x['case_id']:x for x in read(CH/'data/public.json')['cases']}
    ref_ch={x['case_id']:x for x in read(CH/'data/reference.json')['cases']}
    old_e={}
    for x in lines(PRIOR/'result/E_outputs.jsonl'):
        key=(x['model_alias'],x['case_id'],int(x['repeat']))
        if key in old_e:raise RuntimeError('E_DUP')
        old_e[key]=x
    score_e=score_csv(PRIOR/'result/E_scores.csv',('model_alias','case_id','repeat'))
    main_bc={lane['alias']:prior.load_existing_scores(prior.lane_files(lane)['scores'],lane['alias']) for lane in prior.selected()}
    ch_score=score_csv(CH/'analysis/scores.csv',('case_id','condition'))
    rows=[];scores=[];matched=[];rule=[]
    for u in units:
        study=u['study'];alias=u['alias'];case=u['case_id'];rep=u['repeat']
        if study=='main':
            b=main[alias][(case,rep,'B')];c=main[alias][(case,rep,'C')];e=old_e[(alias,case,rep)]
            row=public_main[case];packet=runner.clean_packet(row,row['packet']['db_snapshot'])
            if b['final_proposal']!=c['final_proposal'] or b['upstream_call_ids']!=c['upstream_call_ids']:raise RuntimeError('BC_PROPOSAL_DRIFT')
            extraction=prior.read_extraction_and_final(prior.lane_files(next(l for l in prior.selected() if l['alias']==alias))['collection']/'responses',b['upstream_call_ids'],packet,b['final_proposal'],runner,policy)
            final=b['final_proposal']
        else:
            b=ch[(case,'B')];c=ch[(case,'C')];e=ch[(case,'E')];row=public_ch[case]
            packet=common.clean_packet(row);extraction=b['extraction'];final=b['original_final']
            if final!=c['original_final'] or final!=e['original_final']:raise RuntimeError('CH_PROPOSAL_DRIFT')
        if not b['generation_valid'] or h_indices(b)!=u['indices']:raise RuntimeError('H_INVALID_OR_DRIFT')
        gated,audit,checks=apply_text(packet,extraction,final,policy)
        if [i for i,_ in checks]!=u['indices']:raise RuntimeError('H_INDEX_DRIFT')
        db=out/'db'/study/alias/f'{case}-r{rep}-E_text.sqlite';db.parent.mkdir(parents=True,exist_ok=True)
        policy.store.init_db(db,packet['db_snapshot'])
        receipt=policy.store.execute(db,gated,packet)
        if receipt.get('read_after_write_verified') is not True:raise RuntimeError('READ_AFTER_WRITE')
        if study=='main':
            et={**b,'condition':'E_text','gate_audit':audit,'receipt':receipt,'final_snapshot':receipt['after'],'delivered_text':final['reply']}
            scored=evaluator.score_output(et,row,ref_main[case])
            B=main_bc[alias][(case,rep,'B')];C=main_bc[alias][(case,rep,'C')];E=score_e[(alias,case,str(rep))]
            metrics=['correction_recovery','whole_state_compliance','harmful_write','extra_write','action_allowed','negative_preservation','positive_joint']
            family=next(l['model_family'] for l in prior.selected() if l['alias']==alias)
        else:
            et={**b,'condition':'E_text','gate_audit':audit,'receipt':receipt,'final_snapshot':receipt['after'],'delivered_text':final['reply'],'gated_final':gated}
            scored=analyze.score(et,row,ref_ch[case])
            B=ch_score[(case,'B')];C=ch_score[(case,'C')];E=ch_score[(case,'E')]
            metrics=['expected_state','recovered','safe_preservation','harmful_alteration','other_or_wrong_state']
            family=row['family']
        rows.append(et);scores.append(scored)
        matched.append({'study':study,'model_alias':alias,'model_family':family,'case_id':case,'repeat':rep,
                        'h_operations':len(checks),'e_text_pass':sum(reason=='PASS' for _,reason in checks),
                        'B_state_sha256':state_hash(b['final_snapshot']),'C_state_sha256':state_hash(c['final_snapshot']),
                        'E_state_sha256':state_hash(e['final_snapshot']),'E_text_state_sha256':state_hash(et['final_snapshot']),
                        'C_equals_E_text':int(c['final_snapshot']==et['final_snapshot']),
                        'E_equals_E_text':int(e['final_snapshot']==et['final_snapshot']),
                        'B_equals_E_text':int(b['final_snapshot']==et['final_snapshot']),
                        **{f'{arm}_{metric}':str(value[metric]) for arm,value in [('B',B),('C',C),('E',E),('E_text',scored)] for metric in metrics}})
        for i,reason in checks:
            decision=final['memory_decisions'][i];fact=decision['fact'];alternative_hits=[fact['value'] in s for s in packet['alternatives']]
            rule.append({'study':study,'model_alias':alias,'case_id':case,'repeat':rep,'index':i,
                         'e_text_reason':reason,'C_reason':c['gate_audit'][i].get('correction_fallback'),
                         'proposed_value':fact['value'],'alternative_literal_hits':alternative_hits,
                         'source_turn':packet['turn_id'],'fact_source_turns':fact['source_turns'],
                         'decision_source_turns':decision['source_turns'],
                         'target_fact_id':decision['target_fact_id'],'reference_kind':'AI_AUTHORED'})
    # Outside H, B/C/E original states must agree; E_text is B analytically.
    no_h=[]
    for lane in prior.selected():
        alias=lane['alias']
        for case in sorted(public_main):
            for rep in (1,2,3):
                b=main[alias][(case,rep,'B')]
                if h_indices(b):continue
                c=main[alias][(case,rep,'C')];e=old_e[(alias,case,rep)]
                if b['final_snapshot']!=c['final_snapshot'] or b['final_snapshot']!=e['final_snapshot']:
                    raise RuntimeError('NONH_STATE_DRIFT:'+alias+':'+case)
                no_h.append({'study':'main','model_alias':alias,'case_id':case,'repeat':rep,'E_text':'B_ANALYTICALLY'})
    for case in sorted(public_ch):
        b=ch[(case,'B')]
        if h_indices(b):continue
        c=ch[(case,'C')];e=ch[(case,'E')]
        if b['final_snapshot']!=c['final_snapshot'] or b['final_snapshot']!=e['final_snapshot']:
            raise RuntimeError('CH_NONH_STATE_DRIFT:'+case)
        no_h.append({'study':'challenge','model_alias':'gemini_flash','case_id':case,'repeat':1,'E_text':'B_ANALYTICALLY'})
    if len(rows)!=24 or len(no_h)!=720:raise RuntimeError('UNIT_COUNT')
    with (out/'E_text_H_outputs.jsonl').open('x',encoding='utf-8') as f:
        for x in rows:f.write(stable(x)+'\n')
    with (out/'E_text_H_scores.csv').open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for x in scores for k in x)));w.writeheader();w.writerows(scores)
    with (out/'matched_H.csv').open('x',newline='',encoding='utf-8') as f:
        fields=list(dict.fromkeys(k for x in matched for k in x));w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(matched)
    with (out/'rule_trace.csv').open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rule[0]));w.writeheader();w.writerows(rule)
    save(out/'outside_H_manifest.json',{'units':no_h,'count':720,'rule':'E_text=B analytically; no execution or new score'})
    group_summary=[]
    for study,alias in [('main',l['alias']) for l in prior.selected()]+[('challenge','gemini_flash')]:
        subset=[r for r in matched if r['study']==study and r['model_alias']==alias]
        all_count=144 if study=='main' else 24
        for arm in ('B','C','E','E_text'):
            if study=='main':
                original=main_bc[alias]
                e_all={k:v for k,v in score_e.items() if k[0]==alias}
                endpoints=[('correction_recovery','correction_eligible'),('whole_state_compliance',None),('harmful_write',None),('extra_write',None),('action_allowed',None)]
                scored_h={(r['case_id'],r['repeat']):next(s for s in scores if s['case_id']==r['case_id'] and s['repeat']==r['repeat'] and s['model_alias']==alias and r['study']=='main') for r in subset}
                all_rows=[]
                for case in sorted(public_main):
                    for rep in (1,2,3):
                        if arm=='E_text' and (case,rep) in scored_h: s=scored_h[(case,rep)]
                        elif arm=='E_text':s=original[(case,rep,'B')]
                        elif arm in ('B','C'):s=original[(case,rep,arm)]
                        else:s=e_all[(alias,case,str(rep))]
                        all_rows.append(s)
            else:
                endpoints=[('recovered','supported'),('safe_preservation','unsupported'),('expected_state',None),('harmful_alteration',None)]
                scored_h={r['case_id']:next(s for s in scores if s['case_id']==r['case_id'] and s['condition']=='E_text') for r in subset}
                all_rows=[]
                for case in sorted(public_ch):
                    if arm=='E_text' and case in scored_h:s=scored_h[case]
                    elif arm=='E_text':s=ch_score[(case,'B')]
                    else:s=ch_score[(case,arm)]
                    all_rows.append(s)
            if len(all_rows)!=all_count:raise RuntimeError('SUMMARY_COUNT')
            for metric,elig in endpoints:
                use=[s for s in all_rows if (elig is None or (s['label']==elig if study=='challenge' else s[elig] in (True,'True')))]
                group_summary.append({'study':study,'model_alias':alias,'condition':arm,'metric':metric,
                                      'true_count':sum(s[metric] in (True,'True',1,'1') for s in use),'denominator':len(use),
                                      'H_units':len(subset),'outside_H_analytical':all_count-len(subset)})
    with (out/'effect_table.csv').open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(group_summary[0]));w.writeheader();w.writerows(group_summary)
    reason_counts={reason:sum(r['e_text_reason']==reason for r in rule) for reason in sorted({r['e_text_reason'] for r in rule})}
    result={'schema':'e-text-posthoc-result-v1','freeze_sha256':digest(FREEZE),'H_new_rows':len(rows),
            'outside_H_analytical_units':len(no_h),'new_model_attempts':0,'training_calls':0,
            'old_scores_recomputed':False,'e_text_reason_counts':reason_counts,'effect_table':group_summary}
    save(out/'RESULT.json',result)
    print(stable({'status':'COMPLETE','H_new_rows':len(rows),'outside_H':len(no_h),'reasons':reason_counts}))

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','run']);p.add_argument('--output-dir',type=Path,default=HERE/'result')
    a=p.parse_args()
    if a.mode=='freeze':freeze()
    else:run(a.output_dir)
if __name__=='__main__':main()
