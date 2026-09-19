"""Phase-II EWMA and standardized two-sided tabular CUSUM.

Explicit external reference distribution; no fitted-to-monitoring-data limits.
The reference sigma is the SD of each supplied value, not automatically the
SD of individual units when the supplied values are subgroup means.
"""
import math

def analyze_memory(d, labels):
    from spc import require, number, panel
    mode=d['mode']
    require(d.get('baseline_count',0)==0 and not isinstance(d.get('baseline_count',0),bool), 'memory charts use external reference; baseline_count must be omitted or zero')
    require(d.get('rules','beyond_limits')=='beyond_limits','WECO does not apply to correlated EWMA/CUSUM statistics')
    for field in ('unit','parameter_source','value_definition'):
        require(isinstance(d.get(field),str) and d[field].strip(),field+' required')
    mu=number(d.get('reference_mean'),signed=True);sigma=number(d.get('reference_sigma'),positive=True)
    values=[number(r.get('value'),signed=True) for r in d['samples']]
    require(all('values' not in r for r in d['samples']), 'supply scalar value with explicitly defined reference sigma')
    result=dict(mode=mode,baseline_count=0,sample_ids=labels,sampling_plan=d['sampling_plan'],data_status=d['data_status'],
                assumptions=d.get('assumptions',[]),reference_mean=mu,reference_sigma=sigma,
                parameter_source=d['parameter_source'],value_definition=d['value_definition'],raw_values=values,
                warnings=['参考参数需来自已审查的稳定过程；输入观测须近似独立且方差一致；不自动重置或重新估限。'])
    if mode=='ewma':
        weight=number(d.get('lambda'),positive=True);require(weight<=1,'lambda must be in (0,1]')
        limit=number(d.get('limit_multiplier'),positive=True)
        kind=d.get('limit_method');require(kind in ('steady','time_varying'),'explicit limit_method steady or time_varying required')
        state=mu;var=0;series=[];widths=[]
        for v in values:
            state=weight*v+(1-weight)*state
            var=weight**2*sigma**2+(1-weight)**2*var
            width=limit*math.sqrt(var if kind=='time_varying' else sigma**2*weight/(2-weight))
            require(math.isfinite(state) and math.isfinite(width),'EWMA numerical overflow')
            series.append(state);widths.append(width)
        result.update(parameters={'lambda':weight,'limit_multiplier':limit,'limit_method':kind,'initial_value':mu},
            rule='空心方框：EWMA统计量严格越界；不是原始单点越界，界限不是规格限。',
            header=f"外部参考：μ0={mu:g}，σ={sigma:g}；λ={weight:g}，L={limit:g}；"+('启动期变界限' if kind=='time_varying' else '稳态界限'),
            panels=[panel('指数加权均值 EWMA',series,mu,[mu-w for w in widths],[mu+w for w in widths],d['unit'])])
        result['panels'][0]['series_label']='EWMA'
    else:
        k=number(d.get('k'),positive=True);h=number(d.get('h'),positive=True)
        up=down=0;upper=[];lower=[];standard=[]
        for v in values:
            z=(v-mu)/sigma;up=max(0,up+z-k);down=max(0,down-z-k)
            require(all(math.isfinite(x) for x in (z,up,down)),'CUSUM numerical overflow')
            standard.append(z);upper.append(up);lower.append(down)
        result.update(parameters={'k':k,'h':h,'initial_upper':0,'initial_lower':0,'scale':'standardized'},standardized=standard,
            rule='空心方框：累计量严格超过h；上下偏移分别累计为正值；达到h不报警，报警后不自动重置。',
            header=f'外部参考：μ0={mu:g}，σ={sigma:g}；标准化参数k={k:g}，h={h:g}',
            panels=[panel('上偏移累计 C+',upper,0,0,h,'标准化累计量'),panel('下偏移累计 C−',lower,0,0,h,'标准化累计量')])
        for p in result['panels']:
            p.update(series_label='累计量',limit_label='报警阈值 h',center_label='零基准')
    return result
