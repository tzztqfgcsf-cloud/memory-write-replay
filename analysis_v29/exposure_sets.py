"""Reference-independent exposure sets and the human-review scope (revision of Sections 6.4, 7.1, 8).

Place this directory at the repository root and run, from the root:
    python3 analysis_v29/exposure_sets.py --output-dir /tmp/exposure-sets

Standard library only; no model call and no policy execution. For each rule family it compares
four sets of outputs (model configuration, case, repetition):

  E  exposure, read from the saved gate log before any scoring: the outputs that contain an
     operation on which the compared rules can decide differently (Proposition 1);
  D  the outputs on which the replayed rules leave different executed states;
  O  the outputs on which the executed states or generation validity differ;
  S  the outputs whose endpoints differ under at least one of the two references. S is the set
     that rescore_variant_tolerant.py counts (36 + 23 = 59 for the rule families, 127 for gating).

The archived endpoints require generation validity as well as state conformity. Four gating
outputs have identical stored facts but different validity and scores, so S <= D fails there.
The executable check is S <= O <= E, with O reported as D_state_or_validity; the state-only
checks remain diagnostic fields. For these fixed-proposal comparisons, action is shared.
Review conservatively includes O and exposed outputs where a compared rule was not replayed.
S alone is not a review scope: different states can receive the same score under both references.
This revision changes neither the archived evaluator nor any saved output or score.
"""
import argparse, collections, csv, gzip, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(HERE))
from runtime import evaluate as ev  # noqa: E402  archived evaluator
from rescore_variant_tolerant import score_lenient  # noqa: E402

K = ["harmful_write", "positive_joint", "correction_recovery", "whole_state_compliance"]

# gate: the condition whose saved gate log defines E; held_ops: operations whose HOLD can be
# reversed by another rule in the family (Section 4.2: H for the four rules; every held
# APPEND or CORRECT, plus invalid extractions, for gating versus not gating).
FAMILIES = {
    "controlled_rules": {"conds": ["B", "ALLOWc", "EXACT_LITERAL", "C"], "gate": "B",
                         "held_ops": {"CORRECT"}, "invalid_extraction": False},
    "review_rules": {"conds": ["R_AGREE", "R_ALLOW", "R_LITERAL", "R_WITNESS"], "gate": "R_AGREE",
                     "held_ops": {"CORRECT"}, "invalid_extraction": False},
    "review_vs_review_witness": {"conds": ["G", "R_WITNESS"], "gate": "R_WITNESS",
                                 "held_ops": {"APPEND", "CORRECT"}, "invalid_extraction": True},
}


def state(o):
    """Executed state as a hashable value; None when the output has no readable final state."""
    try:
        return tuple(sorted((str(k), tuple(v)) for k, v in ev._fact_map(o["final_snapshot"]["facts"]).items()))
    except (KeyError, TypeError, ValueError):
        return None


def load():
    cases = json.load(gzip.open(ROOT / "core/data/cases.json.gz"))
    episodes = json.load(gzip.open(ROOT / "core/data/episodes.json.gz"))
    pub = {e["case_id"]: cases["public_rows"][e["public_row_id"]] for e in episodes}
    ref = {e["case_id"]: cases["references"][e["reference_id"]] for e in episodes}
    obs = {}

    def add(key, o):
        s = ev.score_output(o, pub[key[1]], ref[key[1]])
        l = score_lenient(o, pub[key[1]], ref[key[1]])
        obs[key] = {"S": tuple(int(bool(s[k])) for k in K), "L": tuple(int(bool(l[k])) for k in K),
                    "valid": bool(s["generation_valid"]), "state": state(o),
                    "audit": o.get("gate_audit") or []}

    for e in episodes:
        for cond, o in e["outputs"].items():
            add((e["model_alias"], e["case_id"], str(e["repeat"]), cond), o)
    for line in open(ROOT / "diagnostics/saved_allow/outputs.jsonl"):
        o = json.loads(line)
        add((o["model_alias"], o["case_id"], str(o["repeat"]), "ALLOWc"), o)
    return obs


def analyse(obs, name, fam):
    keys = sorted({k[:3] for k in obs if k[3] == fam["gate"]})
    rows = []
    for x in keys:
        present = [c for c in fam["conds"] if (*x, c) in obs]
        missing = [c for c in fam["conds"] if c not in present]
        g = obs[(*x, fam["gate"])]
        held = [a for a in g["audit"] if a.get("after_operation") == "HOLD"
                and a.get("before_operation") in fam["held_ops"]]
        invalid = fam["invalid_extraction"] and (not g["valid"]) and obs[(*x, "G")]["valid"]
        in_e = bool(held) or invalid
        in_d = len({obs[(*x, c)]["state"] for c in present}) > 1
        in_o = len({(obs[(*x, c)]["state"], obs[(*x, c)]["valid"]) for c in present}) > 1
        in_s = any(len({obs[(*x, c)][r] for c in present}) > 1 for r in "SL")
        validity_only_score_difference = in_s and not in_d and in_o
        if not (in_e or in_d or in_o or in_s):
            continue
        rows.append({"family": name, "model_alias": x[0], "case_id": x[1], "repeat": x[2],
                     "E_exposed": int(in_e), "D_states_differ": int(in_d), "S_scores_differ": int(in_s),
                     "D_state_or_validity": int(in_o),
                     "validity_only_score_difference": int(validity_only_score_difference),
                     "held_operations": len(held), "invalid_extraction": int(invalid),
                     "rules_not_replayed": " ".join(missing),
                     # Conservative review scope: state/validity differs or a rule is missing.
                     "review": int(in_e and (in_o or bool(missing)))})
    count = lambda f: sum(bool(f(r)) for r in rows)
    cases = lambda f: len({r["case_id"] for r in rows if f(r)})
    summary = {
        "E_exposed": count(lambda r: r["E_exposed"]),
        "E_cases": cases(lambda r: r["E_exposed"]),
        "D_states_differ": count(lambda r: r["D_states_differ"]),
        "D_state_or_validity": count(lambda r: r["D_state_or_validity"]),
        "S_scores_differ": count(lambda r: r["S_scores_differ"]),
        "validity_only_score_difference": count(lambda r: r["validity_only_score_difference"]),
        "check_S_within_D": count(lambda r: r["S_scores_differ"] and not r["D_states_differ"]) == 0,
        "check_D_within_E": count(lambda r: r["D_states_differ"] and not r["E_exposed"]) == 0,
        "check_S_within_D_state_or_validity": count(lambda r: r["S_scores_differ"] and not r["D_state_or_validity"]) == 0,
        "check_D_state_or_validity_within_E": count(lambda r: r["D_state_or_validity"] and not r["E_exposed"]) == 0,
        "E_with_identical_states": count(lambda r: r["E_exposed"] and not r["D_states_differ"] and not r["rules_not_replayed"]),
        "D_not_in_S": count(lambda r: r["D_states_differ"] and not r["S_scores_differ"]),
        "E_with_rule_not_replayed": count(lambda r: r["E_exposed"] and r["rules_not_replayed"]),
        "review_scope": count(lambda r: r["review"]),
        "review_scope_cases": cases(lambda r: r["review"]),
        "by_configuration": {},
    }
    by = collections.defaultdict(collections.Counter)
    for r in rows:
        c = by[r["model_alias"]]
        for f in ("E_exposed", "D_states_differ", "D_state_or_validity", "S_scores_differ",
                  "validity_only_score_difference", "review"):
            c[f] += r[f]
        if r["E_exposed"] and r["rules_not_replayed"]:
            c["E_with_rule_not_replayed"] += 1
    summary["by_configuration"] = {m: dict(c) for m, c in sorted(by.items())}
    return summary, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    out = Path(ap.parse_args().output_dir)
    out.mkdir(parents=True, exist_ok=False)
    obs = load()
    result, all_rows = {}, []
    for name, fam in FAMILIES.items():
        result[name], rows = analyse(obs, name, fam)
        all_rows += rows
    (out / "exposure_sets.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    with (out / "review_set.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0]) if all_rows else ["family"])
        w.writeheader()
        w.writerows(all_rows)
    print(json.dumps({n: {k: v for k, v in s.items() if k != "by_configuration"} for n, s in result.items()}, indent=1))
    ok = all(s["check_S_within_D_state_or_validity"] and s["check_D_state_or_validity_within_E"]
             for s in result.values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
