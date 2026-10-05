# analysis_v29: variant-tolerant re-scoring and decomposition

Supports manuscript v29 (Sections 5.2, 6.4 and 6.5; Online Appendix K). Copy this directory to the
repository root and run from the root:

```sh
python3 analysis_v29/rescore_variant_tolerant.py --output-dir /tmp/v29-rescore
```

Standard library only; about 15 seconds. No model call, no policy execution: the script re-scores
the saved final states of `core/data` (3,024 episodes x 14 conditions) and
`diagnostics/saved_allow` with the archived evaluator. Exit status 0 means the exact (archived)
reference reproduced all 42,336 archived score rows (all archived evaluator fields except the
call-identifier string). The saved Allow outputs are included in the analysis, but this first
command does not compare their scores with `diagnostics/saved_allow/scores.csv`.

Run the separate verification command to compare the complete result JSON with
`expected_results.json` and re-score all 1,152 saved Allow outputs against their archived CSV:

```sh
python3 analysis_v29/verify_results.py --results /tmp/v29-rescore/results.json \
  --report /tmp/v29-rescore/verification.json
```

Exit status 0 confirms exact parsed-JSON equality, 42,336 core rows with no strict mismatch,
and 1,152 Allow rows with no mismatch across all 31 archived evaluator fields, including
call identifiers. Both commands reject an existing output directory/file so that prior
results are preserved. Neither command changes the source data or archived score tables.

It reports condition totals under both references, the reference-invariance check of
Proposition 1(ii), the exact decomposition of the complete-pipeline difference, and pooled
case-cluster intervals (5,000 draws, seed 20261005). `fig_decomposition.py` draws the
main-article decomposition figure from those counts, writing `figure_10.pdf` beside the
script (requires matplotlib and a LaTeX installation with libertine). Figure rendering is
optional and is not part of the standard-library reproduction check.

`verification.json` records the release-time verification. The supplied re-scoring and
figure scripts and `expected_results.json` retain the manuscript author's original contents;
`verify_results.py` was added to make the saved Allow comparison and complete expected-result
comparison explicit. This is retrospective analysis of saved outputs against authored
references, not independent human validation of semantic equivalence or a new efficacy run.
