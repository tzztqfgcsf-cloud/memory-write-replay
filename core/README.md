# Offline replay of the main saved cohort

This package executes the frozen memory policies and SQLite executor against
archived model proposals, then checks the resulting scores against the archived
score rows. It needs Python 3.10 or newer and its standard library, including
SQLite. No model, API key, account, GPU, package download or network is required.

From the repository root, choose a **new** output directory:

```sh
python3 core/replay.py --output-dir /tmp/memory-write-replay
```

The directory must not already exist and must be outside `core/`. A complete run
checks 3,024 episodes × 14 conditions = 42,336 score rows, with every one of the
31 frozen score fields compared. Each condition starts in an isolated temporary
SQLite state. Temporary states are deleted automatically. The output directory
contains `scores.csv`, `condition_totals.csv`, `differences.json`, and
`verification.json`. Exit status 0 means all evaluated score rows matched.
`complete_cohort: true` distinguishes a complete run from a smoke run.

For a fast installation check:

```sh
python3 core/replay.py --output-dir /tmp/memory-write-smoke --limit 2
```

Add `--write-replayed-outputs` to save fresh receipts and final states as
`replayed_outputs.jsonl.gz`. Package SHA-256 hashes are checked before and after
replay. Network access is rejected by a Python audit hook. No original project
checkout is read, and expected rows are never overwritten.

## Included inputs and algorithms

- 48 authored Korean text cases and authored references; these are synthetic
  development references, not independent human judgments.
- 21 archived configuration aliases, three saved repetitions per case, selected
  by the original cohort manifest. Repetitions and configurations do not create
  new independent cases.
- The original seven conditions: `D`, `G`, `SR1`, `B`, `C`, `R`, `CR`.
- Seven later saved policy conditions: `N_AGREE`, `EXACT_LITERAL`, `N_LITERAL`,
  `R_LITERAL`, `R_WITNESS`, `R_AGREE`, `R_ALLOW`.
- Saved proposals, failures, parse diagnostics, final states, receipts, gate
  audits and expected score rows for all 14 conditions.
- Manifest-selected raw candidate extraction, candidate final, review final and
  review draft responses, plus exact generation requests/prompts/settings and
  other available stages from those same episodes' upstream call lineage.
  These include SR1 feedback and refinement, failed and unparseable responses. Duplicate
  response contents are stored once with every selected source-file provenance.
- Exact frozen protocol, SQLite executor, witness policy, literal exception,
  normalized alternatives, correction-allow exception, and v2 evaluator.

`data/cases.json.gz` stores authored rows and references keyed by content hash.
`data/episodes.json.gz` joins each episode to these rows, saved proposals, parsed
extraction and expected scores. `data/raw_responses.json.gz` preserves selected
model response text and source hashes. `data/generation_requests.json.gz` stores
exact recorded request prompts, schemas and generation settings, with private
session/transport fields excluded. `data/generation_asset_coverage.json` lists
available source-file counts and any missing assets. `data/cohort.json` records the selection
and limitations. `SOURCE_MANIFEST.json` records SHA-256 values for original
repository-relative source files; those paths are provenance identifiers, not
required paths in this standalone package. `PACKAGE_MANIFEST.json` hashes the
public package. `VERIFICATION.json` records the release assembly verification.

Filesystem loader paths and internal module aliases were adapted in copied policy sources. Admission, rendering and evaluation decision functions remain unchanged. The initial export checked copied algorithm
function and class syntax trees against the frozen originals;
`apply_exception` was extracted unchanged from its original module. The public
runner recreates the archived runner wiring without its private source paths or
provider dependencies. Source database paths and private session/provider
metadata are excluded. Original workspace prefixes in call/provenance paths are
converted to repository-relative paths. Raw model response text is unchanged.

## Interpretation and limits

This is deterministic replay of saved generations. It reproduces execution and
evaluation; it does not generate new model answers, verify current provider
availability, establish independent semantic validity, or demonstrate senior
user efficacy. The selected model names are historical configuration aliases.
Generation failures remain in denominators and cannot become successful rows.

The review-based policy alternatives combine the saved review proposal with
candidate-path extraction. These preserve distinct generation provenance: the
hybrid uses three archived generation calls in complete-path accounting even
though this replay makes zero calls.

The input manifest explicitly selects raw files for four generation stages.
Available other stages, including SR1 feedback/refinement, are exported only
through the same selected episodes' recorded upstream lineage. Any unavailable
generation assets are listed; final proposals, failures, states and score rows
remain complete. Candidate-path `E` (ALLOW) archived replay is included in the
release diagnostics for eight selected configurations (1,152 episodes); it was
not archived for all 21 and is outside the 14-condition core replay. The
runner reproduces counts and point estimates. It does not recompute bootstrap
intervals, select configurations, repair proposals, change references, or
reconstruct unavailable generation stages. Additional studies and bounds are
provided separately when included in the release.

## Using the frozen code

Add `core/runtime` to Python's module search path, then import `policies` and
`evaluate`. The exact executor and protocol are `policies.original.store` and
`policies.original.protocol`. The literal helper is `policies.literal`;
`allow.apply_exception` implements the frozen correction-only allow exception.
`evaluate.score_output(output, public_row, reference)` returns the frozen v2
score fields. No component reads a reference while choosing a gate decision.

## Condition codes used in the paper

| Code | Paper label | Admission | Reply |
|---|---|---|---|
| D | Direct | none; executor guards remain | raw proposal reply |
| G | Review | none; executor guards remain | raw proposal reply |
| SR1 | Refine | none; executor guards remain | raw proposal reply |
| B | Agree | exact shared-fact intersection (APPEND and CORRECT) | raw proposal reply |
| C | Witness | Agree, then witness exception on eligible held CORRECT | raw proposal reply |
| R | Agree with receipt rendering | exactly B / Agree | receipt-grounded rendering |
| CR | Witness-R / controlled primary arm | exactly C / Witness | receipt-grounded rendering |
| N_AGREE | Normalized Agree | NFC/casefold/whitespace support matching for held APPEND/CORRECT | raw proposal reply |
| EXACT_LITERAL | Literal on candidate proposals | Agree + exact literal exception on held CORRECT | raw proposal reply |
| N_LITERAL | Normalized Literal | same literal rule, normalization only for final containment test | raw proposal reply |
| R_AGREE | Review + Agree | Agree | raw Review reply |
| R_ALLOW | Review + Allow | Agree + release every eligible held CORRECT (no evidence test) | raw Review reply |
| R_LITERAL | Review + Literal | Agree + exact literal exception | raw Review reply |
| R_WITNESS | Review + Witness | Agree + witness exception | raw Review reply |

Bare `R` means receipt-based reply rendering with AGREE; `CR` uses WITNESS with receipt rendering. In contrast, `R_AGREE`, `R_ALLOW`, `R_LITERAL`, and `R_WITNESS` use the saved REVIEW proposal and candidate extraction, with the raw REVIEW reply. They are not receipt-rendering conditions. B/R and C/CR have identical memory states. The hybrid paths represent three archived generation stages; replay itself calls no model. Candidate-path `E` (ALLOW) is available only in the eight-configuration diagnostic.

### Score fields

| Artifact field | Paper endpoint |
|---|---|
| `positive_joint` | Positive-change completion |
| `correction_recovery` | Strict correction completion |
| `whole_state_compliance` | Whole-state conformity |
| `harmful_write` | Reference-violating state: an extra tuple, newly forbidden tuple, or protected-fact damage |
| `invalid_final` | Invalid output |
| `negative_preservation` | State preservation on negative cases |
| `unsupported_write_claim` | Unsupported completed-writing claim under the frozen phrase detector |

`harmful_write` is a specification-based flag, not a human judgment of semantic harm. Exact predicates are in `runtime/evaluate.py`; admission and rendering are in `runtime/policy.py`, `runtime/policies.py` and `replay.py`.
