#!/usr/bin/env python3
"""Reproducible research plots: checked data -> computation -> vector output.
Dependencies: numpy, matplotlib, scipy, scikit-learn, lifelines (survival only).
"""
from pathlib import Path
import json,math,csv,collections
import numpy as np
MODES={'violin','kde','histogram','regression','hexbin','correlation','paired','bland_altman','forest','survival','roc','pr','calibration','confusion','contour','quiver','dendrogram','upset','summary_table','ablation_table','qq','volcano','manhattan','small_multiples'}
INK='#30302D';ACCENT='#AC6046';GRAY='#6D6A63';BG='#F1EFEB';GRID='#D8D3C8'
def need(ok,message):
    if not ok:raise ValueError(message)
def vector(v,n=1):
    need(isinstance(v,(list,tuple)) and len(v)>=n,'not enough numeric observations')
    need(all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in v),'finite numeric observations required; handle missing explicitly')
    return np.asarray(v,dtype=float)
def matrix(v):
    need(isinstance(v,list) and len(v)>=2,'at least two rows required');a=np.asarray([vector(r) for r in v]);need(a.ndim==2,'rectangular matrix required');return a
def paired(d,x='x',y='y',n=2):
    a,b=vector(d[x],n),vector(d[y],n);need(len(a)==len(b),'paired lengths differ');return a,b
def groups(d,n=2):
    need(d.get('groups'),'groups required');labels=[g['label'] for g in d['groups']];need(len(set(labels))==len(labels),'group labels must be unique');return [(g['label'],vector(g['values'],n)) for g in d['groups']]
def binary(d,prob=False):
    y,s=paired(d,'y_true','scores');need(set(y)=={0.,1.},'both binary classes 0 and 1 required')
    if prob:need(np.all((s>=0)&(s<=1)),'probabilities must be in [0,1]')
    return y,s
def analyze(d):
    from scipy import stats
    m=d['mode'];need(m in MODES,'unsupported research mode');r={'mode':m,'assumptions':d.get('assumptions',[])}
    if m in ('violin','kde','histogram'):
        gs=groups(d);r['groups']=[]
        if m=='histogram':
            edges=vector(d['bin_edges'],2);need(np.all(np.diff(edges)>0),'bin edges must increase');r['bin_edges']=edges.tolist()
        for label,a in gs:
            z={'label':label,'n':len(a)}
            if m=='histogram':
                need(a.min()>=edges[0] and a.max()<=edges[-1],'bins must cover all observations');c,_=np.histogram(a,edges);z.update(counts=c.tolist(),density=(c/(len(a)*np.diff(edges))).tolist())
            else:
                need(np.ptp(a)>0,'KDE requires nonconstant data; use raw points for constant samples')
                bw=d.get('bandwidth','scott');need(bw in ('scott','silverman') if isinstance(bw,str) else isinstance(bw,(float,int)) and not isinstance(bw,bool) and bw>0,'invalid KDE bandwidth')
                kde=stats.gaussian_kde(a,bw_method=bw);sigma=float(np.sqrt(kde.covariance[0,0]));xx=np.linspace(a.min()-3*sigma,a.max()+3*sigma,220);z.update(x=xx.tolist(),density=kde(xx).tolist(),bandwidth_factor=float(kde.factor),kernel_sd=sigma,median=float(np.median(a)))
            r['groups'].append(z)
    elif m in ('regression','hexbin','paired','bland_altman'):
        x,y=paired(d,n=3 if m in ('regression','bland_altman') else 2);r.update(n=len(x))
        if m=='regression':
            need(np.ptp(x)>0 and np.ptp(y)>0,'regression requires nonconstant x and y');fit=stats.linregress(x,y);xx=np.linspace(x.min(),x.max(),120);yy=fit.intercept+fit.slope*xx;sse=float(np.sum((y-fit.intercept-fit.slope*x)**2));se=np.sqrt(sse/(len(x)-2));sxx=np.sum((x-x.mean())**2);margin=stats.t.ppf(.975,len(x)-2)*se*np.sqrt(1/len(x)+(xx-x.mean())**2/sxx)
            r.update(slope=float(fit.slope),intercept=float(fit.intercept),r_squared=float(fit.rvalue**2),line_x=xx.tolist(),line_y=yy.tolist(),low=(yy-margin).tolist(),high=(yy+margin).tolist(),interval='95% pointwise CI for mean response; OLS iid normal homoscedastic errors; not prediction interval')
        elif m=='hexbin':need(np.ptp(x)>0 and np.ptp(y)>0,'hexbin requires two-dimensional range');r['gridsize']=int(d.get('gridsize',18));need(3<=r['gridsize']<=100,'gridsize must be 3..100')
        else:
            ids=d.get('ids');need(ids is not None and len(ids)==len(x) and len(set(ids))==len(ids),'unique paired subject IDs required');diff=y-x;r.update(mean_difference=float(diff.mean()),sd_difference=float(diff.std(ddof=1)),difference=diff.tolist())
            if m=='bland_altman':r.update(pair_mean=((x+y)/2).tolist(),limits=[float(diff.mean()-1.96*diff.std(ddof=1)),float(diff.mean()+1.96*diff.std(ddof=1))],limits_definition='bias +/- 1.96 sample SD; approximate agreement limits, not CI; independent pairs, approximately normal differences')
    elif m=='correlation':
        a=matrix(d['values']);labels=d['labels'];need(a.shape[1]==len(labels) and len(labels)>=2,'one label per variable required');need(np.all(a.std(axis=0)>0),'constant variables have undefined correlation');method=d.get('method','pearson');need(method in ('pearson','spearman'),'unsupported correlation method')
        b=a if method=='pearson' else np.apply_along_axis(stats.rankdata,0,a);r.update(matrix=np.corrcoef(b,rowvar=False).tolist(),method=method,n=len(a),missing='complete input required; no implicit pairwise deletion')
    elif m=='forest':
        need(d.get('rows'),'effect rows required');need(d.get('interval_label'),'interval meaning must be named');scale=d.get('scale','linear');need(scale in ('linear','log'),'scale must be linear or log');ref=d.get('reference',1 if scale=='log' else 0);vector([ref]);r.update(scale=scale,reference=ref)
        for row in d['rows']:
            a=vector([row['low'],row['estimate'],row['high']]);need(a[0]<=a[1]<=a[2],'effect interval must contain estimate')
            if scale=='log':need(a.min()>0 and ref>0,'ratio plot requires positive bounds and reference')
        r['estimation']='input estimates and intervals; no automatic meta-analysis or study weights'
    elif m=='survival':
        from lifelines import KaplanMeierFitter
        r['groups']=[]
        need(d.get('groups'),'survival groups required')
        for g in d['groups']:
            t,e=paired(g,'durations','events');need(np.all(t>=0) and set(e)<= {0.,1.},'nonnegative times and binary event flags required');km=KaplanMeierFitter().fit(t,event_observed=e,label=g['label']);ci=km.confidence_interval_;timeline=km.survival_function_.index.to_numpy();et=km.event_table.reset_index()
            r['groups'].append({'label':g['label'],'n':len(t),'time':timeline.tolist(),'survival':km.survival_function_.iloc[:,0].tolist(),'low':ci.iloc[:,0].tolist(),'high':ci.iloc[:,1].tolist(),'censor_time':t[e==0].tolist(),'censor_survival':np.atleast_1d(km.predict(t[e==0])).tolist(),'event_table':et.to_dict(orient='records')})
        r['interval']='95% Greenwood exponential/log-log; right censoring only; assumes independent censoring; no group hypothesis test'
    elif m in ('roc','pr','calibration'):
        from sklearn import metrics
        y,s=binary(d,prob=m=='calibration');r.update(n=len(y),prevalence=float(y.mean()))
        if m=='roc':
            x,v,_=metrics.roc_curve(y,s);r.update(x=x.tolist(),y=v.tolist(),auc=float(metrics.roc_auc_score(y,s)))
        elif m=='pr':
            p,rec,_=metrics.precision_recall_curve(y,s);r.update(x=rec.tolist(),y=p.tolist(),average_precision=float(metrics.average_precision_score(y,s)))
        else:
            edges=vector(d.get('bin_edges',[0,.2,.4,.6,.8,1]),2);need(edges[0]==0 and edges[-1]==1 and np.all(np.diff(edges)>0),'calibration bins must partition [0,1]');idx=np.minimum(np.searchsorted(edges,s,side='right')-1,len(edges)-2);bins=[]
            for i in range(len(edges)-1):
                mask=idx==i;bins.append({'low':float(edges[i]),'high':float(edges[i+1]),'n':int(mask.sum()),'mean_prediction':float(s[mask].mean()) if mask.any() else None,'observed':float(y[mask].mean()) if mask.any() else None})
            r.update(bins=bins,brier=float(metrics.brier_score_loss(y,s)),bin_rule='left-closed, right-open; final bin includes 1; empty bins omitted from line')
    elif m=='confusion':
        from sklearn.metrics import confusion_matrix
        need(d.get('y_true') and len(d['y_true'])==len(d['y_pred']),'equal nonempty true and predicted labels required');labels=d['labels'];need(len(labels)==len(set(labels)) and set(d['y_true']+d['y_pred'])<=set(labels),'unique complete label set required');cm=confusion_matrix(d['y_true'],d['y_pred'],labels=labels);r.update(counts=cm.tolist(),n=int(cm.sum()),row_totals=cm.sum(axis=1).tolist())
    elif m in ('contour','quiver'):
        x,y=vector(d['x'],2),vector(d['y'],2);need(np.all(np.diff(x)>0) and np.all(np.diff(y)>0),'grid axes must increase')
        for key in (['z'] if m=='contour' else ['u','v']):need(matrix(d[key]).shape==(len(y),len(x)),key+' grid shape mismatch')
        if m=='quiver':need(isinstance(d.get('arrow_scale',1),(int,float)) and d.get('arrow_scale',1)>0,'positive arrow scale required')
        r.update(grid_shape=[len(y),len(x)],interpolation='none; supplied regular-grid observations',arrow_scale=d.get('arrow_scale',1))
    elif m=='dendrogram':
        from scipy.cluster.hierarchy import linkage
        a=matrix(d['values']);need(len(d['labels'])==len(a),'one label per observation required');method=d.get('method','average');metric=d.get('metric','euclidean');need(method in ('single','complete','average','weighted','ward'),'unsupported linkage method');need(metric in ('euclidean','cityblock','cosine'),'unsupported distance metric');need(method!='ward' or metric=='euclidean','Ward requires Euclidean distance');need(d.get('standardize') in (True,False),'declare standardize true/false')
        if d['standardize']:need(np.all(a.std(axis=0,ddof=1)>0),'cannot standardize constant variable');a=(a-a.mean(axis=0))/a.std(axis=0,ddof=1)
        z=linkage(a,method=method,metric=metric,optimal_ordering=True);need(np.isfinite(z).all(),'nonfinite distance');r.update(linkage=z.tolist(),metric=metric,method=method,standardize=d['standardize'])
    elif m=='upset':
        names=list(d['sets']);need(2<=len(names)<=6,'this compact layout supports 2..6 sets');sets={k:set(v) for k,v in d['sets'].items()};need(all(len(sets[k])==len(d['sets'][k]) for k in names),'duplicate element IDs within a set');universe=set().union(*sets.values());need(universe,'nonempty union required');counts=collections.Counter(tuple(int(x in sets[k]) for k in names) for x in universe);r.update(names=names,union_size=len(universe),set_sizes=[len(sets[k]) for k in names],intersections=[{'membership':list(k),'count':v} for k,v in sorted(counts.items(),key=lambda kv:(-kv[1],kv[0]))],definition='exclusive intersections: filled = included, unfilled = excluded; union only')
    elif m=='summary_table':
        r['rows']=[]
        for g in d['groups']:
            vals=g['values'];a=vector([v for v in vals if v is not None],2);q=np.quantile(a,[.25,.5,.75]);r['rows'].append({'group':g['label'],'n':len(a),'missing':len(vals)-len(a),'mean':float(a.mean()),'sd':float(a.std(ddof=1)),'median':float(q[1]),'q1':float(q[0]),'q3':float(q[2])})
        need(r['rows'],'summary groups required');r['definition']='sample SD ddof=1; linear quartiles; only explicit null values omitted and counted'
    elif m=='ablation_table':
        need(d.get('metrics') and d.get('rows'),'metrics and repeated-run rows required');r['rows']=[]
        for row in d['rows']:
            res={'name':row['name'],'metrics':{}}
            for met in d['metrics']:
                need(met['direction'] in ('higher','lower'),'declare metric direction');a=vector(row['runs'][met['key']],2);res['metrics'][met['key']]={'n':len(a),'mean':float(a.mean()),'sd':float(a.std(ddof=1))}
            r['rows'].append(res)
        r['definition']='mean +/- sample SD over explicitly supplied runs; highest mean is not significance; no p values inferred'
    elif m=='qq':
        a=vector(d['values'],3);need(np.ptp(a)>0,'probability plot requires variation');(x,y),(s,b,c)=stats.probplot(a,dist='norm');r.update(x=x.tolist(),y=y.tolist(),slope=float(s),intercept=float(b),definition='normal probability plot, Filliben plotting positions; visual diagnostic, not normality proof')
    elif m in ('volcano','manhattan'):
        need(d.get('rows'),'rows required');key=d.get('probability_key');need(key in ('p','q'),'declare p or q field');p=vector([x[key] for x in d['rows']]);need(np.all((p>0)&(p<=1)),'probabilities must be in (0,1]; do not silently clamp zero');alpha=d.get('threshold');need(isinstance(alpha,(int,float)) and 0<alpha<1,'explicit probability threshold required');r.update(probability_key=key,threshold=alpha,minus_log10=(-np.log10(p)).tolist(),probabilities='provided by input; no test or multiple-testing adjustment computed')
        if m=='volcano':
            effect=vector([x['log2fc'] for x in d['rows']]);cut=d.get('effect_threshold',1);need(cut>0,'positive effect threshold required');r.update(selected=((p<=alpha)&(np.abs(effect)>=cut)).tolist(),effect_threshold=cut)
        else:
            need(d.get('chromosome_order'),'explicit chromosome order required');order=d['chromosome_order'];need(len(order)==len(set(order)) and set(x['chromosome'] for x in d['rows'])<=set(order),'chromosome mapping incomplete');pos=vector([x['position'] for x in d['rows']]);need(np.all(pos>=0),'positions must be nonnegative');r['selected']=(p<=alpha).tolist()
    elif m=='small_multiples':
        gs=d['series'];need(1<=len(gs)<=6,'1..6 small multiples supported');r['series']=[]
        for g in gs:
            x,y=paired(g);need(np.all(np.diff(x)>0),'series time must increase');r['series'].append({'label':g['label'],'n':len(x)})
        r['scales']='shared x and y limits; numeric x, no smoothing'
    return r

def render(d,out,stem):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.colors import LinearSegmentedColormap
    from scipy.cluster.hierarchy import dendrogram
    r=analyze(d);out=Path(out);out.mkdir(parents=True,exist_ok=True);m=d['mode']
    font=d.get('font_path','/System/Library/Fonts/STHeiti Light.ttc');family='DejaVu Sans'
    if Path(font).is_file():font_manager.fontManager.addfont(font);family=font_manager.FontProperties(fname=font).get_name()
    bg=d.get('background',BG)
    plt.rcParams.update({'font.family':family,'font.size':11,'text.color':INK,'axes.labelcolor':INK,'xtick.color':GRAY,'ytick.color':GRAY,'axes.edgecolor':GRID,'svg.fonttype':'none','pdf.fonttype':42,'axes.unicode_minus':False})
    row_count=len(d.get('rows',d.get('groups',[]))) if m in ('forest','summary_table','ablation_table') else 0
    fig,ax=plt.subplots(figsize=(12.8,max(7.6,3+.45*row_count)));fig.patch.set_facecolor(bg);fig.subplots_adjust(left=.13,right=.88,bottom=.19,top=.77)
    fig.text(.1,.925,d['title'],fontsize=22,weight='medium');fig.text(.1,.867,d.get('subtitle',''),fontsize=11,color=GRAY)
    seq=LinearSegmentedColormap.from_list('warm_density',['#F6F3EF','#DBC6B7',ACCENT,'#58392F']);div=LinearSegmentedColormap.from_list('signed',['#5C7173',bg,ACCENT]);colors=[ACCENT,GRAY,'#5C7173'];lines=['-','--',':']
    def legend():ax.legend(frameon=False,fontsize=10,loc='best')
    if m in ('violin','kde','histogram'):
        for i,g in enumerate(r['groups']):
            c=colors[i%3]
            if m=='kde':ax.plot(g['x'],g['density'],label=g['label'],color=c,linestyle=lines[i%3]);ax.fill_between(g['x'],g['density'],color=c,alpha=.08)
            elif m=='histogram':ax.stairs(g['density'] if d.get('density',False) else g['counts'],r['bin_edges'],label=g['label'],color=c,linewidth=2)
            else:
                y=np.asarray(g['x']);v=np.asarray(g['density']);half=.34*v/v.max();ax.fill_betweenx(y,i-half,i+half,color=c,alpha=.2);a=np.asarray(d['groups'][i]['values']);j=np.random.default_rng(41+i).uniform(-.11,.11,len(a));ax.scatter(i+j,a,color=c,s=14,alpha=.6);ax.plot([i-.16,i+.16],[g['median']]*2,color=INK,lw=2)
        if m=='violin':ax.set_xticks(range(len(r['groups'])),[g['label']+'\nn='+str(g['n']) for g in r['groups']])
        else:legend()
    elif m=='regression':
        ax.scatter(d['x'],d['y'],color=GRAY,s=24,alpha=.7);ax.fill_between(r['line_x'],r['low'],r['high'],color=ACCENT,alpha=.16);ax.plot(r['line_x'],r['line_y'],color=ACCENT,label='OLS 均值曲线与 95% CI');legend();ax.text(.02,.96,f"n={r['n']}   R²={r['r_squared']:.3f}",transform=ax.transAxes,va='top')
    elif m=='hexbin':
        h=ax.hexbin(d['x'],d['y'],gridsize=r['gridsize'],mincnt=1,cmap=seq,linewidths=.1);fig.colorbar(h,ax=ax,pad=.025,label='每格观测数');r['cell_counts']=h.get_array().tolist();r['cell_count_sum']=int(np.sum(h.get_array()))
    elif m=='correlation':
        a=np.asarray(r['matrix']);h=ax.imshow(a,vmin=-1,vmax=1,cmap=div);fig.colorbar(h,ax=ax,pad=.035,label=r['method']+' r');ax.set_xticks(range(len(a)),d['labels']);ax.set_yticks(range(len(a)),d['labels'])
        for i in range(len(a)):
            for j in range(len(a)):ax.text(j,i,f'{a[i,j]:.2f}',ha='center',va='center',color='white' if abs(a[i,j])>.65 else INK)
    elif m=='paired':
        for a,b in zip(d['x'],d['y']):ax.plot([0,1],[a,b],color=GRAY,alpha=.35,lw=1);ax.scatter([0,1],[a,b],c=[GRAY,ACCENT],s=23,zorder=3)
        ax.set_xticks([0,1],d.get('conditions',['前','后']));ax.set_xlim(-.35,1.35);ax.text(.03,.96,f"配对 n={r['n']}    平均差={r['mean_difference']:.2f}",transform=ax.transAxes,va='top')
    elif m=='bland_altman':
        ax.scatter(r['pair_mean'],r['difference'],color=ACCENT,s=25)
        for value,label,style in [(r['mean_difference'],'偏倚','-'),(r['limits'][0],'下限','--'),(r['limits'][1],'上限','--')]:ax.axhline(value,color=GRAY,ls=style,lw=1.2);ax.text(1.01,value,f'{label} {value:.2f}',transform=ax.get_yaxis_transform(),va='center',fontsize=9)
    elif m=='forest':
        fig.subplots_adjust(left=.23,right=.78);rows=d['rows'];y=np.arange(len(rows));v=np.array([x['estimate'] for x in rows]);lo=v-np.array([x['low'] for x in rows]);hi=np.array([x['high'] for x in rows])-v;ax.errorbar(v,y,xerr=[lo,hi],fmt='s',color=ACCENT,capsize=4);ax.set_yticks(y,[x['label'] for x in rows]);ax.invert_yaxis();ax.axvline(r['reference'],ls='--',color=GRAY);ax.set_xscale(r['scale']);ax.set_ylim(len(rows)-.4,-.6)
        if r['scale']=='log':
            from matplotlib.ticker import FixedLocator,FuncFormatter,NullLocator
            left,right=ax.get_xlim();ticks=[v*10**e for e in range(math.floor(math.log10(left)),math.ceil(math.log10(right))+1) for v in (1,1.5,2,3,4,5,6,8) if left<=v*10**e<=right]
            if len(ticks)>10:ticks=np.geomspace(left,right,6)
            ax.xaxis.set_major_locator(FixedLocator(ticks));ax.xaxis.set_minor_locator(NullLocator());ax.xaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:g}'))
        for i,row in enumerate(rows):ax.text(1.03,i,f"{row['estimate']:.2f} [{row['low']:.2f}, {row['high']:.2f}]",transform=ax.get_yaxis_transform(),fontsize=9,va='center')
    elif m=='survival':
        fig.subplots_adjust(bottom=.31)
        for i,g in enumerate(r['groups']):
            ax.step(g['time'],g['survival'],where='post',color=colors[i%3],ls=lines[i%3],label=g['label']);ax.fill_between(g['time'],g['low'],g['high'],step='post',color=colors[i%3],alpha=.09);ax.scatter(g['censor_time'],g['censor_survival'],marker='+',color=colors[i%3],s=30)
        ax.set_ylim(-.02,1.04);legend();maxt=max(max(g['durations']) for g in d['groups']);ticks=np.linspace(0,maxt,5);ax.set_xticks(ticks);xmax=maxt*1.03;ax.set_xlim(0,xmax)
        risk=fig.add_axes([.13,.12,.75,.105]);risk.set_xlim(0,xmax);risk.set_ylim(-.7,len(d['groups'])-.3);risk.axis('off')
        for i,g in enumerate(d['groups']):
            yy=len(d['groups'])-1-i;risk.text(-.02,yy,g['label'],transform=risk.get_yaxis_transform(),ha='right',va='center',fontsize=9)
            for t in ticks:risk.text(t,yy,str(sum(v>=t for v in g['durations'])),ha='center',va='center',fontsize=10)
        fig.text(.13,.235,'风险集人数（时点开始前）',fontsize=10,color=GRAY)
    elif m in ('roc','pr'):
        if m=='roc':ax.plot([0,1],[0,1],ls='--',color=GRID);ax.plot(r['x'],r['y'],color=ACCENT,lw=2,label=f"AUROC = {r['auc']:.3f}")
        else:ax.axhline(r['prevalence'],ls='--',color=GRAY,label=f"阳性比例 {r['prevalence']:.2f}");ax.step(r['x'],r['y'],where='post',color=ACCENT,lw=2,label=f"AP = {r['average_precision']:.3f}")
        ax.set(xlim=(-.02,1.02),ylim=(-.02,1.05));legend()
    elif m=='calibration':
        bins=[b for b in r['bins'] if b['n']];ax.plot([0,1],[0,1],ls='--',color=GRAY,label='理想校准');ax.plot([b['mean_prediction'] for b in bins],[b['observed'] for b in bins],'-o',color=ACCENT,label=f"Brier = {r['brier']:.3f}")
        for b in bins:ax.annotate('n='+str(b['n']),(b['mean_prediction'],b['observed']),xytext=(6,7),textcoords='offset points',fontsize=9)
        ax.set(xlim=(-.02,1.05),ylim=(-.02,1.09));legend()
    elif m=='confusion':
        a=np.asarray(r['counts']);s=np.asarray(r['row_totals']);pct=np.divide(a,s[:,None],out=np.zeros_like(a,dtype=float),where=s[:,None]!=0);ax.imshow(pct,cmap=seq,vmin=0,vmax=1);ax.set_xticks(range(len(a)),d['labels']);ax.set_yticks(range(len(a)),d['labels'])
        for i in range(len(a)):
            for j in range(len(a)):ax.text(j,i,str(a[i,j])+('\n'+f'{pct[i,j]:.0%}' if s[i] else '\n无样本'),ha='center',va='center',color='white' if pct[i,j]>.6 else INK)
    elif m=='contour':
        z=np.asarray(d['z']);h=ax.contourf(d['x'],d['y'],z,levels=12,cmap=seq);cont=ax.contour(d['x'],d['y'],z,levels=6,colors=GRAY,linewidths=.55);ax.clabel(cont,fontsize=8);fig.colorbar(h,ax=ax,label=d.get('zlabel','标量值'),pad=.025)
    elif m=='quiver':
        xx,yy=np.meshgrid(d['x'],d['y']);h=ax.quiver(xx,yy,d['u'],d['v'],color=ACCENT,angles='xy',scale_units='xy',scale=r['arrow_scale'],width=.0035);ax.quiverkey(h,.8,1.04,1,'单位向量',labelpos='E');ax.set_aspect('equal')
    elif m=='dendrogram':
        dendrogram(np.asarray(r['linkage']),labels=d['labels'],ax=ax,link_color_func=lambda _:GRAY,leaf_font_size=11);ax.set_ylabel('链接距离')
    elif m=='upset':
        ax.remove();gs=fig.add_gridspec(2,2,left=.15,right=.91,bottom=.2,top=.77,width_ratios=[1,3],height_ratios=[2,1.5],hspace=.12,wspace=.2);bar=fig.add_subplot(gs[0,1]);dots=fig.add_subplot(gs[1,1]);sizes=fig.add_subplot(gs[1,0],sharey=dots);entries=r['intersections'];idx=np.arange(len(entries));bar.bar(idx,[e['count'] for e in entries],color=ACCENT);bar.set_ylabel('互斥交集大小');bar.set_xticks([]);dots.set_yticks(range(len(r['names'])),r['names']);sizes.barh(range(len(r['names'])),r['set_sizes'],color=GRAY);sizes.invert_xaxis();sizes.tick_params(axis='y',labelleft=False);sizes.set_xlabel('集合大小')
        for i,e in enumerate(entries):
            rows=[j for j,x in enumerate(e['membership']) if x];dots.scatter([i]*len(r['names']),range(len(r['names'])),color=GRID,s=28);dots.scatter([i]*len(rows),rows,color=INK,s=35)
            if len(rows)>1:dots.plot([i,i],[min(rows),max(rows)],color=INK,lw=1.4)
        dots.set_xticks([]);dots.set_xlim(-.6,len(entries)-.4);bar.set_xlim(dots.get_xlim());dots.invert_yaxis();ax=bar
    elif m in ('summary_table','ablation_table'):
        ax.axis('off')
        if m=='summary_table':
            cols=['分组','n','缺失','均值 ± SD','中位数 [Q1, Q3]'];rows=[[x['group'],str(x['n']),str(x['missing']),f"{x['mean']:.2f} ± {x['sd']:.2f}",f"{x['median']:.2f} [{x['q1']:.2f}, {x['q3']:.2f}]"] for x in r['rows']]
        else:
            cols=['实验配置']+[x['label']+(' ↑' if x['direction']=='higher' else ' ↓') for x in d['metrics']];rows=[[x['name']]+[f"{x['metrics'][k['key']]['mean']:.3f} ± {x['metrics'][k['key']]['sd']:.3f}\nn={x['metrics'][k['key']]['n']}" for k in d['metrics']] for x in r['rows']]
        table=ax.table(cellText=rows,colLabels=cols,loc='center',cellLoc='center',bbox=[-.04,.18,1.09,.72]);table.auto_set_font_size(False);table.set_fontsize(12)
        for (i,j),cell in table.get_celld().items():cell.set_facecolor(bg);cell.set_edgecolor(GRAY);cell.visible_edges='TB' if i==0 else 'B' if i==len(rows) else '';cell.set_linewidth(1.1);cell.get_text().set_color(INK)
        with (out/(stem+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(cols);w.writerows(rows)
        r['table_columns']=cols;r['table_rows']=rows
    elif m=='qq':
        ax.scatter(r['x'],r['y'],color=ACCENT,s=22);x=np.asarray(r['x']);ax.plot(x,r['slope']*x+r['intercept'],color=GRAY,ls='--')
    elif m=='volcano':
        x=np.array([v['log2fc'] for v in d['rows']]);y=np.asarray(r['minus_log10']);sel=np.array(r['selected']);ax.scatter(x[~sel],y[~sel],color=GRAY,alpha=.45,s=18);ax.scatter(x[sel],y[sel],color=ACCENT,s=24);ax.axhline(-np.log10(r['threshold']),color=GRAY,ls='--');ax.axvline(r['effect_threshold'],color=GRID,ls='--');ax.axvline(-r['effect_threshold'],color=GRID,ls='--')
        for i,row in enumerate(d['rows']):
            if row.get('label'):ax.annotate(row['label'],(x[i],y[i]),xytext=(4,5),textcoords='offset points',fontsize=8)
    elif m=='manhattan':
        offset=0;ticks=[];names=[];span=max(x['position'] for x in d['rows']);gap=max(1,.035*span)
        for i,c in enumerate(d['chromosome_order']):
            idx=[j for j,x in enumerate(d['rows']) if x['chromosome']==c]
            if not idx:continue
            pos=np.array([d['rows'][j]['position'] for j in idx]);xx=offset+pos;yy=np.asarray(r['minus_log10'])[idx];ax.scatter(xx,yy,color=[GRAY,ACCENT][i%2],s=18);ticks.append((xx.min()+xx.max())/2);names.append(c);offset=xx.max()+gap
        ax.set_xticks(ticks,names);ax.axhline(-np.log10(r['threshold']),color=GRAY,ls='--')
    elif m=='small_multiples':
        ax.remove();n=len(d['series']);axes=fig.subplots(2 if n>3 else 1,3 if n>3 else n,squeeze=False,sharex=True,sharey=True).ravel();fig.subplots_adjust(left=.1,right=.92,wspace=.25,hspace=.5)
        for i,(a,g) in enumerate(zip(axes,d['series'])):a.plot(g['x'],g['y'],color=ACCENT,lw=1.7);a.set_title(g['label'],fontsize=12);a.set_xlabel(d.get('xlabel',''));a.set_ylabel(d.get('ylabel',''))
        for a in axes[n:]:a.set_visible(False)
        ax=axes[0]
    for a in fig.axes:
        a.set_facecolor(bg)
        if a.get_visible() and a.axison and m not in ('correlation','confusion','summary_table','ablation_table','contour','quiver','upset'):
            a.spines[['top','right']].set_visible(False);a.grid(axis='y',color=GRID,alpha=.6,lw=.7);a.set_axisbelow(True)
    if m not in ('summary_table','ablation_table','upset','small_multiples'):
        ax.set_xlabel(d.get('xlabel',''));ax.set_ylabel(d.get('ylabel',ax.get_ylabel()))
    fig.text(.1,.045,d.get('footer','原创演示数据 · 不代表实际研究结论'),fontsize=9,color=GRAY)
    fig.canvas.draw();renderer=fig.canvas.get_renderer();bounds=fig.bbox;r['layout_issues']=[]
    # Axis objects retain out-of-view ticks that the draw pass does not paint.
    unused_ticks=set()
    for a in fig.axes:
        for axis,limits in ((a.xaxis,a.get_xlim()),(a.yaxis,a.get_ylim())):
            lo,hi=sorted(limits)
            for tick in axis.get_major_ticks()+axis.get_minor_ticks():
                if not lo-1e-9<=tick.get_loc()<=hi+1e-9:unused_ticks.update((id(tick.label1),id(tick.label2)))
    for t in fig.findobj(match=lambda o: isinstance(o,matplotlib.text.Text)):
        if not t.get_visible() or not t.get_text().strip() or id(t) in unused_ticks:continue
        bb=t.get_window_extent(renderer)
        if bb.x0<-.5 or bb.y0<-.5 or bb.x1>bounds.x1+.5 or bb.y1>bounds.y1+.5:r['layout_issues'].append({'text':t.get_text(),'bbox':[round(float(v),1) for v in (bb.x0,bb.y0,bb.x1,bb.y1)]})
    for ext in ('svg','png','pdf'):fig.savefig(out/(stem+'.'+ext),facecolor=bg,dpi=150)
    plt.close(fig)
    import importlib.metadata
    r['versions']={}
    for pkg in ('matplotlib','numpy','scipy','scikit-learn','lifelines'):
        try:r['versions'][pkg]=importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:r['versions'][pkg]='not installed'
    r['scope']='calculation and display; assumptions and research validity require task-specific review'
    (out/(stem+'.data.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False))
    (out/(stem+'.calculation.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False));return r
