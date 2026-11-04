"""Descriptive statistics and seeded percentile bootstrap, standard library only."""
import math
import random
import statistics
from collections import Counter, defaultdict


def percentile(values, probability):
    if not values:
        return None
    values = sorted(values)
    index = probability * (len(values) - 1)
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (index - low) * (values[high] - values[low])


def describe(values):
    if not values:
        return dict(sample_size=0,mean=None,median=None,modes=[],mode_frequency=0,mode_fraction=0,
                    sd=None,minimum=None,maximum=None,q1=None,q3=None,iqr=None,p95=None)
    counts = Counter(values)
    frequency = max(counts.values())
    # A continuous sample with no repeats has no repeated empirical mode.
    modes = sorted(v for v, c in counts.items() if c == frequency) if frequency > 1 else []
    return dict(sample_size=len(values), mean=statistics.mean(values), median=statistics.median(values),
                modes=modes, mode_frequency=frequency if modes else 0,
                mode_fraction=frequency / len(values) if modes else 0,
                sd=statistics.stdev(values) if len(values) > 1 else None,
                minimum=min(values), maximum=max(values),
                q1=percentile(values, .25), q3=percentile(values, .75),
                iqr=percentile(values, .75) - percentile(values, .25),
                p95=percentile(values, .95))


def bootstrap(values, repetitions=2000, seed=937):
    if not values:
        return None
    rng = random.Random(seed)
    means, medians = [], []
    for _ in range(repetitions):
        sample = rng.choices(values, k=len(values))
        means.append(sum(sample) / len(sample))
        medians.append(statistics.median(sample))
    return dict(mean_ci95=[percentile(means, .025), percentile(means, .975)],
                median_ci95=[percentile(medians, .025), percentile(medians, .975)],
                repetitions=repetitions, bootstrap_seed=seed, method='percentile bootstrap by seed')


def wilson(successes, trials):
    if not trials:
        return None
    z = 1.959963984540054
    p = successes / trials
    denominator = 1 + z*z/trials
    centre = (p + z*z/(2*trials)) / denominator
    half = z*math.sqrt(p*(1-p)/trials + z*z/(4*trials*trials)) / denominator
    return [max(0, centre-half), min(1, centre+half)]


def analyse(data, repetitions=2000):
    groups = defaultdict(list)
    paired = defaultdict(dict)
    for row in data['runs']:
        groups[(row['phase'], row['n'], row['k'], row['method'])].append(row)
        if row['phase'] == 'mt':
            paired[(row['n'],row['k'],row['seed'])][row['method']] = row
    summaries=[]
    for index, ((phase,n,k,method), rows) in enumerate(sorted(groups.items())):
        completed = [r for r in rows if r['verified']]
        out=dict(phase=phase,n=n,k=k,method=method,trials=len(rows),completed=len(completed),
                 timeouts=sum(r['status']=='timeout' for r in rows),
                 repair_caps=sum(r['status']=='resampling_limit' for r in rows),
                 lll_certified=rows[0]['lll_certified'], completion_ci95=wilson(len(completed),len(rows)))
        for field in ('total_seconds','search_seconds','resamplings','candidates_tested','prefixes',
                      'edge_checks','bitset_intersections'):
            out[field]=describe([r[field] for r in completed])
        if phase=='mt':
            out['total_seconds'].update(bootstrap([r['total_seconds'] for r in completed],repetitions,937+index) or {})
        summaries.append(out)
    ratios=defaultdict(list)
    for (n,k,seed), group in paired.items():
        if len(group)!=3 or not all(r['verified'] for r in group.values()):
            continue
        for numerator,denominator in (('naive','branching'),('naive','hs_bitset'),('branching','hs_bitset')):
            ratios[(n,k,numerator,denominator)].append(group[numerator]['total_seconds']/group[denominator]['total_seconds'])
    speedups=[]
    for index,((n,k,numerator,denominator),values) in enumerate(sorted(ratios.items())):
        speedups.append(dict(n=n,k=k,numerator=numerator,denominator=denominator,
                             **describe(values),**bootstrap(values,repetitions,1937+index)))
    repairs=[]
    for n,k in sorted(data['metadata']['cases']):
        # One count per graph, never treat the three identical trajectories as independent samples.
        values=[g['naive']['resamplings'] for (a,b,s),g in paired.items()
                if (a,b)==(n,k) and len(g)==3 and all(r['verified'] for r in g.values())]
        repairs.append(dict(n=n,k=k,**describe(values)))
    ablation=[]
    by_graph=defaultdict(dict)
    for r in data.get('ablation_runs',[]):
        by_graph[(r['n'],r['k'],r['seed'])]['without']=r
    for r in data['runs']:
        if r['phase']=='final' and r['method']=='hs_bitset':
            by_graph[(r['n'],r['k'],r['seed'])]['with']=r
    cases=sorted({(a,b) for a,b,_ in by_graph})
    for n,k in cases:
        pairs=[g for (a,b,s),g in by_graph.items() if (a,b)==(n,k) and len(g)==2
               and all(r['verified'] for r in g.values())]
        if pairs:
            ablation.append(dict(n=n,k=k,trials=len(pairs),
              with_prefixes=describe([p['with']['prefixes'] for p in pairs]),
              without_prefixes=describe([p['without']['prefixes'] for p in pairs]),
              prefix_ratio=describe([p['without']['prefixes']/p['with']['prefixes'] for p in pairs])))
    return dict(summaries=summaries,paired_speedups=speedups,repairs=repairs,ablation=ablation,
                bootstrap_repetitions=repetitions,independent_unit='one graph seed within an instance')
