import unittest
from pathlib import Path
import sys,json
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.modeling import fit,contexts,event_dp,enumerate_event,exact_partition,rank_modular,Model
from src.structure import quantum_diagnostic


class ResearchTests(unittest.TestCase):
    def test_base_m_history_and_update(self):
        y=np.array([0,1,2,0,2])
        self.assertEqual(contexts(y,2,3).tolist(),[0,1,5,6,2])
        v=np.tile([10.,25.,40.],30)
        m,_,_=fit(v,'ternary20_30',2,80)
        self.assertEqual(m.nxt[5].tolist(),[6,7,8])
        self.assertTrue(np.allclose(m.matrices().sum(0).sum(1),1))

    def test_future_invariance_of_fitting(self):
        rng=np.random.default_rng(9);v=rng.uniform(10,50,150);vv=v.copy();vv[90:]=1000
        for name in ['binary30','binary_train_q80','ternary_train_tertiles']:
            a,_,_=fit(v,name,3,90);b,_,_=fit(vv,name,3,90)
            self.assertEqual(a.edges,b.edges);np.testing.assert_array_equal(a.counts,b.counts)

    def test_future_equivalence_requires_more_than_emission_equality(self):
        counts=np.array([[9,1],[9,1],[2,8],[2,8]])
        p=(counts+.5)/(counts.sum(1,keepdims=True)+1)
        nxt=np.array([[(2*s+x)%4 for x in range(2)] for s in range(4)])
        m=Model('test',2,2,.5,[30],counts,p,nxt,40)
        self.assertEqual(exact_partition(m)['D_c'],4)
        m.counts[:]=[9,1];m.p[:]=[9.5/11,1.5/11]
        self.assertEqual(exact_partition(m)['D_c'],1)
        self.assertLess(rank_modular(m)['rank_mod_p'],4)

    def test_DP_independent_enumeration(self):
        rng=np.random.default_rng(4055);v=rng.uniform(10,50,180)
        for name,k in [('binary30',2),('ternary20_30',1)]:
            m,_,_=fit(v,name,k,150)
            for L in [1,3,5]:
                for kind,K in [('count',0),('count',2),('count',6),('hit',1),('run',2)]:
                    dp=event_dp(m,L,K,kind=kind)
                    for s in range(m.n):self.assertAlmostEqual(dp[s],enumerate_event(m,s,L,K,kind=kind),places=12)

    def test_Gram_and_instrument(self):
        rng=np.random.default_rng(27);m,_,_=fit(rng.uniform(10,60,500),'binary30',2,450)
        d=quantum_diagnostic(m)
        self.assertLess(d['gram_recurrence_max_abs'],1e-12)
        self.assertTrue(d['instrument_numerically_valid'])
        S=np.array(d['memory_states_columns']);Ks=np.array(d['Kraus'])
        for s in range(m.n):
            for word in [(0,1,0),(1,1,1),(1,0,0)]:
                q=S[:,s];prob=1.;state=s
                for x in word:q=Ks[x]@q;prob*=m.p[state,x];state=m.nxt[state,x]
                self.assertAlmostEqual(q@q,prob,places=12)

    def test_saved_forecast_temporal_contract(self):
        import pandas as pd
        root=Path(__file__).resolve().parents[1]
        p=root/'results/outer_forecasts.csv.gz'
        if not p.exists():self.skipTest('run pipeline first')
        d=pd.read_csv(p,low_memory=False)
        self.assertTrue((pd.to_datetime(d.train_end).dt.year<d.year).all())
        self.assertTrue((pd.to_datetime(d.next_date).dt.year==d.year).all())
        self.assertTrue(d.loc[~d.event_eligible,'event_truth'].isna().all())
        for r in json.loads((root/'results/nested_selections.json').read_text()):
            self.assertIn(r['selected']['name'],['binary30','ternary20_30'])
        z=d[d.event_eligible]
        self.assertLess(np.max(np.abs(z.event_brier-(z.event_pred-z.event_truth)**2)),1e-14)

    def test_minimal_quotient_preserves_word_probabilities(self):
        from itertools import product
        root=Path(__file__).resolve().parents[1]
        p=root/'models/ternary20_30_k3/model.json'
        if not p.exists():self.skipTest('run pipeline first')
        m=json.loads(p.read_text());q=json.loads((p.parent/'minimal_predictive_model.json').read_text())
        self.assertEqual(q['D_c'],24)
        for s in range(27):
            for word in product(range(3),repeat=4):
                i=s;j=q['original_to_minimal'][s];a=b=1.
                for x in word:
                    a*=m['emission_probabilities'][i][x];i=m['lambda'][i][x]
                    b*=q['emissions'][j][x];j=q['lambda'][j][x]
                self.assertAlmostEqual(a,b,places=14)

    def test_every_exported_fit_normalized_and_past_only(self):
        import gzip
        root=Path(__file__).resolve().parents[1];p=root/'results/all_fitted_models.json.gz'
        if not p.exists():self.skipTest('run pipeline first')
        fits=json.loads(gzip.decompress(p.read_bytes()))
        self.assertEqual(len(fits),708)
        for f in fits:
            self.assertLess(int(f['fit_end'][:4]),f['score_year'])
            pp=np.array(f['emissions']);tx=np.array(f['T_emission'])
            self.assertTrue((pp>0).all());np.testing.assert_allclose(pp.sum(1),1,atol=1e-14)
            np.testing.assert_allclose(tx.sum((0,2)),1,atol=1e-14)
            self.assertLessEqual(f['predictive_partition']['D_c'],len(pp))


if __name__=='__main__':unittest.main(verbosity=2)
