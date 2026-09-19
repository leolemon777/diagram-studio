#!/usr/bin/env python3
"""Bundle the bounded MLP explorer as a standalone HTML; no remote runtime."""
import argparse, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--out',type=Path,required=True)
 p.add_argument('--model',type=Path,help='Explicit 8-14-10-3 model JSON, no hidden topology truncation')
 p.add_argument('--seed',type=int,default=42)
 p.add_argument('--node',default='node')
 a=p.parse_args()
 library=ROOT/'assets/network-model.js'
 js="const m=require(process.argv[1]);const fs=require('fs');const model=process.argv[2]?JSON.parse(fs.readFileSync(process.argv[2],'utf8')):m.create(Number(process.argv[3]));m.validate(model);process.stdout.write(JSON.stringify({model,result:m.forward(model)}));"
 run=subprocess.run([a.node,'-e',js,str(library),str(a.model.resolve()) if a.model else '',str(a.seed)],check=True,text=True,capture_output=True)
 payload=json.loads(run.stdout)
 html=(ROOT/'assets/network-explorer.html').read_text().replace('/*__MODEL_LIBRARY__*/',library.read_text()).replace('__MODEL_DATA__',json.dumps(payload['model'],ensure_ascii=False).replace('<','\\u003c'))
 a.out.mkdir(parents=True,exist_ok=True)
 (a.out/'index.html').write_text(html)
 (a.out/'model.json').write_text(json.dumps(payload['model'],indent=2))
 (a.out/'forward.json').write_text(json.dumps(payload['result'],indent=2))
 print(json.dumps({'out':str(a.out),'nodes':35,'edges':282,'parameters':309,'probabilities':payload['result']['a'][-1]}))

if __name__=='__main__':main()
