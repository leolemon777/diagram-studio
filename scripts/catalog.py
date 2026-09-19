#!/usr/bin/env python3
"""Find structural recipes without loading every example into context."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('query',nargs='*');p.add_argument('--family');p.add_argument('--limit',type=int,default=12);args=p.parse_args()
root=Path(__file__).resolve().parents[1];rows=json.loads((root/'assets/catalog.json').read_text());terms=[q.lower() for q in args.query]
for row in rows:row['score']=sum(5*int(q in row['name'].lower())+2*int(q in row['family'].lower())+int(q in (row['subtitle']+' '+row['id']+' '+row['type']).lower()) for q in terms)
rows=[r for r in rows if (not terms or r['score']>0) and (not args.family or args.family==r['family'])];rows.sort(key=lambda r:(-r['score'],r['id']))
print(json.dumps([{'name':r['name'],'family':r['family'],'use':r['subtitle'],'type':r['type'],'source':str(root/'assets/examples'/(r['id']+'.json'))} for r in rows[:args.limit]],ensure_ascii=False,indent=2))
