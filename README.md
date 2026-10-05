# Specification-Based Replay of Memory-Write Decisions

Research artifacts for **Diagnosing Memory-Write Decisions in Conversational Assistants Through Specification-Based Replay**, including the revised manuscript and online appendix. The main study and separately collected supplementary diagnostics are organized by experiment.

This repository contains authored Korean cases and evaluation references, saved model outputs, memory-write policies, the evaluator, offline replay, and supporting analyses.

## Manuscript, appendix and reuse terms

[Read the manuscript (PDF)](docs/TIST_v29.pdf) · [Read the online appendix (PDF)](docs/TIST_v29_appendix.pdf) · [Editable LaTeX sources](paper_source/).

Current artifact version: **paper-artifact-v6**. The manuscript includes corrected extraction (Section 6.1), a learned verifier (6.6), real ASR hypotheses (6.7), and variant-tolerant scoring and pipeline decomposition (6.4–6.5; Appendix K).

Original code is available for noncommercial research, teaching and reproduction under the [code license](LICENSES/NONCOMMERCIAL-RESEARCH-CODE-1.0.txt). Original data and documentation use [CC BY-NC 4.0](LICENSES/CC-BY-NC-4.0.txt). Commercial use requires separate permission. Third-party terms are preserved; see [RIGHTS.md](RIGHTS.md).

The ACM supplementary-material description is [readme.txt](readme.txt).

## Run the main experiment offline

Requires Python 3.10 or newer. No API keys, model downloads, or Python packages are required for the main replay.

Download and extract this anonymous archive, then run from its root:

```sh
python3 core/replay.py --output-dir /tmp/memory-write-replay
```

Use a new output directory for each verification. Replay reconstructs memory-write decisions from the saved model responses; it does not call models again.

## Reproduce the surface-variant analysis

```sh
python3 analysis_v29/rescore_variant_tolerant.py --output-dir /tmp/memory-write-v29
python3 analysis_v29/verify_results.py --results /tmp/memory-write-v29/results.json --report /tmp/memory-write-v29/verification.json
```

This verifies the exact archived scores and the complete expected results of the separate variant-tolerant analysis. It uses saved states and makes no model calls. See [analysis_v29](analysis_v29/).

## Reproduce the earlier audit and statistical comparisons

The [v26 Table I9 audit](diagnostics/variant_audit_v26/) supplies a row-level trace and a portable reconstruction of the published classification rule. The [statistics guide](statistics/) provides executable comparisons against the archived confidence intervals and counts. Statistical checks use the dependencies in `statistics/requirements.txt`; the core replay above remains standard-library only.

## Contents

| Directory | What it provides |
|---|---|
| [core](core/) | Main panel: 48 authored cases × 21 model configurations × 3 repeats = 3,024 episodes; saved responses, proposals, references, policies and evaluator; 7 original and 7 additional policy conditions; archived candidate-path ALLOW diagnostics are supplied separately. |
| [diagnostics](diagnostics/) | Supporting experiments, source notices, frozen results and verification instructions. |
| [supplements](supplements/) | Additional corrected-extractor and learned-verifier experiments, external DSTC2 diagnostic, and CareCall-mem availability record. |
| [analysis_v29](analysis_v29/) | Variant-tolerant scoring, fixed-proposal invariance, pipeline decomposition and case-cluster intervals (Tables 7–8; Appendix K). |
| [paper_source](paper_source/) | Main and appendix LaTeX, bibliography and figures. |
| [statistics](statistics/) | Portable checks of saved hybrid, Review+Agree/Allow, and main-panel statistics, with missing historical intervals retained as missing. |
| [schemas](schemas/) | Frozen six-stage structural-output schema and stage selector. |
| [docs](docs/) | The revised manuscript, online appendix and Korean supplementary report. |
| [verification](verification/) | Release-level verification results and file-integrity manifest. |

The additional extractor, LLM-verifier and DSTC2 diagnostics are reported in manuscript Sections 6.1, 6.6 and 6.7, Appendix J, and [Additional results](docs/ADDITIONAL_RESULTS.md), including losses in change completion. They remain separate from the main three-repeat panel. Appendix K reports the separate surface-variant sensitivity analysis; archived exact-reference scores remain unchanged.

## Reading the results

The unit of the main statistical analysis is the **case**, with repeats clustered within cases. The 21 entries are model configurations; this does not mean 21 independent model families. References for authored cases are author-created evaluation references, not independent human gold labels. Failed and incomplete outputs are retained rather than replaced by successful retries.

The repository distinguishes reconstruction of decisions, checking the evaluator against saved scores, and reproducing analysis summaries. Successful offline verification establishes consistency with the archived experiments; it is not a new efficacy experiment.

See the [paper-to-artifact coverage table](REPRODUCING.md#paper-to-artifact-map), [REPRODUCING.md](REPRODUCING.md), [RIGHTS.md](RIGHTS.md), and [CITATION.bib](CITATION.bib).

## 한국어 안내

논문 실험을 확인하고 재현하기 위한 공개 자료입니다. 핵심 실험의 사례·평가 기준·저장된 모델 응답·기억 처리 규칙·평가 코드를 포함합니다. 위 명령으로 추가 API 호출 없이 저장된 응답의 처리 결과를 재현할 수 있습니다. 본 실험과 이후 추가 진단 실험은 폴더를 구분했습니다.
