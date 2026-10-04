"""Explicit English restaurant domain adapter; frozen gate/executor algorithms unchanged."""
from pathlib import Path
import sys,json,copy,hashlib,tempfile
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent))
import support as base
protocol,policy,store=base.protocol,base.policy,base.store
OLDREL=list(protocol.RELATIONS); OLDSLOTS=list(protocol.SLOTS)
REL=['food','area','pricerange']
SLOTS=REL+[v for v in OLDSLOTS if v not in OLDREL]
def domain_schema(x):
 if isinstance(x,list):return [domain_schema(v) for v in x]
 if isinstance(x,dict):
  return {k:(REL if v==OLDREL else SLOTS if v==OLDSLOTS else domain_schema(v)) if k=='enum' else domain_schema(v) for k,v in x.items()}
 return x
protocol.RELATIONS=tuple(REL);protocol.SLOTS=tuple(SLOTS)
SCHEMAS={s:domain_schema(base.schema_for_stage(s)) for s in ('candidate_extract','candidate_final')}
COMMON='''You process an English spoken restaurant-search dialogue. Track only the user's current desired food, area, and pricerange. subject is p1; time is present. Values use lowercase ontology wording; no-preference is dontcare. These are user search preferences, not facts about a restaurant. Existing DB is the verified prior-turn goal, before the CURRENT user utterance. It can legitimately change. Current input candidates are original ranked ASR alternatives of ONE utterance, not successive turns. Their disagreement is uncertainty, not permission to combine incompatible preferences. Do not invent missing speech. Use preceding system context to resolve references. Source t1 denotes prior context/state and t2 the current utterance. Permission allowed is a task-tracking fixture, not measured user consent. No external tools. Operations: APPEND new slot, CORRECT an existing fact_id, HOLD an uncertain write, NO_WRITE for no proposed write. Separate next conversation action (CONTINUE/CLARIFY/SKIP/STOP) from memory writes. JSON only.'''
EXTRACT='''For every candidate_id produce exactly one belief. Put atomic facts supported by that candidate in its facts using the fact schema. Do not force uncertain values into shared facts. For each existing fact_id and each candidate_id produce one correction_witness. If that reading explicitly revises the old preference to a new value use affirmed; if it negates the new value use negated; if ambiguous uncertain; if there is no revision evidence absent. An affirmed witness preserves old subject/relation/time. evidence_quote must be an exact contiguous substring of that candidate and contain new_value. source_turn is t2. For absent use the old value and empty quote. For uncertain/negated without a quotable new value also use old value and empty quote. Witness polarity is your fallible proposal, not a supplied correct answer. Do not decide storage or generate a user reply in this stage.'''
FINAL='''The earlier extraction and witnesses may be wrong. Review every original ASR alternative, preceding dialogue and old DB to propose one final reply, action and memory_decisions. If a user preference change is sufficiently clear, CORRECT the existing target fact_id. APPEND only a newly specified slot. A bare denial need not supply a replacement value. Do not say storage succeeded before execution. Later deterministic gates separately process this proposal. Do not copy the entire prior state as new writes.'''
def messages(stage,pk,ext=None):
 body={'input':protocol._public_packet(pk)}
 if ext is not None:body['fallible_extraction']=ext
 instr=EXTRACT if stage=='candidate_extract' else FINAL
 return [{'role':'system','content':COMMON+'\n'+instr+'\nJSON schema:\n'+json.dumps(SCHEMAS[stage],sort_keys=True)}, {'role':'user','content':json.dumps(body,sort_keys=True)}]
def parse(stage,text,pk):
 if stage=='candidate_extract':
  ext=policy.parse_extraction(text,pk);protocol.validate_beliefs({'beliefs':ext['beliefs']},pk);return ext
 return protocol.validate_final(protocol.parse(text,'final'),pk)
def gated(name,pk,ext,q):
 g,a=protocol.apply_gate(q,{'beliefs':ext['beliefs']},pk)
 if name=='ALLOW':
  for i in base.policies.literal.h_indices({'gate_audit':a}):
   g['memory_decisions'][i]=copy.deepcopy(q['memory_decisions'][i]);a[i].update(after_operation='CORRECT',reason='ALLOW_CORRECTION_EXCEPTION')
 elif name=='LITERAL':g,a,_=base.policies.literal.apply_text(pk,ext,q,policy)
 elif name=='WITNESS':g,a=policy._gated_final(pk,ext,q,'C')
 elif name!='AGREE':raise ValueError(name)
 return g,a
def execute(pk,q):
 with tempfile.TemporaryDirectory() as tmp:
  db=Path(tmp)/'state.sqlite';return store.execute(db,q,pk)
def evaluate(pk,after,gold):
 target={(s,gold[s]) for s in REL if s in gold}
 got={(f['relation'],f['value']) for f in after['facts'] if f['subject']=='p1' and f['time']=='present'}
 before={(f['relation'],f['value']) for f in pk['db_snapshot']['facts']}
 required=target-before;new=got-before
 return {'joint_goal_correct':got==target,'new_wrong_write_count':len(new-target),'has_new_wrong_write':bool(new-target),'required_change_count':len(required),'correct_change_count':len(new&required),'all_required_changes_completed':bool(required) and required<=got,'preserved_valid_prior_count':len(before&target&got),'valid_prior_count':len(before&target),'after_goal':sorted(got),'missing_target':sorted(target-got),'extra_target':sorted(got-target)}
sha=base.sha;save=base.save;load=base.load
