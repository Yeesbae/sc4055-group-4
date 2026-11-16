"""Focused retrospective validation of the three-level second-order candidate."""
import gzip,json,hashlib,itertools,sys,time
from pathlib import Path
from fractions import Fraction
from collections import Counter
import numpy as np
import pandas as pd
from scipy.stats import beta
from .modeling import fit,contexts,score_forecasts,event_dp,enumerate_event,Model,exact_partition,rank_modular
from .structure import quantum_diagnostic
from .phase_bounds import all_phase_certificate,rational_determinant,future_amplitude

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results';CFG=json.loads((ROOT/'configs/protocol.json').read_text())
SEED=CFG['paired_bootstrap']['seed']
MEANINGS=['low -> low','low -> moderate','low -> high (abrupt stress entry)',
          'moderate -> low (cooling)','moderate -> moderate','moderate -> high (stress entry)',
          'high -> low (abrupt cooling)','high -> moderate (recent stress exit)','high -> high (persistent stress)']

def save(path,obj):
    (ROOT/path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def load_data(path):
    raw=Path(path).read_bytes();d=pd.read_csv(path);d['date']=pd.to_datetime(d.DATE,format='%m/%d/%Y');d=d[d.date<=CFG['data_cutoff']].reset_index(drop=True)
    z=pd.DataFrame({'date':d.date.dt.strftime('%Y-%m-%d'),'CLOSE':d.CLOSE}).to_csv(index=False,float_format='%.6f').encode()
    manifest=json.loads((ROOT/'data/manifests/vix_manifest.json').read_text())
    assert hashlib.sha256(z).hexdigest()==manifest['clean_date_close_sha256']
    assert not d.date.duplicated().any() and d.CLOSE.notna().all()
    save('data/manifests/input_verification.json',{'raw_sha256':hashlib.sha256(raw).hexdigest(),'canonical_sha256':hashlib.sha256(z).hexdigest(),'n':len(d),'cutoff':CFG['data_cutoff'],'source':'official Cboe file reused without new observations','no_new_confirmation':True})
    return d

def record_forecasts(model,y,ctx,dates,year,label):
    ids=np.flatnonzero(dates.dt.year.to_numpy()==year);start,end=int(ids[0]),int(ids[-1])+1
    ts=np.arange(start-1,end-1);z=score_forecasts(model,y,ctx,ts);valid=ts+6<end
    g=pd.DataFrame(z);g['origin']=ts;g['date']=[str(dates[t].date()) for t in ts];g['target_date']=[str(dates[t+1].date()) for t in ts]
    g['year']=year;g['model']=label;g['event_eligible']=valid
    for c in ['event_truth','event_brier']:g.loc[~valid,c]=np.nan
    return g

def pool_model(model,strength,reference):
    prior=reference.p[np.arange(9)%3]
    pp=(model.counts+strength*prior)/(model.counts.sum(1,keepdims=True)+strength)
    return Model(model.name,2,3,model.alpha,model.edges,model.counts,pp,model.nxt,model.train_end)

def summarize(d,group=('model',)):
    out=[]
    for keys,g in d.groupby(list(group),sort=False):
        if not isinstance(keys,tuple):keys=(keys,)
        e=g[g.event_eligible];r=dict(zip(group,keys));r.update(n_one=len(g),n_event=len(e),event_brier=float(e.event_brier.mean()),event_rate=float(e.event_truth.mean()),mean_prediction=float(e.event_pred.mean()),stress_logloss=float(g.stress_logloss.mean()),categorical_logloss=float(g.categorical_logloss.mean()),stress_brier=float(g.stress_brier.mean()))
        out.append(r)
    return pd.DataFrame(out)

def paired(d):
    rng=np.random.default_rng(SEED);B=CFG['paired_bootstrap']['repetitions'];base=d[d.model=='ternary20_30_k1'].set_index(['year','date']);rows=[]
    for name in ['ternary20_30_k2','ternary20_30_k3','binary30_k2','binary30_k1']:
        c=d[d.model==name].set_index(['year','date']);j=c.join(base[['event_brier','stress_logloss','categorical_logloss','stress_brier']],rsuffix='_base')
        metrics=['event_brier','stress_logloss','stress_brier']+(['categorical_logloss'] if name.startswith('ternary') else [])
        for metric in metrics:
            for scope,years in [('all',range(2015,2027)),('2015-2019',range(2015,2020)),('2020-2022',range(2020,2023)),('2023-2026',range(2023,2027))]:
                chunks=[(j.loc[y][metric]-j.loc[y][metric+'_base']).dropna().to_numpy() for y in years]
                total=sum(map(len,chunks));point=sum(z.sum() for z in chunks)/total
                for block in CFG['paired_bootstrap']['blocks']:
                    means=np.zeros(B)
                    for z in chunks:
                        n=len(z);starts=rng.integers(n,size=(B,int(np.ceil(n/block))));ix=((starts[:,:,None]+np.arange(block))%n).reshape(B,-1)[:,:n];means+=z[ix].sum(1)
                    lo,hi=np.quantile(means/total,[.025,.975]);rows.append(dict(candidate=name,baseline='ternary20_30_k1',metric=metric,scope=scope,block=block,reps=B,n=total,difference=float(point),lo=float(lo),hi=float(hi)))
    return pd.DataFrame(rows)

def event_batch(model,ps,L=6,K=3):
    B=len(ps);v=np.zeros((B,model.n,K+1));v[:,:,K]=1
    for _ in range(L):
        z=np.zeros_like(v)
        for s in range(model.n):
            for c in range(K+1):
                for x in range(model.m):z[:,s,c]+=ps[:,s,x]*v[:,model.nxt[s,x],min(K,c+(x==2))]
        v=z
    return v[:,:,0]

def robust_event(model,L=6,K=3):
    """Conservative MDP envelope: rare rows may choose any output each visit.
    Includes every fixed replacement of those rows, without claiming vertex-only
    scenarios find the exact fixed-parameter extrema.
    """
    vals=[]
    for lower in [True,False]:
        v=np.zeros((model.n,K+1));v[:,K]=1
        for _ in range(L):
            z=np.zeros_like(v)
            for s in range(model.n):
                for c in range(K+1):
                    nxt=np.array([v[model.nxt[s,x],min(K,c+(x==2))] for x in range(3)])
                    z[s,c]=(nxt.min() if lower else nxt.max()) if s in [2,6] else model.p[s]@nxt
            v=z
        vals.append(v[:,0])
    return vals

def rare_exposure(model,L=6):
    # Event transitions USE S_0,...,S_(L-1); a newly reached S_L is irrelevant.
    q=np.isin(np.arange(9),[2,6]).astype(float)
    for _ in range(L-1):q=np.where(np.isin(np.arange(9),[2,6]),1,np.array([sum(model.p[s,x]*q[model.nxt[s,x]] for x in range(3)) for s in range(9)]))
    return q

def exact_event_fractions(model,kind,K):
    p=model.fractions();out=[]
    for initial in range(9):
        total=Fraction(0)
        for word in itertools.product(range(3),repeat=6):
            s=initial;w=Fraction(1)
            for x in word:w*=p[s][x];s=int(model.nxt[s,x])
            hits=[x==2 for x in word]
            if kind=='count':good=sum(hits)>=K
            elif kind=='hit':good=any(hits)
            else:good=any(all(hits[j:j+K]) for j in range(7-K))
            if good:total+=w
        out.append(total)
    return out

def uncertainty(model,values):
    rng=np.random.default_rng(SEED+1);B=CFG['parameter_uncertainty']['repetitions'];rows=[];eventrows=[]
    nominal=np.array([[rng.dirichlet(row+.5) for row in model.counts] for _ in range(B)])
    sets=[('nominal_Dirichlet',0,nominal)]
    y=np.searchsorted([20,30],values,side='right');ct=contexts(y,2,3);targets=np.arange(2,len(y));flat=ct[targets-1]*3+y[targets];n=len(flat)
    for block in CFG['parameter_uncertainty']['blocks']:
        means=[];hybrid=[]
        for _ in range(B):
            starts=rng.integers(n,size=int(np.ceil(n/block)));ix=((starts[:,None]+np.arange(block))%n).ravel()[:n]
            cc=np.bincount(flat[ix],minlength=27).reshape(9,3)
            means.append((cc+.5)/(cc.sum(1,keepdims=True)+1.5));hybrid.append([rng.dirichlet(row+.5) for row in cc])
        sets.extend([('block_refit_mean',block,np.array(means)),('block_plus_Dirichlet_sensitivity',block,np.array(hybrid))])
    for method,block,draws in sets:
        ev=event_batch(model,draws)
        for s in range(9):
            lo,hi=np.quantile(ev[:,s],[.025,.975]);eventrows.append(dict(state=s,history=model.labels[s],method=method,block=block,lo=float(lo),hi=float(hi),replicates=B))
            for x in range(3):
                lo,hi=np.quantile(draws[:,s,x],[.025,.975]);rows.append(dict(state=s,history=model.labels[s],output=x,method=method,block=block,lo=float(lo),hi=float(hi),replicates=B))
        np.savez_compressed(R/f'uncertainty_{method}_block{block}.npz',emissions=draws,events=ev)
    pd.DataFrame(rows).to_csv(R/'transition_uncertainty.csv',index=False);pd.DataFrame(eventrows).to_csv(R/'event_uncertainty.csv',index=False)

def main(path):
    start=time.time();df=load_data(path);v=df.CLOSE.to_numpy();dates=df.date;pred=[];sens=[];fitmeta=[]
    for year in CFG['outer_years']:
        end=int(np.searchsorted(dates.to_numpy(),np.datetime64(f'{year}-01-01')))
        for label in CFG['comparison_models']:
            name,k=label.rsplit('_k',1);m,y,c=fit(v,name,int(k),end);pred.append(record_forecasts(m,y,c,dates,year,label))
        # Fixed sensitivity plans, never select the best after evaluation.
        for k in [1,2]:
            for window in [5,10,20]:
                lo=int(np.searchsorted(dates.to_numpy(),np.datetime64(f'{year-window}-01-01')))
                m,_,_=fit(v[lo:end],'ternary20_30',k,end-lo);y=np.searchsorted([20,30],v,side='right');c=contexts(y,k,3)
                label=f'k{k}_window{window}';g=record_forecasts(m,y,c,dates,year,label);sens.append(g)
                fitmeta.append({'model':label,'year':year,'training_start':str(dates[lo].date()),'training_end':str(dates[end-1].date()),'counts':m.counts.tolist(),'emissions':m.p.tolist()})
            for alpha in [.1,1.,2.]:
                m,y,c=fit(v,'ternary20_30',k,end,alpha);label=f'k{k}_alpha{alpha}';sens.append(record_forecasts(m,y,c,dates,year,label))
        m,y,c=fit(v,'ternary20_30',2,end);one,_,_=fit(v,'ternary20_30',1,end)
        for strength in [3,10]:
            mm=pool_model(m,strength,one);label=f'k2_pool{strength}';sens.append(record_forecasts(mm,y,c,dates,year,label))
        print('Completed focused year',year,flush=True)
    d=pd.concat(pred,ignore_index=True);ss=pd.concat(sens,ignore_index=True)
    (R/'forecasts.csv.gz').write_bytes(gzip.compress(d.to_csv(index=False).encode(),mtime=0));(R/'sensitivity_forecasts.csv.gz').write_bytes(gzip.compress(ss.to_csv(index=False).encode(),mtime=0))
    summarize(d).to_csv(R/'comparison_summary.csv',index=False);summarize(d,('model','year')).to_csv(R/'annual_scores.csv',index=False)
    summarize(ss).to_csv(R/'sensitivity_summary.csv',index=False);summarize(ss,('model','year')).to_csv(R/'sensitivity_by_year.csv',index=False)
    save('results/window_fit_records.json',fitmeta);paired(d).to_csv(R/'direct_paired_intervals.csv',index=False)
    # Direct readback comparison against preserved Phase 2 ledger.
    old=pd.read_csv(ROOT/'data/phase2_reference/outer_forecasts.csv.gz',low_memory=False);diff=[]
    for label in CFG['comparison_models']:
        name,k=label.rsplit('_k',1);a=d[d.model==label].set_index(['year','date']);b=old[(old.name==name)&(old.k==int(k))].set_index(['year','date'])
        for field in ['event_pred','stress_pred','categorical_logloss']:
            delta=float(np.max(np.abs(a[field]-b[field])));diff.append({'model':label,'field':field,'max_difference':delta});assert delta<1e-12
    save('validation/phase2_forecast_reconstruction.json',diff)
    # Per-period complete nine-state estimates and class-support checks.
    drift=[]
    for a,b in [(1990,2002),(2003,2014),(2015,2019),(2020,2022),(2023,2026)]:
        vv=v[dates.dt.year.between(a,b)];mm,_,_=fit(vv,'ternary20_30',2,len(vv))
        for r in mm.count_table():drift.append({'period':f'{a}-{b}',**r})
    pd.DataFrame(drift).to_csv(R/'nine_state_subperiods.csv',index=False)
    m,y,c=fit(v,'ternary20_30',2,len(v));diag=quantum_diagnostic(m)
    reference=json.loads((ROOT/'data/phase2_reference/nine_state_model.json').read_text());assert np.max(np.abs(m.p-np.array(reference['emission_probabilities'])))<1e-15
    # Independent Counter audit, independent from the fitted-array estimator.
    counter=Counter((int(y[t-2]),int(y[t-1]),int(y[t])) for t in range(2,len(y)))
    cc=np.array([[counter[(s//3,s%3,x)] for x in range(3)] for s in range(9)])
    assert np.array_equal(cc,m.counts)
    table=m.count_table()
    for r in table:r['meaning']=MEANINGS[r['state']];r['prior_weight_fraction']=1.5/(r['n']+1.5)
    pd.DataFrame(table).to_csv(ROOT/'model/nine_state_table.csv',index=False)
    tx=m.matrices()
    for x in range(3):np.savetxt(ROOT/f'model/T_{x}.csv',tx[x],delimiter=',',fmt='%.17g')
    np.savetxt(ROOT/'model/T.csv',tx.sum(0),delimiter=',',fmt='%.17g')
    evrows=[];exact={}
    for label,kind,K in [('count3of6','count',3),('hit6','hit',1),('run3in6','run',3)]:
        fr=exact_event_fractions(m,kind,K);dp=event_dp(m,6,K,kind=kind);en=np.array([enumerate_event(m,s,6,K,kind=kind) for s in range(9)])
        exact[label]=[str(q) for q in fr]
        for s in range(9):evrows.append({'state':s,'history':m.labels[s],'event':label,'DP':float(dp[s]),'enumeration':float(en[s]),'rational':str(fr[s]),'max_discrepancy':max(abs(float(fr[s])-dp[s]),abs(en[s]-dp[s]))})
        assert np.max(np.abs(dp-np.array([float(q) for q in fr])))<1e-12
    pd.DataFrame(evrows).to_csv(R/'exact_events.csv',index=False)
    low,high=robust_event(m);exposure=rare_exposure(m);primary=event_dp(m)
    rare=pd.DataFrame({'state':range(9),'history':m.labels,'rare_transition_exposure_probability_next6':exposure,'reference_event':primary,'robust_lower':low,'robust_upper':high})
    rare.to_csv(R/'rare_state_robust_event_bounds.csv',index=False)
    g=d[(d.model=='ternary20_30_k2')&d.event_eligible];state_rows=[]
    for s in range(9):
        z=g[g.state==s];state_rows.append({'state':s,'history':m.labels[s],'outer_origins':len(z),'event_positives':int(z.event_truth.sum()),'event_brier':float(z.event_brier.mean()) if len(z) else None,
                                        'mean_event_forecast':float(z.event_pred.mean()) if len(z) else None,'share_of_all_event_loss':float(z.event_brier.sum()/g.event_brier.sum())})
    pd.DataFrame(state_rows).to_csv(R/'outer_scores_by_state.csv',index=False)
    save('results/rare_state_exposure_summary.json',{'weighted_rare_transition_exposure':float(np.mean(exposure[g.state.astype(int)])),
        'weighted_robust_interval_width':float(np.mean((high-low)[g.state.astype(int)])),
        'current_rare_origins':int(g.state.isin([2,6]).sum()),'total_origins':len(g),
        'meaning':'Envelope allows rare-row probabilities to vary at every visit. It is a conservative bound for every fixed rare-row replacement, not an exact confidence interval.'})
    uncertainty(m,v)
    det=rational_determinant(m);assert det!=0;certificate=all_phase_certificate(m)
    save('results/exact_probability_rank.json',{'determinant':str(det),'rank':9,'quantum_general_dimension_lower_bound':3,'independent_method':'exact rational Gaussian elimination, separate from modular certificate','modular':rank_modular(m)})
    save('results/all_phase_dimension_certificate.json',certificate)
    # Bounded identity checks only; no numerical compression optimizer is launched.
    rng=np.random.default_rng(SEED+7);phase_checks=[]
    for j in range(9):
        phi=np.zeros((9,3))
        if j:
            for s in range(9):
                if s!=4:phi[s,1]=rng.uniform(-np.pi,np.pi)
                if s!=8:phi[s,2]=rng.uniform(-np.pi,np.pi)
        B=future_amplitude(m,phi);G=B.conj()@B.T;res=0.
        for a in range(9):
            for b in range(9):res=max(res,abs(G[a,b]-sum(np.sqrt(m.p[a,x]*m.p[b,x])*np.exp(1j*(phi[b,x]-phi[a,x]))*G[m.nxt[a,x],m.nxt[b,x]] for x in range(3))))
        phase_checks.append({'test':j,'minimum_Gram_eigenvalue':float(np.linalg.eigvalsh(G)[0]),'Gram_recurrence_residual':float(res),'phases':phi.tolist(),'det_abs':float(abs(np.linalg.det(B)))})
    save('results/phase_identity_checks.json',{'seed':SEED+7,'purpose':'identity validation, not phase optimization','gauge':'all phi_s0=0; phi_11,1=phi_22,2=0; remaining 16 phase variables','optimizer_skipped_reason':'exact all-phase full-rank obstruction for the fixed pure unifilar model' if certificate['all_blocks_phase_nonsingular'] else 'certificate inconclusive','tests':phase_checks})
    diag['phase3_exact_rank']=certificate['pure_phase_memory_dimension_exact']
    diag['phase3_exact_rank_certificate']='all_phase_dimension_certificate.json; interval-certified determinant dominance plus synchronized two-step amplitude factorization'
    save('results/zero_phase_quantum.json',diag)
    S=np.array(diag['memory_states_columns']);rho=S@np.diag(m.stationary())@S.T;rho_ev=np.linalg.eigvalsh(rho)[::-1]
    save('results/approximation_readiness.json',{'stationary_density_eigenvalues':rho_ev.tolist(),'discarded_stationary_weight_rank8':float(sum(rho_ev[8:])),'discarded_stationary_weight_rank4':float(sum(rho_ev[4:])),
        'limitation':'Spectral tails concern one stationary ensemble. They are neither recurrent-instrument feasibility nor worst-history event-error bounds. No approximate production instrument is trained.'})
    spec={**reference,'model_version':CFG['version'],'role':'conditionally frozen research candidate, not statistically established best financial forecaster',
          'state_meanings':MEANINGS,'context_estimates':table,'exact_events_rational':exact,
          'first_entry':'hit6 probabilities apply only when current symbol is 0 or 1; current category 2 is not first entry',
          'severe35_event':'not identifiable from category 2; requires a separately versioned observation alphabet/threshold, not an oracle change alone',
          'validation_status':'retrospective reconstruction; new direct comparisons; unsupported 02/20 retained; exact equations and numerical recurrent instrument validated; full QAE not implemented',
          'quantum_phase_class_dimension':certificate['pure_phase_memory_dimension_exact'],'general_quantum_dimension_lower_bound':3}
    save('model/nine_state_model_specification.json',spec)
    save('validation/mathematical_checks.json',{'independent_counts_equal':True,'row_normalization_max':float(np.max(np.abs(m.p.sum(1)-1))),
        'minimum_emission':float(m.p.min()),'T_sum_residual':float(np.max(np.abs(tx.sum(0)-np.array(reference['T'])))),
        'stationary_residual':float(np.max(np.abs(m.stationary()@tx.sum(0)-m.stationary()))),
        'exact_causal_states':exact_partition(m),'event_max_discrepancy':max(r['max_discrepancy'] for r in evrows),
        'quantum_instrument_recurrence':diag['recurrence_residual'],'quantum_instrument_completeness':diag['completeness_residual'],
        'all_phase_certificate_pass':certificate['all_blocks_phase_nonsingular'],'elapsed_seconds':time.time()-start})
    print('Focused analysis complete',time.time()-start,flush=True)

if __name__=='__main__':main(Path(sys.argv[1]))
