"""Probability of a monotone Boolean function by memoized Shannon expansion.

Independent Bernoulli BASIC events only. Repeated IDs stay one variable.
No rare-event approximation and no addition of overlapping cut probabilities.
"""
import math
from functools import lru_cache

def quantify(d,nodes,cut_sets):
    from render import need
    from fault_tree import minimal
    need(d.get('probability_model')=='independent_bernoulli','explicit independent_bernoulli model required')
    for field in ('probability_basis','independence_justification'):
        need(isinstance(d.get(field),str) and d[field].strip(),field+' required')
    probs={};sources={}
    for id,r in nodes.items():
        if r['kind']!='basic':
            need('probability' not in r,'gate probabilities must be derived, not supplied');continue
        p=r.get('probability')
        need(isinstance(p,(int,float)) and not isinstance(p,bool) and math.isfinite(p) and 0<=p<=1,'each basic event needs probability in [0,1]')
        need(isinstance(r.get('probability_source'),str) and r['probability_source'].strip(),'basic probability_source required')
        probs[id]=float(p);sources[id]=r['probability_source']
    def canonical(sets):return tuple(tuple(sorted(s)) for s in minimal([frozenset(s) for s in sets]))
    visited=0
    @lru_cache(maxsize=None)
    def evaluate(state):
        nonlocal visited
        visited+=1;need(visited<=100000,'probability decomposition exceeds 100000 states; use specialized solver')
        if not state:return 0.0
        if not state[0]:return 1.0
        var=min(x for term in state for x in term)
        # If var is false, every term requiring it disappears. If true, remove
        # the requirement, then absorb supersets again to canonicalize.
        low=canonical([term for term in state if var not in term])
        high=canonical([tuple(x for x in term if x!=var) for term in state])
        p=probs[var]
        if p==0:return evaluate(low)
        if p==1:return evaluate(high)
        return math.fsum([(1-p)*evaluate(low),p*evaluate(high)])
    result=evaluate(canonical(cut_sets))
    return dict(model='independent_bernoulli',top_probability=result,
                method='memoized Shannon expansion of the full Boolean cut-set expression; floating-point arithmetic',
                probability_basis=d['probability_basis'],independence_justification=d['independence_justification'],
                basic_probabilities=probs,probability_sources=sources,states_evaluated=visited,
                cut_set_probabilities=[dict(events=sorted(s),probability=math.prod(probs[x] for x in s)) for s in cut_sets],
                warning='Cut-set probabilities overlap and must not be summed as an exact total. Independence is declared, not inferred or statistically verified.')
