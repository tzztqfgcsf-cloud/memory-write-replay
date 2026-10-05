# Final manuscript source

Select `main.tex` for the author-identified manuscript, `main_anonymous.tex` for the anonymous review copy, or `appendix.tex` for the online appendix. All share the bibliography and media in this directory.

The author-supplied source is pdfLaTeX-compatible. The distributed PDFs were built with the existing Tectonic 0.17.0 / XeTeX environment (bundled acmart 1.83), giving 22, 21 and 31 pages respectively. Another TeX engine or class version can change line breaks and page count; release PDFs and docs/ copies are identical files. To reproduce this layout use the stated environment. For editing on Overleaf select pdfLaTeX, then replace the distribution PDFs if choosing that build as the final submission.

```sh
tectonic --untrusted main.tex
tectonic --untrusted main_anonymous.tex
tectonic --untrusted appendix.tex
```

Submission preparation changes: Evaluation CCS weight 500 (primary), dialogue/pragmatics weight 100, artifact version/link v7, and explicit ChatGPT/Codex disclosure. The main scientific text and all supplied figure data are preserved; one Appendix K sentence clarifies that the exposure check separates state and generation-validity differences. No experimental counts were changed. The anonymous main removes author metadata and uses the anonymous artifact URL. Author email/ORCID fields, if required by the submission portal, must be supplied by the authors; none have been invented. Existing noncommercial terms apply.
