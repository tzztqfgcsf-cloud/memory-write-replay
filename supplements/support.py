"""Portable imports for post-v20 supplements. Standard library only."""
from pathlib import Path
import sys,json,hashlib,copy
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'core/runtime'))
import policies
policy=policies.original
protocol,store=policy.protocol,policy.store
_SCHEMAS=json.loads(Path(__file__).with_name('schemas.json').read_text())
def schema_for_stage(stage):
 return copy.deepcopy(_SCHEMAS['extraction' if stage=='candidate_extract' else 'final'])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2)
