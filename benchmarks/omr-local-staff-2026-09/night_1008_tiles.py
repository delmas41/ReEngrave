"""night 2026-10-08 read -- ONE tile per image for Sean: ten heads the STEM witness moved to a different staff, on pages the
stem rule was not written on.  Plain question each: "Which staff does the orange note belong to: <A> or <B>?".

Reuses `stem_owner_tiles.draw_tile` (whole system, every staff named at the left, the two candidate staves outlined blue A /
green B in a seeded order, the head orange, its stem traced as the orange line the record's `Q.HEAD_STEM_REACH` row holds).
Staff lines are the record's rows; each outlined staff's five lines are re-measured against pixel rows at the head's x and
printed to `lines_check.json`.  The answer key (what the rules said) is in key.json, NOT on the tiles.

  step 1 (READ ONLY, one load_record per document):  python3 night_1008_tiles.py extract <pick.json> <litolff.record.json> <brahms.record.json> <out.json>
  step 2:                                            python3 night_1008_tiles.py draw <pick.json> <out.json> [outdir]
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO))


def extract(pick, recs, dst):
    from tools.omr.staged.record_io import load_record
    out = {}
    for tag, path in recs.items():
        heads = [p["head"] for p in pick if p["doc"] == tag]
        want = {(int(h.split("/")[1]), int(h.split("/")[2])) for h in heads}
        hs = set(heads)
        rec = load_record(path)["record"]
        sup = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
        info = collections.defaultdict(dict)
        stems, cands, ownv = {}, collections.defaultdict(list), {}
        for o in rec["observations"]:
            q, sj = o["quantity"], o["subject"]
            if sj in hs:
                if q == "head_stem_reach":
                    stems[sj] = dict(direction=o["value"], **(o.get("detail") or {}))
                elif q == "glyph_band_distance":
                    cands[sj].append((o.get("detail") or {}).get("candidate"))
            k = sj.split("/")
            if q in ("staff_lines", "margin_label") and len(k) == 4 and k[0] == "staff" and (int(k[1]), int(k[2])) in want:
                st = info[(int(k[1]), int(k[2]))].setdefault(sj, dict(lines=None, instrument=None, margin=[]))
                if q == "staff_lines" and st["lines"] is None:
                    st["lines"] = o["value"]
                elif q == "margin_label":
                    st["margin"].append(o["value"])
        for v in rec["verdicts"]:
            k = v["subject"].split("/")
            if v["id"] in sup:
                continue
            if v["quantity"] == "instrument" and v["outcome"] == "decided" and len(k) == 4 \
                    and (int(k[1]), int(k[2])) in want and v["subject"] in info[(int(k[1]), int(k[2]))]:
                info[(int(k[1]), int(k[2]))][v["subject"]]["instrument"] = v["value"]
            if v["quantity"] == "glyph_owner" and v["subject"] in hs:
                ownv[v["subject"]] = [v["outcome"], v.get("value"), v.get("reason"), v.get("decider")]
        out[tag] = dict(stems=stems, cands={k: v for k, v in cands.items()}, owner=ownv,
                        info={f"{p}/{s}": v for (p, s), v in info.items()})
        print(tag, "stems", len(stems), "systems", len(info), flush=True)
        del rec
    Path(dst).write_text(json.dumps(out))


def check_lines(gray, lines, cx, sp):
    """Offsets (px) between the record's five lines and the pixel rows of ink at the head's x (median over columns
    clear of the head, +-1.2 sp each side)."""
    import numpy as np
    out = []
    xs = [int(cx + dx * sp) for dx in (-6, -5, -4, -3, 3, 4, 5, 6)]
    for y in lines:
        offs = []
        for x in xs:
            if x < 0 or x >= gray.shape[1]:
                continue
            col = gray[int(y) - 4:int(y) + 5, x] < 128
            if col.any():
                idx = np.nonzero(col)[0]
                offs.append(float(idx.mean() - 4))
        out.append(round(float(np.median(offs)), 2) if len(offs) >= 3 else None)
    return out


def draw(pick, ex, outdir):
    import numpy as np
    import stem_owner_tiles as ST
    import mark_group_no_owner_tiles as MG
    from frame import render_page_matching_gather
    ST.OUT = Path(outdir)
    _short = MG.short
    MG.short = lambda k, st: _short(k, st).replace(", no label", " (no name printed)")
    ST.OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261008)
    qs, keys, checks = [], [], []
    for n, p in enumerate(pick, 1):
        tag, head = p["doc"], p["head"]
        page, sysi = int(head.split("/")[1]), int(head.split("/")[2])
        e = ex[tag]
        staves = {k: v for k, v in e["info"][f"{page}/{sysi}"].items()}
        s = e["stems"][head]
        d = dict(stems={head: s}, rep={head: dict(off=[p["pool"], p["other"], None], on=[p["pool"], p["new"], "stem_toward_staff"],
                                                 off_final=[p["pool"], p["other"], None], on_final=[p["pool"], p["new"], "stem_toward_staff"])})
        label = {"A": "BASE (day) decided the other staff; the stem moves it",
                 "B": "BASE (day) abstained; the stem answers it",
                 "C": "BASE agreed; the stem owner is not the staff it is filed on"}[p["pool"]]
        q, key = ST.draw_tile(n, tag, head, d, staves, [p["new"], p["other"]], rng, label)
        key["base_owner"] = p["base"]
        key["new_owner"] = p["new"]
        key["pool"] = p["pool"]
        key["record_owner"] = e["owner"].get(head)
        qs.append(f"Tile {n:02d}: {q}")
        keys.append(key)
        # frame control: the outlined staves' lines against the page's pixel rows
        pi = render_page_matching_gather(MG.PDF[tag], page, 600)
        import cv2
        gray = cv2.cvtColor(np.asarray(pi.rgb), cv2.COLOR_RGB2GRAY) if np.asarray(pi.rgb).ndim == 3 else np.asarray(pi.rgb)
        cx = (s["head_box_page"][0] + s["head_box_page"][2]) / 2
        chk = {}
        for k in (p["new"], p["other"]):
            ls = staves[k]["lines"]
            sp = (ls[-1] - ls[0]) / 4
            chk[k] = check_lines(gray, ls, cx, sp)
        tip = s[f"{s['direction']}_tip_y"]
        ink_at_tip = bool(gray[int(tip) - 2:int(tip) + 3, int(cx) - 12:int(cx) + 13].min() < 128)
        checks.append(dict(tile=n, head=head, line_offsets_px=chk, stem_tip_y=tip, ink_near_tip=ink_at_tip))
        print(n, tag, head, p["pool"], key["size"], chk, flush=True)
    (ST.OUT / "questions.txt").write_text("\n".join(qs) + "\n")
    (ST.OUT / "key.json").write_text(json.dumps(keys, indent=1, default=str))
    (ST.OUT / "lines_check.json").write_text(json.dumps(checks, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    pick = json.loads(Path(a[1]).read_text())
    if a[0] == "extract":
        extract(pick, {"litolff": a[2], "brahms": a[3]}, a[4])
    else:
        draw(pick, json.loads(Path(a[2]).read_text()), a[3] if len(a) > 3 else str(REPO / "out/print/night_1008"))
