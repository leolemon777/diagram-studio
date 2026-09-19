"""Explicit scan-sampled TON/TOF/TP, CTU/CTD and edge detectors, without hardware emulation."""
from render import need


def fields(row, required):
    need(isinstance(row,dict) and set(row)==set(required),'block fields must be exactly '+str(required))


def integer(value, maximum, name):
    need(type(value) is int and 0<=value<=maximum,name+' must be an unsigned integer <= '+str(maximum))


def validate_block(b, variables):
    need(isinstance(b,dict),'block must be an object')
    kind=b.get('type')
    if kind in ('TON','TOF','TP'):
        fields(b,('id','type','pt_ms','initial','rearm_policy') if kind=='TP' else ('id','type','pt_ms','initial'))
        if kind=='TP':need(b['rearm_policy']=='low_scan_after_completion','explicit low_scan_after_completion rearm policy required')
        integer(b['pt_ms'],2**32-1,'pt_ms')
        need(b['initial']=='reset','timer must explicitly start reset; warm timer resume unsupported')
    elif kind=='CTU':
        fields(b,('id','type','pv','reset','initial_cv','previous_input'))
        integer(b['pv'],65535,'pv');integer(b['initial_cv'],b['pv'],'initial_cv')
        need(isinstance(b['reset'],str) and b['reset'] in variables,'CTU reset must reference a declared Boolean variable')
        need(type(b['previous_input']) is bool,'CTU previous_input must be Boolean')
    elif kind=='CTD':
        fields(b,('id','type','pv','load','initial_cv','previous_input'))
        integer(b['pv'],65535,'pv');integer(b['initial_cv'],65535,'initial_cv')
        need(isinstance(b['load'],str) and b['load'] in variables,'CTD load must reference a declared Boolean variable')
        need(type(b['previous_input']) is bool,'CTD previous_input must be Boolean')
    elif kind in ('R_TRIG','F_TRIG'):
        fields(b,('id','type','previous_input'))
        need(type(b['previous_input']) is bool,'trigger previous_input must be explicit Boolean')
    else:raise ValueError('unsupported block type: '+str(kind))


def initialize(b):
    if b['type']=='TON':return dict(start_ms=None,et_ms=0,q=False)
    if b['type']=='TP':return dict(start_ms=None,et_ms=0,q=False,previous_input=False,phase='idle')
    if b['type']=='TOF':return dict(start_ms=None,et_ms=0,q=False,previous_input=False)
    if b['type']=='CTD':return dict(previous_input=b['previous_input'],cv=b['initial_cv'],q=b['initial_cv']==0)
    if b['type']=='CTU':return dict(previous_input=b['previous_input'],cv=b['initial_cv'],q=b['initial_cv']>=b['pv'])
    return dict(previous_input=b['previous_input'],q=False)


def call(b, state, signal, values, time_ms):
    before=dict(state);kind=b['type'];extra={}
    if kind=='TON':
        if not signal:state.update(start_ms=None,et_ms=0,q=False)
        else:
            if state['start_ms'] is None:state['start_ms']=time_ms
            state['et_ms']=min(b['pt_ms'],time_ms-state['start_ms'])
            state['q']=state['et_ms']>=b['pt_ms']
    elif kind=='TP':
        rising=signal and not state['previous_input'];accepted=False
        if state['phase']=='pulse':
            state['et_ms']=min(b['pt_ms'],time_ms-state['start_ms'])
            if state['et_ms']>=b['pt_ms']:
                state.update(q=False,phase='wait_low')
                if not signal:state.update(phase='idle',et_ms=0,start_ms=None)
        elif state['phase']=='wait_low':
            if not signal:state.update(phase='idle',et_ms=0,start_ms=None)
        elif rising:
            accepted=True;state.update(start_ms=time_ms,et_ms=0,q=b['pt_ms']>0,phase='pulse' if b['pt_ms']>0 else 'wait_low')
        state['previous_input']=signal;extra=dict(rising=rising,trigger_accepted=accepted)
    elif kind=='TOF':
        if signal:state.update(start_ms=None,et_ms=0,q=True)
        else:
            if state['previous_input']:state['start_ms']=time_ms
            if state['start_ms'] is not None:
                state['et_ms']=min(b['pt_ms'],time_ms-state['start_ms'])
                state['q']=state['et_ms']<b['pt_ms']
            else:state.update(et_ms=0,q=False)
        state['previous_input']=signal
    elif kind=='CTU':
        reset=values[b['reset']];rising=signal and not state['previous_input']
        if reset:state['cv']=0
        elif rising:state['cv']=min(b['pv'],state['cv']+1)
        state['previous_input']=signal;state['q']=state['cv']>=b['pv']
        extra=dict(reset=reset,reset_variable=b['reset'],rising=rising)
    elif kind=='CTD':
        load=values[b['load']];rising=signal and not state['previous_input']
        if load:state['cv']=b['pv']
        elif rising:state['cv']=max(0,state['cv']-1)
        state['previous_input']=signal;state['q']=state['cv']==0
        extra=dict(load=load,load_variable=b['load'],rising=rising)
    else:
        state['q']=(signal and not state['previous_input']) if kind=='R_TRIG' else (not signal and state['previous_input'])
        state['previous_input']=signal
    return dict(id=b['id'],type=kind,time_ms=time_ms,input=signal,before=before,after=dict(state),q=state['q'],**extra)


def label(b):
    if b['type']=='TP':return 'IN → Q\nPT = '+str(b['pt_ms'])+' ms\n忙时不重触发；结束后低扫描重备'
    if b['type'] in ('TON','TOF'):return 'IN → Q\nPT = '+str(b['pt_ms'])+' ms\n初态：复位；ET封顶于PT'
    if b['type']=='CTD':return 'CD → Q\nLOAD = '+b['load']+'\nPV = '+str(b['pv'])+'；CV初值 = '+str(b['initial_cv'])
    if b['type']=='CTU':return 'CU → Q\nRESET = '+b['reset']+'\nPV = '+str(b['pv'])+'；CV初值 = '+str(b['initial_cv'])
    return 'CLK → Q\n先前输入 = '+str(int(b['previous_input']))+'\nQ仅在检出边沿的扫描为真'
