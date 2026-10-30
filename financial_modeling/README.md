# SC4055 — Financial Modeling (V3)

This folder isolates the **financial stochastic model** from the complete SC4055 V3 quantum-project archive. It provides the frozen model, conditioning, classical dynamic programming, exact path enumeration, a seeded Monte Carlo helper, and historical comparison summaries. Quantum circuit/QAE code is intentionally excluded.

## Model and financial interpretation

- Source: Cboe VIX daily closing levels, frozen through **2026-10-23**. The original full raw data file is **not redistributed**.
- Categories: `0` for VIX < 20, `1` for 20 <= VIX < 30, `2` for VIX >= 30.
- Order-2 observed-category Markov process: the nine states are `00,01,02,10,11,12,20,21,22`. State `ab` means the penultimate observation was `a` and the latest completed observation was `b`.
- Transitions: `lambda(ab,x)=bx`; the fixed emission probabilities are in `models/nine_state_model_specification.json`, estimated using a symmetric Dirichlet(0.5,0.5,0.5) smoothing prior.
- Main event: **at least three category-2 observations among the next six trading observations**, conditional on the last two completed categories. The conditioning observations are not counted toward the future event.
- This models sustained **high implied volatility**, not realized portfolio losses, defaults, or forecasted stock returns.

## Repository layout

```text
financial_modeling/
├── models/nine_state_model_specification.json  # frozen fitted counts and probabilities
├── src/sc4055/financial.py                   # model parameters and history conditioning
├── src/sc4055/classical.py                   # exact DP, word enumeration and MC
├── src/sc4055/model.py                       # stable public import facade
├── scripts/demo_financial.py                 # minimal executable demonstration
├── tests/test_financial.py                   # independent DP/enumeration checks
├── results/historical_scores.csv             # preserved retrospective score summary
└── results/phase2_historical_comparators.csv # preserved alternative-model summaries
```

## Run

Use Python 3.10+ from this folder:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/demo_financial.py
```

```python
from sc4055.model import condition, dp
state = condition([1, 2])
p = dp(state, L=6, threshold=3, rational=True)
print(float(p))
```

`dp` is the exact model-conditional target. `monte_carlo(s,n,seed)` returns the count of successful paths among `n` six-step simulations. The function uses frozen probabilities and should not be confused with a market forecast.

## Scope and limitations

The frozen model uses 9 history states, 3 symbols, and 27 strictly positive emission probabilities after smoothing. State `02` has only one observed continuation, and `20` has none; the latter is entirely prior defined. Retrospective six-step event Brier scores from the V3 validation were approximately 0.028651 (order 2) versus 0.029131 (order 1), with a paired uncertainty interval crossing zero. Thus, **better forecasting for this event has not been established**. The full V3 research archive contains the richer fitting, walk-forward evaluation, source verification and sensitivity pipelines; this subset focuses on the frozen interface used by the final experiment.

## Provenance

Files `financial.py`, `classical.py`, and the model JSON originate in the provided `SC4055_V3_Complete_Project(6).zip`. To isolate financial code, `financial.py` no longer eagerly loads the quantum memory JSON and `.npz`; all numerical transition values and classical algorithms remain as archived. The public `model.py` is a finance-only facade. This README, demonstration, tests, and packaging metadata are added for GitHub use. Historical result CSVs are preserved from the V3 archive. No parameter refitting has been performed.
