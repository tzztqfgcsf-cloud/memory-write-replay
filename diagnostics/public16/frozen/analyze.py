"""Post-collection provisional source/native-state agreement, never human gold."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / "transfer_dev" / "provisional_reference.json"
PUBLIC = HERE.parent / "transfer_dev" / "public_packets.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def score() -> dict:
    freeze_path = HERE / "FREEZE.json"
    if not freeze_path.is_file():
        raise RuntimeError("PARENT_FREEZE_REQUIRED")
    freeze = read(freeze_path)
    if freeze.get("state") != "FROZEN_BY_PARENT":
        raise RuntimeError("PARENT_FREEZE_STATE")
    if digest(REFERENCE) != freeze.get("reference_sha256_for_post_collection_only"):
        raise RuntimeError("FROZEN_REFERENCE_DRIFT")
    if digest(PUBLIC) != freeze.get("sha256", {}).get(
        "../transfer_dev/public_packets.json"
    ):
        raise RuntimeError("FROZEN_PUBLIC_DRIFT")
    refs = {x["case_id"]: x for x in read(REFERENCE)["references"]}
    source = {x["case_id"]: x for x in read(PUBLIC)["packets"]}
    result = {
        "schema": "multiwoz-transfer-development-provisional-analysis-1",
        "reference_sha256": digest(REFERENCE),
        "public_sha256": digest(PUBLIC),
        "human_gold": False,
        "independent_confirmation": False,
        "positive_eligibility": "source-reader provisional same_task_self_repair only",
        "excluded_from_automatic_correctness": [
            x["case_id"]
            for x in refs.values()
            if x["category_source_reader_provisional_not_gold"]
            != "same_task_self_repair"
        ],
        "rows": [],
        "summaries": [],
    }
    for alias in ("gemini25_flash_transfer", "qwen3_32b_transfer"):
        path = HERE / "collection" / alias / "outputs.jsonl"
        if not path.is_file():
            continue
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        for row in rows:
            ref = refs[row["case_id"]]
            packet = source[row["case_id"]]
            category = ref["category_source_reader_provisional_not_gold"]
            eligible = category == "same_task_self_repair"
            focal = []
            if eligible:
                for expected in ref["after_dataset_state_hidden_from_model"]:
                    relation = expected["relation"]
                    before = next(
                        x
                        for x in packet["before_dataset_state"]
                        if x["relation"] == relation
                    )
                    after_facts = [
                        x
                        for x in row["final_snapshot"]["facts"]
                        if x["subject"] == before["subject"]
                        and x["relation"] == relation
                    ]
                    focal.append(
                        len(after_facts) == 1
                        and norm(after_facts[0]["value"])
                        == norm(expected["after_dataset_annotation"])
                    )
            result["rows"].append(
                {
                    "model_alias": alias,
                    "case_id": row["case_id"],
                    "condition": row["condition"],
                    "category_source_reader_provisional_not_gold": category,
                    "generation_valid": row["generation_valid"],
                    "receipt_status": (row.get("receipt") or {}).get("status"),
                    "automatic_correctness_eligible": eligible,
                    "provisional_native_focal_agreement": all(focal)
                    if eligible and focal
                    else None,
                    "focal_slot_count": len(focal),
                    "unscored_annotation_conflict": ref["admissibility"]
                    == "unscored_annotation_conflict",
                }
            )
    grouped = defaultdict(list)
    for row in result["rows"]:
        grouped[(row["model_alias"], row["condition"])].append(row)
    for (alias, condition), rows in sorted(grouped.items()):
        positive = [x for x in rows if x["automatic_correctness_eligible"]]
        result["summaries"].append(
            {
                "model_alias": alias,
                "condition": condition,
                "observed_rows": len(rows),
                "category_counts": dict(
                    Counter(
                        x["category_source_reader_provisional_not_gold"] for x in rows
                    )
                ),
                "generation_valid_rows": sum(x["generation_valid"] for x in rows),
                "provisional_positive_denominator": len(positive),
                "provisional_native_focal_agreement_count": sum(
                    x["provisional_native_focal_agreement"] is True for x in positive
                ),
                "note": "Exact native annotated-value agreement after casefold/whitespace only; source-reader provisional, not semantic or human correctness.",
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    if not args.analyze:
        parser.error(
            "pass --analyze after collection; no analysis is run during collection"
        )
    result = score()
    if not result["rows"]:
        raise RuntimeError("NO_COLLECTION_OUTPUTS")
    output = HERE / "analysis" / "provisional_result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise RuntimeError("ANALYSIS_ALREADY_EXISTS_NO_SILENT_RESCORE")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {"rows": len(result["rows"]), "path": str(output)}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
