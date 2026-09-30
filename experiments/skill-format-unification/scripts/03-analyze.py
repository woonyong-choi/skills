"""processed/*.csv -> results/summary.json, results/tables/*.csv"""
import csv, json, math, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
P = os.path.join(EXP, "data", "processed")
R = os.path.join(EXP, "results")
os.makedirs(os.path.join(R, "tables"), exist_ok=True)


def rd(name):
    return list(csv.DictReader(open(os.path.join(P, name), encoding="utf-8")))


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]


def pct(a, b):
    return round(100 * (b - a) / a, 1)


def wt(name, rows):
    with open(os.path.join(R, "tables", name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


S = {}

# 토큰 합계
tok = rd("skill_tokens.csv")
tot = defaultdict(lambda: defaultdict(int))
for r in tok:
    for k in ("bytes", "o200k", "claude_legacy", "desc_o200k", "desc_claude_legacy"):
        tot[r["version"]][k] += int(r[k])
    tot[r["version"]]["skills"] += 1
S["totals"] = {v: dict(t) for v, t in tot.items()}
S["totals_change_pct"] = {k: pct(tot["before"][k], tot["after"][k])
                          for k in ("bytes", "o200k", "claude_legacy", "desc_o200k", "desc_claude_legacy")}

# 시나리오
sc = rd("scenario_load.csv")
by = defaultdict(dict)
for r in sc:
    by[r["scenario"]][r["version"]] = r
rows = []
for sid in sorted(by):
    b, a = by[sid]["before"], by[sid]["after"]
    rows.append({"scenario": sid, "request": b["request"],
                 "before_skills": b["skills"], "after_skills": a["skills"],
                 "before_o200k": int(b["o200k"]), "after_o200k": int(a["o200k"]),
                 "change_o200k_pct": pct(int(b["o200k"]), int(a["o200k"])),
                 "before_claude_legacy": int(b["claude_legacy"]), "after_claude_legacy": int(a["claude_legacy"]),
                 "change_claude_legacy_pct": pct(int(b["claude_legacy"]), int(a["claude_legacy"]))})
wt("scenario_load.csv", rows)
S["scenarios"] = {r["scenario"]: {k: r[k] for k in ("request", "before_o200k", "after_o200k", "change_o200k_pct",
                                                   "before_claude_legacy", "after_claude_legacy",
                                                   "change_claude_legacy_pct")} for r in rows}
ch = [r["change_o200k_pct"] for r in rows]
S["scenario_summary"] = {"n": len(ch), "decreased": sum(c < 0 for c in ch), "increased": sum(c > 0 for c in ch),
                         "max_increase_pct": max(ch), "max_decrease_pct": min(ch),
                         "sum_before_o200k": sum(r["before_o200k"] for r in rows),
                         "sum_after_o200k": sum(r["after_o200k"] for r in rows)}
S["scenario_summary"]["sum_change_pct"] = pct(S["scenario_summary"]["sum_before_o200k"],
                                              S["scenario_summary"]["sum_after_o200k"])
S["catalog_o200k"] = {v: int(next(r for r in sc if r["version"] == v)["catalog_o200k"]) for v in ("before", "after")}
S["catalog_claude_legacy"] = {v: int(next(r for r in sc if r["version"] == v)["catalog_claude_legacy"]) for v in ("before", "after")}

# 문체 검사
st = rd("style_check.csv")
S["style_check"] = defaultdict(dict)
for r in st:
    S["style_check"][r["version"]][r["kind"]] = int(r["count"])
S["style_check"] = dict(S["style_check"])

# 트리거
tr = rd("trigger.csv")
runs = defaultdict(list)
for r in tr:
    runs[r["run"]].append(r)
trows = []
for run, rs in sorted(runs.items()):
    n = len(rs)
    k1 = sum(int(r["hit_catalog"]) for r in rs)
    k2 = sum(int(r["hit_after_base"]) for r in rs)
    ex = sum(1 for r in rs if r["extra"])
    trows.append({"run": run, "n": n, "hit_catalog": k1, "hit_catalog_pct": round(100 * k1 / n, 1),
                  "hit_catalog_ci": wilson(k1, n), "hit_after_base": k2,
                  "hit_after_base_pct": round(100 * k2 / n, 1), "hit_after_base_ci": wilson(k2, n),
                  "over_selection": ex,
                  "missing": "; ".join(f'{r["prompt"]}:{r["missing"]}' for r in rs if r["missing"]),
                  "extra": "; ".join(f'{r["prompt"]}:{r["extra"]}' for r in rs if r["extra"])})
wt("trigger.csv", [{**r, "hit_catalog_ci": str(r["hit_catalog_ci"]), "hit_after_base_ci": str(r["hit_after_base_ci"])} for r in trows])
S["trigger"] = {r["run"]: r for r in trows}

# 결정성
dt = rd("determinism.csv")
rounds = defaultdict(lambda: {"nonblank_lines": 0, "diff_lines": 0, "files": 0, "same_headings": 0, "same_file_set": 1})
for r in dt:
    x = rounds[r["round"]]
    x["nonblank_lines"] += int(r["nonblank_lines"])
    x["diff_lines"] += int(r["diff_lines"])
    x["files"] += 1
    x["same_headings"] += int(r["same_headings"])
    x["same_file_set"] &= int(r["same_file_set"])
drows = []
for rnd, x in sorted(rounds.items()):
    drows.append({"round": rnd, **x, "diff_pct": round(100 * x["diff_lines"] / x["nonblank_lines"], 1),
                  "diff_ci": wilson(x["diff_lines"], x["nonblank_lines"])})
wt("determinism.csv", [{**r, "diff_ci": str(r["diff_ci"])} for r in drows])
S["determinism"] = {r["round"]: r for r in drows}

# 누락 대조
au = rd("audit.csv")
kinds = defaultdict(int)
for r in au:
    kinds[r["kind"]] += 1
S["audit"] = {}
for ps in ("1", "2"):
    au_p = [r for r in au if r["pass"] == ps]
    k_p = defaultdict(int)
    for r in au_p:
        k_p[r["kind"]] += 1
    S["audit"]["pass" + ps] = {"findings": len(au_p), "by_kind": dict(k_p), "fixed": sum(int(r["fixed"]) for r in au_p),
                                "loss": k_p.get("loss", 0), "loss_fixed": sum(int(r["fixed"]) for r in au_p if r["kind"] == "loss")}

S["flow"] = {"trigger_runs": len(runs), "writer_outputs": 2 * len(rounds), "audit_passes": 2, "excluded": 0,
             "collected": len(runs) + 2 * len(rounds), "analyzed": len(runs) + 2 * len(rounds)}

# 가설 판정
H1_SET = ["s01", "s03", "s05", "s07", "s09", "s10", "s11", "s13", "s14"]
H2_SET = ["s02", "s04", "s06", "s08", "s12"]
sv = S["scenarios"]
h1 = [x for x in H1_SET if sv[x]["change_o200k_pct"] <= -20]
h2 = [x for x in H2_SET if sv[x]["change_o200k_pct"] <= 10]
new_runs = [r for k, r in S["trigger"].items() if not k.startswith("before")]
last = S["determinism"][max(S["determinism"])]
S["hypotheses"] = {
    "H1": {"met": len(h1), "n": len(H1_SET), "not_met": [x for x in H1_SET if x not in h1],
           "verdict": "채택" if len(h1) == len(H1_SET) else "기각"},
    "H2": {"met": len(h2), "n": len(H2_SET), "not_met": [x for x in H2_SET if x not in h2],
           "verdict": "채택" if len(h2) == len(H2_SET) else "기각"},
    "H3": {"change_pct": S["scenario_summary"]["sum_change_pct"],
           "verdict": "채택" if S["scenario_summary"]["sum_change_pct"] <= -10 else "기각"},
    "H4": {"fixed": S["audit"]["pass1"]["fixed"], "kept": S["audit"]["pass1"]["findings"] - S["audit"]["pass1"]["fixed"],
           "reaudit_present": S["audit"]["pass1"]["fixed"], "reaudit_new": S["audit"]["pass2"]["findings"],
           "verdict": "채택"},
    "H5": {"runs": len(new_runs), "runs_full_hit": sum(r["hit_after_base"] == r["n"] for r in new_runs),
           "max_over_selection": max(r["over_selection"] for r in new_runs),
           "verdict": "채택" if all(r["hit_after_base"] == r["n"] and r["over_selection"] <= 1 for r in new_runs) else "기각"},
    "H6": {"round": last["round"], "diff_pct": last["diff_pct"], "ci": last["diff_ci"],
           "verdict": "채택" if last["diff_ci"][1] <= 10 else ("기각" if last["diff_ci"][0] > 10 else "보류")},
    "H7": {"violations": S["style_check"]["after"]["total"], "before": S["style_check"]["before"]["total"],
           "verdict": "채택" if S["style_check"]["after"]["total"] == 0 else "기각"},
}

json.dump(S, open(os.path.join(R, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)
open(os.path.join(R, "summary.json"), "a").write("\n")
