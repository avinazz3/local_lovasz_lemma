# Ramsey theory checks

Reference commit `8a7f58f20c0b497e8791b0ab99a139476f3f11cf`. Each instance uses the 100 archived seeds 20270000–20270099.

Reproduce the measurements with `python3 scripts/theory_check.py` from the repository root.

## Initial

Every row uses all 100 initial colourings. `SE` is the sample standard deviation divided by √100. `Model SE` uses the exact variance of the count under independent fair edge colours.

| Instance | Mean initial count | m·p | Median | Zero fraction | SE | Model SE |
|---|---:|---:|---:|---:|---:|---:|
| (4,4) | 0.0500 | 0.03125 | 0 | 0.95 | 0.0219043 | 0.0173993 |
| (7,5) | 0.0500 | 0.0410156 | 0 | 0.96 | 0.0261116 | 0.0261099 |
| (13,6) | 0.0300 | 0.104736 | 0 | 0.97 | 0.0171447 | 0.0563716 |
| (22,7) | 0.190 | 0.162643 | 0 | 0.88 | 0.0580752 | 0.0838474 |
| (36,8) | 0.210 | 0.225457 | 0 | 0.90 | 0.0782317 | 0.108218 |
| (5,3) | 2.55 | 2.5 | 2 | 0.00 | 0.137345 | 0.136931 |
| (12,4) | 14.1 | 15.4688 | 12 | 0.00 | 0.697524 | 0.783528 |
| (16,5) | 7.66 | 8.53125 | 6 | 0.03 | 0.718896 | 0.802606 |
| (20,5) | 26.9 | 30.2812 | 22 | 0.00 | 1.6718 | 1.88157 |
| (24,6) | 7.69 | 8.21509 | 5 | 0.05 | 0.950778 | 0.980347 |
| (28,6) | 21.5 | 22.9944 | 19 | 0.00 | 1.49115 | 1.99523 |
| (32,7) | 2.93 | 3.20993 | 1 | 0.31 | 0.449973 | 0.579197 |

The variance accounts for overlapping sets. For two k-sets sharing s ≥ 2 vertices, their joint monochromatic probability is p² × 2^(C(s,2)−1). With zero or one shared vertex, the events are independent. The variance sums the covariances over ordered pairs, including the diagonal s = k.

The following sample means exceed two standard errors under at least one of the two scales. Every flagged count was checked by the naive scan, and the seeded replay matched the archived graph bit for bit.

| Instance | Observed minus m·p | Difference / sample SE | Difference / model SE |
|---|---:|---:|---:|
| (13,6) | -0.0747363 | -4.359 | -1.326 |
| (12,4) | -1.41875 | -2.034 | -1.811 |
| (20,5) | -3.39125 | -2.028 | -1.802 |

Rare counts give discrete, skewed samples and can yield a small sample SE. The model variance allows several overlapping monochromatic sets on a single graph.

For (13,6), 97 graphs have count zero. The total count over the 100 graphs is 3.

All 12 observed means are within two model SEs of m·p.

## Visited

Without/with refers to the two candidate-count tests. Ratios are calculated per seed before taking their mean or median.

| Instance | Median without | Median with | Median ratio | Mean without | Mean with | Mean ratio |
|---|---:|---:|---:|---:|---:|---:|
| (13,6) | 113 | 39 | 2.89189 | 115.79 | 39.91 | 2.896 |
| (22,7) | 727 | 165 | 4.38045 | 737.01 | 167.46 | 4.40222 |
| (36,8) | 4,727.5 | 727.5 | 6.48411 | 4,750.94 | 732.42 | 6.4926 |
| (12,4) | 85.5 | 56 | 1.51317 | 85.67 | 56.66 | 1.51378 |
| (16,5) | 224.5 | 101 | 2.22569 | 226.25 | 101.76 | 2.22659 |
| (20,5) | 461.5 | 208 | 2.21849 | 462.94 | 209.29 | 2.2147 |
| (24,6) | 942.5 | 289 | 3.26259 | 946.81 | 290.23 | 3.26821 |
| (28,6) | 1,594 | 487 | 3.2666 | 1,596.21 | 490.64 | 3.25712 |
| (32,7) | 2,853.5 | 616 | 4.66455 | 2,883.69 | 618.95 | 4.66507 |

### What the counter includes

The `prefixes` counter increments on entry to the recursion ([scalar line 90](https://github.com/avinazz3/local_lovasz_lemma/blob/8a7f58f20c0b497e8791b0ab99a139476f3f11cf/src/ramsey.cpp#L90), [bitset line 113](https://github.com/avinazz3/local_lovasz_lemma/blob/8a7f58f20c0b497e8791b0ab99a139476f3f11cf/src/ramsey.cpp#L113)). It starts with edges at size 2. It includes each entered monochromatic prefix, even if the count test rejects it immediately, and includes a size-k clique when found. It has no empty or singleton entries. On valid final colourings there are no size-k entries.

The unchanged starting-edge loops ([lines 141–146](https://github.com/avinazz3/local_lovasz_lemma/blob/8a7f58f20c0b497e8791b0ab99a139476f3f11cf/src/ramsey.cpp#L141-L146)) use zero-based `u <= n-k` and `v <= n-k+1`, so a complete final search starts at C(n−k+2, 2) edges. Both builds keep these bounds. With the count tests disabled, size i visits precisely the monochromatic i-sets whose second-smallest vertex is at most n−k+1. Each is visited once in increasing order.

Full P sums the fresh-colouring expectations over all sets of sizes 2 through k. P from size 3 subtracts C(n,2). For the actual search, the eligible number at size i is the sum of v × C(n−v−1, i−2) over second vertices v from 1 through n−k+1. Multiplying by the monochromatic probability and summing gives the fresh expectation for eligible sets. Final colourings are outputs of repair, so the fresh values provide a comparison.

| Instance | Full P | P from size 3 | Starting edges visited | Fresh expectation for eligible sets |
|---|---:|---:|---:|---:|
| (13,6) | 174.462158 | 96.462158 | 36 | 116.788330 |
| (22,7) | 900.744003 | 669.744003 | 136 | 755.106247 |
| (36,8) | 5119.163964 | 4489.163964 | 435 | 4786.543513 |
| (12,4) | 136.468750 | 70.468750 | 45 | 112.968750 |
| (16,5) | 325.406250 | 205.406250 | 78 | 273.000000 |
| (20,5) | 656.687500 | 466.687500 | 136 | 589.156250 |
| (24,6) | 1205.293213 | 929.293213 | 190 | 1085.722900 |
| (28,6) | 2051.791260 | 1673.791260 | 276 | 1909.713135 |
| (32,7) | 3311.582001 | 2815.582001 | 351 | 3087.720978 |

### (36,8) visits by size

The measured column averages the 100 final searches with the count tests disabled.

| Size i | Mean visited | Fresh prediction, all i-sets | Fresh prediction, eligible i-sets |
|---:|---:|---:|---:|
| 2 | 435.00 | 630.000000 | 435.000000 |
| 3 | 1667.77 | 1785.000000 | 1667.500000 |
| 4 | 1815.89 | 1840.781250 | 1821.562500 |
| 5 | 718.86 | 736.312500 | 735.421875 |
| 6 | 107.93 | 118.883789 | 118.872742 |
| 7 | 5.49 | 7.960968 | 7.960939 |
| 8 | 0.00 | 0.225457 | 0.225457 |

### Does each search return at the first monochromatic k-set?

**Scalar branching: yes.** `if (int(s.size()) == k) { answer = s; return true; }` saves the clique at [line 92](https://github.com/avinazz3/local_lovasz_lemma/blob/8a7f58f20c0b497e8791b0ab99a139476f3f11cf/src/ramsey.cpp#L92). [Line 104](https://github.com/avinazz3/local_lovasz_lemma/blob/8a7f58f20c0b497e8791b0ab99a139476f3f11cf/src/ramsey.cpp#L104) propagates success recursively and [line 149](https://github.com/avinazz3/local_lovasz_lemma/blob/8a7f58f20c0b497e8791b0ab99a139476f3f11cf/src/ramsey.cpp#L149) exits the starting-edge loop.

**Bitset branching: yes.** The same base case is at [line 115](https://github.com/avinazz3/local_lovasz_lemma/blob/8a7f58f20c0b497e8791b0ab99a139476f3f11cf/src/ramsey.cpp#L115). [Line 131](https://github.com/avinazz3/local_lovasz_lemma/blob/8a7f58f20c0b497e8791b0ab99a139476f3f11cf/src/ramsey.cpp#L131) propagates success recursively and [line 154](https://github.com/avinazz3/local_lovasz_lemma/blob/8a7f58f20c0b497e8791b0ab99a139476f3f11cf/src/ramsey.cpp#L154) exits the starting-edge loop. The final searches here have no success to return early, so each traverses its full permitted tree.

## Sanity checks

- Pinned gzip blob and exact 12 × 100 instance/seed list match. All 3,600 archived MT method rows agree within their paired trials.
- Before M1/M2, all 1,200 seeded replays matched the stored repair count, trajectory hash, and both graph bit strings. The solver source SHA-256 matches the archive.
- Both count-all implementations return C(6,4) = 15 for both single-colour K6 test graphs.
- All 1,200 initial counts are in range. Zero count agrees with zero repairs for every sample.
- Exhaustive naive scan matches every bitset count on 800 graphs, covering all 800 requested graphs with n ≤ 22 and every flagged case.
- All 1,800 final searches exhausted their trees with no target clique. The level totals agree with the existing counter, and sizes 1 and k contribute zero on every final graph.
- All 1,800 edge-level counts match C(n−k+2, 2). Each higher level is bounded by its number of eligible vertex sets. Enabling the count test never increases visits.
- Every with-test final total matches its archived value (900/900). Both existing no-test instances match per seed (200/200).
- The archived without/with medians reproduce exactly: (28,6) 1,594 / 487 and (36,8) 4,727.5 / 727.5.
- CSV readback matches the measured values, keys, and column layout for all 1,200 initial rows and 1,800 final rows.

In `m2_visited.csv`, the size columns are filled for the without-test build up to k, including the measured zero at size 1. Cells for sizes above k and for the with-test breakdown are blank.

## Wall-clock time

The check script used **3.344 seconds** through compilation, repair replay, counting, validation and CSV writing. This is elapsed time for the measurement job. It excludes preparation of the repository and writing this summary. The existing timing benchmark was not run, and no stored timing was changed.
