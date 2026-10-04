from pathlib import Path
import csv,json,collections,hashlib,datetime
P=Path(__file__).parent;D=Path('outputs/first_repeat_integrated_20261001/tables');A=Path('outputs/all_model_evidence_integration_20261001/tables')
def read(p):return list(csv.DictReader(p.open()))
rows=read(D/'all_saved_scores_with_provenance.csv');coverage=read(D/'coverage.csv');cis=read(A/'saved_intervals_by_cohort.csv')
by=collections.defaultdict(lambda:collections.defaultdict(list))
for x in rows:by[x['model_alias']][x['condition']].append(x)
assert len({(x['model_alias'],x['repeat'],x['case_id'],x['condition']) for x in rows})==len(rows)
complete=[]
for m,d in by.items():
 if all(len(d[c])==144 and all(sum(x['repeat']==str(r) for x in d[c])==48 for r in [1,2,3]) for c in ['D','G','B','C','CR','R','SR1']):complete.append(m)
# Discover archived condition names before relying on alias R.
if not complete:
 complete=[m for m,d in by.items() if len(d)==7 and all(len(v)==144 and all(sum(x['repeat']==str(r) for x in v)==48 for r in [1,2,3]) for v in d.values())]
invalid=lambda m,c:sum(x['invalid_final']=='True' for x in by[m][c])
selected=sorted(m for m in complete if max(invalid(m,c) for c in ['G','CR'])<=7)
assert len(complete)==28 and len(selected)==21,(len(complete),len(selected))
labels={x['model_alias']:x for x in coverage};metrics=['positive_joint','correction_recovery','harmful_write','invalid_final']
outrows={}; flat=[]
for m in complete:
 outrows[m]={}
 for metric in metrics:
  e={'positive_joint':'positive_eligible','correction_recovery':'correction_eligible'}.get(metric)
  vals={c:[x for x in by[m][c] if not e or x[e]=='True'] for c in ['G','CR']};n=len(vals['G']);assert n==len(vals['CR'])
  b=sum(x[metric]=='True' for x in vals['G']);a=sum(x[metric]=='True' for x in vals['CR']);eff=(a-b)/n
  match=[x for x in cis if x['model']==m and x['left']=='CR' and x['right']=='G' and x['outcome']==metric and int(x['observations'])==n and abs(float(x['effect'])-eff)<1e-10]
  ci=match[0] if match else None
  q={'model':m,'label':labels[m]['label'],'group':labels[m]['group'],'metric':metric,'repeats':3,'cases':n//3,'observations':n,'before_count':b,'after_count':a,'raw_effect':eff,'raw_ci_low':float(ci['low']) if ci else None,'raw_ci_high':float(ci['high']) if ci else None,'interval_source':ci['source'] if ci else None}
  benefit=-1 if metric in ['harmful_write','invalid_final'] else 1
  q['benefit_effect']=eff*benefit;q['benefit_ci_low']=(float(ci['low']) if benefit==1 else -float(ci['high'])) if ci else None;q['benefit_ci_high']=(float(ci['high']) if benefit==1 else -float(ci['low'])) if ci else None
  outrows[m][metric]=q
  if m in selected:flat.append(q)
def summary(ms):
 return {metric:{'increase':sum(outrows[m][metric]['raw_effect']>0 for m in ms),'decrease':sum(outrows[m][metric]['raw_effect']<0 for m in ms),'tie':sum(outrows[m][metric]['raw_effect']==0 for m in ms)} for metric in metrics}
sensitivity=[]
for limit,label in [(0,'100%'),(7,'95%'),(14,'90%'),(144,'No validity filter')]:
 ms=sorted(m for m in complete if max(invalid(m,c) for c in ['G','CR'])<=limit)
 sensitivity.append({'validity':label,'n':len(ms),'models':ms,'summary':summary(ms)})
stab=read(D/'repeat_stability.csv');rep=[];signs=collections.defaultdict(list)
for r in ['1','2','3']:
 vals=[float(x['effect']) for x in stab if x['model'] in selected and x['repeat']==r];assert len(vals)==21
 rep.append({'repeat':int(r),'n':len(vals),'improved':sum(v>0 for v in vals),'worsened':sum(v<0 for v in vals),'tied':sum(v==0 for v in vals)})
for x in stab:
 if x['model'] in selected:signs[x['model']].append((float(x['effect'])>0)-(float(x['effect'])<0))
manifest=[]
for x in coverage:
 m=x['model_alias']; full=m in complete
 manifest.append({**x,'main_included':m in selected,'complete_three_repeats':full,'valid_review_cr':f'{144-invalid(m,"G")}/144; {144-invalid(m,"CR")}/144' if full else 'Incomplete','reason':'Included' if m in selected else 'Below 95% valid final outputs' if full else 'Fewer than 48 complete case triplets'})
out={'selection':'48 cases in each of three repetitions, each whole path at least95% valid final outputs pooled over144 observations','selected':selected,'n':len(selected),'complete_count':len(complete),'summary':summary(selected),'sensitivity':sensitivity,'repeat_same_cohort':rep,'sign_changes':sum(len(set(v))>1 for v in signs.values()),'manifest':manifest,'rows':{m:outrows[m] for m in selected},'new_model_calls':0,'rescoring':0,'bootstrap_runs':0,'interval_rule':'Only saved intervals with exact configuration, contrast, outcome, observation count and matching effect; unavailable otherwise.'}
for src in ['COHORT_RESULTS.json','model_comparisons.csv']:
 f=P/src; dest=P/('first_repeat_superseded_'+src)
 if f.exists() and not dest.exists():dest.write_bytes(f.read_bytes())
(P/'COHORT_RESULTS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
with (P/'model_comparisons.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=flat[0]);w.writeheader();w.writerows(flat)
plan={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'supersedes':'COHORT_PLAN.json first-repeat selection','authorization':'User: 3회차까지 된것들만 추려서 사용하자','selection':out['selection'],'invalid_limit_per_path':7,'posthoc':True,'selection_uses_semantic_scores':False,'retain_residual_invalid_observations':True,'independent_unit':'case; repetitions clustered within case','new_model_calls':0,'rescoring':0,'new_bootstrap':0,'input_hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [D/'all_saved_scores_with_provenance.csv',D/'coverage.csv',D/'repeat_stability.csv',A/'saved_intervals_by_cohort.csv']}}
(P/'THREE_REPEAT_AMENDMENT.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
print(json.dumps({k:out[k] for k in ['n','complete_count','summary','repeat_same_cohort','sign_changes']},ensure_ascii=False))
for m in selected:
 print(labels[m]['label'],[(k,outrows[m][k]['before_count'],outrows[m][k]['after_count'],bool(outrows[m][k]['interval_source'])) for k in metrics[:3]])
