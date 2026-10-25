import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import norm
from itertools import product
from pathlib import Path


# Financial Stochastic Modelling 
#
# Model Used: Two-State Markov-Switching Model
#
# State 0: Normal Market
# State 1: Stressed Market

# CONFIGURATION

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Number of simulated trading days
N_DAYS = 1000

# Initial market price
INITIAL_PRICE = 100.0

# Initial market state
# 0 = Normal
# 1 = Stressed
INITIAL_STATE = 0

# Prediction horizon
HORIZON = 3

# Financial loss threshold
# -0.05 means cumulative log return <= -5%
LOSS_THRESHOLD = -0.05

STATE_NAMES = {
    0: "Normal",
    1: "Stressed"
}

#  DEFINE MARKOV-SWITCHING MODEL

# Transition probability matrix
#
#                  Next State
#                Normal  Stressed
# Current Normal   0.90    0.10
# Current Stressed 0.20    0.80

P = np.array([
    [0.90, 0.10],
    [0.20, 0.80]
])

# Mean daily log returns
MU = np.array([
    0.0005,    # Normal: +0.05%
    -0.0020    # Stressed: -0.20%
])

# Daily return standard deviations
SIGMA = np.array([
    0.010,     # Normal: 1%
    0.030      # Stressed: 3%
])

N_STATES = len(MU)


# VALIDATE MODEL PARAMETERS

def validate_model():

    assert P.shape == (N_STATES, N_STATES), \
        "Transition matrix dimensions are incorrect."

    assert np.all(P >= 0), \
        "Transition probabilities cannot be negative."

    assert np.allclose(P.sum(axis=1), 1.0), \
        "Each transition matrix row must sum to 1."

    assert np.all(SIGMA > 0), \
        "Standard deviations must be positive."

    assert 0 <= INITIAL_STATE < N_STATES, \
        "Invalid initial state."

    print("Model validation passed.")


# GENERATE SYNTHETIC FINANCIAL DATA

def generate_synthetic_data(n_days=N_DAYS):

    rng = np.random.default_rng(RANDOM_SEED)

    states = np.zeros(n_days, dtype=int)
    returns = np.zeros(n_days)
    prices = np.zeros(n_days + 1)

    prices[0] = INITIAL_PRICE

    current_state = INITIAL_STATE

    for t in range(n_days):

        # Transition to the next market regime
        current_state = rng.choice(
            N_STATES,
            p=P[current_state]
        )

        states[t] = current_state

        # Generate log return based on market regime
        returns[t] = rng.normal(
            loc=MU[current_state],
            scale=SIGMA[current_state]
        )

        # Update market price
        prices[t + 1] = (
            prices[t] * np.exp(returns[t])
        )

    df = pd.DataFrame({
        "day": np.arange(1, n_days + 1),
        "state": states,
        "state_name": [
            STATE_NAMES[s] for s in states
        ],
        "log_return": returns,
        "price": prices[1:]
    })

    df.to_csv(
        OUTPUT_DIR / "synthetic_market_data.csv",
        index=False
    )

    return df


# 5. CALCULATE MULTI-STEP TRANSITION PROBABILITIES

def calculate_transition_probabilities():

    print("TRANSITION PROBABILITY MATRIX")

    print(P)

    P_horizon = np.linalg.matrix_power(
        P,
        HORIZON
    )

    print(f"\n{HORIZON}-DAY TRANSITION MATRIX:")
    print(P_horizon)

    print(
        f"\nStarting from state {INITIAL_STATE}:"
    )

    for state in range(N_STATES):

        probability = P_horizon[
            INITIAL_STATE,
            state
        ]

        print(
            f"P(S_t+{HORIZON} = {state}) "
            f"= {probability:.6f}"
        )

    pd.DataFrame(
        P,
        index=["Normal", "Stressed"],
        columns=["Normal", "Stressed"]
    ).to_csv(
        OUTPUT_DIR / "transition_matrix.csv"
    )

    pd.DataFrame(
        P_horizon,
        index=["Normal", "Stressed"],
        columns=["Normal", "Stressed"]
    ).to_csv(
        OUTPUT_DIR / "three_day_transition_matrix.csv"
    )

    return P_horizon

# ENUMERATE ALL POSSIBLE FUTURE STATE PATHS

def calculate_exact_path_probabilities():

    paths = list(
        product(range(N_STATES), repeat=HORIZON)
    )

    results = []

    for path in paths:

        probability = 1.0
        previous_state = INITIAL_STATE

        for next_state in path:

            probability *= P[
                previous_state,
                next_state
            ]

            previous_state = next_state

        results.append({
            "path": "".join(map(str, path)),
            "final_state": path[-1],
            "path_probability": probability
        })

    df_paths = pd.DataFrame(results)

    print("EXACT STATE PATH PROBABILITIES")

    print(df_paths.to_string(index=False))

    total_probability = (
        df_paths["path_probability"].sum()
    )

    print(
        f"\nTotal probability: "
        f"{total_probability:.6f}"
    )

    assert np.isclose(total_probability, 1.0)

    df_paths.to_csv(
        OUTPUT_DIR / "exact_path_probabilities.csv",
        index=False
    )

    return df_paths

# EXACT PROBABILITY OF STRESSED MARKET


def calculate_stressed_market_probability(P_horizon):

    probability = P_horizon[
        INITIAL_STATE,
        1
    ]

    print("STRESSED MARKET RISK")

    print(
        f"Probability of stressed market "
        f"after {HORIZON} days:"
    )

    print(f"{probability:.6f}")

    print(f"{probability * 100:.2f}%")

    return probability

# EXACT FINANCIAL LOSS PROBABILITY

def calculate_exact_loss_probability(df_paths):

    results = []

    total_loss_probability = 0.0

    for _, row in df_paths.iterrows():

        path = [
            int(state)
            for state in row["path"]
        ]

        path_probability = row[
            "path_probability"
        ]

        # Sum of conditional means
        total_mean = sum(
            MU[state]
            for state in path
        )

        # Sum of conditional variances
        total_variance = sum(
            SIGMA[state] ** 2
            for state in path
        )

        total_std = np.sqrt(total_variance)

        # Conditional probability of loss
        conditional_loss_probability = norm.cdf(
            LOSS_THRESHOLD,
            loc=total_mean,
            scale=total_std
        )

        # Weighted contribution of this path
        contribution = (
            path_probability *
            conditional_loss_probability
        )

        total_loss_probability += contribution

        results.append({
            "path": row["path"],
            "path_probability": path_probability,
            "total_mean": total_mean,
            "total_std": total_std,
            "conditional_loss_probability":
                conditional_loss_probability,
            "weighted_contribution": contribution
        })

    df_loss = pd.DataFrame(results)

    df_loss.to_csv(
        OUTPUT_DIR / "exact_loss_probability_by_path.csv",
        index=False
    )

    print("EXACT FINANCIAL LOSS PROBABILITY")

    print(
        f"Prediction horizon: {HORIZON} days"
    )

    print(
        f"Log-return loss threshold: "
        f"{LOSS_THRESHOLD:.2%}"
    )

    print(
        f"\nExact probability of loss: "
        f"{total_loss_probability:.8f}"
    )

    print(
        f"Percentage: "
        f"{total_loss_probability * 100:.4f}%"
    )

    return total_loss_probability, df_loss


# VALIDATE EXACT PATH DISTRIBUTION

def validate_reference_probabilities(
    df_paths,
    P_horizon
):

    print("REFERENCE VALIDATION")

    for final_state in range(N_STATES):

        # Sum probabilities of paths ending in state
        path_probability = df_paths.loc[
            df_paths["final_state"] == final_state,
            "path_probability"
        ].sum()

        # Matrix multiplication result
        matrix_probability = P_horizon[
            INITIAL_STATE,
            final_state
        ]

        print(
            f"\nState {final_state}:"
        )

        print(
            f"Path enumeration: "
            f"{path_probability:.8f}"
        )

        print(
            f"Matrix calculation: "
            f"{matrix_probability:.8f}"
        )

        assert np.isclose(
            path_probability,
            matrix_probability
        )

    print("\nAll reference probabilities validated.")


# VISUALISE SYNTHETIC MARKET PRICES

def plot_synthetic_prices(df):

    plt.figure(figsize=(12, 5))

    plt.plot(
        df["day"],
        df["price"],
        linewidth=1.3,
        label="Synthetic Market Price"
    )

    plt.title(
        "Synthetic Financial Market Prices\n"
        "Two-State Markov-Switching Model"
    )

    plt.xlabel("Trading Day")
    plt.ylabel("Market Index Value")

    plt.grid(alpha=0.3)
    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "synthetic_prices.png",
        dpi=300
    )

    plt.close()


# VISUALISE RETURN DISTRIBUTIONS

def plot_return_distributions(df):

    plt.figure(figsize=(10, 5))

    normal_returns = df.loc[
        df["state"] == 0,
        "log_return"
    ]

    stressed_returns = df.loc[
        df["state"] == 1,
        "log_return"
    ]

    plt.hist(
        normal_returns,
        bins=40,
        alpha=0.6,
        density=True,
        label="Normal Market"
    )

    plt.hist(
        stressed_returns,
        bins=40,
        alpha=0.6,
        density=True,
        label="Stressed Market"
    )

    plt.title(
        "Daily Log Return Distributions by Market Regime"
    )

    plt.xlabel("Daily Log Return")
    plt.ylabel("Density")

    plt.legend()
    plt.grid(alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "return_distributions.png",
        dpi=300
    )

    plt.close()

# 12. VISUALISE MARKET REGIMES

def plot_market_regimes(df):

    plt.figure(figsize=(12, 4))

    plt.step(
        df["day"],
        df["state"],
        where="post"
    )

    plt.yticks(
        [0, 1],
        ["Normal", "Stressed"]
    )

    plt.title(
        "Simulated Market Regime Switching"
    )

    plt.xlabel("Trading Day")
    plt.ylabel("Market Regime")

    plt.grid(alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "market_regimes.png",
        dpi=300
    )

    plt.close()


# VISUALISE EXACT PATH PROBABILITIES

def plot_path_probabilities(df_paths):

    plt.figure(figsize=(10, 5))

    plt.bar(
        df_paths["path"],
        df_paths["path_probability"]
    )

    plt.title(
        f"Exact Probabilities of "
        f"{HORIZON}-Day Market Regime Paths"
    )

    plt.xlabel("Future State Path")
    plt.ylabel("Probability")

    plt.grid(
        axis="y",
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "path_probabilities.png",
        dpi=300
    )

    plt.close()


# EXPORT MODEL PARAMETERS AND REFERENCE RESULTS

def export_model_results(
    P_horizon,
    stressed_probability,
    loss_probability
):

    import json

    results = {
        "model": "Two-State Markov-Switching Model",

        "state_names": STATE_NAMES,

        "transition_matrix": P.tolist(),

        "mean_returns": MU.tolist(),

        "standard_deviations": SIGMA.tolist(),

        "initial_state": INITIAL_STATE,

        "prediction_horizon": HORIZON,

        "loss_threshold_log_return": LOSS_THRESHOLD,

        "horizon_transition_matrix":
            P_horizon.tolist(),

        "exact_stressed_probability":
            float(stressed_probability),

        "exact_loss_probability":
            float(loss_probability)
    }

    with open(
        OUTPUT_DIR / "model_parameters_and_reference.json",
        "w"
    ) as f:

        json.dump(
            results,
            f,
            indent=4
        )

    print("\nModel parameters exported successfully.")


# MAIN PROGRAM

def main():

    print("=" * 60)
    print("=" * 60)

    # Validate model
    validate_model()

    # Generate synthetic market data
    df = generate_synthetic_data()

    print("\nSynthetic Financial Data:")
    print(df.head(10))

    print("\nMarket Regime Counts:")
    print(df["state_name"].value_counts())

    # Calculate transition probabilities
    P_horizon = calculate_transition_probabilities()

    # Enumerate all future paths
    df_paths = calculate_exact_path_probabilities()

    # Calculate stressed market probability
    stressed_probability = (
        calculate_stressed_market_probability(
            P_horizon
        )
    )

    # Calculate exact financial loss probability
    loss_probability, df_loss = (
        calculate_exact_loss_probability(
            df_paths
        )
    )

    # Validate probabilities
    validate_reference_probabilities(
        df_paths,
        P_horizon
    )

    # Export results
    export_model_results(
        P_horizon,
        stressed_probability,
        loss_probability
    )

    # Generate visualisations
    plot_synthetic_prices(df)

    plot_return_distributions(df)

    plot_market_regimes(df)

    plot_path_probabilities(df_paths)

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    print(
        f"Model: Two-State Markov-Switching Model"
    )

    print(
        f"Prediction horizon: {HORIZON} days"
    )

    print(
        f"Probability of stressed market: "
        f"{stressed_probability:.6f}"
    )

    print(
        f"Probability of cumulative log loss <= -5%: "
        f"{loss_probability:.6f}"
    )

    print(
        f"\nAll results saved to: "
        f"{OUTPUT_DIR.resolve()}"
    )

    print("\nMember 1 implementation completed.")


if __name__ == "__main__":
    main()