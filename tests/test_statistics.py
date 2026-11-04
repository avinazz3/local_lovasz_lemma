import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from experiment_statistics import analyse,bootstrap,describe,percentile,wilson
from verify_results import verify


class StatisticalChecks(unittest.TestCase):
    def test_known_summary_and_multimodes(self):
        d=describe([1,1,3,3,7])
        self.assertEqual(d['mean'],3)
        self.assertEqual(d['median'],3)
        self.assertEqual(d['modes'],[1,3])
        self.assertEqual(d['mode_frequency'],2)
        self.assertEqual(d['iqr'],2)
        self.assertEqual(d['sd'],math.sqrt(6))
        self.assertEqual(describe([1,2,3])['modes'],[])
        self.assertEqual(describe([])['sample_size'],0)

    def test_bootstrap_constant_and_reproducibility(self):
        d=bootstrap([2]*10,100,seed=1)
        self.assertEqual(d['median_ci95'],[2,2])
        self.assertEqual(d['mean_ci95'],[2,2])
        self.assertEqual(bootstrap([1,5,8,20],100,2),bootstrap([1,5,8,20],100,2))
        self.assertIsNone(bootstrap([]))
        self.assertAlmostEqual(wilson(100,100)[0],0.9630065,places=6)
        self.assertEqual(percentile([1,2,3,4],.25),1.75)

    def test_pairing_and_independent_sample_count(self):
        rows=[]
        for seed,time in enumerate([1,10,100,1000]):
            for method,factor in [('naive',2),('branching',1),('hs_bitset',.5)]:
                rows.append(dict(phase='mt',n=5,k=3,seed=seed,method=method,status='success',
                  verified=True,lll_certified=False,total_seconds=factor*time,search_seconds=factor*time,
                  resamplings=seed,candidates_tested=10,prefixes=3,edge_checks=5,bitset_intersections=2))
        d=analyse({'metadata':{'cases':[(5,3)]},'runs':rows},100)
        pair=next(r for r in d['paired_speedups'] if r['numerator']=='naive' and r['denominator']=='branching')
        self.assertEqual(pair['median_ci95'],[2,2])
        self.assertEqual(pair['sample_size'],4)
        self.assertEqual(d['repairs'][0]['sample_size'],4) # Not 12 correlated method rows.

    def test_snapshot_tampering_is_rejected(self):
        data=json.loads((ROOT/'results/baseline/raw.json').read_text())
        snapshot=next(r for r in data['runs'] if r['phase']=='initial' and r['n']==5)
        snapshot['initial_edge_bits']=snapshot['final_edge_bits']='0'*10
        snapshot['clique']=[0,1,2];snapshot['status']='found'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'raw.json';path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'snapshot'):
                verify(path)

    def test_expanded_export(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable,str(ROOT/'scripts/expanded_experiment.py'),
              '--trials','2','--bootstrap','30','--case','5,3','--case','6,3',
              '--max-resamplings','3','--output',directory],check=True,capture_output=True,timeout=20)
            path=Path(directory)/'raw.json.gz'
            self.assertEqual(verify(path)[1],4)
            data=json.loads((Path(directory)/'statistics.json').read_text())
            self.assertTrue(any(r['repair_caps'] for r in data['summaries']))
            self.assertTrue((Path(directory)/'report.md').exists())

    def test_ablation_pairing_and_prefix_counts(self):
        from benchmark import load_results
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable,str(ROOT/'scripts/expanded_experiment.py'),
              '--trials','2','--bootstrap','30','--case','28,6','--output',directory],
              check=True,capture_output=True,timeout=20)
            path=Path(directory)/'raw.json.gz'
            self.assertEqual(verify(path),(20,2))
            data=load_results(path)
            for row in data['ablation_runs']:
                full=next(r for r in data['runs'] if r['phase']=='final'
                          and r['method']=='hs_bitset' and r['seed']==row['seed'])
                self.assertGreaterEqual(row['prefixes'],full['prefixes'])
            data['ablation_runs'][0]['verified']=False
            bad=Path(directory)/'bad.json';bad.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'ablation'):
                verify(bad)


if __name__=='__main__':unittest.main()
