"""Reconstruct private packets after obtaining DSTC2 separately. No network/API calls."""
from pathlib import Path
import argparse,json,hashlib

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--data-dir',type=Path,required=True,help='Directory containing Mar13_* directories from DSTC2 v1 test data');ap.add_argument('--output-dir',type=Path,required=True);args=ap.parse_args()
 manifest=load(Path(__file__).with_name('selected_manifest.json'))
 args.output_dir.mkdir(parents=True,exist_ok=False);packets=[];references=[];REL=['food','area','pricerange']
 for item in manifest['selected_cases']:
  d=args.data_dir/item['dataset_relative_dialogue_path'];lp=d/'log.json';gp=d/'label.json'
  assert sha(lp)==item['source_log_sha256'],lp
  assert sha(gp)==item['source_labels_sha256'],gp
  log=load(lp);lab=load(gp);idx=item['turn_index_zero_based'];turn=log['turns'][idx];label=lab['turns'][idx];prev=lab['turns'][idx-1]['goal-labels'] if idx else {}
  alternatives=[];ranks=[]
  for rank,h in enumerate(turn['input']['live']['asr-hyps'],1):
   t=h['asr-hyp']
   if t.strip() and t not in alternatives:alternatives.append(t);ranks.append(rank)
  assert ranks==item['selected_original_asr_ranks']
  facts=[{'fact_id':'prior_'+s,'subject':'p1','relation':s,'value':prev[s],'time':'present','source_turns':['t1']} for s in REL if s in prev]
  history=[]
  for old in log['turns'][:idx]:history += [{'role':'assistant','text':old['output']['transcript']},{'role':'user','text':old['input']['live']['asr-hyps'][0]['asr-hyp']}]
  history.append({'role':'assistant','text':turn['output']['transcript']})
  packets.append({'episode_id':item['episode_id'],'turn_id':'t2','speaker_id':'p1','memory_permission':'allowed','history':history,'alternatives':alternatives,'db_snapshot':{'facts':facts,'pending':[]}})
  references.append({'episode_id':item['episode_id'],'stratum':item['stratum'],'gold_goal':{s:v for s,v in label['goal-labels'].items() if s in REL},'human_transcription':label['transcription'],'human_checked_semantics':label['semantics']['json']})
 for name,obj in [('packets.json',packets),('references.json',references)]:
  (args.output_dir/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'packets':len(packets),'source_hashes_verified':len(packets)*2,'api_calls':0,'outputs_private':True}))
if __name__=='__main__':main()
