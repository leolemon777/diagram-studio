"""Explicit text projection for snapshot values; no inferred UML type checking."""
import json
from object_snapshot import validate

def notation(d):
 report=validate(d);objects={o['id']:o for o in d['objects']}
 def value(v):
  if v['kind']=='reference':
   o=objects[v['object']]
   # Internal identifier disambiguates anonymous instances; documented display convention.
   return o['name'] or '[anonymous id='+o['id']+']'
  return json.dumps(v['value'],ensure_ascii=False,allow_nan=False)
 return dict(snapshot=d['snapshot'],objects=[dict(id=o['id'],heading=report['objects'][i]['heading'],underline_heading=True,slots=[dict(feature=s['feature'],text=s['feature']+' = '+('{ }' if not s['values'] else ', '.join(value(v) for v in s['values']))) for s in o['slots']]) for i,o in enumerate(d['objects'])],links=d['links'],conventions=['Named references use the instance name; anonymous references use an explicit local identity annotation, not standardized UML notation','{ } denotes explicitly supplied zero values; omitted slots remain unspecified','null is an explicit JSON null literal, not a claim that the classifier permits null'])
