# Input-to-output guide

Use [REPRODUCING.md](REPRODUCING.md) for the commands and requirements. This guide explains what each procedure reads and produces.

| Procedure | Input | Code | Expected output |
|---|---|---|---|
| Main replay | `core/data/`: authored cases, references, saved extraction/proposals and model responses | `core/replay.py` | 3,024 episodes, 14 conditions, 42,336 matching score rows; final-state and gate-audit comparisons. |
| Variant sensitivity | Saved final states, exact and mechanical variant-tolerant references | `analysis_v29/rescore_variant_tolerant.py`, `verify_results.py` | Tables 7–8 and Appendix K; exact agreement with `expected_results.json`, plus archived-row checks. |
| Exposure sets | Saved gate logs, executed states and validity flags | `analysis_v29/exposure_sets.py` | Exposed outputs, differing states or validity, differing scores and missing ALLOW replays. |
| Supporting studies | Separate contrast, boundary, public-dialogue and saved ALLOW outputs | `diagnostics/verify.py` | 3,444 matching saved score rows. |
| Additional authored diagnostics | Corrected-extractor and verifier responses with frozen specifications | `supplements/verify_aggregation.py`, `replay_saved.py` | Frozen aggregate results and 296 matched saved authored outputs. |
| Statistical comparisons | Saved score flags and archived intervals | `statistics/reproduce.py` | Case-cluster comparisons with the archived counts and available intervals. |

## Example: correcting an earlier fact

1. An authored case contains a prior memory, a user correction and its evaluation reference.
2. Saved model outputs contain extracted facts and a proposed memory update.
3. Replay holds that proposal fixed while AGREE, ALLOW, LITERAL or WITNESS decides whether to execute it.
4. The executor produces a receipt and final state; the evaluator compares that state with the authored reference.

The [condition mapping](core/README.md#condition-codes-used-in-the-paper) connects saved codes to paper labels. Adding `--write-replayed-outputs` to the main replay writes receipts and final states alongside the score comparisons. An installation-only check with `--limit 2` covers two episodes and 28 rows.

## Reading the exposure output

Controlled-path E/D/O/S counts are **49/36/36/36**; review-proposal counts are **23/23/23/23**. Gating versus ungated review gives **127/123/127/127**: four score differences arise from generation validity while stored facts stay identical. Definitions are in [the analysis guide](analysis_v29/README.md#exposure-sets-and-the-human-review-scope).

## Actual ASR diagnostic

DSTC2 source acquisition, turn selection and local reconstruction are described in [its guide](supplements/dstc2/README.md). The original corpus is obtained separately. Result summaries are in [Additional results](docs/ADDITIONAL_RESULTS.md).
