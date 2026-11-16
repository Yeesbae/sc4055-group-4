# SC4055 V3.0 - Phase 2

Data-driven VIX stochastic modeling and exact predictive-state validation. Research date: 25 October 2026. This is a separate classical research package; it does not modify V1/V2 or implement new QAE circuits.

## Read first

Read `report/SC4055_V3_Phase2_Financial_Modeling_Report.pdf` and `report/Financial_Modeling_Report.md`. The conclusion is conditional: a two-state first-order model is the recorded engineering selection; a three-level first-order model is a stronger pooled retrospective finite-state alternative. Continuous log-VIX event regression performs better than the finite-state models. There is no unique empirically established financial winner and no fresh confirmatory test.

`models/frozen_principal.json`: binary VIX>=30, order 1, final fit through 2026-10-23.

`models/frozen_fallback.json`: IID binary stress generator, intentionally simpler and predictively weaker.

`models/financial_alternative.json`: three-level (<20, 20-<30, >=30), order 1.

`models/binary30_k2/model.json`: supported four-state alternative if the engineering tolerance is tightened. `results/selection_tolerance_sensitivity.csv` makes this dependency explicit.

## Reproduce

Python 3.12 was used. Create an environment and install `requirements.txt`, then run from this directory:

```bash
python scripts/download_vix.py --output private_data/VIX_History.csv
python scripts/run_research.py --data private_data/VIX_History.csv
python scripts/supplementary_analysis.py private_data/VIX_History.csv
python -m unittest discover -s tests -v
python scripts/make_figures.py
python scripts/build_report.py
```

The frozen cutoff is 2026-10-23. New rows beyond the cutoff are ignored. The canonical date/CLOSE prefix hash is checked; a revised historical prefix requires a new version, not silent acceptance. The original full raw hash is recorded separately. If Cboe revises its history, the original bytes might no longer be downloadable; the manifest cannot restore unavailable bytes. No historical-vintage feed or independent exchange-calendar reconstruction is available.

Raw Cboe data are excluded from this archive because redistribution permission was not established. The download script uses only Python's standard library. Derived forecast ledgers, transition counts, estimates, uncertainty samples, plots, and all analysis code are included. No general-purpose trading recommendation is made.

## Audit trail

- `configs/protocol.json`: choices recorded before these comparisons, informed by an already-inspected earlier investigation. This is not a preregistered confirmatory study.
- `results/outer_forecasts.csv.gz`: 99,099 rows of derived forecasts, including all discretization scenarios, the adaptive policy and event-only baselines. `event_eligible=false` rows retain next-step forecasts but have no scored forward-event label.
- `results/fold_scores.csv`, `fold_definitions.json`, `nested_selections.json`: training-only fit and selection evidence.
- `results/all_fitted_models.json.gz`: complete counts, nominal intervals, emissions, matrices, reachable states, exact partitions, quotient transitions and modular rank diagnostics for all 708 historical and smoothing-sensitivity fits.
- `results/paired_block_intervals.csv`: paired block-length and period sensitivity, 2,000 repetitions.
- `results/event_uncertainty.csv`, `*_parameter_draws.npz`: nominal posterior and context-pair block-refit event uncertainty.
- `results/calibration_intervals.csv`, `secondary_event_scores.csv`, `subperiod_transition_estimates.csv`: calibration, alternative events and drift.
- `models/*/context_counts.csv`, `T_*.csv`, `T.csv`, `model.json`, `minimal_predictive_model.json`: explicit parameters, rational emissions and exact quotient.
- `models/*/structural_diagnostics.json`: conventional zero-phase Gram, probability-rank certificate, recurrence/completeness and resource estimates. Failed or unresolved factorizations remain visible.
- `data/prior_evidence`: aggregate outputs used to independently reproduce the previous static split; no old implementation is imported.
- `validation`: executed tests, forecast-ledger integrity, source preservation, run summaries and known limitations.

The 27-history three-level order-3 process reduces to 24 model-defined causal states. Its sparse contexts and unresolved zero-phase factorization do not establish a useful quantum demonstration. Physical qubits, span dimension and stationary entropy are reported separately.

Selection uses the same primary event across binary30 and ternary20_30. Other thresholds define different targets; their raw scores must not be used to choose a threshold. No model was selected by a quantum Gram outcome.

The source preservation record certifies the inputs present in the original workspace. A self-contained rerun without those supplied input files cannot reverify their bytes; it retains that historical record and reports what is currently available.
