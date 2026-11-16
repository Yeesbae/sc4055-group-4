# Mathematical verification of the frozen nine-state process

All exact statements below concern the specified fitted process, not the true financial market. The determinant argument is derived for this package; no publication-novelty claim is made.

## State convention and exact transitions

States are ab in {00,01,02,10,11,12,20,21,22}, integer 3a+b. The output-labelled transition is

\[
T^{(x)}_{ab,j}=p(x\mid ab)\,\mathbf1\{j=3b+x\},\qquad
p(x\mid ab)=\frac{n_{ab,x}+1/2}{n_{ab}+3/2}.
\]

Every emission is positive and sums to one. Any two-symbol word reaches its own context from every starting state, establishing reachability. Self loops and positive word paths establish an irreducible aperiodic history chain with a unique stationary distribution. Exact rational emission signatures already distinguish all nine states, so none can have the same complete future law. An exact partition-refinement implementation also returns nine classes.

The continuation-probability matrix F[s,xy]=p(x|s)p(y|lambda(s,x)) has a nonzero exact rational determinant. Independent rational Gaussian elimination and a modular determinant agree that its rank is nine. Synchronization makes it an invertible row-scaled stationary Hankel submatrix. Hence every finite homogeneous classical hidden generator needs at least nine states; a general fixed quantum instrument needs D^2>=9, or D>=3.

## A stronger all-phase pure-memory obstruction

Assume normalized pure memory states and one Kraus operator for each output:

\[
K_x|\sigma_{ab}\rangle
=r_{ab,x}|\sigma_{bx}\rangle,\qquad
r_{ab,x}=\sqrt{p(x\mid ab)}e^{i\phi_{ab,x}}.
\]

After two common outputs x,y the final memory is the same normalized state sigma_xy for all initial histories. Thus the Gram matrix is exactly the Gram of the two-step future amplitudes. Let C have rows (x,y), columns (a,b), with C[(x,y),(a,b)]=r_ab,x r_bx,y. Then G=C^dagger C and rank(G)=rank(C), for every transition phase choice.

For each current category b define the 3x3 block

\[
(R_b)_{a,x}=r_{ab,x}.
\]

Let B=C^T, with rows reordered from (a,b) to (b,a). A perfect-shuffle permutation P maps (b,x) to (x,b), giving

\[
B=\operatorname{diag}(R_0,R_1,R_2)\,P\,
\operatorname{diag}(R_0,R_1,R_2).
\]

Consequently

\[
|\det C|=\prod_{b=0}^{2}|\det R_b|^2.
\]

For a 3x3 determinant, each of its six monomial magnitudes is

\[
a_{b,\pi}=\sqrt{\prod_a p(\pi(a)\mid ab)}.
\]

If one monomial has magnitude strictly greater than the sum of all five others, the reverse triangle inequality gives a positive determinant lower bound independent of every phase and determinant sign. In this frozen model, the diagonal monomial dominates in all three blocks. Exact rational square-root enclosures certify margins greater than approximately 0.1659453779, 0.0457869638 and 0.0278990744. Their square product gives |det C|>4.49359e-8. Therefore G is full rank nine for every transition phase.

The bounds use integer-verified rational intervals of width 10^-40: for q=n/d and scale=10^40, L=floor(sqrt(n*scale^2/d)), so L/scale <=sqrt(q)<(L+1)/scale. No floating eigenvalue cutoff or failed optimizer is used as proof.

**Conclusion:** exact D_q<=8, hence also D_q<=4, is impossible in this fixed pure-state, one-Kraus-per-symbol unifilar phase class. Dimension nine is achievable by the validated zero-phase construction, so its optimal exact dimension within this class is nine.

The statement does not exclude different mixed-state histories, multiple Kraus operators per symbol or more general quantum generators. Their general lower bound here remains D>=3. A coherent implementation must charge any purification, environment or controller memory rather than discard it to claim savings.

## Zero-phase instrument

With zero phases C contains square-root two-step word probabilities, so G=C^dagger C is positive semidefinite and unit diagonal. Its finite-horizon synchronization also proves the recurrent Gram equation. A full-rank factor S^dagger S=G and targets Y_x[:,i]=sqrt(p(x|i))*S[:,lambda(i,x)] define K_x=Y_x S^-1. Equality of the input/output Grams proves sum K_x^dagger K_x=I and exact recurrence. Ninety-digit construction followed by floating-point checks is supplied; exact validity follows from the equations, while finite-precision matrix residuals are numerical evidence.

The padded 64x16 isometry maps four memory qubits and a fresh two-qubit output register. Supported memory states span nine dimensions; padding has a specified extension. An orthonormal completion yields a 64x64 unitary, independently checked and compiled in the pilot. This is local recurrent synthesis, not exponential whole-future amplitude loading.

## Event truth and robust sparse-row bounds

Exact Fraction path enumeration and an independent dynamic program agree for count, hit and run events. First-entry probabilities use the hit event only when the current category is not high. A >=35 event cannot be identified from category 2, which lumps all VIX>=30; it requires a new observation specification.

For sparse contexts 02 and 20, the robust envelope lets each uncertain transition choose any distribution at every visit. Backward min/max propagation on the state/count automaton therefore bounds every fixed replacement of these rows, even though the envelope also includes more general time-dependent choices. These are conservative model-sensitivity bounds, not posterior intervals or claims that fixed-row extrema occur at simplex vertices.
