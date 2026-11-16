# V3.0 next-phase implementation contract

Status: CONDITIONAL GO for a nine-state research demonstrator; no claim of established financial superiority or exact dimension compression in the phase-enhanced pure-state architecture.

## Frozen inputs

- Observation: Cboe VIX daily CLOSE; categories 0 (<20), 1 (20 to <30), 2 (>=30). State ab stores the last two observations, oldest first, integer 3a+b. Lambda(ab,x)=bx.
- Model: `model/nine_state_model_specification.json`, version V3.0-Phase3-1.0. Use its rational emissions or full-precision arrays. Do not refit or change priors, thresholds or zero-count rows silently.
- Data cutoff: 2026-10-23; 9,301 observations. All historical evidence is retrospective. Raw and canonical hashes are in `data/manifests/`.
- Event: at least three future symbols equal to 2 among six future trading observations. The current symbol is conditioning information and is not counted.
- All nine initial states have independently evaluated exact rational reference probabilities. Primary production histories may start with 00,11,12,21,22 for runtime control; 02 and 20 must remain visible as prior-dominated sensitivity conditions. Circuit correctness must be checked from all nine.

## Quantum representation and interfaces

- Four memory qubits, six two-qubit output registers, three clean count-work qubits and one flag: 20 qubits total. Logical register positions: memory [0,1,2,3], output t [4+2t,5+2t], t=0,...,5; counter [16,17,18]; flag 19.
- Numerical basis index: memory +16*sum_t x_(t+1)*4^t +2^16*counter +2^19*flag. Output code 2 is binary 10, with high bit 1 and low bit 0. Code 3 is invalid stochastic support.
- `model/coherent_step_arrays.npz` contains the tested 64x64 unitary, 64x16 input isometry and padded 16x9 memory-state matrix. Supported memory indices 0,...,8 contain the nine-dimensional span; padding indices 9,...,15 have a defined isometric extension.
- `model/recurrent_step_pilot.qpy` contains both compiled candidate step circuits; the 64x16 isometry synthesis is the lower-CX pilot. Check the label and the resource JSON rather than assume a file-list index in new software.
- `condition(observed_history)` returns the last two categories; reject an insufficient history unless a separately defined mixed-state initializer and purification are supplied.
- `build_initializer(state)` returns a reversible StatePreparation gate on four memory qubits. Do not use reset-based initialize inside A.
- `build_B(state,L=6)` repeats the same valid step with fresh output registers. Retain final memory, outputs and any coherent environment; do not measure, reset, discard, or substitute a whole-path amplitude loader.
- `build_Cf(outputs,counter,flag)` increments the count only for code 2, XORs flag by count>=3, and uncomputes all count workspace. Define its action on all encoded words, including code 3. A clean implementation can use 12 C4X, 13 C3X, 13 CCX, 1 CX and 24 X in the declared component design.
- `build_A=Cf*B` and `build_A_inverse` must be exact inverses of the actual gate sequence, with all registers retained. Do not substitute a simulator restart.
- `build_Q=-A*S0*A_dagger*S_flag` uses the full 20-register all-zero reflection. Check the joint-state amplification identity, including final memory and flag.

## Validation gates

1. Transition rows normalized, finite and nonnegative; state indices and matrices agree with the frozen specification, residual <=1e-12.
2. Kraus completeness and recurrence, isometry and unitary residuals <=1e-10; compiled supported-input isometry error <=1e-9. Current pilot is substantially below these tolerances.
3. All length-2,4,6 word probabilities from all nine starts agree with independent exact references; max error <=1e-9 and total variation <=1e-8. Invalid output-code and padded-memory leakage <=1e-10. The present pilot covers only lengths 1 and 2; lengths 4 and 6 remain next-phase gates.
4. Initializer plus preparation inverse returns the complete register to zero with vector error <=1e-9, allowing only a common global phase.
5. Test Cf for all 4^6 encoded output words, flag inputs 0/1 and clean count workspace; preserve outputs and memory. Test comparator on count inputs 0,...,7 separately. Workspace must return to zero.
6. Test Q^k A at k=0,1,2,4 against sin^2((2k+1)*asin(sqrt(p_s))) with probability error <=1e-8. Reference probabilities enter validation/scoring only, never the estimator's likelihood fitting or mode selection.
7. Only after these gates run a 20-replicate resource/estimation pilot, initial powers [0,1,2,4], 200 shots per stage and seeded independent measurement-count draws.

## Runtime and resource decision

The source pilot measured 1,096 CX per synthesized recurrent step and estimated 7,280 CX for six-step A from compiled components. Full A/Grover counts are estimates until compiled. A cached ideal-distribution strategy can reduce repeated statevector work, but every logical shot and A/A-dagger call remains charged.

Proposed course engineering limits, not measured achievements: peak process memory <=8 GiB; <=900 seconds for the largest k=4 unique circuit; <=3 hours for all 20 unique state/power circuits over five histories; no production replication before an actual full-circuit timing pass. These are adjustable project constraints only through a documented configuration revision.

Use simulator gate fusion or a validated tensor-network strategy before reducing model scope. If the exact nine-state gate is still too expensive, prefer the separately versioned three-level first-order fallback (18 qubits), preserving the observation and event. Binary order 2 is a smaller 12-qubit engineering control. Never change L or the event silently to make an unfavorable result disappear.

For each trial export powers, shots, successes, independent seeds, estimator status, all likelihood modes and query ledger B=sum_j n_j(2k_j+1), plus compiled width, depth, CX, A/A-dagger calls, oracle/reflection cost and compilation/simulation/fitting times. Cache only ideal distributions from verified circuits and describe amortization explicitly. Compare 100/200-replicate results only after runtime passes; do not delete aliases or unsuccessful trials.

## Claims and comparator boundaries

- Exact DP remains a strong baseline, O(L*D*m*K) for this count event. Quantum sampling-query comparisons do not establish a practical speedup over DP or faster classical-simulator runtime.
- Report financial prediction error, parameter uncertainty, model approximation, state-preparation numerical error and amplitude-estimation error separately. Do not treat a precise QAE estimate of a misspecified model as precise market knowledge.
- The exact all-phase certificate rules out dimensions <=8 (and therefore <=4) in the nine-pure-state, one-Kraus-per-symbol unifilar recurrence with the frozen probabilities. Do not spend the next phase optimizing these impossible exact targets. General mixed/multiple-Kraus instruments are outside the theorem; any extra purification/environment registers must be counted and retained for a coherent inverse.
- Stationary entropy decreases from about 1.632645 bits to 1.084622 bits in the zero-phase construction. This does not reduce four physical memory qubits.

## Optional approximate-memory research, after the exact pipeline

Possible variables: D-dimensional complex Kraus matrices K_0,K_1,K_2, a constrained isometric stack (Stiefel parametrization), and a consistent history-conditioning/filtering encoder. Enforce sum K_x^dagger K_x=I exactly or within a stated certified numerical error. Do not independently project nine exact memory states and assume recurrence survives.

Train on past/training sequences, evaluate held-out whole-word log loss, word TV at lengths 2,4,6, primary and secondary event errors, empirically weighted errors and worst supported history. Separate rare-history posterior uncertainty from compression distortion. Choose application tolerances before optimization, and do not tune solely to the one primary event.

Compare against classical order reduction, valid variable-context models, explicitly weighted causal-state clustering and trained finite hidden generators at the same D=8/4 memory constraint. A clustering-only search is not optimal over all classical generators. The stationary discarded weights (rank 8 about 2.87e-6; rank 4 about 5.69e-4) motivate an investigation but provide neither a recurrent instrument nor uniform conditional-event guarantees. No approximate instrument has been trained in Phase 3.
