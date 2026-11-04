# Ramsey search experiment

Generated 2026-11-04T09:45:55.914503+00:00; 5 trials per instance.

These are measurements on small instances, not a test of asymptotic exponents. Capped runs are reported separately; successful-only medians can be biased when runs are censored.

`naive` scans k-sets; `branching` tests monochromatic prefixes with scalar edges; `hs_bitset` uses common-neighbour bitsets and cardinality pruning. The last two implement the same structured search analysed by Harris–Srinivasan. Bitsets are an engineering optimization, not a distinct third theoretical algorithm.

All methods choose the lexicographically first bad clique and consume identical random draws for initialization and each repair. Their successful paired trajectories and final colourings are checked for equality. All completed outputs are checked by a separate Python verifier; verification and subprocess startup are excluded from solver timings.

## Full Moser–Tardos runs

| n | k | LLL certified | Method | Completed | Timeout / repair cap | Median total (s) | Median search (s) | Median repairs |
|---:|---:|:---:|---|---:|---:|---:|---:|---:|
| 4 | 4 | yes | branching | 5/5 | 0 / 0 | 2.51e-06 | 2.2e-07 | 0 |
| 4 | 4 | yes | hs_bitset | 5/5 | 0 / 0 | 3.53e-06 | 1.3e-06 | 0 |
| 4 | 4 | yes | naive | 5/5 | 0 / 0 | 2.54e-06 | 3.3e-07 | 0 |
| 5 | 3 | no | branching | 5/5 | 0 / 0 | 1.33e-05 | 6.88e-06 | 27 |
| 5 | 3 | no | hs_bitset | 5/5 | 0 / 0 | 1.02e-05 | 5.25e-06 | 27 |
| 5 | 3 | no | naive | 5/5 | 0 / 0 | 9.19e-06 | 3.98e-06 | 27 |
| 7 | 5 | yes | branching | 5/5 | 0 / 0 | 3.58e-06 | 6.11e-07 | 0 |
| 7 | 5 | yes | hs_bitset | 5/5 | 0 / 0 | 4.36e-06 | 1.46e-06 | 0 |
| 7 | 5 | yes | naive | 5/5 | 0 / 0 | 3.68e-06 | 7.41e-07 | 0 |
| 12 | 4 | no | branching | 5/5 | 0 / 0 | 0.0017 | 0.00148 | 1.48e+03 |
| 12 | 4 | no | hs_bitset | 5/5 | 0 / 0 | 0.000807 | 0.000621 | 1.48e+03 |
| 12 | 4 | no | naive | 5/5 | 0 / 0 | 0.00187 | 0.00169 | 1.48e+03 |
| 13 | 6 | yes | branching | 5/5 | 0 / 0 | 8.48e-06 | 4.95e-06 | 0 |
| 13 | 6 | yes | hs_bitset | 5/5 | 0 / 0 | 5.99e-06 | 2.61e-06 | 0 |
| 13 | 6 | yes | naive | 5/5 | 0 / 0 | 1.69e-05 | 1.33e-05 | 0 |
| 20 | 5 | no | branching | 5/5 | 0 / 0 | 0.000576 | 0.000551 | 129 |
| 20 | 5 | no | hs_bitset | 5/5 | 0 / 0 | 0.000137 | 0.000114 | 129 |
| 20 | 5 | no | naive | 5/5 | 0 / 0 | 0.00424 | 0.00421 | 129 |
| 22 | 7 | yes | branching | 5/5 | 0 / 0 | 3.47e-05 | 2.97e-05 | 0 |
| 22 | 7 | yes | hs_bitset | 5/5 | 0 / 0 | 9.81e-06 | 5.46e-06 | 0 |
| 22 | 7 | yes | naive | 5/5 | 0 / 0 | 0.0012 | 0.00119 | 0 |
| 28 | 6 | no | branching | 5/5 | 0 / 0 | 0.000422 | 0.000411 | 14 |
| 28 | 6 | no | hs_bitset | 5/5 | 0 / 0 | 7e-05 | 3.1e-05 | 14 |
| 28 | 6 | no | naive | 5/5 | 0 / 0 | 0.0074 | 0.00739 | 14 |
| 36 | 8 | yes | branching | 5/5 | 0 / 0 | 0.000209 | 0.000201 | 0 |
| 36 | 8 | yes | hs_bitset | 5/5 | 0 / 0 | 2.33e-05 | 1.62e-05 | 0 |
| 36 | 8 | yes | naive | 5/5 | 0 / 0 | 0.158 | 0.158 | 0 |

## Paired full-run speedups

Median of per-seed runtime ratios, using only seeds on which all three methods completed. The counts expose exclusions rather than treating timeouts as completed runs.

| n | k | Complete triplets | Naive / branching | Naive / hs_bitset |
|---:|---:|---:|---:|---:|
| 4 | 4 | 5 | 1.02 | 0.718 |
| 5 | 3 | 5 | 0.884 | 0.861 |
| 7 | 5 | 5 | 1.04 | 0.831 |
| 12 | 4 | 5 | 1.52 | 2.47 |
| 13 | 6 | 5 | 2 | 2.82 |
| 20 | 5 | 5 | 5.34 | 16.9 |
| 22 | 7 | 5 | 27.6 | 126 |
| 28 | 6 | 5 | 29.4 | 183 |
| 36 | 8 | 5 | 804 | 6.86e+03 |

## Searches on identical snapshots

Initial configurations and every available successful final configuration are replayed without resampling. Final snapshots measure the complete absence search, which cannot benefit from stopping at the first violation.

| Snapshot | n | k | Method | Completed | Median search (s) | Median candidates |
|---|---:|---:|---|---:|---:|---:|
| final | 4 | 4 | branching | 5/5 | 2.1e-07 | 2 |
| final | 4 | 4 | hs_bitset | 5/5 | 1.3e-06 | 1 |
| final | 4 | 4 | naive | 5/5 | 3e-07 | 1 |
| final | 5 | 3 | branching | 5/5 | 4.81e-07 | 16 |
| final | 5 | 3 | hs_bitset | 5/5 | 1.46e-06 | 6 |
| final | 5 | 3 | naive | 5/5 | 4.81e-07 | 10 |
| final | 7 | 5 | branching | 5/5 | 6.11e-07 | 18 |
| final | 7 | 5 | hs_bitset | 5/5 | 1.6e-06 | 6 |
| final | 7 | 5 | naive | 5/5 | 6.91e-07 | 21 |
| final | 12 | 4 | branching | 5/5 | 4.42e-06 | 305 |
| final | 12 | 4 | hs_bitset | 5/5 | 3.1e-06 | 59 |
| final | 12 | 4 | naive | 5/5 | 5.24e-06 | 495 |
| final | 13 | 6 | branching | 5/5 | 4.1e-06 | 269 |
| final | 13 | 6 | hs_bitset | 5/5 | 2.42e-06 | 39 |
| final | 13 | 6 | naive | 5/5 | 1.16e-05 | 1.72e+03 |
| final | 20 | 5 | branching | 5/5 | 2.24e-05 | 2.1e+03 |
| final | 20 | 5 | hs_bitset | 5/5 | 6.25e-06 | 206 |
| final | 20 | 5 | naive | 5/5 | 8.5e-05 | 1.55e+04 |
| final | 22 | 7 | branching | 5/5 | 2.63e-05 | 2.34e+03 |
| final | 22 | 7 | hs_bitset | 5/5 | 4.99e-06 | 162 |
| final | 22 | 7 | naive | 5/5 | 0.001 | 1.71e+05 |
| final | 28 | 6 | branching | 5/5 | 7.57e-05 | 8.19e+03 |
| final | 28 | 6 | hs_bitset | 5/5 | 1.14e-05 | 467 |
| final | 28 | 6 | naive | 5/5 | 0.002 | 3.77e+05 |
| final | 36 | 8 | branching | 5/5 | 0.000221 | 2.33e+04 |
| final | 36 | 8 | hs_bitset | 5/5 | 1.62e-05 | 711 |
| final | 36 | 8 | naive | 5/5 | 0.171 | 3.03e+07 |
| initial | 4 | 4 | branching | 5/5 | 2.21e-07 | 2 |
| initial | 4 | 4 | hs_bitset | 5/5 | 1.43e-06 | 1 |
| initial | 4 | 4 | naive | 5/5 | 3.2e-07 | 1 |
| initial | 5 | 3 | branching | 5/5 | 5.3e-07 | 7 |
| initial | 5 | 3 | hs_bitset | 5/5 | 1.58e-06 | 3 |
| initial | 5 | 3 | naive | 5/5 | 4.61e-07 | 5 |
| initial | 7 | 5 | branching | 5/5 | 6.11e-07 | 18 |
| initial | 7 | 5 | hs_bitset | 5/5 | 1.51e-06 | 6 |
| initial | 7 | 5 | naive | 5/5 | 7.01e-07 | 21 |
| initial | 12 | 4 | branching | 5/5 | 6.21e-07 | 23 |
| initial | 12 | 4 | hs_bitset | 5/5 | 1.54e-06 | 5 |
| initial | 12 | 4 | naive | 5/5 | 8.81e-07 | 44 |
| initial | 13 | 6 | branching | 5/5 | 4.06e-06 | 269 |
| initial | 13 | 6 | hs_bitset | 5/5 | 2.45e-06 | 39 |
| initial | 13 | 6 | naive | 5/5 | 1.17e-05 | 1.72e+03 |
| initial | 20 | 5 | branching | 5/5 | 7.51e-07 | 38 |
| initial | 20 | 5 | hs_bitset | 5/5 | 1.72e-06 | 5 |
| initial | 20 | 5 | naive | 5/5 | 4.29e-06 | 794 |
| initial | 22 | 7 | branching | 5/5 | 2.56e-05 | 2.34e+03 |
| initial | 22 | 7 | hs_bitset | 5/5 | 5.07e-06 | 162 |
| initial | 22 | 7 | naive | 5/5 | 0.000774 | 1.71e+05 |
| initial | 28 | 6 | branching | 5/5 | 4.4e-06 | 609 |
| initial | 28 | 6 | hs_bitset | 5/5 | 2.14e-06 | 20 |
| initial | 28 | 6 | naive | 5/5 | 0.000216 | 3.38e+04 |
| initial | 36 | 8 | branching | 5/5 | 0.000201 | 2.33e+04 |
| initial | 36 | 8 | hs_bitset | 5/5 | 1.66e-05 | 711 |
| initial | 36 | 8 | naive | 5/5 | 0.15 | 3.03e+07 |

## Interpretation and reproducibility

The sufficient condition is `e * 2^(1-C(k,2)) * C(k,2) * C(n-2,k-2) <= 1`. Uncertified instances are heuristic stress tests: their termination is not guaranteed by this condition. Each successful colouring individually certifies R(k,k) > n.

Candidate counts mean complete k-sets for naive search, attempted prefix extensions (including seed edges) for scalar branching, and bitset-selected extensions (including seed edges) for hs_bitset. They are not equal-cost units. Bitset intersections and scalar edge checks are recorded separately. All methods maintain the same graph representations.

Counters are instrumented; very short runs are sensitive to timer resolution and machine load. No speedup should be inferred from sub-millisecond timings alone. See raw.json for timings, seeds, certificates, counters, source hashes, compiler and platform; summary.csv also includes means and sample standard deviations.

Reference: Harris and Srinivasan, *Algorithmic and enumerative aspects of the Moser–Tardos distribution*, arXiv:1507.02674v4, Section 3.2, Propositions 3.2–3.4. The experiments do not estimate the unknown Ramsey numbers or reproduce large-k scaling.
