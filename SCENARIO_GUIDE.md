# Input-to-output reproduction guide

Run commands from the extracted artifact or repository root. The main checks use Python 3.10+ and the standard library, with no credentials or new model calls. Choose a fresh output directory each time.

## 1. Reconstruct saved memory-write decisions

**Inputs:** `core/data/` contains the authored cases and evaluation references; the saved generation assets preserve extractions and proposals. `core/replay.py` applies the archived policies and evaluator.

```sh
python3 core/replay.py --output-dir /tmp/memory-write-main --write-replayed-outputs
```

**Expected output:** 3,024 episodes, 14 evaluated conditions and 42,336 score rows. The verification report compares scores, executed states and gate audits against the saved results. Exact reconstruction should produce zero mismatches. For a quick installation check, add `--limit 2`; the resulting 28 rows check installation only, not the whole study.

**Example scenario:** a user corrects an earlier fact. The saved proposal is held constant while AGREE, ALLOW, LITERAL and WITNESS decide whether to execute it. The replay outputs show what was proposed, held or executed and whether the final state meets the authored reference. The [condition mapping](core/README.md) connects archived codes to manuscript names.

## 2. Verify matching-convention sensitivity

**Inputs:** saved final states and the strict and mechanical variant-tolerant references; `analysis_v29/expected_results.json` records the expected analysis.

```sh
python3 analysis_v29/rescore_variant_tolerant.py --output-dir /tmp/memory-write-variants
python3 analysis_v29/verify_results.py --results /tmp/memory-write-variants/results.json --report /tmp/memory-write-variants/verification.json
```

**Expected output:** reproduced Tables 7–8 and Appendix K, with exact archived rows and analysis results matching the expected values. Candidate variants are mechanical matching rules, not independently validated semantic equivalents.

## 3. Inspect decision opportunity

```sh
python3 analysis_v29/exposure_sets.py --output-dir /tmp/memory-write-exposure
```

**Expected output:** exposure sets, differing states, validity-dependent outcome differences and missing ALLOW replays. Controlled-path E/D/O/S counts are 49/36/36/36; review-proposal counts are 23/23/23/23. Gating versus ungated review gives 127/123/127/127: four score differences depend on validity rather than changed facts. The state-only diagnostic retains these differences; the state-or-validity inclusion check passes.

## 4. Check the separately collected diagnostic experiments

```sh
python3 supplements/verify_aggregation.py
python3 supplements/replay_saved.py --output-dir /tmp/memory-write-supplements
```

**Expected output:** frozen aggregate counts and paired intervals, plus 296 matched saved authored responses. The five selected corrected-extractor pairs are linked in `supplements/authored/focal5_provenance.json`. They remain separate from the main three-repetition panel.

DSTC2 acquisition, selected turns and local reconstruction are described in `supplements/dstc2/README.md`. The original corpus must be obtained separately; transcript-bearing corpus files are not redistributed here. CareCall-mem is an availability record, not a completed experiment.

## Reading and reuse

`docs/Manuscript.pdf`, `docs/Appendix.pdf` and `paper_source/` provide the manuscript, supplement and editable sources. `REPRODUCING.md` maps paper sections to artifact paths; `RIGHTS.md` explains noncommercial and third-party terms. Reproduction checks consistency with saved experimental results; it does not establish independent human semantic validity or real-user efficacy.
