#!/usr/bin/env python3
"""Checked Shewhart Xbar-R, p, np, c and u charts. Explicit frozen baseline.

NIST sources and input contract: references/spc.md. Optional WECO mean-chart rules; no capability,
exact discrete-tail, or automatic baseline-cleaning claims.
"""
import argparse
import csv
import json
import math
from pathlib import Path

MODES = ('xbar_r', 'xbar_s', 'ewma', 'cusum', 'p', 'np', 'c', 'u')
# NIST handbook pmc321 table, including its D4=2.115 for n=5.
FACTORS = {2:(1.880,0,3.267), 3:(1.023,0,2.575), 4:(.729,0,2.282),
           5:(.577,0,2.115), 6:(.483,0,2.004), 7:(.419,.076,1.924),
           8:(.373,.136,1.864), 9:(.337,.184,1.816), 10:(.308,.223,1.777)}

def require(condition, message):
    if not condition: raise ValueError(message)

def number(value, *, count=False, positive=False, signed=False):
    require(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value), 'finite numeric value required')
    require(signed or value >= 0, 'nonnegative value required')
    require(not positive or value > 0, 'positive denominator required')
    require(not count or int(value) == value, 'integer count required')
    return float(value)

def panel(name, values, center, lows, highs, unit):
    count=len(values)
    low=list(lows) if isinstance(lows,list) else [lows]*count
    high=list(highs) if isinstance(highs,list) else [highs]*count
    return dict(name=name, values=values, center=center, lcl=low, ucl=high, unit=unit,
                signals=[i+1 for i,(v,lo,hi) in enumerate(zip(values,low,high)) if v<lo or v>hi])

def analyze(d):
    mode=d.get('mode'); require(mode in MODES, 'unsupported SPC mode')
    for field in ('title','data_status','sampling_plan'):
        require(isinstance(d.get(field),str) and d[field].strip(), field+' required')
    rows=d.get('samples'); require(isinstance(rows,list) and 2<=len(rows)<=120, '2–120 chronological samples required')
    require(all(isinstance(r,dict) for r in rows), 'sample objects required')
    labels=[r.get('id') for r in rows]
    require(all(isinstance(v,str) and v.strip() for v in labels) and len(set(labels))==len(labels), 'unique nonempty sample IDs required')
    if mode in ('ewma','cusum'):
        from spc_memory import analyze_memory
        return analyze_memory(d,labels)
    baseline=d.get('baseline_count')
    require(isinstance(baseline,int) and not isinstance(baseline,bool) and 2<=baseline<=len(rows), 'explicit baseline_count in 2..N required')
    warnings=[]
    if baseline<20: warnings.append('基线少于20组：仅作试行估限，需继续采样和过程审查。')
    result=dict(mode=mode, baseline_count=baseline, sample_ids=labels, sampling_plan=d['sampling_plan'],
                data_status=d['data_status'], assumptions=d.get('assumptions',[]), warnings=warnings,
                rule='仅识别严格越过三西格玛控制限的点；控制限不是规格限；无越界不等于已证明稳定。', panels=[])
    if mode in ('xbar_r','xbar_s'):
        require(isinstance(d.get('unit'),str) and d['unit'].strip(), 'measurement unit required')
        require(all(isinstance(r.get('values'),list) for r in rows), 'raw subgroup values required')
        sizes=[len(r['values']) for r in rows]
        require(len(set(sizes))==1, 'constant subgroup size required')
        require(sizes[0] in FACTORS if mode=='xbar_r' else 2<=sizes[0]<=1000, 'Xbar-R size 2..10; Xbar-S size 2..1000 required')
        groups=[[number(v,signed=True) for v in r['values']] for r in rows]
        n=sizes[0]; means=[math.fsum(g)/n for g in groups]
        center=math.fsum(means[:baseline])/baseline
        if mode=='xbar_r':
            ranges=[max(g)-min(g) for g in groups]
            rbar=math.fsum(ranges[:baseline])/baseline
            require(rbar>0, 'zero baseline range: cannot estimate process variation')
            a2,d3,d4=FACTORS[n]
            result.update(subgroup_size=n, factors=dict(A2=a2,D3=d3,D4=d4),
                          panels=[panel('子组均值 X̄',means,center,center-a2*rbar,center+a2*rbar,d['unit']),
                                  panel('子组极差 R',ranges,rbar,d3*rbar,d4*rbar,d['unit'])])
            warnings.append('先检查极差图；合理子组、观测独立和组内近似正态假设需由业务核实。')
        else:
            deviations=[math.sqrt(math.fsum((v-m)**2 for v in g)/(n-1)) for g,m in zip(groups,means)]
            sbar=math.fsum(deviations[:baseline])/baseline
            require(sbar>0, 'zero baseline standard deviation: cannot estimate process variation')
            c4=math.sqrt(2/(n-1))*math.exp(math.lgamma(n/2)-math.lgamma((n-1)/2))
            a3=3/(c4*math.sqrt(n));delta=3*math.sqrt(max(0,1-c4*c4))/c4
            b3=max(0,1-delta);b4=1+delta
            result.update(subgroup_size=n,factors=dict(c4=c4,A3=a3,B3=b3,B4=b4),sigma_estimate=sbar/c4,
                          panels=[panel('子组均值 X̄',means,center,center-a3*sbar,center+a3*sbar,d['unit']),
                                  panel('子组标准差 S',deviations,sbar,b3*sbar,b4*sbar,d['unit'])])
            warnings.append('先检查标准差图；样本标准差采用n−1分母；合理子组及组内近似正态假设需核实。')
    else:
        numerator='nonconforming' if mode in ('p','np') else 'defects'
        counts=[number(r.get(numerator),count=True) for r in rows]
        if mode in ('p','np'):
            sizes=[number(r.get('inspected'),count=True,positive=True) for r in rows]
            require(all(c<=n for c,n in zip(counts,sizes)), 'nonconforming units cannot exceed inspected units')
            if mode=='np': require(len(set(sizes))==1, 'np requires constant sample size; use p for varying n')
            rate=sum(counts[:baseline])/sum(sizes[:baseline])
            require(0<rate<1, 'all-zero/all-one baseline cannot estimate binomial variation')
            if any(min(n*rate,n*(1-rate))<5 for n in sizes): warnings.append('存在低期望计数，正态三西格玛近似可能失真；本图未计算精确二项尾概率。')
            scale=sizes if mode=='np' else [1]*len(rows)
            values=counts if mode=='np' else [c/n for c,n in zip(counts,sizes)]
            lows=[max(0,rate-3*math.sqrt(rate*(1-rate)/n))*s for n,s in zip(sizes,scale)]
            highs=[min(1,rate+3*math.sqrt(rate*(1-rate)/n))*s for n,s in zip(sizes,scale)]
            center=rate*scale[0]
            title='不合格品比例 p' if mode=='p' else '不合格品数 np'
            unit='比例' if mode=='p' else '件'
            result.update(pooled_rate=rate, denominators=sizes)
        else:
            require(isinstance(d.get('exposure_unit'),str) and d['exposure_unit'].strip(), 'exposure_unit required')
            sizes=[number(r.get('exposure'),positive=True) for r in rows]
            if mode=='c': require(len(set(sizes))==1, 'c requires constant exposure; use u for varying exposure')
            rate=sum(counts[:baseline])/sum(sizes[:baseline])
            require(rate>0, 'zero baseline defects: cannot estimate Poisson variation')
            if any(rate*n<5 for n in sizes): warnings.append('存在期望缺陷数小于5的样本，三西格玛近似需谨慎；本图未计算精确泊松尾概率。')
            if mode=='c':
                center=sum(counts[:baseline])/baseline
                lows=[max(0,center-3*math.sqrt(center))]*len(rows)
                highs=[center+3*math.sqrt(center)]*len(rows);values=counts
                title='等检验量缺陷数 c';unit='个'
            else:
                center=rate; values=[c/n for c,n in zip(counts,sizes)]
                lows=[max(0,rate-3*math.sqrt(rate/n)) for n in sizes]
                highs=[rate+3*math.sqrt(rate/n) for n in sizes]
                title='单位检验量缺陷数 u';unit='个 / '+d['exposure_unit']
            result.update(pooled_rate=rate, denominators=sizes, exposure_unit=d['exposure_unit'])
            warnings.append('缺陷数允许同一件多缺陷；假设单位检验机会可比且缺陷近似独立、泊松离散度。')
        result['panels']=[panel(title,values,center,lows,highs,unit)]
    if any(any(i<=baseline for i in p['signals']) for p in result['panels']):
        warnings.append('基线自身有越界点：保留原基线并调查原因，不自动删点重算。')
    rules=d.get('rules','beyond_limits')
    require(rules in ('beyond_limits','weco'), 'rules must be beyond_limits or weco')
    if rules=='weco':
        require(mode in ('xbar_r','xbar_s'), 'WECO currently requires the approximately normal Xbar statistic; not R/S or discrete charts')
        require(d.get('rule_phase') in ('monitoring','all'), 'explicit rule_phase monitoring or all required')
        from spc_rules import weco
        chart=result['panels'][0]
        sigma=(chart['ucl'][0]-chart['center'])/3
        z=[(v-chart['center'])/sigma for v in chart['values']]
        start=baseline if d['rule_phase']=='monitoring' else 0
        events=weco(z[start:],offset=start)
        chart.update(standardized=z,rule_events=events,rule_signals=sorted({e['detected_at'] for e in events}))
        result.update(rules='weco',rule_phase=d['rule_phase'])
        result['rule']='X̄启用WECO四规则；圆环标记窗口结束时的检出点；离散度面板仅三西格玛越界。'
        warnings.append('联合规则增加误报；仅提示调查，不自动判定失控或删除数据。')
    return result

def native_drawio(fig, axes, texts, analysis, title):
    """Export native editable chart marks in the existing figure coordinates.

    This is a drawing, not a spreadsheet-linked live chart. The original input
    remains authoritative for numerical changes and regeneration.
    """
    import html
    import xml.etree.ElementTree as ET
    from matplotlib.colors import to_hex
    w,h=fig.bbox.width,fig.bbox.height
    root=ET.Element('mxfile',host='diagram-studio')
    page=ET.SubElement(root,'diagram',id='spc',name=title)
    model=ET.SubElement(page,'mxGraphModel',page='1',pageScale='1',pageWidth=str(w),pageHeight=str(h),background=to_hex(fig.get_facecolor()))
    cells=ET.SubElement(model,'root');ET.SubElement(cells,'mxCell',id='0');ET.SubElement(cells,'mxCell',id='1',parent='0')
    def line(id,coords,color,width=1,dashed=False):
        points=[(float(x),h-float(y)) for x,y in coords]
        if len(points)<2:return
        style=f'edgeStyle=none;endArrow=none;strokeColor={color};strokeWidth={width};rounded=0;'+('dashed=1;' if dashed else '')
        cell=ET.SubElement(cells,'mxCell',id=id,parent='1',edge='1',style=style)
        geo=ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
        for role,p in [('sourcePoint',points[0]),('targetPoint',points[-1])]:ET.SubElement(geo,'mxPoint',x=str(p[0]),y=str(p[1]),attrib={'as':role})
        if len(points)>2:
            arr=ET.SubElement(geo,'Array',attrib={'as':'points'})
            for x,y in points[1:-1]:ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
    for ai,ax in enumerate(axes):
        for j,artist in enumerate(ax.lines):
            coords=artist.get_transform().transform(artist.get_xydata())
            if artist.get_linestyle() not in ('None','none',''):
                line(f'chart-{ai}-line-{j}',coords,to_hex(artist.get_color()),artist.get_linewidth()*fig.dpi/72,artist.is_dashed())
            marker=artist.get_marker()
            if marker in ('o','s'):
                size=artist.get_markersize()*fig.dpi/72
                for k,(x,y) in enumerate(coords):
                    color=artist.get_markerfacecolor();fill='none' if color=='none' else to_hex(color)
                    cell=ET.SubElement(cells,'mxCell',id=f'chart-{ai}-line-{j}-mark-{k}',parent='1',vertex='1',
                        style=f'shape={"ellipse" if marker=="o" else "rectangle"};rounded=0;fillColor={fill};strokeColor={to_hex(artist.get_markeredgecolor())};')
                    ET.SubElement(cell,'mxGeometry',x=str(x-size/2),y=str(h-y-size/2),width=str(size),height=str(size),attrib={'as':'geometry'})
        for side in ('left','bottom'):
            spine=ax.spines[side]
            if spine.get_visible():line(f'chart-{ai}-{side}',spine.get_transform().transform(spine.get_path().vertices),to_hex(spine.get_edgecolor()),spine.get_linewidth())
        for axis_no,(axis,lim) in enumerate(((ax.xaxis,ax.get_xlim()),(ax.yaxis,ax.get_ylim()))):
            for ti,tick in enumerate(axis.get_major_ticks()):
                if not min(lim)<=tick.get_loc()<=max(lim):continue
                g=tick.gridline
                if g.get_visible():line(f'grid-{ai}-{axis_no}-{ti}',g.get_transform().transform(g.get_xydata()),to_hex(g.get_color()),g.get_linewidth())
    for i,(artist,box) in enumerate(texts):
        # Native rotated text uses its unrotated width/height about the same center.
        angle=float(artist.get_rotation())
        width,height=box.width+5,box.height+4
        if angle%180==90:width,height=height,width
        cx=(box.x0+box.x1)/2;cy=h-(box.y0+box.y1)/2
        align=artist.get_ha() if angle%180==0 else 'center'
        family=artist.get_fontfamily()[0]
        style=f'shape=text;html=1;whiteSpace=nowrap;align={align};verticalAlign=middle;spacing=0;fillColor=none;strokeColor=none;fontFamily={family};fontSize={artist.get_fontsize()*fig.dpi/72};fontColor={to_hex(artist.get_color())};rotation={-angle};'
        cell=ET.SubElement(cells,'mxCell',id=f'text-{i}',parent='1',vertex='1',value=html.escape(artist.get_text()).replace('\n','<br>'),style=style)
        ET.SubElement(cell,'mxGeometry',x=str(cx-width/2),y=str(cy-height/2),width=str(width),height=str(height),attrib={'as':'geometry'})
    # Legend line swatches are artist children rather than axes data lines.
    for ai,ax in enumerate(axes):
        legend=ax.get_legend()
        if legend:
            for j,artist in enumerate(legend.get_lines()):
                line(f'legend-{ai}-{j}',artist.get_transform().transform(artist.get_xydata()),to_hex(artist.get_color()),artist.get_linewidth(),artist.is_dashed())
    return ET.tostring(root,encoding='unicode',xml_declaration=True)

def render(d, output, theme='warm'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, PercentFormatter
    from editorial_style import mpl_style
    from style_family import load_system_fonts
    load_system_fonts()
    a=analyze(d); dest=Path(output);dest.mkdir(parents=True,exist_ok=True);stem=d['mode']
    p,heading,rc=mpl_style(theme)
    with plt.rc_context(rc):
        fig=plt.figure(figsize=(16,10))
        fig.text(.065,.95,'PROCESS MONITORING / 过程监测',fontsize=10,color=p['accent'])
        fig.text(.065,.891,d['title'],fontsize=27,fontfamily=heading,fontweight='normal')
        fig.text(.065,.843,d['sampling_plan'],fontsize=11,color=p['muted'])
        fig.text(.065,.802,a.get('header',f"基线：前 {a['baseline_count']} 组  ·  后续沿用基线  ·  空心方框：严格越界"),fontsize=11,color=p['accent'])
        charts=a['panels']; xx=list(range(1,len(d['samples'])+1)); axes=[]
        rects=[[.09,.31,.84,.40]] if len(charts)==1 else [[.09,.52,.84,.19],[.09,.22,.84,.19]]
        for zdata,rect in zip(charts,rects):
            z=fig.add_axes(rect);axes.append(z)
            z.set_title(zdata['name'],loc='left',fontsize=14,pad=12)
            z.plot(xx,zdata['values'],'o-',color=p['accent'],lw=1.25,ms=4,label=zdata.get('series_label','观测'))
            z.plot(xx,zdata['ucl'],'--',color=p['ink'],lw=1,label=zdata.get('limit_label','UCL / LCL'))
            z.plot(xx,zdata['lcl'],'--',color=p['ink'],lw=1)
            z.axhline(zdata['center'],color=p['muted'],lw=.9,label=zdata.get('center_label','CL'))
            for i in zdata['signals']: z.plot(i,zdata['values'][i-1],'s',mfc='none',mec=p['ink'],ms=10,mew=1.4)
            for i in zdata.get('rule_signals',[]): z.plot(i,zdata['values'][i-1],'o',mfc='none',mec=p['accent'],ms=14,mew=1.5)
            if 0<a['baseline_count']<len(xx): z.axvline(a['baseline_count']+.5,color=p['muted'],ls=':',lw=1)
            z.set_ylabel(zdata['unit']);z.set_xlabel('按采样时间排序的样本号')
            z.xaxis.set_major_locator(MaxNLocator(integer=True,nbins=15))
            z.grid(axis='y');z.set_axisbelow(True);z.margins(x=.015,y=.18)
            if d['mode']=='p': z.yaxis.set_major_formatter(PercentFormatter(1))
            z.legend(loc='lower right',bbox_to_anchor=(1,1.03),ncol=3,fontsize=9)
        footer=[d['data_status'],a['rule']]
        if a['warnings']: footer.append('注意：'+' '.join(a['warnings']))
        from render import wrap
        lines=[]
        for line in footer: lines.extend(wrap(line,1370,15))
        require(len(lines)<=6,'footer too long; shorten sampling notes')
        fig.text(.065,.038,'\n'.join(lines),fontsize=9,color=p['muted'],linespacing=1.7,va='bottom')
        import warnings
        with warnings.catch_warnings(record=True) as drawing_warnings:
            warnings.simplefilter('always')
            fig.canvas.draw()
        missing_glyphs=[str(w.message) for w in drawing_warnings if 'Glyph' in str(w.message) and 'missing' in str(w.message)]
        require(not missing_glyphs,'missing font glyphs: '+repr(missing_glyphs))
        renderer=fig.canvas.get_renderer();overflows=[];visible=[];excluded=set()
        for z in axes:
            for axis,lim in ((z.xaxis,z.get_xlim()),(z.yaxis,z.get_ylim())):
                for tick in axis.get_major_ticks()+axis.get_minor_ticks():
                    if not min(lim)<=tick.get_loc()<=max(lim): excluded.update((id(tick.label1),id(tick.label2)))
        for t in fig.findobj(match=matplotlib.text.Text):
            if not t.get_visible() or not t.get_text() or id(t) in excluded: continue
            box=t.get_window_extent(renderer)
            if box.width==0 or box.height==0: continue
            visible.append((t,box))
            if box.x0<0 or box.y0<0 or box.x1>fig.bbox.width or box.y1>fig.bbox.height: overflows.append(t.get_text())
        overlaps=[]
        for i,(ta,ba) in enumerate(visible):
            for tb,bb in visible[i+1:]:
                if min(ba.x1,bb.x1)-max(ba.x0,bb.x0)>1 and min(ba.y1,bb.y1)-max(ba.y0,bb.y0)>1: overlaps.append([ta.get_text(),tb.get_text()])
        require(not overflows and not overlaps, 'text layout failure: '+repr((overflows,overlaps)))
        (dest/(stem+'.drawio')).write_text(native_drawio(fig,axes,visible,a,d['title']))
        for ext in ('svg','png','pdf'): fig.savefig(dest/(stem+'.'+ext),dpi=150)
        plt.close(fig)
    (dest/(stem+'.input.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2))
    (dest/(stem+'.analysis.json')).write_text(json.dumps(a,ensure_ascii=False,indent=2,allow_nan=False))
    (dest/(stem+'.qa.json')).write_text(json.dumps(dict(text_overflow=overflows,text_overlap=overlaps,missing_glyphs=missing_glyphs,
        scope='Matplotlib text extents only; actual image and editable format reviews recorded separately'),ensure_ascii=False,indent=2))
    with (dest/(stem+'.csv')).open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['panel','sample_id','baseline','value','CL','LCL','UCL','beyond_limit'])
        for chart in a['panels']:
            for i,label in enumerate(a['sample_ids']):
                writer.writerow([chart['name'],label,i<a['baseline_count'],chart['values'][i],chart['center'],chart['lcl'][i],chart['ucl'][i],i+1 in chart['signals']])
    if a.get('rules')=='weco':
        with (dest/(stem+'.rules.csv')).open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['panel','rule','detected_at','sample_id','window_start','window_end','side','contributors'])
            for chart in a['panels']:
                for e in chart.get('rule_events',[]):
                    writer.writerow([chart['name'],e['rule'],e['detected_at'],a['sample_ids'][e['detected_at']-1],e['window_start'],e['window_end'],e['side'],';'.join(map(str,e['contributors']))])
    return a

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input');parser.add_argument('--out',required=True);parser.add_argument('--theme',default='warm')
    args=parser.parse_args();render(json.loads(Path(args.input).read_text()),args.out,args.theme)

if __name__=='__main__':main()
