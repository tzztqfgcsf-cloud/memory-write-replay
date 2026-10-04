import csv,json
from pathlib import Path
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent
assert (R/'EXECUTION_COMPLETE.json').exists()
assert not (R/'ANALYSIS_COMPLETE.json').exists(),'Analysis already complete'
m=json.loads((R/'input_manifest.json').read_text())
old=pd.read_csv(m['integrated_scores_path']);old=old[old.model_alias.isin(m['selected_models']) & (old.split=='test')].copy()
new=pd.read_csv(R/'new_scores.csv');df=pd.concat([old,new],ignore_index=True)
keys=['model_alias','case_id','repeat'];assert not df.duplicated(keys+['condition']).any()
metrics={'positive_joint':'positive_eligible','correction_recovery':'correction_eligible','harmful_write':None,'invalid_final':None,'whole_state_compliance':None,'unsupported_write_claim':None}
contrasts=[('N_AGREE','B'),('N_LITERAL','EXACT_LITERAL'),('N_LITERAL','C'),('R_LITERAL','G'),('R_WITNESS','G'),('R_WITNESS','R_LITERAL')]
rows=[];pairs=[]
for a,b in contrasts:
 x=df[df.condition==a].set_index(keys);y=df[df.condition==b].set_index(keys);assert set(x.index)==set(y.index)
 for metric,elig in metrics.items():
  z=pd.DataFrame({'before':y[metric].astype(int),'after':x[metric].astype(int)})
  if elig:z=z[x[elig]]
  z['delta']=z.after-z.before;z['gain']=(z.after>z.before).astype(int);z['loss']=(z.after<z.before).astype(int)
  z=z.reset_index();z['contrast']=a+' vs '+b;z['metric']=metric;pairs.extend(z.to_dict('records'))
  for model in m['selected_models']+['ALL21']:
   v=z if model=='ALL21' else z[z.model_alias==model]
   # Repeat and configuration observations remain together in the case cluster.
   cd=v.groupby('case_id').delta.mean().to_numpy();rng=np.random.default_rng(20261001)
   bs=cd[rng.integers(0,len(cd),(5000,len(cd)))].mean(axis=1)*100;lo,hi=np.quantile(bs,[.025,.975])
   rows.append({'model_alias':model,'candidate':a,'baseline':b,'metric':metric,'cases':len(cd),'observations':len(v),'before':int(v.before.sum()),'after':int(v.after.sum()),'gains':int(v.gain.sum()),'losses':int(v.loss.sum()),'net':int(v.delta.sum()),'delta_pp':float(cd.mean()*100),'ci_low_pp':float(lo),'ci_high_pp':float(hi)})
s=pd.DataFrame(rows);s.to_csv(R/'paired_comparisons.csv',index=False);pd.DataFrame(pairs).to_csv(R/'paired_observations.csv',index=False)
counts=df.groupby(['model_alias','condition'])[list(metrics)+['positive_eligible','correction_eligible']].sum().reset_index();counts.to_csv(R/'condition_counts.csv',index=False)
# Changes in decisions explain normalization independently of correctness.
audit=[]
for line in (R/'outputs.jsonl').open():
 o=json.loads(line)
 for a in o['gate_audit']:
  if a.get('reason') in ['NORMALIZED_TUPLE_SUPPORT','NORMALIZED_LITERAL_EXCEPTION']:
   audit.append({k:o[k] for k in ['model_alias','case_id','repeat','condition']}|a)
(R/'normalization_changes.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
# Coverage-only sensitivity: both compared records valid, descriptive, no cohort reselection.
coverage=[]
for a,b in [('R_LITERAL','G'),('R_WITNESS','G')]:
 x=df[df.condition==a].set_index(keys);y=df[df.condition==b].set_index(keys);common=x.generation_valid & y.generation_valid
 for model in m['selected_models']+['ALL21']:
  keep=common if model=='ALL21' else common & (common.index.get_level_values('model_alias')==model)
  for metric in metrics:
   valid=keep & (x[metrics[metric]] if metrics[metric] else True)
   coverage.append({'model_alias':model,'candidate':a,'baseline':b,'metric':metric,'jointly_valid_observations':int(valid.sum()),'before':int(y.loc[valid,metric].sum()),'after':int(x.loc[valid,metric].sum())})
pd.DataFrame(coverage).to_csv(R/'joint_valid_sensitivity.csv',index=False)
summary=s[s.model_alias=='ALL21'].to_dict('records')
(R/'SUMMARY.json').write_text(json.dumps({'aggregated_case_cluster_comparisons':summary,'literal_fallback_admissions_under_normalized_policy':len(audit),'literal_fallback_admissions_note':'Includes exact-literal passes; not incremental normalization changes.','new_conditions':5,'inference_calls':0},ensure_ascii=False,indent=2))
(R/'ANALYSIS_COMPLETE.json').write_text(json.dumps({'status':'COMPLETE','new_rows_scored_once':15120,'old_scores_read_only':True,'bootstrap_draws':5000,'seed':20261001,'unit':'case, all repeats and model configurations jointly clustered for ALL21','model_calls':0,'conditions_fixed_before_outcomes':True,'inference':'exploratory pointwise intervals; selected fixed configurations, no population-of-models claim'},indent=2))
print(s[(s.model_alias=='ALL21') & s.metric.isin(['correction_recovery','harmful_write','positive_joint','invalid_final'])].to_string(index=False))
