"""UML instance snapshot input; structural validation, not metamodel conformance."""
import argparse,json,re,math
from pathlib import Path

def validate(d):
 def fields(x,required):
  if not isinstance(x,dict) or set(x)!=set(required):raise ValueError('invalid fields: '+str(required))
 def text(x,empty=False):
  if not isinstance(x,str) or (not empty and not x.strip()):raise ValueError('nonempty text required')
 fields(d,('title','snapshot','assumptions','objects','links'));text(d['title']);text(d['snapshot'])
 if not isinstance(d['assumptions'],list) or not d['assumptions']:raise ValueError('assumptions required')
 for a in d['assumptions']:text(a)
 if not isinstance(d['objects'],list) or not d['objects']:raise ValueError('objects required')
 if not isinstance(d['links'],list):raise ValueError('links must be list')
 ids=set();refs=[];rows=[]
 def ident(i):
  if not isinstance(i,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,63}',i) or i in ids:raise ValueError('unique ASCII id required')
  ids.add(i)
 for o in d['objects']:
  fields(o,('id','name','classifiers','slots'));ident(o['id']);text(o['name'],True)
  if not isinstance(o['classifiers'],list):raise ValueError('classifiers must be list')
  for c in o['classifiers']:text(c)
  if len(set(o['classifiers']))!=len(o['classifiers']):raise ValueError('duplicate classifier')
  if not o['name'].strip() and not o['classifiers']:raise ValueError('anonymous instance needs classifier')
  if not isinstance(o['slots'],list):raise ValueError('slots must be list')
  features=set()
  for slot in o['slots']:
   fields(slot,('feature','values'));text(slot['feature'])
   if slot['feature'] in features:raise ValueError('duplicate slot feature')
   features.add(slot['feature'])
   if not isinstance(slot['values'],list):raise ValueError('slot values must be list')
   for v in slot['values']:
    if not isinstance(v,dict):raise ValueError('tagged slot value required')
    kind=v.get('kind')
    if kind=='literal':
     fields(v,('kind','value'));value=v['value']
     if value is not None and not isinstance(value,(str,bool,int,float)):raise ValueError('scalar literal required')
     if isinstance(value,float) and not math.isfinite(value):raise ValueError('finite number required')
    elif kind=='reference':fields(v,('kind','object'));refs.append(v['object'])
    else:raise ValueError('unsupported slot value')
  rows.append(dict(id=o['id'],heading=o['name']+(' : '+', '.join(o['classifiers'])),slots=len(o['slots'])))
 object_ids=set(ids)
 for ref in refs:
  if not isinstance(ref,str) or ref not in object_ids:raise ValueError('unknown referenced instance')
 for link in d['links']:
  fields(link,('id','association','ends'));ident(link['id']);text(link['association'],True)
  if not isinstance(link['ends'],list) or len(link['ends'])!=2:raise ValueError('current link schema requires two ends')
  for end in link['ends']:
   fields(end,('role','object'));text(end['role'],True)
   if not isinstance(end['object'],str) or end['object'] not in object_ids:raise ValueError('unknown link endpoint')
 return dict(snapshot=d['snapshot'],objects=rows,links=len(d['links']),references=len(refs),scope='instance identity, slot structure and reference integrity; classifier features, value types and multiplicities not checked')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);a=p.parse_args();d=json.loads(Path(a.input).read_text());result=validate(d);dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True);(dest/(Path(a.input).stem+'.validation.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
