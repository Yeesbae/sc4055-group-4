"""Reproduce all Phase-2 fits and validation from official CSV.
Usage: python scripts/run_research.py --data private_data/VIX_History.csv
"""
import argparse,hashlib,itertools,json,platform,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from scipy.optimize import minimize
from scipy.special import expit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.modeling import fit,discretize,contexts,event_dp,enumerate_event,score_forecasts,Model
from src.structure import quantum_diagnostic
from src.modeling import exact_partition,rank_modular

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results'
CFG=json.loads((ROOT/'configs/protocol.json').read_text());SEED=CFG['bootstrap']['seed']

def write(path,obj):
    (ROOT/path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def fit_record(model,year,dates):
    """Full mathematical record for every fit, including sensitivity scenarios."""
    part=exact_partition(model);blocks=part['blocks'];reps=[blocks.index(b) for b in range(part['D_c'])]
    minimal_next=[[blocks[j] for j in model.nxt[s]] for s in reps]
    return {'name':model.name,'order':model.k,'alphabet_size':model.m,'alpha':model.alpha,'score_year':year,
            'fit_end':str(dates[model.train_end-1].date()),'edges':model.edges,'state_indexing':'base m, oldest to newest',
            'state_labels':model.labels,'emissions':model.p.tolist(),'lambda':model.nxt.tolist(),
            'T_emission':model.matrices().tolist(),'T':model.matrices().sum(0).tolist(),
            'context_estimates':model.count_table(),'stationary_occupancy':model.stationary().tolist(),
            'reachable_states':list(range(model.n)),'normalization_residual':float(np.max(np.abs(model.p.sum(1)-1))),
            'minimum_emission':float(model.p.min()),'predictive_partition':part,
            'minimal_emissions':model.p[reps].tolist(),'minimal_lambda':minimal_next,
            'probability_rank':rank_modular(model)}

def dataset(path):
    b=path.read_bytes();df=pd.read_csv(path);df['date']=pd.to_datetime(df.DATE,format='%m/%d/%Y',errors='raise')
    integrity={'raw_rows':len(df),'duplicates':int(df.date.duplicated().sum()),
               'missing_close':int(df.CLOSE.isna().sum()),'missing_all_fields':df.isna().sum().to_dict(),
               'unsorted':not df.date.is_monotonic_increasing}
    if integrity['duplicates'] or integrity['missing_close']:raise ValueError('Integrity failure; do not silently repair')
    df=df.sort_values('date');future=int((df.date>pd.Timestamp(CFG['data_cutoff'])).sum())
    df=df[df.date<=pd.Timestamp(CFG['data_cutoff'])].reset_index(drop=True)
    canonical=pd.DataFrame({'date':df.date.dt.strftime('%Y-%m-%d'),'CLOSE':df.CLOSE}).to_csv(index=False,float_format='%.6f').encode('utf-8')
    canonical_hash=hashlib.sha256(canonical).hexdigest()
    if canonical_hash!=CFG.get('expected_clean_date_close_sha256',canonical_hash):
        raise ValueError('Official historical prefix differs from the frozen snapshot; do not silently rerun a revised series. Preserve new bytes and version the investigation.')
    if not (df.CLOSE>0).all():raise ValueError('Nonpositive index level')
    gaps=df.date.diff().dt.days.fillna(0)
    weekends=df.date.dt.dayofweek>=5
    info={'source_url':'https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv',
          'resolved_url':'https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv',
          'download_date':'2026-10-25','sha256':hashlib.sha256(b).hexdigest(),'raw_bytes':len(b),
          **integrity,'clean_date_close_sha256':canonical_hash,'rows_used':len(df),'coverage':[str(df.date.min().date()),str(df.date.max().date())],
          'excluded_after_cutoff':future,'weekend_rows':int(weekends.sum()),
          'gap_days_histogram':gaps.astype(int).value_counts().sort_index().to_dict(),
          'long_gaps_over4_days':[{'next_date':str(df.date[i].date()),'gap_days':int(gaps[i])} for i in np.flatnonzero(gaps.to_numpy()>4)],
          'cleaning':'Parse dates strictly, reject duplicates/missing/nonpositive closes, sort ascending, cap at 2026-10-23. No forward filling, no calendar-day interpolation. CLOSE only.',
          'calendar_check':'Rows are source trading observations, not inferred business-day rows. No independent exchange holiday-calendar reconciliation; gaps are flagged, not assumed missing.',
          'methodology':'2003 SPX wide-strike method replaced original OEX VIX (now VXO); supplied history back to 1990. Weekly options added 2014-10-06; this change was not backdated. Mixed methodology remains a regime caveat.',
          'licensing':'Official public download verified; raw redistribution license not established. Raw CSV is kept private and excluded from ZIP; download script and hash included.',
          'data_unit':'Index-level daily observations, not borrower-level/default/security loss data'}
    write('data/manifests/vix_manifest.json',info)
    return df


def baseline_forecasts(values,dates,train_end,origins):
    stress=values>=30;L=6
    training_origins=np.arange(1,train_end-L)
    train_z=np.array([sum(stress[t+1:t+L+1])>=3 for t in training_origins],int)
    current=stress[training_origins].astype(int)
    empirical=[]
    for h in (0,1):
        zz=train_z[current==h];empirical.append((sum(zz)+.5)/(len(zz)+1))
    # Fixed ridge direct-event regression; no future feature at an origin.
    lv=np.log(values);change=np.r_[0,np.diff(lv)]
    features=np.column_stack([lv,change]);mu=features[training_origins].mean(0);sd=features[training_origins].std(0)
    X=np.column_stack([np.ones(len(training_origins)),(features[training_origins]-mu)/sd])
    def fun(w):
        z=X@w;return float(np.logaddexp(0,z).sum()-train_z@z+.5*(w[1:]@w[1:]))
    def jac(w):return X.T@(expit(X@w)-train_z)+np.r_[0,w[1:]]
    opt=minimize(fun,np.zeros(3),jac=jac,method='BFGS',options={'gtol':1e-6})
    pred=expit(np.column_stack([np.ones(len(origins)),(features[origins]-mu)/sd])@opt.x)
    grad=float(np.max(np.abs(jac(opt.x))))
    return {'event_climatology':np.full(len(origins),(sum(train_z)+.5)/(len(train_z)+1)),
            'current_state_event_frequency':np.asarray(empirical)[stress[origins].astype(int)],
            'continuous_logVIX_ridge':pred,
            'persistence':stress[origins].astype(float)}, {'ridge_success':bool(opt.success or grad<1e-4),'ridge_message':str(opt.message),'ridge_gradient_max':grad,'ridge_coefficients':opt.x.tolist(),
                                                         'training_event_origins':len(training_origins),'last_training_event_end':str(dates[train_end-1].date())}


def score_records(model,y,ctx,dates,year):
    mask=dates.dt.year.to_numpy()==year;ix=np.flatnonzero(mask)
    start=int(ix[0]);end=int(ix[-1])+1
    ts=np.arange(max(3,start-1),end-1)  # target t+1 belongs to year
    scored=score_forecasts(model,y,ctx,ts)
    valid=ts+6<end
    rows=[]
    for i,t in enumerate(ts):
        row={'year':year,'date':str(dates[t].date()),'next_date':str(dates[t+1].date()),
             'name':model.name,'k':model.k,'alpha':model.alpha,'train_end':str(dates[model.train_end-1].date()),
             'event_eligible':bool(valid[i]),'state':int(ctx[t])}
        for key,val in scored.items():
            if key=='state':continue
            row[key]=float(val[i])
        if not valid[i]:
            for key in ['event_truth','event_brier']:row[key]=np.nan
        rows.append(row)
    return rows,ts,valid


def summarize(rows):
    d=pd.DataFrame(rows);out=[]
    for keys,g in d.groupby(['year','name','k','alpha'],sort=False):
        ev=g[g.event_eligible]
        r=dict(zip(['year','name','k','alpha'],keys));r.update(n_one=len(g),n_event=len(ev))
        for col in ['categorical_logloss','categorical_brier','stress_logloss','stress_brier']:r[col]=float(g[col].mean())
        r.update(event_brier=float(ev.event_brier.mean()),event_rate=float(ev.event_truth.mean()),event_mean_pred=float(ev.event_pred.mean()))
        out.append(r)
    return pd.DataFrame(out)


def choose(foldmeta,foldscores,years):
    options=[]
    for name in CFG['principal_candidates']:
        for k in CFG['orders']:
            z=foldscores[(foldscores.name==name)&(foldscores.k==k)&foldscores.year.isin(years)]
            meta=[foldmeta[(name,k,y)] for y in years]
            eligible=all(r['min_count']>=25 for r in meta)
            options.append({'name':name,'k':k,'states':(2 if name=='binary30' else 3)**k,
                            'inner_brier':float(np.average(z.event_brier,weights=z.n_event)),
                            'eligible_support':eligible,'min_training_context_count':min(r['min_count'] for r in meta)})
    eligible=[r for r in options if r['eligible_support']]
    best=min(r['inner_brier'] for r in eligible)
    within=[r for r in eligible if r['inner_brier']<=best+CFG['practical_tie_brier']]
    winner=min(within,key=lambda r:(r['states'],r['name']!='binary30',r['k']))
    return winner,options


def block_intervals(pred):
    """Conditional paired score bootstrap; annual blocks preserve model boundaries."""
    rng=np.random.default_rng(SEED);rows=[];B=CFG['bootstrap']['reps']
    base=pred[(pred.name=='binary30')&(pred.k==1)].copy()
    base=base.set_index(['year','date'])
    comparisons=[('binary30',k) for k in (0,2,3)]+[('ternary20_30',k) for k in (1,2,3)]+[('selected_policy',-1),('continuous_logVIX_ridge',-1),('current_state_event_frequency',-1)]
    for name,k in comparisons:
        g=pred[(pred.name==name)&(pred.k==k)].set_index(['year','date'])
        both=g.join(base[['event_brier','stress_logloss']],rsuffix='_base',how='inner')
        for metric in ['event_brier','stress_logloss']:
            if both[metric].isna().all():continue
            for scope,years in [('all',range(2015,2027)),('2015-2019',range(2015,2020)),('2020-2022',range(2020,2023)),('2023-2026',range(2023,2027))]:
                chunks=[]
                for y in years:
                    if y not in both.index.get_level_values(0):continue
                    z=both.loc[y];v=(z[metric]-z[metric+'_base']).dropna().to_numpy()
                    if len(v):chunks.append(v)
                if not chunks:continue
                total=sum(map(len,chunks));point=sum(v.sum() for v in chunks)/total
                for block in CFG['bootstrap']['blocks']:
                    acc=np.zeros(B)
                    for v in chunks:
                        n=len(v);starts=rng.integers(n,size=(B,int(np.ceil(n/block))))
                        ids=(starts[:,:,None]+np.arange(block))%n;ids=ids.reshape(B,-1)[:,:n]
                        acc+=v[ids].sum(1)
                    lo,hi=np.quantile(acc/total,[.025,.975])
                    rows.append(dict(name=name,k=k,baseline='binary30_k1',metric=metric,scope=scope,block=block,reps=B,n=total,difference=float(point),lo=float(lo),hi=float(hi)))
    return pd.DataFrame(rows)


def calibration(pred):
    rows=[]
    for (name,k),g in pred.groupby(['name','k']):
        for target,pcol,ycol in [('event','event_pred','event_truth'),('one_step_stress','stress_pred','next_stress')]:
            z=g[g.event_eligible] if target=='event' else g
            if z[pcol].isna().all():continue
            z=z[z[ycol].notna()].copy();bins=np.minimum((z[pcol].to_numpy()*10).astype(int),9)
            for b in range(10):
                mask=bins==b
                if not mask.any():continue
                rows.append(dict(name=name,k=k,target=target,bin=b,n=int(mask.sum()),mean_pred=float(z[pcol].to_numpy()[mask].mean()),observed=float(z[ycol].to_numpy()[mask].mean())))
    return pd.DataFrame(rows)


def export_model(model,tag,df):
    tx=model.matrices();p=OUT # ensure all machine-readable arrays under models
    d=ROOT/'models'/tag;d.mkdir(exist_ok=True)
    pd.DataFrame(model.count_table()).to_csv(d/'context_counts.csv',index=False)
    for x,t in enumerate(tx):np.savetxt(d/f'T_{x}.csv',t,delimiter=',',fmt='%.17g')
    np.savetxt(d/'T.csv',tx.sum(0),delimiter=',',fmt='%.17g')
    diag=quantum_diagnostic(model)
    partition=diag['partition'];blocks=partition['blocks'];Dc=partition['D_c']
    reps=[blocks.index(b) for b in range(Dc)]
    qp=model.p[reps];qn=np.array([[blocks[j] for j in model.nxt[i]] for i in reps])
    qt=np.zeros((model.m,Dc,Dc))
    for i in range(Dc):
        for x in range(model.m):qt[x,i,qn[i,x]]=qp[i,x]
    qpi=np.array([sum(model.stationary()[i] for i in range(model.n) if blocks[i]==b) for b in range(Dc)])
    quotient={'D_c':Dc,'original_history_count':model.n,'original_to_minimal':blocks,'representatives':reps,
              'emissions':qp.tolist(),'lambda':qn.tolist(),'T_emission':qt.tolist(),'T':qt.sum(0).tolist(),
              'stationary_occupancy':qpi.tolist(),'note':'Exact quotient of fixed fitted process. Aggregate counts are not resmoothed; inherited probabilities preserve all future laws.'}
    write(f'models/{tag}/minimal_predictive_model.json',quotient)
    if Dc<model.n:
        from types import SimpleNamespace
        qq=SimpleNamespace(n=Dc,m=model.m,k=model.k,p=qp,nxt=qn,
                           fractions=lambda:[model.fractions()[i] for i in reps],stationary=lambda:qpi)
        qd=quantum_diagnostic(qq)
        write(f'models/{tag}/minimal_structural_diagnostics.json',qd)
        diag['minimized_diagnostic_reference']='minimal_structural_diagnostics.json'
        diag['unminimized_singular_reason']='Exact redundant histories; use canonical quotient before numerical factorization.'
    write(f'models/{tag}/structural_diagnostics.json',diag)
    ev=event_dp(model);enum=np.array([enumerate_event(model,s) for s in range(model.n)])
    assert np.max(np.abs(ev-enum))<1e-12
    spec={'model_version':CFG['version'],'tag':tag,'observation':model.name,'thresholds':model.edges,
          'indexing':'oldest to newest, state integer is base-m encoding; symbols >= threshold use upper bin',
          'state_labels':model.labels,'order':model.k,'alphabet':list(range(model.m)),'alpha_per_symbol':model.alpha,
          'counts':model.counts.tolist(),'emission_probabilities':model.p.tolist(),
          'emission_probabilities_rational':[[str(q) for q in row] for row in model.fractions()],
          'lambda':model.nxt.tolist(),'T_emission':tx.tolist(),'T':tx.sum(0).tolist(),
          'stationary_occupancy':model.stationary().tolist(),'reachable_states':list(range(model.n)),
          'reachability_proof':'Dirichlet smoothing gives every symbol positive probability; each length-k word reaches its own context from any start. Irreducible with self loops, unique stationary distribution.',
          'causal_minimization':diag['partition'],'event':CFG['primary_event'],
          'high_symbol':model.m-1,'exact_model_event_probabilities':ev.tolist(),
          'enumeration_DP_max_difference':float(np.max(np.abs(ev-enum))),
          'fit_coverage':[str(df.date.iloc[0].date()),str(df.date.iloc[model.train_end-1].date())],
          'data_manifest':'data/manifests/vix_manifest.json','threshold_rationale':'fixed 30 persistent stress proxy; 20 split tests moderate-state information. No official default/risk cutoff.',
          'validation':'retrospective nested rolling-origin forecasts, prospective holdout unavailable; deployment refit is not retrospectively scored as an untouched model',
          'uncertainty':'context_counts.csv contains nominal Dirichlet/Beta intervals; event_uncertainty.csv adds posterior propagation and dependent block refits; nonstationarity unresolved'}
    write(f'models/{tag}/model.json',spec)
    return spec,diag


def model_uncertainty(model):
    rng=np.random.default_rng(SEED+model.k+model.m);rows=[];B=500
    # Nominal Dirichlet posterior under homogeneous Markov likelihood.
    ps=[np.vstack([rng.dirichlet(row+model.alpha) for row in model.counts]) for _ in range(B)]
    for method,probs in [('Dirichlet_posterior',ps)]:
        vals=[]
        for p in probs:
            z=Model(model.name,model.k,model.m,model.alpha,model.edges,model.counts,p,model.nxt,model.train_end);vals.append(event_dp(z))
        for s in range(model.n):
            lo,hi=np.quantile(np.array(vals)[:,s],[.025,.975]);rows.append(dict(state=s,method=method,block=0,replicates=B,lo=float(lo),hi=float(hi)))
    return rows


def dependent_parameter_refits(model, values):
    """Resample original context/next pairs in circular blocks, never stitch symbols.
    This retains within-block history dependence and avoids invented boundary transitions.
    """
    rng=np.random.default_rng(SEED+99+model.k);out=[];B=500
    y,_=discretize(values,model.name,model.train_end);ctx=contexts(y,model.k,model.m)
    target=np.arange(model.k,model.train_end)
    flat=(ctx[target-1] if model.k else np.zeros(len(target),int))*model.m+y[target]
    n=len(flat)
    for block in [20,60,120]:
        probs=[];events=[]
        for _ in range(B):
            starts=rng.integers(n,size=int(np.ceil(n/block)))
            ids=((starts[:,None]+np.arange(block))%n).ravel()[:n]
            counts=np.bincount(flat[ids],minlength=model.n*model.m).reshape(model.n,model.m)
            pp=(counts+model.alpha)/(counts.sum(1,keepdims=True)+model.m*model.alpha)
            z=Model(model.name,model.k,model.m,model.alpha,model.edges,counts,pp,model.nxt,model.train_end)
            events.append(event_dp(z));probs.append(pp)
        for s in range(model.n):
            lo,hi=np.quantile(np.array(events)[:,s],[.025,.975])
            out.append(dict(state=s,method='context_pair_block_refit',block=block,replicates=B,lo=float(lo),hi=float(hi)))
        np.savez_compressed(ROOT/f'results/{model.name}_k{model.k}_block{block}_parameter_draws.npz',emissions=np.array(probs),events=np.array(events))
    return out


def main():
    t0=time.time();ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);args=ap.parse_args()
    df=dataset(args.data);v=df.CLOSE.to_numpy();dates=df.date;years=dates.dt.year.to_numpy();foldmeta={};allrows=[];fm=[];transition_history=[];secondary=[];fit_records=[]
    for year in range(2012,2027):
        train_end=int(np.searchsorted(dates.to_numpy(),np.datetime64(f'{year}-01-01')))
        if not (years==year).any():continue
        for name in CFG['candidate_discretizations']:
            for k in CFG['orders']:
                model,y,ctx=fit(v,name,k,train_end)
                fit_records.append(fit_record(model,year,dates))
                rows,ts,valid=score_records(model,y,ctx,dates,year);allrows.extend(rows)
                r={'name':name,'k':k,'year':year,'thresholds':model.edges,'train_end':train_end,
                   'min_count':int(model.counts.sum(1).min()),'zero_contexts':int((model.counts.sum(1)==0).sum()),
                   'sparse_contexts':int((model.counts.sum(1)<25).sum()),'states':model.n}
                foldmeta[(name,k,year)]=r;fm.append(r)
                if name in CFG['principal_candidates']:
                    for row in model.count_table():transition_history.append({'year':year,'name':name,'k':k,**row})
                    if year>=2015:
                        it=ts[valid];states=ctx[it]
                        for ev,kind,K in [('hit6','hit',1),('run3in6','run',3)]:
                            a=event_dp(model,6,K,kind=kind)[states]
                            from src.modeling import predicate
                            z=np.array([predicate(y[t+1:t+7],kind,K,model.m-1) for t in it],int)
                            secondary.append(dict(year=year,name=name,k=k,event=ev,n=len(it),brier=float(np.mean((a-z)**2)),rate=float(z.mean()),mean_pred=float(a.mean())))
                        if k:
                            ix=(states%model.m)<model.m-1;a=event_dp(model,6,1,kind='hit')[states]
                            z=np.array([any(y[t+1:t+7]>=model.m-1) for t in it],int)
                            secondary.append(dict(year=year,name=name,k=k,event='first_entry_high6_current_not_high',n=int(ix.sum()),brier=float(np.mean((a[ix]-z[ix])**2)),rate=float(z[ix].mean()),mean_pred=float(a[ix].mean())))
        print('Completed historical year',year,flush=True)
    scores=summarize(allrows);scores.to_csv(OUT/'fold_scores.csv',index=False);write('results/fold_definitions.json',fm)
    pd.DataFrame(transition_history).to_csv(OUT/'transition_history.csv',index=False)
    pd.DataFrame(secondary).to_csv(OUT/'secondary_event_scores.csv',index=False)
    pred=pd.DataFrame(allrows);outer=pred[pred.year>=2015].copy();selections=[]
    for year in CFG['outer_test_years']:
        winner,options=choose(foldmeta,scores,[year-3,year-2,year-1])
        selections.append({'outer_year':year,'selected':winner,'options':options})
        z=outer[(outer.year==year)&(outer.name==winner['name'])&(outer.k==winner['k'])].copy();z['source_model']=winner['name'];z['source_order']=winner['k'];z['name']='selected_policy';z['k']=-1
        outer=pd.concat([outer,z],ignore_index=True)
    write('results/nested_selections.json',selections)
    # Strong event-only baselines with features available at each origin.
    baseline_meta=[]
    for year in CFG['outer_test_years']:
        z=outer[(outer.year==year)&(outer.name=='binary30')&(outer.k==1)].copy()
        train_end=int(np.searchsorted(dates.to_numpy(),np.datetime64(f'{year}-01-01')))
        lookup={str(d.date()):i for i,d in enumerate(dates)};origins=np.array([lookup[x] for x in z.date])
        bp,meta=baseline_forecasts(v,dates,train_end,origins);baseline_meta.append({'year':year,**meta})
        for name,a in bp.items():
            w=z.copy();w['name']=name;w['k']=-1;w['event_pred']=a;w['event_brier']=(a-w.event_truth)**2
            for c in ['categorical_logloss','categorical_brier','stress_logloss','stress_brier','stress_pred']:w[c]=np.nan
            outer=pd.concat([outer,w],ignore_index=True)
    write('results/direct_baseline_fits.json',baseline_meta)
    # Serialize and verify before publishing the compressed forecast ledger.
    import gzip
    forecast_bytes=outer.to_csv(index=False).encode('utf-8')
    packed=gzip.compress(forecast_bytes,mtime=0)
    (OUT/'outer_forecasts.csv.gz').write_bytes(packed)
    assert gzip.decompress((OUT/'outer_forecasts.csv.gz').read_bytes())==forecast_bytes
    write('validation/forecast_ledger_integrity.json',{'rows':len(outer),'csv_bytes':len(forecast_bytes),'gzip_bytes':len(packed),'sha256':hashlib.sha256(packed).hexdigest(),'roundtrip_verified':True})
    summary=[]
    for (name,k),g in outer.groupby(['name','k']):
        e=g[g.event_eligible];r={'name':name,'k':int(k),'n_one':len(g),'n_event':len(e),'event_brier':float(e.event_brier.mean()),'event_rate':float(e.event_truth.mean()),'mean_pred':float(e.event_pred.mean())}
        for c in ['categorical_logloss','categorical_brier','stress_logloss','stress_brier']:
            r[c]=float(g[c].mean()) if g[c].notna().any() else None
        summary.append(r)
    pd.DataFrame(summary).to_csv(OUT/'outer_summary.csv',index=False)
    block_intervals(outer).to_csv(OUT/'paired_block_intervals.csv',index=False)
    calibration(outer).to_csv(OUT/'calibration.csv',index=False)
    # Alpha sensitivity on the same primary binary target, no selection.
    sens=[]
    for alpha in CFG['alpha_sensitivity']:
        for year in CFG['outer_test_years']:
            end=int(np.searchsorted(dates.to_numpy(),np.datetime64(f'{year}-01-01')))
            for name in CFG['principal_candidates']:
                for k in CFG['orders']:
                    model,y,c=fit(v,name,k,end,alpha);r,_,_=score_records(model,y,c,dates,year);sens.extend(r)
                    fit_records.append(fit_record(model,year,dates))
    summarize(sens).to_csv(OUT/'smoothing_sensitivity.csv',index=False)
    fit_bytes=json.dumps(fit_records,separators=(',',':'),allow_nan=False).encode('utf-8')
    (OUT/'all_fitted_models.json.gz').write_bytes(gzip.compress(fit_bytes,mtime=0))
    assert gzip.decompress((OUT/'all_fitted_models.json.gz').read_bytes())==fit_bytes
    # Exact event battery, all states, every principal order. Freeze full-history refits.
    final_winner,options=choose(foldmeta,scores,CFG['future_final_selection_validation_years'])
    write('results/final_selection.json',{'selected':final_winner,'options':options,'validation_years':[2023,2024,2025],
                                        'deploy_refit_end':CFG['data_cutoff'],'claim':'future-use specification, not new confirmatory historical evidence'})
    event_rows=[];struct=[];uncert=[];models={}
    for name in CFG['principal_candidates']:
        for k in CFG['orders']:
            model,y,c=fit(v,name,k,len(v));tag=f'{name}_k{k}';models[tag]=model
            spec,diag=export_model(model,tag,df)
            struct.append({'tag':tag,'states':model.n,'minimum_count':int(model.counts.sum(1).min()),'Cmu':diag.get('stationary_classical_entropy'),
                           'Cq':diag.get('stationary_quantum_entropy'),'rank_exact':diag['probability_rank']['rational_probability_rank_exact'],
                           'Dq_lower_bound':diag['probability_rank']['quantum_dimension_lower_bound'],'instrument_pass':diag.get('instrument_numerically_valid',False),
                           'min_Gram_eigenvalue_float':min(diag['eigenvalues_float64']),'width_estimate':diag['registers']['total_width_upper_bound_design']})
            for event,kind,K in [('count3of6','count',3),('hit6','hit',1),('run3in6','run',3)]:
                dp=event_dp(model,6,K,kind=kind)
                for s in range(model.n):
                    en=enumerate_event(model,s,6,K,kind=kind)
                    event_rows.append({'tag':tag,'state':s,'event':event,'DP':float(dp[s]),'enumeration':float(en),'difference':float(abs(dp[s]-en))})
            # First entry conditioned current not high; category upgrade hit event.
            for s in range(model.n):
                if k and s%model.m<model.m-1:
                    a=event_dp(model,6,1,kind='hit')[s]
                    event_rows.append({'tag':tag,'state':s,'event':'first_entry_high6_current_not_high','DP':float(a),'enumeration':float(enumerate_event(model,s,6,1,kind='hit')),'difference':float(abs(a-enumerate_event(model,s,6,1,kind='hit')))})
                if k and model.m==3 and s%3<2:
                    high=s%3+1;a=event_dp(model,6,1,high=high,kind='hit')[s];en=enumerate_event(model,s,6,1,high=high,kind='hit')
                    event_rows.append({'tag':tag,'state':s,'event':'higher_category_within6','DP':float(a),'enumeration':float(en),'difference':float(abs(a-en))})
    principal=f"{final_winner['name']}_k{final_winner['k']}";fallback='binary30_k0'
    for tag in dict.fromkeys([principal,fallback,'binary30_k2','binary30_k3']):
        for r in model_uncertainty(models[tag])+dependent_parameter_refits(models[tag],v):uncert.append({'tag':tag,**r})
    pd.DataFrame(uncert).to_csv(OUT/'event_uncertainty.csv',index=False)
    pd.DataFrame(event_rows).to_csv(OUT/'exact_event_checks.csv',index=False)
    pd.DataFrame(struct).to_csv(OUT/'quantum_readiness.csv',index=False)
    # Freeze aliases retain complete specs and exact matrices, no borrowed V2 parameters.
    for role,tag in [('principal',principal),('fallback',fallback)]:
        obj=json.loads((ROOT/f'models/{tag}/model.json').read_text());obj['role']=role;obj['selected_tag']=tag
        write(f'models/frozen_{role}.json',obj)
    # Full-data threshold summaries are descriptive only, never fed into selectors.
    desc=[]
    for name in CFG['candidate_discretizations']:
        y,edges=discretize(v,name,len(v));pops=np.bincount(y,minlength=len(edges)+1)
        desc.append({'name':name,'edges':edges,'counts':pops.tolist(),'rates':(pops/len(y)).tolist(),
                     'interpretation':'descriptive; quantile thresholds were independently fitted in each historical training fold'})
    write('results/discretization_descriptive.json',desc)
    # Within-bin spread quantifies discarded level information, not proof of Markov order.
    loss=[]
    for name in CFG['candidate_discretizations']:
        y,edges=discretize(v,name,len(v));train_end=int(np.searchsorted(dates.to_numpy(),np.datetime64('2015-01-01')))
        yy,ee=discretize(v,name,train_end);centres=np.array([v[:train_end][yy[:train_end]==x].mean() for x in range(len(ee)+1)])
        for lo,hi,label in [(0,train_end,'train1990_2014'),(train_end,len(v),'retrospective2015_2026')]:
            z=v[lo:hi];r=centres[yy[lo:hi]]
            loss.append({'name':name,'period':label,'thresholds':str(ee),'squared_level_reconstruction_error':float(np.mean((z-r)**2)),
                         'level_variance':float(np.var(z)),'fraction_variance_lost':float(np.mean((z-r)**2)/np.var(z))})
    pd.DataFrame(loss).to_csv(OUT/'discretization_information_loss.csv',index=False)
    write('validation/run_summary.json',{'elapsed_seconds':time.time()-t0,'fitted_model_records':len(fit_records),'seed':SEED,'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'platform':platform.platform(),
                                         'principal':principal,'fallback':fallback,'max_exact_event_difference':max(r['difference'] for r in event_rows),
                                         'confirmatory_test_available':False,'full_quantum_circuits_implemented':False,'all_direct_fits_pass':all(m['ridge_success'] for m in baseline_meta)})
    print('Principal',principal,'fallback',fallback,'elapsed',time.time()-t0,flush=True)

if __name__=='__main__':main()
