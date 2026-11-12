#!/usr/bin/env python3
"""Reproduce the expanded experiment's graphs and measure clique counts only."""

import csv
import gzip
import hashlib
import json
import math
import os
import statistics
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "results/expanded/raw.json.gz"
OUTPUT = ROOT / "results/theory_check"
COMMIT = "8a7f58f20c0b497e8791b0ab99a139476f3f11cf"
SOURCE_URL = f"https://github.com/avinazz3/local_lovasz_lemma/blob/{COMMIT}/src/ramsey.cpp"
REFERENCE_BLOB = "bbf99ea8b779fc5f9607bc297a9d46c59d619888"
CASES = [(4, 4), (7, 5), (13, 6), (22, 7), (36, 8), (5, 3), (12, 4), (16, 5),
         (20, 5), (24, 6), (28, 6), (32, 7)]
VISIT_CASES = [(13, 6), (22, 7), (36, 8), (12, 4), (16, 5), (20, 5), (24, 6),
               (28, 6), (32, 7)]
ABLATED_MEDIANS = {(28, 6): (1594, 487), (36, 8): (4727.5, 727.5)}
SEEDS = range(20270000, 20270100)
METHODS = {"naive", "branching", "hs_bitset"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def instance(case):
    return f"({case[0]},{case[1]})"


def read_reference():
    compressed = REFERENCE.read_bytes()
    blob = hashlib.sha1(f"blob {len(compressed)}\0".encode() + compressed).hexdigest()
    require(blob == REFERENCE_BLOB, "expanded data differs from the pinned Git blob")
    data = json.loads(gzip.decompress(compressed))
    metadata = data["metadata"]
    require(metadata["complete"] and list(map(tuple, metadata["cases"])) == CASES
            and metadata["seed"] == SEEDS.start and metadata["trials"] == len(SEEDS),
            "archived cases or seeds differ from the requested study")
    groups, final_counts, ablation_counts = {}, {}, {}
    for row in data["runs"]:
        key = (row["n"], row["k"], row["seed"])
        if row["phase"] == "mt":
            methods = groups.setdefault(key, {})
            require(row["method"] not in methods, f"duplicate MT row {key}")
            methods[row["method"]] = row
        if row["phase"] == "final" and row["method"] == "hs_bitset":
            require(key not in final_counts, f"duplicate final row {key}")
            final_counts[key] = row
    for row in data["ablation_runs"]:
        key = (row["n"], row["k"], row["seed"])
        require(key not in ablation_counts, f"duplicate ablation row {key}")
        ablation_counts[key] = row
    keys = [(*case, seed) for case in CASES for seed in SEEDS]
    require(set(groups) == set(keys), "archived MT rows do not cover the exact requested samples")
    reference = {}
    for key in keys:
        methods = groups[key]
        require(set(methods) == METHODS, f"missing archived method for {key}")
        fields = ("resamplings", "trajectory_hash", "initial_edge_bits", "final_edge_bits")
        require(all(r["verified"] and r["status"] == "success" for r in methods.values())
                and len({tuple(r[field] for field in fields) for r in methods.values()}) == 1,
                f"archived methods disagree for {key}")
        reference[key] = methods["hs_bitset"]
    return metadata, reference, final_counts, ablation_counts


def build(directory, metadata):
    source = (ROOT / "src/ramsey.cpp").read_bytes()
    require(hashlib.sha256(source).hexdigest() == metadata["source_sha256"]["src/ramsey.cpp"],
            "solver source differs from the archived expanded experiment")
    instrumented = source.decode()
    for anchor, replacement in [
        ("struct Counters {", "struct Counters {\n    std::array<uint64_t, 65> visited_by_size{};"),
        ("Clique& answer, Counters& c, Budget& budget) {\n    ++c.prefixes;\n    budget.tick();\n"
         "    if (int(s.size()) == k) { answer = s; return true; }\n#ifndef RAMSEY_NO_CARDINALITY_PRUNING",
         "Clique& answer, Counters& c, Budget& budget) {\n    ++c.visited_by_size[s.size()];\n"
         "    ++c.prefixes;\n    budget.tick();\n    if (int(s.size()) == k) { answer = s; return true; }\n"
         "#ifndef RAMSEY_NO_CARDINALITY_PRUNING"),
    ]:
        require(instrumented.count(anchor) == 1, "unable to locate the original counter")
        instrumented = instrumented.replace(anchor, replacement, 1)
    (directory / "ramsey_instrumented.cpp").write_text(instrumented)
    binaries = {}
    for name in ("with_count_test", "without_count_test"):
        binary = directory / name
        command = [os.environ.get("CXX", "c++"), "-O3", "-DNDEBUG", "-std=c++17", "-Wall",
                   "-Wextra", "-Wpedantic", "-I", str(directory)]
        if name == "without_count_test":
            command.append("-DRAMSEY_NO_CARDINALITY_PRUNING")
        subprocess.run([*command, str(ROOT / "scripts/theory_check.cpp"), "-o", str(binary)], check=True)
        binaries[name] = binary
    return binaries


def run_batch(binary, requests):
    request_lines = "".join(" ".join(map(str, row)) + "\n" for row in requests)
    result = subprocess.run([str(binary)], input=request_lines, text=True, capture_output=True)
    require(result.returncode == 0, f"{binary.name} failed: {result.stderr.strip()}")
    output = result.stdout.splitlines()
    require(len(output) == len(requests), f"{binary.name} returned an incomplete batch")
    return output


def check_replays(binary, metadata, reference):
    requests = [("replay", *key, metadata["max_resamplings"]) for key in reference]
    for key, line in zip(reference, run_batch(binary, requests)):
        repairs, trajectory, initial, final = line.split()
        archived = reference[key]
        require(int(repairs) == archived["resamplings"],
                f"repair mismatch {key}: observed {repairs}, archived {archived['resamplings']}")
        require((trajectory, initial, final) == (archived["trajectory_hash"],
                archived["initial_edge_bits"], archived["final_edge_bits"]),
                f"trajectory hash or graph mismatch {key}")


def fresh_probability(size):
    return 2.0 ** (1 - math.comb(size, 2))


def model_standard_error(n, k):
    # Ordered pairs of k-sets with intersection s. s=k gives the diagonal term.
    p = fresh_probability(k)
    variance = math.comb(n, k) * p**2 * sum(
        math.comb(k, s) * math.comb(n - k, k - s) * (2**(math.comb(s, 2) - 1) - 1)
        for s in range(2, k + 1)
    )
    return math.sqrt(variance / len(SEEDS))


def measure_initial(binary, reference, checks):
    keys = list(reference)
    counts = dict(zip(keys, map(int, run_batch(binary, [
        ("count_bitset", n, k, reference[n, k, seed]["initial_edge_bits"]) for n, k, seed in keys
    ]))))
    for key, count in counts.items():
        require(0 <= count <= math.comb(*key[:2]), f"invalid initial count {key}")
        require((count == 0) == (reference[key]["resamplings"] == 0),
                f"initial count and repair status disagree {key}")
    checks.append("All 1,200 initial counts are in range. Zero count agrees with zero repairs for every sample.")
    stats, outliers = {}, []
    for n, k in CASES:
        values = [counts[n, k, seed] for seed in SEEDS]
        mean = statistics.mean(values)
        prediction = math.comb(n, k) * fresh_probability(k)
        se = statistics.stdev(values) / math.sqrt(len(values))
        model_se = model_standard_error(n, k)
        if abs(mean - prediction) > 2 * min(se, model_se):
            outliers.append((n, k))
        stats[n, k] = (mean, prediction, statistics.median(values), values.count(0) / len(values), se, model_se)

    # Independently inspect each k-set for all requested small cases and any flagged case.
    cross_keys = [key for key in keys if key[0] <= 22 or key[:2] in outliers]
    for key, line in zip(cross_keys, run_batch(binary, [
        ("count_naive", *key[:2], reference[key]["initial_edge_bits"]) for key in cross_keys
    ])):
        require(int(line) == counts[key], f"naive and bitset counts disagree {key}")
    checks.append(f"Exhaustive naive scan matches every bitset count on {len(cross_keys):,} graphs, "
                  "covering all 800 requested graphs with n ≤ 22 and every flagged case.")
    return counts, stats, outliers


def eligible_sets(n, k, size):
    return sum(v * math.comb(n - v - 1, size - 2) for v in range(1, n - k + 2))


def measure_visits(binaries, reference, final_counts, ablation_counts, checks):
    keys = [(*case, seed) for case in VISIT_CASES for seed in SEEDS]
    requests = [("visit", *key[:2], reference[key]["final_edge_bits"]) for key in keys]
    visits = {}
    for build_name, binary in binaries.items():
        for key, line in zip(keys, run_batch(binary, requests)):
            n, k, _ = key
            total, *levels = map(int, line.split())
            require(len(levels) == k and total == sum(levels) and levels[0] == levels[-1] == 0,
                    f"inconsistent level counts for {key} {build_name}")
            require(levels[1] == math.comb(n - k + 2, 2), f"unexpected starting edge count for {key}")
            require(all(0 <= value <= eligible_sets(n, k, size)
                        for size, value in enumerate(levels[1:], 2)), f"out-of-range level count for {key}")
            archived = (final_counts if build_name == "with_count_test" else ablation_counts).get(key)
            if build_name == "with_count_test" or key[:2] in ABLATED_MEDIANS:
                require(archived is not None and archived["prefixes"] == total
                        and archived["final_edge_bits"] == reference[key]["final_edge_bits"],
                        f"archived visited count or final graph mismatch for {key} {build_name}")
            visits[key, build_name] = total, levels
    statistics_by_case = {}
    for case in VISIT_CASES:
        before = [visits[(*case, seed), "without_count_test"][0] for seed in SEEDS]
        after = [visits[(*case, seed), "with_count_test"][0] for seed in SEEDS]
        require(all(x >= y > 0 for x, y in zip(before, after)), f"pruning increased visits at {case}")
        ratios = [x / y for x, y in zip(before, after)]
        medians = statistics.median(before), statistics.median(after)
        if case in ABLATED_MEDIANS:
            require(medians == ABLATED_MEDIANS[case], f"ablation median mismatch at {case}: {medians}")
        statistics_by_case[case] = (*medians, statistics.median(ratios), statistics.mean(before),
                                    statistics.mean(after), statistics.mean(ratios))
    checks.extend([
        "All 1,800 final searches exhausted their trees with no target clique. The level totals agree with the existing counter, and sizes 1 and k contribute zero on every final graph.",
        "All 1,800 edge-level counts match C(n−k+2, 2). Each higher level is bounded by its number of eligible vertex sets. Enabling the count test never increases visits.",
        "Every with-test final total matches its archived value (900/900). Both existing no-test instances match per seed (200/200).",
        "The archived without/with medians reproduce exactly: (28,6) 1,594 / 487 and (36,8) 4,727.5 / 727.5.",
    ])
    return visits, statistics_by_case


def csv_file(path, header, rows):
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def summary(initial, outliers, visits, visited, checks, elapsed):
    lines = [
        "# Ramsey theory checks", "",
        f"Reference commit `{COMMIT}`. Each instance uses the 100 archived seeds 20270000–20270099.", "",
        "Reproduce the measurements with `python3 scripts/theory_check.py` from the repository root.", "",
        "## Initial", "",
        "Every row uses all 100 initial colourings. `SE` is the sample standard deviation divided by √100. `Model SE` uses the exact variance of the count under independent fair edge colours.", "",
        "| Instance | Mean initial count | m·p | Median | Zero fraction | SE | Model SE |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case, (mean, expected, median, zero, se, model_se) in initial.items():
        lines.append(f"| {instance(case)} | {mean:#.3g} | {expected:.6g} | {median:g} | {zero:.2f} | {se:.6g} | {model_se:.6g} |")
    lines += ["", "The variance accounts for overlapping sets. For two k-sets sharing s ≥ 2 vertices, their joint monochromatic probability is p² × 2^(C(s,2)−1). With zero or one shared vertex, the events are independent. The variance sums the covariances over ordered pairs, including the diagonal s = k.", ""]
    if outliers:
        lines += ["The following sample means exceed two standard errors under at least one of the two scales. Every flagged count was checked by the naive scan, and the seeded replay matched the archived graph bit for bit.", "",
                  "| Instance | Observed minus m·p | Difference / sample SE | Difference / model SE |",
                  "|---|---:|---:|---:|"]
        for case in outliers:
            mean, expected, _, _, se, model_se = initial[case]
            difference = mean - expected
            observed_scale = f"{difference / se:+.3f}" if se else "undefined (SE = 0)"
            lines.append(f"| {instance(case)} | {difference:+.6g} | {observed_scale} | {difference / model_se:+.3f} |")
        lines += ["", "Rare counts give discrete, skewed samples and can yield a small sample SE. The model variance allows several overlapping monochromatic sets on a single graph."]
        if (13, 6) in outliers:
            mean, _, _, zero, _, _ = initial[13, 6]
            lines += ["", f"For (13,6), {round(zero * len(SEEDS))} graphs have count zero. "
                      f"The total count over the 100 graphs is {round(mean * len(SEEDS))}."]
    else:
        lines += ["All 12 observed means are within two SEs of m·p under both scales."]
    if outliers and all(abs(row[0] - row[1]) <= 2 * row[-1] for row in initial.values()):
        lines += ["", "All 12 observed means are within two model SEs of m·p."]
    lines += ["", "## Visited", "",
              "Without/with refers to the two candidate-count tests. Ratios are calculated per seed before taking their mean or median.", "",
              "| Instance | Median without | Median with | Median ratio | Mean without | Mean with | Mean ratio |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for case, (median_without, median_with, median_ratio, mean_without, mean_with, mean_ratio) in visited.items():
        lines.append(f"| {instance(case)} | {median_without:,g} | {median_with:,g} | {median_ratio:.6g} | "
                     f"{mean_without:,.2f} | {mean_with:,.2f} | {mean_ratio:.6g} |")
    lines += ["", "### What the counter includes", "",
              f"The `prefixes` counter increments on entry to the recursion ([scalar line 90]({SOURCE_URL}#L90), [bitset line 113]({SOURCE_URL}#L113)). It starts with edges at size 2. It includes each entered monochromatic prefix, even if the count test rejects it immediately, and includes a size-k clique when found. It has no empty or singleton entries. On valid final colourings there are no size-k entries.", "",
              f"The unchanged starting-edge loops ([lines 141–146]({SOURCE_URL}#L141-L146)) use zero-based `u <= n-k` and `v <= n-k+1`, so a complete final search starts at C(n−k+2, 2) edges. Both builds keep these bounds. With the count tests disabled, size i visits precisely the monochromatic i-sets whose second-smallest vertex is at most n−k+1. Each is visited once in increasing order.", "",
              "Full P sums the fresh-colouring expectations over all sets of sizes 2 through k. P from size 3 subtracts C(n,2). For the actual search, the eligible number at size i is the sum of v × C(n−v−1, i−2) over second vertices v from 1 through n−k+1. Multiplying by the monochromatic probability and summing gives the fresh expectation for eligible sets. Final colourings are outputs of repair, so the fresh values provide a comparison.", "",
              "| Instance | Full P | P from size 3 | Starting edges visited | Fresh expectation for eligible sets |",
              "|---|---:|---:|---:|---:|"]
    for n, k in VISIT_CASES:
        full = sum(math.comb(n, i) * fresh_probability(i) for i in range(2, k + 1))
        restricted = sum(eligible_sets(n, k, i) * fresh_probability(i) for i in range(2, k + 1))
        lines.append(f"| {instance((n, k))} | {full:.6f} | {full - math.comb(n, 2):.6f} | "
                     f"{math.comb(n-k+2, 2)} | {restricted:.6f} |")
    lines += ["", "### (36,8) visits by size", "",
              "The measured column averages the 100 final searches with the count tests disabled.", "",
              "| Size i | Mean visited | Fresh prediction, all i-sets | Fresh prediction, eligible i-sets |",
              "|---:|---:|---:|---:|"]
    for i in range(2, 9):
        mean = statistics.mean(visits[(36, 8, seed), "without_count_test"][1][i - 1] for seed in SEEDS)
        lines.append(f"| {i} | {mean:.2f} | {math.comb(36, i)*fresh_probability(i):.6f} | "
                     f"{eligible_sets(36, 8, i)*fresh_probability(i):.6f} |")
    lines += ["", "### Does each search return at the first monochromatic k-set?", "",
              f"**Scalar branching: yes.** `if (int(s.size()) == k) {{ answer = s; return true; }}` saves the clique at [line 92]({SOURCE_URL}#L92). [Line 104]({SOURCE_URL}#L104) propagates success recursively and [line 149]({SOURCE_URL}#L149) exits the starting-edge loop.", "",
              f"**Bitset branching: yes.** The same base case is at [line 115]({SOURCE_URL}#L115). [Line 131]({SOURCE_URL}#L131) propagates success recursively and [line 154]({SOURCE_URL}#L154) exits the starting-edge loop. The final searches here have no success to return early, so each traverses its full permitted tree.", "",
              "## Sanity checks", "", *[f"- {check}" for check in checks], "",
              "In `m2_visited.csv`, the size columns are filled for the without-test build up to k, including the measured zero at size 1. Cells for sizes above k and for the with-test breakdown are blank.", "",
              "## Wall-clock time", "",
              f"The check script used **{elapsed:.3f} seconds** through compilation, repair replay, counting, validation and CSV writing. This is elapsed time for the measurement job. It excludes preparation of the repository and writing this summary. The existing timing benchmark was not run, and no stored timing was changed.", ""]
    return "\n".join(lines)


def main():
    start = time.perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks = []
    try:
        metadata, reference, final_counts, ablation_counts = read_reference()
        checks.append("Pinned gzip blob and exact 12 × 100 instance/seed list match. All 3,600 archived MT method rows agree within their paired trials.")
        with tempfile.TemporaryDirectory(prefix="ramsey-theory-") as directory:
            binaries = build(Path(directory), metadata)
            binary = binaries["with_count_test"]
            check_replays(binary, metadata, reference)
            checks.append("Before M1/M2, all 1,200 seeded replays matched the stored repair count, trajectory hash, and both graph bit strings. The solver source SHA-256 matches the archive.")
            print(checks[-1], flush=True)
            synthetic = [(method, 6, 4, colour * 15) for method in ("count_bitset", "count_naive")
                         for colour in ("0", "1")]
            require(run_batch(binary, synthetic) == ["15"] * len(synthetic), "single-colour count check failed")
            checks.append("Both count-all implementations return C(6,4) = 15 for both single-colour K6 test graphs.")
            counts, initial, outliers = measure_initial(binary, reference, checks)
            print(checks[-1], flush=True)
            visits, visited = measure_visits(binaries, reference, final_counts, ablation_counts, checks)
            print(checks[-1], flush=True)
        initial_rows = [[instance(key[:2]), key[2], count] for key, count in counts.items()]
        initial_header = ["instance", "seed", "count"]
        csv_file(OUTPUT / "m1_initial.csv", initial_header, initial_rows)
        max_size = max(k for _, k in VISIT_CASES)
        visit_rows = []
        for (key, build_name), (total, levels) in visits.items():
            breakdown = levels if build_name == "without_count_test" else []
            padding = [""] * (max_size - len(breakdown))
            visit_rows.append([instance(key[:2]), key[2], build_name, total, *breakdown, *padding])
        visit_header = ["instance", "seed", "build", "total_visited",
                        *[f"visited_{i}" for i in range(1, max_size + 1)]]
        csv_file(OUTPUT / "m2_visited.csv", visit_header, visit_rows)
        for filename, header, rows in [("m1_initial.csv", initial_header, initial_rows),
                                       ("m2_visited.csv", visit_header, visit_rows)]:
            with (OUTPUT / filename).open(newline="") as stream:
                require(list(csv.reader(stream)) == [header, *[list(map(str, row)) for row in rows]],
                        f"CSV readback disagrees with measured values: {filename}")
        checks.append("CSV readback matches the measured values, keys, and column layout for all 1,200 initial rows and 1,800 final rows.")
        elapsed = time.perf_counter() - start
        (OUTPUT / "summary.md").write_text(summary(initial, outliers, visits, visited, checks, elapsed))
        print(f"Saved {len(counts)} initial counts and {len(visits)} final search records in {elapsed:.3f} s.")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        elapsed = time.perf_counter() - start
        completed = "\n".join(f"- {check}" for check in checks)
        (OUTPUT / "summary.md").write_text(f"# Ramsey theory checks stopped\n\n{error}\n\n"
                                          f"Checks completed:\n\n{completed}\n\nElapsed: {elapsed:.3f} seconds.\n")
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
