"""ROADMAP 2.290 build round 2 -- the picks for `make_tiles_r2.py` (READ-ONLY on the records).

    python3 benchmarks/page-heads-ledger-2026-11/build_picks_r2.py WORKDIR R1WORKDIR OUT.json [SEED=2290]

WORKDIR = this round's lane-report work dir (`<plate>.<arm>.gathered.record.json`, `.symbols.json`); R1WORKDIR = round 1's (the code before the round-2 rules).
SELECTION RULE (stated, seeded), to 12, Sean's round-1 places never shown again:
  1. every note LOST or GAINED OFF -> ON (`lost_notes.py`'s matching, by place), drawn at the claimed ink of its ON head, else at its box;
  2. then every place a round-2 rule REFUSED a round-1 claim (a round-1 head claim with no round-2 claim on its ink), `random.Random(SEED)` order, alternating
     the reasons (`too_small` / `too_tall` / `split`: the claim exists but its ink is no longer one head's) so each kind is shown;
  3. then heads newly claimed on the page ledger (round-2 claims that were not round-1 claims), seeded, the plates alternating.
Each pick: plate, page, box (page px: the claimed ink's extent, or the refused ink's), staff_lines [top line y, bottom line y], kind, why.
"""
import json
import pathlib
import random
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_picks as BP                                  # noqa: E402

R1_TILES = HERE / "answers" / "answers-2.290-build-r1.json"


def overlap_share(a, b):
    ix, iy = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    return ix * iy / float(max(1e-9, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))))


def claim_boxes(idx):
    st, boxes, mg, claims, staff = idx
    out = []
    for c in claims:
        sb = [st[(c["page"], i)] for i in c["strokes"] if (c["page"], i) in st]
        if sb:
            out.append((c, [min(b[0] for b in sb), min(b[1] for b in sb), max(b[2] for b in sb), max(b[3] for b in sb)], sb))
    return out


def staff_lines(staff, glyph):
    lines = staff.get("staff/" + "/".join(glyph.split("/")[1:4]))
    return [lines[0], lines[-1]] if lines else None


def main():
    work, w1, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 2290
    rng = random.Random(seed)
    r1_boxes = {(t["plate"], t["page"]): [] for t in json.loads(R1_TILES.read_text())["tiles"]}
    for t in json.loads(R1_TILES.read_text())["tiles"]:
        r1_boxes[(t["plate"], t["page"])].append(t["box"])

    def seen_in_r1(plate, page, box):
        return any(overlap_share(box, b) > 0.3 for b in r1_boxes.get((plate, page), []))
    lost, refused, new = [], [], []
    for plate in ("litolff", "brahms"):
        f_on = work / ("%s.on.gathered.record.json" % plate)
        if not f_on.exists():
            continue
        on = BP.index(BP.load(f_on))
        r1 = BP.index(BP.load(w1 / ("%s.on.gathered.record.json" % plate)))
        cb_on, cb_r1 = claim_boxes(on), claim_boxes(r1)
        sp = 15.75 if plate == "litolff" else 32.0
        # 1. lost / gained notes
        txt = subprocess.run([sys.executable, str(HERE / "lost_notes.py"), str(work), plate], capture_output=True, text=True,
                             cwd=str(HERE.parents[1]), env=dict(__import__("os").environ, PYTHONPATH=".")).stdout
        for ln in txt.splitlines():
            if "glyph " not in ln or not (ln.startswith("LOST") or ln.startswith("GAINED")):
                continue
            g = ln.split("glyph ")[-1].strip()
            kind = "lost" if ln.startswith("LOST") else "gained"
            if g not in on[1]:
                continue
            it = BP.item(plate, g, on[0], on[1], on[3], on[4], "note_%s" % kind)
            lines = staff_lines(on[4], g)
            if lines is None:
                continue
            lost.append(dict(plate=plate, page=it["page"], box=it["box"], staff_lines=lines, kind="note_" + kind, why=ln.split("  glyph")[0], glyph=g))
        # 2. refusals: a round-1 claim with no round-2 claim on its ink
        for c, box, sb in cb_r1:
            if any(overlap_share(box, b2) >= 0.5 for _c2, b2, _s2 in cb_on if _c2["page"] == c["page"]):
                continue
            w, h = (box[2] - box[0]) / sp, (box[3] - box[1]) / sp
            reason = "too_small" if min(w, h) < 0.6 else ("too_tall" if h > 1.5 else "split")
            lines = staff_lines(r1[4], c["rep"]) if c.get("rep") else None
            if lines is None:
                continue
            refused.append(dict(plate=plate, page=c["page"], box=[round(v, 1) for v in box], staff_lines=lines, kind="refused_" + reason,
                                why="a round-1 claim round 2 refuses (%.2f x %.2f sp)" % (w, h), glyph=c.get("rep")))
        # 3. newly claimed
        old = {(c["page"], round(b[0]), round(b[1])) for c, b, _s in cb_r1}
        for c, box, sb in cb_on:
            if (c["page"], round(box[0]), round(box[1])) in old or not c.get("rep"):
                continue
            lines = staff_lines(on[4], c["rep"])
            if lines is None:
                continue
            new.append(dict(plate=plate, page=c["page"], box=[round(v, 1) for v in box], staff_lines=lines, kind="newly_claimed", why="a head claimed only by round 2",
                            glyph=c["rep"]))
    lost = [p for p in lost if not seen_in_r1(p["plate"], p["page"], p["box"])]
    refused = [p for p in refused if not seen_in_r1(p["plate"], p["page"], p["box"])]
    new = [p for p in new if not seen_in_r1(p["plate"], p["page"], p["box"])]
    picks = sorted(lost, key=lambda p: (p["plate"], p["page"], p["box"][0]))[:12]
    by_reason = {}
    for p in refused:
        by_reason.setdefault(p["kind"], []).append(p)
    for v in by_reason.values():
        rng.shuffle(v)
    keys = sorted(by_reason)
    i = 0
    while len(picks) < 12 and any(by_reason.values()) and i < 1000:
        k = keys[i % len(keys)]
        if by_reason[k]:
            picks.append(by_reason[k].pop())
        i += 1
    for p in ("litolff", "brahms"):
        pass
    pool = {p: [x for x in new if x["plate"] == p] for p in ("litolff", "brahms")}
    for v in pool.values():
        rng.shuffle(v)
    i = 0
    while len(picks) < 12 and (pool["litolff"] or pool["brahms"]):
        k = ("litolff", "brahms")[i % 2]
        if pool[k]:
            picks.append(pool[k].pop())
        i += 1
    pathlib.Path(out).write_text(json.dumps(picks, indent=1))
    print("lost/gained", len(lost), "refused", len(refused), {k: len(v) for k, v in by_reason.items()}, "new", len(new), "-> picks", len(picks))


if __name__ == "__main__":
    main()
