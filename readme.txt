SUPPLEMENTARY MATERIAL
Diagnosing Memory-Write Decisions in Conversational Assistants
Through Specification-Based Replay

Materials: https://github.com/tzztqfgcsf-cloud/memory-write-replay

CONTENTS
Input cases and evaluation references, saved model requests and responses,
memory-write policies and evaluator, replay and analysis code, manuscript
and online appendix, and editable LaTeX sources.

HOW TO USE
README.md is the starting point. REPRODUCING.md contains the commands,
requirements and paper-to-artifact map. SCENARIO_GUIDE.md explains the
inputs, procedures and expected outputs.

The main replay requires Python 3.10+ and the standard library. Its expected
result is 3,024 episodes and 42,336 matching score rows. Statistical checks
use the dependencies listed in statistics/requirements.txt. No new model
calls are needed for offline reproduction.

RIGHTS
Original code uses the Noncommercial Research Code License 1.0. Original
data and documentation use CC BY-NC 4.0. Third-party notices and exceptions
are described in RIGHTS.md.
