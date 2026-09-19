#!/usr/bin/env python3
"""Nine reusable operational recipes. Calculation is separate from presentation.
Use JSON inputs, explicit provenance, and exact units. All examples are synthetic.
"""
import argparse
import copy
import csv
import json
import math
from pathlib import Path
from editorial_style import PALETTES, mpl_style, palette

MODES = ('oee','balance','control_imr','vsm','sipoc','sales_review',
         'sales_funnel','inventory_review','energy_review')

def need(ok, message):
    if not ok: raise ValueError(message)

def num(x, positive=False, signed=False):
    need(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x), 'finite numeric value required')
    need(signed or x >= 0, 'nonnegative value required')
    need(not positive or x > 0, 'positive value required')
    return float(x)

def integer(x, positive=False):
    num(x,positive)
    need(int(x)==x, 'integer count required')
    return int(x)

def named(rows, low=1, high=12):
    need(isinstance(rows,list) and low<=len(rows)<=high, f'expected {low}–{high} named rows')
    names=[r.get('name') for r in rows]
    need(all(isinstance(n,str) and n.strip() for n in names) and len(set(names))==len(names), 'unique nonempty names required')
    return rows

def analyze(d):
    mode=d['mode']; need(mode in MODES,'unsupported operations mode')
    need(bool(d.get('title')) and bool(d.get('data_status')), 'title and data_status required')
    out={'mode':mode,'data_status':d['data_status'],'assumptions':d.get('assumptions',[])}
    if mode=='oee':
        rows=[]
        for r in named(d['periods'],1,4):
            planned=num(r['planned_minutes'],True); stopped=num(r['stop_minutes'])
            need(stopped<planned,'stop time must be less than planned time')
            cycle=num(r['ideal_cycle_seconds'],True); total=integer(r['total_count'],True); good=integer(r['first_pass_good'])
            need(good<=total,'first-pass good cannot exceed total')
            run=planned-stopped; ideal=cycle*total/60; productive=cycle*good/60
            need(ideal<=run+1e-9,'performance exceeds 100%; check ideal cycle and counts')
            a=run/planned;p=ideal/run;q=good/total
            rows.append({**r,'run_minutes':run,'availability':a,'performance':p,'quality':q,
                'oee':a*p*q,'stop_loss_minutes':stopped,'speed_loss_minutes':max(0,run-ideal),
                'quality_loss_minutes':ideal-productive,'productive_minutes':productive})
        out['periods']=rows
    elif mode=='balance':
        available=num(d['available_seconds'],True); demand=integer(d['demand_units'],True)
        rows=named(d['stations'],2,10)
        cycles=[num(r['cycle_seconds'],True) for r in rows]
        bottleneck=max(cycles)
        out.update(stations=rows,takt_seconds=available/demand,
            bottleneck_seconds=bottleneck,bottlenecks=[r['name'] for r in rows if r['cycle_seconds']==bottleneck],
            ideal_capacity_units=math.floor(available/bottleneck),
            balance_efficiency=sum(cycles)/(len(cycles)*bottleneck),
            over_takt=[r['name'] for r in rows if r['cycle_seconds']>available/demand])
    elif mode=='control_imr':
        values=[num(x,signed=True) for x in d['values']]
        need(8<=len(values)<=120,'I-MR requires 8–120 sequential observations for this renderer')
        n=d.get('baseline_count',len(values));need(isinstance(n,int) and not isinstance(n,bool) and 8<=n<=len(values),'baseline_count must be 8–N')
        need(bool(d.get('unit')),'measurement unit required')
        base=values[:n]; mr=[abs(b-a) for a,b in zip(values,values[1:])]
        mean=sum(base)/n;mrbar=sum(mr[:n-1])/(n-1)
        need(mrbar>0,'zero baseline moving range: cannot estimate nonzero process variation')
        sigma=mrbar/1.128;lo=mean-3*sigma;hi=mean+3*sigma
        out.update(values=values,baseline_count=n,center=mean,mr=mr,mr_center=mrbar,
            lcl=lo,ucl=hi,mr_lcl=0,mr_ucl=3.267*mrbar,
            individual_signals=[i+1 for i,x in enumerate(values) if x<lo or x>hi],
            mr_signals=[i+2 for i,x in enumerate(mr) if x>3.267*mrbar],
            rule='Only points beyond the three-sigma limits; no run or trend tests. Trial limits require process review.')
    elif mode=='vsm':
        rows=named(d['processes'],2,5);waiting=0;processing=0
        for r in rows:
            processing+=num(r['cycle_seconds'],True)/60
            waiting+=num(r['wait_before_minutes'])
            integer(r['inventory_before'])
        need(d.get('supplier') and d.get('customer') and d.get('information_flow'), 'supplier, customer and information_flow required')
        tail=num(d.get('finished_wait_minutes',0));waiting+=tail
        out.update(processes=rows,processing_minutes=processing,waiting_minutes=waiting,
            lead_minutes=waiting+processing,processing_share=processing/(waiting+processing))
    elif mode=='sipoc':
        need(bool(d.get('boundary_start')) and bool(d.get('boundary_end')),'explicit process boundary required')
        for k in ('suppliers','inputs','process','outputs','customers'):
            need(isinstance(d.get(k),list) and 1<=len(d[k])<=6 and all(isinstance(x,str) and x.strip() for x in d[k]), 'SIPOC '+k+' requires 1–6 nonempty items')
        need(len(d['outputs'])==len(d['customers']), 'outputs and customer requirements must be paired by row')
        out['output_customer_pairs']=list(zip(d['outputs'],d['customers']))
    elif mode=='sales_review':
        from datetime import datetime
        rows=named(d['months'],2,12);dates=[]
        for r in rows:
            t=datetime.strptime(r['name'],'%Y-%m');need(t.strftime('%Y-%m')==r['name'],'use YYYY-MM')
            dates.append(t);num(r['actual']);num(r['target'],True)
        need(all((b.year-a.year)*12+b.month-a.month==1 for a,b in zip(dates,dates[1:])), 'sales months must be consecutive')
        total=sum(r['actual'] for r in rows);target=sum(r['target'] for r in rows)
        for key in ('regions','products'):
            rr=named(d[key],1,6)
            for r in rr:num(r['value'])
            need(math.isclose(sum(r['value'] for r in rr),total,rel_tol=1e-9,abs_tol=1e-6),key+' must reconcile to period sales')
        need(bool(d.get('unit')),'sales unit required')
        out.update(total=total,target=target,attainment=total/target,gap=total-target,
            months=[{**r,'attainment':r['actual']/r['target']} for r in rows])
    elif mode=='sales_funnel':
        need(bool(d.get('cohort')),'same-cohort definition required')
        rows=named(d['stages'],2,7);counts=[integer(r['count']) for r in rows]
        need(counts[0]>0 and all(b<=a for a,b in zip(counts,counts[1:])), 'funnel counts must be nonincreasing and start above zero')
        out['stages']=[{**r,'from_previous':counts[i]/counts[i-1] if i and counts[i-1]>0 else None,
            'from_start':counts[i]/counts[0], 'lost':counts[i-1]-counts[i] if i else 0} for i,r in enumerate(rows)]
        out['overall_conversion']=counts[-1]/counts[0]
    elif mode=='inventory_review':
        rows=named(d['items'],1,8)
        for r in rows:
            need(bool(r.get('unit')),'item unit required')
            for k in ('opening','receipts','issues','closing'):num(r[k])
            need(math.isclose(r['opening']+r['receipts']-r['issues'],r['closing'],abs_tol=1e-6), 'inventory ledger does not reconcile: '+r['name'])
        cogs=num(d['period_cogs'],True);average=num(d['average_inventory_cost'],True);days=num(d['period_days'],True)
        ending=num(d['ending_inventory_cost']);aging=named(d['aging'],2,6)
        for r in aging:num(r['value'])
        need(math.isclose(sum(r['value'] for r in aging),ending,rel_tol=1e-9,abs_tol=1e-6),'aging must reconcile to ending cost')
        need(bool(d.get('cost_unit')),'cost unit required')
        out.update(turnover_for_period=cogs/average,inventory_days=days*average/cogs,
            period_days=days,items=rows,ending_inventory_cost=ending)
    elif mode=='energy_review':
        from energy_plot import analyze as energy_analyze
        need(1<=len(d['series'])<=2,'energy review supports one or two separately scaled resources')
        dd={**d,'mode':'intensity'};calc=energy_analyze(dd)
        out.update(months=calc['months'],series=calc['series'],rows=calc['rows'])
    return out

def structural(d,theme):
    from render import Scene, audit, svg, drawio
    p=palette(theme);s=Scene(dict(title=d['title'],width=1800,height=1040),'editorial-'+p['id'])
    s.text(80,40,1500,30,'OPERATIONS ATLAS  /  运营与精益',16,'accent')
    s.text(80,90,1640,68,d['title'],44)
    s.text(80,164,1640,45,d.get('subtitle',''),20,'muted')
    def text(x,y,w,h,v,fs=22,tone='ink'):return s.text(x,y,w,h,v,fs,tone)
    if d['mode']=='sipoc':
        text(80,225,1640,45,f"过程边界：{d['boundary_start']} → {d['boundary_end']}",23,'accent')
        labels=['S · 供应方','I · 输入与要求','P · 关键过程','O · 输出','C · 客户与要求']
        keys=['suppliers','inputs','process','outputs','customers']
        for i,(label,key) in enumerate(zip(labels,keys)):
            x=80+i*330
            s.add(x,310,310,535,kind='panel',fill='tint' if i==2 else 'bg',stroke='line',radius=0)
            text(x+22,340,266,44,label,26,'accent')
            for j,value in enumerate(d[key]):
                text(x+22,410+j*66,266,60,(f'{j+1:02d}  ' if key=='process' else '')+value,20)
        text(80,866,1640,60,'阅读规则：先确定范围；输出与客户要求逐行配对。其余列用于界定过程，不表示逐行因果。',18,'muted')
    else:
        a=analyze(d);rows=d['processes'];n=len(rows);step=1640/n;w=min(260,step-42)
        text(80,236,1640,45,f"{d['supplier']}  →  {d['customer']}  ·  {d.get('state','当前态')}",24,'accent')
        text(80,310,1640,65,'信息流：'+d['information_flow'],22)
        s.edge(points=[[1640,390],[160,390]],dashed=True,width=1.4,tone='muted')
        for i,r in enumerate(rows):
            x=80+i*step
            s.add(x,495,w,148,r['name'],f"CT {r['cycle_seconds']:g} 秒 / 件",tone='accent',radius=0,check=True,fs=27)
            text(x,665,w,75,f"前置库存 {r['inventory_before']:g} 件\n等待 {r['wait_before_minutes']:g} 分钟",19,'muted')
            s.edge(points=[[x+w/2,390],[x+w/2,476]],dashed=True,width=1.3,tone='muted')
            if i<n-1:s.edge(points=[[x+w+3,565],[x+step-12,565]],width=2)
        text(80,758,1640,36,'时间线 · 等待以分钟计；加工周期统一换算为分钟；每个等待段只计一次',18,'muted')
        # Explicit stepped timeline: the horizontal lengths are schematic, labels carry duration.
        points=[]
        for i,r in enumerate(rows):
            x=80+i*step
            points.extend([[x,830],[x+step*.48,830],[x+step*.48,870],[x+step*.9,870],[x+step*.9,830]])
            text(x,790,step*.5,32,f"等待 {r['wait_before_minutes']:g} min",16)
            text(x+step*.48,876,step*.5,32,f"加工 {r['cycle_seconds']/60:.2f} min",16,'accent')
        s.edge(points=points,arrow=False,width=1.2,tone='ink')
        text(80,924,1640,45,f"等待合计 {a['waiting_minutes']:g} min  ·  加工合计 {a['processing_minutes']:.2f} min  ·  流经时间 {a['lead_minutes']:.2f} min  ·  出货等待 {d.get('finished_wait_minutes',0):g} min",21,'accent')
    text(80,988,1640,35,d['data_status']+'  /  '+d.get('footnote','可编辑结构示意；未作现场工程验证'),16,'muted')
    q=audit(s);need(not q['errors'],'layout: '+str(q['errors']))
    return s,q,svg(s),drawio(s)

def render(d,out,theme='warm',stem=None):
    a=analyze(d);out=Path(out);out.mkdir(parents=True,exist_ok=True);stem=stem or d['mode']
    files=[]
    def save(suffix,value):
        path=out/(stem+suffix);path.write_text(value,encoding='utf-8');files.append(path.name)
    save('.input.json',json.dumps(d,ensure_ascii=False,indent=2))
    save('.analysis.json',json.dumps(a,ensure_ascii=False,indent=2,allow_nan=False))
    if d['mode'] in ('vsm','sipoc'):
        s,q,svg,drawio=structural(d,theme)
        save('.svg',svg);save('.drawio',drawio)
        save('.scene.json',json.dumps(dict(nodes=s.nodes,edges=s.edges,palette=s.palette,width=s.w,height=s.h),ensure_ascii=False,indent=2))
        save('.qa.json',json.dumps(q,ensure_ascii=False,indent=2))
        # Render the same scene model using the existing Matplotlib dependency.
        render_scene(s,out/stem,theme)
        files.extend([stem+'.png',stem+'.pdf'])
        return {'files':files,'analysis':a}
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    from matplotlib.lines import Line2D
    import numpy as np
    p,heading,rc=mpl_style(theme)
    with plt.rc_context(rc):
        fig=plt.figure(figsize=(16,10),layout=None)
        fig.text(.055,.925,d['title'],fontsize=29,fontfamily=heading,color=p['ink'])
        fig.text(.055,.875,d.get('subtitle',''),fontsize=12,color=p['muted'])
        fig.text(.055,.975,'OPERATIONS ATLAS  /  运营与精益',fontsize=10,color=p['accent'])
        fig.add_artist(Line2D([.055,.945],[.842,.842],transform=fig.transFigure,color=p['line'],lw=.8))
        fig.text(.055,.035,d['data_status']+'  /  '+d.get('footnote','输入与计算结果随图保存'),fontsize=10,color=p['muted'])
        axes=[]
        def ax(rect,title,ylabel=''):
            z=fig.add_axes(rect);axes.append(z);z.set_title(title,loc='left',pad=18,fontsize=14,color=p['ink']);z.set_ylabel(ylabel,fontsize=10);z.set_axisbelow(True);z.grid(axis='y');return z
        def metric(x,label,value,note=''):
            fig.text(x,.77,label,fontsize=11,color=p['muted']);fig.text(x,.716,value,fontsize=29,fontfamily=heading,color=p['accent']);fig.text(x,.682,note,fontsize=10,color=p['muted'])
        def bars(z,labels,values,percent=False):
            xx=np.arange(len(values)); bb=z.bar(xx,values,width=.55,color=p['accent']);z.set_xticks(xx,labels)
            z.set_ylim(0,max(values or [1])*1.23 or 1)
            for b,v in zip(bb,values):z.annotate(f'{v:.1%}' if percent else f'{v:g}',(b.get_x()+b.get_width()/2,v),xytext=(0,5),textcoords='offset points',ha='center',fontsize=10)
            if percent:z.yaxis.set_major_formatter(PercentFormatter(1))
        mode=d['mode']
        if mode=='oee':
            r=a['periods'][-1];metric(.055,'设备综合效率',f"{r['oee']:.1%}",r['name']);metric(.365,'一次合格产出',f"{r['first_pass_good']:,} 件",'返工品不计入一次合格');metric(.675,'可生产时间',f"{r['run_minutes']:g} min",'计划时间扣除停机')
            z=ax([.075,.20,.40,.38],'01  效率分解','比率');xx=np.arange(4);ww=.7/len(a['periods'])
            for i,r in enumerate(a['periods']):
                vals=[r[k] for k in ('availability','performance','quality','oee')]
                b=z.bar(xx+(i-(len(a['periods'])-1)/2)*ww,vals,ww,label=r['name'],color=p['accent'] if i==len(a['periods'])-1 else p['tint'],edgecolor=p['ink'],linewidth=.6,hatch=['//','..','xx'][i] if i<len(a['periods'])-1 else '')
                z.bar_label(b,labels=[f'{v:.1%}' for v in vals],padding=5,fontsize=10 if len(a['periods'])<=2 else 8)
            z.set_xticks(xx,['时间开动率','性能效率','质量率','OEE']);z.set_ylim(0,1.18);z.yaxis.set_major_formatter(PercentFormatter(1));z.legend(loc='upper left',bbox_to_anchor=(0,-.20),ncol=2)
            z=ax([.565,.20,.36,.38],'02  计划时间如何分配','分钟');r=a['periods'][-1]
            bars(z,['停机','速度损失','质量损失','有效生产'],[r[k] for k in ('stop_loss_minutes','speed_loss_minutes','quality_loss_minutes','productive_minutes')])
        elif mode=='balance':
            metric(.055,'需求节拍',f"{a['takt_seconds']:.1f} 秒 / 件",'净可用时间 ÷ 需求量');metric(.365,'瓶颈理想产能',f"{a['ideal_capacity_units']:,} 件",'单件流稳态上限；未扣停机和不良');metric(.675,'工位平衡率',f"{a['balance_efficiency']:.1%}",'总作业时间 ÷ 工位数 ÷ 瓶颈周期')
            z=ax([.075,.19,.85,.39],'01  工位周期与需求节拍','秒 / 件');bars(z,[r['name'] for r in d['stations']],[r['cycle_seconds'] for r in d['stations']]);z.axhline(a['takt_seconds'],color=p['ink'],ls='--',lw=1.2,label=f"需求节拍 {a['takt_seconds']:.1f} s");z.legend(loc='upper right');fig.text(.075,.11,'超过节拍：'+('、'.join(a['over_takt']) or '无')+'。改善优先核查瓶颈作业，而非要求所有工位同步提速。',fontsize=11)
        elif mode=='control_imr':
            metric(.055,'基线均值',f"{a['center']:.3f}",d['unit']);metric(.365,'单值越界点',str(len(a['individual_signals'])),'仅检测三倍标准差越界');metric(.675,'基线样本数',str(a['baseline_count']),'基线估限，后续点沿用同一控制限')
            for rect,title,values,x,cl,lo,hi,signals in [([.075,.40,.81,.18],'01  单值图 I',a['values'],list(range(1,len(a['values'])+1)),a['center'],a['lcl'],a['ucl'],a['individual_signals']),([.075,.12,.81,.16],'02  移动极差 MR',a['mr'],list(range(2,len(a['values'])+1)),a['mr_center'],0,a['mr_ucl'],a['mr_signals'])]:
                z=ax(rect,title,d['unit']);z.plot(x,values,'o-',ms=3.8,lw=1.2,color=p['accent'])
                for v,label in [(hi,'UCL'),(cl,'CL'),(lo,'LCL')]:
                    z.axhline(v,color=p['ink'] if label=='CL' else p['muted'],lw=.8,ls='-' if label=='CL' else '--');z.text(1.012,v,f'{label} {v:.3f}',transform=z.get_yaxis_transform(),fontsize=9,va='center')
                for i in signals:z.plot(i,values[x.index(i)],marker='s',mfc='none',mec=p['ink'],ms=9)
                if a['baseline_count']<len(a['values']):z.axvline(a['baseline_count']+.5,color=p['muted'],ls=':',lw=1)
                z.set_xlabel('时间顺序 / 样本号',fontsize=9)
        elif mode=='sales_review':
            metric(.055,'期间销售额',f"{a['total']:,.0f}",d['unit']);metric(.365,'目标达成率',f"{a['attainment']:.1%}",'同一期间与收入口径');metric(.675,'目标差额',f"{a['gap']:+,.0f}",d['unit'])
            z=ax([.075,.22,.44,.36],'01  月度实际与目标',d['unit']);xx=np.arange(len(d['months']))
            z.plot(xx,[r['actual'] for r in d['months']],'o-',color=p['accent'],label='实际');z.plot(xx,[r['target'] for r in d['months']],'s--',color=p['muted'],label='目标',ms=4);z.set_xticks(xx,[r['name'][5:]+'月' for r in d['months']]);z.set_ylim(bottom=0);z.legend(loc='upper left')
            z=ax([.61,.39,.315,.19],'02  区域销售额',d['unit']);bars(z,[r['name'] for r in d['regions']],[r['value'] for r in d['regions']])
            z=ax([.61,.105,.315,.16],'03  产品销售额',d['unit']);bars(z,[r['name'] for r in d['products']],[r['value'] for r in d['products']])
        elif mode=='sales_funnel':
            metric(.055,'同批起始线索',f"{d['stages'][0]['count']:,}",d['cohort']);metric(.365,'最终成交',f"{d['stages'][-1]['count']:,}",'逐级嵌套、同一批对象');metric(.675,'全链路转化率',f"{a['overall_conversion']:.1%}",'成交 ÷ 起始线索')
            z=ax([.16,.16,.58,.43],'01  转化与流失','');z.grid(False);rr=a['stages'];yy=list(range(len(rr)));z.barh(yy,[r['count'] for r in rr],color=p['accent'],height=.58);z.set_yticks(yy,[r['name'] for r in rr]);z.invert_yaxis();z.set_xlim(0,rr[0]['count']*1.30);z.set_xlabel('对象数')
            for i,r in enumerate(rr):z.text(r['count']+rr[0]['count']*.02,i,f"{r['count']:,}",va='center')
            fig.text(.79,.615,'相邻转化 / 流失',fontsize=11,color=p['muted'])
            for i,r in enumerate(rr):z.text(1.08,i,'起点' if i==0 else (f"{r['from_previous']:.1%} / {r['lost']:,}" if r['from_previous'] is not None else '无可转化对象'),transform=z.get_yaxis_transform(),va='center',fontsize=11)
        elif mode=='inventory_review':
            metric(.055,'期间库存周转',f"{a['turnover_for_period']:.2f} 次",f"{d['period_days']:g} 天期间；非年化");metric(.365,'平均库存天数',f"{a['inventory_days']:.1f} 天",'期间天数 × 平均成本库存 ÷ 销货成本');metric(.675,'期末成本库存',f"{a['ending_inventory_cost']:,.0f}",d['cost_unit'])
            z=ax([.075,.37,.85,.20],'01  数量结存核对','');z.set_axis_off()
            table=z.table(cellText=[[r['name'],r['unit'],f"{r['opening']:g}",f"{r['receipts']:g}",f"{r['issues']:g}",f"{r['closing']:g}"] for r in d['items']],colLabels=['物料','单位','期初','入库','出库','期末'],loc='center',cellLoc='center');table.auto_set_font_size(False);table.set_fontsize(11);table.scale(1,1.85)
            for (i,j),cell in table.get_celld().items():cell.set_facecolor(p['tint'] if i==0 else p['bg']);cell.set_edgecolor(p['line']);cell.set_linewidth(.6);cell.get_text().set_color(p['ink'])
            z=ax([.075,.115,.85,.13],'02  期末库存账龄（按成本）',d['cost_unit']);bars(z,[r['name'] for r in d['aging']],[r['value'] for r in d['aging']])
        elif mode=='energy_review':
            n=len(d['series']);xs=np.arange(len(d['months']))
            for i,(s,r) in enumerate(zip(d['series'],a['series'])):
                x=.075+i*(.86/n);width=.86/n-.07
                z=ax([x,.50,width,.23],s['name']+' · 总量',s['unit']);z.plot(xs,s['values'],'o-',color=p['accent'],ms=4);z.set_xticks(xs,[m[5:] for m in d['months']]);z.set_ylim(bottom=0)
                z=ax([x,.15,width,.22],s['name']+' · 单位产量消耗',s['unit']+'/'+d['production_unit']);vals=[row['value'] for row in a['rows'] if row['series']==s['name']];z.plot(xs,vals,'s-',color=p['ink'],ms=4);z.set_xticks(xs,[m[5:]+'月' for m in d['months']]);z.set_ylim(bottom=0)
                avg=r.get('aggregate_intensity');fig.text(x,.08,f"期间加权单耗：{avg:.4f}" if avg is not None else '期间加权单耗：不可计算',fontsize=11,color=p['accent'])
        fig.canvas.draw()
        renderer=fig.canvas.get_renderer();overflow=[];not_drawn=set()
        for z in axes:
            for axis,limits in [(z.xaxis,z.get_xlim()),(z.yaxis,z.get_ylim())]:
                low,high=sorted(limits)
                for tick in axis.get_major_ticks()+axis.get_minor_ticks():
                    if not low<=tick.get_loc()<=high:not_drawn.update([id(tick.label1),id(tick.label2)])
        for t in fig.findobj(match=matplotlib.text.Text):
            if not t.get_visible() or not t.get_text() or id(t) in not_drawn:continue
            bb=t.get_window_extent(renderer)
            if bb.width and bb.height and (bb.x0<-1 or bb.y0<-1 or bb.x1>fig.bbox.width+1 or bb.y1>fig.bbox.height+1):overflow.append(t.get_text())
        need(not overflow,'text outside canvas: '+repr(overflow))
        for ext in ('svg','pdf','png'):
            fig.savefig(out/(stem+'.'+ext),dpi=150);files.append(stem+'.'+ext)
        plt.close(fig)
        save('.qa.json',json.dumps({'canvas_text_overflow':overflow,'scope':'canvas bounds; visual overlap needs inspection'},ensure_ascii=False,indent=2))
    return {'files':files,'analysis':a}

def render_scene(s,dest,theme):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, FancyArrowPatch
    from render import label_lines, color
    p,heading,rc=mpl_style(theme)
    with plt.rc_context(rc):
        fig=plt.figure(figsize=(s.w/100,s.h/100),dpi=100)
        z=fig.add_axes([0,0,1,1]);z.set_xlim(0,s.w);z.set_ylim(s.h,0);z.set_axis_off()
        for n in s.nodes:
            if n['kind']!='text':z.add_patch(Rectangle((n['x'],n['y']),n['w'],n['h'],facecolor=color(s.palette,n.get('fill','panel')),edgecolor=color(s.palette,n.get('stroke','line')),lw=1))
        for e in s.edges:
            pts=e['points'];xs,ys=zip(*pts);z.plot(xs,ys,color=color(s.palette,e.get('tone','accent')),lw=e.get('width',1)*.72,ls='--' if e.get('dashed') else '-')
            if e.get('arrow',True):z.add_patch(FancyArrowPatch(pts[-2],pts[-1],arrowstyle='-|>',mutation_scale=12,color=color(s.palette,e.get('tone','accent'))))
        for n in s.nodes:
            lines=label_lines(n);total=sum(t[1]*1.35 for t in lines);align=n.get('align','center');x=n['x'] if align=='left' else n['x']+n['w']/2
            y=n['y']+(n['h']-total)/2+(lines[0][1] if lines else 0)
            for line,size,bold,tone in lines:
                z.text(x,y,line,ha=align,va='baseline',fontsize=size*.72,fontfamily=heading if size>=36 else rc['font.family'],fontweight='bold' if bold else 'normal',color=color(s.palette,tone));y+=size*1.35
        for ext in ('png','pdf'):fig.savefig(str(dest)+'.'+ext,dpi=100)
        plt.close(fig)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('--out',required=True);parser.add_argument('--theme',choices=list(PALETTES),default='warm');args=parser.parse_args()
    d=json.loads(Path(args.source).read_text());print(json.dumps(render(d,args.out,args.theme),ensure_ascii=False))

if __name__=='__main__':main()
