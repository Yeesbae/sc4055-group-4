"""Create the explicit conditional decision and approximation diagnostics."""
import json,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.modeling import fit,exact_partition

def main(data):
    df=pd.read_csv(data);date=pd.to_datetime(df.DATE,format='%m/%d/%Y');v=df.CLOSE.to_numpy()[date<='2026-10-23']
    q=json.loads((ROOT/'results/zero_phase_quantum.json').read_text());S=np.array(q['memory_states_columns']);p=fit(v,'ternary20_30',2,len(v))[0].stationary();rho=S@np.diag(p)@S.T;e,U=np.linalg.eigh(rho);U=U[:,::-1]
    rows=[]
    for r in [4,8]:
        P=U[:,:r]@U[:,:r].T
        for s in range(9):rows.append({'target_rank':r,'state':s,'history':f'{s//3}{s%3}','projection_discarded_state_norm2':float(1-np.linalg.norm(P@S[:,s])**2),'stationary_weight':float(p[s]),'note':'one-time spectral projection diagnostic only; no recurrent approximate instrument'})
    pd.DataFrame(rows).to_csv(ROOT/'results/approximate_projection_by_state.csv',index=False)
    complexity=[]
    for name,k in [('ternary20_30',1),('ternary20_30',2),('ternary20_30',3),('binary30',2),('binary30',1)]:
        m,_,_=fit(v,name,k,len(v));D=exact_partition(m)['D_c'];memory=int(np.ceil(np.log2(D)));outputs=6*(2 if name.startswith('ternary') else 1)
        complexity.append({'model':f'{name}_k{k}','history_states':m.n,'causal_states':D,'unobserved_contexts':int((m.counts.sum(1)==0).sum()),'contexts_below25':int((m.counts.sum(1)<25).sum()),'physical_memory_qubits_conventional_upper':memory,'output_qubits':outputs,'total_register_design_qubits':memory+outputs+4,'quantum_status':'exact nine-state zero-phase instrument verified' if k==2 and name=='ternary20_30' else ('large sparse factorization unresolved in Phase 2' if k==3 else 'small zero-phase construction available')})
    pd.DataFrame(complexity).to_csv(ROOT/'results/model_complexity_comparison.csv',index=False)
    ci=pd.read_csv(ROOT/'results/direct_paired_intervals.csv');c=ci[(ci.candidate=='ternary20_30_k2')&(ci.metric=='event_brier')&(ci.scope=='all')&(ci.block==60)].iloc[0]
    result={'version':'V3.0-Phase3-1.0','decision':'CONDITIONAL GO','principal_research_model':'three-level second-order VIX model, fixed thresholds 20/30 and Dirichlet(0.5) emissions',
            'financial_superiority_established':False,'supported_all_nine_states':False,'sparse_states':{'02':1,'20':0},
            'Brier_difference_order2_minus_order1':float(c.difference),'paired_block60_interval':[float(c.lo),float(c.hi)],
            'conditional_freeze':True,'freeze_scope':'research demonstration and next-stage exact coherent implementation, not validated market deployment or unique optimal financial model',
            'quantum_pure_unifilar_phase_class_dimension':9,'exact_phase_compression_to8_or4':'NO-GO by interval-certified all-phase rank proof',
            'general_fixed_quantum_instrument_lower_dimension_bound':3,'general_mixed_or_multiKraus_compression':'unresolved; added coherent environments/purifications must be counted',
            'quantum_circuit_status':'one/two-step core and 20-qubit Aer pilots pass; full six-step A/oracle/Grover/MLAE not implemented',
            'course_feasibility':'conditional on actual full-circuit timing, cached unique-circuit strategy and correctness gates in the contract',
            'fallbacks':['three-level order 1 preserves observation and event at lower width','binary order 2 is the smaller engineering representation'],
            'required_conditions':['show unsupported/prior-dominated rows explicitly','do not claim six-step financial superiority','do not claim exact phase dimensional saving','validate all nine starts and the entire encoded oracle','run full-circuit timing gate before 100-200 replicate production','keep exact classical DP and separate statistical/model/quantum-estimator errors'],
            'preserve_phase2_recommendation':'Phase 2 preferred a smaller model under its support/tolerance rule; this focused conditional research exception does not rewrite that result.'}
    (ROOT/'V3_Model_Decision.json').write_text(json.dumps(result,indent=2)+'\n')
    spec=json.loads((ROOT/'model/nine_state_model_specification.json').read_text());spec['phase3_decision']=result;spec['pilot_resource_reference']='results/quantum_resource_pilot.json';spec['implementation_contract']='Next_Phase_Implementation_Contract.md'
    (ROOT/'model/nine_state_model_specification.json').write_text(json.dumps(spec,indent=2)+'\n')
    (ROOT/'SC4055_V3_Phase3_Nine_State_Model_Specification.json').write_text(json.dumps(spec,indent=2)+'\n')
    print('Conditional decision frozen; exact phase-compression branch closed')

if __name__=='__main__':main(sys.argv[1])
