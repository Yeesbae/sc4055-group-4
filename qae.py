import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from itertools import product
from scipy.stats import norm

from qiskit.circuit.library import RYGate
from qiskit.circuit.library import ZGate
from qiskit.primitives import StatevectorSampler
from qiskit import transpile

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

import json

from member2.sc4055_2 import build_A_structured

def prob_to_angle(prob):
    return 2 * np.arcsin(np.sqrt(prob))

def build_A(prob, n_days):
    angle = prob_to_angle(prob)
    qc = QuantumCircuit(n_days)
    for i in range(n_days):
        qc.ry(angle, i)
    return qc

def build_A_marked(prob, n_days):
    qc = QuantumCircuit(n_days + 1)
    qc.compose(build_A(prob, n_days), range(n_days), inplace=True)
    days = list(range(n_days))
    qc.x(days)
    qc.mcx(days, n_days)
    qc.x(days)
    qc.x(n_days)
    return qc

def build_A_markov():
    p_ns = 0.10
    p_ss = 0.80
    a_ns = prob_to_angle(p_ns)
    a_ss = prob_to_angle(p_ss)
    qc = QuantumCircuit(3)
    qc.ry(a_ns, 0)
    for d in range(1, 3):
        qc.x(d - 1)
        qc.cry(a_ns, d - 1, d)
        qc.x(d - 1)
        qc.cry(a_ss, d - 1, d)
    return qc

def build_A_markov_marked():
    qc = QuantumCircuit(4)
    qc.compose(build_A_markov(), [0, 1, 2], inplace=True)
    qc.cx(2, 3)
    return qc

MU = np.array([0.0005, -0.0020])
SIGMA = np.array([0.010, 0.030])
LOSS_THRESHOLD = -0.05

def loss_probs():
    q = {}
    for path in product(range(2), repeat=3):
        total_mean = sum(MU[i] for i in path)
        total_std = np.sqrt(sum(SIGMA[i] ** 2 for i in path))
        q[path] = norm.cdf(LOSS_THRESHOLD, loc=total_mean, scale=total_std)
    return q

def build_A_markov_loss():
    q = loss_probs()
    qc = QuantumCircuit(4)
    qc.compose(build_A_markov(), [0, 1, 2], inplace=True)
    for path, q_path in q.items():
        zeros = [i for i, s in enumerate(path) if s == 0]
        if zeros:
            qc.x(zeros)
        qc.append(RYGate(prob_to_angle(q_path)).control(3), [0, 1, 2, 3])
        if zeros:
            qc.x(zeros)
    return qc

with open("model/nine_state_model_specification.json") as f:   # need to adjust path to Member 1's file
    SPEC = json.load(f)

REF_V3 = SPEC["exact_model_event_probabilities"]

HI_M2 = lambda t: 4 + 2 * t + 1    # Member 2's layout: out_t on qubits (4+2t, 5+2t); high bit = VIX >= 30

def build_A_v3_marked(start, L=6):
    """Member 2's A for history index `start` (0-8), plus a >=3-of-6 counter oracle; flag on qubit 19."""
    A_mem = build_A_structured(start, L)       # 16 qubits: 4 memory + 12 output
    n = A_mem.num_qubits
    qc = QuantumCircuit(n + 4)
    qc.compose(A_mem, range(n), inplace=True)

    c0, c1, c2, flag = n, n + 1, n + 2, n + 3  # 16, 17, 18, 19
    for t in range(L):                         # count days with VIX >= 30
        qc.mcx([HI_M2(t), c0, c1], c2)
        qc.ccx(HI_M2(t), c0, c1)
        qc.cx(HI_M2(t), c0)

    qc.cx(c2, flag)                            # flag = count >= 3
    qc.x(c2)
    qc.mcx([c2, c1, c0], flag)
    qc.x(c2)
    return qc

def reflect_zero(n):
    qc = QuantumCircuit(n)
    qc.x(range(n))
    mcz = ZGate().control(n - 1)
    qc.append(mcz, list(range(n)))
    qc.x(range(n))
    return qc

def grover_op(A_marked, flag_qubit):
    n = A_marked.num_qubits
    qc = QuantumCircuit(n)
    qc.z(flag_qubit)
    a_cross = A_marked.inverse()
    qc.compose(a_cross, inplace=True)
    s0 = reflect_zero(n)
    qc.compose(s0, inplace=True)
    a_prime = A_marked
    qc.compose(a_prime, inplace=True)
    return qc

def resources(qc):
    t = transpile(qc, basis_gates=["cx", "rz", "sx", "x"], optimization_level=1)
    return t.num_qubits, t.count_ops().get("cx", 0), t.depth()

sampler = StatevectorSampler()

def count_hits(A, Q, m, shots, flag_qubit):
    n = A.num_qubits
    qc = QuantumCircuit(n, 1)
    qc.compose(A, inplace=True)
    for _ in range(m):
        qc.compose(Q, inplace=True)
    qc.measure(flag_qubit, 0)
    result = sampler.run([qc], shots=shots).result()
    counts = result[0].data.c.get_counts()
    return counts.get('1', 0)

_prob_cache = {}
_sv_cache = {}

def clear_cache():
    _prob_cache.clear()
    _sv_cache.clear()

def count_hits_fast(A, Q, m, shots, flag_qubit):
    if m not in _prob_cache:
        done = [k for k in _sv_cache if k <= m]
        if done:
            k = max(done)
            sv = _sv_cache[k]
        else:
            k, sv = 0, Statevector(A)
            _sv_cache[0] = sv
        while k < m:
            sv = sv.evolve(Q)
            k += 1
            _sv_cache[k] = sv
        _prob_cache[m] = sv.probabilities([flag_qubit])[1]
    return np.random.binomial(shots, _prob_cache[m])

def log_likelihood(theta, ms, hs, NS):
    total = 0
    for k in range(len(ms)):
        m = ms[k]
        h = hs[k]
        N = NS[k]
        p = np.sin((2*m + 1) * theta) ** 2
        p = np.clip(p, 1e-12, 1 - 1e-12)
        total += h * np.log(p) + (N - h) * np.log(1 - p)
    return total

def mlae(A, Q, ms, shots, flag_qubit):
    hs = []
    for m in ms:
        h = count_hits_fast(A, Q, m, shots, flag_qubit)
        hs.append(h)
    NS = [shots] * len(ms)
    thetas = np.linspace(0, np.pi / 2, 10_000)
    lls = log_likelihood(thetas, ms, hs, NS)
    theta_hat = thetas[np.argmax(lls)]
    p_hat = np.sin(theta_hat) ** 2
    N_queries = sum(shots * (2*m + 1) for m in ms)
    return p_hat, N_queries

def lis(k):
    result = []
    for i in range(k + 1):
        result.append(i)
    return result

def eis(k):
    result = [0]
    for i in range(k):
        result.append(2 ** i)
    return result

def rmse_mlae(A, Q, ms, shots, flag_qubit, p_true, trials):
    p_hats = []
    for _ in range(trials):
        p_hat, N = mlae(A, Q, ms, shots, flag_qubit)
        p_hats.append(p_hat)
    rmse = np.sqrt(np.mean((np.array(p_hats) - p_true) ** 2))
    return rmse, N

def rmse_classical(N, p_true, trials):
    p_hats = []
    for _ in range(trials):
        p_hat = np.random.binomial(N, p_true) / N
        p_hats.append(p_hat)
    rmse = np.sqrt(np.mean((np.array(p_hats) - p_true) ** 2))
    return rmse

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# For 2 state uses: flag_qubit=3 and K_max=5
def run_experiment(A, Q, p_true, trials=300, K_max=4, shots=100, flag_qubit=19):
    """RMSE vs query count for LIS, EIS and classical Monte Carlo at matched N."""
    clear_cache()
    results = {"LIS": [], "EIS": [], "Classical": []}
    for K in range(1, K_max + 1):
        rmse, N = rmse_mlae(A, Q, lis(K), shots, flag_qubit, p_true, trials)
        results["LIS"].append((N, rmse))
        rmse, N = rmse_mlae(A, Q, eis(K), shots, flag_qubit, p_true, trials)
        results["EIS"].append((N, rmse))
        results["Classical"].append((N, rmse_classical(N, p_true, trials)))
    return results

def summarise(results, label):
    """Print the RMSE table and slopes, and save the raw numbers to CSV."""
    rows = [{"method": m, "N": n, "rmse": r} for m, pts in results.items() for n, r in pts]
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / f"rmse_{label}.csv", index=False)
    print(f"\n=== {label} ===")
    print(df.pivot(index="N", columns="method", values="rmse"))
    for m, pts in results.items():
        Ns = np.array([n for n, r in pts])
        rs = np.array([r for n, r in pts])
        print(f"{m}: slope {np.polyfit(np.log(Ns), np.log(rs), 1)[0]:.2f} "
              f"(from 2nd point: {np.polyfit(np.log(Ns[1:]), np.log(rs[1:]), 1)[0]:.2f})")
    e, c = results["EIS"][-1], results["Classical"][-1]
    print(f"At N = {e[0]}: EIS {e[1]:.5f} vs classical {c[1]:.5f} -> {c[1] / e[1]:.1f}x lower")

def plot_results(results, title, filename):
    """Log-log RMSE vs N plot, saved to OUTPUT_DIR."""
    plt.figure(figsize=(7, 5))
    for name, points in results.items():
        Ns = [n for n, r in points]
        rmses = [r for n, r in points]
        slope = np.polyfit(np.log(Ns), np.log(rmses), 1)[0]
        plt.loglog(Ns, rmses, "o-", label=f"{name} (slope {slope:.2f})")
    plt.xlabel("Number of queries to A (N)")
    plt.ylabel("RMSE")
    plt.title(title)
    plt.legend()
    plt.grid(True, which="both", alpha=0.3)
    plt.gca().tick_params(axis="x", which="both", rotation=30)
    plt.savefig(OUTPUT_DIR / filename, dpi=200, bbox_inches="tight")
    plt.show()
