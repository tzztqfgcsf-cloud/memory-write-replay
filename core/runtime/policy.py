"""Reference-blind correction gate and receipt-grounded delivery.

The old protocol and SQLite executor are loaded from their frozen files.  No
experiment source, reference, or result is read by this module.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any


_OLD = Path(__file__).resolve().parent / "frozen"


def _load_frozen(name: str) -> Any:
    module_name = f"_sorieum_frozen_20260926_{name}"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _OLD / f"{name}.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load frozen {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[module_name]
        raise
    return module


protocol = _load_frozen("protocol")
# Frozen store.py imports `protocol` by its original bare name. Bind that name
# only while loading the file; store retains the exact frozen module reference.
_prior_protocol = sys.modules.get("protocol")
sys.modules["protocol"] = protocol
try:
    store = _load_frozen("store")
finally:
    if _prior_protocol is None:
        del sys.modules["protocol"]
    else:
        sys.modules["protocol"] = _prior_protocol


WITNESS_KEYS = {
    "candidate_id", "target_fact_id", "subject", "relation", "time",
    "new_value", "source_turn", "evidence_quote", "polarity",
}
POLARITIES = {"affirmed", "negated", "uncertain", "absent"}
POLICIES = {"B", "C", "R", "CR"}


def parse_extraction(raw: str, packet: dict | None = None) -> dict:
    """Parse the first call; preserve negative/incomplete evidence for audit.

    Structural witness errors fail the extraction. Missing candidate/target
    witnesses remain representable and simply cannot rescue a correction.
    """
    if not isinstance(raw, str):
        raise protocol.ProtocolError("EXTRACTION_NOT_TEXT")
    cleaned = raw.strip()
    fence = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", cleaned, re.DOTALL | re.IGNORECASE)
    if fence:
        cleaned = fence.group(1)
    try:
        value = json.loads(cleaned, object_pairs_hook=protocol._unique_object,
                           parse_constant=protocol._invalid_constant)
    except (json.JSONDecodeError, TypeError) as error:
        raise protocol.ProtocolError("EXTRACTION_JSON_PARSE") from error
    if not isinstance(value, dict) or set(value) != {"beliefs", "correction_witnesses"}:
        raise protocol.ProtocolError("EXTRACTION_KEYS")
    protocol._validate_beliefs_shape({"beliefs": value["beliefs"]})
    witnesses = value["correction_witnesses"]
    if not isinstance(witnesses, list):
        raise protocol.ProtocolError("WITNESSES_LIST")
    for row in witnesses:
        if not isinstance(row, dict) or set(row) != WITNESS_KEYS:
            raise protocol.ProtocolError("WITNESS_KEYS")
        for key in WITNESS_KEYS - {"evidence_quote", "polarity"}:
            if not isinstance(row[key], str) or not row[key].strip():
                raise protocol.ProtocolError("WITNESS_" + key.upper())
        if not isinstance(row["evidence_quote"], str):
            raise protocol.ProtocolError("WITNESS_QUOTE")
        if row["polarity"] not in POLARITIES:
            raise protocol.ProtocolError("WITNESS_POLARITY")
        if row["relation"] not in protocol.RELATIONS or row["time"] not in protocol.TIMES:
            raise protocol.ProtocolError("WITNESS_FACT_ENUM")
    if packet is not None:
        protocol._packet(packet)
    return value


def _correction_witness_reason(packet: dict, extraction: dict, decision: dict) -> str:
    """Conservative deterministic checks around fallible model polarity."""
    proposed = decision["fact"]
    target_id = decision["target_fact_id"]
    if proposed is None or not isinstance(target_id, str) or not target_id:
        return "MISSING_PROPOSAL_OR_TARGET"
    matches = [item for item in packet.get("db_snapshot", {}).get("facts", [])
               if item["fact_id"] == target_id]
    if len(matches) != 1:
        return "TARGET_NOT_UNIQUE_OR_MISSING"
    old = matches[0]
    if any(old[key] != proposed[key] for key in ("subject", "relation", "time")):
        return "TARGET_IDENTITY_OR_TIME_CHANGED"
    if old["value"] == proposed["value"]:
        return "VALUE_UNCHANGED"
    if packet["turn_id"] not in proposed["source_turns"] or packet["turn_id"] not in decision["source_turns"]:
        return "CURRENT_SOURCE_NOT_CITED"
    expected = {f"c{index + 1}" for index in range(len(packet["alternatives"]))}
    rows = extraction.get("correction_witnesses", [])
    relevant = [row for row in rows if row["target_fact_id"] == target_id]
    if len(relevant) != len(expected) or {row["candidate_id"] for row in relevant} != expected:
        return "WITNESS_COVERAGE_OR_DUPLICATE"
    for row in relevant:
        index = int(row["candidate_id"][1:]) - 1
        if row["polarity"] != "affirmed":
            return "WITNESS_NOT_AFFIRMED"
        if any(row[key] != proposed[other] for key, other in (
            ("subject", "subject"), ("relation", "relation"), ("time", "time"),
            ("new_value", "value"),
        )):
            return "WITNESS_TUPLE_CONFLICT"
        quote = row["evidence_quote"]
        if not quote or quote not in packet["alternatives"][index] or proposed["value"] not in quote:
            return "WITNESS_QUOTE_NOT_EXACT_OR_VALUE_MISSING"
        if row["source_turn"] != packet["turn_id"]:
            return "WITNESS_SOURCE_TURN_MISMATCH"
    return "CORRECTION_WITNESS_VALID"


def _gated_final(packet: dict, extraction: dict, final: dict, policy: str) -> tuple[dict, list[dict]]:
    old, audit = protocol.apply_gate(final, {"beliefs": extraction["beliefs"]}, packet)
    if policy not in {"C", "CR"}:
        return old, audit
    result = copy.deepcopy(old)
    audit = copy.deepcopy(audit)
    for index, (before, after, row) in enumerate(zip(
        final["memory_decisions"], result["memory_decisions"], audit, strict=True,
    )):
        if before["operation"] != "CORRECT" or after["operation"] != "HOLD":
            continue
        if row["reason"] != "NOT_SUPPORTED_BY_ALL_CANDIDATES" or not row.get("candidate_coverage_valid"):
            row["correction_fallback"] = "OLD_GATE_NOT_ELIGIBLE"
            continue
        reason = _correction_witness_reason(packet, extraction, before)
        row["correction_fallback"] = reason
        if reason == "CORRECTION_WITNESS_VALID":
            result["memory_decisions"][index] = copy.deepcopy(before)
            row["after_operation"] = "CORRECT"
            row["reason"] = "CORRECTION_WITNESS_RESCUED"
    return result, audit


_ACTION_TEXT = {
    "CONTINUE": "이어서 말씀해 주세요.",
    "SKIP": "다른 이야기를 이어가겠습니다.",
    "STOP": "여기서 대화를 마칠게요.",
}
_GENERIC_CLARIFY = "확인이 필요한 부분을 다시 말씀해 주세요."
_SLOT_QUESTIONS = {
    "residence": "어느 지역에 거주하시는지 알려주세요.",
    "birthplace": "어디에서 태어나셨는지 알려주세요.",
    "workplace": "어디에서 일하셨는지 알려주세요.",
    "learned_from": "누구에게 배우셨는지 알려주세요.",
    "hobby": "어떤 취미인지 알려주세요.",
    "meeting_place": "만나는 장소가 어디인지 알려주세요.",
    "preferred_contact": "어떤 연락 방법을 원하시는지 알려주세요.",
    "event_year": "몇 년도에 일어난 일인지 알려주세요.",
    "shop_name": "가게 이름이 무엇인지 알려주세요.",
    "travel_destination": "여행하신 곳이 어디인지 알려주세요.",
    "topic_permission": "이 주제를 계속 이야기해도 될까요?",
    "stop_intent": "대화를 여기서 마칠까요?",
    "recipient": "누구에게 보내면 될까요?",
    "destination": "어디로 가면 될까요?",
    "message_content": "어떤 내용을 보내면 될까요?",
    "application_field": "어떤 신청 항목인지 알려주세요.",
    "meeting_time": "언제 만나기로 하셨나요?",
    "travel_date": "여행 날짜가 언제인가요?",
}


def _receipt_confirms_fact(receipt: dict, row: dict) -> bool:
    after = row.get("after")
    if not isinstance(after, dict) or not isinstance(after.get("fact_id"), str):
        return False
    return any(fact == after for fact in receipt.get("after", {}).get("facts", []))


def render_receipt_reply(receipt: dict, action: dict) -> str:
    """Fixed Korean delivery; positive storage claims require durable receipt."""
    pieces: list[str] = []
    status = receipt.get("status")
    if status == "REJECTED":
        pieces.append("기억을 변경하지 못했습니다.")
    elif status == "ALREADY_APPLIED":
        pieces.append("이번에는 기억을 새로 변경하지 않았습니다.")
    elif status == "APPLIED":
        decisions = receipt.get("decisions", [])
        if receipt.get("read_after_write_verified") is True:
            if any(row.get("operation") == "APPEND" and row.get("status") == "APPLIED"
                   and _receipt_confirms_fact(receipt, row) for row in decisions):
                pieces.append("말씀하신 내용을 기억에 추가했습니다.")
            if any(row.get("operation") == "CORRECT" and row.get("status") == "APPLIED"
                   and _receipt_confirms_fact(receipt, row) for row in decisions):
                pieces.append("기억의 내용을 고쳤습니다.")
        if any(row.get("status") == "BLOCKED_PERMISSION" for row in decisions):
            pieces.append("기억을 저장하지 않았습니다.")
        if not pieces and any(row.get("operation") == "HOLD" for row in decisions):
            pieces.append("확인 전이라 기억으로 확정하지 않았습니다.")
    else:
        pieces.append("기억을 변경하지 못했습니다.")
    if action["kind"] == "CLARIFY":
        pieces.append(_SLOT_QUESTIONS.get(action.get("question_slot"), _GENERIC_CLARIFY))
    else:
        pieces.append(_ACTION_TEXT[action["kind"]])
    return " ".join(pieces)


def apply_policy(packet: dict, extraction: dict, final: dict, policy: str,
                 db_path: str | Path) -> dict:
    """Apply one of four paired policies to one original two-call proposal.

    The caller must use isolated DBs per policy and provide its policy-specific
    snapshot in packet. The returned original reply is never overwritten.
    """
    if policy not in POLICIES:
        raise protocol.ProtocolError("UNKNOWN_POLICY")
    protocol._packet(packet)
    protocol.validate_final(final, packet)
    if not isinstance(extraction, dict) or set(extraction) != {"beliefs", "correction_witnesses"}:
        raise protocol.ProtocolError("EXTRACTION_KEYS")
    # Re-validate direct dict callers with the same strict structural parser.
    extraction = parse_extraction(json.dumps(extraction, ensure_ascii=False))
    gated, audit = _gated_final(packet, extraction, final, policy)
    receipt = store.execute(db_path, gated, packet)
    raw_reply = final["reply"]
    delivered = render_receipt_reply(receipt, final["action"]) if policy in {"R", "CR"} else raw_reply
    return {
        "policy": policy, "raw_reply": raw_reply, "delivered_text": delivered,
        "gated_final": gated, "gate_audit": audit, "audit": audit,
        "receipt": receipt, "final_snapshot": receipt["after"],
    }
