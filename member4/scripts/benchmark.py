import json,time,numpy as np,pandas as pd,hashlib
from sc4055.model import *
from sc4055.estimation import *
cfg=json.loads((ROOT/'configs/production.json').read_text());cache=json.loads((ROOT/'results/raw/ideal_distribution_cache.json').read_text())
assert len(cache)==len(cfg['states'])*len(cfg['powers'])
# Cache distributions, never model truths, feed quantum shot generation.
lookup={(r['state'],r['power']):r for r in cache}
# Small estimator pilot runs before any production repetitions.
pilot=[]
for s in cfg['states']:
    for rep in range(cfg['pilot_repetitions']):
        seed=int(np.random.SeedSequence([cfg['seed'],s,rep,777]).generate_state(1)[0])
        h=np.random.default_rng(seed).binomial(200,[lookup[s,k]['p_flag'] for k in cfg['powers']])
        z=mle(h,[200]*4,cfg['powers'])
        assert z['success'] and np.isfinite(z['estimate'])
        pilot.append(dict(state=LABELS[s],replicate=rep,seed=seed,successes=h.tolist(),estimate=z['estimate'],optimizer_success=z['success']))
(ROOT/'results/raw/pilot_20_replicates.json').write_text(json.dumps(pilot,indent=2))
print('20-REPLICATE PILOT PASSED for each of five histories',flush=True)
raw=[];summaryrows=[];stages=[];modes=[]
for s in cfg['states']:
    p=dp(s);powers=cfg['powers'];probs=[lookup[s,k]['p_flag'] for k in powers]
    for n in cfg['shots_per_stage']:
        shots=[n]*len(powers);B=budget(powers,shots);qest=[];cest=[];qt=[];ct=[];fail=0;ambiguous=0
        for rep in range(cfg['repetitions']):
            seed=int(np.random.SeedSequence([cfg['seed'],s,n,rep,0]).generate_state(1)[0]);rng=np.random.default_rng(seed)
            t=time.perf_counter();h=rng.binomial(shots,probs);z=mle(h,shots,powers);qtime=time.perf_counter()-t
            mcseed=int(np.random.SeedSequence([cfg['seed'],s,n,rep,1]).generate_state(1)[0]);t=time.perf_counter();mc=monte_carlo(s,B,mcseed);ctime=time.perf_counter()-t
            qest.append(z['estimate']);cest.append(mc/B);qt.append(qtime);ct.append(ctime);fail+=not z['success'];ambiguous+=z['gap']<2
            row=dict(state=LABELS[s],state_index=s,shots_per_stage=n,budget=B,replicate=rep,quantum_seed=seed,classical_seed=mcseed,mlae=z['estimate'],mc=mc/B,mc_successes=mc,loglik=z['loglik'],mode_gap=z['gap'],optimizer_success=z['success'],mlae_fit_seconds=qtime,mc_seconds=ctime)
            raw.append(row)
            for k,hi in zip(powers,h):stages.append(dict(state=LABELS[s],shots=n,replicate=rep,power=k,successes=int(hi),seed=seed,circuit_sha256=lookup[s,k]['circuit_sha256'],query_units=n*(2*k+1)))
            modes.append(dict(state=LABELS[s],shots=n,replicate=rep,modes=z['modes']))
        # Independent method samples; bootstrap independent replicate pairs (no paired-seed coupling claim).
        rng=np.random.default_rng([cfg['seed'],s,n,99]);qe=(np.array(qest)-p)**2;ce=(np.array(cest)-p)**2
        ix=rng.integers(0,len(qe),(cfg['bootstrap_repetitions'],len(qe)));jx=rng.integers(0,len(ce),(cfg['bootstrap_repetitions'],len(ce)))
        diff=np.sqrt(qe[ix].mean(axis=1))-np.sqrt(ce[jx].mean(axis=1));ratio=np.sqrt(qe[ix].mean(axis=1)/ce[jx].mean(axis=1))
        rs=[lookup[s,k] for k in powers]
        for method,est,times in [('MLAE',qest,qt),('Monte Carlo',cest,ct)]:
            d=summary(est,p);d.update(state=LABELS[s],method=method,truth=p,budget=B,shots_per_stage=n,shots=4*n if method=='MLAE' else B,failure_rate=fail/200 if method=='MLAE' else 0,ambiguous_rate=ambiguous/200 if method=='MLAE' else 0,mean_runtime_seconds=float(np.mean(times)),circuit_width=20 if method=='MLAE' else 0,total_cx_per_rep=n*sum(r['cx'] for r in rs) if method=='MLAE' else 0,total_depth_sum_per_rep=n*sum(r['depth'] for r in rs) if method=='MLAE' else 0,unique_circuit_simulation_seconds=sum(r['simulation_seconds'] for r in rs) if method=='MLAE' else 0,rmse_difference_lo=float(np.quantile(diff,.025)),rmse_difference_hi=float(np.quantile(diff,.975)),rmse_ratio_lo=float(np.quantile(ratio,.025)),rmse_ratio_hi=float(np.quantile(ratio,.975)),rmse_ratio=float(np.sqrt(qe.mean()/ce.mean())),tail_absolute_error_gt_005=float(np.mean(abs(np.array(est)-p)>.05)))
            boot=(qe if method=='MLAE' else ce)[ix if method=='MLAE' else jx].mean(axis=1)**.5
            d.update(rmse_ci_lo=float(np.quantile(boot,.025)),rmse_ci_hi=float(np.quantile(boot,.975)))
            summaryrows.append(d)
        print(LABELS[s],n,'RMSE',summary(qest,p)['rmse'],summary(cest,p)['rmse'],flush=True)
        pd.DataFrame(raw).to_csv(ROOT/'results/raw/replicates.csv',index=False)
        pd.DataFrame(stages).to_csv(ROOT/'results/raw/shot_counts.csv',index=False)
        pd.DataFrame(summaryrows).to_csv(ROOT/'results/processed/benchmark_summary.csv',index=False)
        (ROOT/'results/raw/likelihood_modes.json').write_text(json.dumps(modes,indent=1))
print('BENCHMARK_COMPLETE',len(raw),'independent method-pairs',flush=True)
