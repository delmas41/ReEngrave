"""2.171 probe 4: tables from e2_run output. Per plate, per class, per group (lost A/B/C, D, kept, judged): n, mean / median conf of the best box of the
WANTED family over the symbol (0 when none), share >= 0.25, for every condition; effect sizes per variable; new false boxes; phase spread.
usage: e4_analyse.py   (reads probe/2.171/data/{lit,bra}_run.json, writes probe/2.171/data/analysis.txt and summary.json)"""
import json
import statistics
import sys
from collections import defaultdict

ROOT = __file__.rsplit("/probe/", 1)[0]
D = ROOT + "/probe/2.171/data/"
COND_ORDER = ["prod", "sc0.5", "sc0.7", "sc0.85", "sc1.20", "sc1.4", "sc2.0", "wide", "wide_rule", "mirror", "foreign", "triple", "system", "L1gray", "L2white", "L3whitepad", "mw32", "mw64", "mw128", "mw256", "mg128", "mv64", "mwv128", "area", "wide_area",
              "phx1", "phx2", "phx3", "phx4", "phx5", "phx6", "phy2", "phy4", "phy6", "pos_c", "pos_l", "pos_r", "pos_c8", "pos_c16", "pos_c24"]
PHASE = ["prod", "phx1", "phx2", "phx3", "phx4", "phx5", "phx6", "phy2", "phy4", "phy6"]
POS = ["pos_c", "pos_c8", "pos_c16", "pos_c24"]
FAMS = ("dot", "flag", "rest", "blackhead")
out = []


def P(s=""):
    out.append(s)
    print(s)


def conf(sc, cond, kind="want"):
    v = sc.get(cond)
    if not v or not v.get(kind):
        return 0.0
    return v[kind][1]


def group_of(S):
    if S["role"] == "lost":
        return "lost" if S["cause"] in ("A", "B", "C") else "D"
    return S["role"]


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def fam(cls):
    if cls == "augmentationDot":
        return "dot"
    if cls.startswith("flag"):
        return "flag"
    if cls.startswith("rest"):
        return "rest"
    if cls.startswith("notehead"):
        return "head"
    return "other"


summary = {}
for plate in ("lit", "bra"):
    R = json.load(open(D + "%s_run.json" % plate))
    SUB = json.load(open(D + "subjects.json"))[plate]["subjects"]
    rows = []   # (S, scdict)
    for key, r in R.items():
        if "subj" not in r:
            continue
        for i, sc in r["subj"].items():
            rows.append((SUB[int(i)], sc, key))
    P("=" * 100)
    P("PLATE %s: %d subjects in %d bars" % (plate, len(rows), len(R)))
    groups = defaultdict(list)
    for S, sc, key in rows:
        groups[(group_of(S), S["want"])].append((S, sc))
        groups[(group_of(S), "ALL")].append((S, sc))
        groups[("ALL", S["want"])].append((S, sc))
        groups[("ALL", "ALL")].append((S, sc))
    P("subject counts: " + ", ".join("%s/%s=%d" % (g, f, len(v)) for (g, f), v in sorted(groups.items()) if f != "ALL" and g != "ALL"))
    summary[plate] = {}
    # ---- table per group (lost / kept) x class: all conditions
    for g in ("lost", "kept", "D", "judged"):
        for f in FAMS + ("ALL",):
            L = groups.get((g, f), [])
            if len(L) < 3:
                continue
            P()
            P("%s | group %s | class %s | n=%d   (conf of the best box of the wanted family over the symbol; 0 if none)" % (plate, g, f, len(L)))
            P("  %-11s %6s %6s %9s   %s" % ("condition", "mean", "median", "share>=.25", "d-mean vs prod / d-share"))
            base_m = base_s = None
            for cond in COND_ORDER:
                vals = [conf(sc, cond) for S, sc in L if cond in sc]
                if not vals:
                    continue
                m, md, sh = statistics.mean(vals), statistics.median(vals), sum(1 for v in vals if v >= 0.25) / len(vals)
                if cond == "prod":
                    base_m, base_s = m, sh
                P("  %-11s %6.3f %6.3f %9.2f   %+.3f / %+.2f" % (cond, m, md, sh, m - base_m, sh - base_s))
                summary[plate].setdefault("%s|%s" % (g, f), {})[cond] = dict(n=len(vals), mean=round(m, 3), median=round(md, 3), share=round(sh, 3))
    # ---- phase spread vs context change, per symbol
    P()
    P("%s per-symbol spread: how far does conf move when ONE thing changes?" % plate)
    for g in ("lost", "kept"):
        L = groups.get((g, "ALL"), [])
        sp_phase = [max(conf(sc, c) for c in PHASE) - min(conf(sc, c) for c in PHASE) for S, sc in L]
        sp_pos = [max(conf(sc, c) for c in POS) - min(conf(sc, c) for c in POS) for S, sc in L]
        sp_scale = [max(conf(sc, c) for c in ("sc0.7", "prod", "sc1.4")) - min(conf(sc, c) for c in ("sc0.7", "prod", "sc1.4")) for S, sc in L]
        d_wide = [abs(conf(sc, "wide") - conf(sc, "prod")) for S, sc in L]
        d_l2 = [abs(conf(sc, "L2white") - conf(sc, "prod")) for S, sc in L]
        d_area = [abs(conf(sc, "area") - conf(sc, "prod")) for S, sc in L]
        for nm, v in (("phase (crop edge moved 0-6 canonical px; max-min over 10 runs)", sp_phase), ("grid phase (symbol moved 0/8/16/24 net px)", sp_pos),
                      ("scale x0.7..x1.4 (max-min)", sp_scale), ("|wide - prod| (context, same pixel size)", d_wide),
                      ("|L2white - prod| (canvas shape + white fill)", d_l2), ("|area - prod| (interpolation)", d_area)):
            P("  %-5s %-62s median %.3f  mean %.3f  share>0.10: %.2f  share>0.25: %.2f" % (g, nm, statistics.median(v), statistics.mean(v),
                                                                                        sum(1 for x in v if x > 0.10) / len(v), sum(1 for x in v if x > 0.25) / len(v)))
    # ---- null-adjusted effect: the sampling-phase runs change nothing real, so their mean change is the floor any "re-roll" gets
    NULL = ["phx1", "phx2", "phx3", "phx4", "phx5", "phx6", "phy2", "phy4", "phy6"]
    VARS = [("SCALE x0.7", ["sc0.7"]), ("SCALE x1.4", ["sc1.4"]), ("SCALE x0.5", ["sc0.5"]), ("SCALE x2", ["sc2.0"]),
            ("CONTEXT wide (ink)", ["wide"]), ("CONTEXT mirror (own ink)", ["mirror"]), ("CONTEXT foreign ink", ["foreign"]), ("CONTEXT wide_rule (2.167d)", ["wide_rule"]), ("CONTEXT triple", ["triple"]), ("CONTEXT system", ["system"]),
            ("CANVAS wide shape, white", ["L2white"]), ("CANVAS wide shape, grey", ["L1gray"]),
            ("MARGIN 64 white", ["mw64"]), ("MARGIN 128 white", ["mw128"]), ("MARGIN 256 white", ["mw256"]), ("MARGIN 128 grey", ["mg128"]),
            ("VERT margin 64", ["mv64"]), ("H+V margin 128", ["mwv128"]),
            ("INTERP area", ["area"]), ("PAIR wide+area", ["wide_area"]), ("FILL-only white pad", ["L3whitepad"]),
            ("POSITION centre", ["pos_c"]), ("POSITION left edge", ["pos_l"]), ("POSITION right edge", ["pos_r"]), ("GRID phase +16", ["pos_c16"])]
    P()
    P("%s EFFECT OF EACH VARIABLE ALONE (mean change of the wanted-family conf vs prod; 'null' = mean change over the 9 sampling-phase runs, which move nothing real)" % plate)
    P("  %-26s %-26s %-26s %-26s" % ("variable", "lost (n=%d)" % len(groups.get(("lost", "ALL"), [])), "D gate-dropped (n=%d)" % len(groups.get(("D", "ALL"), [])), "kept (n=%d)" % len(groups.get(("kept", "ALL"), []))))
    P("  %-26s %-26s %-26s %-26s" % ("", "dMean  share>=.25  dNull", "dMean  share>=.25", "dMean  share>=.25"))
    for nm, cs in [("NULL (phase mean)", NULL)] + VARS:
        cells_ = []
        for g in ("lost", "D", "kept"):
            L = groups.get((g, "ALL"), [])
            if not L:
                cells_.append("-")
                continue
            dm = statistics.mean([statistics.mean([conf(sc, c) for c in cs]) - conf(sc, "prod") for S, sc in L])
            sh = statistics.mean([sum(1 for c in cs if conf(sc, c) >= 0.25) / len(cs) for S, sc in L])
            nl = statistics.mean([statistics.mean([conf(sc, c) for c in NULL]) - conf(sc, "prod") for S, sc in L])
            cells_.append("%+.3f   %.2f       %+.3f" % (dm, sh, nl) if g == "lost" else "%+.3f   %.2f" % (dm, sh))
        P("  %-26s %-26s %-26s %-26s" % (nm, cells_[0], cells_[1], cells_[2]))
        summary[plate].setdefault("effects", {})[nm] = cells_
    # ---- paired bootstrap of the excess over the null for the lost group (resample symbols, 2000 draws)
    import random
    rnd = random.Random(2171)
    Lg = groups.get(("lost", "ALL"), [])
    P()
    P("%s EXCESS OVER THE PHASE NULL, lost symbols (n=%d): mean of [conf(cond) - mean conf over the 9 phase runs], 95%% paired-bootstrap interval" % (plate, len(Lg)))
    for nm, c_ in (("wide (context, same px)", "wide"), ("wide_rule (2.167d)", "wide_rule"), ("mirror (own ink)", "mirror"), ("foreign ink", "foreign"),
                   ("white canvas, wide shape", "L2white"), ("white margin 128", "mw128"), ("triple", "triple"), ("system", "system"),
                   ("scale x0.5", "sc0.5"), ("scale x0.7", "sc0.7"), ("scale x1.4", "sc1.4"), ("interp area", "area"), ("wide + area", "wide_area")):
        xs = [conf(sc, c_) - statistics.mean([conf(sc, q) for q in NULL]) for S, sc in Lg if c_ in sc]
        if not xs:
            continue
        bs = sorted(statistics.mean(rnd.choice(xs) for _ in xs) for _ in range(2000))
        P("  %-26s %+.3f   [%+.3f, %+.3f]%s" % (nm, statistics.mean(xs), bs[50], bs[1949], "   <- interval excludes 0" if bs[50] > 0 or bs[1949] < 0 else ""))
    # ---- attribution of a recovery: lost symbols (prod < 0.25) that a condition lifts to >= 0.25
    P()
    P("%s RECOVERY ATTRIBUTION, lost symbols (A/B/C) with a located wanted-family box: which single change lifts the best wanted box to >= 0.25?" % plate)
    L = groups.get(("lost", "ALL"), [])
    P("  n lost = %d; prod >= 0.25: %d" % (len(L), sum(1 for S, sc in L if conf(sc, "prod") >= 0.25)))
    ATT = [("any phase shift (null)", NULL), ("scale (0.5..2)", ["sc0.5", "sc0.7", "sc0.85", "sc1.20", "sc1.4", "sc2.0"]), ("wide ink", ["wide"]),
           ("any context (wide/triple/system)", ["wide", "triple", "system"]), ("white canvas/margins", ["L2white", "mw32", "mw64", "mw128", "mw256", "mv64", "mwv128"]),
           ("grey canvas", ["L1gray", "mg128"]), ("interp area", ["area"]), ("grid position", ["pos_c", "pos_l", "pos_r", "pos_c8", "pos_c16", "pos_c24"])]
    for nm, cs in ATT:
        hit = [(S, sc) for S, sc in L if conf(sc, "prod") < 0.25 and max(conf(sc, c) for c in cs) >= 0.25]
        P("  lifted by %-34s: %2d of %2d   (by the single run: %s)" % (nm, len(hit), len(L), ", ".join("%s %d" % (c, sum(1 for S, sc in L if conf(sc, 'prod') < .25 and conf(sc, c) >= .25)) for c in cs)))
    # symbols lifted by wide ink but not by canvas, scale, interp or phase
    only = [(S, sc) for S, sc in L if conf(sc, "prod") < 0.25 and conf(sc, "wide") >= 0.25 and max(conf(sc, c) for c in NULL + ["L2white", "mw64", "mw128", "mw256", "area"]) < 0.25]
    P("  lifted by wide INK but by none of: phase shifts, white canvas, margins, area interpolation: %d" % len(only))
    for S, sc in only:
        P("      %s %s %s rec %.2f -> wide %.2f" % (S["key"], S["cause"], S["cls"] or "-", S["rec_conf"] or 0, conf(sc, "wide")))
    P("  lifted by something, never by wide ink: %d" % sum(1 for S, sc in L if conf(sc, "prod") < 0.25 and conf(sc, "wide") < 0.25 and max(conf(sc, c) for c in COND_ORDER if c in sc) >= 0.25))
    P("  lifted by nothing at all: %d" % sum(1 for S, sc in L if max(conf(sc, c) for c in COND_ORDER if c in sc) < 0.25))
    # ---- the 0.13 -> 0.60 pattern: symbols that cross the 0.25 floor between prod and wide_rule
    P()
    P("%s symbols with prod < 0.25 and wide_rule >= 0.5 (the 2.167d pattern): which single change reproduces it?" % plate)
    cnt = 0
    for S, sc, key in rows:
        if conf(sc, "prod") < 0.25 and conf(sc, "wide_rule") >= 0.5:
            cnt += 1
            P("  %s %s %-12s rec %.2f | " % (key, group_of(S), S["cls"] or "-", S["rec_conf"] or 0) + " ".join("%s=%.2f" % (c, conf(sc, c)) for c in ("prod", "wide", "wide_rule", "mirror", "foreign", "triple", "system", "L1gray", "L2white", "L3whitepad", "area", "wide_area", "phx3", "phx6", "pos_c", "pos_c16", "sc0.7", "sc1.4")))
    P("  (%d symbols)" % cnt)
    # ---- new boxes (false-box census) per condition on the same bars
    P()
    P("%s boxes >= 0.25 of dot/flag/rest/head inside the bar's own x-range, not in prod (new), and prod boxes not kept (lost); 45 bars" % plate)
    tot = defaultdict(lambda: defaultdict(int))
    for key, r in R.items():
        if "conds" not in r:
            continue
        x0, y0, x1, y1 = r["meta"]["cell"]
        top, bot = r["meta"]["lines"]
        sp = r["meta"]["spacing"]

        def inbar(b):
            cx, cy = (b[2] + b[4]) / 2, (b[3] + b[5]) / 2
            return b[1] >= 0.25 and fam(b[0]) != "other" and x0 <= cx <= x1 and top - 3 * sp <= cy <= bot + 3 * sp
        prod = [b for b in r["conds"]["prod"]["boxes"] if inbar(b)]
        tot["prod"]["n"] += len(prod)
        for cond, v in r["conds"].items():
            if cond == "prod":
                continue
            bs = [b for b in v["boxes"] if inbar(b)]
            tot[cond]["n"] += len(bs)
            tot[cond]["new"] += sum(1 for b in bs if not any(fam(a[0]) == fam(b[0]) and iou(a[2:6], b[2:6]) > 0.4 for a in prod))
            tot[cond]["lost"] += sum(1 for a in prod if not any(fam(a[0]) == fam(b[0]) and iou(a[2:6], b[2:6]) > 0.4 for b in bs))
    for cond in COND_ORDER:
        if cond in tot and not cond.startswith("pos_"):
            P("  %-11s boxes %4d  new %3d  lost %3d" % (cond, tot[cond]["n"], tot[cond]["new"], tot[cond]["lost"]))
    summary[plate]["newboxes"] = {k: dict(v) for k, v in tot.items()}
open(D + "analysis.txt", "w").write("\n".join(out))
json.dump(summary, open(D + "summary.json", "w"), indent=1)
