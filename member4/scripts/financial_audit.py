"""Verify acquired data/counts and recompute preserved historical forecast scores."""
import argparse,json,time,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from sc4055.model import *
p=argparse.ArgumentParser();p.add_argument('--csv',type=Path);args=p.parse_args();out={}
if args.csv:
    b=args.csv.read_bytes();d=pd.read_csv(args.csv);d['date']=pd.to_datetime(d.DATE,format='%m/%d/%Y');assert not d.date.duplicated().any();d=d[d.date<='2026-10-23'].sort_values('date')
    canonical=pd.DataFrame({'date':d.date.dt.strftime('%Y-%m-%d'),'CLOSE':d.CLOSE}).to_csv(index=False,float_format='%.6f').encode()
    manifest=json.loads((ROOT/'archive/SC4055_V3_Research_Handoff/phase3_nine_state_validation/data/manifests/vix_manifest.json').read_text())
    assert hashlib.sha256(canonical).hexdigest()==manifest['clean_date_close_sha256']
    x=np.digitize(d.CLOSE.to_numpy(),[20,30]);counts=np.zeros((9,3),int)
    for a,b,c in zip(x[:-2],x[1:-1],x[2:]):counts[3*a+b,c]+=1
    assert np.array_equal(counts,SPEC['counts']);out['data']=dict(status='PASSED',rows=len(d),counts=counts.tolist(),raw_sha256=hashlib.sha256(args.csv.read_bytes()).hexdigest(),canonical_sha256=hashlib.sha256(canonical).hexdigest())
f=ROOT/'archive/SC4055_V3_Research_Handoff/phase3_nine_state_validation/results/forecasts.csv.gz';df=pd.read_csv(f)
print('Forecast columns',list(df),flush=True)
out['forecast_columns']=list(df)
scores=[]
for model,d in df.groupby('model'):
    a=d[d.event_eligible]
    e=(a.event_pred-a.event_truth)**2
    assert np.max(abs(e-a.event_brier))<1e-12
    scores.append(dict(model=model,n_event=len(a),event_brier=float(e.mean()),next_category_logloss=float(d.categorical_logloss.mean())))
out['recomputed_historical_scores']=scores
pd.DataFrame(scores).to_csv(ROOT/'results/processed/historical_scores.csv',index=False)
# Binary order 3 and the direct-event regression were validated in Phase 2.
prior=pd.read_csv(ROOT/'archive/SC4055_V3_Research_Handoff/phase2_financial_modeling/results/outer_summary.csv')
prior.to_csv(ROOT/'results/processed/phase2_historical_comparators.csv',index=False)
# Timing exact DP independent of any quantum cache.
ts=[]
for _ in range(100):
    t=time.perf_counter();pr=[dp(s) for s in range(9)];ts.append(time.perf_counter()-t)
out['dp_timing']=dict(repeats=100,all_nine_median_seconds=float(np.median(ts)),per_state_median_seconds=float(np.median(ts)/9))
out['exact_events']=[dict(state=LABELS[s],probability=float(dp(s,rational=True)),rational=str(dp(s,rational=True))) for s in range(9)]
out['memory']=dict(classical_dimension=9,quantum_dimension=9,classical_fixed_bits=4,physical_memory_qubits=4,total_qubits=20,Cmu=MEM['stationary_classical_entropy'],Cq=MEM['stationary_quantum_entropy'])
(ROOT/'results/processed/financial_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
