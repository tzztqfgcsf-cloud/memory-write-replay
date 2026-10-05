# Manuscript sources

`main.tex` is the main manuscript; `appendix.tex` is the matching online appendix. Upload this folder to Overleaf and select **pdfLaTeX**. Compile each main document separately. The source uses `acmart`, `kotex`, and the bundled PDF figures. The submitted source was prepared for pdfLaTeX; the release PDFs were compiled locally with Tectonic 0.17.0 (XeTeX), with embedded Latin and Korean fonts. Engine/font versions can change line breaks.

Local build, using an existing Tectonic installation:

```sh
tectonic --untrusted main.tex
tectonic --untrusted appendix.tex
```

No author identities or production DOI have been added. The availability statement uses the anonymous review URL and artifact version paper-artifact-v6. AI-use disclosure names ChatGPT and Codex. Scientific text and figure data are preserved from the supplied manuscript. Original code and text retain the respective repository noncommercial terms.
