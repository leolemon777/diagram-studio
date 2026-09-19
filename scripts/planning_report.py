#!/usr/bin/env python3
"""Validate and render gauges, report tables, sales tables, schedules and calendars."""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import math
import textwrap
from collections import defaultdict
from pathlib import Path


INK = '#30302D'
MUTED = '#6D6A63'
BG = '#F1EFEB'
PAPER = '#FAF9F6'
GRID = '#D8D3C8'
GREEN = '#58705A'
BLUE = '#657487'
AMBER = '#C1965B'
RED = '#A65448'
COLORS = {'green': GREEN, 'blue': BLUE, 'amber': AMBER, 'red': RED}


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _unique(values, message):
    _need(len(values) == len(set(values)), message)


def _base(data, mode):
    _need(data.get('mode') == mode, f'mode must be {mode}')
    _need(isinstance(data.get('title'), str) and data['title'].strip(), 'title required')


def _gauge(data):
    _base(data, 'gauge')
    metric = data.get('metric', {})
    _need(metric.get('label') and metric.get('unit'), 'gauge metric label and unit required')
    _need(all(_finite(metric.get(key)) for key in ('min', 'max', 'value', 'target')), 'gauge range, value and target must be finite')
    low, high = float(metric['min']), float(metric['max'])
    _need(low < high and low <= metric['value'] <= high and low <= metric['target'] <= high, 'gauge value and target must be inside a valid range')
    _need(metric.get('direction') in {'higher-better', 'lower-better'}, 'gauge direction required')
    thresholds = data.get('thresholds')
    _need(isinstance(thresholds, list) and thresholds, 'gauge thresholds required')
    ordered = sorted(thresholds, key=lambda row: row.get('min', math.inf))
    cursor = low
    for row in ordered:
        _need(row.get('label') and row.get('color') in COLORS and row.get('basis'), 'each threshold needs label, color and basis')
        _need(_finite(row.get('min')) and _finite(row.get('max')) and row['min'] < row['max'], 'threshold bounds must be finite and increasing')
        _need(math.isclose(float(row['min']), cursor, abs_tol=1e-9), 'gauge thresholds must be contiguous without gaps or overlap')
        cursor = float(row['max'])
    _need(math.isclose(cursor, high, abs_tol=1e-9), 'gauge thresholds must cover the declared range')
    fraction = lambda value: (float(value) - low) / (high - low)
    target_met = metric['value'] >= metric['target'] if metric['direction'] == 'higher-better' else metric['value'] <= metric['target']
    return {'mode': 'gauge', 'range': [low, high], 'value_fraction': fraction(metric['value']),
            'target_fraction': fraction(metric['target']), 'target_gap': float(metric['value']) - float(metric['target']),
            'target_met': target_met, 'thresholds': len(ordered), 'threshold_coverage': 'passed'}


def _columns(data):
    columns = data.get('columns')
    _need(isinstance(columns, list) and columns, 'columns required')
    ids = [column.get('id') for column in columns]
    _need(all(ids), 'each column needs id'); _unique(ids, 'column ids must be unique')
    for column in columns:
        _need(column.get('label') and column.get('type') in {'text', 'integer', 'number'}, 'column label and type required')
        if column['type'] != 'text':
            _need(isinstance(column.get('unit'), str) and column['unit'].strip(), 'numeric columns require units')
    return columns


def _report(data):
    _base(data, 'report-table')
    columns = _columns(data); ids = [column['id'] for column in columns]
    records = data.get('records')
    _need(isinstance(records, list) and records, 'report records required')
    record_ids = [row.get('id') for row in records]
    _need(all(record_ids), 'report record ids required'); _unique(record_ids, 'report record ids must be unique')
    for row in records:
        _need(set(row.get('values', {})) == set(ids), 'each report record must cover every column exactly once')
        for column in columns:
            value = row['values'][column['id']]
            if column['type'] == 'integer': _need(isinstance(value, int) and not isinstance(value, bool), 'integer report value required')
            elif column['type'] == 'number': _need(_finite(value), 'finite numeric report value required')
            else: _need(isinstance(value, str) and value.strip(), 'nonempty report text required')
    summaries = data.get('summaries')
    _need(isinstance(summaries, list) and summaries, 'report summaries required')
    result = {}
    numeric = {column['id']: column for column in columns if column['type'] != 'text'}
    for summary in summaries:
        column = summary.get('column'); operation = summary.get('operation')
        _need(column in numeric and operation in {'sum', 'average', 'min', 'max'}, 'summary must reference a numeric column and supported operation')
        values = [row['values'][column] for row in records]
        result[f'{column}:{operation}'] = {'sum': sum(values), 'average': sum(values) / len(values), 'min': min(values), 'max': max(values)}[operation]
    return {'mode': 'report-table', 'records': len(records), 'columns': len(columns), 'summaries': result,
            'numeric_units': {item: numeric[item]['unit'] for item in numeric}, 'detail_summary_separation': 'passed'}


def _sales(data):
    _base(data, 'sales-table')
    _need(data.get('currency') and data.get('period'), 'sales currency and period required')
    records = data.get('records')
    _need(isinstance(records, list) and records, 'sales records required')
    ids = [row.get('id') for row in records]; _need(all(ids), 'sales record ids required'); _unique(ids, 'sales record ids must be unique')
    grain = []
    for row in records:
        _need(all(isinstance(row.get(key), str) and row[key].strip() for key in ('region', 'product')), 'sales region and product required')
        _need(isinstance(row.get('orders'), int) and row['orders'] >= 0, 'orders must be nonnegative integers')
        _need(isinstance(row.get('units'), int) and row['units'] >= 0, 'units must be nonnegative integers')
        _need(_finite(row.get('revenue')) and row['revenue'] >= 0, 'revenue must be finite and nonnegative')
        grain.append((row['region'], row['product']))
    _unique(grain, 'sales region-product grain must be unique')
    subtotals = defaultdict(lambda: {'orders': 0, 'units': 0, 'revenue': 0.0})
    total = {'orders': 0, 'units': 0, 'revenue': 0.0}
    for row in records:
        for key in total:
            subtotals[row['region']][key] += row[key]; total[key] += row[key]
    return {'mode': 'sales-table', 'records': len(records), 'grain_unique': 'passed',
            'subtotals': dict(subtotals), 'grand_total': total, 'subtotal_double_counting': 'prevented; totals use leaf records only'}


def _parse_local(value):
    parsed = dt.datetime.fromisoformat(value)
    _need(parsed.tzinfo is None, 'schedule timestamps must be local wall time; timezone is declared separately')
    return parsed


def _schedule(data):
    _base(data, 'schedule')
    _need(isinstance(data.get('timezone'), str) and '/' in data['timezone'], 'IANA timezone label required')
    activities = data.get('activities')
    _need(isinstance(activities, list) and activities, 'schedule activities required')
    ids = [row.get('id') for row in activities]; _need(all(ids), 'schedule activity ids required'); _unique(ids, 'schedule activity ids must be unique')
    enriched = []
    for row in activities:
        _need(all(isinstance(row.get(key), str) and row[key].strip() for key in ('label', 'owner', 'start', 'end')), 'schedule label, owner, start and end required')
        start, end = _parse_local(row['start']), _parse_local(row['end'])
        _need(start < end, 'schedule activity end must be after start')
        enriched.append({**row, 'start_dt': start, 'end_dt': end, 'duration_minutes': int((end - start).total_seconds() / 60)})
    conflicts = []
    gaps = []
    for owner in sorted({row['owner'] for row in enriched}):
        rows = sorted((row for row in enriched if row['owner'] == owner), key=lambda row: row['start_dt'])
        for left, right in zip(rows, rows[1:]):
            if right['start_dt'] < left['end_dt']:
                conflicts.append({'owner': owner, 'activities': [left['id'], right['id']], 'overlap_minutes': int((left['end_dt'] - right['start_dt']).total_seconds() / 60)})
            else:
                gaps.append({'owner': owner, 'between': [left['id'], right['id']], 'minutes': int((right['start_dt'] - left['end_dt']).total_seconds() / 60)})
    return {'mode': 'schedule', 'timezone': data['timezone'], 'activities': [{k: v for k, v in row.items() if k not in {'start_dt', 'end_dt'}} for row in enriched],
            'conflicts': conflicts, 'conflict_count': len(conflicts), 'gaps': gaps,
            'total_minutes': sum(row['duration_minutes'] for row in enriched)}


def _calendar(data):
    _base(data, 'project-calendar')
    year, month = data.get('year'), data.get('month')
    _need(isinstance(year, int) and 2000 <= year <= 2100 and isinstance(month, int) and 1 <= month <= 12, 'valid calendar year and month required')
    first_weekday, days_in_month = calendar.monthrange(year, month)
    events = data.get('events')
    _need(isinstance(events, list) and events, 'calendar events required')
    ids = [row.get('id') for row in events]; _need(all(ids), 'calendar event ids required'); _unique(ids, 'calendar event ids must be unique')
    enriched = []
    month_start, month_end = dt.date(year, month, 1), dt.date(year, month, days_in_month)
    for row in events:
        _need(all(isinstance(row.get(key), str) and row[key].strip() for key in ('label', 'resource', 'start', 'end')), 'calendar label, resource, start and end required')
        start, end = dt.date.fromisoformat(row['start']), dt.date.fromisoformat(row['end'])
        _need(month_start <= start <= end <= month_end, 'calendar event must stay inside the displayed month')
        enriched.append({**row, 'duration_days': (end - start).days + 1})
    conflicts = []
    for left_index, left in enumerate(enriched):
        for right in enriched[left_index + 1:]:
            if left['resource'] == right['resource'] and max(left['start'], right['start']) <= min(left['end'], right['end']):
                conflicts.append({'resource': left['resource'], 'events': [left['id'], right['id']]})
    return {'mode': 'project-calendar', 'year': year, 'month': month, 'first_weekday_monday0': first_weekday,
            'days_in_month': days_in_month, 'events': enriched, 'multi_day_events': sum(row['duration_days'] > 1 for row in enriched),
            'resource_conflicts': conflicts, 'conflict_count': len(conflicts), 'calendar_alignment': 'passed'}


ANALYZERS = {'gauge': _gauge, 'report-table': _report, 'sales-table': _sales,
             'schedule': _schedule, 'project-calendar': _calendar}


def analyze(data):
    mode = data.get('mode')
    _need(mode in ANALYZERS, 'unsupported planning/report mode')
    result = ANALYZERS[mode](data)
    result['data_status'] = data.get('data_status', 'unspecified')
    result['assumptions'] = data.get('assumptions', [])
    return result


def _font():
    from matplotlib import font_manager
    path = Path('/System/Library/Fonts/STHeiti Light.ttc')
    if path.exists():
        font_manager.fontManager.addfont(path)
        return font_manager.FontProperties(fname=path).get_name()
    return 'DejaVu Sans'


def _figure(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'font.family': _font(), 'font.size': 10.5, 'text.color': INK,
                                 'svg.fonttype': 'none', 'svg.hashsalt': 'diagram-studio-planning-report-v1'})
    fig = plt.figure(figsize=(12.8, 7.2), facecolor=BG)
    ax = fig.add_axes([0.055, 0.13, 0.89, 0.67]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    fig.text(0.055, 0.92, data['title'], fontsize=23, weight='medium')
    fig.text(0.055, 0.862, data.get('subtitle', ''), fontsize=10.5, color=MUTED)
    fig.text(0.055, 0.045, data.get('footer', '模拟数据 · 计算摘要与输入模型随图保留'), fontsize=9.5, color=MUTED)
    return fig, ax


def _wrap(value, width):
    lines = []
    for raw in str(value).split('\n'):
        lines.extend(textwrap.wrap(raw, width=max(4, width), break_long_words=True, break_on_hyphens=False) or [''])
    return '\n'.join(lines)


def _table(ax, headers, rows, widths, aligns=None, row_colors=None, cell_colors=None, font_size=9.0):
    from matplotlib.patches import Rectangle
    _need(math.isclose(sum(widths), 1, abs_tol=1e-9), 'table widths must sum to 1')
    aligns = aligns or ['left'] * len(headers); row_colors = row_colors or {}; cell_colors = cell_colors or {}
    height = min(0.115, 0.91 / (len(rows) + 1)); top = 0.97
    xs = [0]
    for width in widths: xs.append(xs[-1] + width)
    ax.add_patch(Rectangle((0, top-height), 1, height, facecolor='#E7E1D8', edgecolor=GRID, linewidth=1))
    for index, header in enumerate(headers):
        center = aligns[index] == 'center'; x = (xs[index]+xs[index+1])/2 if center else xs[index]+0.010
        ax.text(x, top-height/2, header, ha='center' if center else 'left', va='center', fontsize=9.2, weight='medium')
    for row_index, row in enumerate(rows):
        bottom = top - height*(row_index+2); face = row_colors.get(row_index, PAPER if row_index%2==0 else '#F4F1EC')
        ax.add_patch(Rectangle((0,bottom),1,height,facecolor=face,edgecolor=GRID,linewidth=.8))
        for column_index, value in enumerate(row):
            if (row_index,column_index) in cell_colors:
                ax.add_patch(Rectangle((xs[column_index],bottom),widths[column_index],height,facecolor=cell_colors[(row_index,column_index)],edgecolor='none',alpha=.22))
            center = aligns[column_index] == 'center'; x = (xs[column_index]+xs[column_index+1])/2 if center else xs[column_index]+0.010
            ax.text(x,bottom+height/2,_wrap(value,max(5,int(widths[column_index]*82))),ha='center' if center else 'left',va='center',fontsize=font_size)
    for x in xs: ax.plot([x,x],[top-height*(len(rows)+1),top],color=GRID,linewidth=.8)
    return top-height*(len(rows)+1)


def _render_gauge(data, meta):
    from matplotlib.patches import Circle, Polygon, Rectangle, Wedge
    fig, ax = _figure(data); metric = data['metric']; low, high = meta['range']; center=(.36,.46); radius=.28
    def angle(value): return 210 - (float(value)-low)/(high-low)*240
    for row in sorted(data['thresholds'], key=lambda item:item['min']):
        a1, a2 = angle(row['max']), angle(row['min'])
        ax.add_patch(Wedge(center,radius,a1,a2,width=.095,facecolor=COLORS[row['color']],edgecolor=BG,linewidth=2))
        mid=math.radians((a1+a2)/2); ax.text(center[0]+.35*math.cos(mid),center[1]+.35*math.sin(mid),row['label'],ha='center',va='center',fontsize=9,color=MUTED)
    theta=math.radians(angle(metric['value'])); tip=(center[0]+.22*math.cos(theta),center[1]+.22*math.sin(theta))
    ax.plot([center[0],tip[0]],[center[1],tip[1]],color=INK,linewidth=3,zorder=5); ax.add_patch(Circle(center,.025,color=INK,zorder=6))
    target=math.radians(angle(metric['target'])); outer=(center[0]+.31*math.cos(target),center[1]+.31*math.sin(target)); left=(outer[0]+.022*math.cos(target+2.45),outer[1]+.022*math.sin(target+2.45)); right=(outer[0]+.022*math.cos(target-2.45),outer[1]+.022*math.sin(target-2.45))
    ax.add_patch(Polygon([outer,left,right],closed=True,color=BLUE,zorder=7))
    ax.text(center[0],.21,f"{metric['value']:g}{metric['unit']}",ha='center',fontsize=27,weight='medium')
    ax.text(center[0],.145,f"目标 {metric['target']:g}{metric['unit']} · {'已达成' if meta['target_met'] else '未达成'}",ha='center',fontsize=11,color=GREEN if meta['target_met'] else RED)
    ax.text(.05,.20,f"{low:g}{metric['unit']}",fontsize=9,color=MUTED); ax.text(.63,.20,f"{high:g}{metric['unit']}",fontsize=9,color=MUTED)
    ax.add_patch(Rectangle((.70,.24),.29,.48,facecolor=PAPER,edgecolor=GRID,linewidth=1))
    ax.text(.72,.67,'阈值依据',fontsize=10,weight='medium')
    for index,row in enumerate(data['thresholds']):
        ax.text(.72,.60-index*.12,f"{row['min']:g}–{row['max']:g}{metric['unit']}  {row['label']}\n{row['basis']}",fontsize=8.7,color=MUTED,va='top')
    return fig


def _render_report(data, meta):
    fig, ax = _figure(data); columns=data['columns']
    headers=[column['label']+(f"\n({column['unit']})" if column['type']!='text' else '') for column in columns]
    rows=[[row['values'][column['id']] for column in columns] for row in data['records']]
    widths=[.22,.18,.15,.15,.15,.15]; aligns=['left','left']+['center']*(len(columns)-2)
    bottom=_table(ax,headers,rows,widths,aligns)
    operations={'sum':'合计','average':'平均','min':'最小','max':'最大'}
    summary=' · '.join(f"{next(c for c in columns if c['id']==key.split(':')[0])['label']} {operations[key.split(':')[1]]} = {value:g}{next(c for c in columns if c['id']==key.split(':')[0])['unit']}" for key,value in meta['summaries'].items())
    ax.text(0,max(.02,bottom-.065),'汇总（独立于明细） · '+summary,fontsize=9.5,color=MUTED)
    return fig


def _render_sales(data, meta):
    fig, ax = _figure(data); rows=[]; row_colors={}; index=0
    by_region=defaultdict(list)
    for row in data['records']: by_region[row['region']].append(row)
    for region,items in by_region.items():
        for row in items:
            rows.append([region,row['product'],row['orders'],row['units'],f"{row['revenue']:,.0f}"]); index+=1
        subtotal=meta['subtotals'][region]; rows.append([region+' 小计','—',subtotal['orders'],subtotal['units'],f"{subtotal['revenue']:,.0f}"]); row_colors[index]='#E8EDE7'; index+=1
    total=meta['grand_total']; rows.append(['总计','叶级记录',total['orders'],total['units'],f"{total['revenue']:,.0f}"]); row_colors[index]='#E3E7EC'
    bottom=_table(ax,['区域','产品','订单数\n(单)','销量\n(台)','销售额\n('+data['currency']+')'],rows,[.20,.28,.15,.15,.22],['left','left','center','center','center'],row_colors)
    ax.text(0,max(.02,bottom-.06),f"期间 {data['period']} · 小计按叶级记录计算，不重复计入总计",fontsize=9.5,color=MUTED)
    return fig


def _render_schedule(data, meta):
    from matplotlib.patches import Rectangle
    fig, ax = _figure(data); acts=meta['activities']; owners=[]
    for row in acts:
        if row['owner'] not in owners: owners.append(row['owner'])
    starts=[dt.datetime.fromisoformat(row['start']) for row in acts]; ends=[dt.datetime.fromisoformat(row['end']) for row in acts]
    day=min(starts).date(); start_hour=min(value.hour for value in starts); end_hour=max(value.hour+(1 if value.minute else 0) for value in ends)
    left,right=.18,.96; top=.90; lane_h=.16
    for hour in range(start_hour,end_hour+1):
        x=left+(hour-start_hour)/(end_hour-start_hour)*(right-left); ax.plot([x,x],[top-lane_h*len(owners),top],color=GRID,linewidth=.8); ax.text(x,top+.03,f'{hour:02d}:00',ha='center',fontsize=8.5,color=MUTED)
    conflict_ids={item for conflict in meta['conflicts'] for item in conflict['activities']}
    for lane,owner in enumerate(owners):
        y=top-lane_h*(lane+1); ax.add_patch(Rectangle((0,y),right,lane_h,facecolor=PAPER if lane%2==0 else '#F4F1EC',edgecolor=GRID,linewidth=.8)); ax.text(.01,y+lane_h/2,owner,va='center',fontsize=9.5)
        for row in [item for item in acts if item['owner']==owner]:
            start,end=dt.datetime.fromisoformat(row['start']),dt.datetime.fromisoformat(row['end'])
            x1=left+((start.hour+start.minute/60)-start_hour)/(end_hour-start_hour)*(right-left); x2=left+((end.hour+end.minute/60)-start_hour)/(end_hour-start_hour)*(right-left)
            color=RED if row['id'] in conflict_ids else GREEN if row.get('status')=='confirmed' else BLUE
            ax.add_patch(Rectangle((x1,y+.025),max(.012,x2-x1),lane_h-.05,facecolor=color,edgecolor='none',alpha=.82))
            ax.text((x1+x2)/2,y+lane_h/2,_wrap(row['label'],14),ha='center',va='center',fontsize=8,color='white')
    ax.text(0,.08,f"{day.isoformat()} · 时区 {meta['timezone']} · 活动 {len(acts)} 项 · 冲突 {meta['conflict_count']} 处（红色）",fontsize=9.5,color=MUTED)
    return fig


def _render_calendar(data, meta):
    from matplotlib.patches import Rectangle
    fig, ax = _figure(data); weeks=calendar.Calendar(firstweekday=0).monthdayscalendar(data['year'],data['month']); x0=.02; y_top=.91; width=.137; gap=.005; height=.155
    for index,label in enumerate(['一','二','三','四','五','六','日']): ax.text(x0+index*(width+gap)+width/2,.96,label,ha='center',fontsize=9.5,color=MUTED)
    palette=[GREEN,BLUE,AMBER,RED]; resource_color={resource:palette[index%len(palette)] for index,resource in enumerate(dict.fromkeys(row['resource'] for row in data['events']))}
    for week_index,week in enumerate(weeks):
        for day_index,day in enumerate(week):
            x=x0+day_index*(width+gap); y=y_top-(week_index+1)*height
            ax.add_patch(Rectangle((x,y),width,height-.006,facecolor=PAPER if day else '#E8E4DD',edgecolor=GRID,linewidth=.8))
            if not day: continue
            ax.text(x+.008,y+height-.030,str(day),fontsize=8.5,color=MUTED,va='top')
            date=dt.date(data['year'],data['month'],day); events=[row for row in data['events'] if dt.date.fromisoformat(row['start'])<=date<=dt.date.fromisoformat(row['end'])]
            for event_index,event in enumerate(events[:3]):
                ey=y+height-.062-event_index*.031; ax.add_patch(Rectangle((x+.007,ey-.022),width-.014,.027,facecolor=resource_color[event['resource']],edgecolor='none',alpha=.84))
                ax.text(x+.012,ey-.009,_wrap(event['label'],12),fontsize=6.9,color='white',va='center')
    legend=' · '.join(f"{resource}" for resource in resource_color)
    ax.text(.02,.06,f"{data['year']}年{data['month']}月 · {meta['days_in_month']}天 · 跨天事件 {meta['multi_day_events']} 项 · 资源：{legend}",fontsize=9.3,color=MUTED)
    return fig


RENDERERS={'gauge':_render_gauge,'report-table':_render_report,'sales-table':_render_sales,'schedule':_render_schedule,'project-calendar':_render_calendar}


def render(data, output, stem=None):
    import matplotlib
    import matplotlib.pyplot as plt
    meta=analyze(data); output=Path(output); output.mkdir(parents=True,exist_ok=True); stem=stem or data.get('id') or data['mode']
    fig=RENDERERS[data['mode']](data,meta)
    fig.savefig(output/f'{stem}.svg',facecolor=BG,metadata={'Date':None})
    fig.savefig(output/f'{stem}.png',facecolor=BG,dpi=150,metadata={'Software':'diagram-studio planning_report.py'})
    plt.close(fig)
    (output/f'{stem}.input.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    meta['matplotlib_version']=matplotlib.__version__; meta['scope']='验证本批次阈值、单位、汇总、粒度、日历日期与时间冲突；不把模拟记录冒充现场事实'
    (output/f'{stem}.calculation.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2,default=str)+'\n')
    qa={'mode':data['mode'],'errors':[],'warnings':[],'layout_issues':[],
        'checks':['input schema','mode-specific calculations','finite values','SVG and PNG generated'],
        'visual_review':'pending; open the actual SVG/PNG before acceptance'}
    (output/f'{stem}.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
    return meta


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('input'); parser.add_argument('--out',required=True); parser.add_argument('--stem')
    args=parser.parse_args(); source=Path(args.input)
    try: print(json.dumps(render(json.loads(source.read_text()),args.out,args.stem or source.stem),ensure_ascii=False,default=str))
    except (KeyError,ValueError,ImportError) as error: parser.error(str(error))


if __name__=='__main__': main()
