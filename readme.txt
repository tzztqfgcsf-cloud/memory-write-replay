SUPPLEMENTARY MATERIAL
Diagnosing Memory-Write Decisions in Conversational Assistants
Through Specification-Based Replay

Release: paper-artifact-v5 (revised manuscript and synchronized documentation)

Repository: https://anonymous.4open.science/r/memory-admission-9E37/

CONTENTS
core/ contains the main experiment: 48 authored Korean
cases, 21 model configurations, three repetitions, saved requests and
responses, evaluation references, memory-write policies, and offline replay.
The replay checks 42,336 score rows across 14 policy conditions.
diagnostics/ contains supporting experiments and archived analysis code.
supplements/ contains separately identified additional corrected-extractor,
learned-verifier, and DSTC2 diagnostics, plus a CareCall-mem availability record.
docs/TIST_v27.pdf is the revised 28-page manuscript, including additional
diagnostics in Section 7.4.
docs/TIST_v26_appendix.pdf is the online appendix,
distributed unchanged.
diagnostics/variant_audit_v26/ contains the Table I9 row-level audit.
statistics/ contains portable saved-statistics checks and dependency details.
schemas/ contains the frozen structural-output schemas.
verification/ contains verification records and file checksums.

REQUIREMENTS AND USE
Python 3.10 or newer, using only the standard library. No API credentials,
model downloads, additional Python packages, or model calls are required
for the core and supplementary offline checks. The statistics/ entrypoint
additionally requires Python 3.11+ and its listed NumPy/pandas dependencies.
From the extracted repository directory:

  python3 core/replay.py --output-dir /tmp/memory-write-main-replay
  python3 diagnostics/verify.py
  python3 diagnostics/variant_audit_v26/reproduce.py --output-dir /tmp/memory-write-v26-audit --verify-archived
  python3 supplements/verify_aggregation.py
  python3 supplements/replay_saved.py --output-dir /tmp/memory-write-supplement-replay

Choose new writable output directories for each replay. The expected main
result is 42,336 matching score rows, with matching states and gate audits.
The supporting diagnostic check compares 3,444 score rows; the supplementary
saved-response replay matches 296 outputs. See REPRODUCING.md and the
component README files for condition definitions and detailed instructions.

SCOPE AND RIGHTS
Offline replay uses saved generations. Some statistical analyses are
archived as historical code and tables rather than portable entrypoints.
DSTC2 source transcripts must be obtained separately from their source;
identifiers, hashes, reconstruction instructions and non-transcript results
are included. The full CareCall-mem labeled dataset is not included.
Authored evaluation references are not independent human gold annotations.
Original code uses the Noncommercial Research Code License 1.0.
Original data and documentation use CC BY-NC 4.0. Consult RIGHTS.md and
the bundled third-party notices for scope and exceptions.
