"""Exploratory zero-phase memory diagnostics; exact rational rank is separate."""
from decimal import Decimal, localcontext
from itertools import product
import math
import numpy as np
from .modeling import exact_partition, rank_modular


def entropy(e):
    e=np.asarray(e);e=e[e>0]
    return float(-sum(e*np.log2(e)))


def quantum_diagnostic(model):
    """After k outputs all contexts synchronize. G=B B^T exactly, B_sw=sqrt P(w|s).
    Decimal Cholesky avoids discarding small positive eigenvalues. Precision is
    a numerical diagnostic, never an exact algebraic rank certificate.
    """
    D=model.n;m=model.m;words=list(product(range(m),repeat=model.k))
    with localcontext() as dc:
        dc.prec=90; zero=Decimal(0);one=Decimal(1)
        p=[[Decimal(q.numerator)/Decimal(q.denominator) for q in row] for row in model.fractions()]
        B=[]
        for i in range(D):
            row=[]
            for word in words:
                s=i;v=one
                for x in word:v*=p[s][x];s=int(model.nxt[s,x])
                row.append(v.sqrt())
            B.append(row)
        G=[[sum((B[i][w]*B[j][w] for w in range(len(words))),zero) for j in range(D)] for i in range(D)]
        L=[[zero for _ in range(D)] for _ in range(D)];pivots=[];ok=True
        for i in range(D):
            for j in range(i+1):
                z=G[i][j]-sum((L[i][r]*L[j][r] for r in range(j)),zero)
                if i==j:
                    pivots.append(str(z))
                    if z<=0:ok=False;break
                    L[i][j]=z.sqrt()
                else:L[i][j]=z/L[j][j]
            if not ok:break
        gf=np.array(G,float)
        recurrence=max(abs(gf[i,j]-sum(math.sqrt(model.p[i,x]*model.p[j,x])*gf[model.nxt[i,x],model.nxt[j,x]] for x in range(m))) for i in range(D) for j in range(D))
        result={'zero_phase_Gram':gf.tolist(),'eigenvalues_float64':np.linalg.eigvalsh(gf).tolist(),
                'gram_recurrence_max_abs':float(recurrence),'precision_decimal_digits':90,
                'cholesky_squared_pivots_90digit':pivots,'all_90digit_pivots_positive':ok,
                'rank_status':'full rank numerically supported at 90 digits, not an exact symbolic Gram-rank proof' if ok else 'numerically unresolved; do not truncate and call exact',
                'analytic_validity':'G is PSD, unit diagonal and recurrent by synchronization after k outputs; independent of rank tolerance',
                'no_global_optimization':True}
        if ok:
            S=[[L[j][i] for j in range(D)] for i in range(D)]
            # Inverse of upper triangular S at high precision.
            inv=[[zero for _ in range(D)] for _ in range(D)]
            for i in range(D-1,-1,-1):
                inv[i][i]=one/S[i][i]
                for j in range(i+1,D):inv[i][j]=-sum((S[i][r]*inv[r][j] for r in range(i+1,j+1)),zero)/S[i][i]
            ops=[]
            for x in range(m):
                Y=[[p[i][x].sqrt()*S[r][model.nxt[i,x]] for i in range(D)] for r in range(D)]
                K=[[sum((Y[r][j]*inv[j][c] for j in range(D)),zero) for c in range(D)] for r in range(D)]
                ops.append(np.array(K,float))
            sf=np.array(S,float)
            rec=max(np.linalg.norm(ops[x]@sf[:,i]-math.sqrt(model.p[i,x])*sf[:,model.nxt[i,x]]) for x in range(m) for i in range(D))
            comp=np.linalg.norm(sum(k.T@k for k in ops)-np.eye(D))
            rho=sf@np.diag(model.stationary())@sf.T
            result.update(memory_states_columns=sf.tolist(),Kraus=[k.tolist() for k in ops],
                          recurrence_residual=float(rec),completeness_residual=float(comp),
                          stationary_classical_entropy=entropy(model.stationary()),
                          stationary_quantum_entropy=entropy(np.linalg.eigvalsh(rho)),
                          condition_number_S=float(np.linalg.cond(sf)),
                          instrument_numerically_valid=bool(rec<1e-9 and comp<1e-9))
        result['partition']=exact_partition(model);result['probability_rank']=rank_modular(model)
        result['registers']={'classical_predictive_states':result['partition']['D_c'],
                            'conventional_memory_qubits_upper_bound':math.ceil(math.log2(D)),
                            'future_output_qubits_L6':6*math.ceil(math.log2(m)),
                            'count_workspace_qubits':3,'event_flag':1,
                            'total_width_upper_bound_design':math.ceil(math.log2(D))+6*math.ceil(math.log2(m))+4,
                            'note':'register design estimate; no compiled circuit; ternary invalid padded label must have zero amplitude'}
        return result
