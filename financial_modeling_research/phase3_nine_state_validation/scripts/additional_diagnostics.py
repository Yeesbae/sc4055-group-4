"""Calibration, per-origin support and secondary-event evaluation on fixed years."""
import json,sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.modeling import fit,contexts,event_dp,predicate
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results'

def main(data):
    d=pd.read_csv(data);d['date']=pd.to_datetime(d.DATE,format='%m/%d/%Y');d=d[d.date<='2026-10-23'].reset_index(drop=True);v=d.CLOSE.to_numpy();dates=d.date
    pred=pd.read_csv(R/'forecasts.csv.gz',low_memory=False);rng=np.random.default_rng(40552631);cal=[];support=[];secondary=[]
    for year in range(2015,2027):
        end=int(np.searchsorted(dates.to_numpy(),np.datetime64(f'{year}-01-01')))
        for k in [1,2,3]:
            model,y,c=fit(v,'ternary20_30',k,end)
            if k==2:
                for row in model.count_table():support.append({'outer_year':year,**row})
            g=pred[(pred.model==f'ternary20_30_k{k}')&(pred.year==year)&pred.event_eligible];origins=g.origin.to_numpy(int)
            for label,kind,K in [('hit6','hit',1),('run3in6','run',3)]:
                a=event_dp(model,6,K,kind=kind)[c[origins]];z=np.array([predicate(y[t+1:t+7],kind,K,2) for t in origins],int)
                secondary.append(dict(model=f'ternary20_30_k{k}',year=year,event=label,n=len(z),brier=float(np.mean((a-z)**2)),rate=float(z.mean()),mean_prediction=float(a.mean())))
                if kind=='hit':
                    ix=(c[origins]%3)!=2;secondary.append(dict(model=f'ternary20_30_k{k}',year=year,event='first_high_entry6_current_not_high',n=int(ix.sum()),brier=float(np.mean((a[ix]-z[ix])**2)),rate=float(z[ix].mean()),mean_prediction=float(a[ix].mean())))
    pd.DataFrame(support).to_csv(R/'annual_nine_state_context_support.csv',index=False);pd.DataFrame(secondary).to_csv(R/'secondary_event_scores.csv',index=False)
    for name in pred.model.unique():
        allg=pred[pred.model==name]
        for target,pc,yc in [('event','event_pred','event_truth'),('stress','stress_pred','next_stress')]:
            g=allg[allg.event_eligible].copy() if target=='event' else allg.copy();g=g.reset_index(drop=True);p=g[pc].to_numpy();y=g[yc].to_numpy();bins=np.minimum((p*10).astype(int),9)
            for b in range(10):
                ix=bins==b
                if not ix.any():continue
                nums=np.zeros(1000);dens=np.zeros(1000)
                for year in range(2015,2027):
                    j=np.flatnonzero(g.year.to_numpy()==year);n=len(j);block=60;starts=rng.integers(n,size=(1000,int(np.ceil(n/block))))
                    ids=j[((starts[:,:,None]+np.arange(block))%n).reshape(1000,-1)[:,:n]];w=bins[ids]==b;nums+=(w*y[ids]).sum(1);dens+=w.sum(1)
                boot=np.divide(nums,dens,out=np.full(1000,np.nan),where=dens>0);lo,hi=np.nanquantile(boot,[.025,.975])
                cal.append(dict(model=name,target=target,bin=b,n=int(ix.sum()),mean_prediction=float(p[ix].mean()),observed_frequency=float(y[ix].mean()),lo=float(lo),hi=float(hi),block=60,valid_reps=int(np.isfinite(boot).sum())))
    pd.DataFrame(cal).to_csv(R/'calibration.csv',index=False)
    # Calendar regimes chosen before the focused comparisons; retain all years.
    regimes=[]
    for name in pred.model.unique():
        for a,b in [(2015,2019),(2020,2022),(2023,2026)]:
            g=pred[(pred.model==name)&pred.year.between(a,b)];z=g[g.event_eligible]
            regimes.append(dict(model=name,period=f'{a}-{b}',n_one=len(g),n_event=len(z),event_brier=float(z.event_brier.mean()),event_rate=float(z.event_truth.mean()),categorical_logloss=float(g.categorical_logloss.mean()),stress_logloss=float(g.stress_logloss.mean())))
    pd.DataFrame(regimes).to_csv(R/'regime_scores.csv',index=False)
    # Isolate how much rare current contexts contribute; do not delete them.
    z=pred[(pred.model=='ternary20_30_k2')&pred.event_eligible]
    by=[]
    for label,mask in [('all',np.ones(len(z),bool)),('current_rare',z.state.isin([2,6])),('current_supported',~z.state.isin([2,6])),('forecast_ge0.1',z.event_pred>=.1),('forecast_ge0.5',z.event_pred>=.5)]:
        a=z[mask];by.append(dict(group=label,n=len(a),brier=float(a.event_brier.mean()),observed_rate=float(a.event_truth.mean()),mean_prediction=float(a.event_pred.mean())))
    pd.DataFrame(by).to_csv(R/'high_impact_origin_diagnostics.csv',index=False)
    print('Additional diagnostics complete')

if __name__=='__main__':main(sys.argv[1])
