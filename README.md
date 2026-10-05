# Specification-Based Replay of Memory-Write Decisions

Research artifacts for **Diagnosing Memory-Write Decisions in Conversational Assistants Through Specification-Based Replay**, including the revised manuscript and online appendix. The main study and separately collected supplementary diagnostics are organized by experiment.

This repository contains authored Korean cases and evaluation references, saved model outputs, memory-write policies, the evaluator, offline replay, and supporting analyses.

## Manuscript, appendix and reuse terms

[Read the revised manuscript (PDF)](docs/TIST_v27.pdf) · [Read the online appendix (PDF)](docs/TIST_v26_appendix.pdf). The manuscript includes the additional diagnostics in Section 7.4; the appendix retains its original experimental tables.

Original code is available for noncommercial research, teaching and reproduction under the [code license](LICENSES/NONCOMMERCIAL-RESEARCH-CODE-1.0.txt). Original data and documentation use [CC BY-NC 4.0](LICENSES/CC-BY-NC-4.0.txt). Commercial use requires separate permission. Third-party terms are preserved; see [RIGHTS.md](RIGHTS.md).

The ACM supplementary-material description is [readme.txt](readme.txt).

## Run the main experiment offline

Requires Python 3.10 or newer. No API keys, model downloads, or Python packages are required for the main replay.

```sh
git clone https://github.com/tzztqfgcsf-cloud/memory-write-replay.git
cd memory-write-replay
python3 core/replay.py --output-dir /tmp/memory-write-replay
```

Use a new output directory for each verification. Replay reconstructs memory-write decisions from the saved model responses; it does not call models again.

## Reproduce the v26 audit and statistical comparisons

The [v26 Table I9 audit](diagnostics/variant_audit_v26/) supplies a row-level trace and a portable reconstruction of the published classification rule. The [statistics guide](statistics/) provides executable comparisons against the archived confidence intervals and counts. Statistical checks use the dependencies in `statistics/requirements.txt`; the core replay above remains standard-library only.

## Contents

| Directory | What it provides |
|---|---|
| [core](core/) | Main panel: 48 authored cases × 21 model configurations × 3 repeats = 3,024 episodes; saved responses, proposals, references, policies and evaluator; 7 original and 7 additional policy conditions; archived candidate-path ALLOW diagnostics are supplied separately. |
| [diagnostics](diagnostics/) | Supporting experiments, source notices, frozen results and verification instructions. |
| [supplements](supplements/) | Additional corrected-extractor and learned-verifier experiments, external DSTC2 diagnostic, and CareCall-mem availability record. |
| [statistics](statistics/) | Portable checks of saved hybrid, Review+Agree/Allow, and main-panel statistics, with missing historical intervals retained as missing. |
| [schemas](schemas/) | Frozen six-stage structural-output schema and stage selector. |
| [docs](docs/) | The revised manuscript, online appendix and Korean supplementary report. |
| [verification](verification/) | Release-level verification results and file-integrity manifest. |

The additional extractor, LLM-verifier and DSTC2 diagnostics are reported in manuscript Section 7.4 and [Additional results](docs/ADDITIONAL_RESULTS.md), including losses in change completion. They remain separate from the main three-repeat panel and are not added to the original appendix tables.

## Reading the results

The unit of the main statistical analysis is the **case**, with repeats clustered within cases. The 21 entries are model configurations; this does not mean 21 independent model families. References for authored cases are author-created evaluation references, not independent human gold labels. Failed and incomplete outputs are retained rather than replaced by successful retries.

The repository distinguishes reconstruction of decisions, checking the evaluator against saved scores, and reproducing analysis summaries. Successful offline verification establishes consistency with the archived experiments; it is not a new efficacy experiment.

See the [paper-to-artifact coverage table](REPRODUCING.md#paper-to-artifact-map), [REPRODUCING.md](REPRODUCING.md), [RIGHTS.md](RIGHTS.md), and [CITATION.bib](CITATION.bib).

## 한국어 안내

논문 실험을 확인하고 재현하기 위한 공개 자료입니다. 핵심 실험의 사례·평가 기준·저장된 모델 응답·기억 처리 규칙·평가 코드를 포함합니다. 위 명령으로 추가 API 호출 없이 저장된 응답의 처리 결과를 재현할 수 있습니다. 본 실험과 이후 추가 진단 실험은 폴더를 구분했습니다.
