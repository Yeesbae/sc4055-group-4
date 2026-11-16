"""Publication-oriented figures regenerated exclusively from saved results."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results';F=ROOT/'figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','savefig.dpi':260})
BLUE='#155e75';TEAL='#0f766e';ORANGE='#c76b28';RED='#b5484f';GRAY='#667085'

def save(fig,name):
    import io
    from PIL import Image
    buf=io.BytesIO();fig.savefig(buf,format='png',bbox_inches='tight',facecolor='white');payload=buf.getvalue();assert len(payload)>1000
    (F/f'{name}.png').write_bytes(payload)
    Image.open(io.BytesIO((F/f'{name}.png').read_bytes())).verify()
    buf=io.StringIO();fig.savefig(buf,format='svg',bbox_inches='tight',facecolor='white');(F/f'{name}.svg').write_text(buf.getvalue());plt.close(fig)

def main():
    t=pd.read_csv(ROOT/'model/nine_state_table.csv',dtype={'history':str});ci=pd.read_csv(R/'direct_paired_intervals.csv');summary=pd.read_csv(R/'comparison_summary.csv')
    fig,ax=plt.subplots(figsize=(8.5,3.7));x=np.arange(9);ax.bar(x,t.n,color=[RED if n<25 else BLUE for n in t.n]);ax.set_yscale('symlog',linthresh=2);ax.set_xticks(x,t.history);ax.set_ylabel('Observed continuation count (symlog)');ax.set_xlabel('History, oldest to newest');ax.set_title('Two contexts remain almost entirely prior-defined')
    for i,n in enumerate(t.n):ax.text(i,max(1,n)*1.15,str(n),ha='center',fontsize=9)
    ax.grid(axis='y',alpha=.15);fig.tight_layout();save(fig,'context_support')
    fig,axs=plt.subplots(1,2,figsize=(9.3,3.8))
    for ax,metric,title in zip(axs,['event_brier','categorical_logloss'],['Six-step event Brier difference','Three-category log-loss difference']):
        z=ci[(ci.candidate=='ternary20_30_k2')&(ci.metric==metric)&(ci.scope=='all')]
        for j,(_,r) in enumerate(z.iterrows()):ax.errorbar(r.difference,j,xerr=[[r.difference-r.lo],[r.hi-r.difference]],fmt='o',capsize=4,color=BLUE)
        ax.set_yticks(range(len(z)),[f'Block {b}' for b in z.block]);ax.invert_yaxis();ax.axvline(0,color=GRAY,ls='--');ax.set_title(title,fontsize=11);ax.set_xlabel('Order 2 minus order 1');ax.grid(axis='x',alpha=.2)
        from matplotlib.ticker import MaxNLocator,FormatStrFormatter
        ax.xaxis.set_major_locator(MaxNLocator(4));ax.xaxis.set_major_formatter(FormatStrFormatter('%.4f' if metric=='event_brier' else '%.3f'))
    fig.tight_layout();save(fig,'direct_paired_comparison')
    fig,ax=plt.subplots(figsize=(8.8,3.8));z=pd.read_csv(R/'regime_scores.csv');xs=np.arange(3)
    for name,color,label in [('ternary20_30_k1',GRAY,'Three levels order 1'),('ternary20_30_k2',BLUE,'Three levels order 2'),('ternary20_30_k3',ORANGE,'Three levels order 3'),('binary30_k2',TEAL,'Binary order 2')]:
        a=z[z.model==name];ax.plot(xs,a.event_brier,'o-',label=label,color=color)
    ax.set_xticks(xs,['2015-2019','2020-2022','2023-2026']);ax.set_ylabel('Primary-event Brier');ax.set_title('Regime differences dominate the small order effect');ax.grid(alpha=.15);ax.legend(fontsize=8);fig.tight_layout();save(fig,'regime_comparison')
    z=pd.read_csv(R/'calibration.csv');fig,axs=plt.subplots(1,2,figsize=(9.2,3.9))
    for ax,target in zip(axs,['stress','event']):
        ax.plot([0,1],[0,1],'--',color=GRAY,lw=1)
        for name,color,label in [('ternary20_30_k1',GRAY,'Order 1'),('ternary20_30_k2',BLUE,'Order 2'),('ternary20_30_k3',ORANGE,'Order 3')]:
            a=z[(z.model==name)&(z.target==target)&(z.n>=20)]
            ax.errorbar(a.mean_prediction,a.observed_frequency,yerr=[np.maximum(0,a.observed_frequency-a.lo),np.maximum(0,a.hi-a.observed_frequency)],fmt='o-',color=color,label=label,capsize=2,ms=3,lw=1)
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='Forecast mean',ylabel='Observed frequency',title='Next-day high stress' if target=='stress' else 'At least 3 high-stress days in 6');ax.grid(alpha=.15)
    axs[1].legend(fontsize=8);fig.tight_layout();save(fig,'calibration')
    z=pd.read_csv(R/'sensitivity_summary.csv');fig,ax=plt.subplots(figsize=(8.4,3.8));xs=np.arange(4)
    for k,offset,color,label in [(1,-.18,GRAY,'Order 1'),(2,.18,BLUE,'Order 2')]:
        vals=[z[z.model==f'k{k}_window{w}'].event_brier.iloc[0] for w in [5,10,20]]+[summary[summary.model==f'ternary20_30_k{k}'].event_brier.iloc[0]]
        ax.bar(xs+offset,vals,width=.34,color=color,label=label)
    ax.set_xticks(xs,['5 years','10 years','20 years','Expanding']);ax.set_ylabel('Primary-event Brier');ax.set_title('Short windows weaken stress estimation');ax.legend();ax.grid(axis='y',alpha=.15);fig.tight_layout();save(fig,'training_windows')
    u=pd.read_csv(R/'event_uncertainty.csv',dtype={'history':str});base=pd.read_csv(R/'exact_events.csv',dtype={'history':str});base=base[base.event=='count3of6'];fig,ax=plt.subplots(figsize=(9.1,4))
    for method,block,offset,color,label in [('nominal_Dirichlet',0,-.12,TEAL,'Nominal Dirichlet'),('block_plus_Dirichlet_sensitivity',60,.12,BLUE,'Block 60 + prior sensitivity')]:
        a=u[(u.method==method)&(u.block==block)];point=base.DP.to_numpy();ax.errorbar(x+offset,point,yerr=[np.maximum(0,point-a.lo.to_numpy()),np.maximum(0,a.hi.to_numpy()-point)],fmt='o',capsize=3,label=label,color=color)
    ax.set_xticks(x,t.history);ax.set(xlabel='Initial history',ylabel='Primary-event probability',title='Conditional event uncertainty is largest in rare contexts',ylim=(-.03,1.03));ax.legend(fontsize=8);ax.grid(alpha=.15);fig.tight_layout();save(fig,'event_uncertainty')
    q=json.loads((R/'zero_phase_quantum.json').read_text());rho=json.loads((R/'approximation_readiness.json').read_text());fig,axs=plt.subplots(1,2,figsize=(9.1,3.6))
    for ax,e,label in [(axs[0],q['eigenvalues_float64'][::-1],'Gram eigenvalues'),(axs[1],rho['stationary_density_eigenvalues'],'Stationary density eigenvalues')]:
        ax.semilogy(range(1,10),e,'o-',color=BLUE);ax.set(xlabel='Index (descending)',ylabel='Eigenvalue',title=label);ax.grid(alpha=.2)
    fig.tight_layout();save(fig,'quantum_spectra')
    r=json.loads((R/'quantum_resource_pilot.json').read_text());fig,axs=plt.subplots(1,2,figsize=(9.2,3.7));steps=r['step_compilations'];axs[0].bar([0,1],[z['CX'] for z in steps],color=[GRAY,BLUE]);axs[0].set_xticks([0,1],['Generic unitary','Input isometry']);axs[0].set_ylabel('Measured CX per local step');axs[0].set_title('Actual 6-qubit synthesis')
    for i,z in enumerate(steps):axs[0].text(i,z['CX']+25,str(z['CX']),ha='center')
    stages=r['stages_estimated'];axs[1].plot([z['Grover_power'] for z in stages],[z['CX'] for z in stages],'o-',color=BLUE);axs[1].set(xlabel='Grover power',ylabel='Estimated CX per trial circuit',title='Full-circuit composition estimate');axs[1].grid(alpha=.2);fig.tight_layout();save(fig,'circuit_resources')
    print('Saved eight figures in PNG and SVG')

if __name__=='__main__':main()
