"""Stage-specific structural contracts for a future, separately frozen run.

This module reads only its own versioned schema snapshot. It never reads
episode inputs, references, saved model outputs, credentials, or model weights.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


_SCHEMAS = json.loads(Path(__file__).with_name("schemas.json").read_text(encoding="utf-8"))
STAGES = (
    "g_draft", "g_final", "candidate_extract", "candidate_final",
    "sr_feedback", "sr_refine",
)
_STAGE_TO_SCHEMA = {
    "g_draft": "final", "g_final": "final", "candidate_extract": "extraction",
    "candidate_final": "final", "sr_feedback": "feedback", "sr_refine": "final",
    # D/final, when run independently, has the same structural contract.
    "d_final": "final",
}


def schema_for_stage(stage: str) -> dict[str, Any]:
    """Return a private copy of the complete JSON schema for one call stage."""
    try:
        key = _STAGE_TO_SCHEMA[stage]
    except (KeyError, TypeError) as error:
        raise ValueError(f"UNKNOWN_STAGE:{stage}") from error
    return copy.deepcopy(_SCHEMAS[key])


def structural_errors(stage: str, value: Any) -> list[str]:
    """Check only the JSON-schema keywords present in this snapshot.

    This is an offline shape check, not the runtime's semantic validator and
    not a model-quality score. It rejects extra keys and Python bool-as-int.
    """
    schema = schema_for_stage(stage)
    errors: list[str] = []

    def walk(rule: dict, item: Any, path: str) -> None:
        if "anyOf" in rule:
            if not any(not _suberrors(branch, item) for branch in rule["anyOf"]):
                errors.append(path + ":anyOf")
            return
        allowed = rule.get("type")
        if allowed is not None:
            types = allowed if isinstance(allowed, list) else [allowed]
            matches = {
                "object": lambda: isinstance(item, dict),
                "array": lambda: isinstance(item, list),
                "string": lambda: isinstance(item, str),
                "boolean": lambda: isinstance(item, bool),
                "null": lambda: item is None,
            }
            if not any(matches[k]() for k in types):
                errors.append(path + ":type")
                return
        if "enum" in rule and item not in rule["enum"]:
            errors.append(path + ":enum")
        if isinstance(item, dict):
            required = set(rule.get("required", []))
            for key in sorted(required - item.keys()):
                errors.append(path + "." + key + ":required")
            properties = rule.get("properties", {})
            if rule.get("additionalProperties") is False:
                for key in sorted(item.keys() - properties.keys()):
                    errors.append(path + "." + key + ":additionalProperties")
            for key in item.keys() & properties.keys():
                walk(properties[key], item[key], path + "." + key)
        if isinstance(item, list) and "items" in rule:
            for index, child in enumerate(item):
                walk(rule["items"], child, f"{path}[{index}]")

    def _suberrors(rule: dict, item: Any) -> list[str]:
        before = len(errors)
        walk(rule, item, "$branch")
        branch_errors = errors[before:]
        del errors[before:]
        return branch_errors

    walk(schema, value, "$")
    return errors


def build_local_logits_processor(tokenizer: Any, stage: str) -> Any:
    """Compile this stage's grammar with the existing mlx-vlm route.

    No tokenizer is loaded here. Callers must provide one from an approved
    local snapshot. This function does not generate or load model weights.
    """
    from mlx_vlm.structured import build_json_schema_logits_processor

    return build_json_schema_logits_processor(tokenizer, schema_for_stage(stage))
