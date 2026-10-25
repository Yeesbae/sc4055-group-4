"""Exact model inference and generated trajectory sampling."""
from fractions import Fraction
from itertools import product
import numpy as np
from .financial import P_R,P,NEXT

def dp(s,L=6,threshold=3,rational=False):
    zero=Fraction(0) if rational else 0.
    a=[[zero for _ in range(threshold+1)] for _ in range(9)];a[s][0]=1
    for _ in range(L):
        b=[[zero for _ in range(threshold+1)] for _ in range(9)]
        for j in range(9):
            for c in range(threshold+1):
                for x in range(3):b[NEXT[j,x]][min(threshold,c+(x==2))]+=a[j][c]*(P_R[j][x] if rational else P[j,x])
        a=b
    return sum(row[threshold] for row in a)

def enumerate_words(s,L=6,rational=False):
    out={}
    for w in product(range(3),repeat=L):
        j=s;pr=Fraction(1) if rational else 1.
        for x in w:pr*=P_R[j][x] if rational else P[j,x];j=NEXT[j,x]
        out[sum(x*4**t for t,x in enumerate(w))]=pr
    return out

def monte_carlo(s,n,seed):
    rng=np.random.default_rng(seed);states=np.full(n,s);count=np.zeros(n,int)
    for _ in range(6):
        u=rng.random(n);cum=P[states].cumsum(axis=1);x=(u[:,None]>cum[:,:2]).sum(axis=1)
        count+=x==2;states=NEXT[states,x]
    return int((count>=3).sum())
