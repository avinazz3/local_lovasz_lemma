# Expanded Ramsey experiment

100 new seeds per instance; 12 instances. Each seed is the sampling unit, not each repeated method/snapshot invocation.

## Full-run runtime distributions (milliseconds)

| n | k | Method | Complete | Mean | Median | SD | IQR | 95% CI for mean |
|---:|---:|---|---:|---:|---:|---:|---:|---|
|4|4|branching|100/100|0.0028109|0.002394|0.0025826|0.00022325|0.0024522–0.0034099|
|4|4|hs_bitset|100/100|0.0034943|0.00335|0.00056022|0.00029025|0.003398–0.0036135|
|4|4|naive|100/100|0.0036397|0.0024185|0.0095361|0.000189|0.0024709–0.0057003|
|5|3|branching|100/100|0.015689|0.009259|0.017023|0.013748|0.012614–0.019094|
|5|3|hs_bitset|100/100|0.01994|0.0096795|0.031438|0.013427|0.014403–0.026518|
|5|3|naive|100/100|0.014169|0.008042|0.016524|0.011685|0.011023–0.017473|
|7|5|branching|100/100|0.0068305|0.003675|0.026182|0.00028325|0.0037258–0.012542|
|7|5|hs_bitset|100/100|0.01074|0.004432|0.037553|0.000361|0.0046895–0.018941|
|7|5|naive|100/100|0.0037467|0.0036705|0.00029007|0.0002425|0.0036946–0.0038089|
|12|4|branching|100/100|4.0905|3.2264|3.7892|3.937|3.4195–4.8686|
|12|4|hs_bitset|100/100|2.3042|1.7151|2.1281|2.3013|1.9064–2.7246|
|12|4|naive|100/100|5.5888|4.5116|5.113|5.1535|4.6245–6.6179|
|13|6|branching|100/100|0.0091745|0.007622|0.009989|0.0007745|0.0077266–0.011411|
|13|6|hs_bitset|100/100|0.0088573|0.005789|0.026322|0.000305|0.0058446–0.01453|
|13|6|naive|100/100|0.02405|0.015509|0.046571|0.0014522|0.016903–0.034448|
|16|5|branching|100/100|0.041365|0.028298|0.072459|0.016594|0.030781–0.058352|
|16|5|hs_bitset|100/100|0.016596|0.012589|0.013582|0.0057465|0.014132–0.019367|
|16|5|naive|100/100|0.11548|0.097482|0.072866|0.074928|0.10247–0.13086|
|20|5|branching|100/100|2.5094|1.9166|2.3761|2.6809|2.0818–2.9953|
|20|5|hs_bitset|100/100|0.84108|0.58817|0.82649|0.81683|0.68812–1.0235|
|20|5|naive|100/100|17.555|13.029|17.593|16.114|14.337–21.292|
|22|7|branching|100/100|0.044616|0.031783|0.039074|0.0056935|0.037936–0.05294|
|22|7|hs_bitset|100/100|0.010099|0.009489|0.0024127|0.00080425|0.0097083–0.010648|
|22|7|naive|100/100|1.0535|0.85229|0.86828|0.19384|0.91496–1.2355|
|24|6|branching|100/100|0.10207|0.077947|0.066143|0.055424|0.090005–0.11607|
|24|6|hs_bitset|100/100|0.022632|0.018152|0.017106|0.0073595|0.019763–0.026332|
|24|6|naive|100/100|1.7957|1.5055|1.0791|1.0248|1.5945–2.0258|
|28|6|branching|100/100|0.3498|0.2911|0.19609|0.22008|0.31557–0.39042|
|28|6|hs_bitset|100/100|0.088564|0.048423|0.20446|0.040656|0.059438–0.13497|
|28|6|naive|100/100|12.958|10.181|10.38|8.9407|11.055–15.177|
|32|7|branching|100/100|0.25045|0.20404|0.18357|0.12791|0.21803–0.29193|
|32|7|hs_bitset|100/100|0.029352|0.025087|0.017198|0.0092157|0.026551–0.033372|
|32|7|naive|100/100|27.606|25.835|11.792|16.791|25.364–29.989|
|36|8|branching|100/100|0.26118|0.22928|0.088132|0.08448|0.2445–0.2804|
|36|8|hs_bitset|100/100|0.027752|0.02327|0.015311|0.0021455|0.025122–0.030889|
|36|8|naive|100/100|152.21|143.66|30.134|16.998|146.82–158.31|

## Repairs per independent graph

| n | k | Complete triplets | Mean | Median | Modes | Modal frequency | SD | IQR | Range |
|---:|---:|---:|---:|---:|---|---|---:|---:|---|
|4|4|100|0.05|0|0|95/100|0.21904|0|0–1|
|5|3|100|43.76|23|29|6/100|52.793|51.5|1–257|
|7|5|100|0.04|0|0|96/100|0.19695|0|0–1|
|12|4|100|4666.2|3475|637|2/100|4153.6|4257.5|93–21557|
|13|6|100|0.03|0|0|97/100|0.17145|0|0–1|
|16|5|100|7.17|6|2|13/100|5.4477|7|0–28|
|20|5|100|670.42|504|no repeated mode|0/100|650.01|651.75|11–3323|
|22|7|100|0.12|0|0|88/100|0.3266|0|0–1|
|24|6|100|3.96|3|3|22/100|3.3026|3|0–20|
|28|6|100|16.28|13|10|8/100|11.794|13.25|1–57|
|32|7|100|1.48|1|0|31/100|1.4176|2|0–6|
|36|8|100|0.11|0|0|90/100|0.3451|0|0–2|

## Paired speedup (total time)

| n | k | Comparison | Complete pairs | Median ratio | Bootstrap 95% CI |
|---:|---:|---|---:|---:|---|
|4|4|branching / hs_bitset|100|0.71166|0.7028–0.72019|
|4|4|naive / branching|100|1.0127|0.9982–1.0222|
|4|4|naive / hs_bitset|100|0.72129|0.71011–0.72656|
|5|3|branching / hs_bitset|100|0.95605|0.93159–0.9862|
|5|3|naive / branching|100|0.86829|0.85863–0.8813|
|5|3|naive / hs_bitset|100|0.83964|0.80365–0.84865|
|7|5|branching / hs_bitset|100|0.83184|0.82111–0.84312|
|7|5|naive / branching|100|1.0041|0.99177–1.0086|
|7|5|naive / hs_bitset|100|0.83813|0.82205–0.85039|
|12|4|branching / hs_bitset|100|1.7874|1.7469–1.8344|
|12|4|naive / branching|100|1.3966|1.3788–1.4291|
|12|4|naive / hs_bitset|100|2.5005|2.4085–2.5727|
|13|6|branching / hs_bitset|100|1.3234|1.2938–1.3484|
|13|6|naive / branching|100|2.0345|2.0122–2.0701|
|13|6|naive / hs_bitset|100|2.7013|2.6638–2.7398|
|16|5|branching / hs_bitset|100|2.1868|2.0927–2.2641|
|16|5|naive / branching|100|3.2093|3.122–3.3918|
|16|5|naive / hs_bitset|100|7.1061|6.752–7.5173|
|20|5|branching / hs_bitset|100|3.1877|3.0871–3.3214|
|20|5|naive / branching|100|7.1614|6.9404–7.4053|
|20|5|naive / hs_bitset|100|23.065|22.296–23.705|
|22|7|branching / hs_bitset|100|3.3252|3.2741–3.4128|
|22|7|naive / branching|100|26.157|25.745–28.002|
|22|7|naive / hs_bitset|100|90.288|87.601–93.168|
|24|6|branching / hs_bitset|100|4.358|4.0623–4.5094|
|24|6|naive / branching|100|17.724|17.117–18.671|
|24|6|naive / hs_bitset|100|78.92|74.609–88.262|
|28|6|branching / hs_bitset|100|5.8388|5.5153–6.0148|
|28|6|naive / branching|100|36.665|34.476–38.174|
|28|6|naive / hs_bitset|100|221.49|205.4–229.04|
|32|7|branching / hs_bitset|100|7.7084|7.3068–8.0131|
|32|7|naive / branching|100|123.45|117.8–129.67|
|32|7|naive / hs_bitset|100|985.67|905.42–1068.8|
|36|8|branching / hs_bitset|100|9.3992|9.0937–9.9232|
|36|8|naive / branching|100|644.02|620.69–667.99|
|36|8|naive / hs_bitset|100|6135.8|6034–6255.9|

## Bitset cardinality-pruning ablation

Only the two candidate-count tests are disabled in the alternative binary; all other C++ search code is unchanged. Comparison uses identical final graphs and counts partial cliques, avoiding timer noise.

| n | k | Graphs | Median prefixes without pruning | Median prefixes with pruning | Median paired reduction |
|---:|---:|---:|---:|---:|---:|
|28|6|100|1594.0|487.0|3.2666|
|36|8|100|4727.5|727.5|6.4841|

## Statistical interpretation

IQR is the 75th minus 25th percentile (linear interpolation). SD is the sample standard deviation. Modes retain all tied repeated values; modal frequencies expose weak/ambiguous modes. Exact timing modes are retained in JSON but not interpreted: repeated nanosecond values can reflect clock quantization. Discrete repair-count modes are more meaningful.

Intervals use 2000 seeded percentile bootstrap resamples within each instance. Paired speedup resamples one per-seed ratio, preserving method pairing. Completion intervals use the Wilson method. Intervals are pointwise, not simultaneous across all comparisons. They quantify sampling variability on this machine, not uncertainty across machines or a guaranteed asymptotic speedup.

Capped runs are not assigned a fake completed runtime. Descriptive runtime and paired-ratio summaries use completed runs/triplets, and completion counts expose exclusions. With censoring these estimates describe the completed subset. No pooling of the 3 methods or 3 phases increases the independent sample size.
