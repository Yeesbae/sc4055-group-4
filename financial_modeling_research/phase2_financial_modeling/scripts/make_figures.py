"""Regenerate scientific figures solely from saved numerical results."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'figures';R=ROOT/'results'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','savefig.dpi':190})
BLUE='#155e75';TEAL='#0f766e';ORANGE='#c76b28';GRAY='#667085'

def save(fig,name):
    fig.savefig(OUT/f'{name}.png',bbox_inches='tight',facecolor='white');plt.close(fig)

def main():
    s=pd.read_csv(R/'outer_summary.csv');ci=pd.read_csv(R/'paired_block_intervals.csv')
    items=[('binary30',0,'IID'),('binary30',1,'Binary order 1'),('binary30',2,'Binary order 2'),('binary30',3,'Binary order 3'),('ternary20_30',1,'Three levels, order 1'),('ternary20_30',2,'Three levels, order 2*'),('continuous_logVIX_ridge',-1,'Continuous direct baseline'),('selected_policy',-1,'Nested selection policy')]
    vals=[s[(s.name==n)&(s.k==k)].event_brier.iloc[0] for n,k,l in items]
    fig,ax=plt.subplots(figsize=(9.1,4.5));y=np.arange(len(items))
    bars=ax.barh(y,vals,color=[GRAY,BLUE,BLUE,BLUE,TEAL,TEAL,ORANGE,'#a33e42'],height=.64)
    ax.set_yticks(y,[x[2] for x in items]);ax.invert_yaxis();ax.set_xlim(0,.064);ax.set_xlabel('Six-step event Brier score (lower is better)')
    for b,v in zip(bars,vals):ax.text(v+.0006,b.get_y()+b.get_height()/2,f'{v:.5f}',va='center',fontsize=9)
    ax.set_title('Same event, annual expanding fits, 2015-2026');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    fig.text(.02,-.04,'* Some three-level order-2 contexts have no training support. All results are retrospective.',fontsize=8,color=GRAY)
    fig.tight_layout();save(fig,'primary_scores')
    fig,ax=plt.subplots(figsize=(8.7,3.6))
    its=[('binary30',2,'Binary order 2'),('binary30',3,'Binary order 3'),('ternary20_30',1,'Three levels, order 1'),('continuous_logVIX_ridge',-1,'Continuous direct baseline')]
    for i,(n,k,label) in enumerate(its):
        a=ci[(ci.name==n)&(ci.k==k)&(ci.scope=='all')&(ci.metric=='event_brier')&(ci.block==60)].iloc[0]
        ax.errorbar(a.difference,i,xerr=[[a.difference-a.lo],[a.hi-a.difference]],fmt='o',color=TEAL if n.startswith('ternary') else BLUE,capsize=4)
    ax.axvline(0,color=GRAY,ls='--');ax.set_yticks(range(4),[z[2] for z in its]);ax.invert_yaxis();ax.set_xlabel('Brier difference from binary order 1 (negative favors candidate)');ax.set_title('Paired 95% moving-block intervals, block = 60')
    ax.grid(axis='x',alpha=.15);fig.tight_layout();save(fig,'paired_intervals')
    c=pd.read_csv(R/'calibration_intervals.csv');fig,axs=plt.subplots(1,2,figsize=(9.2,3.9))
    for ax,label in zip(axs,['one_step_stress','event']):
        ax.plot([0,1],[0,1],ls='--',color=GRAY,lw=1)
        for n,k,color,txt in [('binary30',1,BLUE,'Binary order 1'),('ternary20_30',1,TEAL,'Three levels order 1'),('continuous_logVIX_ridge',-1,ORANGE,'Continuous baseline')]:
            z=c[(c.name==n)&(c.k==k)&(c.target==label)&(c.n>=20)]
            if len(z):
                ax.errorbar(z.mean_pred,z.observed,yerr=np.vstack([np.maximum(0,z.observed-z.lo),np.maximum(0,z.hi-z.observed)]),fmt='o-',label=txt,color=color,lw=1,capsize=2,ms=3)
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='Mean forecast',ylabel='Observed frequency',title='Next stress observation' if label=='one_step_stress' else 'At least 3 stress days in 6')
        ax.grid(alpha=.15)
    axs[1].legend(fontsize=7,loc='upper left');fig.tight_layout();save(fig,'calibration')
    d=pd.read_csv(R/'regime_scores.csv');fig,ax=plt.subplots(figsize=(9.1,3.9));xs=np.arange(3)
    for n,k,c,label in [('binary30',1,BLUE,'Binary order 1'),('binary30',3,'#60a5bd','Binary order 3'),('ternary20_30',1,TEAL,'Three levels order 1'),('selected_policy',-1,'#a33e42','Nested selection'),('continuous_logVIX_ridge',-1,ORANGE,'Continuous baseline')]:
        z=d[(d.name==n)&(d.k==k)];ax.plot(xs,z.event_brier,'o-',color=c,label=label)
    ax.set_xticks(xs,['2015-2019','2020-2022','2023-2026']);ax.set_ylabel('Primary-event Brier');ax.set_title('Performance changes with the market period');ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=2);fig.tight_layout();save(fig,'regime_scores')
    h=pd.read_csv(R/'subperiod_transition_estimates.csv');z=h[h.name=='binary30'];fig,axs=plt.subplots(1,2,figsize=(9.1,3.6))
    for state,ax in enumerate(axs):
        a=z[z.state==state];ax.errorbar(np.arange(len(a)),a.p_1,yerr=[a.p_1-a.lo95_1,a.hi95_1-a.p_1],fmt='o-',capsize=4,color=BLUE)
        ax.set_xticks(np.arange(len(a)),[f'{x}-{y}' for x,y in zip(a.start_year,a.end_year)],rotation=30,ha='right',fontsize=8)
        ax.set_ylabel('P(next close >= 30)');ax.set_title('Current close < 30' if state==0 else 'Current close >= 30');ax.grid(alpha=.2)
    fig.tight_layout();save(fig,'transition_stability')
    fig,ax=plt.subplots(figsize=(8.6,3.7))
    for tag,color in [('binary30_k1',BLUE),('binary30_k2',TEAL),('binary30_k3',ORANGE),('ternary20_30_k1','#7c3aed')]:
        o=json.loads((ROOT/f'models/{tag}/structural_diagnostics.json').read_text());ev=np.array(o['eigenvalues_float64'])[::-1]
        ax.semilogy(np.arange(1,len(ev)+1),ev,'o-',label=tag,color=color)
    ax.set(xlabel='Eigenvalue index (descending)',ylabel='Zero-phase Gram eigenvalue',title='Small eigenvalues are not exact dimension reduction');ax.legend(fontsize=8);ax.grid(alpha=.2);fig.tight_layout();save(fig,'gram_spectra')
    print('Saved six figures from numerical records')

if __name__=='__main__':main()
