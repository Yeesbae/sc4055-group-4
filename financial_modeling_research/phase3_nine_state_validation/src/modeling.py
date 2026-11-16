"""Finite observed-history stochastic models. No quantum circuits or QAE."""
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
import numpy as np
from scipy.stats import beta


def discretize(values, name, train_end):
    v = np.asarray(values)
    fixed = {'binary20':[20.], 'binary25':[25.], 'binary30':[30.],
             'binary35':[35.], 'ternary20_30':[20.,30.]}
    if name in fixed:
        edges = fixed[name]
    elif name == 'binary_train_q80':
        edges = [float(np.quantile(v[:train_end], .8, method='linear'))]
    elif name == 'ternary_train_tertiles':
        edges = np.quantile(v[:train_end], [1/3,2/3], method='linear').tolist()
    else:
        raise ValueError(name)
    return np.searchsorted(edges, v, side='right'), edges


def contexts(y, k, m):
    """At index t: context ending at t, oldest symbol most significant."""
    out = np.zeros(len(y), dtype=int)
    if k:
        n=m**k; s=0
        for t,x in enumerate(y):
            s=(s*m+int(x))%n; out[t]=s
    return out


@dataclass
class Model:
    name: str
    k: int
    m: int
    alpha: float
    edges: list
    counts: np.ndarray
    p: np.ndarray
    nxt: np.ndarray
    train_end: int

    @property
    def n(self): return self.m**self.k

    @property
    def labels(self):
        return [''.join(map(str,w)) or 'empty' for w in product(range(self.m),repeat=self.k)]

    def fractions(self):
        a=Fraction(str(self.alpha))
        return [[(int(c)+a)/(int(sum(row))+self.m*a) for c in row] for row in self.counts]

    def matrices(self):
        tx=np.zeros((self.m,self.n,self.n))
        for s in range(self.n):
            for x in range(self.m): tx[x,s,self.nxt[s,x]]=self.p[s,x]
        return tx

    def stationary(self):
        T=self.matrices().sum(0)
        a=T.T-np.eye(self.n); a[-1]=1
        b=np.zeros(self.n); b[-1]=1
        pi=np.linalg.solve(a,b)
        assert np.min(pi)>-1e-10
        return pi

    def count_table(self):
        pi=self.stationary(); rows=[];total=self.counts.sum()
        for s in range(self.n):
            n=int(self.counts[s].sum())
            row={'state':s,'history':self.labels[s],'n':n,'supported_n25':n>=25,
                 'empirical_context_weight':float(n/total),'stationary_weight':float(pi[s])}
            for x in range(self.m):
                row[f'count_{x}']=int(self.counts[s,x]);row[f'p_{x}']=float(self.p[s,x])
                row[f'p_{x}_exact']=str(self.fractions()[s][x])
                if self.m>1:
                    lo,hi=beta.ppf([.025,.975],self.counts[s,x]+self.alpha,n-self.counts[s,x]+(self.m-1)*self.alpha)
                    row[f'lo95_{x}']=float(lo);row[f'hi95_{x}']=float(hi)
            rows.append(row)
        return rows


def fit(values, name, k, train_end, alpha=.5):
    y,edges=discretize(values,name,train_end);m=len(edges)+1;n=m**k
    ctx=contexts(y,k,m); counts=np.zeros((n,m),dtype=int)
    for t in range(k,train_end):
        s=ctx[t-1] if k else 0
        counts[s,y[t]]+=1
    p=(counts+alpha)/(counts.sum(1,keepdims=True)+m*alpha)
    nxt=np.array([[(s*m+x)%n for x in range(m)] for s in range(n)])
    return Model(name,k,m,alpha,edges,counts,p,nxt,train_end),y,ctx


def predicate(word, kind='count', K=3, high=1):
    hits=[x>=high for x in word]
    if kind=='count': return sum(hits)>=K
    if kind=='hit': return any(hits)
    if kind=='run':
        best=run=0
        for h in hits:
            run=run+1 if h else 0;best=max(best,run)
        return best>=K
    raise ValueError(kind)


def enumerate_event(model, state, L=6, K=3, high=None, kind='count'):
    """Independent product-of-path-probabilities implementation."""
    high=model.m-1 if high is None else high
    answer=0.
    for word in product(range(model.m),repeat=L):
        s=state;w=1.
        for x in word: w*=model.p[s,x];s=int(model.nxt[s,x])
        if predicate(word,kind,K,high): answer+=w
    return answer


def event_dp(model, L=6, K=3, high=None, kind='count'):
    """Backward finite automaton DP for every initial state. O(L D m K)."""
    high=model.m-1 if high is None else high
    if kind=='hit': K=1; kind='count'
    if K<=0: return np.ones(model.n)
    v=np.zeros((model.n,K+1));v[:,K]=1.
    for _ in range(L):
        z=np.zeros_like(v)
        for s in range(model.n):
            for c in range(K+1):
                for x in range(model.m):
                    if c==K: d=K
                    elif kind=='count':d=min(K,c+(x>=high))
                    elif kind=='run':d=min(K,c+1) if x>=high else 0
                    else:raise ValueError(kind)
                    z[s,c]+=model.p[s,x]*v[model.nxt[s,x],d]
        v=z
    return v[:,0]


def score_forecasts(model,y,ctx,indices,L=6,K=3):
    """indices are forecast origins, y[t+1] is next target, never y[t]."""
    t=np.asarray(indices,dtype=int);states=ctx[t]
    high=model.m-1;prob=model.p[states];next_y=y[t+1]
    stress_prob=prob[:,high]
    truth=(next_y==high).astype(int)
    pp=np.clip(prob[np.arange(len(t)),next_y],1e-15,1)
    one_ll=-np.log(pp)
    one_brier=np.sum((prob-np.eye(model.m)[next_y])**2,axis=1)
    a=event_dp(model,L,K)[states]
    target=np.array([sum(y[i+1:i+L+1]>=high)>=K for i in t],dtype=int)
    return {'state':states,'next_y':next_y,'next_stress':truth,'stress_pred':stress_prob,
            'categorical_logloss':one_ll,'categorical_brier':one_brier,
            'stress_logloss':-(truth*np.log(np.clip(stress_prob,1e-15,1))+(1-truth)*np.log(np.clip(1-stress_prob,1e-15,1))),
            'stress_brier':(stress_prob-truth)**2,'event_pred':a,'event_truth':target,'event_brier':(a-target)**2}


def exact_partition(model):
    """Greatest exact probabilistic bisimulation for a positive unifilar model.
    Equal emissions and equivalent successors iff all future word laws agree.
    """
    p=model.fractions(); blocks=[0]*model.n;trace=[]
    while True:
        signatures=[(tuple(p[s]),tuple(blocks[j] for j in model.nxt[s])) for s in range(model.n)]
        keys={};new=[]
        for sig in signatures:
            if sig not in keys:keys[sig]=len(keys)
            new.append(keys[sig])
        trace.append(len(keys))
        if new==blocks:break
        blocks=new
    return {'D_c':len(set(blocks)),'blocks':blocks,'refinement_class_counts':trace,
            'exact_equality':'rational counts plus rational Dirichlet prior; no distance tolerance',
            'scope':'causal states of this positive fitted finite-order process only'}


def rank_modular(model,prime=1000000007):
    """Exact rational conditional future matrix of all length-k words, modulo p.
    Nonzero determinant mod p is an exact full-rank certificate over Q.
    """
    ps=model.fractions(); pm=[]
    for row in ps:
        pm.append([(p.numerator%prime)*pow(p.denominator%prime,-1,prime)%prime for p in row])
    words=list(product(range(model.m),repeat=model.k))
    a=[]
    for s in range(model.n):
        row=[]
        for word in words:
            state=s;v=1
            for x in word:v=v*pm[state][x]%prime;state=int(model.nxt[state,x])
            row.append(v)
        a.append(row)
    det=1;rank=0
    for c in range(model.n):
        pivot=next((i for i in range(rank,model.n) if a[i][c]),None)
        if pivot is None:continue
        if pivot!=rank:a[pivot],a[rank]=a[rank],a[pivot];det=-det
        q=a[rank][c];det=det*q%prime;inv=pow(q,-1,prime)
        for i in range(rank+1,model.n):
            w=a[i][c]*inv%prime
            for j in range(c,model.n):a[i][j]=(a[i][j]-w*a[rank][j])%prime
        rank+=1
    return {'prime':prime,'rank_mod_p':rank,'determinant_mod_p':det if rank==model.n else 0,
            'rational_probability_rank_exact':model.n if rank==model.n else None,
            'quantum_dimension_lower_bound':int(np.ceil(np.sqrt(rank))),
            'classical_hidden_dimension_lower_bound':rank,
            'proof':'All states reached after k outputs; positive prefix weights. Conditional length-k matrix is an invertible row-scaled Hankel submatrix when determinant mod p is nonzero. A fixed D-dimensional instrument has probability rank at most D^2.',
            'limitation':'rank mod p below D is only a lower bound, not proof of rank deficiency'}
