"""Validated nested structure for Nassi-Shneiderman diagrams; no code execution."""
import re

def validate(d):
    def fields(x,keys):
        if not isinstance(x,dict) or set(x)!=set(keys):raise ValueError('invalid fields: '+str(keys))
    def text(x):
        if not isinstance(x,str) or not x.strip():raise ValueError('nonempty text required')
    fields(d,('title','assumptions','body'));text(d['title'])
    if not isinstance(d['assumptions'],list) or not d['assumptions']:raise ValueError('assumptions required')
    for s in d['assumptions']:text(s)
    ids=set();inventory=[]
    def sequence(body,depth,path):
        if not isinstance(body,list):raise ValueError('body must be list')
        if depth>12:raise ValueError('nesting exceeds 12')
        for index,node in enumerate(body):
            if not isinstance(node,dict):raise ValueError('node must be object')
            kind=node.get('kind')
            schema={'action':('id','kind','text'),'if':('id','kind','condition','then','else'),'while':('id','kind','condition','body'),'repeat':('id','kind','until','body'),'case':('id','kind','expression','branches','default')}
            if kind not in schema:raise ValueError('unknown structure')
            fields(node,schema[kind]);ident=node['id']
            if not isinstance(ident,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,31}',ident) or ident in ids:raise ValueError('unique ASCII id required')
            ids.add(ident)
            if len(ids)>500:raise ValueError('more than 500 nodes')
            inventory.append(dict(id=ident,kind=kind,path=path+[index]))
            if kind=='action':text(node['text'])
            elif kind=='if':
                text(node['condition']);sequence(node['then'],depth+1,path+[index,'then']);sequence(node['else'],depth+1,path+[index,'else'])
            elif kind in ('while','repeat'):
                text(node['condition' if kind=='while' else 'until']);sequence(node['body'],depth+1,path+[index,'body'])
            else:
                text(node['expression']);branches=node['branches']
                if not isinstance(branches,list) or not 1<=len(branches)<=8:raise ValueError('1..8 case branches required')
                labels=set()
                for j,branch in enumerate(branches):
                    fields(branch,('label','body'));text(branch['label'])
                    if branch['label'] in labels:raise ValueError('duplicate case label')
                    labels.add(branch['label']);sequence(branch['body'],depth+1,path+[index,'branches',j])
                sequence(node['default'],depth+1,path+[index,'default'])
    sequence(d['body'],0,[])
    return dict(nodes=inventory,count=len(ids),scope='nested control structure only; opaque expressions not parsed or executed',loop_semantics={'while':'continue while condition true; zero iterations allowed','repeat':'execute body then test until; exit when true'})
