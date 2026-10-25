"""Global-grid likelihood mode search, then bounded refinement of EVERY mode."""
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import xlogy

def loglik(theta,h,n,powers):
    p=np.sin(np.multiply.outer(np.atleast_1d(theta),2*np.asarray(powers)+1))**2
    p=np.clip(p,1e-15,1-1e-15)
    return (xlogy(h,p)+xlogy(np.asarray(n)-h,1-p)).sum(axis=1)

def mle(h,n,powers):
    grid=np.linspace(0,np.pi/2,8193);ll=loglik(grid,h,n,powers)
    ix=np.flatnonzero((ll[1:-1]>=ll[:-2])&(ll[1:-1]>=ll[2:]))+1
    modes=[{'theta':float(grid[j]),'loglik':float(ll[j]),'success':True} for j in [0,len(grid)-1]]
    for j in ix:
        z=minimize_scalar(lambda t:-loglik(t,h,n,powers)[0],bounds=(grid[j-1],grid[j+1]),method='bounded',options={'xatol':1e-13})
        modes.append(dict(theta=float(z.x),loglik=float(-z.fun),success=bool(z.success)))
    modes.sort(key=lambda z:z['loglik'],reverse=True);best=modes[0]
    return dict(estimate=float(np.sin(best['theta'])**2),loglik=best['loglik'],success=all(z['success'] for z in modes),modes=modes,gap=best['loglik']-modes[1]['loglik'])

def budget(powers,shots):return int(np.dot(2*np.asarray(powers)+1,shots))

def summary(est,truth):
    a=np.asarray(est);e=a-truth
    return dict(mean=float(a.mean()),bias=float(e.mean()),rmse=float(np.sqrt(np.mean(e*e))),std=float(a.std(ddof=1)),variance=float(a.var(ddof=1)),empirical_q025=float(np.quantile(a,.025)),empirical_q975=float(np.quantile(a,.975)),repetitions=len(a))
