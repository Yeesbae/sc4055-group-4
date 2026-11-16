"""Bounded optimized-simulator follow-up: <=2 coherent steps, 20-qubit width."""
import json,time,importlib.metadata
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qpy
from qiskit.circuit.library import StatePreparation
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1]

def main():
    a=np.load(ROOT/'model/coherent_step_arrays.npz');mem=a['memory_states'];p=np.array(json.loads((ROOT/'model/nine_state_model_specification.json').read_text())['emission_probabilities'])
    resource=json.loads((ROOT/'results/quantum_resource_pilot.json').read_text())
    with (ROOT/'model/recurrent_step_pilot.qpy').open('rb') as f:circuits=qpy.load(f)
    idx=0 if resource['selected_step']['label']=='generic_64x64_unitary' else 1;step=circuits[idx]
    backend=AerSimulator(method='statevector',precision='double',max_parallel_threads=1,max_parallel_experiments=1,enable_truncation=False,fusion_enable=True,fusion_max_qubit=5)
    rows=[]
    for L in [1,2]:
        for s in [0,8]:
            qc=QuantumCircuit(20);qc.append(StatePreparation(mem[:,s]),range(4))
            # Expand initializer to native u/cx without building a full QAE circuit.
            from qiskit import transpile
            qc=transpile(qc,basis_gates=['u','cx'],optimization_level=1,seed_transpiler=4055)
            for t in range(L):qc.compose(step,[0,1,2,3,4+2*t,5+2*t],inplace=True)
            qc.save_statevector();begin=time.perf_counter();result=backend.run(qc,shots=1,seed_simulator=4055).result();elapsed=time.perf_counter()-begin
            assert result.success;sv=np.asarray(result.get_statevector());assert len(sv)==2**20
            error=0
            from itertools import product
            for word in product(range(3),repeat=L):
                code=sum(x*4**j for j,x in enumerate(word));got=float(np.sum(abs(sv[16*code:16*(code+1)])**2));state=s;want=1
                for x in word:want*=p[state,x];state=(state*3+x)%9
                error=max(error,abs(got-want))
            assert error<1e-9;rows.append({'L':L,'initial_state':s,'wall_seconds':elapsed,'Aer_time_taken':float(result.time_taken),'amplitudes':len(sv),'max_word_probability_error':error})
    # Full-width arbitrary state, repeated elementary kernels. Subtract baseline
    # allocation/readout overhead; keep raw timings rather than hiding negatives.
    rng=np.random.default_rng(4055);sv=rng.normal(size=2**20)+1j*rng.normal(size=2**20);sv/=np.linalg.norm(sv)
    kernel_backend=AerSimulator(method='statevector',precision='double',max_parallel_threads=1,enable_truncation=False,fusion_enable=False)
    kernels=[]
    for kind in ['none','u','cx']:
        timings=[]
        for rep in range(3):
            qc=QuantumCircuit(20);qc.set_statevector(sv)
            if kind!='none':
                for j in range(256):
                    if kind=='u':qc.u(.23,.47,.61,j%20)
                    else:qc.cx(j%20,(j+7)%20)
            qc.save_statevector();t=time.perf_counter();rr=kernel_backend.run(qc,shots=1,seed_simulator=4055).result();timings.append(time.perf_counter()-t);assert rr.success
        kernels.append({'gate':kind,'gates':0 if kind=='none' else 256,'wall_seconds':timings,'median':float(np.median(timings))})
    base=kernels[0]['median'];per={x['gate']:max(0.,(x['median']-base)/256) for x in kernels[1:]}
    if min(per.values())<=0:raise ValueError('Kernel subtraction unresolved; no runtime projection')
    stages=[]
    for stage in resource['stages_estimated']:
        stages.append({'Grover_power':stage['Grover_power'],'CX':stage['CX'],'U':stage['U'],
                       'seconds_component_projection':stage['CX']*per['cx']+stage['U']*per['u']})
    schedules=[]
    for powers in [[0,1,2,4],[0,1,2,4,8]]:
        unique=sum(z['seconds_component_projection'] for z in stages if z['Grover_power'] in powers)*5
        for reps in [100,200]:schedules.append({'powers':powers,'conditions':5,'replicates':reps,'cached_unique_circuit_seconds_projection':unique,'uncached_seconds_projection':unique*reps})
    out={'versions':{'qiskit-aer':importlib.metadata.version('qiskit-aer'),'qiskit':importlib.metadata.version('qiskit')},
         'settings':{'method':'statevector','precision':'double','max_parallel_threads':1,'enable_truncation':False,'coherent_pilot_fusion':True,'kernel_fusion':False,'coherent_steps_max':2},
         'measured_pilots':rows,'measured_kernel_timings':kernels,'baseline_subtracted_seconds_per_gate':per,
         'stage_component_projections':stages,'schedule_projections':schedules,
         'limitation':'Actual 20-qubit measurements cover only one/two steps. Full six-step A, event oracle, Grover powers and MLAE runs are not implemented. Runtime projections omit multi-gate fusion, transpiler/global optimization, measurement fitting and variable simulator overhead.'}
    (ROOT/'results/aer_resource_pilot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
