# Frozen structural schemas

Exact byte copies of the main structured-output-v2 schema snapshot and stage selector. `schema_for_stage` returns the recorded structural contract for each stage. The snapshot also includes an optional MLX logits-processor helper; it is not used by the offline replay and its optional dependencies are not required. Structure validation is separate from semantic evaluation. Exact source hashes are in SOURCE_MANIFEST.json.
