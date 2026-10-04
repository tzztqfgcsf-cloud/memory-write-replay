"""Replay saved authored raw text through unchanged gate and SQLite executor. No APIs/scoring."""
from pathlib import Path
import argparse,json,tempfile
import support
from authored import methods
methods.protocol=support.protocol
R=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output-dir',type=Path,required=True);args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=False)
 comparisons=[]
 for d in sorted((R/'authored').glob('paper_*')):
  data=support.load(d/'public_inputs.json');saved=[json.loads(s) for s in (d/'new_outputs.jsonl').read_text().splitlines()];jobs={j['id']:j for j in support.load(d/'queue.json')}
  for old in saved:
   call=old['upstream_call_ids'][0];job=jobs[call];response=support.load(d/'responses'/f'{call}.json');x=data[job['key']];pk=x['packet'];q=x['candidate' if job['stage']=='extract' else 'review']['final_proposal'];valid=q is not None;g=None;a=[];errors=[]
   try:
    if job['stage']=='extract':
     ext=support.policy.parse_extraction(response['text'],pk);support.protocol.validate_beliefs({'beliefs':ext['beliefs']},pk)
     if valid:g,a=support.policy._gated_final(pk,ext,q,'B')
    elif valid:g,a=methods.judge_gate(q,response['text']);support.protocol.validate_final(g,pk)
   except (ValueError,KeyError,TypeError,AssertionError) as ex:valid=False;errors.append('PARSE_'+str(getattr(ex,'code',type(ex).__name__)))
   with tempfile.TemporaryDirectory() as tmp:
    db=Path(tmp)/'state.sqlite';after=support.store.init_db(db,pk['db_snapshot']);receipt=None
    if valid:receipt=support.store.execute(db,g,pk);after=receipt['after']
   assert valid==old['generation_valid'],(d.name,call,'validity')
   assert errors==old['parse_errors'],(d.name,call,'parse errors')
   assert after==old['final_snapshot'],(d.name,call,'snapshot')
   assert a==old['gate_audit'],(d.name,call,'audit')
   if valid:assert g==old['gated_proposal'],(d.name,call,'gated proposal')
   comparisons.append({'collection':d.name,'call':call,'generation_valid':valid,'snapshot_match':True,'gate_match':True})
 report={'status':'PASS','model_calls':0,'original_score_recomputation':False,'compared_saved_outputs':len(comparisons),'comparisons':comparisons}
 (args.output_dir/'replay_comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='comparisons'}))
if __name__=='__main__':main()
