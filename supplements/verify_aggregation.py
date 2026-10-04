"""Verify released hashes and recompute aggregates of FROZEN scores. No inference/rescoring."""
from pathlib import Path
import json,csv,collections,random,math,hashlib
R=Path(__file__).resolve().parent
METRICS=['generation_valid','correction_recovery','positive_joint','harmful_write','whole_state_compliance']
def load(p):return json.loads(p.read_text())
def rows(p):
 with p.open() as f:return [{k:True if v=='True' else False if v=='False' else v for k,v in r.items()} for r in csv.DictReader(f)]
def eq(a,b):
 if isinstance(a,dict):assert set(a)==set(b),(set(a)^set(b));[eq(a[k],b[k]) for k in a]
 elif isinstance(a,list):assert len(a)==len(b);[eq(x,y) for x,y in zip(a,b)]
 elif isinstance(a,float):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10),(a,b)
 else:assert a==b,(a,b)
def authored():
 baseline=rows(R/'authored/baseline_scores.csv');scored=0;attempted=0
 for d in sorted((R/'authored').glob('paper_*')):
  scores=rows(d/'new_scores.csv');summary=load(d/'SUMMARY.json');scored+=len(scores);attempted+=len(list((d/'responses').glob('*.json')))
  assert len(scores)==summary['new_scored_rows']
  groups=collections.defaultdict(list)
  for s in scores+baseline:groups[(s['model_alias'],s['condition'])].append(s)
  totals={key:{'n':len(ss),'positive_eligible':sum(s['positive_eligible'] for s in ss),'correction_eligible':sum(s['correction_eligible'] for s in ss),**{m:sum(s[m] for s in ss) for m in METRICS}} for key,ss in groups.items()}
  assert len(totals)==len(summary['totals'])
  for t in summary['totals']:eq(totals[(t['model'],t['condition'])],{k:v for k,v in t.items() if k not in ['model','condition']})
  for p in summary['paired']:
   a={s['case_id']:s for s in groups[(p['model'],p['before'])]};b={s['case_id']:s for s in groups[(p['model'],p['after'])]};m=p['metric'];ids=sorted(set(a)&set(b))
   eligible='correction_eligible' if m=='correction_recovery' else 'positive_eligible' if m=='positive_joint' else None
   if eligible:ids=[i for i in ids if a[i][eligible]]
   diff=[int(b[i][m])-int(a[i][m]) for i in ids];rng=random.Random(20261004)
   vals=sorted(sum(rng.choices(diff,k=len(diff)))/len(diff)*100 for _ in range(5000))
   eq({'cases':len(ids),'difference_count':sum(diff),'difference_pp':sum(diff)/len(diff)*100,'ci95_pp':[vals[124],vals[4874]]},{k:p[k] for k in ['cases','difference_count','difference_pp','ci95_pp']})
  responses=[load(p) for p in sorted((d/'responses').glob('*.json'))];usage=collections.defaultdict(lambda:{'calls':0,'input_tokens':0,'output_tokens':0,'reasoning_tokens':0,'latency_sum':0.})
  for s in responses:
   u=usage[s['requested_model']];u['calls']+=1;u['latency_sum']+=s['latency_seconds']
   for k in ['input_tokens','output_tokens','reasoning_tokens']:u[k]+=s.get('usage',{}).get(k) or 0
  for u in usage.values():u['latency_mean']=u['latency_sum']/u['calls']
  eq(dict(usage),summary['usage'])
 focal=load(R/'authored/focal5_provenance.json');fcounts={'original_success':0,'corrected_success':0,'original_holds':0,'corrected_holds':0,'harm_original':0,'harm_corrected':0}
 for p in focal['pairs']:
  score=rows(R/'authored'/p['scores'])[p['score_csv_line_1based']-2];assert score['case_id']==p['case_id'];assert int(score['repeat'])==p['selected_repeat'];assert score['condition']=='extract_'+p['arm']
  response=load(R/'authored'/p['response']);assert response['status']=='OK'
  output=json.loads((R/'authored'/p['output']).read_text().splitlines()[p['output_line_1based']-1]);assert output['case_id']==p['case_id']
  fcounts[p['arm']+'_success']+=score['correction_recovery'];fcounts['harm_'+p['arm']]+=score['harmful_write'];fcounts[p['arm']+'_holds']+=sum(x['before_operation']=='CORRECT' and x['after_operation']=='HOLD' for x in output['gate_audit'])
 eq(fcounts,{k:focal['summary'][k] for k in fcounts})
 return {'authored_new_scored_rows':scored,'authored_attempts':attempted,'focal_cases':len(focal['pairs'])//2,**fcounts}
def dstc2():
 records=load(R/'dstc2/scored_cases_flags.json');expected=load(R/'dstc2/RESULTS.json');names=['RAW','AGREE','ALLOW','LITERAL','WITNESS']
 for model,strata in expected['models'].items():
  for stratum,g in strata.items():
   rr=[r for r in records if r['model']==model and (stratum=='all' or r['stratum']==stratum)]
   assert len(rr)==g['completed'];assert len({r['caller_cluster'] for r in rr})==g['callers']
   for n in names:
    vals=[r['policies'][n] for r in rr]
    eq({'joint_goal_correct':sum(v['joint_goal_correct'] for v in vals),'turns_with_new_wrong_write':sum(v['has_new_wrong_write'] for v in vals),'new_wrong_writes':sum(v['new_wrong_write_count'] for v in vals),'required_changes':sum(v['required_change_count'] for v in vals),'correct_changes':sum(v['correct_change_count'] for v in vals),'all_required_changes_completed':sum(v['all_required_changes_completed'] for v in vals),'turns_requiring_change':sum(v['required_change_count']>0 for v in vals)},g['policies'][n])
 def ci(rr,a,b,metric):
  if not rr:return None
  clusters=collections.defaultdict(list)
  for r in rr:clusters[r['caller_cluster']].append(float(r['policies'][b][metric])-float(r['policies'][a][metric]))
  vals=list(clusters.values());rng=random.Random(20261004);samples=[]
  for _ in range(5000):
   selected=[vals[rng.randrange(len(vals))] for _ in vals];flat=[v for vv in selected for v in vv];samples.append(100*sum(flat)/len(flat))
  samples.sort();return {'difference_pp':100*sum(v for vs in vals for v in vs)/len(rr),'caller_cluster_95CI_pp':[samples[124],samples[4874]],'n_cases':len(rr),'n_callers':len(vals),'replicates':5000}
 for p in load(R/'dstc2/PAIRED_INTERVALS.json'):
  rr=[r for r in records if r['model']==p['model'] and (p['stratum']=='all' or r['stratum']==p['stratum'])];a,b=p['from'],p['to']
  eq(ci(rr,a,b,'joint_goal_correct'),p['joint_goal']);eq(ci(rr,a,b,'has_new_wrong_write'),p['wrong_write_turns']);eq(ci([r for r in rr if r['policies'][a]['required_change_count']>0],a,b,'all_required_changes_completed'),p['required_change_completion'])
 return {'dstc2_valid_pairs':len(records),'dstc2_flash_valid_pairs':expected['models']['gemini-3.8-flash']['all']['completed'],'dstc2_pro_valid_pairs':expected['models']['gemini-3.1-pro-preview']['all']['completed']}
def main():
 for p in load(R/'EXPORT_PROVENANCE.json'):
  assert hashlib.sha256((R/p['exported_path']).read_bytes()).hexdigest()==p['exported_sha256'],p['exported_path']
 observed={**authored(),**dstc2(),'model_calls':0,'frozen_scores_rescored':0}
 eq(observed,load(R/'expected_metrics.json'));print(json.dumps({'status':'PASS',**observed},indent=2))
if __name__=='__main__':main()
