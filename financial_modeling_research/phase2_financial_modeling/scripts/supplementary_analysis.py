"""Additional paired diagnostics, calibration uncertainty, stability and source audit."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.modeling import fit,event_dp,enumerate_event,contexts,predicate
from scripts.run_research import block_intervals
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results'


def main(data):
    df=pd.read_csv(data);df['date']=pd.to_datetime(df.DATE,format='%m/%d/%Y');df=df[df.date<='2026-10-23'].reset_index(drop=True)
    v=df.CLOSE.to_numpy();dates=df.date;pred=pd.read_csv(OUT/'outer_forecasts.csv.gz',low_memory=False)
    block_intervals(pred).to_csv(OUT/'paired_block_intervals.csv',index=False)
    # Within-year regime tables weighted by number of usable predictions.
    regimes=[]
    for name in ['binary30','ternary20_30','selected_policy','continuous_logVIX_ridge']:
        for k in sorted(pred.loc[pred.name==name,'k'].unique()):
            for a,b,label in [(2015,2019,'2015-2019'),(2020,2022,'2020-2022'),(2023,2026,'2023-2026')]:
                g=pred[(pred.name==name)&(pred.k==k)&pred.year.between(a,b)];e=g[g.event_eligible]
                regimes.append(dict(name=name,k=int(k),period=label,n=len(e),event_rate=float(e.event_truth.mean()),event_brier=float(e.event_brier.mean()),
                                    one_step_stress_logloss=float(g.stress_logloss.mean()) if g.stress_logloss.notna().any() else None))
    pd.DataFrame(regimes).to_csv(OUT/'regime_scores.csv',index=False)
    # Calibration intervals conditional on fitted probabilities, annual moving blocks.
    rng=np.random.default_rng(40552626);rows=[]
    for name,k in [('binary30',1),('binary30',2),('binary30',3),('ternary20_30',1),('continuous_logVIX_ridge',-1)]:
        g=pred[(pred.name==name)&(pred.k==k)]
        for label,pc,yc in [('event','event_pred','event_truth'),('one_step_stress','stress_pred','next_stress')]:
            gg=g[g.event_eligible].copy() if label=='event' else g.copy()
            gg=gg[gg[pc].notna()&gg[yc].notna()]
            if not len(gg):continue
            probs=gg[pc].to_numpy();truth=gg[yc].to_numpy();bins=np.minimum((probs*10).astype(int),9)
            for b in range(10):
                keep=bins==b
                if not keep.any():continue
                num=np.zeros(800);den=np.zeros(800)
                for year in sorted(gg.year.unique()):
                    ix=np.flatnonzero(gg.year.to_numpy()==year);n=len(ix);block=60
                    starts=rng.integers(n,size=(800,int(np.ceil(n/block))))
                    ids=((starts[:,:,None]+np.arange(block))%n).reshape(800,-1)[:,:n]
                    orig=ix[ids];w=(bins[orig]==b);num+=(w*truth[orig]).sum(1);den+=w.sum(1)
                boot=np.divide(num,den,out=np.full(800,np.nan),where=den>0)
                lo,hi=np.nanquantile(boot,[.025,.975])
                rows.append(dict(name=name,k=k,target=label,bin=b,n=int(keep.sum()),mean_pred=float(probs[keep].mean()),observed=float(truth[keep].mean()),lo=float(lo),hi=float(hi),usable_reps=int(np.isfinite(boot).sum()),block=60))
    pd.DataFrame(rows).to_csv(OUT/'calibration_intervals.csv',index=False)
    # Alternative final specification: conditional recommendation, not silent reselection.
    alt=json.loads((ROOT/'models/ternary20_30_k1/model.json').read_text());alt.update(role='supported_financial_alternative',
        selection_note='Better pooled retrospective primary-event Brier than binary order1; latest three-year difference smaller than recorded 0.001 engineering tolerance. No untouched confirmation.')
    (ROOT/'models/financial_alternative.json').write_text(json.dumps(alt,indent=2)+'\n')
    # Severe-state hitting references from binary35.
    m,_,_=fit(v,'binary35',1,len(v));severe=[]
    for s in range(m.n):
        dp=event_dp(m,6,1,kind='hit')[s];en=enumerate_event(m,s,6,1,kind='hit')
        severe.append(dict(state=s,DP=float(dp),enumeration=float(en),difference=abs(float(dp-en))))
    (OUT/'severe35_hit6.json').write_text(json.dumps({'model':{'threshold':35,'order':1,'counts':m.counts.tolist(),'emissions':m.p.tolist()},'event':'first severe entry within six trading observations when current<35; hit probability otherwise','values':severe},indent=2))
    # Reproduce prior static split independently; indexing matches prior report here.
    old=pd.read_csv(ROOT/'data/prior_evidence/vix_one_step_scores.csv')
    oldev=pd.read_csv(ROOT/'data/prior_evidence/vix_event_scores.csv')
    check=[];end=int(np.searchsorted(dates.to_numpy(),np.datetime64('2015-01-01')))
    for k in [1,2,3]:
        m,y,c=fit(v,'binary30',k,end)
        targets=np.flatnonzero(dates.to_numpy()>=np.datetime64('2020-01-01'))
        q=m.p[c[targets-1],1];z=y[targets]
        ll=float(np.mean(-z*np.log(q)-(1-z)*np.log1p(-q)))
        origins=np.array([t for t in range(len(y)-6) if dates[t]>=pd.Timestamp('2020-01-01')])
        a=event_dp(m)[c[origins]];zz=np.array([sum(y[t+1:t+7])>=3 for t in origins],int)
        bs=float(np.mean((a-zz)**2));pl=float(old[(old.model==f'order_{k}')&(old.split=='test')].logloss.iloc[0]);pb=float(oldev[(oldev.model==f'order_{k}')&(oldev.split=='test')].brier.iloc[0])
        check.append(dict(order=k,reproduced_logloss=ll,prior_logloss=pl,difference_logloss=ll-pl,reproduced_event_brier=bs,prior_event_brier=pb,difference_brier=bs-pb))
    (OUT/'prior_claim_reproduction.json').write_text(json.dumps(check,indent=2))
    # Selection sensitivity to the practical tolerance, using existing inner data only.
    f=json.loads((OUT/'final_selection.json').read_text());opts=[x for x in f['options'] if x['eligible_support']]
    best=min(x['inner_brier'] for x in opts);ss=[]
    for tol in [0,.00025,.0005,.001,.002]:
        w=min([x for x in opts if x['inner_brier']<=best+tol],key=lambda x:(x['states'],x['name']!='binary30'))
        ss.append({'tolerance':tol,**w})
    pd.DataFrame(ss).to_csv(OUT/'selection_tolerance_sensitivity.csv',index=False)
    # Explicit age-window training fits test nonstationarity, not new model optimization.
    stab=[]
    for a,b in [(1990,2002),(2003,2014),(2015,2019),(2020,2022),(2023,2026)]:
        values=v[(dates.dt.year>=a)&(dates.dt.year<=b)]
        for name in ['binary30','ternary20_30']:
            mm,_,_=fit(values,name,1,len(values))
            for row in mm.count_table():stab.append({'start_year':a,'end_year':b,'name':name,**row})
    pd.DataFrame(stab).to_csv(OUT/'subperiod_transition_estimates.csv',index=False)
    # Independent exact preservation check across supplied inputs.
    before=json.loads((ROOT/'data/manifests/source_preservation_before.json').read_text());after={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before if Path(p).is_file()}
    if len(after)==len(before):
        (ROOT/'validation/source_preservation.json').write_text(json.dumps({'all_unchanged':before==after,'before':before,'after':after},indent=2));assert before==after
    else:
        (ROOT/'validation/source_recheck_current_environment.json').write_text(json.dumps({'original_sources_available':len(after),'original_source_count':len(before),'available_sources_unchanged':all(before[p]==v for p,v in after.items()),'note':'Original source preservation record is retained; missing supplied files cannot be reverified in this environment.'},indent=2))
    print('Supplementary analyses complete. Prior max loss difference',max(abs(x['difference_logloss']) for x in check))


if __name__=='__main__':main(Path(sys.argv[1]))
