# Post-v20 supplementary reproducibility materials

These are **October 4, 2026 post-v20 supplements**, not experiments newly inserted into, or replacements for, the frozen TIST v20 study. The release's `core/` material reproduces the original authored study and deterministic policies. This directory preserves the later corrected-extractor intervention, learned-judge diagnostic, five selected correction cases, and external DSTC2 component diagnostic. Do not pool these experiments or call the supplements independent confirmation.

Everything below runs offline with Python's standard library. No API client, credentials, provider response headers, original local user paths, model weights, third-party paper copies or CareCall data are distributed here. Saved response text and token/latency metadata are supplied for authored synthetic cases. Original provider envelopes and request IDs are omitted. Archived paths in provenance are relative locators prefixed `source_archive/`; they identify private source files and are not required filesystem paths. `EXPORT_PROVENANCE.json` records original SHA-256 and public sanitized SHA-256 separately.

## Verify frozen scores and replay saved responses

From the repository root:

```sh
python3 supplements/verify_aggregation.py
python3 supplements/replay_saved.py --output-dir /tmp/sorieum-supplement-replay
```

Use a new output directory for replay. `verify_aggregation.py` recalculates aggregates, the frozen paired bootstrap intervals and token/latency totals from existing score flags; it never calls a model or reruns the scorer. `replay_saved.py` parses each saved authored raw response, applies the unchanged gate and SQLite executor, and compares with the frozen snapshot and gate audit. It never regenerates a model response, scores historical results or changes original records. The expected result is 296 matched saved outputs. A fresh model experiment would be a separate run with its own permissions, cost and provenance; this public package provides the exact saved prompts and settings but does not dispatch model calls.

Expected aggregate values are in `expected_metrics.json`: 298 authored attempts, 296 frozen scored rows, five focal pairs, original correction success 1/5, corrected success 5/5, original CORRECT holds 4, corrected holds 0, and no harmful writes in either focal arm. The external valid-pair counts are 22 Flash and 48 Pro. These are frozen exploratory observations, not senior human efficacy.

## Authored corrected-extractor and judge materials

`authored/` preserves three collections separately:

| Collection | Status | Attempts | Frozen new score rows |
|---|---|---:|---:|
| `paper_mechanism_validation_20261004` | STOPPED; Gemini 2.5 Flash partial | 291 | 290 |
| `paper_focal5_completion_20261004` | STOPPED at one HTTP 429 | 4 | 3 |
| `paper_focal5_quota_completion_20261004` | COMPLETE for its three-request recovery only | 3 | 3 |

The original 336-request mechanism plan remains partial. Completing the focal five does not complete the full 48-case Gemini 2.5 Flash matrix. The initial mechanism collection contains Gemini 3.8 Flash original/corrected extractor responses for 48 cases each and 144 Gemini 3.1 Pro judge responses on saved Flash 2.5, Flash 3.8 and Qwen 3 14B proposals. The judge's requested model is Pro; each output's model alias identifies the archived proposal source.

Each collection contains:

- `public_inputs.json`: authored packets, selected saved extraction/proposals and state; **model input only**.
- `evaluation_only.json`: frozen authored specification and original scoring metadata; **evaluation only**, never supplied to extractor/judge.
- `queue.json`: all planned request messages and structural schemas, including unattempted jobs; `requests/` records attempted jobs, and `responses/` contains sanitized raw text, failure/status and usage.
- `CONTRACT.json`: model IDs, temperature, thinking setting, token cap, selection, comparisons and stopping rules. Its operational limits describe the historical run, not current billing prices.
- `selected_manifest.json`, `FREEZE.json`, source hashes: exact case/repetition and archive provenance. Sanitization changes file bytes; use exported hashes to check this release and original hashes to compare separately obtained source archives.
- `new_outputs.jsonl`, `new_scores.csv`, extractor traces, frozen totals/intervals and `SUMMARY.json`.

`baseline_scores.csv` copies 864 archived selected-repetition rows used as contrasts; `baseline_provenance.json` identifies their original score files. No baseline was rescored for this release. `methods.py` retains the single prewritten corrected instruction, judge instruction/schema and judge gate. `schemas.json` retains the frozen provider-facing structural schemas. Validation is structural and does not establish semantic understanding.

`focal5_provenance.json` binds all ten successful focal responses to their exact collection, request/response file, saved-output line, score-CSV line, selected repetition and original response SHA-256. CT01 uses two responses from the initial mechanism collection. CT42 uses two from the first completion collection. CT45 and CT46 use original responses from the initial collection and corrected responses from quota recovery. CT48 uses the original response from first completion and corrected response from quota recovery. The failed HTTP 429 corrected CT48 response remains separately recorded; it is not counted as an additional successful sample. Four earlier responses were reused and six additional successful responses completed the five pairs. Five cases were selected after historical failures; the original instruction's spontaneous 1/5 recovery is retained. This is a retrospective mechanism diagnostic with fixed saved proposals, gate, executor and authored specification.

## External DSTC2 supplement

`dstc2/README.md` specifies data acquisition and local reconstruction. No corpus, transcript-bearing packet, gold slot value, saved model text, proposal or execution receipt is redistributed. Selected source dialogue IDs/zero-based turn indices and SHA-256 are provided, together with portable author-created adapter/prompt/evaluation code, pseudonymized caller-cluster scalar score flags, tables and frozen caller-cluster intervals. The original downloaded upstream code and PDFs are excluded.

**Gemini 3.8 Flash completed only 22/48 valid pairs and remains PARTIAL. Gemini 3.1 Pro completed 48/48.** The combined external collection made 142 attempts with 70 completed pairs. Missing transport cases are absent from policy denominators, not zero scores. This English restaurant slot-goal diagnostic is separate from Korean authored corrections and from senior autobiographical memory. Prior human-derived goal state was supplied; it is not end-to-end dialogue tracking or the official full DSTC2 tracker score. Reference-enriched cases form a separately labeled, pre-output diagnostic stratum. Permission `allowed` is a task-tracking fixture, not observed consent. The selected batch contained no official slot deletion, so the adapter's absence of DELETE support remains untested.

## CareCall status

`carecall/status.json` records BLOCKED access/label status, zero calls and no evaluation. The required original Korean full dataset, human operation-label pairs and their split/episode provenance were unavailable. Official dataset restrictions are separate from the license of this repository's original code. No human efficacy or operation-label accuracy result is claimed; no author contact or application is included in this release.
