"""Independently rerun one raw production trial per history at budget 3600."""
import json,numpy as np,pandas as pd
from sc4055.model import ROOT,monte_carlo
from sc4055.estimation import mle
raw=pd.read_csv(ROOT/'results/raw/replicates.csv',dtype={'state':str});cache=json.loads((ROOT/'results/raw/ideal_distribution_cache.json').read_text());rows=[]
for state,d in raw[raw.budget==3600].groupby('state'):
    r=d.iloc[0];s=int(r.state_index);probs=[next(z['p_flag'] for z in cache if z['state']==s and z['power']==k) for k in [0,1,2,4]]
    h=np.random.default_rng(int(r.quantum_seed)).binomial([200]*4,probs);z=mle(h,[200]*4,[0,1,2,4]);mc=monte_carlo(s,3600,int(r.classical_seed))
    assert abs(z['estimate']-r.mlae)<1e-14 and mc==r.mc_successes
    rows.append(dict(state=state,mlae=z['estimate'],mc_successes=mc,status='PASSED'))
print(json.dumps(rows,indent=2))
