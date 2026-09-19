#!/usr/bin/env python3
"""Export a checked BPMN collaboration subset with diagram interchange layout.
This exporter creates non-executable models. It is not a workflow runtime.
"""
import argparse,json,re,math,xml.etree.ElementTree as E
from pathlib import Path
NS={'bpmn':'http://www.omg.org/spec/BPMN/20100524/MODEL','bpmndi':'http://www.omg.org/spec/BPMN/20100524/DI','dc':'http://www.omg.org/spec/DD/20100524/DC','di':'http://www.omg.org/spec/DD/20100524/DI'}
for k,v in NS.items():E.register_namespace(k,v)
def tag(p,n):return '{'+NS[p]+'}'+n
def need(x,m):
    if not x:raise ValueError(m)
def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def compile_model(d):
    pools=d['pools'];nodes=d['nodes'];flows=d['flows'];messages=d.get('messages',[])
    need(pools and nodes,'pools and nodes are required')
    allids=[x['id'] for x in pools+nodes+flows+messages]
    need(len(set(allids))==len(allids),'all IDs must be unique')
    need(all(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9.-]*',x) for x in allids),'IDs must be XML-safe identifiers')
    # Prefix all generated IDs to avoid collisions with user model IDs.
    need(not any(x.startswith('DS_') for x in allids),'DS_ is reserved')
    pd={p['id']:p for p in pools};nd={n['id']:n for n in nodes}
    kinds={'startEvent','endEvent','task','userTask','serviceTask','sendTask','receiveTask','exclusiveGateway','parallelGateway'}
    for n in nodes:
        need(n['pool'] in pd,'node has unknown pool');need(n['kind'] in kinds,'unsupported BPMN element '+n['kind'])
        need(all(finite(n[k]) and n[k]>=0 for k in ('x','y')),'invalid coordinates')
    incoming={n['id']:[] for n in nodes};outgoing={n['id']:[] for n in nodes}
    for f in flows:
        need(f['from'] in nd and f['to'] in nd,'unknown sequence endpoint')
        need(nd[f['from']]['pool']==nd[f['to']]['pool'],'sequence flow must not cross pools')
        need(nd[f['from']]['kind']!='endEvent','end event cannot have outgoing sequence flow')
        need(nd[f['to']]['kind']!='startEvent','start event cannot have incoming sequence flow')
        outgoing[f['from']].append(f);incoming[f['to']].append(f)
    for n in nodes:
        if n['kind']=='startEvent':need(len(outgoing[n['id']])>=1,'start event needs outgoing flow')
        elif n['kind']=='endEvent':need(len(incoming[n['id']])>=1,'end event needs incoming flow')
        else:need(incoming[n['id']] and outgoing[n['id']],'internal node must have incoming and outgoing flows')
        if n['kind']=='exclusiveGateway' and len(outgoing[n['id']])>1:
            need(all(f.get('name') for f in outgoing[n['id']]),'exclusive branches need named conditions')
    for m in messages:
        need(m['from'] in nd and m['to'] in nd,'unknown message endpoint')
        need(nd[m['from']]['pool']!=nd[m['to']]['pool'],'message flow must cross pools')
        need(nd[m['from']]['kind'] not in ('exclusiveGateway','parallelGateway') and nd[m['to']]['kind'] not in ('exclusiveGateway','parallelGateway'),'gateway cannot be a message endpoint')
        need(nd[m['from']]['kind']!='startEvent' and nd[m['to']]['kind']!='endEvent','invalid event message direction')
    # This subset requires explicit starts and ends; reject disconnected cycles.
    def reachable(seeds,edges,key):
        seen=set(seeds);todo=list(seeds)
        while todo:
            for f in edges[todo.pop()]:
                if f[key] not in seen:seen.add(f[key]);todo.append(f[key])
        return seen
    need(set(nd)==reachable([n['id'] for n in nodes if n['kind']=='startEvent'],outgoing,'to'),'each node must be reachable from a start')
    need(set(nd)==reachable([n['id'] for n in nodes if n['kind']=='endEvent'],incoming,'from'),'each node must be able to reach an end')
    root=E.Element(tag('bpmn','definitions'),{'id':'DS_definitions','targetNamespace':'https://diagram-studio.local/bpmn','exporter':'diagram-studio'})
    collaboration=E.SubElement(root,tag('bpmn','collaboration'),id='DS_collaboration')
    for p in pools:
        E.SubElement(collaboration,tag('bpmn','participant'),id=p['id'],name=p['name'],processRef='DS_process_'+p['id'])
    for m in messages:E.SubElement(collaboration,tag('bpmn','messageFlow'),id=m['id'],name=m.get('name',''),sourceRef=m['from'],targetRef=m['to'])
    for p in pools:
        process=E.SubElement(root,tag('bpmn','process'),id='DS_process_'+p['id'],isExecutable='false')
        for n in nodes:
            if n['pool']!=p['id']:continue
            elem=E.SubElement(process,tag('bpmn',n['kind']),id=n['id'],name=n.get('name',''))
            for flow in incoming[n['id']]:E.SubElement(elem,tag('bpmn','incoming')).text=flow['id']
            for flow in outgoing[n['id']]:E.SubElement(elem,tag('bpmn','outgoing')).text=flow['id']
        for f in flows:
            if nd[f['from']]['pool']==p['id']:E.SubElement(process,tag('bpmn','sequenceFlow'),id=f['id'],name=f.get('name',''),sourceRef=f['from'],targetRef=f['to'])
    diagram=E.SubElement(root,tag('bpmndi','BPMNDiagram'),id='DS_diagram');plane=E.SubElement(diagram,tag('bpmndi','BPMNPlane'),id='DS_plane',bpmnElement='DS_collaboration')
    geometry={}
    for obj in pools+nodes:
        kind=obj.get('kind','pool');w=obj.get('w',36 if kind in ('startEvent','endEvent') else 50 if kind.endswith('Gateway') else 120);h=obj.get('h',36 if kind in ('startEvent','endEvent') else 50 if kind.endswith('Gateway') else 80)
        need(all(finite(v) for v in (obj['x'],obj['y'],w,h)) and w>0 and h>0,'invalid shape geometry')
        geometry[obj['id']]=(obj['x'],obj['y'],w,h)
        shape=E.SubElement(plane,tag('bpmndi','BPMNShape'),id='DS_shape_'+obj['id'],bpmnElement=obj['id'])
        if kind=='pool':shape.set('isHorizontal','true')
        E.SubElement(shape,tag('dc','Bounds'),x=str(obj['x']),y=str(obj['y']),width=str(w),height=str(h))
        if obj.get('label_box'):
            label=E.SubElement(shape,tag('bpmndi','BPMNLabel'));lx,ly,lw,lh=obj['label_box'];E.SubElement(label,tag('dc','Bounds'),x=str(lx),y=str(ly),width=str(lw),height=str(lh))
    for n in nodes:
        x,y,w,h=geometry[n['id']];px,py,pw,ph=geometry[n['pool']]
        need(x>=px+30 and y>=py and x+w<=px+pw and y+h<=py+ph,'node outside its pool')
    for f in flows+messages:
        edge=E.SubElement(plane,tag('bpmndi','BPMNEdge'),id='DS_edge_'+f['id'],bpmnElement=f['id'])
        x,y,w,h=geometry[f['from']];xx,yy,ww,hh=geometry[f['to']]
        points=f.get('points',[(x+w,y+h/2),(xx,yy+hh/2)])
        need(len(points)>=2,'edge requires two waypoints')
        for px,py in points:
            need(finite(px) and finite(py),'invalid waypoint')
            E.SubElement(edge,tag('di','waypoint'),x=str(px),y=str(py))
        if f.get('label_box'):
            label=E.SubElement(edge,tag('bpmndi','BPMNLabel'));lx,ly,lw,lh=f['label_box'];E.SubElement(label,tag('dc','Bounds'),x=str(lx),y=str(ly),width=str(lw),height=str(lh))
    return E.tostring(root,encoding='unicode',xml_declaration=True)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--out',required=True);a=p.parse_args()
    try:xml=compile_model(json.loads(Path(a.input).read_text()))
    except (KeyError,ValueError,TypeError) as e:p.error(str(e))
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(xml,encoding='utf-8');print(out)
if __name__=='__main__':main()
