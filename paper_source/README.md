# Manuscript sources

Compile `main.tex` for the author-identified manuscript, `main_anonymous.tex` for its anonymous copy, and `appendix.tex` for the accompanying appendix. The source folder includes the bibliography, vector PDF figures and the official acmart 2.18 template. The class options are `acmsmall,review`; the anonymous target also uses `anonymous`.

The CCS concepts are Evaluation (500), Nonmonotonic, default reasoning and belief revision (300), and Discourse, dialogue and pragmatics (100). The three concepts are recorded in both main sources and `CCS.xml`. The authors' AI-use disclosure identifies ChatGPT and Codex.

Upload this whole folder to Overleaf, select pdfLaTeX and compile the selected target. An existing local TeX installation can run `pdflatex`, `bibtex`, then `pdflatex` twice for the main article; the appendix needs repeated `pdflatex` compilation for cross-references.

The distributed PDFs were compiled with Tectonic 0.17.0 / XeTeX: manuscript 23 pages, anonymous copy 23 pages and appendix 31 pages. pdfLaTeX/Overleaf compilation has not been independently run in this environment; engine and font versions can change line breaks.

```sh
tectonic --untrusted main.tex
tectonic --untrusted main_anonymous.tex
tectonic --untrusted appendix.tex
```

Original research materials retain the repository's noncommercial terms. ACM template files retain their own terms; see `ACM_TEMPLATE_NOTICE.txt`.
