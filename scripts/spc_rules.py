"""Four WECO tests on standardized approximately normal independent statistics.

Signals are recorded at the window end (detection time), with contributing
indices retained. Call separately for each explicitly selected phase.
"""
import math

def weco(z, offset=0):
    if not isinstance(z,list) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in z):
        raise ValueError('finite standardized observations required')
    if isinstance(offset,bool) or not isinstance(offset,int) or offset<0:
        raise ValueError('nonnegative integer offset required')
    events=[]
    for end in range(len(z)):
        for code,width,threshold,required in [('WE1',1,3,1),('WE2',3,2,2),('WE3',5,1,4),('WE4',8,0,8)]:
            start=end-width+1
            if start<0: continue
            for side in (1,-1):
                contributors=[offset+i+1 for i in range(start,end+1) if side*z[i]>threshold]
                if len(contributors)>=required:
                    events.append(dict(rule=code,detected_at=offset+end+1,window_start=offset+start+1,
                                       window_end=offset+end+1,side='above' if side==1 else 'below',contributors=contributors))
    return events
