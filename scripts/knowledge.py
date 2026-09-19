#!/usr/bin/env python3
"""Search complete type rules, compare choices, and compile a scoped prompt."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load():return json.loads((ROOT/'assets/knowledge.json').read_text(encoding='utf-8'))
def search(data,query='',family=None,group=None):
    terms=query.casefold().split();found=[]
    for row in data['types']:
        if family and row['family']!=family:continue
        if group and row['group']!=group:continue
        title=(row['name']+' '+row['id']).casefold()
        text=' '.join([row['name'],row['id'],row['group'],row['family'],row['inputs'],row['rule'],' '.join(row['variants']),' '.join(row.get('aliases',[]))]).casefold()
        if terms and not all(q in text for q in terms):continue
        score=sum(20*(q==row['name'].casefold() or q==row['id'].casefold())+5*(q in title)+2*(q in row['group'].casefold()) for q in terms)
        found.append((score,row))
    return [r for _,r in sorted(found,key=lambda x:-x[0])]
def get_card(data,id):
    matches=[r for r in data['types'] if r['id']==id or str(r.get('official_id',''))==id]
    if len(matches)!=1:raise ValueError('unknown type id: '+id)
    row=dict(matches[0]);sources={s['id']:s for s in data['sources']}
    row['source_details']=[sources[s] for s in row['sources']]
    row['example_paths']=[str(ROOT/'assets/examples'/(s+'.json')) for s in row['examples']]
    row['advanced_example_paths']=[str(ROOT/'assets/advanced-examples'/(s+'.json')) for s in row.get('advanced_examples',[])]
    row['scientific_example_paths']=[str(ROOT/'assets/scientific-examples'/(s+'.json')) for s in row.get('scientific_examples',[])]
    row['energy_example_paths']=[str(ROOT/'assets/energy-examples'/(s+'.json')) for s in row.get('energy_examples',[])]
    row['operations_example_paths']=[str(ROOT/'assets/operations-examples'/(s+'.json')) for s in row.get('operations_examples',[])]
    row['data_art_example_paths']=[str(ROOT/'assets/data-art-examples'/(s+'.json')) for s in row.get('data_art_examples',[])]
    row['fault_tree_example_paths']=[str(ROOT/'assets/fault-tree-examples'/(s+'.json')) for s in row.get('fault_tree_examples',[])]
    row['kanban_example_paths']=[str(ROOT/'assets/kanban-models'/(s+'.json')) for s in row.get('kanban_models',[])]
    row['deployment_example_paths']=[str(ROOT/'assets/deployment-models'/(s+'.json')) for s in row.get('deployment_models',[])]
    row['activity_example_paths']=[str(ROOT/'assets/activity-models'/(s+'.json')) for s in row.get('activity_models',[])]
    row['component_example_paths']=[str(ROOT/'assets/component-models'/(s+'.json')) for s in row.get('component_models',[])]
    row['usecase_example_paths']=[str(ROOT/'assets/usecase-models'/(s+'.json')) for s in row.get('usecase_models',[])]
    row['object_example_paths']=[str(ROOT/'assets/object-models'/(s+'.json')) for s in row.get('object_models',[])]
    row['structured_example_paths']=[str(ROOT/'assets/structured-models'/(s+'.json')) for s in row.get('structured_models',[])]
    row['ctud_example_paths']=[str(ROOT/'assets/ctud-models'/(s+'.json')) for s in row.get('ctud_models',[])]
    row['pert_example_paths']=[str(ROOT/'assets/pert-models'/(s+'.json')) for s in row.get('pert_models',[])]
    row['pid_example_paths']=[str(ROOT/'assets/pid-models'/(s+'.json')) for s in row.get('pid_models',[])]
    row['pid_layout_paths']=[str(ROOT/'assets/pid-models'/(s+'.layout.json')) for s in row.get('pid_models',[])]
    row['relational_example_paths']=[str(ROOT/'assets/relational-models'/(s+'.json')) for s in row.get('relational_models',[])]
    row['management_example_paths']=[str(ROOT/'assets/management-models'/(s+'.json')) for s in row.get('management_models',[])]
    row['governed_flow_example_paths']=[str(ROOT/'assets/governed-flow-models'/(s+'.json')) for s in row.get('governed_flow_models',[])]
    row['planning_report_example_paths']=[str(ROOT/'assets/planning-report-models'/(s+'.json')) for s in row.get('planning_report_models',[])]
    row['strategy_analysis_example_paths']=[str(ROOT/'assets/strategy-analysis-models'/(s+'.json')) for s in row.get('strategy_analysis_models',[])]
    row['organization_relation_example_paths']=[str(ROOT/'assets/organization-relation-models'/(s+'.json')) for s in row.get('organization_relation_models',[])]
    row['architecture_model_paths']=[str(ROOT/'assets/architecture-models'/(s+'.json')) for s in row.get('architecture_models',[])]
    row['software_infrastructure_model_paths']=[str(ROOT/'assets/software-infrastructure-models'/(s+'.json')) for s in row.get('software_infrastructure_models',[])]
    row['facilities_engineering_model_paths']=[str(ROOT/'assets/facilities-engineering-models'/(s+'.json')) for s in row.get('facilities_engineering_models',[])]
    row['remaining_type_model_paths']=[str(ROOT/'assets/remaining-type-models'/(s+'.json')) for s in row.get('remaining_type_models',[])]
    row['cross_industry_model_paths']=[str(ROOT/'assets/cross-industry-models'/(s+'.json')) for s in row.get('cross_industry_models',[])]
    row['ladder_example_paths']=[str(ROOT/'assets/ladder-examples'/(s+'.json')) for s in row.get('ladder_examples',[])]
    row['event_tree_example_paths']=[str(ROOT/'assets/event-tree-examples'/(s+'.json')) for s in row.get('event_tree_examples',[])]
    row['qfd_example_paths']=[str(ROOT/'assets/qfd-examples'/(s+'.json')) for s in row.get('qfd_examples',[])]
    row['house_quality_example_paths']=[str(ROOT/'assets/house-quality-examples'/(s+'.json')) for s in row.get('house_quality_examples',[])]
    row['spc_example_paths']=[str(ROOT/'assets/spc-examples'/(s+'.json')) for s in row.get('spc_examples',[])]
    return row
def compile_prompt(card,request):return card['prompt'].replace('{需求}',request)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('query',nargs='*');p.add_argument('--family');p.add_argument('--group');p.add_argument('--card');p.add_argument('--prompt');p.add_argument('--list',action='store_true');p.add_argument('--limit',type=int,default=12);args=p.parse_args();d=load()
    if args.prompt and not args.card:p.error('--prompt requires --card')
    if args.card:
        try:r=get_card(d,args.card)
        except ValueError as e:p.error(str(e))
        print(compile_prompt(r,args.prompt) if args.prompt else json.dumps(r,ensure_ascii=False,indent=2));return
    rows=search(d,' '.join(args.query),args.family,args.group)
    if args.list:
        print(json.dumps({'scope':d['scope'],'count':len(rows),'types':[{k:r[k] for k in ('id','name','family','group','validation')} for r in rows]},ensure_ascii=False,indent=2))
    else:print(json.dumps([{k:r[k] for k in ('id','name','group','decision','validation','examples')} for r in rows[:max(0,args.limit)]],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
