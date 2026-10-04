"""Two-call, reference-blind prompts shared across B/C/R/CR."""
from __future__ import annotations

import copy
import json

from . import policy

protocol = policy.protocol

WITNESS_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": sorted(policy.WITNESS_KEYS),
    "properties": {
        "candidate_id": {"type": "string"},
        "target_fact_id": {"type": "string"},
        "subject": {"type": "string"},
        "relation": {"type": "string", "enum": list(protocol.RELATIONS)},
        "time": {"type": "string", "enum": list(protocol.TIMES)},
        "new_value": {"type": "string"},
        "source_turn": {"type": "string", "enum": ["t1", "t2"]},
        "evidence_quote": {"type": "string"},
        "polarity": {"type": "string", "enum": sorted(policy.POLARITIES)},
    },
}
EXTRACTION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["beliefs", "correction_witnesses"],
    "properties": {
        "beliefs": protocol.BELIEFS_SCHEMA["properties"]["beliefs"],
        "correction_witnesses": {"type": "array", "items": WITNESS_SCHEMA},
    },
}


def extraction_messages(packet: dict) -> list[dict[str, str]]:
    """First call: candidate facts and target-indexed correction witnesses."""
    public = protocol._public_packet(packet)
    instruction = (
        "각 전사 대안에 대해 belief를 정확히 하나씩 작성한다. 해당 대안이 지지하는 원자 사실을 "
        "사실 스키마에 기록하고, 불확실한 새값을 억지로 공통 사실로 만들지 않는다. "
        "기존 DB의 각 fact_id와 각 candidate_id 조합에 대해 correction_witness를 하나씩 작성한다. "
        "그 대안이 기존 기억을 새값으로 명시 정정하면 polarity=affirmed, 새값을 부정하면 "
        "negated, 뜻이 불확실하면 uncertain, 정정 근거가 없으면 absent로 적는다. "
        "affirmed는 기존 subject/relation/time을 유지한 정정만 뜻한다. source_turn은 인용한 "
        "현재 발화의 turn_id다. affirmed의 evidence_quote는 해당 candidate text에 문자 그대로 "
        "있는 연속 구절이며 new_value를 포함해야 한다. absent에서는 new_value에 기존 DB값을 "
        "그대로 적고 evidence_quote는 빈 문자열로 둔다. negated/uncertain에서 인용 가능한 "
        "새값이 없으면 new_value에 기존 DB값을 적고 evidence_quote는 빈 문자열로 둔다. "
        "polarity는 모델 제안이며 판정 정답이 아니다. "
        "저장 여부와 사용자 응답은 이 단계에서 결정하지 않는다. JSON만 출력한다."
    )
    system = protocol.COMMON_INSTRUCTION + "\n" + instruction + "\nJSON schema:\n" + json.dumps(
        EXTRACTION_SCHEMA, ensure_ascii=False, sort_keys=True,
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps({"input": public}, ensure_ascii=False, sort_keys=True)},
    ]


def final_messages(packet: dict, extraction: dict) -> list[dict[str, str]]:
    """Second call: one original reply/action/memory proposal for all policies."""
    public = protocol._public_packet(packet)
    if not isinstance(extraction, dict) or set(extraction) != {"beliefs", "correction_witnesses"}:
        raise protocol.ProtocolError("EXTRACTION_KEYS")
    instruction = (
        "앞선 후보별 추출과 정정 witness는 틀릴 수 있다. 모든 원문 대안, 이전 대화, DB, "
        "현재 동의를 다시 확인하고 하나의 최종 원래 제안을 작성한다. action과 memory_decisions를 "
        "분리하고, 명시적 정정이 충분히 분명하면 기존 fact_id를 CORRECT한다. 실제 DB 실행 "
        "전이므로 reply에서 저장 성공을 확언하지 않는다. 이후 정책별 게이트와 실행은 별도로 "
        "처리된다. JSON만 출력한다."
    )
    system = protocol.COMMON_INSTRUCTION + "\n" + instruction + "\nJSON schema:\n" + json.dumps(
        protocol.FINAL_SCHEMA, ensure_ascii=False, sort_keys=True,
    )
    body = {"input": public, "fallible_extraction": copy.deepcopy(extraction)}
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(body, ensure_ascii=False, sort_keys=True)},
    ]
