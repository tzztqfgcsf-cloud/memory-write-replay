"""Common, reference-free protocol for the new controlled comparison.

This module never reads source, reference, labels, credentials, or model outputs
from disk. Parsing preserves semantic values; the only text cleanup is removal
of one enclosing Markdown JSON fence. Callers preserve raw text independently.
"""
from __future__ import annotations

import copy
import json
import re
from typing import Any

RELATIONS = (
    "residence", "birthplace", "workplace", "learned_from", "hobby",
    "meeting_place", "preferred_contact", "event_year", "shop_name",
    "travel_destination",
)
TIMES = ("past", "present", "unknown")
KINDS = ("CONTINUE", "CLARIFY", "SKIP", "STOP")
OPERATIONS = ("APPEND", "CORRECT", "HOLD", "NO_WRITE")
SLOTS = (*RELATIONS, "topic_permission", "stop_intent", "recipient", "destination", "message_content", "application_field", "meeting_time", "travel_date", "other")
FACT_KEYS = {"subject", "relation", "value", "time", "source_turns"}
DECISION_KEYS = {"operation", "target_fact_id", "fact", "slot", "alternatives", "source_turns"}
ACTION_KEYS = {"kind", "speaker_id", "required_slots", "question_slot"}


class ProtocolError(ValueError):
    """A recorded contract failure, never an instruction to retry a model."""

    def __init__(self, code: str, errors: list[str] | None = None):
        self.code = code
        self.errors = errors or [code]
        super().__init__(";".join(self.errors))


def _object(value: Any, keys: set[str], code: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ProtocolError(code)
    return value


def _string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(code)
    return value


def _strings(value: Any, code: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ProtocolError(code)
    for item in value:
        _string(item, code)
    return value


def fact_tuple(value: dict) -> tuple[str, str, str, str]:
    """Exact canonical output equality, without fuzzy string normalization."""
    return tuple(value[key] for key in ("subject", "relation", "value", "time"))


def _validate_fact(value: Any) -> dict:
    value = _object(value, FACT_KEYS, "FACT_KEYS")
    _string(value["subject"], "FACT_SUBJECT")
    _string(value["value"], "FACT_VALUE")
    if value["relation"] not in RELATIONS:
        raise ProtocolError("FACT_RELATION")
    if value["time"] not in TIMES:
        raise ProtocolError("FACT_TIME")
    _strings(value["source_turns"], "FACT_SOURCE_TURNS")
    return value


def _validate_final_shape(value: Any) -> dict:
    value = _object(value, {"reply", "action", "memory_decisions"}, "FINAL_KEYS")
    _string(value["reply"], "REPLY_EMPTY")
    action = _object(value["action"], ACTION_KEYS, "ACTION_KEYS")
    if action["kind"] not in KINDS:
        raise ProtocolError("ACTION_KIND")
    _string(action["speaker_id"], "ACTION_SPEAKER")
    slots = _strings(action["required_slots"], "ACTION_REQUIRED_SLOTS")
    if any(slot not in SLOTS for slot in slots):
        raise ProtocolError("ACTION_REQUIRED_SLOT_VALUE")
    if action["question_slot"] is not None and action["question_slot"] not in SLOTS:
        raise ProtocolError("QUESTION_SLOT_VALUE")
    decisions = value["memory_decisions"]
    if not isinstance(decisions, list):
        raise ProtocolError("MEMORY_DECISIONS_LIST")
    for decision in decisions:
        _object(decision, DECISION_KEYS, "MEMORY_DECISION_KEYS")
        operation = decision["operation"]
        if not isinstance(operation, str) or operation not in OPERATIONS:
            raise ProtocolError("MEMORY_OPERATION")
        target = decision["target_fact_id"]
        if target is not None:
            _string(target, "TARGET_FACT_ID")
        if decision["slot"] is not None and decision["slot"] not in RELATIONS:
            raise ProtocolError("MEMORY_SLOT")
        _strings(decision["alternatives"], "MEMORY_ALTERNATIVES")
        _strings(decision["source_turns"], "DECISION_SOURCE_TURNS")
        if decision["fact"] is not None:
            _validate_fact(decision["fact"])
    return value


def _validate_beliefs_shape(value: Any) -> dict:
    value = _object(value, {"beliefs"}, "BELIEFS_KEYS")
    rows = value["beliefs"]
    if not isinstance(rows, list):
        raise ProtocolError("BELIEFS_LIST")
    ids = []
    for row in rows:
        _object(row, {"candidate_id", "facts"}, "BELIEF_KEYS")
        ids.append(_string(row["candidate_id"], "CANDIDATE_ID"))
        if not isinstance(row["facts"], list):
            raise ProtocolError("BELIEF_FACTS_LIST")
        for fact in row["facts"]:
            _validate_fact(fact)
        tuples = [fact_tuple(fact) for fact in row["facts"]]
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ProtocolError("DUPLICATE_KEY")
        value[key] = item
    return value


def _invalid_constant(value: str) -> None:
    raise ProtocolError("NONFINITE_JSON:" + value)


def parse(text: str, stage: str) -> dict:
    """Return a validated dict; raise ProtocolError on any parsing/shape error."""
    if not isinstance(text, str):
        raise ProtocolError("RESPONSE_NOT_TEXT")
    cleaned = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", cleaned, re.DOTALL | re.IGNORECASE)
    if fence:
        cleaned = fence.group(1)
    try:
        value = json.loads(cleaned, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (json.JSONDecodeError, TypeError) as error:
        raise ProtocolError("JSON_PARSE") from error
    if stage in {"beliefs", "extract"}:
        return _validate_beliefs_shape(value)
    if stage in {"final", "draft"}:
        return _validate_final_shape(value)
    raise ProtocolError("UNKNOWN_STAGE")


def _packet(packet: dict) -> dict:
    if not isinstance(packet, dict):
        raise ProtocolError("PACKET_TYPE")
    for key in ("turn_id", "speaker_id"):
        _string(packet.get(key), "PACKET_" + key.upper())
    if packet["turn_id"] not in {"t1", "t2"}:
        raise ProtocolError("PACKET_TURN_ID")
    alternatives = packet.get("alternatives")
    if not isinstance(alternatives, list) or not alternatives:
        raise ProtocolError("PACKET_ALTERNATIVES")
    for item in alternatives:
        _string(item, "PACKET_ALTERNATIVE_TEXT")
    if not isinstance(packet.get("memory_permission"), str) or packet["memory_permission"] not in {"allowed", "unknown", "denied"}:
        raise ProtocolError("PACKET_PERMISSION")
    if not isinstance(packet.get("history", []), list):
        raise ProtocolError("PACKET_HISTORY")
    state = packet.get("db_snapshot", {})
    if not isinstance(state, dict) or not isinstance(state.get("facts", []), list):
        raise ProtocolError("PACKET_DB_SNAPSHOT")
    for item in state.get("facts", []):
        if not isinstance(item, dict) or not {"fact_id", "subject", "relation", "value", "time"} <= set(item):
            raise ProtocolError("PACKET_DB_FACT_FIELDS")
        for key in ("fact_id", "subject", "value"):
            _string(item[key], "PACKET_DB_FACT_TEXT")
        if item["relation"] not in RELATIONS or item["time"] not in TIMES:
            raise ProtocolError("PACKET_DB_FACT_ENUM")
        _strings(item.get("source_turns", []), "PACKET_DB_FACT_SOURCES")
    return packet


def _allowed_sources(packet: dict) -> set[str]:
    return {"t1"} if packet["turn_id"] == "t1" else {"t1", "t2"}


def _validate_sources(value: dict, packet: dict) -> None:
    allowed = _allowed_sources(packet)
    if not set(value["source_turns"]) <= allowed:
        raise ProtocolError("SOURCE_TURN_NOT_OBSERVED")


def validate_final(value: dict, packet: dict) -> dict:
    """Validate packet-dependent metadata; never silently repair model values."""
    _packet(packet)
    _validate_final_shape(value)
    return value


def validate_beliefs(value: dict, packet: dict) -> dict:
    _packet(packet)
    _validate_beliefs_shape(value)
    expected = {f"c{index + 1}" for index in range(len(packet["alternatives"]))}
    if len(value["beliefs"]) != len(expected) or {row["candidate_id"] for row in value["beliefs"]} != expected:
        raise ProtocolError("CANDIDATE_COVERAGE")
    for row in value["beliefs"]:
        for fact in row["facts"]:
            _validate_sources(fact, packet)
    return value


def apply_gate(parsed_final: dict, beliefs: dict, packet: dict) -> tuple[dict, list[dict]]:
    """Apply S's factual-support gate only; permission is the executor's guard.

    Evidence is fallible model extraction, not an oracle. Complete candidate
    coverage is required, exact tuple equality is used, and established DB
    facts may also support an unchanged fact. All candidate-shared new values
    can replace an old value via CORRECT; old DB values are not extra candidates.
    """
    validate_final(parsed_final, packet)
    try:
        validate_beliefs(beliefs, packet)
        eligible = True
    except ProtocolError:
        eligible = False
    candidate_sets = [{fact_tuple(fact) for fact in row["facts"]} for row in beliefs.get("beliefs", [])] if eligible else []
    shared = set.intersection(*candidate_sets) if candidate_sets else set()
    committed = {fact_tuple(fact) for fact in packet.get("db_snapshot", {}).get("facts", [])}
    result = copy.deepcopy(parsed_final)
    audit = []
    for index, decision in enumerate(result["memory_decisions"]):
        before = decision["operation"]
        reason = "NONCOMMIT_UNCHANGED"
        if before in {"APPEND", "CORRECT"}:
            proposed = decision["fact"]
            if proposed is None:
                audit.append({"index": index, "before_operation": before,
                              "after_operation": before, "reason": "COMMIT_FACT_MISSING_EXECUTOR_WILL_REJECT"})
                continue
            key = fact_tuple(proposed)
            if key in shared:
                reason = "ALL_CANDIDATES_SUPPORT"
            elif key in committed:
                reason = "ALREADY_COMMITTED_FACT"
            else:
                reason = "NOT_SUPPORTED_BY_ALL_CANDIDATES"
                alternatives = sorted({
                    fact["value"] for row in beliefs.get("beliefs", []) for fact in row["facts"]
                    if (fact["subject"], fact["relation"], fact["time"])
                    == (proposed["subject"], proposed["relation"], proposed["time"])
                })
                decision.update(operation="HOLD", fact=None, slot=proposed["relation"], alternatives=alternatives)
        audit.append({"index": index, "before_operation": before,
                      "after_operation": decision["operation"], "reason": reason, "candidate_coverage_valid": eligible})
    return result, audit


FACT_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": sorted(FACT_KEYS),
    "properties": {
        "subject": {"type": "string"}, "relation": {"type": "string", "enum": list(RELATIONS)},
        "value": {"type": "string"}, "time": {"type": "string", "enum": list(TIMES)},
        "source_turns": {"type": "array", "items": {"type": "string", "enum": ["t1", "t2"]}},
    },
}
FINAL_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["reply", "action", "memory_decisions"],
    "properties": {
        "reply": {"type": "string"},
        "action": {
            "type": "object", "additionalProperties": False, "required": sorted(ACTION_KEYS),
            "properties": {
                "kind": {"type": "string", "enum": list(KINDS)},
                "speaker_id": {"type": "string"},
                "required_slots": {"type": "array", "items": {"type": "string", "enum": list(SLOTS)}},
                "question_slot": {"anyOf": [{"type": "string", "enum": list(SLOTS)}, {"type": "null"}]},
            },
        },
        "memory_decisions": {
            "type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": sorted(DECISION_KEYS),
                "properties": {
                    "operation": {"type": "string", "enum": list(OPERATIONS)},
                    "target_fact_id": {"type": ["string", "null"]},
                    "fact": {"anyOf": [FACT_SCHEMA, {"type": "null"}]},
                    "slot": {"anyOf": [{"type": "string", "enum": list(RELATIONS)}, {"type": "null"}]},
                    "alternatives": {"type": "array", "items": {"type": "string"}},
                    "source_turns": {"type": "array", "items": {"type": "string", "enum": ["t1", "t2"]}},
                },
            },
        },
    },
}
BELIEFS_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["beliefs"],
    "properties": {"beliefs": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["candidate_id", "facts"],
        "properties": {"candidate_id": {"type": "string"}, "facts": {"type": "array", "items": FACT_SCHEMA}},
    }}},
}

COMMON_INSTRUCTION = """당신은 개인 경험 대화를 이어 가고 허용된 사실 기억을 관리한다.
입력 대안들은 같은 사람의 같은 발화에 대한 가능한 전사이며 독립된 화자가 아니다.
모든 대안을 읽고 행동, 사실, 관계의 주체, 시점, 저장 동의를 구분한다. 확정되지 않은
값을 사실로 말하거나 저장하지 않는다. 다음 행동에 필요 없는 불확실성은 남겨 두고
근거 있는 대화를 이어갈 수 있다. 행동에 필요한 값은 구체적으로 질문하거나 안전하게
넘긴다. 확인 질문이 적절할 수도 있으며 질문 수를 줄이는 것 자체가 목적이 아니다.
분명하고 허용된 사실은 기록하고, 명시적인 정정은 기존 fact_id를 CORRECT한다.
단순히 항상 HOLD하거나 항상 NO_WRITE하지 않는다. 기존 DB는 앞선 시점의 기억이며
현재 명시 정정이 있으면 새값으로 고칠 수 있다. pending은 확정 사실이 아니다.
memory_permission allowed에서만 개인사실을 영속 기록한다. denied/unknown이면
APPEND/CORRECT/HOLD로 우회 저장하지 말고 NO_WRITE한다. 과거 동의와 현재 동의를 혼동하지 않는다.
출력 reply는 실제 사용자에게 전달할 자연스러운 한국어 문장이다. DB 쓰기는 뒤에서 실행되므로 성공했다고 미리 확언하지 않는다. known speaker_id를 보존한다.
CLARIFY라면 무엇을 묻는지 실제 문장과 question_slot에 명시하고, 다른 kind에는 question_slot=null. 수신인은 recipient, 길 찾기의 목적지는 destination, 목록에 없는 확인 대상은 other로 표기한다. 저장 완료를 도구 실행 전에 확언하지 않는다.
CONTINUE는 목적에 맞게 이어가기, SKIP은 안전한 다른 주제로 이동, STOP은 대화 중단이다.
단순히 질문이라는 이유로 CONTINUE의 후속 경험 질문을 CLARIFY로 분류하지 않는다.
기억 결정은 원자 사실별이다. 공통 사실 APPEND와 미확정 사실 HOLD를 같은 turn에 섞을 수 있다.
APPEND/CORRECT에는 fact를, HOLD/NO_WRITE에는 fact=null을 쓴다. alternatives는 미확정 값 후보만 적는 보조정보이며 원문 전사 전체를 복사하지 않는다. APPEND/CORRECT/NO_WRITE의 alternatives는 []로 둔다. HOLD의 slot은 보류할 관계다. 불필요한 HOLD 대신 NO_WRITE를 사용한다. APPEND는 target_fact_id=null,
CORRECT는 기존 fact_id가 필요하다. fact의 subject/relation/value/time은 명시 근거에 맞는
일관된 표현을 쓴다. 본인의 fact.subject는 'participant'로, 행동 speaker_id는 입력 화자 ID(예: p1)로 구분한다. source_turns에는 지금까지 관찰한 t1/t2만 사용한다. 새로운 관계나 시점을
만들지 않는다. 내부 진단이나 조건 이름을 사용자에게 말하지 않는다. JSON 외 텍스트를 출력하지 않는다.
"""


def _public_packet(packet: dict) -> dict:
    _packet(packet)
    history = []
    for item in packet.get("history", []):
        if not isinstance(item, dict) or not isinstance(item.get("role"), str) or not isinstance(item.get("text"), str):
            raise ProtocolError("HISTORY_ITEM")
        history.append({"role": item["role"], "text": item["text"]})
    state = packet.get("db_snapshot", {})
    facts = []
    for item in state.get("facts", []):
        facts.append({key: item[key] for key in ("fact_id", "subject", "relation", "value", "time", "source_turns") if key in item})
    pending = []
    for item in state.get("pending", []):
        pending.append({key: item[key] for key in ("pending_id", "slot", "alternatives", "source_turns", "target_fact_id") if key in item})
    return {
        "episode_id": packet.get("episode_id", packet.get("id", "")),
        "turn_id": packet["turn_id"], "speaker_id": packet["speaker_id"], "history": history,
        "candidates": [{"candidate_id": f"c{index + 1}", "text": text} for index, text in enumerate(packet["alternatives"])],
        "memory_permission": packet["memory_permission"], "db_snapshot": {"facts": facts, "pending": pending},
        "allowed_source_turns": sorted(_allowed_sources(packet)),
    }


def messages(packet: dict, arm: str, stage: str, prior: dict | None = None) -> list[dict[str, str]]:
    """Build a whitelist-only request; S/U prompts are exactly identical.

    D/final, G/draft+final, S and U/beliefs+final. The caller owns the distinct
    arm DB histories; only a verified identical-state request may share raw.
    """
    if arm not in {"D", "G", "S", "U"}:
        raise ProtocolError("UNKNOWN_ARM")
    if (arm == "D" and stage != "final") or (arm == "G" and stage not in {"draft", "final"}) or (arm in {"S", "U"} and stage not in {"beliefs", "final"}):
        raise ProtocolError("ARM_STAGE")
    body = {"input": _public_packet(packet)}
    if stage == "beliefs":
        if prior is not None:
            raise ProtocolError("UNEXPECTED_PRIOR")
        instruction = (
            "각 candidate_id마다 정확히 하나의 belief를 반환한다. 해당 대안을 참이라고 가정할 때 "
            "원문·이전 대화·DB가 지지하는 원자 개인 사실을 facts에 적는다. 같은 사실은 같은 canonical "
            "subject/relation/value/time으로 적되, 실제 값·관계·시점 차이를 억지로 같게 만들지 않는다. "
            "명시 정정은 새 사실을 나타내며 기존 DB값과 동시에 확정하지 않는다. 뜻을 지어내거나 "
            "어느 대안을 미리 버리지 않는다. 개인 사실이 없으면 facts=[]다. 이는 오류 가능 중간 추출이며 "
            "저장 결정이나 사람 정답이 아니다."
        )
        schema = BELIEFS_SCHEMA
    elif arm == "G" and stage == "draft":
        if prior is not None:
            raise ProtocolError("UNEXPECTED_PRIOR")
        instruction = "모든 전사 대안·현재 대화·DB를 함께 검토하고 가장 적절한 응답과 기억 결정 초안을 공통 스키마로 작성한다."
        schema = FINAL_SCHEMA
    else:
        schema = FINAL_SCHEMA
        if arm == "D":
            if prior is not None:
                raise ProtocolError("UNEXPECTED_PRIOR")
            instruction = "모든 근거와 제약을 충분히 검토한 뒤 최종 응답과 원자 사실별 기억 결정을 직접 작성한다."
        elif arm == "G":
            if prior is None:
                raise ProtocolError("PRIOR_REQUIRED")
            if "stage_failure" not in prior:
                validate_final(prior, packet)
            body["fallible_draft"] = copy.deepcopy(prior)
            instruction = (
                "앞선 초안은 틀릴 수 있다. 원문으로 돌아가 모든 대안, 관계 주체, 시점, 누락, 저장 동의, "
                "과도한 확인 질문, 필요한 기록 누락, 실제 질문 문장, 기존 기억 정정을 비판적으로 재검토하라. "
                "초안을 그대로 따를 필요 없이 최종 응답과 기억 결정을 공통 스키마로 작성한다."
            )
        else:
            if prior is None:
                raise ProtocolError("PRIOR_REQUIRED")
            # Retain even incomplete/failing first-stage evidence; the gate
            # separately checks eligibility instead of deleting the response.
            body["fallible_candidate_beliefs"] = copy.deepcopy(prior)
            instruction = (
                "후보별 추출은 틀릴 수 있으므로 원문도 다시 읽는다. 다음에 선택할 행동이 실제로 필요로 하는 "
                "정보(required_slots)와 저장할 사실의 확정 근거를 따로 판단한다. 후보간 다른 값이 행동에 "
                "필요 없으면 그 값을 전제로 하지 않는 대화를 할 수 있다. 행동에 필요한 정보가 다르면 "
                "그 부분을 구체적으로 확인하거나 안전하게 넘긴다. 모든 관련 대안과 확정 DB가 지지하는 "
                "사실만 저장하고 나머지는 보류한다. 충분한 새 정정 근거가 있으면 기존값을 고친다. "
                "실제 사용자 응답과 최종 기억 결정을 공통 스키마로 작성한다."
            )
    prompt = COMMON_INSTRUCTION + "\n" + instruction + "\nJSON schema:\n" + json.dumps(schema, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps(body, ensure_ascii=False, sort_keys=True)}]


def semantic_diagnostics(value: dict, packet: dict) -> list[str]:
    """Record cross-field inconsistencies without relabeling them JSON failures.

    Raw fields are retained. Storage feasibility is still checked by the executor.
    """
    issues=[]
    if packet['speaker_id'] not in {'UNKNOWN','unknown'} and value['action']['speaker_id']!=packet['speaker_id']:
        issues.append('KNOWN_SPEAKER_MISMATCH')
    if value['action']['kind']=='CLARIFY' and value['action']['question_slot'] is None:
        issues.append('CLARIFY_SLOT_REQUIRED')
    if value['action']['kind']!='CLARIFY' and value['action']['question_slot'] is not None:
        issues.append('NONCLARIFY_QUESTION_SLOT')
    for d in value['memory_decisions']:
        if d['operation'] in {'HOLD','NO_WRITE'} and d['fact'] is not None:
            issues.append('UNUSED_FACT_PRESENT')
        if d['operation']=='CORRECT' and d['target_fact_id'] is None:
            issues.append('CORRECT_TARGET_REQUIRED')
        if d['operation'] in {'APPEND','NO_WRITE'} and d['target_fact_id'] is not None:
            issues.append('UNUSED_TARGET_PRESENT')
        sources=set(d['source_turns']) | (set(d['fact']['source_turns']) if d['fact'] is not None else set())
        if not sources <= _allowed_sources(packet):
            issues.append('SOURCE_TURN_NOT_OBSERVED')
        if d['operation'] in {'APPEND','CORRECT'} and d['fact'] is None:
            issues.append('COMMIT_FACT_REQUIRED')
        if d['operation'] in {'APPEND','CORRECT'} and d['fact'] is not None and d['slot'] != d['fact']['relation']:
            issues.append('FACT_SLOT_MISMATCH')
        if d['operation']=='HOLD' and d['slot'] is None:
            issues.append('HOLD_SLOT_REQUIRED')
        if d['operation'] in {'APPEND','CORRECT','NO_WRITE'} and d['alternatives']:
            issues.append('UNUSED_ALTERNATIVES_PRESENT')
    return issues
