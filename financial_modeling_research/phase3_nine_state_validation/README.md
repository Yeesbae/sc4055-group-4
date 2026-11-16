# SC4055 V3.0 Phase 3 - Focused Nine-State VIX Validation

Decision: **CONDITIONAL GO** as a research demonstrator, not an established superior six-step financial forecaster. Previous V1/V2/Phase-2 artifacts are preserved.

## Main findings

- Fixed observation: <20, 20 to <30, >=30; state is the last two categories. All nine states are distinct and reachable in the fitted process. This does not identify the real VIX causal architecture.
- Full-fit continuation counts for 02 and 20 are 1 and 0. Their reference emission rows are 60% and 100% prior weight. They remain explicit in every model table.
- Direct six-step Brier difference, order 2 minus order 1: approximately -0.000480, a 1.65% relative improvement; all tested moving-block intervals include zero. Full three-category next-step log loss improves more clearly.
- New exact theorem for this fixed fitted process: every transition-phase choice in the pure-state, one-Kraus-per-output unifilar class has memory dimension 9. Dimensions <=8 and <=4 are excluded in that class. General mixed/multiple-Kraus instruments remain unresolved beyond the probability-rank lower bound D>=3.
- The exact zero-phase instrument passes recurrence/completeness. The 6-qubit recurrent-step input-isometry synthesis uses 1,096 CX at the locked settings. Four physical memory qubits remain necessary in the proved phase class.
- An exact six-step count-oracle design uses 20 total qubits. Actual pilots cover only one/two coherent steps, including a full-width 20-qubit Aer check. Full A/Grover/MLAE counts and runtimes are component estimates, not production measurements.

## Deliverables

- `report/SC4055_V3_Phase3_Nine_State_Validation_Report.pdf` and `.md`: focused report.
- `SC4055_V3_Phase3_Nine_State_Model_Specification.json`: standalone frozen conditional research specification.
- `model/nine_state_table.csv`, `T_0.csv`, `T_1.csv`, `T_2.csv`, `T.csv`: complete numerical state estimates and matrices. Read history labels as strings to preserve leading zeroes.
- `results/direct_paired_intervals.csv`: direct contrasts against three-level order 1, by metric, period and block length.
- `results/transition_uncertainty.csv`, `event_uncertainty.csv` and `.npz` draws: nominal, block-refit and hybrid sensitivity distributions. A block bootstrap cannot invent unobserved contexts; do not interpret a constant prior row as precise knowledge.
- `results/all_phase_dimension_certificate.json`, `exact_probability_rank.json`, `phase_identity_checks.json`: exact/validated mathematical evidence.
- `results/quantum_resource_pilot.json`, `aer_resource_pilot.json`: measured components and explicitly separated projections.
- `Mathematical_Verification.md`, `V3_Model_Decision.json`, `Next_Phase_Implementation_Contract.md`: proofs, conditional decision and precise next gate.
- `figures/`: publication-oriented PNG and SVG versions.

## Reproduction

Python 3.12 and the versions in `requirements.txt` were tested. From this directory:

```bash
python -m pip install -r requirements.txt
python scripts/download_vix.py --output private_data/VIX_History.csv
python -m src.analysis private_data/VIX_History.csv
python scripts/additional_diagnostics.py private_data/VIX_History.csv
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/resource_pilot.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/aer_resource_pilot.py
python scripts/finalize_decision.py private_data/VIX_History.csv
python -m unittest discover -s tests -v
python scripts/make_figures.py
python scripts/build_report.py
```

The official raw CSV is excluded because redistribution permission was not established. The canonical historical date/CLOSE prefix hash is checked before fitting, with a fixed cutoff of 2026-10-23. Later rows are excluded. A revised historical prefix requires a newly versioned investigation; the manifests cannot reconstruct historical bytes if the official source changes them. No point-in-time historical-vintage database is claimed.

PDF regeneration also uses the free DejaVu Sans font files under `/usr/share/fonts/truetype/dejavu/`; install that font package or adjust the font paths on another operating system. Numerical analysis does not depend on those paths.

The model fitting and structural utility files under `src/` are copied unchanged from Phase 2 except for the new focused analysis modules; no previous files are imported or modified. The preserved Phase-2 forecast ledger is a reconstruction target, not fresh confirmation.

Circuit resource comparisons use all-to-all connectivity, basis u/cx, optimization level 1, exact synthesis and seed 4055. Aer uses CPU, double precision, one thread, disabled idle-qubit truncation. No noise, GPU speed or hardware advantage is inferred. The repeated-estimator experiment belongs to the next phase.
