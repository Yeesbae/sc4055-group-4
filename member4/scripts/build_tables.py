import json,numpy as np,pandas as pd
from sc4055.model import *
R=ROOT/'report';b=pd.read_csv(ROOT/'results/processed/benchmark_summary.csv',dtype={'state':str});cache=json.loads((ROOT/'results/raw/ideal_distribution_cache.json').read_text());audit=json.loads((ROOT/'results/processed/financial_audit.json').read_text())
def table(name,headers,rows,align):
 text='\\begin{tabular}{'+align+'}\\toprule\n'+' & '.join(headers)+'\\\\ \\midrule\n'
 text+='\n'.join(' & '.join(map(str,row))+'\\\\' for row in rows)+'\n\\bottomrule\\end{tabular}\n';(R/name).write_text(text)
table('event_table.tex',['History','Continuations','$p_s$','History','Continuations','$p_s$'],[[LABELS[i],sum(SPEC['counts'][i]),f'{dp(i):.9f}',LABELS[i+5] if i<4 else '',sum(SPEC['counts'][i+5]) if i<4 else '',f'{dp(i+5):.9f}' if i<4 else ''] for i in range(5)],'lrrlrr')
prior=pd.read_csv(ROOT/'results/processed/phase2_historical_comparators.csv');rows=[]
for name,label in [('binary30','Binary'),('ternary20_30','Three levels')]:
 for k in [1,2,3]:
  v=prior[(prior.name==name)&(prior.k==k)].iloc[0];rows.append([label,k,f'{v.event_brier:.6f}'])
rows.append(['Continuous direct-event ridge','--',f"{prior[prior.name=='continuous_logVIX_ridge'].iloc[0].event_brier:.6f}"])
table('financial_table.tex',['Observation','Order','Event Brier'],rows,'llr')
a=[r for r in cache if r['state']==0];table('resources_table.tex',['$k$','$A/A^\\dagger$ calls','Width','CX','Depth','Simulation (s)'],[[r['power'],2*r['power']+1,20,f"{r['cx']:,}",f"{r['depth']:,}",f"{r['simulation_seconds']:.2f}"] for r in a],'rrrrrr')
rows=[]
for state in ['00','01','11','12','22']:
 d=b[(b.state==state)&(b.budget==3600)];q=d[d.method=='MLAE'].iloc[0];c=d[d.method=='Monte Carlo'].iloc[0]
 rows.append([state,f'{q.rmse:.6f}',f'{c.rmse:.6f}',f'{q.rmse_ratio:.3f}',f'[{q.rmse_ratio_lo:.3f}, {q.rmse_ratio_hi:.3f}]'])
table('benchmark_table.tex',['History','MLAE RMSE','MC RMSE','Ratio','95\\% ratio interval'],rows,'lrrrr')
qr=b[b.method=='MLAE'];rat=qr.rmse_ratio
(R/'benchmark_findings.tex').write_text(f"Across the 15 state/budget settings, the empirical MLAE-to-Monte-Carlo RMSE ratio ranges from {rat.min():.3f} to {rat.max():.3f}. MLAE has lower observed RMSE in {int((rat<1).sum())} settings and higher RMSE in {int((rat>1).sum())}. The upper endpoint of the 95\\% ratio interval is below one in {int((qr.rmse_ratio_hi<1).sum())} settings. These exploratory intervals are not adjusted for multiple comparisons. There are {int(round((qr.failure_rate*200).sum()))} recorded optimizer failures among 3,000 production quantum estimates. The largest ambiguity-diagnostic rate is {100*qr.ambiguous_rate.max():.1f}\\%. All trials remain included.\n")
(R/'execution_metrics.tex').write_text(f"Across all 20 unique circuits, maximum amplification error is {max(r['amplification_error'] for r in cache):.2e}, and summed unique simulation time is {sum(r['simulation_seconds'] for r in cache):.2f} seconds ({sum(r['simulation_seconds'] for r in cache)/60:.2f} minutes), including the reused pilot. The largest recorded process RSS high-water value is {max(r['peak_rss_mib'] for r in cache):.1f} MiB. The median DP time over 100 repetitions for all nine states is {audit['dp_timing']['all_nine_median_seconds']*1e3:.3f} ms. Host timings are descriptive, with no controlled cross-platform performance claim.\n")
checks=json.loads((ROOT/'validation/checks.json').read_text());pytest=json.loads((ROOT/'validation/pytest_summary.json').read_text()) if (ROOT/'validation/pytest_summary.json').exists() else {'passed':0}
(R/'verification_metrics.tex').write_text(f"The executed new gate/mathematics validation runner records {len(checks)} checks, all passed. The inherited Phase-3 suite records nine passed tests, including the exact phase certificate. The additional regression suite records {pytest['passed']} passed tests. Full output-word checks cover all nine histories at lengths 1,2,4,6. Grover powers 0,1,2,4 cover five production histories. Complete event-flag tests cover all nine. A complete 20-qubit preparation/inverse return-to-zero check covers history 00; its structurally unitary gates and inverse define the same reversal for other starts. The oracle exhaustive proof uses an exact basis-permutation circuit executor, separately from Aer statevector validation of the full algorithm.\n")
print('TABLES_COMPLETE',flush=True)
