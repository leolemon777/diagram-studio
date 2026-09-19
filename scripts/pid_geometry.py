"""Orthogonal route diagnostics. Coordinates never create topology connections."""

def intersection(a,b,c,d):
    """Return closed-segment point/overlap intersection, or None."""
    ah=a[1]==b[1];ch=c[1]==d[1]
    if ah==ch:
        axis=0 if ah else 1;fixed=1-axis
        if a[fixed]!=c[fixed]:return None
        lo=max(min(a[axis],b[axis]),min(c[axis],d[axis]));hi=min(max(a[axis],b[axis]),max(c[axis],d[axis]))
        if lo>hi:return None
        p=[0,0];q=[0,0];p[axis]=lo;q[axis]=hi;p[fixed]=q[fixed]=a[fixed]
        return dict(kind='overlap' if lo<hi else 'touch',points=[p,q] if lo<hi else [p])
    h1,h2,v1,v2=(a,b,c,d) if ah else (c,d,a,b)
    x=v1[0];y=h1[1]
    if min(h1[0],h2[0])<=x<=max(h1[0],h2[0]) and min(v1[1],v2[1])<=y<=max(v1[1],v2[1]):
        p=[x,y];return dict(kind='touch' if p in [list(a),list(b),list(c),list(d)] else 'crossing',points=[p])
    return None

def diagnose(connections,boxes):
    """Boxes are conservative symbol envelopes; boundary contact is allowed."""
    findings=[];segments=[]
    for conn in connections:
        for index,(a,b) in enumerate(zip(conn['points'],conn['points'][1:])):
            segments.append((conn['id'],index,a,b))
            for item,(left,top,right,bottom) in boxes.items():
                hit=(a[1]==b[1] and top<a[1]<bottom and max(min(a[0],b[0]),left)<min(max(a[0],b[0]),right)) or (a[0]==b[0] and left<a[0]<right and max(min(a[1],b[1]),top)<min(max(a[1],b[1]),bottom))
                if hit:findings.append(dict(kind='symbol_intrusion',connection=conn['id'],segment=index,item=item))
    for i,(aid,ai,a,b) in enumerate(segments):
        for bid,bi,c,d in segments[i+1:]:
            hit=intersection(a,b,c,d)
            if not hit:continue
            if aid==bid and abs(ai-bi)==1 and hit['kind']=='touch':continue
            findings.append(dict(**hit,connections=[aid,bid],segments=[ai,bi]))
    return dict(findings=findings,scope='Exact axis-aligned external-route intersections and conservative symbol envelopes; no automatic connection or rerouting')

def crossing_display(connections,diagnostics,declarations):
    """Split declared under-routes, preserving original topology and final arrow endpoint."""
    from pid_model import need,fields
    need(type(declarations) is list,'crossings must be a list')
    candidates=[f for f in diagnostics['findings'] if f['kind']=='crossing' and len(set(f['connections']))==2]
    others=[f for f in diagnostics['findings'] if f not in candidates]
    need(not others,'ambiguous route geometry: '+str(others))
    byid={c['id']:c for c in connections};cuts={};claimed=set()
    for dec in declarations:
        fields(dec,('over','under','at','gap'),'crossing')
        need(isinstance(dec['over'],str) and isinstance(dec['under'],str) and dec['over']!=dec['under'],'two distinct crossing ids required')
        need(type(dec['at']) is list and len(dec['at'])==2 and all(type(x) in (int,float) for x in dec['at']),'crossing point required')
        need(type(dec['gap']) in (int,float) and 8<=dec['gap']<=40,'gap must be 8..40')
        matches=[(i,f) for i,f in enumerate(candidates) if set(f['connections'])=={dec['over'],dec['under']} and f['points'][0]==dec['at']]
        need(len(matches)==1,'declaration must match one actual crossing')
        i,f=matches[0];need(i not in claimed,'duplicate crossing declaration');claimed.add(i)
        si=f['segments'][f['connections'].index(dec['under'])];points=byid[dec['under']]['points'];a,b=points[si:si+2];axis=0 if a[1]==b[1] else 1
        distance=abs(dec['at'][axis]-a[axis]);length=abs(b[axis]-a[axis]);half=dec['gap']/2
        need(half<distance<length-half,'gap too close to endpoint or bend')
        cuts.setdefault((dec['under'],si),[]).append((distance-half,distance+half))
    need(len(claimed)==len(candidates),'undeclared crossing')
    result={}
    for conn in connections:
        parts=[];current=[conn['points'][0]]
        for si,(a,b) in enumerate(zip(conn['points'],conn['points'][1:])):
            axis=0 if a[1]==b[1] else 1;sign=1 if b[axis]>a[axis] else -1;last=-1
            for lo,hi in sorted(cuts.get((conn['id'],si),[])):
                need(lo>last,'overlapping crossing gaps');last=hi
                p=list(a);q=list(a);p[axis]+=sign*lo;q[axis]+=sign*hi
                current.append(p);parts.append(current);current=[q]
            current.append(b)
        parts.append(current);result[conn['id']]=parts
    return result
