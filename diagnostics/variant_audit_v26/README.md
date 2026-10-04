# v26 Appendix I.1 / Table I9: archived variant audit

This diagnostic reproduces the composition of the **82 reference violations
avoided by Review+Witness relative to Review**. It reads only saved artifacts
from the public `core/data` package; it makes no model calls, executes no memory
policy, and performs no new score evaluation. It requires Python 3.10+ and the
standard library.

From the repository root, choose a new output directory:

```sh
python3 diagnostics/variant_audit_v26/reproduce.py \
  --output-dir /tmp/memory-write-v26-audit --verify-archived
```

Exit status 0 means the published totals and explicitly listed case counts match, the
structural checks pass, source hashes are unchanged, and the four generated
result files are byte-identical to `analysis/`. The output must not already
exist and must be outside `core/` and this diagnostic directory. To reproduce
without comparing the archived copies, omit `--verify-archived`.

## Result

| Held operation / class | Observations |
|---|---:|
| APPEND: subject label | 29 |
| APPEND: spacing | 6 |
| APPEND: value form | 17 |
| APPEND: other unlisted fact | 17 |
| APPEND: forbidden fact | 2 |
| CORRECT: forbidden value | 11 |
| **Total** | **82** |

There are 71 APPEND holds: 52 variants across nine cases and 19 other APPEND
holds. All 11 CORRECT holds involve a forbidden value. All 82 observations have
exactly one held operation. In all 52 variant observations the saved
`required_present` field is false for both Review and Review+Witness, and
positive-change completion fails under both. This changes the interpretation
of the exact-reference harm endpoint, not any original score.

## Mechanical rule and source

The rule is printed in `docs/TIST_v26_appendix.pdf`, Appendix I.1 / Table I9.
The original variant classification program or 82-row audit table was not
located in the scoped project searches recorded in `SOURCE_HASHES.json`.
`reproduce.py` is a **new portable transcription of the printed rule**, not a
claim to have recovered that original program.

1. Select saved episodes with `expected_scores.G.harmful_write=true` and
   `expected_scores.R_WITNESS.harmful_write=false`. In the frozen condition
   labels, **G is Review**; R is a candidate-path policy and is not the Review
   comparator.
2. Read each failed reference component from the saved G score and each held
   operation from the saved R_WITNESS gate log. The held tuple comes from the
   corresponding pre-gate decision, whose equality to the G decision is checked.
3. For each case, inspect every archived output among the 14 core conditions
   whose saved `whole_state_compliance` is true. Collect its facts that are new
   relative to that episode's initial snapshot. In the nine variant cases,
   every conforming output has the same single new fact; the script also checks
   that this fact is in the authored reference's required facts.
4. Require equal relation and time. Normalize subject/value strings with Unicode
   NFC, `casefold()`, and removal of Unicode whitespace (`"".join(text.split())`).
   Apply the printed tests in order:
   - **spacing:** normalized subject and value are equal but their raw forms
     differ;
   - **subject label:** values are equal and subjects are equal, one contains
     the other, or both are the participant labels `participant` / `p1`;
   - **value form:** one normalized value contains the other and subjects match
     by the preceding equality/containment/participant-label rule.
5. Classify remaining holds as forbidden when the saved G `forbidden_absent`
   is false, otherwise unlisted. Check that APPEND observations without a
   forbidden tuple violate only the unlisted-fact restriction among the harm
   components. Compare computed counts with Table I9 only **after** selection
   and classification. Expected counts never choose a class or a required fact.

There is no CTxx-specific semantic mapping in the classifier. The CTxx counts
in `EXPECTED` are assertions against the published table, not classification
inputs. There are no translations, Korean particle stripping, teacher-name
substitutions, or special rules for an individual model. Representational
variants requiring translation or restructuring remain outside the rule.

## Files and traceability

- `reproduce.py`: standard-library-only portable inspection program.
- `SOURCE_HASHES.json`: hashes of the archived input files and the v26 appendix,
  rule origin, and scoped search provenance.
- `analysis/rows.csv`: 82 observation rows with configuration/case/repetition,
  held operation and tuple, matched required fact, saved failed components,
  completion flags, gate record, input JSON pointers, raw Review response ID,
  and original episode provenance.
- `analysis/required_fact_trace.json`: conforming-state evidence, with episode
  indices and conditions, for all affected cases. The derived new facts remain
  traceable to saved snapshots and initial states.
- `analysis/summary.json`: all aggregate and class/case counts, mismatches,
  structural checks, and interpretation limits. `published.class_case_counts`
  contains only individually numbered Table I9 cases. Additional per-case
  breakdowns under `actual.class_case_counts` are derived here; the table gives
  only grouped totals for the 17 unlisted APPEND and 11 forbidden CORRECT rows.
- `analysis/input_hashes.json`: the exact hashes checked before and after the
  audit.
- `VERIFICATION.json`: fresh reproduction and clean-copy verification record.

CSV pointers refer to the uncompressed JSON value in
`core/data/episodes.json.gz`; its top-level array is zero-indexed. Public row
and reference IDs index `public_rows` and `references` respectively in
`core/data/cases.json.gz`. A raw Review response ID indexes the public raw
response asset store documented in `core/README.md`. Original source paths in
`source_provenance` are provenance identifiers, not runtime dependencies.

## Limits

The rule was written after the avoided observations were listed, as stated in
the appendix. It is a post hoc mechanical audit of archived representations,
not semantic adjudication, a new efficacy experiment, or independent human
review. References are authored development references. Configurations and
repetitions do not create new independent cases. Existing frozen scores,
policies, references, and raw responses are preserved.
