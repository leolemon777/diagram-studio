#!/usr/bin/env python3
"""Render reproducible statistical SVGs. Requires matplotlib and numpy.
No inferential interval is fabricated: error bounds must come from the input.
"""
import argparse,json,math,shutil
from pathlib import Path
def need(x,m):
    if not x:raise ValueError(m)
def numeric(values):
    return all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values)
def summarize(d):
    import numpy as np
    from scientific_extended import MODES,analyze
    if d['mode'] in MODES:return analyze(d)
    mode=d['mode'];meta={'mode':mode,'assumptions':d.get('assumptions',[])}
    if mode in ('boxplot','ecdf'):
        need(d.get('groups'),'groups required')
        for g in d['groups']:
            need(g.get('values') and numeric(g['values']),'finite raw samples required')
        meta['groups']=[]
        for g in d['groups']:
            a=np.asarray(g['values'],float);q=np.quantile(a,[.25,.5,.75]);iqr=q[2]-q[0]
            meta['groups'].append({'label':g['label'],'n':len(a),'quartiles':q.tolist(),'tukey_whiskers':[float(a[a>=q[0]-1.5*iqr].min()),float(a[a<=q[2]+1.5*iqr].max())]})
    elif mode=='errorbar':
        need(d.get('uncertainty_kind') in ('SD','SE','CI','provided interval'),'declare SD, SE, CI or provided interval')
        need(d.get('data'),'data required')
        for r in d['data']:need(numeric([r['estimate'],r['low'],r['high']]) and r['low']<=r['estimate']<=r['high'],'interval must contain estimate')
        meta['uncertainty_kind']=d['uncertainty_kind'];meta['interval_source']=d.get('interval_source','user-provided; calculation not verified')
    elif mode=='pareto':
        need(d.get('data') and numeric([r['value'] for r in d['data']]),'finite counts required')
        need(all(r['value']>=0 for r in d['data']) and sum(r['value'] for r in d['data'])>0,'nonnegative counts with positive total required')
        rows=sorted(d['data'],key=lambda r:-r['value']);total=sum(r['value'] for r in rows);acc=0;meta['sorted']=[]
        for r in rows:acc+=r['value'];meta['sorted'].append({**r,'cumulative_pct':100*acc/total})
    else:raise ValueError('supported modes: boxplot, ecdf, errorbar, pareto')
    return meta
def render(d,out,stem='figure'):
    from scientific_extended import MODES,render as extended_render
    if d['mode'] in MODES:return extended_render(d,out,stem)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib import font_manager
    meta=summarize(d);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    font='/System/Library/Fonts/STHeiti Light.ttc'
    if Path(font).exists():font_manager.fontManager.addfont(font);family=font_manager.FontProperties(fname=font).get_name()
    else:family='DejaVu Sans'
    bg=d.get('background','#F1EFEB');ink='#30302D';accent='#AC6046';muted='#6D6A63'
    plt.rcParams.update({'font.family':family,'font.size':12,'axes.labelcolor':ink,'text.color':ink,'xtick.color':muted,'ytick.color':muted,'axes.edgecolor':'#C9C3BA','svg.fonttype':'none','axes.unicode_minus':False})
    fig,ax=plt.subplots(figsize=(12.8,7.2));fig.patch.set_facecolor(bg);ax.set_facecolor(bg)
    fig.subplots_adjust(left=.12,right=.88,bottom=.19,top=.79)
    fig.text(.12,.91,d['title'],fontsize=22,weight='medium');fig.text(.12,.855,d.get('subtitle',''),fontsize=11,color=muted)
    mode=d['mode']
    if mode=='boxplot':
        groups=d['groups'];b=ax.boxplot([g['values'] for g in groups],tick_labels=[g['label'] for g in groups],patch_artist=True,widths=.45,whis=1.5)
        for patch in b['boxes']:patch.set(facecolor='#E9DDD2',edgecolor=accent)
        for item in b['medians']:item.set(color=ink,linewidth=2)
        for item in b['fliers']:item.set(marker='o',markerfacecolor='none',markeredgecolor=accent,markersize=5)
        for i,g in enumerate(groups,1):
            # Deterministic jitter reveals raw observations without inventing data.
            xs=i+np.linspace(-.12,.12,len(g['values']));ax.scatter(xs,g['values'],s=15,color=muted,alpha=.6,zorder=3)
    elif mode=='ecdf':
        for i,g in enumerate(d['groups']):
            x=np.sort(g['values']);y=np.arange(1,len(x)+1)/len(x)
            xx=np.r_[x[0],x];yy=np.r_[0,y];ax.step(xx,yy,where='post',label=g['label'],color=[accent,muted,ink][i%3],linestyle=['-','--',':'][i%3],linewidth=2)
        ax.set_ylim(0,1.04);ax.legend(frameon=False);ax.set_ylabel(d.get('ylabel','累计比例'))
    elif mode=='errorbar':
        rows=d['data'];x=np.arange(len(rows));y=np.array([r['estimate'] for r in rows]);lo=y-np.array([r['low'] for r in rows]);hi=np.array([r['high'] for r in rows])-y
        ax.errorbar(x,y,yerr=np.vstack([lo,hi]),fmt='o',capsize=6,color=accent,elinewidth=1.5);ax.set_xticks(x,[r['label'] for r in rows]);ax.margins(x=.18)
    elif mode=='pareto':
        rows=meta['sorted'];x=np.arange(len(rows));ax.bar(x,[r['value'] for r in rows],color=accent,width=.6);ax.set_xticks(x,[r['label'] for r in rows]);ax.set_ylim(bottom=0)
        ax2=ax.twinx();ax2.plot(x,[r['cumulative_pct'] for r in rows],marker='o',color=ink);ax2.set_ylim(0,105);ax2.set_ylabel('累计比例 (%)');ax2.spines[['top','left']].set_visible(False)
    if mode!='ecdf':ax.set_ylabel(d.get('ylabel','数值'))
    ax.set_xlabel(d.get('xlabel',''));ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',color='#D8D3C8',alpha=.65,linewidth=.7);ax.set_axisbelow(True)
    fig.text(.12,.055,d.get('footer','演示数据 · 源数据与计算摘要随图保留'),fontsize=10,color=muted)
    for ext in ['svg','png']:fig.savefig(out/(stem+'.'+ext),facecolor=bg,dpi=150)
    plt.close(fig)
    (out/(stem+'.data.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2))
    meta['matplotlib_version']=matplotlib.__version__;meta['scope']='可复算描述与绘制；不验证研究设计或用户提供区间的统计有效性'
    (out/(stem+'.calculation.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    return meta
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--out',required=True);a=p.parse_args();src=Path(a.input)
    try:print(json.dumps(render(json.loads(src.read_text()),a.out,src.stem),ensure_ascii=False))
    except (KeyError,ValueError,ImportError) as e:p.error(str(e))
if __name__=='__main__':main()
