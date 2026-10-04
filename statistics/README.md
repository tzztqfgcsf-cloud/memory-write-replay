# Portable verification of frozen statistics

This entrypoint reads the **existing Boolean score fields** in
`core/data/episodes.json.gz`. It recomputes the archived counts, paired effects,
and available confidence intervals and verifies them against the public CSVs.
It never invokes the evaluator, a model, or a provider. New scoring, reference
changes, model/network calls, cohort selection, and overwritten historical
analysis files are all zero. A Python audit hook rejects network access.

## Run

The statistical runner needs **Python 3.11+**, NumPy and pandas. The core policy
replay still needs only the standard library. The declared and tested versions
are in [requirements.txt](requirements.txt): NumPy 2.3.5 and pandas 2.2.3. The
release check used Python 3.12.14. Create an isolated environment outside the
repository; dependency installation can need a network, but the statistical run
is offline. Do not install into a model environment.

From the repository root:

```sh
python3 -m venv /tmp/memory-write-statistics-venv
/tmp/memory-write-statistics-venv/bin/python -m pip install -r statistics/requirements.txt
/tmp/memory-write-statistics-venv/bin/python statistics/reproduce.py --output /tmp/memory-write-statistics-results
```

Choose a new or empty output directory **outside the repository**. An existing
nonempty directory is rejected. All paths are resolved from the runner's public
repository location, so it also runs from any other working directory. No
original project paths, API keys, raw-response retrieval, or private files are
needed. Historical source strings in CSVs are provenance labels and are never
opened. Exit status 0 and `VERIFICATION.json` status `PASS` mean all requested
archived comparisons matched. Counts match exactly; CSV floating values use an
absolute tolerance of `1e-12` to allow decimal serialization/round-off.

## Comparison definitions and scope

The comparison unit is a fixed archived configuration × original authored case
× saved repetition. The fixed public cohort is 21 configurations × 48 cases ×
3 repetitions = 3,024 episodes. All 14 saved conditions and 42,336 score rows
are read. No configuration is reselected. Failures remain in their existing
denominators. The authored references are not independent human gold.

`G` is the saved two-call general review path. `CR` is the separate candidate
extraction/final-proposal path plus witness correction rule. `B` applies strict
agreement on that candidate path; `C` adds the witness exception. `N_AGREE` and
`N_LITERAL` are their normalized agreement/literal controls; `EXACT_LITERAL`
is the exact literal control. `R_LITERAL` and `R_WITNESS` apply literal/witness
rules to the saved review proposal paired with candidate-path extraction.
`R_AGREE` has the common strict APPEND rule and strict CORRECT agreement;
`R_ALLOW` preserves that APPEND rule and allows otherwise-held CORRECT decisions.
The hybrid preserves distinct review-proposal and candidate-extraction
provenance. Its historical generation accounting is separate from this
zero-call statistical run; see [core/README.md](../core/README.md).

| Output | Compared archived rows | Comparison and recipe |
|---|---:|---|
| `hybrids_paired_comparisons.csv` | 792 | Six fixed contrasts × six metrics × (21 configurations + `ALL21`); NumPy seed 20261001 |
| `review_bounds_paired_comparisons.csv` | 880 | Eight fixed contrasts × five metrics × (21 configurations + `ALL21`); NumPy seed 20261002 |
| `panel21_model_comparisons.csv` | 84 | `CR − G`, four metrics × 21 configurations; all counts/effects and the 44 originally available intervals |
| `panel21_coverage.csv` | 84 | Per-row interval availability, seed, draw count and historical source label |
| `condition_counts.csv` | 294 | 21 × 14 grouped saved-score sums; also checks five aggregated Review-bound rows against archived `SUMMARY.json` |

Hybrid contrasts (candidate minus baseline): `N_AGREE − B`,
`N_LITERAL − EXACT_LITERAL`, `N_LITERAL − C`, `R_LITERAL − G`,
`R_WITNESS − G`, `R_WITNESS − R_LITERAL`.

Review-bound contrasts: `R_AGREE − G`, `R_ALLOW − G`, `R_LITERAL − G`,
`R_WITNESS − G`, `R_ALLOW − R_AGREE`, `R_WITNESS − R_AGREE`,
`R_WITNESS − R_ALLOW`, `R_WITNESS − R_LITERAL`.

The six hybrid metrics are `positive_joint`, `correction_recovery`,
`harmful_write`, `invalid_final`, `whole_state_compliance`, and
`unsupported_write_claim`. Review bounds omit `unsupported_write_claim`;
the main panel uses the first four. Positive success is restricted to the
stored `positive_eligible` flag: 28 cases, 84 observations per configuration,
1,764 for `ALL21`. Correction recovery uses `correction_eligible`: 11 cases,
33 per configuration, 693 for `ALL21`. Other metrics retain all 48 cases:
144 per configuration and 3,024 for `ALL21`. Eligibility must be identical
across the stored policies. Condition totals sum every row, including false
scores on ineligible observations; their denominators differ from the paired
eligible-endpoint tables.

## Fixed resampling recipes

For each metric, first pair the same configuration/case/repetition, calculate
`after − before`, and average those differences inside each case. Draw 5,000
samples of the eligible cases **with replacement**, each having the original
number of cases. Retain all repeats in a case. For `ALL21`, all configurations
also remain in the case cluster; they are not resampled independently. Report
the 2.5th and 97.5th percentiles with linear interpolation. All intervals are
pointwise exploratory percentile intervals without multiplicity adjustment.

Hybrid and Review-bound recipes use `numpy.random.default_rng`, a fresh RNG
with the stated fixed seed for **each row**, sorted case IDs from pandas
`groupby`, and percentage-point output (`×100` before quantiles). The recipes
match their archived `analyze.py` implementations, but the old scripts remain
historical provenance with their original paths and one-time execution guards.

The main panel's 44 saved intervals use the historical evaluator's distinct
`random.Random(seed).choice` algorithm. Integer differences are summed inside
each sorted case and divided by its three repeats; each draw averages those
case means. Linear percentile interpolation occurs in proportion units.
The eight Gemini/Qwen `positive_joint` intervals use seed **20260927**.
The twelve Kiro configurations' three available endpoints use seed
**20260930**. Seeds are fixed from the original analyses, not selected by trying
to match the confidence limits. `interval_source` determines which declared
recipe applies; no source path is followed.

The remaining **40 main-panel intervals were absent in the archived panel**
(one positive, nine correction, nine harmful-write, and 21 invalid-final).
They remain blank; the runner does not calculate or substitute new intervals
for them. It verifies their point estimates and explicitly marks each missing
interval in `panel21_coverage.csv`. Inversion for a benefit-oriented harm metric
uses `[-high, -low]`, exactly as the original panel.

## Verification and limits

[VERIFICATION.json](VERIFICATION.json) records the release's actual standalone
run using only copied public inputs, including input/code hashes, versions,
1,756 matched archived comparison rows, and 5 matched aggregate condition rows.
The runner checks the consumed input hashes before/after, writes all fresh
results to the requested external directory, and fails on any row/value mismatch.
Its mismatch check was also exercised with a changed archived interval in an
isolated copy; the original inputs were preserved.

This verifies arithmetic on frozen scores. It does not independently validate
the evaluator, authored reference, semantic correctness, current provider
configuration, or real-user benefit. For policy execution and all 31 saved
score fields, run [core/replay.py](../core/replay.py) separately. The other
413-row saved-interval archive includes additional historical cohorts and
contrasts and is not wholly regenerated by this entrypoint. Operation-level
decision traces, sensitivity cohorts, other diagnostics and supplement-study
intervals remain their separately documented archived or executable artifacts;
they are not included in this statistics claim. A zero interval on a fixed
observed sample is not proof of zero population uncertainty, and this run
does not reevaluate any hypothesis or establish general model superiority.
