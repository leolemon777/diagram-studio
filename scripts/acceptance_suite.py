#!/usr/bin/env python3
"""Render the v37 cross-industry acceptance set from fresh, simulated briefs."""
from __future__ import annotations

import argparse
import copy
import html
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'scripts'
if str(SCRIPTS) not in sys.path: sys.path.insert(0,str(SCRIPTS))
import cross_industry
import render as generic


GENERIC_SCENARIOS=(
    ('education-course-launch',ROOT/'assets/examples/61-gantt-delivery.json','教育培训：课程上线','日期、进度、依赖与里程碑'),
    ('admin-procurement-approval',ROOT/'assets/acceptance-scenarios/admin-procurement-approval.json','行政办公：采购审批','责任交接、分支与回流'),
    ('team-responsibility-tree',ROOT/'assets/acceptance-scenarios/team-responsibility-tree.json','企业管理：团队分工','层级与职责范围'),
    ('marketing-campaign-review',ROOT/'assets/acceptance-scenarios/marketing-campaign-review.json','营销电商：活动复盘','统一口径、零基线与标签'),
    ('software-service-architecture',ROOT/'assets/acceptance-scenarios/software-service-architecture.json','软件产品：系统说明','层次、边界和连接'),
    ('medical-appointment-service',ROOT/'assets/acceptance-scenarios/medical-appointment-service.json','医疗服务：预约到随访','服务节点与责任交接'),
    ('retail-order-fulfillment',ROOT/'assets/acceptance-scenarios/retail-order-fulfillment.json','零售物流：订单履约','状态流转与异常回流'),
)
FINANCE_SOURCE=ROOT/'assets/acceptance-scenarios/finance-project-quotation.json'


def require(condition,message):
    if not condition: raise AssertionError(message)


def svg_text(path):
    root=ET.parse(path).getroot()
    return '\n'.join(''.join(node.itertext()) for node in root.iter('{http://www.w3.org/2000/svg}text'))


def page_ratio(svg):
    root=ET.parse(svg).getroot()
    width=float(root.attrib['width'].removesuffix('pt'))
    height=float(root.attrib['height'].removesuffix('pt'))
    return round(width/height,4)


def render_generic(out):
    reports=[]
    for identifier,source,scenario,focus in GENERIC_SCENARIOS:
        result=generic.render_file(source,out/identifier,'light')
        require(not result['qa']['errors'],f'{identifier}: generic layout errors')
        require(ET.parse(result['drawio']).getroot().tag=='mxfile',f'{identifier}: draw.io XML invalid')
        data=json.loads(source.read_text(encoding='utf-8'))
        changed=copy.deepcopy(data)
        if data['type']=='gantt': target=changed['tasks'][0]
        elif data['type']=='tree': target=changed['root']
        elif data['type']=='architecture': target=changed['layers'][0]['items'][0]
        elif data['type']=='chart': target=changed['data'][0]
        else: target=changed['nodes'][0]
        old=target['label']; target['label']='变更验证'
        if data['type']=='gantt': target['progress']=63
        if data['type']=='chart': target['value']+=17
        mutation_dir=out/(identifier+'-mutation'); mutation_dir.mkdir(parents=True,exist_ok=True)
        mutation_source=mutation_dir/'changed.json'
        mutation_source.write_text(json.dumps(changed,ensure_ascii=False),encoding='utf-8')
        mutated=generic.render_file(mutation_source,mutation_dir,'light')
        visible=svg_text(mutated['svg'])
        require('变更验证' in visible and old not in visible,f'{identifier}: stale or missing changed label')
        require(not mutated['qa']['errors'] and not mutated['qa']['warnings'],f'{identifier}: mutation layout failed')
        if data['type']=='gantt': require('63%' in visible,'changed progress not visible')
        if data['type']=='chart':
            scene=json.loads((mutation_dir/'changed.scene.json').read_text())
            require(scene['meta']['data_values'][0]==target['value'],'changed chart value not propagated')
        reports.append({
            'id':identifier,'scenario':scenario,'focus':focus,'status':'passed',
            'source':str(source.relative_to(ROOT)),'svg':str(Path(result['svg']).relative_to(out)),
            'drawio':str(Path(result['drawio']).relative_to(out)),'validation':'通用几何检查及修改重绘通过；未运行实际字体边界或原生编辑器检查',
            'mutation':{'status':'passed','svg':str(Path(mutated['svg']).relative_to(out)),'stale_label_visible':False},
            'rendered_visual_check':'not-run',
        })
    return reports


def render_finance(out):
    data=json.loads(FINANCE_SOURCE.read_text(encoding='utf-8'))
    base=out/'finance-project-quotation'
    calc=cross_industry.render(data,base,'quotation')
    qa=json.loads((base/'quotation.qa.json').read_text(encoding='utf-8'))
    require(not qa['errors'] and not qa['warnings'],'finance quotation visual QA failed')
    require(round(calc['total'],2)==25440,'finance quotation total is wrong')
    require(abs(page_ratio(base/'quotation.svg')-(210/297))<.0005,'finance quotation paper ratio is wrong')

    changed=copy.deepcopy(data)
    changed['line_items'][1]['quantity']=3
    changed['declared_total']=28196
    mutation=out/'finance-project-quotation-mutation'
    changed_calc=cross_industry.render(changed,mutation,'quotation')
    text=svg_text(mutation/'quotation.svg')
    require(changed_calc['total']==28196,'mutated finance total is wrong')
    require('到货质检与交付复核 ×3' in text and '¥28,196' in text,'mutated finance values were not rendered')
    require('¥25,440' not in text and '到货质检与交付复核 ×2' not in text,'stale finance values remain visible')
    return {
        'id':'finance-project-quotation','scenario':'财务采购：项目报价','focus':'明细、税率、汇总和物理页面尺寸',
        'status':'passed','source':str(FINANCE_SOURCE.relative_to(ROOT)),'svg':'finance-project-quotation/quotation.svg',
        'drawio':None,'validation':'财务计算、渲染数据变异、页面比例和实际文字边界检查通过；JSON 是可编辑源',
        'mutation':{'quantity':3,'total':changed_calc['total'],'stale_values_visible':False},
    }


def check_gantt_variants():
    files=[ROOT/'assets/examples/60-gantt-executive.json',ROOT/'assets/examples/61-gantt-delivery.json',ROOT/'assets/examples/62-gantt-print.json']
    models=[json.loads(path.read_text(encoding='utf-8')) for path in files]
    expected=models[0]['tasks']
    require(all(model['tasks']==expected for model in models[1:]),'gantt variants do not share task data')
    require([model['gantt_variant'] for model in models]==['executive','delivery','print'],'gantt variant ids changed')
    return {'shared_task_count':len(expected),'variants':['executive','delivery','print'],'critical_path':'not calculated'}


def write_html(out,report):
    rows=[]
    for row in report['scenarios']:
        links=f'<a href="{html.escape(row["svg"])}">SVG</a>'
        if row['drawio']: links+=f' · <a href="{html.escape(row["drawio"])}">draw.io</a>'
        rows.append('<tr><td>'+html.escape(row['scenario'])+'</td><td>'+html.escape(row['focus'])+'</td><td>'+html.escape(row['validation'])+'</td><td>'+links+'</td></tr>')
    out.joinpath('index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v37 跨行业验收集</title><style>body{background:#f1efeb;color:#34322d;font:16px/1.65 -apple-system,"PingFang SC",sans-serif;max-width:1180px;margin:38px auto;padding:0 24px}h1,h2{font-family:"Songti SC",serif}table{width:100%;border-collapse:collapse;background:#faf9f6}th,td{padding:12px;border:1px solid #d8d3c8;text-align:left;vertical-align:top}a{color:#765541}</style><h1>v37 跨行业常用成果验收集</h1><p>全部为模拟输入。页面列出实际运行的检查，不把它们表述为行业标准或人工终验。</p><table><tr><th>场景</th><th>检查重点</th><th>验证</th><th>产物</th></tr>'''+''.join(rows)+'''</table></html>''',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    args=parser.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    scenarios=render_generic(out); scenarios.insert(4,render_finance(out))
    report={
        'version':'v37-candidate','data_status':'all inputs are simulated',
        'scenarios':scenarios,'gantt_variants':check_gantt_variants(),
        'boundary':'视觉检查使用渲染后的文字边界。此验收集不包含人工设计签收、原生 draw.io 编辑或行业专业审批。',
    }
    (out/'acceptance-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_html(out,report)
    print(json.dumps({'scenarios':len(scenarios),'out':str(out),'gantt_variants':report['gantt_variants']},ensure_ascii=False))


if __name__=='__main__': main()
