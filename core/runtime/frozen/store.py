"""Isolated SQLite state and receipts for the controlled memory experiment.

All decisions are applied atomically. Permission is a common executor guard,
separate from the S condition's semantic-support gate. This is an episode
sandbox, not a migration or writer for the product's existing memory database.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

import protocol


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS facts (
            fact_id TEXT PRIMARY KEY, subject TEXT NOT NULL,
            relation TEXT NOT NULL, value TEXT NOT NULL, time TEXT NOT NULL,
            source_turns TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pending (
            pending_id TEXT PRIMARY KEY, slot TEXT NOT NULL,
            target_fact_id TEXT, alternatives TEXT NOT NULL, source_turns TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            receipt_id TEXT PRIMARY KEY, turn_id TEXT NOT NULL UNIQUE,
            output_hash TEXT NOT NULL, packet_hash TEXT NOT NULL, receipt TEXT NOT NULL
        );
    """)
    return connection


def _fact(row: sqlite3.Row) -> dict:
    return {
        "fact_id": row["fact_id"], "subject": row["subject"], "relation": row["relation"],
        "value": row["value"], "time": row["time"], "source_turns": json.loads(row["source_turns"]),
    }


def _snapshot(connection: sqlite3.Connection) -> dict:
    facts = [_fact(row) for row in connection.execute("SELECT * FROM facts ORDER BY fact_id")]
    pending = [
        {"pending_id": row["pending_id"], "slot": row["slot"], "target_fact_id": row["target_fact_id"],
         "alternatives": json.loads(row["alternatives"]), "source_turns": json.loads(row["source_turns"])}
        for row in connection.execute("SELECT * FROM pending ORDER BY pending_id")
    ]
    return {"facts": facts, "pending": pending}


def _seed_fact(value: Any) -> dict:
    if not isinstance(value, dict):
        raise protocol.ProtocolError("SEED_FACT_TYPE")
    required = {"fact_id", "subject", "relation", "value", "time"}
    if not required <= set(value) or any(not isinstance(value[key], str) or not value[key].strip() for key in required):
        raise protocol.ProtocolError("SEED_FACT_FIELDS")
    if value["relation"] not in protocol.RELATIONS or value["time"] not in protocol.TIMES:
        raise protocol.ProtocolError("SEED_FACT_ENUM")
    source_turns = value.get("source_turns", [])
    if not isinstance(source_turns, list) or any(not isinstance(item, str) for item in source_turns):
        raise protocol.ProtocolError("SEED_SOURCE_TURNS")
    return {**{key: value[key] for key in required}, "source_turns": source_turns}


def init_db(db_path: str | Path, initial_snapshot: dict | None = None) -> dict:
    """Seed once. Existing episode state is returned unchanged, never reset."""
    state = initial_snapshot or {"facts": [], "pending": []}
    if not isinstance(state, dict) or not isinstance(state.get("facts", []), list) or not isinstance(state.get("pending", []), list):
        raise protocol.ProtocolError("SEED_STATE_SHAPE")
    connection = _connect(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        initialized = connection.execute("SELECT value FROM meta WHERE key='initialized'").fetchone()
        if initialized is None:
            ids = set()
            for raw in state.get("facts", []):
                fact = _seed_fact(raw)
                if fact["fact_id"] in ids:
                    raise protocol.ProtocolError("SEED_DUPLICATE_FACT_ID")
                ids.add(fact["fact_id"])
                connection.execute(
                    "INSERT INTO facts VALUES (?,?,?,?,?,?)",
                    (fact["fact_id"], fact["subject"], fact["relation"], fact["value"], fact["time"], _json(fact["source_turns"])),
                )
            for index, pending in enumerate(state.get("pending", [])):
                if not isinstance(pending, dict) or pending.get("slot") not in protocol.RELATIONS:
                    raise protocol.ProtocolError("SEED_PENDING")
                alternatives = pending.get("alternatives", [])
                source_turns = pending.get("source_turns", [])
                if not isinstance(alternatives, list) or not all(isinstance(item, str) for item in alternatives):
                    raise protocol.ProtocolError("SEED_PENDING_ALTERNATIVES")
                if not isinstance(source_turns, list) or not all(isinstance(item, str) for item in source_turns):
                    raise protocol.ProtocolError("SEED_PENDING_SOURCES")
                connection.execute(
                    "INSERT INTO pending VALUES (?,?,?,?,?)",
                    (pending.get("pending_id", f"seed-pending-{index + 1}"), pending["slot"],
                     pending.get("target_fact_id"), _json(alternatives), _json(source_turns)),
                )
            connection.execute("INSERT INTO meta VALUES ('initialized','true')")
            connection.execute("INSERT INTO meta VALUES ('initial_snapshot_hash',?)", (_digest(_snapshot(connection)),))
        result = _snapshot(connection)
        connection.execute("COMMIT")
        return result
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def snapshot(db_path: str | Path) -> dict:
    """Return committed and pending separately; pending is never a fact result."""
    connection = _connect(db_path)
    try:
        return _snapshot(connection)
    finally:
        connection.close()


def _expected_snapshot(state: dict) -> dict:
    facts = sorted((_seed_fact(fact) for fact in state.get("facts", [])), key=lambda fact: fact["fact_id"])
    pending = []
    for index, item in enumerate(state.get("pending", [])):
        pending.append({
            "pending_id": item.get("pending_id", f"seed-pending-{index + 1}"),
            "slot": item["slot"], "target_fact_id": item.get("target_fact_id"),
            "alternatives": item.get("alternatives", []), "source_turns": item.get("source_turns", []),
        })
    return {"facts": facts, "pending": sorted(pending, key=lambda item: item["pending_id"])}


def _store_fact(connection: sqlite3.Connection, fact_id: str, fact: dict) -> None:
    connection.execute(
        "INSERT INTO facts VALUES (?,?,?,?,?,?)",
        (fact_id, fact["subject"], fact["relation"], fact["value"], fact["time"], _json(fact["source_turns"])),
    )


def _apply_decision(connection: sqlite3.Connection, decision: dict, turn_id: str, index: int) -> dict:
    operation = decision["operation"]
    result = {"index": index, "operation": operation, "status": "APPLIED", "before": None, "after": None}
    if operation == "NO_WRITE":
        result["status"] = "NO_CHANGE"
    elif operation == "HOLD":
        if decision["slot"] is None:
            raise protocol.ProtocolError("HOLD_SLOT_REQUIRED")
        # A slot/target pending entry represents an unresolved memory field.
        # It is intentionally absent from the facts table and its search surface.
        pending_id = "p-" + _digest([decision["slot"], decision["target_fact_id"]])[:20]
        row = connection.execute("SELECT * FROM pending WHERE pending_id=?", (pending_id,)).fetchone()
        if row:
            result["before"] = {"pending_id": pending_id, "slot": row["slot"], "target_fact_id": row["target_fact_id"],
                                "alternatives": json.loads(row["alternatives"]), "source_turns": json.loads(row["source_turns"])}
        connection.execute(
            "INSERT INTO pending VALUES (?,?,?,?,?) ON CONFLICT(pending_id) DO UPDATE SET alternatives=excluded.alternatives, source_turns=excluded.source_turns",
            (pending_id, decision["slot"], decision["target_fact_id"], _json(decision["alternatives"]), _json(decision["source_turns"])),
        )
        result["after"] = {"pending_id": pending_id, "slot": decision["slot"], "target_fact_id": decision["target_fact_id"],
                           "alternatives": decision["alternatives"], "source_turns": decision["source_turns"]}
    else:
        fact = decision["fact"]
        if fact is None:
            raise protocol.ProtocolError("COMMIT_FACT_REQUIRED")
        if operation == "APPEND":
            duplicate = connection.execute(
                "SELECT * FROM facts WHERE subject=? AND relation=? AND value=? AND time=? ORDER BY fact_id LIMIT 1",
                protocol.fact_tuple(fact),
            ).fetchone()
            if duplicate:
                result.update(status="NO_CHANGE_DUPLICATE", before=_fact(duplicate), after=_fact(duplicate))
            else:
                fact_id = "f-" + _digest([turn_id, index, fact])[:20]
                _store_fact(connection, fact_id, fact)
                result["after"] = {"fact_id": fact_id, **fact}
        elif operation == "CORRECT":
            if decision["target_fact_id"] is None:
                raise protocol.ProtocolError("CORRECT_TARGET_REQUIRED")
            target = decision["target_fact_id"]
            row = connection.execute("SELECT * FROM facts WHERE fact_id=?", (target,)).fetchone()
            if row is None:
                raise protocol.ProtocolError("CORRECT_TARGET_MISSING")
            old = _fact(row)
            if old["subject"] != fact["subject"] or old["relation"] != fact["relation"]:
                raise protocol.ProtocolError("CORRECT_TARGET_IDENTITY_MISMATCH")
            result["before"] = old
            connection.execute(
                "UPDATE facts SET value=?,time=?,source_turns=? WHERE fact_id=?",
                (fact["value"], fact["time"], _json(fact["source_turns"]), target),
            )
            result["after"] = {"fact_id": target, **fact}
        else:
            raise protocol.ProtocolError("UNKNOWN_STORE_OPERATION")
        # Per-episode slots concern the participant; target-specific correction
        # pending is resolved only for that target. Other targets are retained.
        connection.execute(
            "DELETE FROM pending WHERE slot=? AND (target_fact_id IS NULL OR target_fact_id=?)",
            (fact["relation"], decision["target_fact_id"] if operation == "CORRECT" else None),
        )
    return result


def execute(db_path: str | Path, output: dict, packet: dict) -> dict:
    """Validate, atomically execute once per turn, and return a persisted receipt.

    Contract/target failures are recorded without partially applying decisions.
    Permission blocks are explicit, common to every condition, and do not edit
    model output. A model's raw storage acknowledgment is not a success receipt.
    """
    init_db(db_path, packet.get("db_snapshot", {"facts": [], "pending": []}))
    connection = _connect(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        before = _snapshot(connection)
        turn_id = packet.get("turn_id", "UNKNOWN")
        output_hash = _digest(output)
        packet_hash = _digest(packet)
        previous = connection.execute("SELECT * FROM events WHERE turn_id=?", (turn_id,)).fetchone()
        if previous:
            prior_receipt = json.loads(previous["receipt"])
            if previous["output_hash"] == output_hash and previous["packet_hash"] == packet_hash:
                connection.execute("COMMIT")
                return {**prior_receipt, "status": "ALREADY_APPLIED", "original_status": prior_receipt["status"]}
            connection.execute("COMMIT")
            return {
                "status": "REJECTED", "reason": "TURN_ALREADY_FINALIZED", "turn_id": turn_id,
                "receipt_id": prior_receipt["receipt_id"], "output_hash": output_hash,
                "before": before, "after": before, "before_hash": _digest(before), "after_hash": _digest(before),
                "permission_blocked": False, "decisions": [], "metadata_preserved": True,
            }
        receipt = {
            "receipt_id": "r-" + _digest([packet.get("episode_id", packet.get("id")), turn_id, output_hash])[:24],
            "episode_id": packet.get("episode_id", packet.get("id")), "turn_id": turn_id,
            "status": "APPLIED", "reason": None, "output_hash": output_hash,
            "permission": packet.get("memory_permission"), "permission_blocked": False,
            "known_speaker_id": packet.get("speaker_id"), "metadata_preserved": True,
            "before": before, "before_hash": _digest(before), "decisions": [],
        }
        connection.execute("SAVEPOINT decisions")
        try:
            protocol.validate_final(output, packet)
            if _expected_snapshot(packet.get("db_snapshot", {})) != before:
                raise protocol.ProtocolError("STATE_SNAPSHOT_MISMATCH")
            for index, decision in enumerate(output["memory_decisions"]):
                if packet["memory_permission"] != "allowed" and decision["operation"] != "NO_WRITE":
                    receipt["permission_blocked"] = True
                    receipt["decisions"].append({"index": index, "operation": decision["operation"],
                                                "status": "BLOCKED_PERMISSION", "before": None, "after": None})
                else:
                    if decision["operation"] in {"APPEND", "CORRECT"}:
                        if decision["fact"] is None:
                            raise protocol.ProtocolError("COMMIT_FACT_REQUIRED")
                        if not decision["fact"]["source_turns"]:
                            raise protocol.ProtocolError("COMMIT_SOURCE_REQUIRED")
                        protocol._validate_sources(decision, packet)
                        protocol._validate_sources(decision["fact"], packet)
                    receipt["decisions"].append(_apply_decision(connection, decision, turn_id, index))
            connection.execute("RELEASE SAVEPOINT decisions")
        except protocol.ProtocolError as error:
            connection.execute("ROLLBACK TO SAVEPOINT decisions")
            connection.execute("RELEASE SAVEPOINT decisions")
            receipt.update(status="REJECTED", reason=error.code, errors=error.errors)
            for row in receipt["decisions"]:
                if row["status"] not in {"BLOCKED_PERMISSION", "NO_CHANGE"}:
                    row["status"] = "ROLLED_BACK"
            receipt["failed_decision_index"] = len(receipt["decisions"])
        after = _snapshot(connection)
        receipt.update(after=after, after_hash=_digest(after), committed_fact_count=len(after["facts"]),
                       pending_count=len(after["pending"]), state_changed=before != after)
        connection.execute(
            "INSERT INTO events VALUES (?,?,?,?,?)",
            (receipt["receipt_id"], turn_id, output_hash, packet_hash, _json(receipt)),
        )
        connection.execute("COMMIT")
        # Querying after COMMIT verifies the durable state, not just the model's proposal.
        receipt["read_after_write_verified"] = _snapshot(connection) == after
        return receipt
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def events(db_path: str | Path) -> list[dict]:
    """Read execution receipts without presenting pending values as facts."""
    connection = _connect(db_path)
    try:
        return [json.loads(row["receipt"]) for row in connection.execute("SELECT receipt FROM events ORDER BY turn_id")]
    finally:
        connection.close()
