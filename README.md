# Algorithmic Local Lovász Lemma: Ramsey experiments

Reproducible experiments for the CS4234 report on Moser–Tardos resampling and fast search for monochromatic cliques. The program constructs red/blue edge colourings of `K_n` avoiding monochromatic `K_k`, or explicitly reports a time/repair limit.

## Build and test

Requirements: Python 3.9+, Make, and GCC or Clang with C++17 support. There are no third-party Python dependencies. The bitset implementation uses GCC/Clang's `popcount`/`ctz` intrinsics.

```sh
git clone https://github.com/avinazz3/local_lovasz_lemma.git
cd local_lovasz_lemma
make
make test
```

Optional CMake build:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

`make sanitize` compiles and runs the correctness suite with AddressSanitizer and UndefinedBehaviorSanitizer. Tests exhaust all 64 two-colourings of `K_4` for `k=2,3,4`, compare random small graphs with a Python exhaustive oracle, check identical repair trajectories, exercise vertex 63 and `K_64`, validate certificates, and check capped/impossible instances and result exports.

## Three measured implementations

| CLI name | Search | Role in the comparison |
|---|---|---|
| `naive` | Enumerate increasing `k`-vertex subsets; stop checking a set at its first conflicting edge. | Exhaustive baseline. |
| `branching` | Grow increasing monochromatic prefixes; test new incident edges individually. | Direct structured branching search. |
| `hs_bitset` | Grow the same prefixes using colour-specific common-neighbour bitsets and cardinality pruning. | Optimized implementation of the branching search analysed by Harris–Srinivasan. |

**The last two are not separate theoretical algorithms.** In the supplied paper, Harris–Srinivasan's Ramsey improvement is the analysis of structured branching search through intermediate MT states. We use `hs_bitset` as an explicit engineering variant to make a useful three-way experimental comparison; the paper does not supply an additional exponent improvement for using bitsets. See [docs/methodology.md](docs/methodology.md).

All three choose the lexicographically first bad clique, start with the same per-trial graph, and redraw its edges in the same order. Consequently they follow identical repair trajectories when allowed to finish. The harness checks their resampling counts, trajectory hashes, and exact final graph certificates. It also independently verifies every completed search and construction in Python.

The supported range is **`2 <= k <= n <= 64`**. This is an intentional machine-word limit for manageable small-instance experiments, not a general large-Ramsey-graph solver.

## Run the experiment

```sh
# Fast end-to-end check, including snapshot comparisons.
python3 scripts/benchmark.py --preset smoke --trials 2 --output results/local/smoke

# Default report experiment: 9 instances, 5 paired seeds, all three methods.
python3 scripts/benchmark.py --preset report --trials 5 --seconds 1 \
  --max-resamplings 10000 --output results/local/report

# Custom instances, with more repetitions and a larger budget.
python3 scripts/benchmark.py --case 22,7 --case 36,8 --trials 20 \
  --seconds 10 --output results/local/custom
```

The `--seconds` limit is **per solver invocation**, not for the entire benchmark. A trial runs three complete constructions and, by default, three searches on each initial/final snapshot. C++ checks the deadline periodically, so a cooperative limit can overshoot slightly. The harness also imposes a larger hard subprocess deadline to detect a broken solver. Use `--skip-snapshots` to measure only constructions.

The report preset contains LLL-certified instances `(n,k) = (4,4), (7,5), (13,6), (22,7), (36,8)` and heuristic stress instances `(5,3), (12,4), (20,5), (28,6)`. Each row records whether

```text
e * 2^(1-C(k,2)) * C(k,2) * C(n-2,k-2) <= 1
```

holds. This is the report's explicit sufficient condition. An uncertified instance may succeed; the LLL runtime guarantee is not claimed for it. No exact Ramsey-number values are inferred from failures or timeouts.

### Output files

| File | Contents |
|---|---|
| `raw.json` | All runs; seeds; full initial/final graph certificates; trajectory hashes; timings; counters; compiler/platform, executable/source hashes, and build command when available. Checkpointed after each trial. |
| `runs.csv` | One row per invocation, excluding bulky certificates. |
| `summary.csv`, `summary.json` | Per-instance/method/phase completion counts, cap counts, means, medians, and sample standard deviations. |
| `report.md` | Tables for the report, paired speedups, snapshot searches, and interpretation caveats. |

An interrupted run retains an atomic `raw.json` checkpoint marked `complete=false`. The verifier rejects incomplete datasets; old summary files are removed when a new run starts in the same output directory. Use separate output directories for concurrent experiments.

Successful-only summaries exclude capped runs and show the number excluded. The paired speedup table uses only seeds where **all three** constructions finish. Timeouts are never treated as valid colourings or substituted as completed runtimes. The checked-in [results/baseline](results/baseline) directory contains the initial measured run and is an example dataset; regenerate it to measure your machine.

Recheck the saved certificates and pairing without rerunning the benchmark:

```sh
python3 scripts/verify_results.py results/baseline/raw.json
```

## Expanded statistical study

The larger [results/expanded](results/expanded) study uses **100 new seeds for each of 12 instances**, instead of the five-seed, nine-instance pilot. It includes 3,600 constructions, 7,200 snapshot searches, and 200 controlled pruning-ablation searches. All completed certificates and the exact snapshot-to-construction pairing are independently checked. The two extra ablation datasets disable only the bitset candidate-count tests on the same final graphs.

```sh
make test
python3 scripts/expanded_experiment.py --trials 100 --bootstrap 2000 --output results/local/expanded
python3 scripts/verify_results.py results/expanded/raw.json.gz
```

The expanded runner builds on the same C++ solver. It shuffles all instance/seed triplets, randomizes method order within each triplet, performs excluded warm-ups, and pins itself and subprocesses to one permitted CPU where the operating system supports it. The default limits are five seconds and 100,000 repairs per invocation. Three extra cases are `(16,5)`, `(24,6)`, and `(32,7)`. Measured seeds `20270000` through `20270099` are disjoint from the pilot seeds; each case has 100 sampling units. Do not pool methods, phases, or different cases as if they were independent repetitions of the same experiment.

`statistics.json` includes means, medians, all tied repeated modes with their frequencies, sample standard deviations, quartiles, IQRs, ranges, 95th percentiles, and approximate bootstrap intervals. `summary.csv`, `repairs.csv`, and `paired_speedups.csv` expose the same analysis as tables. Runtime modes can reflect timer quantization, so the report interprets modes for discrete repair counts instead. When all values occur once, the mode list is empty and means **no repeated empirical mode**, not a numerical mode of zero.

The 95% intervals use 2,000 seeded percentile-bootstrap resamples. For speedups, one ratio is calculated per paired seed, then those paired observations are resampled. Intervals are pointwise and describe variability in this environment, not performance across machines. Capped runs remain explicit and are excluded only from completed-run statistics. `raw.json.gz` preserves all graphs and measurements in compressed JSON; `verify_results.py` reads it directly. The original pilot remains unchanged in `results/baseline`.

## Run one solver or replay a graph

```sh
./build/ramsey_experiment --n 20 --k 5 --seed 20261104 \
  --method hs_bitset --seconds 5 --max-resamplings 10000

# K5 with a red 5-cycle and blue complement: no monochromatic triangle.
./build/ramsey_experiment --n 5 --k 3 --method branching \
  --search-only --bits 1001100101
```

Each invocation prints one JSON object. Graph bits encode edges `(0,1),(0,2),...,(0,n-1),(1,2),...` with colours `0` and `1`. Construction statuses are `success`, `timeout`, and `resampling_limit`; snapshot statuses are `found`, `absent`, and `timeout`. A capped run is ordinary experimental data (exit code 0); invalid arguments or internal errors produce a nonzero exit code. Standalone C++ `success` means its search certified absence; the benchmark adds independent verification before marking `verified=true`.

Timings exclude subprocess startup, JSON serialization, and Python verification. `total_seconds` includes graph initialization, all searches (including the final absence search), repairs, and solver bookkeeping. All implementations maintain both scalar and bitset graph representations, so representation updates are charged consistently. Candidate counts have method-specific meanings and are not interchangeable units of work.

## References

- R. A. Moser and G. Tardos, *A constructive proof of the general Lovász Local Lemma*, Journal of the ACM 57(2), Article 11, 2010.
- D. G. Harris and A. Srinivasan, [*Algorithmic and enumerative aspects of the Moser–Tardos distribution*](https://arxiv.org/abs/1507.02674v4), 2017, Lemma 2.6, Theorem 3.1, and Propositions 3.2–3.4.

These small experiments compare implementations and search costs; they do not establish the asymptotic `2^(k²/2+o(k²))` versus `2^(k²/8+o(k²))` bounds empirically. The latter are theoretical results from the reference.
