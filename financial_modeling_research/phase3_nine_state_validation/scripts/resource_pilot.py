"""Minimum coherent recurrent-step pilot and component resource measurements.

No full six-step oracle/A/Grover/QAE experiment is built. Whole-circuit costs
are estimates from separately compiled components and declared composition.
"""
import sys,json,time,platform,hashlib,importlib.metadata
from pathlib import Path
import numpy as np
from scipy.linalg import null_space
from qiskit import QuantumCircuit,transpile,qpy
from qiskit.circuit.library import UnitaryGate,Isometry,StatePreparation,MCXGate
from qiskit.quantum_info import Statevector,Operator
ROOT=Path(__file__).resolve().parents[1]

def save(path,obj):(ROOT/path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def compile_record(qc,label):
    t=time.perf_counter();c=transpile(qc,basis_gates=['u','cx'],optimization_level=1,seed_transpiler=4055,approximation_degree=1.0)
    return c,{'label':label,'qubits':c.num_qubits,'depth':c.depth(),'CX':int(c.count_ops().get('cx',0)),'U':int(c.count_ops().get('u',0)),'total_gates':c.size(),'compile_seconds':time.perf_counter()-t}

def main():
    t0=time.perf_counter();d=json.loads((ROOT/'results/zero_phase_quantum.json').read_text());m=json.loads((ROOT/'model/nine_state_model_specification.json').read_text())
    K=np.array(d['Kraus']);S=np.array(d['memory_states_columns']);V=np.zeros((64,16),complex)
    for x in range(3):V[16*x:16*x+9,:9]=K[x]
    for i in range(9,16):V[i,i]=1
    U=np.column_stack([V,null_space(V.conj().T)]);mem=np.zeros((16,9),complex);mem[:9]=S
    assert np.linalg.norm(U.conj().T@U-np.eye(64))<1e-10
    np.savez_compressed(ROOT/'model/coherent_step_arrays.npz',unitary=U,isometry=V,memory_states=mem)
    naive=QuantumCircuit(6,name='dense_U_step');naive.append(UnitaryGate(U),range(6))
    iso=QuantumCircuit(6,name='isometry_U_step');iso.append(Isometry(V,0,0),range(6))
    compiled=[];records=[]
    for qc,label in [(naive,'generic_64x64_unitary'),(iso,'64x16_input_isometry')]:
        c,r=compile_record(qc,label);op=Operator(c).data
        r['input_isometry_error']=float(np.linalg.norm(op[:,:16]-V));assert r['input_isometry_error']<1e-8
        compiled.append(c);records.append(r);print('Step synthesis',r,flush=True)
    best_index=min(range(2),key=lambda i:records[i]['CX']);best=compiled[best_index];cost=records[best_index]
    with (ROOT/'model/recurrent_step_pilot.qpy').open('wb') as f:qpy.dump(compiled,f)
    path_checks=[];p=np.array(m['emission_probabilities']);nxt=np.array(m['lambda'])
    from itertools import product
    for L in [1,2]:
        for s in range(9):
            qc=QuantumCircuit(4+2*L);qc.append(StatePreparation(mem[:,s]),range(4))
            for j in range(L):qc.append(UnitaryGate(U),list(range(4))+[4+2*j,5+2*j])
            t=time.perf_counter();sv=Statevector.from_instruction(qc);elapsed=time.perf_counter()-t
            err=0;validmass=0
            for word in product(range(3),repeat=L):
                code=sum(x*4**j for j,x in enumerate(word));pr=float(np.sum(abs(sv.data[16*code:16*(code+1)])**2));validmass+=pr
                state=s;expected=1.
                for x in word:expected*=p[state,x];state=nxt[state,x]
                err=max(err,abs(pr-expected))
            back=sv.evolve(qc.inverse()).data;inverse=float(np.linalg.norm(back-np.eye(1,len(back),0).ravel()))
            path_checks.append({'L':L,'state':s,'max_word_probability_error':err,'invalid_output_mass':max(0.,1-validmass),'inverse_error':inverse,'seconds':elapsed})
            assert err<1e-10 and inverse<1e-9
    # Validate a two-step actually compiled pilot from both nontrivial conditions.
    for s in [0,8]:
        qc=QuantumCircuit(8);qc.append(StatePreparation(mem[:,s]),range(4));qc.compose(best,range(6),inplace=True);qc.compose(best,[0,1,2,3,6,7],inplace=True)
        t=time.perf_counter();sv=Statevector.from_instruction(qc);elapsed=time.perf_counter()-t;err=0
        for x,y in product(range(3),repeat=2):
            code=x+4*y;pr=float(np.sum(abs(sv.data[16*code:16*(code+1)])**2));err=max(err,abs(pr-p[s,x]*p[nxt[s,x],y]))
        assert err<1e-9;path_checks.append({'kind':'compiled_two_step','state':s,'max_word_probability_error':err,'seconds':elapsed})
    save('results/coherent_path_pilot.json',path_checks)
    init=[]
    for s in range(9):
        qc=QuantumCircuit(4);qc.append(StatePreparation(mem[:,s]),range(4));_,r=compile_record(qc,f'initializer_{s}');init.append(r)
    primitives=[]
    for controls in [2,3,4,19]:
        qc=QuantumCircuit(controls+1);qc.append(MCXGate(controls),range(controls+1));_,r=compile_record(qc,f'C{controls}X_no_extra_qubits');primitives.append(r);print('Primitive',r,flush=True)
    cat={int(r['label'].split('X')[0][1:]):r for r in primitives};maxinit={q:max(z[q] for z in init) for q in ['CX','U','depth']}
    # Negative-control high symbol ==2: flip output low bit before and after
    # every controlled increment. 6 increments plus 6 inverses =24 X gates.
    oracle={}
    for metric in ['CX','U','depth']:
        oracle[metric]=12*cat[4][metric]+13*cat[3][metric]+13*cat[2][metric]+(0 if metric=='U' else 1)
        if metric in ['U','depth']:oracle[metric]+=24
    # Reflection: X on 20 qubits, H on one, MCX19, H, X on 20.
    reflection={q:cat[19][q]+(42 if q in ['U','depth'] else 0) for q in ['CX','U','depth']}
    A={q:maxinit[q]+6*cost[q]+oracle[q] for q in ['CX','U','depth']}
    # Microbench full dense width on core Statevector, separate from circuit pilot.
    rng=np.random.default_rng(4055);n=20;data=rng.normal(size=2**n)+1j*rng.normal(size=2**n);data/=np.linalg.norm(data);sv=Statevector(data)
    kernels=[]
    for kind in ['u','cx']:
        qc=QuantumCircuit(n)
        for j in range(16):
            if kind=='u':qc.u(.23,.47,.61,j%n)
            else:qc.cx(j%n,(j+7)%n)
        ts=[]
        for _ in range(3):
            t=time.perf_counter();out=sv.evolve(qc);ts.append(time.perf_counter()-t);assert abs(np.linalg.norm(out.data)-1)<1e-10
        kernels.append({'gate':kind,'width':20,'gates_per_timing':16,'seconds':ts,'median_seconds_per_gate':float(np.median(ts)/16)})
    per={z['gate']:z['median_seconds_per_gate'] for z in kernels}
    stages=[]
    for k in [0,1,2,4,8]:
        counts={q:(2*k+1)*A[q]+k*reflection[q]+(k if q in ['U','depth'] else 0) for q in ['CX','U','depth']}
        sec=counts['CX']*per['cx']+counts['U']*per['u']
        stages.append({'Grover_power':k,'A_or_Adagger':2*k+1,**counts,'core_Statevector_seconds_microbenchmark_projection':float(sec)})
    schedules=[]
    for powers in [[0,1,2,4],[0,1,2,4,8]]:
        one=sum(z['core_Statevector_seconds_microbenchmark_projection'] for z in stages if z['Grover_power'] in powers)
        for reps in [100,200]:
            schedules.append({'powers':powers,'replicates':reps,'conditions':5,'shots_per_stage':200,
                              'independent_circuit_statevector_runs':5*len(powers)*reps,
                              'uncached_seconds_projection':float(5*reps*one),
                              'cached_unique_circuits':5*len(powers),'cached_seconds_projection':float(5*one),
                              'logical_A_queries_all_conditions':int(5*reps*200*sum(2*k+1 for k in powers)),
                              'limitation':'component-weighted projection from isolated 20-qubit gate kernels, not a measured six-step A/Grover/MLAE runtime; circuit caching reuses ideal distributions while retaining logical shot/query charges'})
    result={'versions':{p:importlib.metadata.version(p) for p in ['qiskit','rustworkx','dill','stevedore','numpy','scipy']},
            'settings':{'basis':['u','cx'],'optimization_level':1,'seed_transpiler':4055,'approximation_degree':1.0,'coupling_map':'all-to-all','backend':'Qiskit core Statevector; no Aer, GPU or hardware used','max_coherent_steps':2},
            'platform':platform.platform(),'step_compilations':records,'selected_step':cost,'initializers':init,'atomic_primitive_compilations':primitives,
            'registers':{'memory':4,'six_ternary_outputs':12,'counter':3,'flag':1,'total':20,'double_statevector_bytes':16*2**20,'dense_density_matrix_bytes':16*4**20},
            'oracle_analytic_composition':{'C4X':12,'C3X':13,'CCX':13,'CX':1,'X':24,'note':'high symbol == binary 10; comparator flag XOR(c2 OR(c1 AND c0)); counter uncomputed'},
            'oracle_estimated_from_components':oracle,'reflection_estimated_from_components':reflection,'A_L6_component_upper_estimate':A,
            'A_inverse':'inverse the actual synthesized preparation including all count workspace; same estimated costs',
            'stages_estimated':stages,'kernel_timings':kernels,'replicate_feasibility_projection':schedules,
            'evidence_boundary':'Only one/two-step quantum circuits and isolated gate primitives were compiled/simulated. Full six-step oracle, A, Grover and QAE production circuits remain unimplemented.',
            'unitary_residual':float(np.linalg.norm(U.conj().T@U-np.eye(64))),
            'max_pilot_word_probability_error':max(z['max_word_probability_error'] for z in path_checks),
            'elapsed_seconds':time.perf_counter()-t0}
    save('results/quantum_resource_pilot.json',result);print('Resource pilot complete',result['elapsed_seconds'],flush=True)

if __name__=='__main__':main()
