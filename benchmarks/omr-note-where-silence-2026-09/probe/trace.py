"""EACH LONE NOTE, BACK TO ITS OWN INK -- and the whole-page distributions
that say whether that ink is unusual.

The population probe says a bar holds one note and half a bar's worth of time.
This says WHICH DETECTION that note is, what the detector called it, and where
its box sits against ITS OWN STAFF'S LINES -- which is the only join that can
tell *"a whole rest read as a notehead"* from *"the staff above's note landed
here"* from *"an ordinary note whose neighbours were never read"*. All three are
one lone note in an underfull bar and the FILE cannot separate them.

⚠️ THE DISTRIBUTIONS ARE THE CONTROL AND THEY COME FIRST. A cut read off the
suspects alone is a cut fitted to them. So the document's OWN detected
`restWhole` glyphs and its OWN 2,000-odd noteheads are measured in the same
units first; only then are the suspects placed in that picture. If the two
populations do not separate, no shape rule is available and this says so.

Units are STAFF SPACES and STAFF STEPS, never pixels: staves of one plate
differ in spacing and the DPI differs between runs.

    python3 .../trace.py --cache cache.json --lone lone.json [--json OUT]
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys


def _key(subject, n):
    return tuple(int(x) for x in subject.split("/")[1:1 + n])


def load(cache_path):
    c = json.load(open(cache_path))
    box, page_box, cls, conf, npos, rest = {}, {}, {}, {}, {}, {}
    lines, spacing = {}, {}
    for o in c["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            box[s] = o["value"]
            pg = (o.get("detail") or {}).get("bbox_page_px")
            if pg:
                page_box[s] = pg
        elif q == "glyph_conf":
            conf[s] = o.get("score")
        elif q == "notehead_class":
            cls[s] = o["value"]
        elif q == "rest":
            rest[s] = o["value"]
        elif q == "notehead_staff_position":
            npos[s] = o["value"]
        elif q == "staff_lines":
            lines[_key(s, 3)] = o["value"]
        elif q == "staff_spacing":
            spacing[_key(s, 3)] = o["value"]
    pitch, duration = {}, {}
    for v in c["verdicts"]:
        if v["outcome"] != "decided":
            continue
        if v["quantity"] == "pitch":
            pitch[v["subject"]] = v["value"]
        elif v["quantity"] == "duration":
            duration[v["subject"]] = v["value"]
    return dict(box=box, page_box=page_box, cls=cls, conf=conf, npos=npos,
                rest=rest, lines=lines, spacing=spacing, pitch=pitch,
                duration=duration)


def geom(R, subject):
    """(height_spaces, width_spaces, aspect, staff_step) in the PAGE frame.

    staff_step: bottom line = 0, one step per HALF space, up is positive. A
    whole rest hangs UNDER the 4th line from the bottom, so its body spans
    step 6 down to step 5 and its centre is 5.5 -- an engraving obligation,
    not a tuned number.
    """
    pb = R["page_box"].get(subject)
    k = _key(subject, 3)
    ly, sp = R["lines"].get(k), R["spacing"].get(k)
    if not pb or not ly or not sp:
        return None
    h = (pb[3] - pb[1]) / sp
    w = (pb[2] - pb[0]) / sp
    if h <= 0:
        return None
    step = (max(ly) - (pb[1] + pb[3]) / 2.0) / (sp / 2.0)
    return h, w, w / h, step


def _spell(v):
    if isinstance(v, dict):
        a = v.get("alter") or 0
        return "%s%s%s" % (v.get("step"),
                           {0: "", 1: "#", -1: "b", 2: "##", -2: "bb"}.get(a, ""),
                           v.get("octave"))
    return str(v)


def _stats(name, vals):
    if not vals:
        print(f"  {name:<26} (none)")
        return
    v = sorted(vals)
    p = lambda f: v[min(len(v) - 1, int(f * len(v)))]
    print(f"  {name:<26} n={len(v):<5} median {statistics.median(v):6.3f}   "
          f"p05 {p(0.05):6.3f}  p95 {p(0.95):6.3f}   "
          f"[{v[0]:.3f} .. {v[-1]:.3f}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--lone", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()

    R = load(a.cache)
    heads = [s for s in R["cls"]]
    wholerests = [s for s, v in R["rest"].items()
                  if str(v).lower().startswith("restwhole")]
    print("=== POSITIVE CONTROL: what the record holds ===")
    print(f"  notehead_class rows          {len(heads)}")
    print(f"  rest rows                    {len(R['rest'])}")
    print(f"    ...restWhole               {len(wholerests)}")
    print(f"  glyphs with a PAGE box       {len(R['page_box'])}")
    print(f"  decided pitches              {len(R['pitch'])}")
    if not heads or not wholerests:
        print("DEAD INSTRUMENT -- refusing to report", file=sys.stderr)
        return 2
    print()

    hg = {s: g for s in heads if (g := geom(R, s))}
    rg = {s: g for s in wholerests if (g := geom(R, s))}
    print("=== THE TWO POPULATIONS, in staff spaces / steps ===")
    print("  -- the document's own detected WHOLE RESTS --")
    _stats("height (spaces)", [g[0] for g in rg.values()])
    _stats("aspect (w/h)", [g[2] for g in rg.values()])
    _stats("staff step (5.5 = slot)", [g[3] for g in rg.values()])
    print("  -- the document's own NOTEHEADS --")
    _stats("height (spaces)", [g[0] for g in hg.values()])
    _stats("aspect (w/h)", [g[2] for g in hg.values()])
    _stats("staff step", [g[3] for g in hg.values()])
    print()

    lone = json.load(open(a.lone))
    rows, unlocated = [], 0
    for c in lone:
        w = c.get("where")
        if not w:
            unlocated += 1
            continue
        pre = "glyph/%d/%d/%d/%d/" % (w["page"], w["system"], w["staff"],
                                      w["cell"])
        here = [s for s in R["page_box"] if s.startswith(pre)]
        want = c["events"][0]["pitch"]
        mine = [s for s in here
                if s in R["cls"] and _spell(R["pitch"].get(s)) == want]
        row = {k: c[k] for k in ("part", "measure", "underfull",
                                 "lone_quarter_in_2_4")}
        row.update(where=w, exported=want,
                   dur_written=c["events"][0]["duration"],
                   bar_ql=c["bar_ql"], type=c["events"][0]["type"],
                   n_glyphs_in_cell=len(here),
                   n_heads_in_cell=sum(1 for s in here if s in R["cls"]),
                   rests_in_cell=[R["rest"][s] for s in here if s in R["rest"]])
        if not mine:
            row["bucket"] = "unjoined"
            unlocated += 1
        else:
            s = mine[0]
            g = geom(R, s)
            row.update(subject=s, cls=R["cls"][s], conf=R["conf"].get(s),
                       duration=R["duration"].get(s))
            if g:
                row.update(height_spaces=round(g[0], 3),
                           width_spaces=round(g[1], 3),
                           aspect=round(g[2], 3), staff_step=round(g[3], 2))
        rows.append(row)

    got = [r for r in rows if "aspect" in r]
    print("=== THE SUSPECTS, in the same units ===")
    print(f"  lone-note bars               {len(lone)}")
    print(f"  joined to a glyph            {len(got)}   (unjoined {unlocated})")
    for label, sel in (("ALL lone notes", got),
                       ("lone QUARTER in 2/4", [r for r in got
                                                if r["lone_quarter_in_2_4"]])):
        print(f"  -- {label} --")
        _stats("height (spaces)", [r["height_spaces"] for r in sel])
        _stats("aspect (w/h)", [r["aspect"] for r in sel])
        _stats("staff step", [r["staff_step"] for r in sel])
        _stats("detector confidence",
               [r["conf"] for r in sel if r.get("conf") is not None])
        print(f"     cells ALSO holding a detected rest: "
              f"{sum(1 for r in sel if r['rests_in_cell'])} of {len(sel)}")
        cc = collections.Counter(r["cls"][0] if isinstance(r["cls"], (list, tuple))
                                 else r["cls"] for r in sel)
        print(f"     detector class: {dict(cc)}")
    print()
    print("=== the six the handoff names ===")
    named = {("P1", 45), ("P1", 85), ("P1", 88), ("P1", 89), ("P2", 49), ("P2", 87)}
    for r in sorted(got, key=lambda r: (r["part"], r["measure"])):
        if (r["part"], r["measure"]) in named:
            w = r["where"]
            print(f"  {r['part']} m{r['measure']:<4} {r['exported']:<4} "
                  f"p{w['page']}/s{w['system']}/st{w['staff']}/c{w['cell']} "
                  f"h={r['height_spaces']:.2f} asp={r['aspect']:.2f} "
                  f"step={r['staff_step']:+.2f} conf={r['conf']} "
                  f"{r['subject']}")

    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)
        print(f"\nwrote {len(rows)} rows -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
