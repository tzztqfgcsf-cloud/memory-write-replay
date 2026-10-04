"""New controls plus read-only prior scores; descriptive operation separation."""
import copy
import csv
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent
BASE=R.parent/'strong_baselines_20261001'
sys.path.insert(0,str(BASE))
import run_offline as h

KEY=['model_alias','case_id','repeat']
CONDS=['G','R_AGREE','R_ALLOW','R_LITERAL','R_WITNESS']
METRICS={'positive_joint':'positive_eligible','correction_recovery':'correction_eligible',
         'harmful_write':None,'invalid_final':None,'whole_state_compliance':None}

def key(o):return tuple(o[k] for k in KEY)
def fact(f):return tuple(f[k] for k in ['subject','relation','value','time'])
def boolcol(d):
    for c in list(METRICS)+['positive_eligible','correction_eligible','generation_valid']:
        assert d[c].isin([True,False]).all(),c
    return d

def main():
    assert (R/'RUN_COMPLETE.json').exists()
    assert not (R/'ANALYSIS_COMPLETE.json').exists(),'Analysis already complete'
    m=h.read(str(BASE/'input_manifest.json'))
    old=pd.read_csv(m['integrated_scores_path'])
    old=old[old.model_alias.isin(m['selected_models']) & (old.split=='test') & (old.condition=='G')]
    prior=pd.read_csv(BASE/'new_scores.csv');prior=prior[prior.condition.isin(['R_LITERAL','R_WITNESS'])]
    new=pd.read_csv(R/'scores.csv')
    df=boolcol(pd.concat([old,prior,new],ignore_index=True))
    assert len(df)==3024*5 and not df.duplicated(KEY+['condition']).any()
    df['stratum']=np.where(df.correction_eligible,'CORRECTION_ELIGIBLE',np.where(df.positive_eligible,'NEW_INFORMATION_ELIGIBLE','NO_POSITIVE_CHANGE'))
    counts=df.groupby('condition',sort=False)[list(METRICS)+['positive_eligible','correction_eligible']].sum().reindex(CONDS)
    counts['observations']=3024;counts.to_csv(R/'condition_totals.csv')
    df.groupby(['model_alias','condition'])[list(METRICS)+['positive_eligible','correction_eligible']].sum().to_csv(R/'model_totals.csv')
    strata=df.groupby(['stratum','condition']).agg(observations=('case_id','size'),cases=('case_id','nunique'),positive_joint=('positive_joint','sum'),correction_recovery=('correction_recovery','sum'),harmful_write=('harmful_write','sum'),invalid_final=('invalid_final','sum'),whole_state_compliance=('whole_state_compliance','sum')).reset_index()
    strata.to_csv(R/'case_strata.csv',index=False)
    comparisons=[('R_AGREE','G'),('R_ALLOW','G'),('R_LITERAL','G'),('R_WITNESS','G'),
                 ('R_ALLOW','R_AGREE'),('R_WITNESS','R_AGREE'),('R_WITNESS','R_ALLOW'),('R_WITNESS','R_LITERAL')]
    results=[]
    for a,b in comparisons:
        x=df[df.condition==a].set_index(KEY);y=df[df.condition==b].set_index(KEY)
        assert set(x.index)==set(y.index)
        for metric,elig in METRICS.items():
            z=pd.DataFrame({'before':y[metric].astype(int),'after':x[metric].astype(int)})
            if elig:z=z[x[elig]]
            z['delta']=z.after-z.before;z=z.reset_index()
            for model in m['selected_models']+['ALL21']:
                v=z if model=='ALL21' else z[z.model_alias==model]
                cd=v.groupby('case_id').delta.mean().to_numpy()
                rng=np.random.default_rng(20261002)
                bs=cd[rng.integers(0,len(cd),(5000,len(cd)))].mean(axis=1)*100
                lo,hi=np.quantile(bs,[.025,.975])
                results.append(dict(model_alias=model,candidate=a,baseline=b,metric=metric,cases=len(cd),observations=len(v),before=int(v.before.sum()),after=int(v.after.sum()),gains=int((v.delta>0).sum()),losses=int((v.delta<0).sum()),delta_pp=float(cd.mean()*100),ci_low_pp=float(lo),ci_high_pp=float(hi)))
    pairs=pd.DataFrame(results);pairs.to_csv(R/'paired_comparisons.csv',index=False)
    outmap={}
    for path in [BASE/'outputs.jsonl',R/'outputs.jsonl']:
        for line in path.open():
            o=json.loads(line)
            if o['condition'] in CONDS:outmap[key(o)+(o['condition'],)]=o
    scoremap=df.set_index(KEY+['condition']).to_dict('index')
    decision_rows=[];effect_rows=[];identity_checks=0
    for e in m['episodes']:
        k=key(e);row,pk,_,_=h.inputs(e)
        ref=h.point(e['reference']['path'],e['reference']['json_pointer'])
        g=h.saved(e['conditions']['G']);outmap[k+('G',)]=g
        proposal=g.get('final_proposal')
        initial={f['fact_id']:fact(f) for f in pk['db_snapshot']['facts']}
        required={fact(f) if isinstance(f,dict) else tuple(f) for f in ref['required_facts']}
        forbidden={fact(f) if isinstance(f,dict) else tuple(f) for f in ref['forbidden_facts']}
        operation_by_condition={}
        for c in CONDS:
            o=outmap[k+(c,)];assert o['final_proposal']==proposal
            valid=bool(scoremap[k+(c,)]['generation_valid'])
            audit={a['index']:a for a in o.get('gate_audit',[])}
            receipt=o.get('receipt') or {};executed={a['index']:a for a in receipt.get('decisions',[])}
            ops={}
            for i,d in enumerate((proposal or {}).get('memory_decisions',[])):
                op=d['operation']
                if op not in ['APPEND','CORRECT']:continue
                after=(audit.get(i,{}).get('after_operation',op) if valid else 'UNAVAILABLE')
                ex=executed.get(i,{})
                applied=valid and ex.get('status')=='APPLIED' and ex.get('operation')==op
                af=ex.get('after');bad=False
                if applied and isinstance(af,dict):
                    ft=fact(af)
                    bad=bool(ft not in set(initial.values())|required or (ft not in set(initial.values()) and ft in forbidden) or (op=='CORRECT' and d['target_fact_id'] in ref['must_preserve_ids'] and initial[d['target_fact_id']]!=ft))
                decision_rows.append(dict(zip(KEY,k))|dict(condition=c,index=i,operation=op,gate_after=after,gate_admitted=after==op,held=after=='HOLD',unavailable=after=='UNAVAILABLE',executed=applied,executed_reference_violating=bad,reason=audit.get(i,{}).get('reason','DIRECT_REVIEW' if valid else 'INVALID_PIPELINE')))
                ops[i]=(op,after)
            operation_by_condition[c]=ops
        # All four gates must have identical APPEND decisions; only CORRECT fallback differs.
        for c in ['R_ALLOW','R_LITERAL','R_WITNESS']:
            assert {i:a for i,a in operation_by_condition[c].items() if a[0]=='APPEND'}=={i:a for i,a in operation_by_condition['R_AGREE'].items() if a[0]=='APPEND'}
            identity_checks+=1
        for a,b in comparisons:
            x=scoremap[k+(a,)];y=scoremap[k+(b,)]
            changed=set()
            for i,(op,after) in operation_by_condition[a].items():
                if after != operation_by_condition[b][i][1]:changed.add(op)
            kind=('+'.join(sorted(changed)) or 'NONE')
            if x['generation_valid'] != y['generation_valid']:kind='VALIDITY_CHANGE'
            for metric in ['harmful_write','positive_joint','correction_recovery']:
                if METRICS[metric] and not x[METRICS[metric]]:continue
                if x[metric] != y[metric]:
                    effect_rows.append(dict(zip(KEY,k))|dict(candidate=a,baseline=b,metric=metric,before=int(y[metric]),after=int(x[metric]),changed_operation_set=kind))
    d=pd.DataFrame(decision_rows);d.to_csv(R/'operation_decisions.csv',index=False)
    totals=d.groupby(['condition','operation']).agg(proposed=('index','size'),gate_admitted=('gate_admitted','sum'),held=('held','sum'),unavailable=('unavailable','sum'),executed=('executed','sum'),executed_reference_violating=('executed_reference_violating','sum')).reset_index()
    totals.to_csv(R/'operation_totals.csv',index=False)
    effects=pd.DataFrame(effect_rows);effects.to_csv(R/'endpoint_change_traces.csv',index=False)
    effects.groupby(['candidate','baseline','metric','before','after','changed_operation_set']).size().rename('observations').reset_index().to_csv(R/'endpoint_changes_by_operation.csv',index=False)
    # Descriptive sensitivity uses the same observations valid in all compared pipelines.
    joint=df.groupby(KEY).generation_valid.all();validkeys=set(joint[joint].index)
    valid=df[df.apply(lambda r:tuple(r[k] for k in KEY) in validkeys,axis=1)]
    valid.groupby('condition').agg(observations=('case_id','size'),harmful_write=('harmful_write','sum'),positive_joint=('positive_joint','sum'),correction_recovery=('correction_recovery','sum')).to_csv(R/'joint_valid_sensitivity.csv')
    summary=dict(counts=counts.reset_index().to_dict('records'),operations=totals.to_dict('records'),case_strata=strata.to_dict('records'),comparisons=pairs[pairs.model_alias=='ALL21'].to_dict('records'),append_identity_checks=identity_checks)
    (R/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    (R/'ANALYSIS_COMPLETE.json').write_text(json.dumps(dict(status='COMPLETE',model_calls=0,new_scored_rows=6048,old_scores_recomputed=0,case_bootstrap_draws=5000,seed=20261002,append_identity_checks=identity_checks,operation_count_note='Decisions, not case endpoints; multiple decisions per observation, non-additive harms',reference='Unchanged authored reference, not independent human gold',analysis_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2))
    print(counts.to_string());print(totals.to_string(index=False))

if __name__=='__main__':main()
