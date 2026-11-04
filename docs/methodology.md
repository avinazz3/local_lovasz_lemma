# Experimental protocol

## Research questions

1. How much time does locating a true bad event take relative to repairing it?
2. How do complete `k`-set enumeration, scalar prefix branching, and bitset prefix branching compare on the same MT trajectory?
3. How does the search cost differ between the initial random colouring and a valid terminal colouring, where the search must certify absence?

## Model and algorithms

Each edge of `K_n` is an independent fair bit. A bad event is a monochromatic `k`-vertex set. A repair redraws all `C(k,2)` edges of the selected set, leaving other edges unchanged. A single `std::mt19937_64` stream per trial supplies initialization and repairs; its low bit is used directly, avoiding library-specific distribution mappings. Vertices and repaired edges are always visited in increasing order.

Every search is complete and returns the lexicographically first monochromatic `k`-set. Enumeration visits complete vertex subsets. Scalar branching starts with an edge, fixes its colour, and tests whether later vertices extend the prefix. Bitset branching intersects same-colour neighbour sets to represent the valid extensions of the entire prefix; it also stops when too few candidates remain. Numeric bounds prevent scalar search from growing a prefix that cannot reach size `k`. No method materializes all `C(n,k)` bad events in advance.

The first method is the report's naive baseline. The second implements the search of Harris–Srinivasan Proposition 3.3 directly. The third uses word-level intersections and cardinality pruning to optimize that search. Harris–Srinivasan's Theorem 3.1 justifies expected search cost over adaptive MT configurations; it is not a different repair algorithm. In particular, the three-way timing experiment must not be presented as proving three different theoretical complexity bounds.

All methods maintain an identical adjacency matrix and two colour-specific neighbour masks. Repair costs include updates to both representations, even for the scalar methods. This isolates the search implementation rather than comparing incompatible graph-maintenance policies.

## Instance selection and stopping rules

`--preset report` includes five cases satisfying the sufficient condition `epD <= 1`, with `p=2^(1-C(k,2))` and `D=C(k,2)C(n-2,k-2)`, plus four heuristic stress cases. Every raw row includes the natural logarithm of `epD`. The expected-repair bound `C(n,k)ep` is recorded only where the condition holds. Certified cases can have no bad event initially: zero repairs are real observations, and their final search still matters.

Each invocation has its own wall-clock deadline and maximum number of repairs. If the repair cap is reached, one more search may certify that the last repair solved the instance; otherwise the status is `resampling_limit`. Deadline checks occur at search entry and every 4096 search operations. The deadline includes graph initialization. Timings can slightly exceed a cooperative deadline; a larger Python subprocess deadline treats a nonresponsive solver as an error rather than inventing a measurement.

The impossible case `(n,k)=(6,3)` is tested with a repair cap in the automated suite. It is not included in the default timing dataset. Failure to finish any other case is not evidence that its colouring does not exist.

## Pairing, validation and counters

Within a trial the three methods have the same `(n,k,seed)`. Method order is shuffled deterministically with a separate Python RNG to reduce fixed-order timing effects. The benchmark checks identical initial graphs. For every pair of successful full runs, it checks exact equality of repair count, the FNV-1a hash of the selected-clique sequence, and final edge bits. Full certificates are retained; a hash alone is not used to verify a colouring.

A separate Python implementation checks each completed output for a monochromatic `K_k`. Automated tests compare that verifier and every C++ search with an exhaustive Python oracle on all `K_4` colourings and random small graphs. The terminal graph itself is a reproducible certificate for `R(k,k)>n`; verification time is recorded separately and excluded from solver runtimes.

Counters are cumulative per invocation:

| Counter | Meaning |
|---|---|
| `search_calls` | Includes the initial and terminal search; for completed full runs, repairs plus one. |
| `candidates_tested` | Complete `k`-sets for naive; attempted scalar extensions/seed edges for branching; bitset-selected extensions/seed edges for hs_bitset. |
| `edge_checks` | Individual scalar edge reads made by the search. |
| `prefixes` | Visited monochromatic prefixes, including seed edges and completed cliques. |
| `bitset_intersections` | Logical candidate-set intersection operations (the seed operation also masks vertex order). |
| `resamplings` | Complete local repairs. |

Candidate units differ; compare timings alongside the counters. Clock polling uses one common operation budget object, but the number of calls depends on the traversal. Measurements include instrumentation overhead.

## Analysis and reporting

Report completion fractions and both time/repair caps. Summary statistics for runtime and work counters use completed rows, with mean, median, and sample standard deviation retained in CSV. The speedup table uses the median of per-seed naive/variant ratios on complete triplets. It does not divide unrelated means or assign capped runs their budget as a fake runtime. If triplets are excluded, the speedup describes the completed subset and may be optimistic.

Replay the initial graph and an available successful final graph with each search, without repairs. This separates search behaviour from the amount of resampling and exposes the cost of a complete absence certificate. There is no final replay for a trial in which no method succeeds.

Keep raw JSON and build metadata with results. Repeat on the same machine with more seeds and larger budgets before drawing practical conclusions. Timings below a millisecond are dominated easily by measurement noise; they should not support strong performance claims. Small `n,k` experiments do not estimate asymptotic exponents or the Ramsey threshold. Add implementation-specific comparisons and these limitations to Section 5 when incorporating the results into the report.

## Larger study and uncertainty

The expanded study adds `(16,5)`, `(24,6)`, and `(32,7)` and measures 100 seeds per case. The new seed range is excluded from the pilot; common seeds are reused across cases but no cross-case pooling is performed. Each instance therefore has 100 seed-based observations, not 300 independent method observations or 900 independent construction/snapshot observations. All 1,200 triplets are shuffled before execution; methods are also shuffled within a triplet. Excluded warm-ups run once per case/method. CPU affinity is recorded when available.

Means describe average cost; medians resist a few unusually long runs; sample SD and IQR describe spread. Quartiles use linear interpolation at `(sample_size-1)*p`. For discrete repairs, retain every tied repeated mode and its observed frequency. With no repeated values, report no repeated mode. A mode seen twice in 100 samples is not a reliable typical value. Exact timing modes are preserved in machine-readable output but not interpreted because time is approximately continuous and clocks quantize measurements.

The custom standard-library percentile bootstrap takes 2,000 samples with replacement, each the same size as the observed sample. The 2.5th and 97.5th percentiles give approximate pointwise intervals for mean runtimes and median paired speedups. Speedup intervals resample per-seed ratios, preserving the pairing; they are not ratios of separate confidence endpoints. Wilson intervals describe completion proportions. Intervals do not cover variability across hardware, do not correct all comparisons simultaneously, and do not turn an empirical observation into an asymptotic guarantee.

For the pruning ablation, compile exactly the same source with `RAMSEY_NO_CARDINALITY_PRUNING`. Only the two candidate-count tests are omitted. Replay the same 100 final `(28,6)` and `(36,8)` graphs, verify absence independently, and compare visited-prefix counts with the original bitset search. This distinguishes less search work from faster word operations without assigning a causal timing percentage to either effect.

The saved-data verifier checks exact graph pairing for every initial/final replay and ablation, in addition to checking each certificate. Duplicate, missing, or mismatched snapshots are rejected. The expanded raw JSON is gzip-compressed to avoid repeating large graph strings uncompressed in Git.
