# Additional diagnostic results

These exploratory experiments were collected separately from the main three-repeat study. They are not included in the current manuscript or online appendix. Both improvements and losses are reported here; their samples and endpoints are not pooled with the main panel.

## Extraction intervention

On five retrospectively selected Gemini 2.5 Flash correction cases, the original instruction completed 1/5 corrections and the amended instruction completed 5/5. Four AGREE holds disappeared, with no reference violations in either arm. CT01 succeeded under both newly collected instructions. The amendment required an affirmed correction to appear in the extracted fact lists. Saved proposals, the gate, executor and evaluation specification were fixed.

The complete 48-case Gemini 3.8 Flash comparison showed no difference: strict corrections 11/11 and whole-state conformity 47/48 under both instructions. The initial Flash 2.5 paired subset had 15 cases: whole-state conformity 14/15 to 15/15 and strict corrections 3/4 to 4/4. The full planned Flash 2.5 matrix remains incomplete. Completing the five selected pairs does not turn it into an independent confirmation.

Sources: [focal results](../supplements/authored/paper_focal5_completion_20261004/FOCAL_RESULT.json), [response provenance](../supplements/authored/focal5_provenance.json), [collection summary](../supplements/authored/paper_mechanism_validation_20261004/SUMMARY.json).

## LLM admission verifier

Gemini 3.1 Pro approved or held 144 saved REVIEW proposals, one selected repetition of 48 cases from each generator. It did not rewrite proposals and was not fine-tuned. Each cell below is REVIEW / REVIEW+WITNESS / LLM verifier.

| Proposal generator | Positive changes /28 | Reference violations /48 | Whole-state conformity /48 |
|---|---|---|---|
| Gemini 2.5 Flash | 27 / 27 / 27 | 2 / 1 / 1 | 46 / 47 / 47 |
| Gemini 3.8 Flash | 28 / 27 / 28 | 0 / 0 / 0 | 48 / 47 / 48 |
| Qwen3 14B | 24 / 24 / 24 | 4 / 3 / 1 | 42 / 43 / 44 |

All three conditions completed 11/11 corrections for each generator. The key paired intervals include zero. The verifier required 144 additional historical calls, with mean provider-reported stage time 4.39 seconds. This is distinct from deterministic replay's zero additional model calls.

Sources: [summary](../supplements/authored/paper_mechanism_validation_20261004/SUMMARY.json), [paired intervals](../supplements/authored/paper_mechanism_validation_20261004/paired_intervals.csv).

## Actual ASR alternatives from DSTC2

The diagnostic selected one turn from each of 48 English restaurant dialogues (41 caller clusters), with 433 actual ASR alternatives and a supplied previous human-derived goal state. It comprises 24 goal revisions, 12 denials without replacement and 12 reference-enriched ASR cases. Current reference labels were held out from generation. The selected sample is a component diagnostic, not the full DSTC2 tracking benchmark.

| Pro policy | Required changes /36 | Newly wrong writes /48 | Complete-goal conformity /48 |
|---|---:|---:|---:|
| ALLOW | 23 | 3 | 33 |
| AGREE | 6 | 0 | 18 |
| LITERAL | 6 | 1 | 17 |
| WITNESS | 6 | 0 | 18 |

WITNESS minus ALLOW: complete-goal conformity **−31.25 percentage points** (caller-cluster 95% interval **[−45.83, −16.33]**); required-change completion **−47.22 points [−62.86, −32.26]**; newly wrong writes **−6.25 points [−13.46, 0.00]**. Of 20 held corrections, 17 were reference-correct and three were wrong. Reduced writing violations therefore came with substantial lost correct changes. The missing-fact pattern diagnosed in the five authored cases did not occur here; holds involved differing extracted values or incomplete support across actual ASR alternatives.

Gemini 3.8 Flash completed only 22/48 pairs. On that separate partial sample, ALLOW to WITNESS changed complete-goal conformity from 9/22 to 3/22 and newly wrong writes from one to zero. The two model samples are not pooled. CareCall was not evaluated because the required original data and human operation labels were unavailable.

Sources: [DSTC2 results](../supplements/dstc2/RESULTS.json), [intervals](../supplements/dstc2/PAIRED_INTERVALS.json), [methods and corpus access](../supplements/dstc2/README.md).
