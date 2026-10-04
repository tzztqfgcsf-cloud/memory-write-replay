# Reproducing the archived results

## 1. Main panel

Run `python3 core/replay.py --output-dir /tmp/sorieum-replay` from the repository root. The output location must be new. Read `core/README.md` for condition definitions and the exact comparisons checked.

All model responses were previously collected. Replay runs the memory-write algorithms and frozen evaluator locally; fresh responses from contemporary model endpoints are neither required nor expected to be identical.

## 2. Supporting v20 diagnostics

Read `diagnostics/README.md`. This collection preserves the supporting experiments separately from the 21-configuration main panel. Its verification command and any narrower verification scope are documented there.

## 3. Post-v20 supplements

Read `supplements/README.md`. Corrected-extractor, learned-verifier and DSTC2 outcomes are later diagnostics, not preregistered replications of v20. DSTC2 material requiring separate upstream data access is represented by identifiers, hashes, adapter code and non-transcript results; it is not bundled as an unrestricted new dataset.

## 4. Integrity

`verification/SHA256SUMS` lists the release's files, except itself. A release ZIP checksum is supplied beside the GitHub release asset. `verification/RELEASE_CHECKS.json` records the fresh checks made before publication. The per-directory source manifests connect portable files to frozen source artifacts; personal workstation paths are removed from the public package.

## What is not required

No family audio, participant contacts, credentials, AIHub source recordings, model weights or unrelated product data are necessary for this paper's replay. These are not part of this archive.

## Version and archive

The GitHub release freezes a named version and downloadable archive. It does not assign a DOI or claim an ACM artifact badge. If a permanent DOI-bearing archive is required for the publication, deposit this exact release in the chosen archival repository and add that DOI after it is issued. See [ACM artifact review and badging policy](https://www.acm.org/publications/policies/artifact-review-and-badging-current).
