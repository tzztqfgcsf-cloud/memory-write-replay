"""Exact frozen Oct4 corrected-extractor instruction and judge gate; no API calls."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from support import protocol
FIX='''추출 위치를 명확히 한다: 해당 전사 대안이 명시적으로 확정한 정정 후의 원자 사실은 그 대안의 beliefs[].facts에도 반드시 기록한다. correction_witnesses에 정정 증거를 기록했다는 이유로 facts에서 그 사실을 빼지 않는다. 정정된 새값과 기존 주체·관계·시점을 사실 스키마에 맞춰 기록한다. 부정·불확실·다른 사람의 사실을 기존 인물의 확정 사실로 넣지 않는다. 한 대안에서만 지지되는 사실을 다른 대안의 facts로 복사하지 않는다. 원문에 없는 사실은 추가하지 않는다.'''
JUDGE='''당신은 개인 대화의 기억 쓰기를 검증한다. 입력의 각 APPEND/CORRECT 제안에 대해 모든 가능한 전사, 대화 문맥, 기존 기억, 저장 동의를 함께 보고 그 쓰기가 정당한지 판단한다. 전사 대안은 동일 발화의 가능한 해석이며 모두에서 근거가 있어야 한다. 표현만 다른 동등한 의미는 인정한다. 다른 사람의 정보, 시점 차이, 부정, 불확실, 인용과 실제 주장을 구분한다. CORRECT는 지정된 기존 기록의 실제 정정인지 확인한다. 명시 정정이 있으면 과거 값과 다르다는 이유만으로 거부하지 않는다. 저장 동의가 denied/unknown이면 승인하지 않는다. reference, 기존 정책 판정, 정답은 제공되지 않는다. 입력의 제안은 틀릴 수 있다. 쓰기 제안마다 index, approve(boolean), reason(짧은 한국어 이유)을 정확히 하나씩 반환한다. 쓰기가 없으면 decisions는 빈 배열이다. JSON만 출력한다.'''
JSCHEMA={'type':'object','properties':{'decisions':{'type':'array','items':{'type':'object','properties':{'index':{'type':'integer'},'approve':{'type':'boolean'},'reason':{'type':'string'}},'required':['index','approve','reason'],'additionalProperties':False}}},'required':['decisions'],'additionalProperties':False}
def judge_messages(pk,q):
 ds=[{'index':i,**d} for i,d in enumerate(q['memory_decisions']) if d['operation'] in ('APPEND','CORRECT')]
 return [{'role':'system','content':JUDGE},{'role':'user','content':json.dumps({'input':protocol._public_packet(pk),'proposed_writes':ds},ensure_ascii=False)}]
def judge_gate(q,raw):
 obj=json.loads(raw);ds=obj['decisions'];inds=[i for i,d in enumerate(q['memory_decisions']) if d['operation'] in ('APPEND','CORRECT')]
 assert len(ds)==len(inds) and {d['index'] for d in ds}==set(inds)
 assert all(type(d['index'])==int and type(d['approve'])==bool and isinstance(d['reason'],str) for d in ds)
 g=copy.deepcopy(q);audit=[]
 for d in ds:
  x=g['memory_decisions'][d['index']];before=x['operation']
  if not d['approve']:x.update(operation='HOLD',slot=x['fact']['relation'],fact=None,alternatives=[])
  audit.append({'decision_index':d['index'],'before_operation':before,'after_operation':x['operation'],'reason':d['reason']})
 return g,audit
