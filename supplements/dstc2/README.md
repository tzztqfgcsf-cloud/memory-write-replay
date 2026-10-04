# DSTC2 external component diagnostic: restricted-data reproduction

The selected source is the [DSTC2 v1 test release](https://github.com/matthen/dstc/releases/tag/v1), specifically [dstc2_test.tar.gz](https://github.com/matthen/dstc/releases/download/v1/dstc2_test.tar.gz), from [matthen/dstc](https://github.com/matthen/dstc). Consult the upstream [DSTC2 paper](https://aclanthology.org/W14-4337/) and data-use terms yourself before downloading or using data. A GPL-3 license for repository code was observed in the source audit; it does **not** establish a separate blanket permission to redistribute the spoken-dialogue corpus. This release therefore contains no original corpus, transcripts, gold goals, packets or model responses derived from them. It also contains no upstream script or article copy.

`selected_manifest.json` lists 48 source dialogue paths, zero-based turn indices, original retained ASR ranks, selection stratum and log/label SHA-256. Source identifiers are retained only to locate corpus files. `scored_cases_flags.json` contains scalar outcome flags and ordinal caller-cluster pseudonyms; original caller identity fields and state values are omitted. These pseudonyms preserve clustering for interval verification, not a claim that public corpus dialogue IDs are anonymous. The sample has 12 reference-enriched N-best, 24 goal-revision and 12 denial-without-explicit-replacement cases, selected before model output; it does not estimate population prevalence.

After obtaining/extracting the data locally, point `--data-dir` at the directory containing the source `Mar13_*` subdirectories:

```sh
python3 supplements/dstc2/reconstruct_local.py \
  --data-dir /path/to/your/dstc2_test/data \
  --output-dir /path/to/new/private-dstc2-reconstruction
```

This verifies 96 source hashes and reconstructs the exact 48 frozen input packets locally. The output directory must be new. Its generated packets/references contain restricted source text and are **private local artifacts**, not release files. Dataset acquisition is independent of this repository. Reconstruction makes no network or model calls.

`adapter.py` ports only the original author-created domain adapter's imports. Its English instructions, schema enum substitution, parse/gate/executor path and evaluation predicates retain the frozen logic. It uses `supplements/support.py` and release `core/runtime` modules. Calling `messages('candidate_extract', packet)` returns the exact extraction prompt; calling `messages('candidate_final', packet, extraction)` returns the exact proposal prompt. The `CONTRACT.json` records temperature 0.2, LOW thinking for both Gemini 3.8 Flash and Gemini 3.1 Pro, an 8192 output-token cap, one repetition, and historical stop rules. Structural schemas are in `supplements/schemas.json`. The adapter supplies all distinct nonempty original ASR alternatives in original rank order and does not use likelihood weighting. Remote inference is not part of these scripts.

Policy names are `RAW`, `AGREE`, `ALLOW`, `LITERAL`, and `WITNESS`; they replay the same extraction/proposal pair. Evaluation is exact lowercase food/area/pricerange goal conformity, new wrong writes and required goal changes. Values receive no post-hoc semantic normalization. Existing stale facts can fail joint conformity without being counted as newly wrong writes. A conflicting APPEND also fails joint conformity. DELETE support is absent and remains untested because zero selected cases removed an official slot. Action/consent correctness is not scored.

`TABLES.csv`, `RESULTS.json` and `PAIRED_INTERVALS.json` retain frozen aggregates. The release-wide aggregation verifier reproduces all scalar policy tables and caller-cluster bootstrap intervals using 5,000 replicates and seed 20261004. It does not need corpus text and does not rerun original scoring.

Collection status is **PARTIAL**: Flash 22/48 valid pairs (21 caller clusters), Pro 48/48 (41 caller clusters), 70 total pairs and 142 attempts. The primary paired policy comparisons use valid completed pairs within each model. Flash missing cases are not zero scores or a completed 48-case experiment. Exact historical model-response replay is unavailable publicly because those responses can contain source dialogue material; a newly permitted model run would be a separate execution and may differ. This package enables hash-checked input reconstruction and deterministic evaluation with independently obtained data, plus transcript-free verification of the published frozen aggregates.
