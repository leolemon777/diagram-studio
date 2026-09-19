#!/usr/bin/env python3
"""Render four bounded comparison studies from one source model per study.

This is a reproducible expression lab, not a replacement for general render.py.
Python standard library only. See references/expression-design.md for bounds.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, PAPER, LINE = '#242E32', '#5D696D', '#FAF9F5', '#D7DCD7'
ACCENT, SOFT, NEG = '#286D65', '#DEE9E3', '#A64732'
W, H = 1360, 850


def digest(d):
    return hashlib.sha256(json.dumps(d, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def validate(d):
    if d.get('simulation') is not True:
        raise ValueError('Examples must be explicitly labelled as simulated.')
    s = d['marketing']['stages']
    if len(s) != 4 or any(x['value'] <= 0 for x in s) or any(a['value'] < b['value'] for a, b in zip(s, s[1:])):
        raise ValueError('Marketing study needs four positive nested cohort counts.')
    c = d['education']['courses']
    if len(c) != 4 or d['education']['scale'] != [0,100] or any(not 0 <= x[k] <= 100 for x in c for k in ('before','after')):
        raise ValueError('Education study needs four courses on the 0–100 scale.')
    p = d['planning']; tasks = p['tasks']; byid = {x['id']:x for x in tasks}
    if len(tasks) != 6 or set(byid) != set('abcdef') or p['horizon'] != 8:
        raise ValueError('Plan study uses six stable task IDs a–f and an eight-week horizon.')
    if p['links'] != [['a','b'],['a','c'],['b','d'],['c','e'],['d','e'],['e','f']]:
        raise ValueError('Plan topology is fixed for this composition study.')
    if any(not 0 <= t['start'] < t['end'] <= 8 for t in tasks):
        raise ValueError('Task interval outside the horizon.')
    if any(byid[a]['end'] > byid[b]['start'] for a,b in p['links']):
        raise ValueError('Finish-to-start constraint violated.')
    s = d['service']
    expected = [('a','b'),('b','c'),('b','d'),('c','e'),('d','e'),('e','f'),('e','d')]
    if len(s['nodes']) != 6 or [n['id'] for n in s['nodes']] != list('abcdef') or [(e['from'],e['to']) for e in s['edges']] != expected:
        raise ValueError('Service study uses the documented six-node, seven-edge topology.')
    for group in (d['marketing']['stages'], c, tasks, s['nodes']):
        if len({n['id'] for n in group}) != len(group):
            raise ValueError('Duplicate source ID.')
        if any(len(n['name']) > 7 for n in group):
            raise ValueError('This bounded study supports names up to seven characters; reflow longer labels.')


class Figure:
    def __init__(self, key, title, subtitle, model, note):
        self.key = key; self.parts = []; self.texts = []; self.model = model
        self.rect(0,0,W,H,PAPER)
        self.text(56,51, 'EXPRESSION STUDY / '+key.upper(),16,MUTED)
        self.text(56,112,title,34,INK,weight=600)
        self.text(56,153,subtitle,21,MUTED)
        self.line([(56,182),(1304,182)],LINE)
        self.line([(56,778),(1304,778)],LINE)
        self.text(56,818,note,18,MUTED)
        self.text(1304,51,'模拟数据',16,MUTED,anchor='end')

    def text(self,x,y,s,size=22,color=INK,anchor='start',weight=400):
        self.texts.append({'x':x,'y':y,'text':str(s),'size':size})
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{html.escape(str(s))}</text>')

    def rect(self,x,y,w,h,fill='none',stroke='none',sw=1):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self,points,color=INK,width=1.5,dash=False,arrow=False):
        attrs = f' stroke-dasharray="7 6"' if dash else ''
        attrs += f' marker-end="url(#{self.key}-arrow)"' if arrow else ''
        self.parts.append(f'<polyline points="'+ ' '.join(f'{x},{y}' for x,y in points) +f'" fill="none" stroke="{color}" stroke-width="{width}"{attrs}/>')

    def circle(self,x,y,r=7,fill=ACCENT,stroke='none',sw=2):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="{self.key}-title" data-model-sha256="{digest(self.model)}" style="font-family:PingFang SC,Microsoft YaHei,sans-serif">'
                f'<title id="{self.key}-title">{html.escape(self.model["title"])} · {self.key}</title>'
                f'<defs><marker id="{self.key}-arrow" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M1,1 L8,4 L1,7" fill="none" stroke="context-stroke" stroke-width="1.5"/></marker></defs>'
                + ''.join(self.parts) + '</svg>')


def marketing(m):
    stages = m['stages']; maximum = stages[0]['value']; scale=830/maximum
    a=Figure('marketing-a','留存阶梯', '以同一零点对齐人数，把总体规模与逐步收缩放在一起。',m,'所有长度使用同一人数尺度。各阶段是嵌套人数，不可相加；所有比例以最初访问人数为分母。')
    for tick in range(6):
        x=250+830*tick/5; a.line([(x,229),(x,692)],LINE,1)
        a.text(x,722,f'{maximum*tick/5:g}',17,MUTED,anchor='middle')
    for i,s in enumerate(stages):
        y=268+i*117
        a.text(56,y+9,s['name'],23)
        a.rect(250,y-17,scale*s['value'],34,ACCENT if i==3 else SOFT)
        a.line([(250,y+17),(250+scale*s['value'],y+17)],ACCENT,2)
        a.text(1286,y+8,f'{s["value"]:,} 人',29,ACCENT,anchor='end',weight=500)
        a.text(1286,y+43,f'{s["value"]/maximum:.1%} 留存',18,MUTED,anchor='end')
    a.text(1080,753,'人数 →',18,MUTED,anchor='end')
    b=Figure('marketing-b','流失去向', '把 1,000 人拆成四个互不重叠的去向，先找到损失最大的环节。'.replace('1,000',f'{maximum:,}'),m,'各段是互斥去向，可相加。向下投影后，段的位置用于排版；段的长度始终表示人数。')
    losses=[stages[i]['value']-stages[i+1]['value'] for i in range(3)]+[stages[-1]['value']]
    names=[f'{s["name"]}后离开' for s in stages[:-1]]+['最终完成购买']
    x=80; span=1200/maximum; colors=['#CCD4CE','#B1C3B9','#829F91',ACCENT]
    b.text(80,242,f'最初访问  {maximum:,} 人',23)
    centers=[]
    for count,color in zip(losses,colors):
        b.rect(x,283,count*span,52,color); centers.append(x+count*span/2); x+=count*span
    for i,(count,name,cx) in enumerate(zip(losses,names,centers)):
        y=407+i*92
        b.line([(cx,343),(cx,y-27),(460,y-27)],LINE,1)
        b.text(80,y,name,22)
        b.rect(460,y-20,count*span,25,colors[i])
        b.text(1248,y,f'{count:,} 人 / {count/maximum:.1%}',22,ACCENT if i==3 else INK,anchor='end')
    return a,b


def education(m):
    courses=m['courses']; a=Figure('education-a','成绩对照针','把每门课程的前后成绩绑在同一条轨道上，同时看基础与变化。',m,'满分 100 分；空心是前测，实心是后测。连接线表示差值，不代表中间存在连续观测。')
    x0=240; span=9
    for tick in range(0,101,20):
        x=x0+tick*span; a.line([(x,234),(x,679)],LINE,1); a.text(x,716,tick,18,MUTED,anchor='middle')
    for i,c in enumerate(courses):
        y=285+i*116; before=x0+c['before']*span; after=x0+c['after']*span; delta=c['after']-c['before']; color=ACCENT if delta>=0 else NEG
        a.text(56,y+8,c['name'],23); a.line([(before,y),(after,y)],color,3)
        a.circle(before,y,8,PAPER,color); a.circle(after,y,8,color)
        a.text(before,y-26,c['before'],22,MUTED,anchor='middle'); a.text(after,y+40,c['after'],23,color,anchor='middle',weight=600)
        a.text(1284,y+8,f'{delta:+g} 分',26,color,anchor='end')
    b=Figure('education-b','增幅刻度谱','把变化排到最前面；右侧始终保留前后原值，避免只有“增长”没有起点。',m,'增幅 = 后测 − 前测，单位为分。按增幅排序；颜色与正负号共同区分方向，不作效果归因。')
    ordered=sorted(courses,key=lambda c:c['after']-c['before'],reverse=True)
    # Symmetric common delta axis, adapted to the source values.
    extent=max(5,max(abs(c['after']-c['before']) for c in courses)); extent=((extent+4)//5)*5
    zero=658; scale=320/extent
    for tick in (-extent,-extent/2,0,extent/2,extent):
        x=zero+tick*scale; b.line([(x,244),(x,693)],INK if tick==0 else LINE,1.5 if tick==0 else 1)
        b.text(x,728,f'{tick:+g}' if tick else '0',18,MUTED,anchor='middle')
    b.text(1240,237,'前测 → 后测',19,MUTED,anchor='end')
    for i,c in enumerate(ordered):
        y=296+i*119; delta=c['after']-c['before']; x=zero+delta*scale; color=ACCENT if delta>=0 else NEG
        b.text(56,y+9,c['name'],23); b.line([(zero,y),(x,y)],color,8); b.circle(x,y,6,color)
        b.text(x+16 if delta>=0 else x-16,y+8,f'{delta:+g}',24,color,anchor='start' if delta>=0 else 'end',weight=600)
        b.text(1240,y+9,f'{c["before"]} → {c["after"]}',25,INK,anchor='end')
    return a,b


def planning(m):
    tasks=m['tasks']; byid={t['id']:t for t in tasks}; a=Figure('planning-a','时间轨道','按真实时间排列任务，先看并行与等待；依赖通过任务编号逐项保留。',m,'0 是项目开始；条带为 [开始, 结束) 区间。这里的“前置”均为完成后开始关系；图中无实际进度数据。')
    x0=285; step=95
    for tick in range(9):
        x=x0+tick*step; a.line([(x,255),(x,713)],LINE,1); a.text(x,233,tick,19,MUTED,anchor='middle')
    a.text(1090,233,'周',19,MUTED); a.text(1292,233,'前置任务',19,MUTED,anchor='end')
    for i,t in enumerate(tasks):
        y=300+i*75; a.text(56,y+8,t['id'].upper(),18,MUTED); a.text(93,y+8,t['name'],23)
        start=x0+t['start']*step; end=x0+t['end']*step
        a.rect(start,y-14,end-start,28,SOFT); a.line([(start,y-14),(start,y+14)],ACCENT,2); a.circle(end,y,6,ACCENT)
        a.text((start+end)/2,y+7,f'{t["start"]}–{t["end"]}',19,INK,anchor='middle')
        parents=[s.upper() for s,d in m['links'] if d==t['id']]
        a.text(1292,y+8,'、'.join(parents) if parents else '起点',21,MUTED,anchor='end')
    b=Figure('planning-b','依赖路径','把先后约束放到画面中心，同时在每个任务旁保留时间区间。',m,'横向位置仅表示依赖层次，距离不表示时长。每条箭头表示完成后开始；准确时间见任务下方。')
    positions={'a':(145,449),'b':(400,340),'c':(650,582),'d':(650,340),'e':(913,449),'f':(1170,449)}
    for s,d in m['links']:
        x,y=positions[s]; xx,yy=positions[d]
        if d == 'e':
            bend=yy-31 if y<yy else yy+35
            entry=yy-10 if y<yy else yy+10
            pts=[(x+17,y),(xx-123,y),(xx-123,bend),(xx-17,entry)]
        elif y==yy: pts=[(x+17,y),(xx-20,yy)]
        else:
            mid=(x+xx)/2; pts=[(x+17,y),(mid,y),(mid,yy),(xx-20,yy)]
        b.line(pts,ACCENT,2,arrow=True)
    for t in tasks:
        x,y=positions[t['id']]; b.circle(x,y,17,PAPER,ACCENT,2); b.text(x,y+6,t['id'].upper(),16,ACCENT,anchor='middle',weight=600)
        b.text(x,y-40,t['name'],24,anchor='middle',weight=500)
        b.text(x,y+50,f'第 {t["start"]}–{t["end"]} 周',22,MUTED,anchor='middle')
        b.text(x,y+79,f'{t["end"]-t["start"]} 周工期',17,MUTED,anchor='middle')
    b.text(56,242,'分支 / 并行准备',18,MUTED); b.text(1280,242,'汇合 / 验证后上线',18,MUTED,anchor='end')
    return a,b


def service(m):
    a=Figure('service-a','主线与回流','把常规处理放在上方，复杂问题与返工集中到下方；箭头始终给出方向。',m,'连线只表示处理关系，粗细不代表流量；“未解决”回到人工处理。间距不代表处理时长。')
    pos={'a':(128,342),'b':(352,342),'c':(642,342),'d':(642,588),'e':(958,342),'f':(1220,342)}
    routes={
        'r1':([(149,342),(329,342)],(234,313)),
        'r2':([(375,342),(619,342)],(495,313)),
        'r3':([(352,365),(352,588),(619,588)],(458,563)),
        'r4':([(665,342),(935,342)],(796,313)),
        'r5':([(665,588),(835,588),(835,405),(958,405),(958,365)],(752,563)),
        'r6':([(981,342),(1197,342)],(1085,313)),
        'r7':([(978,354),(1020,382),(1020,682),(642,682),(642,611)],(829,717))}
    for e in m['edges']:
        points,label=routes[e['id']]; color=NEG if e['id']=='r7' else ACCENT
        a.line(points,color,2.2,e['id']=='r7',True); a.text(*label,e['label'],19,color,anchor='middle')
    for n in m['nodes']:
        x,y=pos[n['id']]; a.circle(x,y,21,PAPER,INK,1.7); a.text(x,y+7,n['id'].upper(),18,anchor='middle'); a.text(x,y-49,n['name'],24,anchor='middle',weight=500)
    b=Figure('service-b','交接矩阵','把每一段有向关系放入固定格子，查“谁交给谁”和遗漏，比追线更直接。',m,'读法：行 = 来源，列 = 去向；实心点表示存在该关系，空格表示无直接关系。返回仍是有向关系。')
    nodes=m['nodes']; lookup={n['id']:i for i,n in enumerate(nodes)}; x0=240; y0=274; cell=76
    b.text(84,246,'来源 ↓ / 去向 →',18,MUTED)
    for i,n in enumerate(nodes):
        x=x0+(i+.5)*cell; y=y0+(i+.5)*cell
        b.text(x,243,n['id'].upper(),20,MUTED,anchor='middle')
        b.text(213,y+7,n['id'].upper()+'  '+n['name'],21,anchor='end')
        b.text(778,278+i*37,n['id'].upper()+'  '+n['name'],19,MUTED)
    for i in range(7):
        b.line([(x0+i*cell,y0),(x0+i*cell,y0+6*cell)],LINE,1)
        b.line([(x0,y0+i*cell),(x0+6*cell,y0+i*cell)],LINE,1)
    for e in m['edges']:
        x=x0+(lookup[e['to']]+.5)*cell; y=y0+(lookup[e['from']]+.5)*cell; color=NEG if e['id']=='r7' else ACCENT
        b.circle(x,y-9,5,color); b.text(x,y+19,e['id'].upper(),16,color,anchor='middle')
    b.text(778,520,'逐条关系',22,weight=500)
    for i,e in enumerate(m['edges']):
        b.text(778,554+i*30,f'{e["id"].upper()}   {e["from"].upper()} → {e["to"].upper()}    {e["label"]}',19,NEG if e['id']=='r7' else INK)
    return a,b


META={
    'marketing':{'label':'营销转化','question':'人数怎样减少？','title':'从规模，看到去向。','views':['留存阶梯','流失去向'],'lead':'同一批 1,000 位用户，既能看各阶段留下多少，也能看最后分别流失在哪里。','use':['需要快速比较各阶段规模。共同零点让长度易于判断。','需要找最大损失环节。互斥拆分让每位用户只被计算一次。'],'trade':['阶段人数不能相加。逐步转化率要另外计算。','突出总人数的去向；逐阶段的累计规模需要回看原始数据。'],'read':['购买人数是多少？占最初访问的多少？','哪个环节流失最多？四个去向能否加回 1,000？']},
    'education':{'label':'教育评估','question':'到底变化多少？','title':'先看起点，或先看变化。','views':['成绩对照针','增幅刻度谱'],'lead':'同样四门课程，原始成绩与增减分数完全一致；改变的是读者先看到的信息。','use':['同时比较起点和终点，避免把低起点的大进步与高水平混为一谈。','需要迅速比较进步与退步，并决定进一步观察的顺序。'],'trade':['前后数值接近时，标签需要上下错开。','按增幅排序会改变课程顺序；保留原值才能理解基础水平。'],'read':['后测最高的是哪门？前测是多少？','哪门进步最大？是否有退步，退步多少分？']},
    'planning':{'label':'项目计划','question':'什么时候，依赖谁？','title':'时间与依赖，各自清楚。','views':['时间轨道','依赖路径'],'lead':'同样六个任务、六条依赖、八周时间。时间图回答排期，关系图回答先后约束。','use':['安排工作和检查并行任务，直接读取每个时间区间。','说明多个准备项如何汇合，讨论某任务等待哪些前置完成。'],'trade':['依赖以编号列出；复杂依赖需要另看路径。','路径距离没有时间含义，不能用视觉长度推断工期。'],'read':['第 4–5 周有哪些任务正在进行？','联合验证依赖谁？内容准备后是否可以直接上线？']},
    'service':{'label':'客户服务','question':'怎么走，哪里返回？','title':'顺着故事读，或逐条核对。','views':['主线与回流','交接矩阵'],'lead':'同样六个节点、七条有向关系。流程图适合讲解，矩阵适合查找与核对。','use':['面向首次阅读的人，沿箭头理解分支、汇合和未解决后的返回。','面向熟悉节点的人，定位来源与去向，避免在密集连线中找关系。'],'trade':['规模增加后，回路线可能产生交叉，需要拆分或换表达。','矩阵有阅读门槛；保留行列方向和节点全称，不作为大众默认图。'],'read':['复杂问题交给谁？用户确认未解决后怎么办？','人工处理的直接下一步是谁？返回关系位于哪个格子？']}
}


def source_table(key,m):
    if key=='marketing':
        headers=['阶段','人数','相对初始留存']; rows=[[s['name'],s['value'],f'{s["value"]/m["stages"][0]["value"]:.1%}'] for s in m['stages']]
    elif key=='education':
        headers=['课程','前测 / 分','后测 / 分','变化 / 分']; rows=[[c['name'],c['before'],c['after'],f'{c["after"]-c["before"]:+g}'] for c in m['courses']]
    elif key=='planning':
        headers=['任务','开始 / 周','结束 / 周','前置任务']; rows=[[t['id'].upper()+' '+t['name'],t['start'],t['end'],'、'.join(s.upper() for s,d in m['links'] if d==t['id']) or '起点'] for t in m['tasks']]
    else:
        names={n['id']:n['name'] for n in m['nodes']}; headers=['关系','来源','去向','条件 / 动作']; rows=[[e['id'].upper(),names[e['from']],names[e['to']],e['label']] for e in m['edges']]
    return '<table><caption>两种表达共用的数据 · 模拟</caption><thead><tr>'+''.join('<th scope="col">'+html.escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table>'


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--input',type=Path,default=ROOT/'assets/expression-examples.json'); p.add_argument('--out',type=Path,required=True); args=p.parse_args()
    data=json.loads(args.input.read_text()); validate(data); args.out.mkdir(parents=True,exist_ok=True)
    studies=[]; qa={'scope':'four bounded studies / source invariants and SVG parse only; browser and human review are separate','figures':[]}
    for key,renderer in [('marketing',marketing),('education',education),('planning',planning),('service',service)]:
        figures=renderer(data[key]); entry={'key':key,**META[key],'svgs':[],'table':source_table(key,data[key])}
        if key == 'marketing':
            maximum=f'{data[key]["stages"][0]["value"]:,}'
            entry['lead']=entry['lead'].replace('1,000',maximum)
            entry['read']=[s.replace('1,000',maximum) for s in entry['read']]
        for fig in figures:
            svg=fig.svg(); ET.fromstring(svg); (args.out/(fig.key+'.svg')).write_text(svg)
            entry['svgs'].append(svg); qa['figures'].append({'file':fig.key+'.svg','source_sha256':digest(data[key]),'text_count':len(fig.texts)})
        studies.append(entry)
    (args.out/'source-models.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    (args.out/'semantic-qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    template=(ROOT/'assets/expression-lab.html').read_text()
    (args.out/'index.html').write_text(template.replace('__STUDIES__',json.dumps(studies,ensure_ascii=False).replace('</','<\/')))
    print(json.dumps({'output':str(args.out),'figures':len(qa['figures']),'status':'rendered; visual review pending'},ensure_ascii=False))


if __name__=='__main__':
    main()
