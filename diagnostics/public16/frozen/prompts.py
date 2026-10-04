"""Six source-only prompts for one original English utterance per case."""

from __future__ import annotations

import copy
import json

from native_runtime import RELATIONS, protocol, public_for_prompt

STAGES = (
    "g_draft",
    "g_final",
    "candidate_extract",
    "candidate_final",
    "sr_feedback",
    "sr_refine",
)
WITNESS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "candidate_id",
        "target_fact_id",
        "subject",
        "relation",
        "time",
        "new_value",
        "source_turn",
        "evidence_quote",
        "polarity",
    ],
    "properties": {
        "candidate_id": {"type": "string", "enum": ["c1"]},
        "target_fact_id": {"type": "string"},
        "subject": {"type": "string"},
        "relation": {"type": "string", "enum": list(RELATIONS)},
        "time": {"type": "string", "enum": ["unknown"]},
        "new_value": {"type": "string"},
        "source_turn": {"type": "string"},
        "evidence_quote": {"type": "string"},
        "polarity": {
            "type": "string",
            "enum": ["affirmed", "negated", "uncertain", "absent"],
        },
    },
}
EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["beliefs", "correction_witnesses"],
    "properties": {
        "beliefs": protocol.BELIEFS_SCHEMA["properties"]["beliefs"],
        "correction_witnesses": {"type": "array", "items": WITNESS_SCHEMA},
    },
}
FEEDBACK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["no_change_needed", "issues"],
    "properties": {
        "no_change_needed": {"type": "boolean"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "draft_location",
                    "evidence_location",
                    "problem",
                    "specific_revision",
                ],
                "properties": {
                    k: {"type": "string"}
                    for k in (
                        "draft_location",
                        "evidence_location",
                        "problem",
                        "specific_revision",
                    )
                },
            },
        },
    },
}


def schema_for_stage(stage: str, packet: dict) -> dict:
    if stage not in STAGES:
        raise ValueError("UNKNOWN_STAGE")
    sources = sorted(protocol._allowed_sources(packet))
    ids = [fact["fact_id"] for fact in packet["db_snapshot"]["facts"]]
    if len(ids) != len(set(ids)) or any(not isinstance(x, str) or not x for x in ids):
        raise ValueError("INVALID_PUBLIC_DB_IDS")
    if stage == "candidate_extract":
        schema = copy.deepcopy(EXTRACTION_SCHEMA)
        beliefs = schema["properties"]["beliefs"]
        belief = beliefs.pop("items")
        belief["properties"]["candidate_id"] = {"type": "string", "enum": ["c1"]}
        belief_fact = belief["properties"]["facts"]["items"]["properties"]
        belief_fact["source_turns"]["items"]["enum"] = sources
        belief_fact["time"] = {"type": "string", "enum": ["unknown"]}
        beliefs.update(prefixItems=[belief], minItems=1, maxItems=1, items=False)
        witnesses = schema["properties"]["correction_witnesses"]
        if ids:
            witnesses["items"]["properties"]["target_fact_id"] = {
                "type": "string",
                "enum": ids,
            }
        else:
            witnesses["maxItems"] = 0
        witnesses["items"]["properties"]["source_turn"]["enum"] = [packet["turn_id"]]
        return schema
    if stage == "sr_feedback":
        return copy.deepcopy(FEEDBACK_SCHEMA)
    schema = copy.deepcopy(protocol.FINAL_SCHEMA)
    item = schema["properties"]["memory_decisions"]["items"]["properties"]
    item["source_turns"]["items"]["enum"] = sources
    item["fact"]["anyOf"][0]["properties"]["source_turns"]["items"]["enum"] = sources
    item["fact"]["anyOf"][0]["properties"]["time"] = {
        "type": "string",
        "enum": ["unknown"],
    }
    item["target_fact_id"] = (
        {"anyOf": [{"type": "string", "enum": ids}, {"type": "null"}]}
        if ids
        else {"type": "null"}
    )
    return schema


COMMON = (
    "You are working in a temporary task-state editing exercise over a sourced MultiWOZ dialogue. "
    "The prior state is an annotation after the previous system turn, not an observed personal-memory database. "
    "The original user did not grant persistent-memory consent; permission to propose edits exists only in this sandbox exercise. "
    "There is one original English user utterance, candidate c1. It is not one of several ASR transcripts. "
    "Read every preceding real turn and the current utterance. Use only relation names domain.part.slot shown in the input. "
    'Use time="unknown" for facts because source dialogues lack wall-clock timestamps. '
    "Cite exact source_turn_id values. Distinguish an originally mistaken utterance from a later plan/preference change, "
    "an assistant misunderstanding, a question, and uncertainty. Do not assert a real booking, cancellation, external action, "
    "or persistent personal-memory write occurred. Any reply is a pre-execution proposal, not a receipt. "
    "For sandbox decisions: CORRECT changes an existing target fact while keeping its subject/relation/time; "
    "APPEND creates a supported new state fact; HOLD is for an unresolved focal value; NO_WRITE makes no state claim. "
    "Do not CORRECT an unfilled dataset sentinel. Return JSON only."
)


def messages(
    packet: dict, stage: str, prior: object = None, feedback: object = None
) -> list[dict[str, str]]:
    public = public_for_prompt(packet)
    schema = schema_for_stage(stage, packet)
    if stage == "g_draft":
        task = (
            "Make a direct initial reply and task-state proposal from the source input."
        )
    elif stage == "g_final":
        task = "Use your prior draft as fallible context and make a complete final proposal. Do not treat the draft as evidence."
    elif stage == "candidate_extract":
        task = (
            "Write one belief for candidate c1. For each existing target fact ID, give exactly one correction_witness. "
            "A witness is affirmed only for an explicit same-task correction supported by a contiguous exact quote in the "
            "current utterance containing the new_value. A later plan change, new preference, assistant error, or question "
            "is not an assertion that the old state was originally false. Use absent/uncertain/negated where appropriate. "
            "The source_turn must be the current source turn ID; no future system response is available. "
            "This extraction may be wrong and is not a gold reference."
        )
    elif stage == "candidate_final":
        task = "Use the fallible extraction and source input to make one final reply and task-state proposal. Recheck source; do not blindly copy extraction."
    elif stage == "sr_feedback":
        task = "Critique the initial draft using only this public source. Point to exact source turns and fields. No numeric score. Do not use hidden labels."
    else:
        task = "Revise the initial draft using the source-only feedback; make a complete final proposal."
    body = {"input": public}
    if stage in {"g_final", "sr_feedback", "sr_refine"}:
        body["fallible_initial_draft"] = prior
    if stage == "candidate_final":
        body["fallible_extraction"] = prior
    if stage == "sr_refine":
        body["fallible_feedback"] = feedback
    system = (
        COMMON
        + "\n"
        + task
        + "\nJSON schema:\n"
        + json.dumps(schema, ensure_ascii=False, sort_keys=True)
    )
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": json.dumps(body, ensure_ascii=False, sort_keys=True),
        },
    ]


def parse_feedback(raw: str) -> dict:
    value = json.loads(
        raw,
        object_pairs_hook=protocol._unique_object,
        parse_constant=protocol._invalid_constant,
    )
    if not isinstance(value, dict) or set(value) != {"no_change_needed", "issues"}:
        raise protocol.ProtocolError("FEEDBACK_KEYS")
    if not isinstance(value["no_change_needed"], bool) or not isinstance(
        value["issues"], list
    ):
        raise protocol.ProtocolError("FEEDBACK_SHAPE")
    for item in value["issues"]:
        if not isinstance(item, dict) or set(item) != {
            "draft_location",
            "evidence_location",
            "problem",
            "specific_revision",
        }:
            raise protocol.ProtocolError("FEEDBACK_ISSUE_KEYS")
        if not all(isinstance(x, str) and x for x in item.values()):
            raise protocol.ProtocolError("FEEDBACK_ISSUE_TEXT")
    if value["no_change_needed"] and value["issues"]:
        raise protocol.ProtocolError("FEEDBACK_CONTRADICTION")
    return value
