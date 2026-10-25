from pathlib import Path
import json,numpy as np,pandas as pd,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sc4055.model import *
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
F=ROOT/'results/figures';F.mkdir(exist_ok=True)
def save(fig,name):fig.savefig(F/(name+'.png'),bbox_inches='tight');fig.savefig(F/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
b=pd.read_csv(ROOT/'results/processed/benchmark_summary.csv',dtype={'state':str});fig,axs=plt.subplots(1,5,figsize=(13.5,3),sharey=True)
for ax,(state,d) in zip(axs,b.groupby('state',sort=False)):
 for method,color in [('MLAE','#087f8c'),('Monte Carlo','#df7840')]:
  a=d[d.method==method];ax.errorbar(a.budget,a.rmse,yerr=[a.rmse-a.rmse_ci_lo,a.rmse_ci_hi-a.rmse],fmt='o-',color=color,label=method,capsize=3)
 ax.set_title(f'History {state}');ax.set_xscale('log');ax.set_yscale('log');ax.set_xlabel('Logical queries');ax.set_xticks([450,1800,3600],['450','1800','3600'],rotation=30,fontsize=8);ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter());ax.grid(alpha=.2)
axs[0].set_ylabel('RMSE');axs[-1].legend(fontsize=8);save(fig,'rmse')
fig,ax=plt.subplots(figsize=(7,3.4));a=b[(b.method=='MLAE')&(b.budget==3600)];ax.errorbar(range(5),a.rmse_ratio,yerr=[a.rmse_ratio-a.rmse_ratio_lo,a.rmse_ratio_hi-a.rmse_ratio],fmt='o',capsize=5,color='#087f8c');ax.axhline(1,color='gray',ls='--');ax.set_xticks(range(5),a.state);ax.set_xlabel('Initial history');ax.set_ylabel('RMSE(MLAE) / RMSE(MC)');save(fig,'rmse_ratio')
cache=pd.DataFrame(json.loads((ROOT/'results/raw/ideal_distribution_cache.json').read_text()));fig,axs=plt.subplots(1,2,figsize=(8,3.1))
for s,d in cache.groupby('label',sort=False):axs[0].plot(d.power,d.cx,'o-',label=s);axs[1].plot(d.power,d.simulation_seconds,'o-')
axs[0].set_ylabel('Measured compiled CX count');axs[1].set_ylabel('Unique circuit simulation (s)')
for ax in axs:ax.set_xlabel('Grover power k');ax.grid(alpha=.2)
axs[0].legend(title='History',fontsize=7,ncol=2);save(fig,'resources')
fig,ax=plt.subplots(figsize=(7,3));probs=[dp(s) for s in range(9)];ax.bar(LABELS,probs,color=['#ce7847' if s in [2,6] else '#087f8c' for s in range(9)]);ax.set_xlabel('Initial two-observation history');ax.set_ylabel('Frozen model event probability');save(fig,'events')
fig,ax=plt.subplots(figsize=(6,3));ax.bar(['Classical entropy','Quantum entropy'],[MEM['stationary_classical_entropy'],MEM['stationary_quantum_entropy']],color=['#df7840','#087f8c']);ax.set_ylabel('Stationary memory entropy (bits)');ax.set_ylim(0,1.9);ax.text(.5,1.8,'Both implementations use dimension 9 / four memory bits or qubits',ha='center',fontsize=8);save(fig,'entropy')
prior=pd.read_csv(ROOT/'results/processed/phase2_historical_comparators.csv');a=prior[((prior.name=='binary30')|(prior.name=='ternary20_30'))&prior.k.isin([1,2,3])];fig,ax=plt.subplots(figsize=(7,3.1))
for name,label,color in [('binary30','Binary threshold 30','#df7840'),('ternary20_30','Three levels 20/30','#087f8c')]:
 d=a[a.name==name];ax.plot(d.k,d.event_brier,'o-',label=label,color=color)
ax.set_xticks([1,2,3]);ax.set_xlabel('Markov order');ax.set_ylabel('Historical six-step event Brier');ax.legend();save(fig,'financial_models')
# Export all presentation chart data, preserving exact values.
(ROOT/'presentation/chart_data.json').write_text(json.dumps(dict(events=probs,labels=LABELS,entropy=[MEM['stationary_classical_entropy'],MEM['stationary_quantum_entropy']],benchmark=b.to_dict('records'),circuits=cache.to_dict('records'),financial=a.to_dict('records')),indent=2))
print('FIGURES_COMPLETE',flush=True)
