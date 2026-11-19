"""ROADMAP 2.322: summarise gaps_page.py output (roles + head boxes) and join Sean's judged answers.

    python3 benchmarks/claim-once-gaps-2026-11/summarise.py PLATE DATADIR JUDGED_JSON
"""
import collections
import json
import pathlib
import sys

plate, data, judged_json = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3]
ROOT = pathlib.Path(__file__).resolve().parents[2]
LATER = {"accidental", "arc", "hairpin", "dynamic", "mark", "dot", "rest"}
EARLIER = {"barline", "bracket", "clef", "key", "meter", "word", "tremolo"}

roles = json.load(open(data / ("%s_roles.json" % plate)))
heads = json.load(open(data / ("%s_heads.json" % plate)))

print("=== %s: ink by beam role and state (px) ===" % plate)
byrole = collections.defaultdict(collections.Counter)
for k, v in roles["state_by_role"].items():
    r, s = k.split("|")
    byrole[r][s] += v
tot = sum(sum(c.values()) for c in byrole.values())
none_tot = sum(c["none"] for c in byrole.values())
print("total ink attributed", tot, "no-owner", none_tot, "(%.2f%%)" % (100.0 * none_tot / tot))
for r, c in sorted(byrole.items(), key=lambda kv: -sum(kv[1].values())):
    n = sum(c.values())
    print("  %-16s ink %9d (%.1f%% of page ink)  one %.1f%%  none %.1f%%  twice(any) %.1f%%  staff %.1f%%" % (
        r, n, 100.0 * n / tot, 100.0 * c["one"] / n, 100.0 * c["none"] / n,
        100.0 * (c["twin"] + c["twin_views"] + c["two_kinds"] + c["views_disagree"] + c["page_not_consulted"]) / n, 100.0 * c["staff_line"] / n))
print("no-owner ink by role (share of all no-owner ink):")
for r, c in sorted(byrole.items(), key=lambda kv: -kv[1]["none"]):
    if c["none"]:
        print("  %-16s %9d  %.1f%%" % (r, c["none"], 100.0 * c["none"] / none_tot))
beam_roles = ("beam", "beam_stub", "beam_doubt")
print("beam-role strokes' no-owner ink: %d = %.1f%% of no-owner ink" % (sum(byrole[r]["none"] for r in beam_roles), 100.0 * sum(byrole[r]["none"] for r in beam_roles) / none_tot))
print("who owns the ink of beam-role strokes (ST_ONE only):")
own = collections.defaultdict(collections.Counter)
for k, v in roles["one_owner_by_role"].items():
    r, o = k.split("|")
    own[r][o] += v
for r in beam_roles:
    n = sum(byrole[r].values())
    print("  %s (ink %d): %s" % (r, n, ", ".join("%s %.1f%%" % (o, 100.0 * v / n) for o, v in own[r].most_common(6))))
print("no-owner ink by tool class, by role:")
cl = collections.defaultdict(collections.Counter)
for k, v in roles["none_by_class_role"].items():
    r, c = k.split("|")
    cl[c][r] += v
for c, rc in sorted(cl.items(), key=lambda kv: -sum(kv[1].values())):
    print("  %-20s %9d  (%.1f%% of none)  top roles: %s" % (c, sum(rc.values()), 100.0 * sum(rc.values()) / none_tot,
                                                         ", ".join("%s %d" % (r, v) for r, v in rc.most_common(4))))

print()
print("=== %s: head boxes ===" % plate)
print("head boxes with ink:", len(heads), " written as note:", sum(h["written"] for h in heads))


def dom(h):
    s = {k: v for k, v in h["share"].items()}
    if not s:
        return None, 0.0
    k = max(s, key=lambda x: s[x])
    return k, s[k]


def tier(k):
    return "later" if k in LATER else "earlier"


def band(x):
    return "0<s<.10" if x < 0.10 else (".10<=s<.25" if x < 0.25 else (".25<=s<.50" if x < 0.50 else "s>=.50"))


tab = collections.defaultdict(lambda: collections.Counter())
for h in heads:
    k, s = dom(h)
    if k is None:
        tab["none"]["boxes"] += 1
        tab["none"]["written"] += h["written"]
        continue
    key = (band(s), tier(k))
    tab[key]["boxes"] += 1
    tab[key]["written"] += h["written"]
for key in sorted(tab, key=str):
    print("  %-30s boxes %5d  written as notes %5d" % (key, tab[key]["boxes"], tab[key]["written"]))
print("by dominant claimant kind (share>=.10 only): boxes / written")
c2 = collections.defaultdict(collections.Counter)
for h in heads:
    k, s = dom(h)
    if k and s >= 0.10:
        c2[k]["boxes"] += 1
        c2[k]["written"] += h["written"]
        if s >= 0.5:
            c2[k]["ge50"] += 1
            c2[k]["ge50_written"] += h["written"]
for k, v in sorted(c2.items(), key=lambda kv: -kv[1]["boxes"]):
    print("  %-10s %-7s boxes %4d written %4d | >=50%%: boxes %3d written %3d" % (k, tier(k), v["boxes"], v["written"], v["ge50"], v["ge50_written"]))
# group (ii): at or over the cut and still written; own head-only ink
g2 = [h for h in heads if h["written"] and dom(h)[1] >= 0.5]
print("group ii (written, a claimant of another kind holds >=50%% of the box ink): %d; of which box owns head-only ink (>0 px): %d" % (
    len(g2), sum(1 for h in g2 if h["head_only_px"] > 0)))
# ---- join Sean's judged answers
J = json.load(open(judged_json))
idx = {(t["item"], str(t["tile"])): t for t in json.load(open(ROOT / "benchmarks/acceptance/judged-tiles.json"))["tiles"]}
jsub = collections.defaultdict(list)
for r in J["tiles"]:
    t = idx.get((r["item"], str(r["tile"])), {})
    for sb in (r["subject"] if isinstance(r["subject"], list) else [r["subject"]]):
        jsub[sb].append({"item": r["item"], "tile": r["tile"], "status": r["status"], "answer": r["answer"],
                         "answer_kind": t.get("answer_kind"), "value": t.get("value")})
reg = json.load(open(ROOT / "data/judged-claims/registry.json"))["tiles"]
regp = collections.defaultdict(list)
for t in reg:
    if t["plate"] == plate and t.get("box"):
        regp[t["page"]].append(t)
cov = []
for h in heads:
    k, s = dom(h)
    if not (k and s >= 0.10):
        continue
    js = jsub.get(h["subject"], [])
    rg = []
    x0, y0, x1, y1 = h["box"]
    for t in regp.get(h["page"], []):
        bx0, by0, bx1, by1 = t["box"]
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            rg.append({"lane": t["lane"], "kind": t["kind"], "value": t["value"], "words": t["words"]})
    if js or rg:
        cov.append({"subject": h["subject"], "page": h["page"], "box": h["box"], "claimant": k, "share": s, "written": h["written"],
                    "written_as": h["written_as"], "judged": js, "claims": rg})
print("heads with a claimant share >=.10 AND a judged answer (by glyph key) or a judged claim tile (by place):", len(cov))
for c in cov:
    print(json.dumps(c)[:700])
json.dump(cov, open(data / ("%s_covered.json" % plate), "w"), indent=1)
