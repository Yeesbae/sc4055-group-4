"""Run from the repository root after pip install -e ."""
from sc4055.model import LABELS, P, NEXT, dp, condition

print("Model: VIX <20, 20-<30, >=30; second-order, nine states")
print("Horizon: six future observations; event: >=3 high-stress observations")
print("Latest completed pair [1,2] -> state:", LABELS[condition([1,2])])
print("Emission matrix shape:", P.shape, "next-state shape:", NEXT.shape)
for state,label in enumerate(LABELS):
    result = dp(state, rational=True)
    print(f"{label}: {float(result):.9f} ({result})")
