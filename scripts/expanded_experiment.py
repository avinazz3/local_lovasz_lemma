#!/usr/bin/env python3
"""Larger paired study with uncertainty estimates and a bitset pruning ablation."""
import argparse
import gzip
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark import METHODS, ROOT, invoke, write_csv
from experiment_statistics import analyse
from verify_results import verify

CASES=[(4,4),(7,5),(13,6),(22,7),(36,8),(5,3),(12,4),(16,5),(20,5),(24,6),(28,6),(32,7)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_tables(directory, stats, metadata):
    def f(value,scale=1):
        return '—' if value is None else f'{scale*value:.5g}'
    flattened=[]
    for row in stats['summaries']:
        flat={k:v for k,v in row.items() if not isinstance(v,dict)}
        for key,value in row.items():
            if isinstance(value,dict):
                for statistic,number in value.items():
                    flat[key+'_'+statistic]=json.dumps(number) if isinstance(number,list) else number
        flattened.append(flat)
    write_csv(directory/'summary.csv',flattened)
    write_csv(directory/'paired_speedups.csv',stats['paired_speedups'])
    write_csv(directory/'repairs.csv',stats['repairs'])
    lines=['# Expanded Ramsey experiment','',
      f"{metadata['trials']} new seeds per instance; {len(metadata['cases'])} instances. "
      'Each seed is the sampling unit, not each repeated method/snapshot invocation.','',
      '## Full-run runtime distributions (milliseconds)','',
      '| n | k | Method | Complete | Mean | Median | SD | IQR | 95% CI for mean |',
      '|---:|---:|---|---:|---:|---:|---:|---:|---|']
    for row in stats['summaries']:
        if row['phase']!='mt': continue
        d=row['total_seconds'];ci=d.get('mean_ci95')
        lines.append(f"|{row['n']}|{row['k']}|{row['method']}|{row['completed']}/{row['trials']}|"
          + '|'.join(f(d[x],1000) for x in ('mean','median','sd','iqr'))
          + ('|'+f(ci[0],1000)+'–'+f(ci[1],1000)+'|' if ci else '|—|'))
    lines += ['', '## Repairs per independent graph','',
      '| n | k | Complete triplets | Mean | Median | Modes | Modal frequency | SD | IQR | Range |',
      '|---:|---:|---:|---:|---:|---|---|---:|---:|---|']
    for d in stats['repairs']:
        modes=', '.join(str(x) for x in d['modes']) or 'no repeated mode'
        lines.append(f"|{d['n']}|{d['k']}|{d['sample_size']}|{f(d['mean'])}|{f(d['median'])}|"
          f"{modes}|{d['mode_frequency']}/{d['sample_size']}|{f(d['sd'])}|{f(d['iqr'])}|{f(d['minimum'])}–{f(d['maximum'])}|")
    lines += ['', '## Paired speedup (total time)','',
      '| n | k | Comparison | Complete pairs | Median ratio | Bootstrap 95% CI |',
      '|---:|---:|---|---:|---:|---|']
    for d in stats['paired_speedups']:
        ci=d['median_ci95']
        lines.append(f"|{d['n']}|{d['k']}|{d['numerator']} / {d['denominator']}|{d['sample_size']}|"
          f"{d['median']:.5g}|{ci[0]:.5g}–{ci[1]:.5g}|")
    lines += ['', '## Bitset cardinality-pruning ablation','',
      'Only the two candidate-count tests are disabled in the alternative binary; all other C++ search code is unchanged. '
      'Comparison uses identical final graphs and counts partial cliques, avoiding timer noise.','',
      '| n | k | Graphs | Median prefixes without pruning | Median prefixes with pruning | Median paired reduction |',
      '|---:|---:|---:|---:|---:|---:|']
    for d in stats['ablation']:
        lines.append(f"|{d['n']}|{d['k']}|{d['trials']}|{d['without_prefixes']['median']}|"
          f"{d['with_prefixes']['median']}|{d['prefix_ratio']['median']:.5g}|")
    lines += ['', '## Statistical interpretation','',
      'IQR is the 75th minus 25th percentile (linear interpolation). SD is the sample standard deviation. '
      'Modes retain all tied repeated values; modal frequencies expose weak/ambiguous modes. '
      'Exact timing modes are retained in JSON but not interpreted: repeated nanosecond values can reflect clock quantization. '
      'Discrete repair-count modes are more meaningful.','',
      f"Intervals use {metadata['bootstrap_repetitions']} seeded percentile bootstrap resamples within each instance. "
      'Paired speedup resamples one per-seed ratio, preserving method pairing. '
      'Completion intervals use the Wilson method. Intervals are pointwise, not simultaneous across all comparisons. '
      'They quantify sampling variability on this machine, not uncertainty across machines or a guaranteed asymptotic speedup.','',
      'Capped runs are not assigned a fake completed runtime. Descriptive runtime and paired-ratio summaries use '
      'completed runs/triplets, and completion counts expose exclusions. With censoring these estimates describe '
      'the completed subset. No pooling of the 3 methods or 3 phases increases the independent sample size.','']
    (directory/'report.md').write_text('\n'.join(lines))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials',type=int,default=100)
    parser.add_argument('--seed',type=int,default=20270000)
    parser.add_argument('--seconds',type=float,default=5)
    parser.add_argument('--max-resamplings',type=int,default=100000)
    parser.add_argument('--bootstrap',type=int,default=2000)
    parser.add_argument('--case',action='append')
    parser.add_argument('--output',type=Path,default=ROOT/'results/expanded')
    args=parser.parse_args()
    cases=[tuple(map(int,s.split(','))) for s in args.case] if args.case else CASES
    if (args.trials<2 or args.bootstrap<20 or args.seconds<=0 or args.seed<1
        or args.seed+args.trials>2**64 or args.max_resamplings<0 or len(set(cases))!=len(cases)
        or any(len(c)!=2 or not 2<=c[1]<=c[0]<=64 for c in cases)):
        parser.error('invalid sample count, budget, bootstrap count or case')
    binary=ROOT/'build/ramsey_experiment'; alternative=ROOT/'build/ramsey_no_pruning'
    if not binary.is_file() or not alternative.is_file():
        parser.error('run make and make build/ramsey_no_pruning first')
    args.output.mkdir(parents=True,exist_ok=True)
    for filename in ('raw.json.gz','statistics.json','summary.csv','paired_speedups.csv','repairs.csv','report.md'):
        (args.output/filename).unlink(missing_ok=True)
    affinity=None
    try:
        affinity=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{affinity})
    except (AttributeError,OSError):
        affinity=None
    sources=[ROOT/'src/ramsey.cpp',ROOT/'Makefile',ROOT/'scripts/benchmark.py',Path(__file__),
             ROOT/'scripts/experiment_statistics.py',ROOT/'scripts/verify_results.py']
    metadata=dict(complete=False,utc_timestamp=datetime.now(timezone.utc).isoformat(),
      cases=cases,trials=args.trials,seed=args.seed,seconds=args.seconds,max_resamplings=args.max_resamplings,
      skip_snapshots=False,bootstrap_repetitions=args.bootstrap,affinity_cpu=affinity,
      ablation_cases=[c for c in cases if c in ((28,6),(36,8))],
      platform=platform.platform(),python=sys.version,
      compiler=subprocess.check_output(['c++','--version'],text=True).splitlines()[0],
      build_command=(ROOT/'build/build_command.txt').read_text().strip(),
      executable_sha256=digest(binary),ablation_executable_sha256=digest(alternative),
      source_sha256={str(p.relative_to(ROOT)):digest(p) for p in sources},
      schedule='all instance/seed triplets shuffled; fresh randomized method order per triplet',
      ablation='candidate-count pruning disabled; measured on final (28,6) and (36,8) graphs')
    cpuinfo=Path('/proc/cpuinfo')
    metadata['cpu']=next((l.split(':',1)[1].strip() for l in cpuinfo.read_text().splitlines()
                          if l.startswith('model name')),platform.processor()) if cpuinfo.exists() else platform.processor()
    (args.output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    # Warm-up draws are disjoint from measured seeds and excluded from all summaries.
    for n,k in cases:
        for method in METHODS:
            invoke(binary,n,k,args.seed-1,method,args.seconds,args.max_resamplings)
    metadata['warmup_invocations']=3*len(cases)
    schedule=[(n,k,args.seed+i) for n,k in cases for i in range(args.trials)]
    order_rng=random.Random(81273);order_rng.shuffle(schedule)
    runs=[];ablations=[]
    partial=args.output/'measurements.partial.jsonl'
    with partial.open('w') as log:
        for number,(n,k,seed) in enumerate(schedule,1):
            order=list(METHODS);order_rng.shuffle(order)
            paired={}
            for method in order:
                row=invoke(binary,n,k,seed,method,args.seconds,args.max_resamplings)
                row['phase']='mt';paired[method]=row;runs.append(row)
                log.write(json.dumps(row)+'\n')
            if len({r['initial_edge_bits'] for r in paired.values()})!=1:
                raise AssertionError('initial graph mismatch')
            completed=[r for r in paired.values() if r['status']=='success']
            if len({(r['resamplings'],r['trajectory_hash'],r['final_edge_bits']) for r in completed})>1:
                raise AssertionError('repair trajectory mismatch')
            snapshots={'initial':paired['naive']['initial_edge_bits']}
            if completed:snapshots['final']=completed[0]['final_edge_bits']
            for phase,bits in snapshots.items():
                for method in order:
                    row=invoke(binary,n,k,seed,method,args.seconds,args.max_resamplings,bits)
                    row['phase']=phase;runs.append(row);log.write(json.dumps(row)+'\n')
            if (n,k) in ((28,6),(36,8)) and 'final' in snapshots:
                row=invoke(alternative,n,k,seed,'hs_bitset',args.seconds,args.max_resamplings,snapshots['final'])
                row['phase']='ablation';ablations.append(row);log.write(json.dumps(row)+'\n')
            log.flush()
            if number%25==0 or number==len(schedule):
                print(f'{number}/{len(schedule)} paired trials completed',flush=True)
    metadata['complete']=True
    data=dict(schema_version=1,metadata=metadata,runs=runs,ablation_runs=ablations)
    temporary=args.output/'raw.json.gz.tmp'
    with gzip.open(temporary,'wt',compresslevel=6) as stream:json.dump(data,stream,separators=(',',':'))
    temporary.replace(args.output/'raw.json.gz')
    checked,trials=verify(args.output/'raw.json.gz')
    print(f'Verified {checked} certificates and {trials} paired trials',flush=True)
    stats=analyse(data,args.bootstrap)
    (args.output/'statistics.json').write_text(json.dumps(stats,indent=2)+'\n')
    write_tables(args.output,stats,metadata)
    (args.output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    partial.unlink()
    print(f'Saved {len(runs)} main and {len(ablations)} ablation measurements to {args.output}',flush=True)


if __name__=='__main__':main()
