# Source mapping

- `models/nine_state_model_specification.json` ← V3 `models/` exact copy
- `src/sc4055/classical.py` ← V3 `src/sc4055/classical.py` exact copy
- `src/sc4055/financial.py` ← V3 equivalent with only quantum asset loading removed
- `src/sc4055/model.py` ← adapted from V3 facade to avoid non-financial imports
- `results/*.csv` ← V3 `results/processed/` exact copies
- `tests/`, `scripts/demo_financial.py`, `pyproject.toml`, `README.md`, `.gitignore` ← standalone packaging additions

This is a focused source release, not the entire historical parameter-estimation and validation pipeline.
