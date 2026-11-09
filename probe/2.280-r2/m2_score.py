"""2.280 micro test: score m1_prototype output against the pre-registered bars (RULES.md). usage: m2_score.py"""
import collections
import json

R = {}
for p in ("litolff", "brahms"):
    d = json.load(open(__import__("os").environ["R2_OUT"] + "/proto_%s.json" % p))
    for s, r in d["results"].items():
        r["plate"] = p
        R[p + ":" + s] = r
    print(p, "control (my copy of the ruler == gather.measure_head_stem, direction):", d["control"])


def grp(g):
    return {k: r for k, r in R.items() if g in r["groups"]}


def filed(r, arm="B"):
    return r[arm]["status"] == "filed"


real, nn = grp("real51"), grp("notnote30")
print("\n== populations: real", len(real), "not-notes", len(nn), "decided", len(grp("decided299")), "agree", len(grp("agree200")))

print("\n== arm A (shipped ruler, raw raster) on the 83")
for name, pool in (("real51", real), ("notnote30", nn)):
    for key in ("A_ship", "A_local"):
        c = collections.Counter(r[key] for r in pool.values())
        print("  %-9s %-8s %s   up/down: %d (%.0f%%)" % (name, key, dict(c), c["up"] + c["down"], 100.0 * (c["up"] + c["down"]) / len(pool)))

print("\n== BAR 1 reach: arm B files a stem for >= 85% of the 51 real heads")
for arm in ("B", "B_noclaims", "C_flip"):
    n = sum(filed(r, arm) for r in real.values())
    print("  %-10s %d / %d = %.1f%%" % (arm, n, len(real), 100.0 * n / len(real)))
for lab in ("H", "D", "S"):
    sub = {k: r for k, r in real.items() if r["label"] == lab}
    print("    label %s: arm B %d/%d   noclaims %d/%d   flip %d/%d   (A up/down %d)" % (
        lab, sum(filed(r) for r in sub.values()), len(sub), sum(filed(r, "B_noclaims") for r in sub.values()), len(sub),
        sum(filed(r, "C_flip") for r in sub.values()), len(sub), sum(r["A_ship"] in ("up", "down") for r in sub.values())))
print("  arm B why-abstain on real:", dict(collections.Counter(r["B"].get("why") for r in real.values() if not filed(r))))
print("  arm B kind:", dict(collections.Counter(r["B"].get("kind") for r in real.values() if filed(r))))

print("\n== BAR 2 false stems: at most 1 of the 30 not-notes")
for arm in ("B", "B_noclaims", "C_flip"):
    n = sum(filed(r, arm) for r in nn.values())
    print("  %-10s %d / %d" % (arm, n, len(nn)))
for k, r in nn.items():
    if filed(r):
        print("    FALSE STEM", k, r["label"], r["B"]["direction"], r["B"].get("kind"), r["B"]["box"])
print("  by label: ", {lab: (sum(filed(r) for r in nn.values() if r["label"] == lab), sum(1 for r in nn.values() if r["label"] == lab)) for lab in ("R", "N")})

print("\n== BAR 4 side control")
a = sum(filed(r) for r in real.values())
c = sum(filed(r, "C_flip") for r in real.values())
print("  reach B %.1f%%  flipped %.1f%%  drop %.1f points (need >= 30)" % (100.0 * a / len(real), 100.0 * c / len(real), 100.0 * (a - c) / len(real)))
ag = grp("agree200")
a2 = sum(filed(r) for r in ag.values())
c2 = sum(filed(r, "C_flip") for r in ag.values())
print("  (extra, on the 200 stemmed heads) reach B %.1f%%  flipped %.1f%%  drop %.1f points" % (100.0 * a2 / len(ag), 100.0 * c2 / len(ag), 100.0 * (a2 - c2) / len(ag)))


# ---- agreement -------------------------------------------------------------------------------------------------------------
def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def row_dir(rb, pb):
    hc = (pb[1] + pb[3]) / 2.0
    return "up" if (rb[1] + rb[3]) / 2.0 < hc else "down"


print("\n== BAR 3 agreement on the 200 heads that already have a shipped stem row")
cnt = collections.Counter()
detail = []
for k, r in ag.items():
    B = r["B"]
    if B["status"] != "filed":
        cnt["abstain"] += 1
        detail.append((k, "abstain", B.get("why")))
        continue
    best = None
    for rb in r["row_boxes"]:
        v = iou(B["box"], rb)
        if best is None or v > best[0]:
            best = (v, rb)
    if best is None:
        cnt["no_row_box_found"] += 1
        detail.append((k, "no_row_box"))
        continue
    same_stem = best[0] >= 0.5
    same_dir = B["direction"] == row_dir(best[1], r["page_box"])
    # looser same-stem test (labelled as such, NOT the registered one): x-centres within 0.35 sp and the y-ranges overlap by >= half the shorter
    rb = best[1]
    sp = r["sp"]
    xc = abs((B["box"][0] + B["box"][2]) / 2.0 - (rb[0] + rb[2]) / 2.0) <= 0.35 * sp
    yo = max(0.0, min(B["box"][3], rb[3]) - max(B["box"][1], rb[1])) / max(1.0, min(B["box"][3] - B["box"][1], rb[3] - rb[1]))
    loose = xc and yo >= 0.5
    cnt[("iou>=.5" if same_stem else "iou<.5", "dir_same" if same_dir else "dir_diff", "loose_same" if loose else "loose_diff")] += 1
    if not (same_stem and same_dir):
        detail.append((k, "disagree", round(best[0], 2), B["direction"], row_dir(best[1], r["page_box"]), "loose" if loose else "nolose"))
n_strict = sum(v for k, v in cnt.items() if isinstance(k, tuple) and k[0] == "iou>=.5" and k[1] == "dir_same")
n_loose = sum(v for k, v in cnt.items() if isinstance(k, tuple) and k[1] == "dir_same" and k[2] == "loose_same")
n_filed = sum(v for k, v in cnt.items() if isinstance(k, tuple))
n_dir_same = sum(v for k, v in cnt.items() if isinstance(k, tuple) and k[1] == "dir_same")
print("  breakdown:", dict(cnt))
print("  REGISTERED (same stem IoU>=0.5 and same direction; an abstention counts as a disagreement): %d / %d = %.1f%% (need 98)" % (n_strict, len(ag), 100.0 * n_strict / len(ag)))
print("  of those filed (%d): same stem+dir %d (%.1f%%); same DIRECTION %d (%.1f%%); loose same stem + dir %d (%.1f%%)" % (
    n_filed, n_strict, 100.0 * n_strict / max(1, n_filed), n_dir_same, 100.0 * n_dir_same / max(1, n_filed), n_loose, 100.0 * n_loose / max(1, n_filed)))
json.dump(detail, open(__import__("os").environ["R2_OUT"] + "/agree_disagreements.json", "w"), indent=0)

print("\n== the 299 decided no-stem heads (arm B files a row for?)")
dd = grp("decided299")
print("  arm B filed %d / %d; by kind %s; why-abstain %s" % (sum(filed(r) for r in dd.values()), len(dd),
      dict(collections.Counter(r["B"].get("kind") for r in dd.values() if filed(r))), dict(collections.Counter(r["B"].get("why") for r in dd.values() if not filed(r)))))
print("  arm A up/down %d" % sum(r["A_ship"] in ("up", "down") for r in dd.values()))
