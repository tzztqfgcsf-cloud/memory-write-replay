"""Explicit v2 erratum: obsolete fact version retirement differs from ID deletion.

The original evaluator, reference and scores remain untouched. This module
supports an explicit reference migration for the diagnosed correction mismatch.
It never imports a model runtime, regenerates an output, or repairs a proposal.
"""
from __future__ import annotations

import argparse
import csv
import copy
import json
import math
from pathlib import Path
import random
import re
from typing import Any


AMENDMENT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
SEED = 20260927
BOOTSTRAP_REPLICATES = 5000
EXPECTED_MODELS = 5
EXPECTED_CONDITIONS = 7
EXPECTED_REPEATS = 3
EXPECTED_CASES = {"dev": 12, "test": 48}
EXPECTED_SPLIT_REPEATS = {"dev": 1, "test": 3}
FACT_FIELDS = ("subject", "relation", "value", "time")
SCORE_FIELDS = (
    "model_alias", "split", "case_id", "family", "repeat", "condition", "upstream_call_ids",
    "positive_eligible", "correction_eligible", "generation_valid", "provider_failure",
    "parse_failure", "generation_failure_unclassified", "invalid_final", "action_allowed",
    "required_present", "forbidden_absent", "preserve_ids_exact", "remove_ids_absent",
    "no_extra_facts", "obsolete_versions_absent", "whole_state_compliance", "positive_joint", "correction_recovery",
    "negative_preservation", "missed_clarification", "unnecessary_clarification",
    "extra_write", "harmful_write", "completed_write_claim", "unsupported_write_claim",
)


def _fact_tuple(value: Any) -> tuple[str, str, str, str]:
    if isinstance(value, dict):
        parts = tuple(value.get(field) for field in FACT_FIELDS)
    elif isinstance(value, (list, tuple)) and len(value) == 4:
        parts = tuple(value)
    else:
        raise ValueError("Fact must contain exact subject/relation/value/time")
    if not all(isinstance(part, str) and part for part in parts):
        raise ValueError("Fact tuple fields must be nonempty strings")
    return parts  # type: ignore[return-value]


def _fact_map(facts: Any) -> dict[str, tuple[str, str, str, str]]:
    if not isinstance(facts, list):
        raise ValueError("Snapshot facts must be a list")
    result = {}
    for fact in facts:
        if not isinstance(fact, dict) or not isinstance(fact.get("fact_id"), str):
            raise ValueError("Snapshot fact requires fact_id")
        fact_id = fact["fact_id"]
        if fact_id in result:
            raise ValueError("Duplicate snapshot fact_id")
        result[fact_id] = _fact_tuple(fact)
    return result


def _packet(public_row: dict) -> dict:
    packet = public_row.get("packet", public_row)
    if not isinstance(packet, dict) or not isinstance(packet.get("db_snapshot"), dict):
        raise ValueError("Public row requires packet.db_snapshot")
    return packet


def _case_id(row: dict) -> str:
    packet = row.get("packet", {})
    value = row.get("case_id", packet.get("case_id", packet.get("id")))
    if not isinstance(value, str) or not value:
        raise ValueError("Row requires case_id")
    return value


def _reference_spec(reference: dict, initial: dict[str, tuple[str, str, str, str]]) -> dict:
    required = {_fact_tuple(item) for item in reference["required_facts"]}
    forbidden = {_fact_tuple(item) for item in reference["forbidden_facts"]}
    preserve = set(reference["must_preserve_ids"])
    remove = set(reference["must_remove_ids"])
    retire = set(reference.get("must_retire_versions", []))
    if not all(isinstance(item, str) for item in preserve | remove | retire):
        raise ValueError("Reference IDs must be strings")
    if (not (preserve | remove | retire) <= set(initial)
            or preserve & (remove | retire) or remove & retire):
        raise ValueError("Reference preserve/remove/retire IDs conflict with initial snapshot")
    allowed = set(reference["allowed_actions"])
    if not allowed or not all(isinstance(item, str) for item in allowed):
        raise ValueError("Reference allowed_actions must be nonempty strings")
    clarification = reference["requires_clarification"]
    if clarification not in {"required", "optional", "unnecessary"}:
        raise ValueError("Unknown requires_clarification")
    return {
        "required": required, "forbidden": forbidden, "preserve": preserve, "remove": remove,
        "retire": retire,
        "allowed": allowed, "clarification": clarification,
        "positive_eligible": bool(required - set(initial.values()) or remove or retire),
        "correction_eligible": bool(remove or retire),
    }


def migrate_correction_reference(public_row: dict, reference: dict) -> dict:
    """Copy the diagnosed reference convention; reject ambiguous migrations.

    Every old removal target must have exactly one required replacement in
    the same subject/relation/time and its old value must already be forbidden.
    All other reference fields and original files are preserved.
    """
    if "must_retire_versions" in reference:
        raise ValueError("Reference already carries v2 retirement semantics")
    initial = _fact_map(_packet(public_row)["db_snapshot"]["facts"])
    spec = _reference_spec(reference, initial)
    for target in spec["remove"]:
        old = initial[target]
        replacements = {fact for fact in spec["required"]
                        if (fact[0], fact[1], fact[3]) == (old[0], old[1], old[3])
                        and fact != old}
        if old not in spec["forbidden"] or len(replacements) != 1:
            raise ValueError("Ambiguous correction migration; review deletion semantics separately")
    migrated = copy.deepcopy(reference)
    migrated["must_retire_versions"] = list(reference["must_remove_ids"])
    migrated["must_remove_ids"] = []
    return migrated


def _generation_status(output: dict) -> tuple[bool, bool, bool, bool]:
    diagnostics = output.get("parse_errors") or []
    if not isinstance(diagnostics, list):
        diagnostics = [diagnostics]
    provider_failure = any(str(item).startswith("PROVIDER_") for item in diagnostics)
    parse_failure = any(not str(item).startswith("PROVIDER_") for item in diagnostics)
    # Earlier extraction errors remain diagnostics if a planned later call
    # produced a valid final proposal. Collector generation_valid owns that
    # final-stage status; shape and snapshot are checked separately below.
    valid = output.get("generation_valid") is True
    unclassified = not valid and not parse_failure and not provider_failure
    return valid, provider_failure, parse_failure, unclassified


def _final_shape_valid(proposal: Any) -> bool:
    if not isinstance(proposal, dict) or set(proposal) != {"reply", "action", "memory_decisions"}:
        return False
    if not isinstance(proposal["reply"], str) or not proposal["reply"].strip():
        return False
    action = proposal["action"]
    if not isinstance(action, dict) or set(action) != {"kind", "speaker_id", "required_slots", "question_slot"}:
        return False
    if not isinstance(action["kind"], str) or action["kind"] not in {"CONTINUE", "CLARIFY", "SKIP", "STOP"}:
        return False
    if not isinstance(action["speaker_id"], str) or not isinstance(action["required_slots"], list):
        return False
    if not all(isinstance(slot, str) for slot in action["required_slots"]):
        return False
    if action["question_slot"] is not None and not isinstance(action["question_slot"], str):
        return False
    decisions = proposal["memory_decisions"]
    if not isinstance(decisions, list):
        return False
    keys = {"operation", "target_fact_id", "fact", "slot", "alternatives", "source_turns"}
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != keys:
            return False
        if not isinstance(decision["operation"], str) or decision["operation"] not in {"APPEND", "CORRECT", "HOLD", "NO_WRITE"}:
            return False
        if decision["target_fact_id"] is not None and not isinstance(decision["target_fact_id"], str):
            return False
        if decision["fact"] is not None:
            if not isinstance(decision["fact"], dict) or set(decision["fact"]) != {
                "subject", "relation", "value", "time", "source_turns",
            }:
                return False
            try:
                _fact_tuple(decision["fact"])
            except ValueError:
                return False
            if not isinstance(decision["fact"].get("source_turns"), list):
                return False
        if decision["slot"] is not None and not isinstance(decision["slot"], str):
            return False
        if not isinstance(decision["alternatives"], list) or not isinstance(decision["source_turns"], list):
            return False
    return True


_COMPLETED_ADD_SENTENCES = {
    "말씀하신 내용을 기억에 추가했습니다", "기억에 추가했습니다", "기억에 저장했습니다",
    "기억을 저장했습니다", "기억에 기록했습니다", "기억을 기록했습니다",
}
_COMPLETED_CORRECT_SENTENCES = {
    "기억의 내용을 고쳤습니다", "기억을 수정했습니다", "기억을 정정했습니다",
}


def _receipt_confirms(receipt: dict, final_map: dict, operation: str) -> bool:
    if receipt.get("status") != "APPLIED" or receipt.get("read_after_write_verified") is not True:
        return False
    try:
        receipt_map = _fact_map(receipt["after"]["facts"])
    except (KeyError, TypeError, ValueError):
        return False
    if receipt_map != final_map:
        return False
    for row in receipt.get("decisions", []):
        if row.get("operation") != operation or row.get("status") != "APPLIED":
            continue
        after = row.get("after")
        if isinstance(after, dict):
            try:
                if final_map.get(after.get("fact_id")) == _fact_tuple(after):
                    return True
            except ValueError:
                continue
    return False


def _write_claim_diagnostic(output: dict, final_map: dict) -> tuple[bool, bool]:
    delivered = output.get("delivered_text")
    if not isinstance(delivered, str):
        return False, False
    # Only exact completed-writing sentences count. This deliberately misses
    # paraphrases and avoids treating past-context or planned actions as a
    # current execution claim.
    sentences = {part.strip() for part in re.split(r"[.!?]\s*", delivered) if part.strip()}
    add = bool(sentences & _COMPLETED_ADD_SENTENCES)
    correct = bool(sentences & _COMPLETED_CORRECT_SENTENCES)
    receipt = output.get("receipt")
    if not isinstance(receipt, dict):
        receipt = {}
    unsupported = (add and not _receipt_confirms(receipt, final_map, "APPEND")) or (
        correct and not _receipt_confirms(receipt, final_map, "CORRECT")
    )
    return add or correct, unsupported


def score_output(output: dict, public_row: dict, reference: dict) -> dict:
    """Score one output; invalid generations can never pass safety or joint goals."""
    packet = _packet(public_row)
    initial = _fact_map(packet["db_snapshot"]["facts"])
    spec = _reference_spec(reference, initial)
    valid, provider_failure, parse_failure, unclassified = _generation_status(output)
    proposal = output.get("final_proposal")
    action = proposal.get("action", {}).get("kind") if isinstance(proposal, dict) else None
    if not _final_shape_valid(proposal):
        valid = False
    snapshot = output.get("final_snapshot")
    try:
        final_map = _fact_map(snapshot["facts"] if isinstance(snapshot, dict) else None)
    except (KeyError, TypeError, ValueError):
        final_map = {}
        valid = False
    final_tuples = set(final_map.values())
    initial_tuples = set(initial.values())
    required_present = spec["required"] <= final_tuples
    forbidden_absent = not (spec["forbidden"] & final_tuples)
    preserve_exact = all(final_map.get(item) == initial[item] for item in spec["preserve"])
    remove_absent = not (spec["remove"] & set(final_map))
    obsolete_absent = not ({initial[item] for item in spec["retire"]} & final_tuples)
    extra = final_tuples - initial_tuples - spec["required"]
    no_extra = not extra
    action_allowed = action in spec["allowed"]
    state_ok = all((required_present, forbidden_absent, preserve_exact, remove_absent,
                    obsolete_absent, no_extra))
    positive_joint = bool(valid and spec["positive_eligible"] and action_allowed and state_ok)
    correction_recovery = bool(valid and spec["correction_eligible"] and action_allowed and state_ok)
    # Negative preservation is a separate state-only measure on cases needing
    # no positive change; it does not inherit action correctness.
    negative_preservation = bool(valid and not spec["positive_eligible"] and state_ok)
    clarification = spec["clarification"]
    missed = bool(valid and clarification == "required" and action != "CLARIFY")
    unnecessary = bool(valid and clarification == "unnecessary" and action == "CLARIFY")
    newly_forbidden = bool((final_tuples - initial_tuples) & spec["forbidden"])
    # Stale retention of a must-remove ID is failed correction, not an
    # additional harmful write. A newly forbidden tuple or damaged protected
    # original ID is counted as harmful state change.
    harmful = bool(extra or newly_forbidden or not preserve_exact)
    claimed, unsupported = _write_claim_diagnostic(output, final_map)
    family = next((value for value in (
        public_row.get("family"), public_row.get("problem_family"), public_row.get("case_family"),
        packet.get("family"), packet.get("problem_family"), packet.get("case_family"),
    ) if isinstance(value, str) and value), "")
    return {
        "model_alias": output["model_alias"], "split": output["split"],
        "case_id": output["case_id"], "family": family, "repeat": output["repeat"],
        "condition": output["condition"],
        "upstream_call_ids": json.dumps(output.get("upstream_call_ids", []), ensure_ascii=False, sort_keys=True),
        "positive_eligible": spec["positive_eligible"], "correction_eligible": spec["correction_eligible"],
        "generation_valid": valid, "provider_failure": provider_failure,
        "parse_failure": parse_failure, "generation_failure_unclassified": unclassified,
        "invalid_final": not valid, "action_allowed": bool(valid and action_allowed),
        "required_present": bool(valid and required_present),
        "forbidden_absent": bool(valid and forbidden_absent),
        "preserve_ids_exact": bool(valid and preserve_exact),
        "remove_ids_absent": bool(valid and remove_absent),
        "no_extra_facts": bool(valid and no_extra),
        "obsolete_versions_absent": bool(valid and obsolete_absent),
        "whole_state_compliance": bool(valid and state_ok),
        "positive_joint": positive_joint, "correction_recovery": correction_recovery,
        "negative_preservation": negative_preservation,
        "missed_clarification": missed, "unnecessary_clarification": unnecessary,
        "extra_write": bool(valid and extra), "harmful_write": bool(valid and harmful),
        "completed_write_claim": claimed, "unsupported_write_claim": unsupported,
    }


def score_records(outputs: list[dict], public_rows: list[dict], references: list[dict], split: str) -> list[dict]:
    selected_public = [row for row in public_rows if row.get("split", _packet(row).get("split")) == split]
    publics = {_case_id(row): row for row in selected_public}
    if len(publics) != len(selected_public):
        raise ValueError("Duplicate public case_id")
    selected_refs = [row for row in references if _case_id(row) in publics]
    refs = {_case_id(row): row for row in selected_refs}
    if len(refs) != len(selected_refs):
        raise ValueError("Duplicate reference case_id")
    if not publics or set(publics) != set(refs):
        raise ValueError("Public/reference split cases differ or are empty")
    seen = set()
    scored = []
    for output in outputs:
        if output.get("split") != split:
            continue
        key = (output["model_alias"], output["case_id"], str(output["repeat"]), output["condition"])
        if key in seen:
            raise ValueError("Duplicate output unit")
        seen.add(key)
        if output["case_id"] not in publics:
            raise ValueError("Output case absent from public/reference split")
        scored.append(score_output(output, publics[output["case_id"]], refs[output["case_id"]]))
    return scored


def _unit_map(rows: list[dict], model: str, condition: str, eligible_field: str | None,
              outcome_field: str) -> dict[tuple[str, str], bool]:
    return {(row["case_id"], str(row["repeat"])): bool(row[outcome_field])
            for row in rows if row["model_alias"] == model and row["condition"] == condition
            and (eligible_field is None or row[eligible_field])}


def _paired_stats(rows: list[dict], model: str, left: str, right: str,
                  eligible: str | None, outcome: str) -> tuple[dict, dict[str, list[tuple[bool, bool]]]]:
    a = _unit_map(rows, model, left, eligible, outcome)
    b = _unit_map(rows, model, right, eligible, outcome)
    if set(a) != set(b):
        raise ValueError(f"Missing paired {left}/{right} units for {model}")
    by_case: dict[str, list[tuple[bool, bool]]] = {}
    gains = harms = 0
    for (case_id, repeat), value in sorted(a.items()):
        other = b[(case_id, repeat)]
        gains += value and not other
        harms += other and not value
        by_case.setdefault(case_id, []).append((value, other))
    case_deltas = {case_id: (sum(x for x, _ in pairs) - sum(y for _, y in pairs)) / len(pairs)
                   for case_id, pairs in by_case.items()}
    return {
        "eligible_cases": len(by_case), "paired_repeated_units": len(a),
        "raw_gain_units": gains, "raw_harm_units": harms,
        "left_rate": sum(a.values()) / len(a) if a else None,
        "right_rate": sum(b.values()) / len(b) if b else None,
        "case_mean_effect": sum(case_deltas.values()) / len(case_deltas) if case_deltas else None,
        "case_mean_deltas": case_deltas,
    }, by_case


def _percentile(sorted_values: list[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def _bootstrap_ci(case_deltas: dict[str, float], seed: int) -> list[float] | None:
    values = list(case_deltas.values())
    if not values:
        return None
    rng = random.Random(seed)
    draws = sorted(sum(rng.choice(values) for _ in values) / len(values)
                   for _ in range(BOOTSTRAP_REPLICATES))
    return [_percentile(draws, 0.025), _percentile(draws, 0.975)]


def _exact_mcnemar(by_case: dict[str, list[tuple[bool, bool]]]) -> dict:
    better = worse = 0
    for pairs in by_case.values():
        if len(pairs) != EXPECTED_REPEATS:
            raise ValueError("McNemar requires three repeats per case")
        a = sum(x for x, _ in pairs) >= 2
        b = sum(y for _, y in pairs) >= 2
        better += a and not b
        worse += b and not a
    discordant = better + worse
    p = min(1.0, 2 * sum(math.comb(discordant, k) for k in range(min(better, worse) + 1))
            / (2 ** discordant)) if discordant else 1.0
    return {"cr_only": better, "g_only": worse, "discordant_cases": discordant,
            "exact_two_sided_p": p}


def _holm(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=lambda model: (p_values[model], model))
    adjusted = {}
    running = 0.0
    count = len(ordered)
    for rank, model in enumerate(ordered):
        running = max(running, min(1.0, (count - rank) * p_values[model]))
        adjusted[model] = running
    return adjusted


def _model_complete(rows: list[dict], model: str, design_cases: set[str], repeat_count: int) -> bool:
    subset = [row for row in rows if row["model_alias"] == model]
    conditions = {row["condition"] for row in subset}
    repeats = {str(row["repeat"]) for row in subset}
    return (
        len(conditions) == EXPECTED_CONDITIONS and {"B", "C", "R", "CR", "G"} <= conditions
        and {row["case_id"] for row in subset} == design_cases and len(repeats) == repeat_count
        and len(subset) == len(design_cases) * EXPECTED_CONDITIONS * repeat_count
    )


def summarize(rows: list[dict], *, split: str = "test", expected_case_ids: set[str] | None = None,
              enforce_design: bool = False, planned_models: list[str] | None = None) -> dict:
    models = sorted({row["model_alias"] for row in rows})
    conditions = sorted({row["condition"] for row in rows})
    cases = {row["case_id"] for row in rows}
    design_cases = expected_case_ids if expected_case_ids is not None else cases
    expected_repeats = EXPECTED_SPLIT_REPEATS[split]
    expected_total = EXPECTED_MODELS * EXPECTED_CONDITIONS * len(design_cases) * expected_repeats
    if len(rows) > expected_total:
        raise ValueError("More rows than the bounded design allows")
    if len({(row["model_alias"], row["condition"], row["case_id"], str(row["repeat"])) for row in rows}) != len(rows):
        raise ValueError("Duplicate model/condition/case/repeat unit")
    complete_models = {model: _model_complete(rows, model, design_cases, expected_repeats)
                       for model in models}
    complete = len(models) == EXPECTED_MODELS and all(complete_models.values()) and len(rows) == expected_total
    if enforce_design:
        if len(design_cases) != EXPECTED_CASES[split]:
            raise ValueError("Public split case count differs from frozen design")
        if planned_models is not None and (len(set(planned_models)) != EXPECTED_MODELS or not set(models) <= set(planned_models)):
            raise ValueError("Planned model aliases must contain five unique names including observed models")
    aggregate = {}
    for model in models:
        aggregate[model] = {}
        for condition in conditions:
            subset = [row for row in rows if row["model_alias"] == model and row["condition"] == condition]
            counts = {"units": len(subset), **{
                field: sum(bool(row[field]) for row in subset)
                for field in SCORE_FIELDS if field not in {
                    "model_alias", "split", "case_id", "family", "repeat", "condition", "upstream_call_ids",
                }
            }}
            valid_count = counts["generation_valid"]
            negative_eligible = len(subset) - counts["positive_eligible"]
            counts["rates"] = {
                "whole_state_compliance_per_total": counts["whole_state_compliance"] / len(subset) if subset else None,
                "extra_write_per_total": counts["extra_write"] / len(subset) if subset else None,
                "invalid_final_per_total": counts["invalid_final"] / len(subset) if subset else None,
                "provider_failure_per_total": counts["provider_failure"] / len(subset) if subset else None,
                "parse_failure_per_total": counts["parse_failure"] / len(subset) if subset else None,
                "whole_state_compliance_per_valid": counts["whole_state_compliance"] / valid_count if valid_count else None,
                "extra_write_per_valid": counts["extra_write"] / valid_count if valid_count else None,
                "positive_joint_per_eligible": counts["positive_joint"] / counts["positive_eligible"] if counts["positive_eligible"] else None,
                "correction_recovery_per_eligible": counts["correction_recovery"] / counts["correction_eligible"] if counts["correction_eligible"] else None,
                "negative_preservation_per_eligible": counts["negative_preservation"] / negative_eligible if negative_eligible else None,
            }
            aggregate[model][condition] = counts
    comparisons = {}
    raw_p = {}
    if enforce_design and split != "test":
        return {
            "method": "authored_reference_exact_state_not_semantic_human_gold",
            "analysis_status": "PARTIAL_DESCRIPTIVE" if not complete else "DEV_DESCRIPTIVE",
            "expected_units": expected_total, "observed_units": len(rows),
            "missing_units": expected_total - len(rows),
            "models": models, "conditions": conditions, "repeat_count": expected_repeats,
            "model_complete": complete_models,
            "aggregate": aggregate, "paired_comparisons": {},
            "claim_diagnostic": "Exact completed memory-writing sentences only; lower-bound textual flag, not semantic accuracy or human preference.",
        }
    for index, model in enumerate(models):
        if enforce_design and not complete_models[model]:
            comparisons[model] = {"status": "PARTIAL_NOT_TESTED", "p_used_for_holm": 1.0,
                                  "CR_minus_G_positive_joint": None,
                                  "C_minus_B_correction_recovery": None,
                                  "C_minus_B_harmful_writes_descriptive": None}
            continue
        if {"CR", "G"} <= set(conditions):
            primary, case_pairs = _paired_stats(rows, model, "CR", "G", "positive_eligible", "positive_joint")
            primary["bootstrap_seed"] = SEED + index
            primary["bootstrap_replicates"] = BOOTSTRAP_REPLICATES
            primary["case_cluster_ci95"] = _bootstrap_ci(primary["case_mean_deltas"], SEED + index)
            primary["majority_of_three_mcnemar"] = _exact_mcnemar(case_pairs)
            raw_p[model] = primary["majority_of_three_mcnemar"]["exact_two_sided_p"]
        else:
            primary = None
        correction = None
        harmful = None
        if {"C", "B"} <= set(conditions):
            correction, _ = _paired_stats(rows, model, "C", "B", "correction_eligible", "correction_recovery")
            harmful, _ = _paired_stats(rows, model, "C", "B", None, "harmful_write")
            harmful = {"eligible_cases": harmful["eligible_cases"],
                       "paired_repeated_units": harmful["paired_repeated_units"],
                       "new_harm_units_C_only": harmful["raw_gain_units"],
                       "harm_removed_units_B_only": harmful["raw_harm_units"],
                       "case_mean_harm_effect_C_minus_B": harmful["case_mean_effect"]}
        comparisons[model] = {"CR_minus_G_positive_joint": primary,
                              "C_minus_B_correction_recovery": correction,
                              "C_minus_B_harmful_writes_descriptive": harmful}
    family_names = planned_models if planned_models is not None else models
    uncomputed_names = [model for model in family_names if model not in raw_p]
    padding = EXPECTED_MODELS - len(raw_p) - len(uncomputed_names)
    holm_inputs = {**raw_p, **{name: 1.0 for name in uncomputed_names}}
    holm_inputs.update({f"__uncomputed_{i+1}": 1.0 for i in range(max(padding, 0))})
    adjusted = _holm(holm_inputs)
    for model, p in adjusted.items():
        if model in raw_p:
            comparisons[model]["CR_minus_G_positive_joint"]["majority_of_three_mcnemar"]["holm_p_across_models"] = p
    for model in uncomputed_names:
        comparisons.setdefault(model, {"status": "NOT_COLLECTED", "p_used_for_holm": 1.0,
                                      "CR_minus_G_positive_joint": None,
                                      "C_minus_B_correction_recovery": None,
                                      "C_minus_B_harmful_writes_descriptive": None})
    return {
        "method": "authored_reference_exact_state_not_semantic_human_gold",
        "analysis_status": "COMPLETE_TEST" if complete and split == "test" else (
            "PARTIAL_WITH_COMPLETE_MODEL_RESULTS" if enforce_design and raw_p else
            "PARTIAL_DESCRIPTIVE" if enforce_design else "SYNTHETIC_OR_UNENFORCED"
        ),
        "expected_units": expected_total, "observed_units": len(rows), "missing_units": expected_total - len(rows),
        "models": models, "conditions": conditions, "repeat_count": expected_repeats,
        "model_complete": complete_models,
        "holm_family": {"planned_size": EXPECTED_MODELS, "tested_model_count": len(raw_p),
                        "uncomputed_model_count": EXPECTED_MODELS - len(raw_p),
                        "uncomputed_aliases": uncomputed_names, "uncomputed_p_for_adjustment": 1.0},
        "bootstrap_seed": SEED, "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "aggregate": aggregate, "paired_comparisons": comparisons,
        "claim_diagnostic": "Explicit completed memory-writing phrases only; lower-bound textual flag, not semantic accuracy or human preference.",
    }


def _read_rows(path: Path, collection_keys: tuple[str, ...]) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    value = json.loads(path.read_text())
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in collection_keys:
            if isinstance(value.get(key), list):
                return value[key]
        if all(isinstance(row, dict) for row in value.values()):
            return [{"case_id": case_id, **row} for case_id, row in value.items()]
    raise ValueError(f"Unsupported row container: {path.name}")


def _write_once(rows: list[dict], result: dict, split: str, out_dir: Path) -> None:
    target = out_dir / split
    scores_path = target / "scores.csv"
    result_path = target / "result.json"
    if scores_path.exists() or result_path.exists():
        raise FileExistsError("Analysis output already exists; frozen results are not overwritten")
    target.mkdir(parents=True, exist_ok=True)
    with scores_path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCORE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    try:
        with result_path.open("x") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
    except BaseException:
        scores_path.unlink()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.add_argument("--public", type=Path, default=ROOT / "data" / "public.json")
    parser.add_argument("--reference", type=Path, default=ROOT / "data" / "reference.json")
    parser.add_argument("--outputs", type=Path, action="append", default=None,
                        help="Repeat for explicit lane files; otherwise discover collection/{split}/*/outputs.jsonl")
    parser.add_argument("--collection-dir", type=Path, default=ROOT / "collection")
    parser.add_argument("--model-alias", action="append", default=None,
                        help="Repeat five times to name the planned Holm family, including stopped lanes")
    parser.add_argument("--analysis-dir", type=Path, default=AMENDMENT / "analysis")
    parser.add_argument("--migrate-correction-reference", action="store_true",
                        help="Explicitly migrate obsolete-version targets on the selected split")
    args = parser.parse_args(argv)
    if args.analysis_dir.resolve() == (ROOT / "analysis").resolve():
        raise ValueError("The original analysis directory is read-only for this erratum")
    public = _read_rows(args.public, ("cases", "rows", "packets"))
    reference = _read_rows(args.reference, ("cases", "rows", "references"))
    public = [row for row in public if row.get("split", _packet(row).get("split")) == args.split]
    public_by_id = {_case_id(row): row for row in public}
    reference = [row for row in reference if _case_id(row) in public_by_id]
    migrated_targets = 0
    if args.migrate_correction_reference:
        migrated_targets = sum(len(row["must_remove_ids"]) for row in reference)
        reference = [migrate_correction_reference(public_by_id[_case_id(row)], row)
                     for row in reference]
    output_paths = args.outputs or sorted((args.collection_dir / args.split).glob("*/outputs.jsonl"))
    if not output_paths:
        raise FileNotFoundError("No collected output lane files found")
    outputs = []
    for path in output_paths:
        lane_rows = _read_rows(path, ("outputs", "rows"))
        if args.outputs is None and any(row.get("model_alias") != path.parent.name for row in lane_rows):
            raise ValueError("Collection lane directory and model_alias disagree")
        outputs.extend(lane_rows)
    scores = score_records(outputs, public, reference, args.split)
    public_ids = {_case_id(row) for row in public if row.get("split", _packet(row).get("split")) == args.split}
    discovered_aliases = sorted(path.name for path in (args.collection_dir / args.split).iterdir()
                                if path.is_dir()) if (args.collection_dir / args.split).is_dir() else []
    planned_models = args.model_alias or (discovered_aliases if len(discovered_aliases) == EXPECTED_MODELS else None)
    result = summarize(scores, split=args.split, expected_case_ids=public_ids,
                       enforce_design=True, planned_models=planned_models)
    result["evaluation_amendment"] = {
        "version": "obsolete_fact_version_v2",
        "migration_requested": args.migrate_correction_reference,
        "migrated_targets": migrated_targets,
        "post_output_erratum": True,
        "new_model_calls": 0,
        "original_scores_preserved": True,
    }
    _write_once(scores, result, args.split, args.analysis_dir)
    print(json.dumps({"split": args.split, "status": result["analysis_status"],
                      "units": len(scores), "expected_units": result["expected_units"],
                      "missing_units": result["missing_units"], "models": len(result["models"]),
                      "conditions": len(result["conditions"]),
                      "invalid_final": sum(row["invalid_final"] for row in scores),
                      "analysis_dir": str(args.analysis_dir / args.split)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
