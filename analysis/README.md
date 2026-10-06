# Variant-tolerant re-scoring and decomposition

Supports manuscript Sections 5.2, 6.4 and 6.5 and Online Appendix K. Commands are in [REPRODUCING.md](../REPRODUCING.md#variant-tolerant-scoring-and-decomposition).

Standard library only. No model call, no policy execution: the script re-scores
the saved final states of `core/data` (3,024 episodes x 14 conditions) and
`diagnostics/saved_allow` with the archived evaluator. Exit status 0 means the exact (archived)
reference reproduced all 42,336 archived score rows (all archived evaluator fields except the
call-identifier string). The saved Allow outputs are included in the analysis, but this first
command does not compare their scores with `diagnostics/saved_allow/scores.csv`.

Run the separate verification command to compare the complete result JSON with
`expected_results.json` and re-score all 1,152 saved Allow outputs against their archived CSV.

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
figure scripts and `expected_results.json` retain the archived analysis scripts and expected results;
`verify_results.py` was added to make the saved Allow comparison and complete expected-result
comparison explicit. Matching conventions and interpretation are summarized in [REPRODUCING.md](../REPRODUCING.md#scope).

## Exposure sets and the human-review scope

`exposure_sets.py` answers a different question from the re-scoring: on which outputs could a
human judgment of the executed state change a rule comparison? The command is in [REPRODUCING.md](../REPRODUCING.md#final-manuscript-exposure-audit).

For the controlled-path rules, the review-proposal rules, and gating versus not gating, it
reports E, the exposed outputs read from the saved gate log before scoring; D, the outputs
with different executed fact states; O, the outputs with different states or generation
validity (`D_state_or_validity`); and S, the outputs whose endpoints differ under at least one
reference (the 36, 23, and 127 of the re-scoring). Exit status 0 confirms S within O within E
for every family. The archived endpoints require generation validity in addition to state
conformity; the proposed action is shared in these fixed-proposal comparisons.

For gating versus not gating, four invalid-extraction outputs have the same stored facts but
different validity and endpoint scores. Accordingly, S has 127 outputs while D has 123;
`check_S_within_D` remains false as an explicit diagnostic, and
`validity_only_score_difference` reports four. O has 127. For the controlled-path and
review-proposal correction rules, both the state-only and state-or-validity inclusion checks
pass (E/D/O/S = 49/36/36/36 and 23/23/23/23).

`D_not_in_S` counts different states that both references score alike.
`E_with_rule_not_replayed` counts exposed outputs on which a compared rule (Allow on four
configurations, 14 outputs) was not replayed. `review_set.csv` lists every output in E, D, O,
or S with these flags. Rows with `review = 1` conservatively include state-or-validity
differences and exposed outputs with a missing rule: 48 controlled-path, 23 review-proposal,
and 127 gating outputs. The manuscript's proposed starting set of all 49 controlled-path
exposures is conservative; the one fully replayed state tie is listed with `review = 0`.
No saved outputs, evaluator definitions, or archived scores are changed by this correction.
