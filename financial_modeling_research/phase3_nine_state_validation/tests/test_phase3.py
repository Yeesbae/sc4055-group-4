import unittest,json,gzip,sys,itertools
from pathlib import Path
from fractions import Fraction
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.modeling import fit,event_dp,exact_partition
from src.phase_bounds import sqrt_enclosure,all_phase_certificate,future_amplitude,rational_determinant
from src.analysis import robust_event,event_batch
ROOT=Path(__file__).resolve().parents[1]

def reference():
    x=json.loads((ROOT/'model/nine_state_model_specification.json').read_text())
    from src.modeling import Model
    return Model('ternary20_30',2,3,.5,[20,30],np.array(x['counts']),np.array(x['emission_probabilities']),np.array(x['lambda']),9301)

class Phase3Tests(unittest.TestCase):
    def test_all_nine_emission_matrices_and_stationarity(self):
        m=reference();T=m.matrices();self.assertTrue((m.p>0).all());np.testing.assert_allclose(m.p.sum(1),1,atol=1e-14)
        for s in range(9):
            for x in range(3):self.assertEqual(m.nxt[s,x],3*(s%3)+x);self.assertEqual(np.count_nonzero(T[x,s]),1)
        np.testing.assert_allclose(m.stationary()@T.sum(0),m.stationary(),atol=1e-13)
        self.assertEqual(exact_partition(m)['D_c'],9);self.assertNotEqual(rational_determinant(m),0)

    def test_exact_sqrt_bounds_and_all_phase_obstruction(self):
        for q in [Fraction(2,3),Fraction(3,11225),Fraction(1,10**12),Fraction(49,81)]:
            lo,hi=sqrt_enclosure(q);self.assertLessEqual(lo*lo,q);self.assertGreater(hi*hi,q)
        m=reference();cert=all_phase_certificate(m);self.assertTrue(cert['all_blocks_phase_nonsingular'])
        for b in cert['blocks']:self.assertGreater(Fraction(b['strict_determinant_lower_bound']),0)

    def test_certificate_does_not_reject_a_degenerate_counterexample(self):
        m=reference();m.counts[:]=[2,2,2];m.p[:]=1/3
        self.assertFalse(all_phase_certificate(m)['all_blocks_phase_nonsingular'])

    def test_independent_two_step_amplitude_factorization(self):
        from scipy.linalg import block_diag
        m=reference();rng=np.random.default_rng(19)
        for _ in range(10):
            phi=rng.uniform(-np.pi,np.pi,(9,3));blocks=[np.sqrt(m.p[[3*a+b for a in range(3)]])*np.exp(1j*phi[[3*a+b for a in range(3)]]) for b in range(3)]
            A=block_diag(*blocks);P=np.zeros((9,9))
            for b,x in itertools.product(range(3),repeat=2):P[3*b+x,3*x+b]=1
            B=future_amplitude(m,phi)[[0,3,6,1,4,7,2,5,8]]
            np.testing.assert_allclose(A@P@A,B,atol=1e-14)

    def test_event_DP_matches_rational_reference(self):
        m=reference();rows=json.loads((ROOT/'model/nine_state_model_specification.json').read_text())['exact_events_rational']
        for key,kind,K in [('count3of6','count',3),('hit6','hit',1),('run3in6','run',3)]:
            np.testing.assert_allclose(event_dp(m,6,K,kind=kind),[float(Fraction(x)) for x in rows[key]],atol=1e-13)

    def test_rare_row_robust_envelope_covers_fixed_draws(self):
        m=reference();lo,hi=robust_event(m);rng=np.random.default_rng(20);ps=np.tile(m.p,(100,1,1));ps[:,2]=rng.dirichlet([.4,.4,.4],100);ps[:,6]=rng.dirichlet([.4,.4,.4],100)
        a=event_batch(m,ps);self.assertTrue((a>=lo-1e-13).all());self.assertTrue((a<=hi+1e-13).all())

    def test_sparse_context_never_masquerades_as_observed(self):
        m=reference();self.assertEqual(m.counts[2].sum(),1);self.assertEqual(m.counts[6].sum(),0)
        np.testing.assert_allclose(m.p[6],[1/3]*3)
        import pandas as pd
        z=pd.read_csv(ROOT/'results/transition_uncertainty.csv');a=z[(z.state==6)&(z.method=='nominal_Dirichlet')]
        self.assertTrue(((a.hi-a.lo)>.8).all())

    def test_forecast_temporal_alignment_and_preserved_phase2(self):
        import pandas as pd
        d=pd.read_csv(ROOT/'results/forecasts.csv.gz');self.assertEqual(len(d),5*3003)
        self.assertTrue((pd.to_datetime(d.target_date).dt.year==d.year).all());self.assertTrue(d.loc[~d.event_eligible,'event_truth'].isna().all())
        x=json.loads((ROOT/'validation/phase2_forecast_reconstruction.json').read_text());self.assertTrue(all(a['max_difference']<1e-12 for a in x))

    def test_padded_quantum_step_and_recorded_pilot(self):
        z=np.load(ROOT/'model/coherent_step_arrays.npz');U,V,S=z['unitary'],z['isometry'],z['memory_states'];np.testing.assert_allclose(U.conj().T@U,np.eye(64),atol=1e-12);np.testing.assert_allclose(U[:,:16],V,atol=1e-14)
        m=reference()
        for s in range(9):
            target=np.zeros(64,complex)
            for x in range(3):target[16*x:16*(x+1)]=np.sqrt(m.p[s,x])*S[:,m.nxt[s,x]]
            np.testing.assert_allclose(U@np.r_[S[:,s],np.zeros(48)],target,atol=1e-12)
        p=json.loads((ROOT/'results/quantum_resource_pilot.json').read_text());self.assertEqual(p['registers']['total'],20);self.assertLess(p['max_pilot_word_probability_error'],1e-9)

if __name__=='__main__':unittest.main(verbosity=2)
