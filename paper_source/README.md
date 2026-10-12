# Manuscript sources

Compile `main.tex` for the main manuscript, `main_anonymous.tex` for the anonymous review copy, and `appendix.tex` for the online appendix. This folder contains the bibliography, vector figures and the official acmart 2.18 template.

The editable LaTeX was reconstructed from the manuscript PDFs and checked against their text, tables, equations and references. The distributed PDFs are the authoritative manuscript copies: 24-page main and anonymous papers, and a 27-page appendix. The appendix uses the current `analysis/` reproduction path.

Upload the whole folder to Overleaf and select pdfLaTeX, or use an existing TeX installation. The reconstructed sources were compiled locally with Tectonic/XeTeX; engine and font differences change pagination (25-page identified source, 24-page anonymous source and 30-page appendix in that check). The source compile is a content check and is not a byte-identical regeneration of the distributed PDFs.

```sh
tectonic --untrusted main.tex
tectonic --untrusted main_anonymous.tex
tectonic --untrusted appendix.tex
```

Original materials retain the repository's noncommercial terms. ACM template files retain their own notices; see `ACM_TEMPLATE_NOTICE.txt`.
