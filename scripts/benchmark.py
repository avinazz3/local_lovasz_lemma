#!/usr/bin/env python3
"""Reproducible paired Ramsey experiments; Python standard library only."""
import argparse
import csv
import hashlib
import itertools
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("naive", "branching", "hs_bitset")
PRESETS = {
    "smoke": [(5, 3), (12, 4), (13, 6)],
    "report": [(4, 4), (7, 5), (13, 6), (22, 7), (36, 8),
               (5, 3), (12, 4), (20, 5), (28, 6)],
}


def graph_from_bits(n, bits):
    if len(bits) != math.comb(n, 2) or set(bits) - {"0", "1"}:
        raise ValueError("invalid graph certificate")
    graph = [[None] * n for _ in range(n)]
    for (u, v), bit in zip(itertools.combinations(range(n), 2), bits):
        graph[u][v] = graph[v][u] = int(bit)
    return graph


def exhaustive_first(n, k, bits):
    """Small-instance oracle, intentionally independent of the C++ searches."""
    graph = graph_from_bits(n, bits)
    for vertices in itertools.combinations(range(n), k):
        colour = graph[vertices[0]][vertices[1]]
        if all(graph[u][v] == colour for u, v in itertools.combinations(vertices, 2)):
            return list(vertices)
    return []


def certificate_first(n, k, bits):
    """Independent Python verifier; graph-certificate verification is not timed as MT."""
    graph = graph_from_bits(n, bits)

    def extend(prefix, candidates, colour):
        if len(prefix) == k:
            return prefix
        need = k - len(prefix)
        if len(candidates) < need:
            return []
        for index, vertex in enumerate(candidates):
            if len(candidates) - index < need:
                break
            following = [u for u in candidates[index + 1:] if graph[vertex][u] == colour]
            found = extend(prefix + [vertex], following, colour)
            if found:
                return found
        return []

    # Colour-specific DFS from each smallest vertex. Compare both colours to
    # obtain the same lexicographic order without depending on the C++ code.
    for u in range(n - k + 1):
        found = []
        for colour in (0, 1):
            candidates = [v for v in range(u + 1, n) if graph[u][v] == colour]
            result = extend([u], candidates, colour)
            if result and (not found or result < found):
                found = result
        if found:
            return found
    return []


def lll_condition(n, k):
    # Inclusive-neighbourhood overcount from the report; log form avoids overflow.
    degree_bound = math.comb(k, 2) * math.comb(n - 2, k - 2)
    log_epd = 1 + (1 - math.comb(k, 2)) * math.log(2) + math.log(degree_bound)
    return {"lll_certified": log_epd <= 0, "log_epd": log_epd,
            "expected_resampling_bound": math.comb(n, k) * math.e * 2 ** (1 - math.comb(k, 2))
            if log_epd <= 0 else None}


def invoke(binary, n, k, seed, method, seconds, max_resamplings, bits=None):
    command = [str(binary), "--n", str(n), "--k", str(k), "--seed", str(seed),
               "--method", method, "--seconds", str(seconds),
               "--max-resamplings", str(max_resamplings)]
    if bits is not None:
        command += ["--search-only", "--bits", bits]
    process = subprocess.run(command, text=True, capture_output=True, timeout=seconds + 10)
    if process.returncode:
        raise RuntimeError(f"Solver failed ({process.returncode}): {process.stderr}")
    result = json.loads(process.stdout)
    result["verified"] = False
    result["verification_seconds"] = 0.0
    if result["status"] in ("success", "found", "absent"):
        start = time.perf_counter()
        found = certificate_first(n, k, result["final_edge_bits"])
        if result["status"] in ("success", "absent") and found:
            raise AssertionError(f"Invalid absence certificate: {found}")
        if result["status"] == "found" and found != result["clique"]:
            raise AssertionError(f"Search returned {result['clique']}, expected {found}")
        result["verification_seconds"] = time.perf_counter() - start
        result["verified"] = True
    result.update(lll_condition(n, k))
    return result


def summary_rows(runs):
    groups = defaultdict(list)
    for row in runs:
        groups[(row["phase"], row["n"], row["k"], row["method"])].append(row)
    summaries = []
    for (phase, n, k, method), rows in sorted(groups.items()):
        completed = [r for r in rows if r["verified"]]
        out = dict(phase=phase, n=n, k=k, method=method, trials=len(rows),
                   completed=len(completed), timeouts=sum(r["status"] == "timeout" for r in rows),
                   resampling_limits=sum(r["status"] == "resampling_limit" for r in rows),
                   lll_certified=rows[0]["lll_certified"])
        for field in ("total_seconds", "search_seconds", "resamplings", "candidates_tested",
                      "edge_checks", "prefixes", "bitset_intersections"):
            values = [r[field] for r in completed]
            out["median_" + field] = statistics.median(values) if values else None
            out["mean_" + field] = statistics.mean(values) if values else None
            out["sd_" + field] = statistics.stdev(values) if len(values) > 1 else None
        summaries.append(out)
    return summaries


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def checkpoint(directory, metadata, runs):
    temporary = directory / "raw.json.tmp"
    temporary.write_text(json.dumps({"schema_version": 1, "metadata": metadata,
                                     "runs": runs}, indent=2) + "\n")
    temporary.replace(directory / "raw.json")


def fmt(value, digits=3):
    return "—" if value is None else f"{value:.{digits}g}"


def write_report(path, runs, summaries, metadata):
    text = ["# Ramsey search experiment", "",
            f"Generated {metadata['utc_timestamp']}; {metadata['trials']} trials per instance.", "",
            "These are measurements on small instances, not a test of asymptotic exponents. "
            "Capped runs are reported separately; successful-only medians can be biased when runs are censored.", "",
            "`naive` scans k-sets; `branching` tests monochromatic prefixes with scalar edges; "
            "`hs_bitset` uses common-neighbour bitsets and cardinality pruning. The last two implement "
            "the same structured search analysed by Harris–Srinivasan. Bitsets are an engineering "
            "optimization, not a distinct third theoretical algorithm.", "",
            "All methods choose the lexicographically first bad clique and consume identical random "
            "draws for initialization and each repair. Their successful paired trajectories and final "
            "colourings are checked for equality. All completed outputs are checked by a separate "
            "Python verifier; verification and subprocess startup are excluded from solver timings.", "",
            "## Full Moser–Tardos runs", "",
            "| n | k | LLL certified | Method | Completed | Timeout / repair cap | Median total (s) | Median search (s) | Median repairs |",
            "|---:|---:|:---:|---|---:|---:|---:|---:|---:|"]
    for row in summaries:
        if row["phase"] != "mt":
            continue
        text.append(f"| {row['n']} | {row['k']} | {'yes' if row['lll_certified'] else 'no'} | "
                    f"{row['method']} | {row['completed']}/{row['trials']} | "
                    f"{row['timeouts']} / {row['resampling_limits']} | "
                    f"{fmt(row['median_total_seconds'])} | {fmt(row['median_search_seconds'])} | "
                    f"{fmt(row['median_resamplings'])} |")
    text += ["", "## Paired full-run speedups", "",
             "Median of per-seed runtime ratios, using only seeds on which all three methods completed. "
             "The counts expose exclusions rather than treating timeouts as completed runs.", "",
             "| n | k | Complete triplets | Naive / branching | Naive / hs_bitset |", "|---:|---:|---:|---:|---:|"]
    groups = defaultdict(dict)
    for row in runs:
        if row["phase"] == "mt":
            groups[(row["n"], row["k"], row["seed"])][row["method"]] = row
    ratios = defaultdict(list)
    for (n, k, seed), group in groups.items():
        if len(group) == 3 and all(r["verified"] for r in group.values()):
            ratios[(n, k)].append(tuple(group["naive"]["total_seconds"] / group[m]["total_seconds"]
                                         for m in METHODS[1:]))
    for n, k in sorted({(r["n"], r["k"]) for r in runs if r["phase"] == "mt"}):
        pairs = ratios[(n, k)]
        vals = [statistics.median(x[i] for x in pairs) if pairs else None for i in (0, 1)]
        text.append(f"| {n} | {k} | {len(pairs)} | {fmt(vals[0])} | {fmt(vals[1])} |")
    text += ["", "## Searches on identical snapshots", "",
             "Initial configurations and every available successful final configuration are replayed "
             "without resampling. Final snapshots measure the complete absence search, which cannot "
             "benefit from stopping at the first violation.", "",
             "| Snapshot | n | k | Method | Completed | Median search (s) | Median candidates |",
             "|---|---:|---:|---|---:|---:|---:|"]
    for row in summaries:
        if row["phase"] == "mt":
            continue
        text.append(f"| {row['phase']} | {row['n']} | {row['k']} | {row['method']} | "
                    f"{row['completed']}/{row['trials']} | {fmt(row['median_search_seconds'])} | "
                    f"{fmt(row['median_candidates_tested'])} |")
    text += ["", "## Interpretation and reproducibility", "",
             "The sufficient condition is `e * 2^(1-C(k,2)) * C(k,2) * C(n-2,k-2) <= 1`. "
             "Uncertified instances are heuristic stress tests: their termination is not guaranteed by "
             "this condition. Each successful colouring individually certifies R(k,k) > n.", "",
             "Candidate counts mean complete k-sets for naive search, attempted prefix extensions "
             "(including seed edges) for scalar branching, and bitset-selected extensions (including "
             "seed edges) for hs_bitset. They are not equal-cost units. Bitset intersections and "
             "scalar edge checks are recorded separately. All methods maintain the same graph representations.", "",
             "Counters are instrumented; very short runs are sensitive to timer resolution and machine "
             "load. No speedup should be inferred from sub-millisecond timings alone. See raw.json for "
             "timings, seeds, certificates, counters, source hashes, compiler and platform; summary.csv "
             "also includes means and sample standard deviations.", "",
             "Reference: Harris and Srinivasan, *Algorithmic and enumerative aspects of the "
             "Moser–Tardos distribution*, arXiv:1507.02674v4, Section 3.2, Propositions 3.2–3.4. "
             "The experiments do not estimate the unknown Ramsey numbers or reproduce large-k scaling.", ""]
    path.write_text("\n".join(text))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build/ramsey_experiment")
    parser.add_argument("--preset", choices=PRESETS, default="report")
    parser.add_argument("--case", action="append", help="Override preset with n,k; repeatable")
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261104)
    parser.add_argument("--seconds", type=float, default=1.0)
    parser.add_argument("--max-resamplings", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=ROOT / "results/local")
    parser.add_argument("--skip-snapshots", action="store_true")
    args = parser.parse_args(argv)
    cases = [tuple(map(int, case.split(","))) for case in args.case] if args.case else PRESETS[args.preset]
    if (args.trials < 1 or args.seed < 0 or args.seed + args.trials > 2**64 or
            not math.isfinite(args.seconds) or not 0 < args.seconds <= 86400 or
            args.max_resamplings < 0 or len(set(cases)) != len(cases) or
            any(len(c) != 2 or not 2 <= c[1] <= c[0] <= 64 for c in cases)):
        parser.error("invalid trials, seed, limit, or case (require 2 <= k <= n <= 64)")
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("build the C++ executable first; see README.md")
    args.output.mkdir(parents=True, exist_ok=True)
    # A restarted/interrupted experiment must not expose an old summary beside
    # a new partial raw dataset. Only files owned by this runner are replaced.
    for filename in ("runs.csv", "summary.csv", "summary.json", "report.md"):
        (args.output / filename).unlink(missing_ok=True)
    tracked_sources = [*sorted((ROOT / "src").glob("*.cpp")), Path(__file__), ROOT / "CMakeLists.txt", ROOT / "Makefile"]
    metadata = dict(complete=False, utc_timestamp=datetime.now(timezone.utc).isoformat(),
                    platform=platform.platform(), python=sys.version, cpu=platform.processor(),
                    compiler=subprocess.run(["c++", "--version"], capture_output=True, text=True).stdout.splitlines()[0],
                    executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                    source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in tracked_sources},
                    cases=cases, trials=args.trials, seed=args.seed, seconds=args.seconds,
                    max_resamplings=args.max_resamplings, method_order="shuffled deterministically per trial",
                    timings="steady_clock inside C++; excludes process startup and independent verification")
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        metadata["cpu"] = next((line.split(":", 1)[1].strip() for line in cpuinfo.read_text().splitlines()
                                if line.startswith("model name")), metadata["cpu"])
    cmake_cache = ROOT / "build/CMakeCache.txt"
    if cmake_cache.exists():
        metadata["cmake_build_type"] = next((line.split("=", 1)[1] for line in cmake_cache.read_text().splitlines()
                                              if line.startswith("CMAKE_BUILD_TYPE:")), "unknown")
    build_command = binary.parent / "build_command.txt"
    if build_command.exists():
        metadata["build_command"] = build_command.read_text().strip()
    runs = []
    checkpoint(args.output, metadata, runs)
    order_rng = random.Random(args.seed)
    for n, k in cases:
        for trial in range(args.trials):
            seed = args.seed + trial
            order = list(METHODS)
            order_rng.shuffle(order)
            paired = {}
            for method in order:
                row = invoke(binary, n, k, seed, method, args.seconds, args.max_resamplings)
                row["phase"] = "mt"
                paired[method] = row
                runs.append(row)
                print(f"n={n} k={k} seed={seed} {method}: {row['status']} "
                      f"{row['total_seconds']:.4f}s repairs={row['resamplings']}", flush=True)
            if len({r["initial_edge_bits"] for r in paired.values()}) != 1:
                raise AssertionError("initial configurations differ")
            completed = [r for r in paired.values() if r["status"] == "success"]
            if len({(r["resamplings"], r["trajectory_hash"], r["final_edge_bits"]) for r in completed}) > 1:
                raise AssertionError("successful paired trajectories differ")
            if not args.skip_snapshots:
                snapshots = {"initial": paired["naive"]["initial_edge_bits"]}
                if completed:
                    snapshots["final"] = completed[0]["final_edge_bits"]
                for phase, bits in snapshots.items():
                    for method in order:
                        row = invoke(binary, n, k, seed, method, args.seconds, args.max_resamplings, bits)
                        row["phase"] = phase
                        runs.append(row)
            # Checkpoint every complete triplet; a stopped long run retains its evidence.
            checkpoint(args.output, metadata, runs)
    summaries = summary_rows(runs)
    write_csv(args.output / "runs.csv", [{k: v for k, v in row.items()
                                          if k not in ("initial_edge_bits", "final_edge_bits", "clique")}
                                         for row in runs])
    write_csv(args.output / "summary.csv", summaries)
    write_report(args.output / "report.md", runs, summaries, metadata)
    (args.output / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    metadata["complete"] = True
    checkpoint(args.output, metadata, runs)
    print(f"Saved {len(runs)} measurements to {args.output}")


if __name__ == "__main__":
    main()
