"""Verify archived statistics using frozen scores only; no scorer/model imports."""
import argparse
import csv
import gzip
import hashlib
import json
import math
import platform
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "diagnostics/analysis_archive"
KEY = ["model_alias", "case_id", "repeat"]
METRICS = {
    "positive_joint": "positive_eligible",
    "correction_recovery": "correction_eligible",
    "harmful_write": None,
    "invalid_final": None,
    "whole_state_compliance": None,
    "unsupported_write_claim": None,
}
HYBRIDS = [("N_AGREE", "B"), ("N_LITERAL", "EXACT_LITERAL"),
           ("N_LITERAL", "C"), ("R_LITERAL", "G"),
           ("R_WITNESS", "G"), ("R_WITNESS", "R_LITERAL")]
BOUNDS = [("R_AGREE", "G"), ("R_ALLOW", "G"), ("R_LITERAL", "G"),
          ("R_WITNESS", "G"), ("R_ALLOW", "R_AGREE"),
          ("R_WITNESS", "R_AGREE"), ("R_WITNESS", "R_ALLOW"),
          ("R_WITNESS", "R_LITERAL")]
INTS = {"cases", "observations", "before", "after", "gains", "losses", "net",
        "repeats", "before_count", "after_count"}
FLOATS = {"delta_pp", "ci_low_pp", "ci_high_pp", "raw_effect", "raw_ci_low",
          "raw_ci_high", "benefit_effect", "benefit_ci_low", "benefit_ci_high"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_scores():
    episodes = json.loads(gzip.decompress((ROOT / "core/data/episodes.json.gz").read_bytes()))
    cohort = json.loads((ROOT / "core/data/cohort.json").read_text())
    models = cohort["selected_configurations"]
    require(len(episodes) == 3024 and len(models) == 21, "Unexpected cohort size")
    rows = []
    keys = set()
    cases = set()
    expected_conditions = set(cohort["original_conditions"] + cohort["saved_alternative_conditions"])
    for episode in episodes:
        key = tuple(episode[k] for k in KEY)
        require(key not in keys, "Duplicate episode")
        keys.add(key)
        cases.add(episode["case_id"])
        require(set(episode["expected_scores"]) == expected_conditions, "Condition coverage changed")
        for condition, score in episode["expected_scores"].items():
            require(tuple(score[k] for k in KEY) == key and score["condition"] == condition,
                    "Score provenance differs from episode")
            for field in list(METRICS) + ["positive_eligible", "correction_eligible"]:
                require(type(score[field]) is bool, "Non-Boolean score: " + field)
            rows.append(score)
    require(len(cases) == 48, "Unexpected case count")
    require(keys == {(m, c, r) for m in models for c in cases for r in [1, 2, 3]},
            "Missing cohort triplets")
    df = pd.DataFrame(rows)
    require(not df.duplicated(KEY + ["condition"]).any(), "Duplicate scored observation")
    for field in ["positive_eligible", "correction_eligible"]:
        require(df.groupby(KEY)[field].nunique().max() == 1, "Eligibility varies across policies")
    return df, models


def paired(df, candidate, baseline, metric):
    x = df[df.condition == candidate].set_index(KEY)
    y = df[df.condition == baseline].set_index(KEY)
    require(set(x.index) == set(y.index), "Missing paired observations")
    z = pd.DataFrame({"before": y[metric].astype(int), "after": x[metric].astype(int)})
    eligible = METRICS[metric]
    if eligible:
        z = z[x[eligible]]
    z["delta"] = z.after - z.before
    return z.reset_index()


def counts(v):
    return {"cases": int(v.case_id.nunique()), "observations": len(v),
            "before": int(v.before.sum()), "after": int(v.after.sum()),
            "gains": int((v.delta > 0).sum()), "losses": int((v.delta < 0).sum())}


def numpy_interval(cd, seed):
    rng = np.random.default_rng(seed)
    draws = cd[rng.integers(0, len(cd), (5000, len(cd)))].mean(axis=1) * 100
    lo, hi = np.quantile(draws, [.025, .975], method="linear")
    return float(lo), float(hi)


def reproduce_pairs(df, models, contrasts, metrics, seed, net):
    rows = []
    for candidate, baseline in contrasts:
        for metric in metrics:
            z = paired(df, candidate, baseline, metric)
            for model in models + ["ALL21"]:
                v = z if model == "ALL21" else z[z.model_alias == model]
                cd = v.groupby("case_id").delta.mean().to_numpy()
                lo, hi = numpy_interval(cd, seed)
                row = dict(model_alias=model, candidate=candidate, baseline=baseline,
                           metric=metric, **counts(v))
                if net:
                    row["net"] = int(v.delta.sum())
                row.update(delta_pp=float(cd.mean() * 100), ci_low_pp=lo, ci_high_pp=hi)
                rows.append(row)
    return rows


def python_interval(values, seed):
    # Historical evaluator uses Python random.choice, sorted case order,
    # integer sum / repeats, and linear interpolation of sorted draws.
    rng = random.Random(seed)
    draws = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(5000))
    result = []
    for probability in [.025, .975]:
        position = (len(draws) - 1) * probability
        low = int(position)
        high = min(low + 1, len(draws) - 1)
        result.append(draws[low] + (draws[high] - draws[low]) * (position - low))
    return result


def reproduce_panel(df, models):
    archived = read_csv(ARCHIVE / "panel21/model_comparisons.csv")
    require(len(archived) == 84 and {r["model"] for r in archived} == set(models),
            "Unexpected archived panel")
    rows, coverage = [], []
    for old in archived:
        model, metric = old["model"], old["metric"]
        v = paired(df, "CR", "G", metric)
        v = v[v.model_alias == model]
        stat = counts(v)
        effect = (stat["after"] - stat["before"]) / len(v)
        source = old["interval_source"]
        seed = None
        if source:
            if source.endswith("combined_analysis_preparation_v2/analysis/paired_case_cluster_intervals.csv"):
                seed = 20260930
            elif source.endswith("result.json") and metric == "positive_joint":
                seed = 20260927
            else:
                raise ValueError("No fixed portable recipe for archived panel interval")
        # Sum integers inside a case before division, as the original evaluator.
        case_values = [int(g.delta.sum()) / len(g) for _, g in v.groupby("case_id", sort=True)]
        lo, hi = python_interval(case_values, seed) if seed is not None else (None, None)
        benefit = -1 if metric in ["harmful_write", "invalid_final"] else 1
        row = {"model": model, "label": old["label"], "group": old["group"],
               "metric": metric, "repeats": 3, "cases": stat["cases"],
               "observations": len(v), "before_count": stat["before"],
               "after_count": stat["after"], "raw_effect": effect,
               "raw_ci_low": lo, "raw_ci_high": hi, "interval_source": source,
               "benefit_effect": benefit * effect,
               "benefit_ci_low": (lo if benefit == 1 else -hi) if lo is not None else None,
               "benefit_ci_high": (hi if benefit == 1 else -lo) if hi is not None else None}
        rows.append(row)
        coverage.append({"model": model, "candidate": "CR", "baseline": "G",
                         "metric": metric, "cases": stat["cases"], "observations": len(v),
                         "count_effect_status": "RECOMPUTED_FROM_FROZEN_SCORES",
                         "interval_status": "RECOMPUTED" if seed is not None else "NOT_AVAILABLE_IN_ARCHIVED_PANEL",
                         "draws": 5000 if seed is not None else 0,
                         "seed": seed, "rng": "python_random_choice" if seed is not None else "",
                         "archived_source": source})
    return rows, coverage


def compare(rows, archive_path, keys):
    expected = read_csv(archive_path)
    actual = {tuple(str(r[k]) for k in keys): r for r in rows}
    target = {tuple(r[k] for k in keys): r for r in expected}
    require(len(actual) == len(rows) and len(target) == len(expected), "Duplicate comparison rows")
    mismatches = []
    require(set(actual) == set(target), "Archived/reproduced row keys differ")
    for key, old in target.items():
        row = actual[key]
        for field, val in old.items():
            new = row[field]
            if field in INTS:
                match = int(val) == new
            elif field in FLOATS:
                match = new is None if val == "" else new is not None and math.isclose(
                    float(val), float(new), rel_tol=0, abs_tol=1e-12)
            else:
                match = str(new) == val
            if not match:
                mismatches.append({"key": list(key), "field": field, "archived": val,
                                   "reproduced": new})
    return {"archive": str(archive_path.relative_to(ROOT)), "rows": len(rows),
            "columns_compared": list(expected[0]), "numeric_absolute_tolerance": 1e-12,
            "mismatch_count": len(mismatches), "mismatches": mismatches}


def condition_counts(df):
    fields = list(METRICS) + ["positive_eligible", "correction_eligible"]
    return df.groupby(["model_alias", "condition"], sort=True)[fields].sum().reset_index().to_dict("records")


def main():
    def reject_network(event, _args):
        if event.startswith("socket.") or event == "urllib.Request":
            raise RuntimeError("Network access is disabled for offline statistics")
    sys.addaudithook(reject_network)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="New or empty output directory outside the source repository")
    args = parser.parse_args()
    out = args.output.resolve()
    require(out != ROOT and ROOT not in out.parents, "Output must be outside the source repository")
    require(not out.exists() or (out.is_dir() and not any(out.iterdir())), "Output directory must be new or empty")
    inputs = [ROOT / "core/data/episodes.json.gz", ROOT / "core/data/cohort.json",
              ARCHIVE / "hybrids/paired_comparisons.csv",
              ARCHIVE / "review_bounds/paired_comparisons.csv",
              ARCHIVE / "panel21/model_comparisons.csv",
              ARCHIVE / "review_bounds/SUMMARY.json"]
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    df, models = load_scores()
    hybrid = reproduce_pairs(df, models, HYBRIDS, METRICS, 20261001, True)
    bounds = reproduce_pairs(df, models, BOUNDS, list(METRICS)[:-1], 20261002, False)
    panel, panel_coverage = reproduce_panel(df, models)
    checks = [compare(hybrid, inputs[2], ["model_alias", "candidate", "baseline", "metric"]),
              compare(bounds, inputs[3], ["model_alias", "candidate", "baseline", "metric"]),
              compare(panel, inputs[4], ["model", "metric"])]
    totals = condition_counts(df)
    # Independent aggregate archived checks (counts include ineligible rows;
    # comparison tables filter eligible observations for positive endpoints).
    old_counts = json.loads((ARCHIVE / "review_bounds/SUMMARY.json").read_text())["counts"]
    aggregate = df.groupby("condition")[list(METRICS)[:-1] + ["positive_eligible", "correction_eligible"]].sum()
    count_errors = []
    for row in old_counts:
        for field, old in row.items():
            if field == "condition":
                continue
            actual = 3024 if field == "observations" else int(aggregate.loc[row["condition"], field])
            if actual != old:
                count_errors.append({"condition": row["condition"], "field": field,
                                     "archived": old, "reproduced": actual})
    unchanged = all(sha(ROOT / rel) == value for rel, value in frozen.items())
    passed = unchanged and not count_errors and all(c["mismatch_count"] == 0 for c in checks)
    report = {"schema": "portable-frozen-statistics-verification-v1", "status": "PASS" if passed else "FAIL",
              "scope": "Existing frozen-score statistics only; no new scoring or hypothesis evaluation",
              "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
              "episodes": 3024, "score_rows": len(df), "conditions": int(df.condition.nunique()),
              "selected_configurations": len(models), "unique_cases": 48,
              "repeats": [1, 2, 3], "checks": checks,
              "condition_totals_archived_check": {"rows": len(old_counts), "mismatches": count_errors},
              "panel_intervals_recomputed": sum(r["interval_status"] == "RECOMPUTED" for r in panel_coverage),
              "panel_intervals_unavailable": sum(r["interval_status"] != "RECOMPUTED" for r in panel_coverage),
              "source_hashes": frozen, "source_files_unchanged": unchanged,
              "entrypoint_sha256": sha(Path(__file__)), "requirements_sha256": sha(Path(__file__).with_name("requirements.txt")),
              "network_calls": 0, "model_calls": 0, "new_scored_rows": 0,
              "original_scores_overwritten": 0, "archived_analysis_overwritten": 0,
              "numeric_equality_note": "Counts exact; all CSV floating fields within absolute 1e-12 (round-off tolerance)."}
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "hybrids_paired_comparisons.csv", hybrid)
    write_csv(out / "review_bounds_paired_comparisons.csv", bounds)
    write_csv(out / "panel21_model_comparisons.csv", panel)
    write_csv(out / "panel21_coverage.csv", panel_coverage)
    write_csv(out / "condition_counts.csv", totals)
    (out / "VERIFICATION.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["status", "score_rows", "panel_intervals_recomputed",
                                           "panel_intervals_unavailable", "network_calls", "model_calls", "new_scored_rows"]}))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
