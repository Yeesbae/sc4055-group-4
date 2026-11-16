# Quantum-Enhanced Financial Risk Estimation

### A VIX-Based Study Using Quantum Predictive Models and Amplitude Estimation

**SC4055 Introduction to Quantum Computing — Group 4**  
Nanyang Technological University (NTU), Singapore

## 1. Project Overview

This project investigates the application of quantum computing to financial risk estimation using the Cboe Volatility Index (VIX).

We study how quantum predictive models can represent stochastic financial processes and how Quantum Amplitude Estimation (QAE) can estimate event probabilities. Simulation-based experiments are used to compare quantum approaches with classical methods.

The project consists of four main components:

1. **Financial Modeling:** Constructing a stochastic model of VIX dynamics and calculating reference event probabilities.
2. **Quantum Predictive Model:** Implementing quantum circuits to represent the stochastic process and investigating predictive memory requirements.
3. **Quantum Amplitude Estimation:** Applying Maximum Likelihood Amplitude Estimation (MLAE) to estimate event probabilities.
4. **Classical Benchmarking:** Comparing quantum estimation methods with classical Monte Carlo using numerical experiments.

All experiments are simulator-based and do not require access to quantum hardware.

## 2. Financial Risk Model

Daily VIX observations are classified into three categories:

| State | VIX Level |
|---|---|
| 0 — Low | VIX < 20 |
| 1 — Moderate | 20 ≤ VIX < 30 |
| 2 — High | VIX ≥ 30 |

A second-order Markov model uses the two most recent observations to define nine possible history states.

The primary event of interest is:

**At least three high-volatility observations (VIX ≥ 30) among the next six trading days, conditional on the previous two observations.**

Exact probabilities from the fitted stochastic model provide reference values for evaluating the estimation algorithms.

This event measures sustained high implied volatility rather than realized portfolio losses.

## 3. Repository Structure

```text
sc4055-group-4/
|
|-- financial_modeling/
|   Classical stochastic model, exact
|   probability calculations and tests
|
|-- quantum-predictive-model/
|   Quantum predictive model implementation
|   and memory analysis
|
|-- quantum-amplitude-estimation/
|   Quantum state preparation, MLAE,
|   Grover operator and numerical experiments
|
|-- member_4_code.py
|   Classical benchmarking and
|   experimental analysis
|
|-- financial_modeling_research/
|   Supplementary financial model research,
|   historical validation and supporting results
|
|-- README.md
```

Individual modules contain their own source files, experimental materials and, where available, detailed documentation.

## 4. Requirements

The project uses Python and standard scientific computing libraries, including:

- NumPy
- SciPy
- Matplotlib
- Pandas
- Qiskit
- Qiskit Aer
- JAX (for parts of the quantum predictive model)

Dependencies vary between modules. Python 3.12 is a suitable starting environment, although individual components have their own version requirements.

Refer to the module-specific dependency files and documentation for detailed setup instructions.

## 5. Running the Experiments

The components can be explored separately.

### Financial Modeling

From the repository root:

```bash
cd financial_modeling
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/demo_financial.py
```

This runs the financial-model tests and a demonstration of exact event-probability calculations.

### Quantum Predictive Model

The main implementation is located in:

`quantum-predictive-model/sc4055_2.py`

It includes quantum circuit construction, stochastic process simulation, and predictive memory analysis.

This component uses Qiskit and additional scientific Python libraries. See the source code for the implemented calculations.

### Quantum Amplitude Estimation

The QAE implementation is located in:

`quantum-amplitude-estimation/`

Main files include:

- `qae.py` — Grover operator, event oracle, MLAE and experimental routines.
- `qae_demo.ipynb` — Jupyter notebook demonstrating validation and estimation experiments.
- `member2/sc4055_2.py` — Quantum predictive circuit used by the QAE implementation.
- `model/nine_state_model_specification.json` — Financial model parameters and exact reference probabilities.

The notebook and QAE scripts should be run with the working directory set to `quantum-amplitude-estimation/` so their relative file paths resolve correctly.

For detailed experiment settings and reproduction instructions, see:

[QAE Documentation](quantum-amplitude-estimation/README.md)

### Classical Benchmarking

The independent benchmarking implementation is:

`member_4_code.py`

It compares MLAE with classical Monte Carlo across selected initial VIX states using matched query budgets.

The experiments examine estimation error, root-mean-square error (RMSE), and scaling with computational queries.

### Supplementary Financial Research

Additional model development and validation materials are available in `financial_modeling_research/`, including historical comparisons, uncertainty analyses, and reproducibility documentation.

## 6. Results and Limitations

The simulations investigate the potential advantages of quantum probability estimation and the memory requirements of quantum representations of stochastic processes.

The main comparisons consider:

- Exact model probabilities and estimated probabilities.
- Quantum versus classical estimation error.
- RMSE as a function of query budget.
- Predictive memory and quantum circuit resource requirements.

The results are conditional on the chosen stochastic model and simulation assumptions. They do not demonstrate a practical quantum advantage on current hardware or establish superior real-world financial forecasting performance.

## 7. Project Deliverables

The SC4055 group project submission consists of:

- **Project Report:** Quantum-Enhanced Financial Risk Estimation — A VIX-Based Study Using Quantum Predictive Models and Amplitude Estimation.
- **Recorded Presentation:** Group presentation explaining the methods, implementation, results and limitations.
- **Source Code:** This GitHub repository, containing the implementations and supporting experiments.

## 8. Contributors

**SC4055 — Group 4**

Nanyang Technological University, Singapore

This project was completed collaboratively by four group members, with contributions to financial modeling, quantum predictive modeling, quantum amplitude estimation, and classical benchmarking.
