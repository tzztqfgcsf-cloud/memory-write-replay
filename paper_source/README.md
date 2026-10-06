# ACM review-submission sources

Select `main.tex` for the main manuscript, `main_anonymous.tex` for the anonymous review copy, or `appendix.tex` for the accompanying appendix. In the anonymous snapshot both main targets are anonymous.

The sources use the official `manuscript,review` options and carry the unmodified ACM acmart 2.20 class (2026-08-16) and bibliography style. The local class pins the layout. A valid CCSXML block exported from https://dl.acm.org/ccs is embedded in both main sources: Evaluation500; belief revision300; intelligent agents300; dialogue/pragmatics100. `CCS.xml` is also supplied separately.

The distributed PDFs were actually compiled with Tectonic 0.17.0 / XeTeX using this local class: main20 pages, anonymous main20 pages, appendix31 pages. pdfLaTeX is selected in the source directive for Overleaf; an actual pdfLaTeX/Overleaf build has not been performed in the release environment. The checked distribution is the included PDF. Rebuilding with another engine can reflow pages; if choosing that PDF for submission, update the corresponding release asset and hashes together.

```sh
tectonic --untrusted main.tex
tectonic --untrusted main_anonymous.tex
tectonic --untrusted appendix.tex
```

Paper-artifact-v8 changes only formatting, CCS metadata and artifact version. One unchanged model snapshot identifier in the appendix is allowed to wrap. All scientific text, figures, references, raw outputs and scores are preserved. ChatGPT and Codex remain disclosed. Author email and ORCID values have not been invented; author contact details can be added when supplied. Template files retain their original license; see ACM_TEMPLATE_NOTICE.txt. Original research materials keep their noncommercial terms.
