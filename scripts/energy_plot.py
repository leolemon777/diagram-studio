#!/usr/bin/env python3
"""Deterministic energy and operational charts. Analyze with stdlib; render with Matplotlib.
Missing monthly observations are explicit nulls, never implicitly zero or interpolated.
"""
import argparse
import calendar
import csv
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

MODES = ('indexed','month_change','year_change','seasonal','cumulative','intensity',
         'target_gap','calendar','load_duration','rolling','cumulative_deviation','paired_comparison')

def need(ok, message):
    if not ok: raise ValueError(message)

def number(x, nullable=True):
    need((nullable and x is None) or (isinstance(x,(int,float)) and not isinstance(x,bool)
         and math.isfinite(x) and x >= 0), 'values must be finite nonnegative numbers or explicit null')
    return x

def vector(values, n):
    need(isinstance(values,list) and len(values)==n,'array length must match observations')
    return [number(v) for v in values]

def monthly(d):
    months=d['months']; need(isinstance(months,list) and len(months)>=2,'at least two months required')
    dates=[datetime.strptime(s,'%Y-%m') for s in months]
    need(all(t.strftime('%Y-%m')==s for t,s in zip(dates,months)),'months must use YYYY-MM')
    need(all((b.year-a.year)*12+b.month-a.month==1 for a,b in zip(dates,dates[1:])),
         'months must be consecutive and ordered; insert explicit null for missing observations')
    ss=d['series'];need(1<=len(ss)<=3,'one to three named series supported')
    need(len({s['name'] for s in ss})==len(ss),'series names must be unique')
    for s in ss:
        need(bool(s.get('name')) and bool(s.get('unit')),'series name and unit required')
        vector(s['values'],len(months))
    return dates,ss

def analyze(d):
    mode=d['mode'];need(mode in MODES,'unsupported energy mode')
    need(bool(d.get('data_status')),'data_status must declare actual/synthetic provenance')
    out={'mode':mode,'data_status':d['data_status'],'assumptions':d.get('assumptions',[]),'rows':[]}
    if mode=='calendar':
        y=d['year'];need(isinstance(y,int) and not isinstance(y,bool) and 1<=y<=9998,'valid year required')
        need(bool(d.get('unit')),'unit required');seen={}
        for r in d['records']:
            t=date.fromisoformat(r['date']);need(t.year==y and r['date'] not in seen,'wrong year or duplicate day')
            seen[r['date']]=number(r['value'])
        first=date(y,1,1);last=date(y,12,31);origin=first-timedelta(days=first.weekday())
        for i in range((last-first).days+1):
            t=first+timedelta(days=i);out['rows'].append({'date':t.isoformat(),'week':(t-origin).days//7,
                'weekday':t.weekday(),'value':seen.get(t.isoformat())})
        need(any(r['value'] is not None for r in out['rows']),'at least one observed day required')
        out.update({'missing_days':sum(r['value'] is None for r in out['rows']),
                    'weeks':(last-origin).days//7+1,'unit':d['unit']});return out
    if mode=='load_duration':
        dt=d['interval_hours'];number(dt,False);need(dt>0,'positive interval_hours required')
        rr=d['records'];need(len(rr)>=2,'at least two power intervals required')
        tt=[datetime.fromisoformat(r['timestamp'].replace('Z','+00:00')) for r in rr]
        need(all(t.tzinfo is not None for t in tt),'timestamps require timezone offset')
        tt=[t.astimezone(timezone.utc) for t in tt]
        need(all(abs((b-a).total_seconds()-dt*3600)<1e-6 for a,b in zip(tt,tt[1:])),
             'load-duration requires consecutive equal-duration interval-average power')
        vals=[number(r['kw'],False) for r in rr];rank=sorted(vals,reverse=True)
        out['rows']=[{'from_hour':i*dt,'to_hour':(i+1)*dt,'kw':v} for i,v in enumerate(rank)]
        out.update({'duration_hours':len(vals)*dt,'energy_kwh':sum(vals)*dt,'peak_kw':max(vals),
                    'load_factor':sum(vals)/len(vals)/max(vals) if max(vals)>0 else None,
                    'last_interval':'last timestamp is the START of one full interval'});return out
    if mode=='paired_comparison':
        need(bool(d.get('unit')) and len(d.get('period_labels',[]))==2,'unit and two period labels required')
        rr=d['pairs'];need(1<=len(rr)<=15 and len({r['id'] for r in rr})==len(rr),'unique paired IDs required; max 15')
        for r in rr:
            a=number(r['before'],False);b=number(r['after'],False)
            out['rows'].append({**r,'delta':b-a,'change_pct':(b/a-1)*100 if a else None})
        return out
    dates,ss=monthly(d);n=len(dates);out['series']=[];out['months']=d['months']
    if mode in ('seasonal','cumulative'):need(dates[0].month==1,'seasonal/year-to-date examples must start in January')
    if mode=='seasonal':need(len({t.year for t in dates})>=2,'seasonal comparison requires at least two calendar years')
    if mode=='year_change':need(n>=13,'year-on-year requires at least 13 months')
    if mode=='rolling':need(isinstance(d.get('window'),int) and not isinstance(d['window'],bool)
        and 2<=d['window']<=n,'window must be an integer between 2 and observation count')
    if mode=='intensity':
        production=vector(d['production'],n);need(bool(d.get('production_unit')),'production unit required')
    for s in ss:
        vals=s['values'];result=[];meta={'name':s['name'],'input_unit':s['unit']}
        target=vector(s.get('targets'),n) if mode in ('target_gap','cumulative_deviation') else None
        if mode=='indexed':need(vals[0] is not None and vals[0]>0,'positive observed first-month baseline required')
        running=0;complete=True
        for i,v in enumerate(vals):
            r={'month':d['months'][i],'series':s['name'],'input_value':v}
            if mode=='indexed':x=v/vals[0]*100 if v is not None else None
            elif mode in ('month_change','year_change'):
                lag=1 if mode=='month_change' else 12;base=vals[i-lag] if i>=lag else None
                x=(v/base-1)*100 if v is not None and base is not None and base>0 else None
                r.update({'reference_month':d['months'][i-lag] if i>=lag else None,'reference_value':base})
            elif mode=='seasonal':x=v
            elif mode=='cumulative':
                if dates[i].month==1:running=0;complete=True
                if v is None:complete=False
                if complete:running+=v
                x=running if complete else None
            elif mode=='intensity':
                denom=production[i];x=v/denom if v is not None and denom is not None and denom>0 else None
                r['production']=denom
            elif mode=='target_gap':
                t=target[i];x=(v/t-1)*100 if v is not None and t is not None and t>0 else None;r['target']=t
            elif mode=='rolling':
                w=d['window'];chunk=vals[max(0,i-w+1):i+1]
                x=sum(chunk)/w if i>=w-1 and all(z is not None for z in chunk) else None
            elif mode=='cumulative_deviation':
                t=target[i];r['target']=t
                if v is None or t is None:complete=False
                if complete:running+=v-t
                x=running if complete else None
            result.append(x);r['value']=x;out['rows'].append(r)
        need(any(v is not None for v in result),'no calculable observations for '+s['name'])
        meta.update({'values':result,'undefined_count':sum(v is None for v in result)})
        if mode=='intensity':
            valid=[i for i,x in enumerate(result) if x is not None]
            meta.update({'aggregate_intensity':sum(vals[i] for i in valid)/sum(production[i] for i in valid),
                         'aggregate_scope':'only periods with observed consumption and positive production',
                         'included_periods':len(valid),'excluded_periods':n-len(valid)})
        out['series'].append(meta)
    return out

def render(d,out,stem=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib import font_manager, colors
    from matplotlib.patches import Rectangle
    from matplotlib.ticker import FuncFormatter
    a=analyze(d);mode=d['mode'];out=Path(out);out.mkdir(parents=True,exist_ok=True);stem=stem or mode
    font=Path('/System/Library/Fonts/STHeiti Light.ttc')
    if font.exists():font_manager.fontManager.addfont(str(font));family=font_manager.FontProperties(fname=str(font)).get_name()
    else:family=['Noto Sans CJK SC','Microsoft YaHei','DejaVu Sans']
    bg=d.get('background','#F1EFEB');ink='#30302D';muted='#6D6A63';grid='#D8D3C8';palette=['#AC6046','#67685E','#8C7964']
    plt.rcParams.update({'font.family':family,'font.size':12,'text.color':ink,'axes.labelcolor':ink,
        'xtick.color':muted,'ytick.color':muted,'svg.fonttype':'none','pdf.fonttype':42,'axes.unicode_minus':False})
    fig=plt.figure(figsize=(16,9),dpi=100,facecolor=bg)
    fig.text(.065,.925,d['title'],fontsize=27);fig.text(.065,.871,d.get('subtitle',''),fontsize=12,color=muted)
    fig.text(.935,.93,d['data_status'],ha='right',fontsize=10,color=palette[0])
    fig.text(.065,.035,d.get('footer','输入与计算记录随图保存；方法假设见规则卡'),fontsize=10,color=muted)
    def axis(rect):
        ax=fig.add_axes(rect,facecolor=bg);ax.spines[['top','right','left']].set_visible(False)
        ax.spines['bottom'].set_color(grid);ax.grid(axis='y',color=grid,alpha=.6,linewidth=.7);ax.set_axisbelow(True)
        ax.tick_params(length=0,pad=9,labelsize=10);return ax
    if mode=='calendar':
        ax=axis([.075,.27,.86,.48]);lo=min(r['value'] for r in a['rows'] if r['value'] is not None)
        hi=max(r['value'] for r in a['rows'] if r['value'] is not None);hi=hi if hi>lo else lo+1
        norm=colors.Normalize(lo,hi);cmap=colors.LinearSegmentedColormap.from_list('warm',['#F4EEE7','#CF9C84','#98543E'])
        for r in a['rows']:
            ax.add_patch(Rectangle((r['week']-.46,r['weekday']-.46),.92,.92,
                facecolor='#D8D3C8' if r['value'] is None else cmap(norm(r['value'])),edgecolor=bg,lw=.5,
                hatch='///' if r['value'] is None else None))
        ticks=[r for r in a['rows'] if r['date'].endswith('-01')]
        ax.set_xticks([r['week'] for r in ticks],[str(int(r['date'][5:7]))+'月' for r in ticks])
        ax.set_yticks(range(7),['周一','周二','周三','周四','周五','周六','周日'])
        ax.set_xlim(-1,a['weeks']);ax.set_ylim(6.8,-.8);ax.grid(False);ax.spines['bottom'].set_visible(False)
        cax=fig.add_axes([.60,.16,.33,.017]);fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax,orientation='horizontal',label=d['unit'])
        fig.text(.075,.16,f"斜线格 = 缺失（{a['missing_days']} 天）；浅色实格含真实零值",fontsize=11,color=muted)
    elif mode=='load_duration':
        ax=axis([.10,.17,.81,.59]);rr=a['rows'];xx=[r['from_hour'] for r in rr]+[rr[-1]['to_hour']]
        yy=[r['kw'] for r in rr]+[rr[-1]['kw']]
        ax.step(xx,yy,where='post',color=palette[0],lw=2.5);ax.fill_between(xx,yy,step='post',color=palette[0],alpha=.08)
        ax.set_xlim(0,a['duration_hours']);ax.set_ylim(bottom=0);ax.set_xlabel('按负荷从高到低排列的累计时长（h）');ax.set_ylabel('区间平均功率（kW）')
        fig.text(.10,.795,f"观察时长 {a['duration_hours']:g} h   ·   积分电量 {a['energy_kwh']:,.1f} kWh",fontsize=12,color=muted)
    elif mode=='paired_comparison':
        ax=axis([.17,.17,.70,.60]);rr=a['rows'];yy=list(range(len(rr)))
        ax.hlines(yy,[r['before'] for r in rr],[r['after'] for r in rr],color=grid,lw=3)
        ax.scatter([r['before'] for r in rr],yy,s=60,color=palette[1],label=d['period_labels'][0],zorder=3)
        ax.scatter([r['after'] for r in rr],yy,s=65,color=palette[0],marker='D',label=d['period_labels'][1],zorder=3)
        ax.set_yticks(yy,[r['label'] for r in rr]);ax.invert_yaxis();ax.set_xlabel(d['unit']);ax.set_xlim(left=0)
        ax.legend(frameon=False,ncol=2,loc='lower left',bbox_to_anchor=(0,1.04))
        for y,r in zip(yy,rr):ax.annotate(f"{r['delta']:+g}",(max(r['before'],r['after']),y),xytext=(13,0),textcoords='offset points',va='center',fontsize=10,color=muted)
        ax.margins(x=.18,y=.16)
    else:
        dates=[datetime.strptime(s,'%Y-%m') for s in d['months']];ss=d['series']
        multi=mode!='indexed' and len(ss)>1
        need(len(ss)<=2 or not multi,'separate-unit layout supports up to two panels; split larger requests')
        axes=[axis([.11,.18,.72,.57])] if not multi else [axis([.11,.54,.77,.22]),axis([.11,.16,.77,.22])]
        for i,(s,res) in enumerate(zip(ss,a['series'])):
            ax=axes[i] if multi else axes[0];col=palette[i];v=np.array([np.nan if x is None else x for x in res['values']])
            if mode in ('seasonal','cumulative'):
                years=sorted({t.year for t in dates})
                for j,year in enumerate(years):
                    idx=[k for k,t in enumerate(dates) if t.year==year]
                    ax.plot([dates[k].month for k in idx],v[idx],marker='o',ms=4,lw=2,
                        linestyle=['-','--',':'][j%3],color=palette[j%3],label=str(year))
                ax.set_xticks(range(1,13),[str(m)+'月' for m in range(1,13)]);ax.set_xlim(.7,12.3)
                ax.legend(frameon=False,ncol=min(3,len(years)),fontsize=10)
            else:
                start=12 if mode=='year_change' else 0
                if mode in ('month_change','year_change','target_gap'):
                    ax.bar(dates[start:],v[start:],width=19,color=[col if x>=0 else '#8C8D83' for x in v[start:]],zorder=3)
                    ax.axhline(0,color=muted,lw=.9)
                else:
                    if mode=='rolling':ax.plot(dates,s['values'],color='#A9A296',lw=1.4,marker='.',label='月度原始值')
                    ax.plot(dates,v,color=col,marker='o',ms=4,lw=2.3,linestyle=['-','--',':'][i],
                            label=s['name'] if mode!='rolling' else f"后向 {d['window']} 月均值")
                    if mode=='rolling':ax.legend(frameon=False,fontsize=10)
                step=max(1,math.ceil((len(dates)-start)/12));ticks=list(range(start,len(dates),step))
                ax.set_xticks([dates[k] for k in ticks],[dates[k].strftime('%Y.%m') for k in ticks])
                ax.set_xlim(dates[start]-timedelta(days=17),dates[-1]+timedelta(days=30))
            unit='指数（首月 = 100）' if mode=='indexed' else ('变化率（%）' if mode in ('month_change','year_change') else ('偏差（%）' if mode=='target_gap' else s['unit']))
            if mode=='intensity':unit=s['unit']+'/'+d['production_unit']
            ax.set_ylabel(unit,fontsize=11)
            if mode=='indexed':
                ax.axhline(100,color=grid,ls='--',lw=1)
                if res['values'][-1] is not None:ax.annotate(f"{s['name']} {v[-1]:.1f}",(dates[-1],v[-1]),xytext=(12,0),textcoords='offset points',color=col,va='center',fontsize=11)
                ax.legend(frameon=False,ncol=len(ss),loc='upper left',fontsize=10)
            elif mode in ('cumulative','seasonal','intensity','rolling'):ax.set_ylim(bottom=0)
            elif mode=='cumulative_deviation':ax.axhline(0,color=muted,lw=.9)
            if multi:ax.set_title(s['name'],loc='left',pad=15,fontsize=14)
            elif mode!='indexed':ax.set_title(s['name'],loc='left',pad=20,fontsize=13)
            if mode=='intensity':fig.text(.83,.79 if i==0 else .41,f"有效期总耗量 / 总产量 = {res['aggregate_intensity']:.3f} {unit}",ha='right',fontsize=10,color=muted)
            if max(abs(x) for x in res['values'] if x is not None)>=1000:
                ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x:,.0f}'))
    fig.canvas.draw();renderer=fig.canvas.get_renderer();issues=[]
    for t in fig.findobj(matplotlib.text.Text):
        if not t.get_visible() or not t.get_text():continue
        # Matplotlib may retain inactive tick artists beyond the current limits.
        if t.axes is not None and t in t.axes.get_xticklabels()+t.axes.get_yticklabels():
            if not t.axes.bbox.overlaps(t.get_window_extent(renderer)):continue
        b=t.get_window_extent(renderer)
        if b.x0<-.5 or b.y0<-.5 or b.x1>1600.5 or b.y1>900.5:issues.append(t.get_text())
    a['layout_bounds_issues']=issues;a['matplotlib_version']=matplotlib.__version__
    for ext in ('svg','png','pdf'):fig.savefig(out/(stem+'.'+ext),facecolor=bg,dpi=120)
    plt.close(fig)
    (out/(stem+'.data.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2))
    (out/(stem+'.calculation.json')).write_text(json.dumps(a,ensure_ascii=False,indent=2,allow_nan=False))
    columns=list(dict.fromkeys(k for r in a['rows'] for k in r))
    with (out/(stem+'.csv')).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(a['rows'])
    return a

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--out',required=True);a=p.parse_args()
    d=json.loads(Path(a.input).read_text());r=render(d,a.out,Path(a.input).stem)
    print(json.dumps({'mode':r['mode'],'rows':len(r['rows']),'layout_bounds_issues':r['layout_bounds_issues']},ensure_ascii=False))
