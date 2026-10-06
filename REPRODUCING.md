# Reproducing the paper artifacts

Run commands from the repository root. Use new output directories for each run.
Saved inputs and published results are never overwritten. No model API calls
are made by the supported checks.

## Main saved-generation execution

```sh
python3 core/replay.py --output-dir /tmp/memory-write-main-replay
```

Python 3.10 or newer and the standard library are sufficient. A complete run
checks 3,024 episodes across 14 policy conditions: 42,336 score rows, plus final
states and gate audits. `--limit 2` is an optional installation check of 28 rows;
it is not a full-cohort verification. See [core/README.md](core/README.md).

## Supporting experimental checks

```sh
python3 diagnostics/verify.py
python3 supplements/verify_aggregation.py
python3 supplements/replay_saved.py --output-dir /tmp/memory-write-supplement-replay
```

These use the Python standard library. The first command compares 3,444 saved
score rows. The other commands verify the supplementary aggregates and replay
296 saved authored outputs. External DSTC2 corpus access is documented in
[supplements/dstc2/README.md](supplements/dstc2/README.md).

## Appendix Table I9 classification

```sh
python3 diagnostics/variant_audit_v26/reproduce.py --output-dir /tmp/memory-write-v26-audit --verify-archived
```

This reconstructs 82 observation-level classifications from saved inputs using
the mechanical rule printed in Appendix I.1. See the diagnostic README for
the distinction between published counts and additional derived breakdowns.

## Variant-tolerant scoring and decomposition

```sh
python3 analysis_v29/rescore_variant_tolerant.py --output-dir /tmp/memory-write-variants
python3 analysis_v29/verify_results.py --results /tmp/memory-write-variants/results.json --report /tmp/memory-write-variants/verification.json
```

Python standard library only. Verifies all 42,336 main-panel exact-reference rows, the 1,152 saved ALLOW rows, and the new analysis against `analysis_v29/expected_results.json`. The tolerant scores are a separate sensitivity analysis, not replacements for the archived scores. It also checks the numbers supporting Tables 7–8 and Appendix K.

## Statistical reproduction

Use Python 3.11 or newer and an isolated environment for the additional statistics dependencies:

```sh
python3 -m venv /tmp/memory-write-statistics-env
/tmp/memory-write-statistics-env/bin/python -m pip install -r statistics/requirements.txt
/tmp/memory-write-statistics-env/bin/python statistics/reproduce.py --output /tmp/memory-write-statistics
```

Installing dependencies requires network access; once installed, the verification
uses only published local files. The [statistics guide](statistics/README.md)
identifies the exact comparisons, seeds, resampling scheme and numerical
tolerances. Existing missing intervals remain missing. The program compares
reconstructed statistics with archived results; it does not call models,
rescore responses, select a new cohort or replace historical tables.

## Paper-to-artifact map

| Paper material | Public evidence | Supported check |
|---|---|---|
| Appendix A-B: original protocol and original-family profiles | `diagnostics/primary_original/`, `diagnostics/saved_allow/` | `diagnostics/verify.py` for saved scores; original analysis sources and intervals are also archived. |
| Appendix C: configurations and resource accounting | `core/data/cohort.json`, `core/data/generation_requests.json.gz`, `diagnostics/resources/` | Recorded configuration/call metadata; no new runtime or provider benchmark. |
| Appendix D-F: contrast, boundary and public-dialogue probes | `diagnostics/contrast24/`, `diagnostics/boundary12/`, `diagnostics/public16/` | `diagnostics/verify.py` checks saved score fields. |
| Appendix G: selected complete three-repeat panel | `core/`, `diagnostics/analysis_archive/panel21/`, `statistics/` | Full core replay; portable statistical checks cover the counts/effects and available historical panel intervals described in `statistics/README.md`. |
| Appendix H: translated example cases | `core/data/cases.json.gz`, `core/data/episodes.json.gz` | Trace case identifiers to original Korean inputs and saved outputs. |
| Appendix I: hybrid admission bounds and comparisons | `core/`, `diagnostics/analysis_archive/hybrids/`, `diagnostics/analysis_archive/review_bounds/`, `statistics/` | Saved states/scores and portable archived-comparison checks. |
| Appendix I.1 / Table I9: 82 avoided reference violations | `diagnostics/variant_audit_v26/` | Row-level reconstruction of the rule stated in Appendix I.1; see its README for the command and exact scope. |
| Sections 6.1, 6.6–6.7 and Appendix J: corrected-extractor / LLM-verifier / DSTC2 diagnostics | `supplements/` | Aggregate verification and supported saved-response replay; corpus exclusions documented. |
| Sections 5.2, 6.4–6.5, Tables 7–8 and Appendix K | `analysis_v29/` | Reproduce and verify both references, fixed-proposal invariance, operation-level decomposition and 5,000-draw case-cluster intervals. |

The manuscript and appendix are distributed together with the matching editable sources. The earlier Table I9 audit remains a documented reconstruction; Appendix K adds a separate analysis without overwriting those results.

## Integrity

`verification/SHA256SUMS` covers every current repository file except itself. Downloadable assets have a separate `SHA256SUMS.txt`. `verification/SUBMISSION_ALIGNMENT.json` records the document hashes and source alignment; component-level verification records accompany the replay and analysis code. Earlier snapshots remain in Git history and historical archives.

## Scope

The main analysis clusters repeated observations within the 48 cases. The 21 entries are model configurations. Authored references are evaluation specifications, not independent human gold annotations; mechanical variant matching is a sensitivity analysis. Saved failures are retained, and unavailable external-model pairs are excluded from the corresponding paired comparison rather than scored as zero. Supporting experiments have separate samples and are not pooled with the main panel.

The supported entrypoints reproduce saved outputs and published analyses. Historical analysis scripts are supplied for inspection and can depend on their original directory layout. Available confidence intervals are identified in the statistics guide. DSTC2 source transcripts must be acquired separately as described in its component guide.

## Final-manuscript exposure audit

Run `python3 analysis_v29/exposure_sets.py --output-dir /tmp/memory-write-exposure` in a fresh directory. This supports Sections 6.2, 6.4, 7.1 and 8 by separating gate-log exposure, differing final states, validity-dependent outcome differences, score differences and missing ALLOW replays. See `analysis_v29/README.md` for definitions and validation.

## Document identity

`docs/Manuscript_anonymous.pdf` is the 23-page anonymous review manuscript. `docs/Appendix.pdf` is the matching 31-page appendix. Editable anonymous sources are in `paper_source/`. Downloadable PDF assets are identical to these files.
