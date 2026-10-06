# Specification-Based Replay of Memory-Write Decisions

Materials for **Diagnosing Memory-Write Decisions in Conversational Assistants Through Specification-Based Replay**.

[Manuscript](docs/Manuscript.pdf) · [Anonymous review copy](docs/Manuscript_anonymous.pdf) · [Online appendix](docs/Appendix.pdf) · [LaTeX sources](paper_source/)

The main paper has 23 pages and the appendix has 31 pages.

## Start here

Python 3.10+ and the standard library are sufficient for the main replay. Download and extract the materials, or clone the repository, then run:

```sh
git clone https://github.com/tzztqfgcsf-cloud/memory-write-replay.git
cd memory-write-replay
python3 core/replay.py --output-dir /tmp/memory-write-replay
```

Use a fresh output directory. The expected result is **3,024 episodes × 14 conditions = 42,336 matching score rows**, with matching final states and gate audits. Replay uses saved model responses and makes no new model calls.

[Full reproduction instructions](REPRODUCING.md) · [Input-to-output examples](SCENARIO_GUIDE.md) · [Condition and score definitions](core/README.md)

## Materials

| Path | Contents |
|---|---|
| `core/` | 48 authored Korean cases, evaluation references, 21 model configurations with three repetitions, saved requests/responses, policies and evaluator. |
| `analysis/` | Variant-tolerant scoring, pipeline decomposition and exposure-set analysis for Tables 7–8 and Appendix K. |
| `diagnostics/` | Supporting experiments, saved ALLOW comparisons, operation-level audit and source notices. |
| `supplements/` | Corrected-extractor, learned-verifier and actual-ASR diagnostics reported in Sections 6.1, 6.6–6.7 and Appendix J. |
| `statistics/` | Reproduction of case-cluster statistical comparisons. |
| `schemas/` | Frozen generation schemas and stage selector. |
| `paper_source/`, `docs/` | Editable manuscript sources, PDFs and a summary of additional results. |
| `verification/` | Document alignment record and current file checksums. |

The [paper-to-artifact map](REPRODUCING.md#paper-to-artifact-map) identifies the files behind each appendix section. Statistical scope and result interpretation are described in [REPRODUCING.md](REPRODUCING.md#scope).

Original code uses the [noncommercial research license](LICENSES/NONCOMMERCIAL-RESEARCH-CODE-1.0.txt); original data and documentation use [CC BY-NC 4.0](LICENSES/CC-BY-NC-4.0.txt). See [RIGHTS.md](RIGHTS.md) for third-party terms and [CITATION.bib](CITATION.bib) to cite the materials.
