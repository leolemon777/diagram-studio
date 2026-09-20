#!/usr/bin/env python3
"""Reproduce five common refined diagrams and meaningful content mutations."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import render

ROOT=Path(__file__).resolve().parents[1]


def mutations(models):
    changed=copy.deepcopy(models)
    d=changed['workflow']
    d['nodes'][2]['label']='提供完整的自助排查说明与适用条件'
    d['nodes'].insert(-1,{'id':'review','label':'复核处理记录与客户确认结果'})
    d['edges']=[e for e in d['edges'] if (e['from'],e['to'])!=('confirm','close')]
    d['edges'] += [{'from':'confirm','to':'review','label':'已解决'},{'from':'review','to':'close','label':'记录完整'}]
    d['layout']['primary_path']=['receive','triage','self_help','confirm','review','close']
    d=changed['architecture'];d['layers'][1]['items'][0]['detail']='记录订单状态，并在后续履约、客户咨询和异常处理中保留统一的业务标识'
    d['layers'][1]['items'].append({'id':'returns','label':'售后与退款服务','detail':'跟踪退货状态和退款请求'})
    d['edges'].append({'from':'support','to':'returns','label':'售后申请'})
    d=changed['gantt'];d['tasks'][1]['label']='课程大纲、分层练习与讲师教学脚本联合评审'
    d['tasks'][1]['owner']='教研团队 / 外部讲师 / 无障碍体验评审'
    d['tasks'][1]['progress']=63
    d['tasks'].append({'id':'followup','label':'开课反馈与首轮学习支持','owner':'班主任团队','start':'2026-10-10','end':'2026-10-13','progress':0,'depends':['launch']})
    d=changed['comparison'];d['data'][0]['label']='内容搜索、知识文章与长期自然访问带来的有效线索'
    d['data'][0]['value']=64;d['data'][2]['value']=-70
    d['data'].append({'label':'合作伙伴的联合内容与推荐','value':92})
    d=changed['trend'];d['data'][1]['value']=None;d['data'][4]['value']=1040
    d['data'].append({'date':'2026-10-05','value':1380})
    for d in changed.values():d['subtitle']+='（内容变更验收）'
    return changed


def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    models=json.loads((ROOT/'assets/refinement-cases.json').read_text())
    altered=mutations(models);records=[]
    names={'workflow':['流程','Workflow'],'architecture':['架构','Architecture'],'gantt':['甘特','Gantt'],'comparison':['对比','Comparison'],'trend':['趋势','Trend']}
    for key,model in models.items():
        variants=[('base',model),('changed',altered[key])]
        if key=='comparison':
            variant=copy.deepcopy(model);variant['comparison_style']='dot';variants.append(('dot',variant))
        for version,data in variants:
            folder=out/key/version;folder.mkdir(parents=True,exist_ok=True)
            source=folder/'source.json';source.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            result=render.render_file(source,folder)
            if result['qa']['errors'] or result['qa']['warnings']:raise ValueError(str(result['qa']))
            scene=json.loads((folder/'source.scene.json').read_text())
            sizes=[line[1] for n in scene['nodes'] if n.get('check') or n.get('content_text') for line in render.label_lines(n)]
            sizes.extend(e.get('_label_font',15) for e in scene['edges'] if e.get('label'))
            records.append({'type':key,'name':names[key],'version':version,'title':data['title'],
                            'svg':f'{key}/{version}/source.svg','reader':f'{key}/{version}/source.html',
                            'source':f'{key}/{version}/source.brief.json','drawio':f'{key}/{version}/source.drawio',
                            'receipt':f'{key}/{version}/source.delivery.json','width':scene['width'],'height':scene['height'],
                            'minimum_font':min(sizes or [14]),'geometry':'passed','browser':'not-run','manual':'not-run'})
    (out/'cases.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    template=(ROOT/'assets/refinement-gallery.html').read_text()
    (out/'index.html').write_text(template.replace('__CASES__',json.dumps(records,ensure_ascii=False).replace('<','\\u003c')))
    shutil.copy2(ROOT/'scripts/browser_quality.js',out/'browser_quality.js')
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    args=parser.parse_args();print(json.dumps({'diagrams':len(run(args.out)),'index':str(Path(args.out)/'index.html')}))
