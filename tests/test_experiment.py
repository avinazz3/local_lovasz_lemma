#!/usr/bin/env python3
"""Exhaustive small graphs, paired repairs, certificates and limits."""
import itertools
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from benchmark import METHODS, certificate_first, exhaustive_first, lll_condition
from verify_results import verify

BINARY = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build/ramsey_experiment"
if len(sys.argv) > 1:
    del sys.argv[1]


def run(n, k, method, *extra):
    process = subprocess.run([str(BINARY), "--n", str(n), "--k", str(k), "--method", method,
                              "--seed", "71", "--seconds", "2", *map(str, extra)],
                             text=True, capture_output=True, check=True, timeout=10)
    return json.loads(process.stdout)


class Correctness(unittest.TestCase):
    def check_graph(self, n, k, bits):
        expected = exhaustive_first(n, k, bits)
        self.assertEqual(certificate_first(n, k, bits), expected)
        for method in METHODS:
            row = run(n, k, method, "--search-only", "--bits", bits)
            self.assertEqual(row["clique"], expected, (n, k, method, bits))
            self.assertEqual(row["status"], "found" if expected else "absent")

    def test_all_four_vertex_colourings(self):
        for number in range(2 ** math.comb(4, 2)):
            bits = f"{number:06b}"
            for k in (2, 3, 4):
                self.check_graph(4, k, bits)

    def test_random_small_graphs(self):
        rng = random.Random(191)
        for n in range(5, 10):
            for _ in range(8):
                bits = "".join(str(rng.randrange(2)) for _ in range(math.comb(n, 2)))
                for k in (3, 4, min(n, 5)):
                    self.check_graph(n, k, bits)

    def test_triangle_free_five_cycle(self):
        red = {tuple(sorted((i, (i + 1) % 5))) for i in range(5)}
        bits = "".join(str(int(edge in red)) for edge in itertools.combinations(range(5), 2))
        self.check_graph(5, 3, bits)

    def test_vertex_63_and_full_width_shifts(self):
        # A random bipartite two-colouring and high-index target exercise bit 63.
        bits = "".join(str(int(u // 32 == v // 32)) for u, v in itertools.combinations(range(64), 2))
        expected = certificate_first(64, 32, bits)
        self.assertEqual(expected, list(range(32)))
        for method in ("branching", "hs_bitset"):
            self.assertEqual(run(64, 32, method, "--search-only", "--bits", bits)["clique"], expected)
        # A single-colour K64 forces the extension through vertex 63.
        self.assertEqual(run(64, 64, "hs_bitset", "--search-only", "--bits", "1" * 2016)["clique"], list(range(64)))

    def test_identical_resampling_trajectories(self):
        for n, k in ((5, 3), (12, 4), (16, 5)):
            rows = [run(n, k, method) for method in METHODS]
            self.assertTrue(all(r["status"] == "success" for r in rows))
            self.assertEqual(len({(r["resamplings"], r["trajectory_hash"], r["final_edge_bits"])
                                  for r in rows}), 1)
            for row in rows:
                self.assertEqual(exhaustive_first(n, k, row["final_edge_bits"]), [])
                self.assertEqual(row["search_calls"], row["resamplings"] + 1)

    def test_impossible_instance_and_caps(self):
        # R(3,3)=6; a capped run must not be mistaken for success.
        for method in METHODS:
            row = run(6, 3, method, "--max-resamplings", "10")
            self.assertEqual(row["status"], "resampling_limit")
            self.assertEqual(row["resamplings"], 10)
            row = run(64, 2, method, "--seconds", "0.000000001")
            self.assertEqual(row["status"], "timeout")
        self.assertEqual(run(4, 3, "naive", "--bits", "0" * 6,
                             "--max-resamplings", "0")["status"], "resampling_limit")

    def test_finite_lll_condition(self):
        self.assertTrue(lll_condition(13, 6)["lll_certified"])
        self.assertFalse(lll_condition(6, 3)["lll_certified"])

    def test_invalid_inputs(self):
        for args in (("--n", "65"), ("--k", "1"), ("--method", "missing"),
                     ("--bits", "000"), ("--seconds", "nan"), ("--seed", "-1")):
            process = subprocess.run([str(BINARY), "--n", "5", "--k", "3", *args], capture_output=True)
            self.assertNotEqual(process.returncode, 0)

    def test_benchmark_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable, str(ROOT / "scripts/benchmark.py"), "--binary", str(BINARY),
                            "--case", "5,3", "--case", "6,3", "--trials", "1", "--max-resamplings", "10",
                            "--output", directory], check=True, capture_output=True, timeout=20)
            raw = json.loads((Path(directory) / "raw.json").read_text())
            self.assertTrue(any(r["status"] == "resampling_limit" for r in raw["runs"]))
            self.assertTrue(all(not r["verified"] for r in raw["runs"] if r["status"] == "resampling_limit"))
            for name in ("runs.csv", "summary.csv", "summary.json", "report.md"):
                self.assertTrue((Path(directory) / name).stat().st_size)
            self.assertEqual(verify(Path(directory) / "raw.json")[1], 2)
            raw["runs"][0]["verified"] = not raw["runs"][0]["verified"]
            (Path(directory) / "raw.json").write_text(json.dumps(raw))
            with self.assertRaises(ValueError):
                verify(Path(directory) / "raw.json")
            raw["runs"][0]["verified"] = not raw["runs"][0]["verified"]
            raw["metadata"]["complete"] = False
            (Path(directory) / "raw.json").write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError, "incomplete"):
                verify(Path(directory) / "raw.json")


if __name__ == "__main__":
    unittest.main()
