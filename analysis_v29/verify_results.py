"""Verify the variant-tolerant analysis results and strictly re-score the 1,152 saved Allow outputs.

Standard library only; no model calls or policy execution. Run after
rescore_variant_tolerant.py and keep --report outside the archival data.
"""
import argparse
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
from runtime import evaluate as ev  # noqa: E402 -- import the archived, repository-local runtime


def key(row):
    return tuple(str(row[field]) for field in ("model_alias", "case_id", "repeat", "condition"))


def verify(results_path):
    expected = json.loads((Path(__file__).parent / "expected_results.json").read_text())
    actual = json.loads(results_path.read_text())
    with gzip.open(ROOT / "core/data/cases.json.gz", "rt") as stream:
        cases = json.load(stream)
    with gzip.open(ROOT / "core/data/episodes.json.gz", "rt") as stream:
        episodes = json.load(stream)
    by_case = {e["case_id"]: e for e in episodes}
    allow_dir = ROOT / "diagnostics/saved_allow"
    with (allow_dir / "scores.csv").open(newline="") as stream:
        saved = list(csv.DictReader(stream))
    expected_allow = {key(row): row for row in saved}
    seen = set()
    mismatch_count = 0
    examples = []
    with (allow_dir / "outputs.jsonl").open() as stream:
        for line in stream:
            output = json.loads(line)
            unit = key(output)
            if unit in seen:
                raise ValueError("Duplicate saved Allow output key")
            seen.add(unit)
            episode = by_case[output["case_id"]]
            score = ev.score_output(output, cases["public_rows"][episode["public_row_id"]],
                                    cases["references"][episode["reference_id"]])
            expected_score = expected_allow.get(unit)
            fields = list(ev.SCORE_FIELDS)
            different = fields if expected_score is None else [
                field for field in fields if str(score[field]) != str(expected_score[field])
            ]
            mismatch_count += bool(different)
            if different and len(examples) < 10:
                examples.append({"unit": unit, "fields": different})
    missing = set(expected_allow) - seen
    equal = actual == expected
    passed = (equal and actual["archived_rows_compared"] == 42336
              and actual["strict_mismatches"] == 0
              and len(saved) == len(expected_allow) == len(seen) == 1152
              and not missing and mismatch_count == 0)
    return {
        "schema": "v29-offline-analysis-check-v1", "status": "PASS" if passed else "FAIL",
        "results_equal_expected": equal,
        "results_sha256": hashlib.sha256(results_path.read_bytes()).hexdigest(),
        "core_rows_compared": actual["archived_rows_compared"],
        "core_strict_mismatches": actual["strict_mismatches"],
        "core_fields_compared": [field for field in ev.SCORE_FIELDS if field != "upstream_call_ids"],
        "allow_rows_compared": len(seen), "allow_strict_mismatches": mismatch_count,
        "allow_fields_compared": list(ev.SCORE_FIELDS),
        "allow_missing_output_rows": len(missing), "allow_mismatch_examples": examples,
        "new_model_calls": 0, "policy_executions": 0,
        "method": "Strict saved-state scoring with archived evaluator; whole JSON equality for v29 analysis.",
        "limitations": "Reproduces authored-reference analysis; no independent human semantic validation.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--report", type=Path, help="Optional fresh output file; existing files are rejected")
    args = parser.parse_args()
    report = verify(args.results)
    if args.report:
        with args.report.open("x") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    print(json.dumps({name: report[name] for name in (
        "status", "results_equal_expected", "core_rows_compared", "core_strict_mismatches",
        "allow_rows_compared", "allow_strict_mismatches", "new_model_calls")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
