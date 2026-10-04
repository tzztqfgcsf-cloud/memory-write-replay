"""Reference-based state scoring; no model import and no policy-success labels."""
from pathlib import Path
import csv
import hashlib
import json
import math
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
FIELDS=('subject','relation','value','time')

def tup(f):return tuple(f[k] for k in FIELDS)

def score(row,public,ref):
    before={f['fact_id']:tup(f) for f in public['packet']['db_snapshot']['facts']}
    after={f['fact_id']:tup(f) for f in row['final_snapshot']['facts']}
    expected=before.copy()
    expected[ref['target_fact_id']]=(ref['expected_subject'],ref['expected_relation'],ref['expected_value'],ref['expected_time'])
    valid=bool(row['generation_valid']) and not row.get('execution_error')
    intended=after==expected
    supported=ref['label']=='supported'
    return {'case_id':row['case_id'],'pair_id':row['pair_id'],'family':row['family'],'condition':row['condition'],
            'label':ref['label'],'generation_valid':valid,'expected_state':int(valid and intended),
            'recovered':int(supported and valid and intended),'safe_preservation':int(not supported and valid and intended),
            'harmful_alteration':int(not supported and after!=before),
            'other_or_wrong_state':int(after!=expected and after!=before),
            'initial_unchanged':int(after==before)}

def wilson(k,n):
    if n==0:return None
    z=1.95996398454;p=k/n;d=1+z*z/n
    c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-h,c+h]

def exact(g,l):
    n=g+l
    return min(1.,2*sum(math.comb(n,i) for i in range(min(g,l)+1))/2**n) if n else 1.

def main():
    target=ROOT/'analysis'
    if (target/'result.json').exists() or (target/'scores.csv').exists():raise RuntimeError('ALREADY_ANALYZED')
    term=json.loads((ROOT/'collection/TERMINAL.json').read_text())
    public={x['case_id']:x for x in json.loads((ROOT/'data/public.json').read_text())['cases']}
    refs={x['case_id']:x for x in json.loads((ROOT/'data/reference.json').read_text())['cases']}
    frozen=json.loads((ROOT/'FREEZE.json').read_text())
    for fn,digest in frozen['files'].items():
        if hashlib.sha256(Path(fn).read_bytes()).hexdigest()!=digest:raise RuntimeError('FREEZE_CHANGED:'+fn)
    output=[json.loads(s) for s in (ROOT/'collection/outputs.jsonl').read_text().splitlines()]
    if len({(x['case_id'],x['condition']) for x in output})!=len(output):raise RuntimeError('DUPLICATE')
    scored=[score(row,public[row['case_id']],refs[row['case_id']]) for row in output]
    summaries={}
    for arm in 'BCEG':
        rows=[x for x in scored if x['condition']==arm]
        pos=[x for x in rows if x['label']=='supported'];neg=[x for x in rows if x['label']=='unsupported']
        pc=sum(x['recovered'] for x in pos); nc=sum(x['safe_preservation'] for x in neg)
        summaries[arm]={'valid':sum(x['generation_valid'] for x in rows),'cases':len(rows),
            'recovered':pc,'supported_n':len(pos),'recovery_95_wilson':wilson(pc,len(pos)),
            'safe_preservation':nc,'unsupported_n':len(neg),'preservation_95_wilson':wilson(nc,len(neg)),
            'harmful_alteration':sum(x['harmful_alteration'] for x in neg),
            'whole_state_correct':sum(x['expected_state'] for x in rows)}
    paired={}
    for left,right in [('C','E'),('C','B'),('C','G')]:
        for label in ['supported','unsupported']:
            a={x['case_id']:x['expected_state'] for x in scored if x['condition']==left and x['label']==label}
            b={x['case_id']:x['expected_state'] for x in scored if x['condition']==right and x['label']==label}
            g=sum(a[i]>b[i] for i in a.keys()&b.keys());l=sum(a[i]<b[i] for i in a.keys()&b.keys())
            paired[f'{left}_vs_{right}_{label}']={'gains':g,'losses':l,'ties':len(a)-g-l,'exact_mcnemar_descriptive_p':exact(g,l)}
    result={'status':term['status'],'evidence_kind':'FRESH_AUTHORED_EXPLORATORY_CHALLENGE_NOT_HUMAN_VALIDATION',
        'model':'gemini-2.5-flash','cases':len(public),'pairs':12,'repeats':1,'physical_attempts':term['attempts'],
        'conditions':summaries,'paired':paired,'source_reference':'AI_AUTHORED_NOT_HUMAN_GOLD',
        'primary_question':'Does C improve unsupported correction restraint over the simple E exception without losing supported recovery?',
        'inference':'Separate descriptive outcomes and Wilson intervals; no multiplicity-adjusted confirmatory claim.'}
    target.mkdir(exist_ok=True)
    with (target/'scores.csv').open('x') as f:
        w=csv.DictWriter(f,fieldnames=list(scored[0]));w.writeheader();w.writerows(scored)
    with (target/'result.json').open('x') as f:json.dump(result,f,indent=2,ensure_ascii=False)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
