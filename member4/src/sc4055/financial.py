from pathlib import Path
from fractions import Fraction
from itertools import product
import json, numpy as np
ROOT=Path(__file__).resolve().parents[2]
SPEC=json.loads((ROOT/'models/nine_state_model_specification.json').read_text())
P_R=[[Fraction(x) for x in row] for row in SPEC['emission_probabilities_rational']]
P=np.array(P_R,dtype=float)
NEXT=np.array(SPEC['lambda'])
LABELS=SPEC['state_labels']
MEM=json.loads((ROOT/'models/zero_phase_quantum.json').read_text())
ARRAYS=np.load(ROOT/'models/coherent_step_arrays.npz')


def condition(observed_categories):
    """Return the last-two-category state; no unsupported mixture initializer."""
    if len(observed_categories)<2:raise ValueError('At least two completed observations are required')
    a,b=observed_categories[-2:]
    if a not in (0,1,2) or b not in (0,1,2):raise ValueError('Categories must be 0, 1, or 2')
    return int(3*a+b)
