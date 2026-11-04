#!/usr/bin/env python3
"""Recheck saved graph certificates and paired trajectories without rerunning MT."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from benchmark import METHODS, certificate_first, lll_condition, load_results


def verify(path):
    data = load_results(path)
    if data.get("schema_version") != 1:
        raise ValueError("unsupported results schema")
    if data.get("metadata", {}).get("complete") is not True:
        raise ValueError("experiment is incomplete; saved checkpoints are not final results")
    pairs = defaultdict(list)
    snapshots = defaultdict(list)
    checked = 0
    for row in data["runs"]:
        n, k = row["n"], row["k"]
        if row["method"] not in METHODS or row["phase"] not in ("mt", "initial", "final"):
            raise ValueError("unknown method or phase")
        if row["lll_certified"] != lll_condition(n, k)["lll_certified"]:
            raise ValueError("incorrect LLL certification flag")
        if row["status"] in ("success", "found", "absent"):
            found = certificate_first(n, k, row["final_edge_bits"])
            if row["status"] == "found":
                if not found or row["clique"] != found:
                    raise ValueError("incorrect found-clique certificate")
            elif found:
                raise ValueError("incorrect absence certificate")
            if not row["verified"]:
                raise ValueError("completed output was not marked verified")
            checked += 1
        elif row["status"] in ("timeout", "resampling_limit"):
            if row["verified"]:
                raise ValueError("capped output marked verified")
        else:
            raise ValueError("unknown status")
        if row["phase"] == "mt":
            pairs[(n, k, row["seed"])].append(row)
            if row["status"] == "success" and row["search_calls"] != row["resamplings"] + 1:
                raise ValueError("missing terminal search")
        else:
            snapshots[(n, k, row["seed"], row["phase"])].append(row)
            if row['initial_edge_bits'] != row['final_edge_bits'] or row['resamplings'] != 0:
                raise ValueError('snapshot search changed its graph')
    for key, rows in pairs.items():
        if len(rows) != 3 or {r["method"] for r in rows} != set(METHODS):
            raise ValueError(f"missing or duplicate method in trial {key}")
        if len({r["initial_edge_bits"] for r in rows}) != 1:
            raise ValueError("initial configurations differ")
        finished = [r for r in rows if r["status"] == "success"]
        if len({(r["resamplings"], r["trajectory_hash"], r["final_edge_bits"]) for r in finished}) > 1:
            raise ValueError("successful paired trajectories differ")
        expected_graphs = {'initial': rows[0]['initial_edge_bits']}
        if finished:
            expected_graphs['final'] = finished[0]['final_edge_bits']
        if not data['metadata'].get('skip_snapshots', False):
            for phase, bits in expected_graphs.items():
                replay = snapshots.get((*key, phase), [])
                if len(replay) != 3 or {r['method'] for r in replay} != set(METHODS):
                    raise ValueError('missing or duplicate snapshot method')
                if any(r['initial_edge_bits'] != bits for r in replay):
                    raise ValueError('snapshot does not match its paired MT graph')
    allowed_snapshots = set()
    if not data['metadata'].get('skip_snapshots', False):
        for key, rows in pairs.items():
            allowed_snapshots.add((*key, 'initial'))
            if any(r['status'] == 'success' for r in rows):
                allowed_snapshots.add((*key, 'final'))
    if set(snapshots) != allowed_snapshots:
        raise ValueError('unexpected or missing snapshot trials')
    metadata = data["metadata"]
    expected = {(n, k, metadata["seed"] + trial) for n, k in metadata["cases"]
                for trial in range(metadata["trials"])}
    if set(pairs) != expected:
        raise ValueError("dataset does not include exactly the configured MT trials")
    seen_ablation=set()
    for row in data.get('ablation_runs',[]):
        key=(row['n'],row['k'],row['seed'])
        if key in seen_ablation or key not in pairs:
            raise ValueError('duplicate or unpaired ablation graph')
        seen_ablation.add(key)
        finished=[r for r in pairs[key] if r['status']=='success']
        if (not finished or row['initial_edge_bits']!=finished[0]['final_edge_bits']
            or row['final_edge_bits']!=row['initial_edge_bits'] or row['resamplings']!=0
            or row['status']!='absent' or not row['verified']
            or certificate_first(row['n'],row['k'],row['final_edge_bits'])):
            raise ValueError('invalid ablation snapshot certificate')
        checked+=1
    expected_ablation={key for key,rows in pairs.items()
      if list(key[:2]) in [list(c) for c in metadata.get('ablation_cases',[])]
      and any(r['status']=='success' for r in rows)}
    if seen_ablation!=expected_ablation:
        raise ValueError('missing or unexpected ablation graph')
    return checked, len(pairs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    checked, trials = verify(args.results)
    print(f"Verified {checked} completed graph certificates and {trials} paired MT trials.")


if __name__ == "__main__":
    main()
