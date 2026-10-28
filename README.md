# Quantum Amplitude Estimation (QAE)

Estimates the probability of a financial risk event with Maximum Likelihood Amplitude Estimation (MLAE), and compares its accuracy against classical Monte Carlo at equal query cost.

Built and validated on the two-state Markov-switching model (Normal / Stressed regimes, 3-day horizon). The Grover operator and MLAE code take any state-preparation circuit as input, so they can be reused with other models.

## Files

| File | Contents |
| --- | --- |
| `qae.py` | All circuits and functions (import this) |
| `qae_demo.ipynb` | Validation checks, experiments and plots |
| `output/` | Saved plots (`rmse_vs_N_*.png`) and raw results (`rmse_*.csv`) |

## Setup

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install qiskit scipy pandas matplotlib ipykernel
```

No Qiskit Aer is needed. Sampling uses Qiskit's built-in `StatevectorSampler`.

## Quick start

```python
from qae import *

A = build_A_markov_loss()          # state preparation + loss-event flag
Q = grover_op(A, flag_qubit=3)     # Grover operator
p_hat, N = mlae(A, Q, eis(4), shots=100, flag_qubit=3)
print(p_hat, N)                    # about 0.035, N = 3500
```

## Pipeline

1. **Encode the model.** One qubit per day (0 = Normal, 1 = Stressed). RY and controlled-RY rotations load the transition probabilities, giving a superposition of all 8 regime paths.
2. **Mark the event.** A flag qubit (qubit 3) is rotated so that P(flag = 1) equals the event probability.
3. **Amplify.** The Grover operator Q = A′ S₀ A′† S_χ rotates the state so that P(flag = 1) = sin²((2m+1)θ) after m steps, where sin²θ = p.
4. **Estimate.** MLAE combines measurement counts from several values of m into one maximum-likelihood estimate p̂ = sin²θ̂.

## Main functions

| Function | Description |
| --- | --- |
| `build_A_markov()` | 3-qubit Markov regime model (no flag) |
| `build_A_markov_marked()` | Adds flag for "stressed on day 3" (exact p = 0.219) |
| `build_A_markov_loss()` | Adds flag for "3-day log loss ≤ −5%" (exact p = 0.0348193) |
| `reflect_zero(n)` | Reflection S₀ = I − 2\|0…0⟩⟨0…0\| |
| `grover_op(A, flag_qubit)` | Grover operator Q for any marked circuit A′ |
| `count_hits(...)` | Runs Q^m A′ with shots and counts flag = 1 |
| `mlae(A, Q, ms, shots, flag_qubit)` | Returns (p̂, number of queries to A) |
| `lis(K)`, `eis(K)` | Linear and exponential Grover schedules |
| `run_experiment(A, Q, p_true, ...)` | RMSE vs query count for LIS, EIS and classical |
| `summarise(results, label)` | Prints the RMSE table and slopes; saves a CSV |
| `plot_results(results, title, filename)` | Log-log RMSE plot, saved to `output/` |
| `resources(qc)` | Qubits, CX count and depth after transpiling |

## Reproducing the results

```python
from qae import *
np.random.seed(40552026)

A = build_A_markov_loss()
res = run_experiment(A, grover_op(A, 3), p_true=0.034819255)   # 300 trials, a few minutes
summarise(res, "loss")
plot_results(res, "Estimation error vs query count (3-day loss ≤ −5%)", "rmse_vs_N_loss.png")
```

Results for the loss event (300 trials per point, 100 shots per circuit):

| Method | RMSE at N = 6,800 | Log-log slope |
| --- | --- | --- |
| Classical Monte Carlo | 0.00231 | −0.46 |
| MLAE, linear schedule | — | −0.75 |
| MLAE, exponential schedule | 0.00083 | −0.68 |

MLAE has lower error than classical at every budget tested, about 2.8× lower at N = 6,800. The linear schedule's maximum budget is 3,600, so it has no entry at 6,800.

## Notes

- **Qubit order:** qubit 0 = day 1, qubit 2 = day 3, qubit 3 = flag. Qiskit prints qubit 0 as the rightmost character of a bit string.
- **Changing the event:** `run_experiment` calls `clear_cache()` automatically. If you call `mlae` directly with a new circuit, call `clear_cache()` first, or cached probabilities from the previous circuit will be reused.
- **Fast sampling:** `mlae` uses `count_hits_fast`, which computes each circuit's exact flag probability once and then draws binomial samples. For noiseless simulation this is statistically identical to running the shots. Switch to `count_hits` for direct circuit sampling.
- **Using another model:** any `QuantumCircuit` without measurements or resets works as `A`, as long as the event is marked on a flag qubit. Pass that qubit's index as `flag_qubit`.

## Limitations

- Noiseless simulation only. The deepest loss-event circuit has 5,768 CX gates, which would rarely run error-free on current hardware.
- The loss oracle uses one controlled rotation per regime path (2^L), so its cost doubles with each extra day.
- Not yet applied to the nine-state V3 VIX model.

## Reference

J. Chen et al., "Quantum-Enhanced Inference of Conditional Future Probabilities with Reduced Memory Cost," arXiv:2610.10756 (2026).