"""Exact all-phase rank obstruction for an order-two observed Markov model.

No phase optimizer is required if every 3x3 emission-amplitude block has a
strictly dominant determinant monomial. Square-root bounds use only integers
and rational arithmetic, so the certificate is not a floating rank threshold.
"""
from fractions import Fraction
from itertools import permutations
from math import isqrt
import numpy as np


def sqrt_enclosure(q,digits=40):
    q=Fraction(q);scale=10**digits
    n=isqrt(q.numerator*scale*scale//q.denominator)
    assert n*n*q.denominator<=q.numerator*scale*scale<(n+1)**2*q.denominator
    return Fraction(n,scale),Fraction(n+1,scale)


def all_phase_certificate(model):
    assert model.k==2 and model.m==3
    p=model.fractions();perms=list(permutations(range(3)));blocks=[]
    lower_B=Fraction(1)
    for b in range(3):
        terms=[]
        for perm in perms:
            q=Fraction(1)
            for a,x in enumerate(perm):q*=p[3*a+b][x]
            lo,hi=sqrt_enclosure(q)
            terms.append({'permutation':list(perm),'squared_magnitude':str(q),'lo':lo,'hi':hi})
        j=max(range(6),key=lambda i:terms[i]['lo'])
        bound=terms[j]['lo']-sum((t['hi'] for i,t in enumerate(terms) if i!=j),Fraction(0))
        lower_B*=bound**2
        blocks.append({'current_symbol':b,'histories':[f'{a}{b}' for a in range(3)],
                       'dominant_permutation':terms[j]['permutation'],'strict_determinant_lower_bound':str(bound),
                       'strict_determinant_lower_bound_float':float(bound),'certified_phase_nonsingular':bound>0,
                       'terms':[{'permutation':t['permutation'],'squared_magnitude':t['squared_magnitude'],'lower':str(t['lo']),'upper':str(t['hi'])} for t in terms]})
    success=all(b['certified_phase_nonsingular'] for b in blocks)
    return {'blocks':blocks,'all_blocks_phase_nonsingular':success,
            'future_amplitude_determinant_abs_lower_bound':str(lower_B) if success else None,
            'future_amplitude_determinant_abs_lower_bound_float':float(lower_B) if success else None,
            'Gram_determinant_lower_bound_float':float(lower_B**2) if success else None,
            'pure_phase_memory_dimension_exact':9 if success else None,
            'Dq_le8_in_this_class':'excluded' if success else 'not excluded by this certificate',
            'Dq_le4_in_this_class':'excluded' if success else 'not excluded by this certificate',
            'proof_scope':'Pure normalized history-conditioned memory states; one Kraus operator per emitted symbol; K_x sigma_ab = sqrt(p(x|ab))*exp(i phi_abx)*sigma_bx; fixed autonomous recurrence. Arbitrary transition phases covered.',
            'general_instrument_scope':'Mixed history memories or multi-Kraus-per-output realizations are NOT excluded by this phase theorem. Probability rank nine only gives D>=3 for a general fixed instrument.',
            'factorization':'R_b[a,x]=sqrt(p(x|ab))*exp(i phi_abx). B[(b,a),(x,y)]=R_b[a,x] R_x[b,y]. After a row permutation B=diag(R_b) P diag(R_x). Thus abs(det B)=product_b abs(det R_b)^2. G=B.conj() B.T has rank nine for all phases.',
            'precision':'Exact rational sqrt enclosures of width 10^-40, verified by integer inequalities; positive margins prove the conclusion without numerical eigenvalue cutoffs.'}


def future_amplitude(model,phases=None):
    phi=np.zeros((9,3)) if phases is None else np.asarray(phases)
    out=np.empty((9,9),complex)
    for s in range(9):
        for x in range(3):
            j=model.nxt[s,x]
            for y in range(3):out[s,3*x+y]=np.sqrt(model.p[s,x]*model.p[j,y])*np.exp(1j*(phi[s,x]+phi[j,y]))
    return out


def rational_determinant(model):
    """Independent exact Gaussian elimination of length-two probabilities."""
    p=model.fractions();a=[]
    for s in range(9):
        a.append([p[s][x]*p[model.nxt[s,x]][y] for x in range(3) for y in range(3)])
    d=Fraction(1)
    for c in range(9):
        pivot=next((i for i in range(c,9) if a[i][c]),None)
        if pivot is None:return Fraction(0)
        if pivot!=c:a[pivot],a[c]=a[c],a[pivot];d=-d
        v=a[c][c];d*=v
        for i in range(c+1,9):
            f=a[i][c]/v
            for j in range(c+1,9):a[i][j]-=f*a[c][j]
            a[i][c]=0
    return d
