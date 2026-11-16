"""Member 4: classical benchmarking and experimental analysis.
MLAE (EIS/LIS schedules) vs classical Monte Carlo on the VIX stress event
P(>=3 high-stress days in next 6 | history). Noiseless; shots drawn binomially
from the exact flag probability sin^2((2m+1)theta), as in Section 3.2."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- 1. Fitted chain (Table 1): recover integer counts, rebuild smoothed probs
STATES = ["00","01","02","10","11","12","20","21","22"]
NS = dict(zip(STATES, [5611,254,1,255,2349,92,0,93,644]))
P_TAB = {"00":(.966860,.032873,.000267),"01":(.397260,.592955,.009785),
         "02":(.2,.6,.2),"10":(.723197,.274854,.001949),
         "11":(.065731,.903850,.030419),"12":(.005348,.304813,.689840),
         "20":(1/3,1/3,1/3),"21":(.005291,.788360,.206349),
         "22":(.000775,.099923,.899303)}
P = {}
for s in STATES:
    cnt = [round(p*(NS[s]+1.5)-0.5) for p in P_TAB[s]]
    P[s] = np.array([(c+.5)/(NS[s]+1.5) for c in cnt])      # Eq. (4)

# ---- 2. Exact event probability by dynamic programming over (state, #high)
def exact_p(h, n=6, k=3):
    memo = {}
    def f(s, left, hi):
        if hi >= k: return 1.0
        if left == 0: return 0.0
        key = (s, left, hi)
        if key not in memo:
            memo[key] = sum(P[s][x]*f(s[1]+str(x), left-1, hi+(x==2)) for x in range(3))
        return memo[key]
    return f(h, n, 0)

# ---- 3. Estimators
def mlae(p, ms, rng, Nk=100, grid=10_000):
    th = np.linspace(0, np.pi/2, grid+2)[1:-1]              # avoid log(0)
    ll = np.zeros_like(th)
    for m in ms:
        pm = np.sin((2*m+1)*np.arctan2(np.sqrt(p), np.sqrt(1-p)))**2
        h = rng.binomial(Nk, pm)
        a = np.sin((2*m+1)*th)**2
        ll += h*np.log(a+1e-300) + (Nk-h)*np.log(1-a+1e-300)  # Sec 3.2 likelihood
    return np.sin(th[np.argmax(ll)])**2

def monte_carlo(p, N, rng):
    return rng.binomial(N, p)/N      # N independent six-day paths

def schedules(K):
    return {"EIS": [0]+[2**j for j in range(K)] if K else [0],
            "LIS": list(range(K+1))}
cost = lambda ms, Nk=100: Nk*sum(2*m+1 for m in ms)

# ---- 4. Experiment
def run(hists=("00","01","11","12","22"), trials=300, seed=0):
    rng = np.random.default_rng(seed); out = {}
    for h in hists:
        p = exact_p(h)
        for name in ("EIS","LIS"):
            for K in range(1,5):
                ms = schedules(K)[name]; N = cost(ms)
                e_q = [mlae(p, ms, rng)-p for _ in range(trials)]
                e_c = [monte_carlo(p, N, rng)-p for _ in range(trials)]
                out[(h,name,K)] = (N, np.sqrt(np.mean(np.square(e_q))),
                                      np.sqrt(np.mean(np.square(e_c))), p)
    return out

def slope(out, h, name):             # log-log slope of RMSE vs N, excl. N=400
    pts = [(out[(h,name,K)][0], out[(h,name,K)][1]) for K in range(1,5)]
    pts = [(n,r) for n,r in pts if n > 400]
    return np.polyfit(np.log([n for n,_ in pts]), np.log([r for _,r in pts]), 1)[0]

if __name__ == "__main__":
    out = run()
    print("hist    p       MLAE    MC      ratio  EIS_slope LIS_slope")
    for h in ("00","01","11","12","22"):
        N, rq, rc, p = out[(h,"EIS",4)]
        print(f"{h}  {p:.4f}  {rq:.5f} {rc:.5f}  {rq/rc:.2f}  "
              f"{slope(out,h,'EIS'):+.2f}  {slope(out,h,'LIS'):+.2f}   (N={N})")
    # Figure: RMSE vs queries (log-log), MLAE-EIS vs MC
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.2), sharey=False)
    for ax, h in zip(axs, ("01","12","22")):
        Ns = [out[(h,"EIS",K)][0] for K in range(1,5)]
        ax.loglog(Ns, [out[(h,"EIS",K)][1] for K in range(1,5)], "o-", label="MLAE (EIS)")
        Nl = [out[(h,"LIS",K)][0] for K in range(1,5)]
        ax.loglog(Nl, [out[(h,"LIS",K)][1] for K in range(1,5)], "s--", label="MLAE (LIS)")
        ax.loglog(Ns, [out[(h,"EIS",K)][2] for K in range(1,5)], "^-", label="Monte Carlo")
        ax.set_title(f"history {h}, p={out[(h,'EIS',1)][3]:.3f}", fontsize=9)
        ax.set_xlabel("queries N"); ax.grid(alpha=.3, which="both")
    axs[0].set_ylabel("RMSE"); axs[0].legend(fontsize=7)
    plt.tight_layout(); plt.savefig("/mnt/user-data/outputs/member4_rmse_vs_queries.png", dpi=200)
