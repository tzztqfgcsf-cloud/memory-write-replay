"""Portable saved-state scoring checks, standard library only; no API or collectors."""
import copy,csv,gzip,hashlib,importlib.util,json,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text())
def jsonl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def compare(actual,saved,keys):
 assert len(actual)==len(saved),(len(actual),len(saved))
 old={tuple(str(x[k]) for k in keys):x for x in saved}
 errors=[]
 for a in actual:
  b=old[tuple(str(a[k]) for k in keys)]
  for k,v in a.items():
   if k in b and str(v)!=str(b[k]):errors.append((tuple(a[x] for x in keys),k))
 assert not errors,errors[:12]

def verify_allow():
    core=load('portable_core_replay',ROOT.parent/'core/replay.py')
    episodes=core.read_gzip('episodes.json.gz');cases=core.read_gzip('cases.json.gz');raw=core.read_gzip('raw_responses.json.gz')
    keyed={(e['model_alias'],e['case_id'],e['repeat']):e for e in episodes}
    d=ROOT/'saved_allow';pr=read(d/'PROVENANCE.json')
    assert hashlib.sha256((d/'outputs.jsonl').read_bytes()).hexdigest()==pr['output_sha256']
    assert hashlib.sha256((d/'scores.csv').read_bytes()).hexdigest()==pr['scores_sha256']
    expected=list(csv.DictReader((d/'scores.csv').open()));actual=[]
    with tempfile.TemporaryDirectory(prefix='tist_allow_replay_') as td:
      for i,old in enumerate(jsonl(d/'outputs.jsonl')):
        e=keyed[(old['model_alias'],old['case_id'],old['repeat'])]
        public=cases['public_rows'][e['public_row_id']];ref=cases['references'][e['reference_id']]
        pk=core.packet(public);f,ferr=core.extraction(e,pk,raw)
        assert old['final_proposal']==e['outputs']['B']['final_proposal']
        valid=bool(f is not None and e['outputs']['B']['generation_valid'])
        assert valid==old['generation_valid']
        o=copy.deepcopy(old);db=Path(td)/str(i);initial=core.policies.original.store.init_db(db,pk['db_snapshot'])
        o.update(final_snapshot=initial,receipt=None,gate_audit=[])
        if valid:
          g,a=core.allow.apply_exception(pk,f,o['final_proposal'])
          receipt=core.policies.original.store.execute(db,g,pk)
          o.update(final_snapshot=receipt['after'],receipt=receipt,gated_proposal=g,gate_audit=a)
        scored=core.evaluate.score_output(o,public,ref)
        actual.append(scored)
    compare(actual,expected,['model_alias','case_id','repeat','condition'])
    return {'saved_rows_verified':len(actual),'models':8,'cases':48,'repetitions':3,'method':'fresh Allow admission + isolated SQLite execution + frozen v2 scoring, compared with archived E scores','new_model_calls':0}

def main():
 mf=read(ROOT/'TRANSFORM_MANIFEST.json')
 for x in mf['files']:
  assert hashlib.sha256((ROOT/x['destination']).read_bytes()).hexdigest()==x['published_sha256'],x['destination']
 summary={}
 for name in ['contrast24','boundary12']:
  d=ROOT/name;ev=load(name+'_frozen',d/'runtime/analyze.py')
  public={x['case_id']:x for x in read(d/'data/public.json')['cases']}
  refs={x['case_id']:x for x in read(d/'data/reference.json')['cases']}
  rows=jsonl(d/'collection/outputs.jsonl');saved=list(csv.DictReader((d/'analysis/scores.csv').open()))
  actual=[ev.score(x,public[x['case_id']],refs[x['case_id']]) for x in rows]
  compare(actual,saved,['case_id','condition'])
  counts={c:{'outputs':sum(x['condition']==c for x in actual),'supported_success':sum(x['recovered'] for x in actual if x['condition']==c),'unsupported_preserved':sum(x['safe_preservation'] for x in actual if x['condition']==c)} for c in sorted({x['condition'] for x in rows})}
  summary[name]={'cases':len(public),'saved_rows_verified':len(rows),'condition_counts':counts}
 # Original primary: frozen score function, preserved invalid/provider-failure rows.
 d=ROOT/'primary_original';ev=load('primary_frozen',d/'frozen/evaluate.py')
 public={x['case_id']:x for x in read(d/'data/public.json')['packets']};refs={x['case_id']:x for x in read(d/'data/reference.json')['references']}
 rows=sum((jsonl(d/'collection'/a/'outputs.jsonl') for a in ['gemini_flash','llama31_8b']),[])
 actual=[ev.score_output(x,public[x['case_id']],refs[x['case_id']]) for x in rows]
 saved=list(csv.DictReader((d/'analysis/scores.csv').open()));compare(actual,saved,['model_alias','case_id','repeat','condition'])
 summary['primary_original']={'cases':48,'repetitions':3,'models':2,'saved_rows_verified':len(actual),'invalid_rows':sum(x['invalid_final'] for x in actual),'failure_rows':sum(x['provider_failure'] for x in actual)}
 # Public focal-state agreement: exact original loop and normalization (not main score).
 d=ROOT/'public16';ev=load('transfer_frozen',d/'frozen/analyze.py')
 refs={x['case_id']:x for x in read(d/'data/provisional_reference.json')['references']};pub={x['case_id']:x for x in read(d/'data/public_packets.json')['packets']}
 rows=jsonl(d/'collection/outputs.jsonl');saved=read(d/'analysis/provisional_result.json')['rows'];actual=[]
 for row in rows:
  ref=refs[row['case_id']];p=pub[row['case_id']];eligible=ref['category_source_reader_provisional_not_gold']=='same_task_self_repair';focal=[]
  if eligible:
   for expected in ref['after_dataset_state_hidden_from_model']:
    relation=expected['relation'];before=next(x for x in p['before_dataset_state'] if x['relation']==relation)
    after=[x for x in row['final_snapshot']['facts'] if x['subject']==before['subject'] and x['relation']==relation]
    focal.append(len(after)==1 and ev.norm(after[0]['value'])==ev.norm(expected['after_dataset_annotation']))
  actual.append({'model_alias':row['model_alias'],'case_id':row['case_id'],'condition':row['condition'],'generation_valid':row['generation_valid'],'automatic_correctness_eligible':eligible,'provisional_native_focal_agreement':all(focal) if eligible and focal else None})
 compare(actual,saved,['model_alias','case_id','condition'])
 summary['public16']={'cases':16,'scored_cases':10,'unscored_cases':6,'saved_rows_verified':len(rows),'focal_agreement':{c:sum(x['provisional_native_focal_agreement'] is True for x in actual if x['condition']==c) for c in sorted({x['condition'] for x in actual})},'human_gold':False}
 summary['saved_allow']=verify_allow()
 summary.update(status='PASS',manifest_files_verified=len(mf['files']),new_model_calls=0,original_files_modified=0,bootstrap_runs=0,timing_artifact_recovered=False)
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
