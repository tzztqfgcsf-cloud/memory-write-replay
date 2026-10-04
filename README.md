# Sorieum: specification-based replay of memory-write decisions

Reproducibility materials for **Diagnosing Memory-Write Decisions in Conversational Assistants Through Specification-Based Replay** (manuscript v20).

This repository contains the experimental materials behind the paper: authored Korean cases and evaluation references, saved model outputs, memory-write policies, evaluator, offline replay, and supporting analyses. It is not a product demo or a report-only repository.

## Run the main experiment offline

Requires Python 3.10 or newer. No API keys, model downloads, or Python packages are required for the main replay.

```sh
git clone https://github.com/tzztqfgcsf-cloud/sorieum-paper-supplements.git
cd sorieum-paper-supplements
python3 core/replay.py --output-dir /tmp/sorieum-replay
```

Use a new output directory for each verification. Replay reconstructs memory-write decisions from the saved model responses; it does not call models again.

## Contents

| Directory | What it provides |
|---|---|
| [core](core/) | Main panel: 48 authored cases × 21 model configurations × 3 repeats = 3,024 episodes; saved responses, proposals, references, policies and evaluator; 7 original and 7 additional policy conditions; archived candidate-path ALLOW diagnostics are supplied separately. |
| [diagnostics](diagnostics/) | Supporting v20 experiments, source notices, frozen results and verification instructions. |
| [supplements](supplements/) | Post-v20 corrected-extractor and learned-verifier experiments, external DSTC2 diagnostic, and CareCall-mem availability record. |
| [schemas](schemas/) | Frozen six-stage structural-output schema and stage selector. |
| [docs](docs/) | The Korean supplementary report, provided as a reading aid. |
| [verification](verification/) | Release-level verification results and file-integrity manifest. |

The supplementary experiments were conducted after v20. They are not retroactively presented as v20's main results. See each directory's README for its exact reproducibility scope.

## Reading the results

The unit of the main statistical analysis is the **case**, with repeats clustered within cases. The 21 entries are model configurations; this does not mean 21 independent model families. References for authored cases are author-created evaluation references, not independent human gold labels. Failed and incomplete outputs are retained rather than replaced by successful retries.

The repository distinguishes reconstruction of decisions, checking the evaluator against saved scores, and reproducing analysis summaries. Successful offline verification establishes consistency with the archived experiments; it is not a new efficacy experiment.

See [REPRODUCING.md](REPRODUCING.md), [RIGHTS.md](RIGHTS.md), and [CITATION.bib](CITATION.bib).

## 한국어 안내

논문 실험을 확인하고 재현하기 위한 공개 자료입니다. 핵심 실험의 사례·평가 기준·저장된 모델 응답·기억 처리 규칙·평가 코드를 포함합니다. 위 명령으로 추가 API 호출 없이 저장된 응답의 처리 결과를 재현할 수 있습니다. 본문 v20 실험과 이후 보완 실험은 폴더를 구분했습니다.
