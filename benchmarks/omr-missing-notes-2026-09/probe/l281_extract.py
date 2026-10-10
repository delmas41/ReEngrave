#!/usr/bin/env python3
"""l281_extract: ONE streamed read of a record, everything ROADMAP 2.81 Phase 1 needs
about the "bare stem" population, into a small JSON. A reading probe: it decides
nothing and changes no product code.

WHY STREAMED. `record_io.load_record` measured 6.6x the file resident
(UNDECIDED.md sec.5); the 5.3 GB Brahms record would need ~35 GB. `ijson` over the
file keeps only the unpooled fields it names (`basis`, `considered`, `correlated`,
the only pooled ones, are never read), the same reader `lud_extract.py --stream`
used and bit-compared against `load_record` on Litolff. This script repeats that
control: `--control RECORD_SMALL` loads it BOTH ways and compares the extracts.

THREE PASSES, each its own `--what`, so the three can run in parallel:

  obs   note heads (`Q.GLYPH_BOX`, class + canonical and page box), and per CELL the
        `Q.STEM`, `Q.STEM_TIP_INK`, `Q.STEM_SLASH` rows, per head `Q.HEAD_STEM_REACH`
  abs   `Q.STEM_TIP_INK` ABSTENTIONS (the reason word is what says `occupied`)
  ver   per note head, every `Q.DURATION` verdict at every stage (ADJUDICATE,
        EVALUATE, INFER, with `supersedes`), plus `Q.HEAD_STEM`, `Q.STEM_DIRECTION`,
        `Q.STEM_VALUE`, `Q.GLYPH_OWNER`, `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`,
        `Q.NOTEHEAD_IS_A_WHOLE_REST` (their decided standing only, no detail)

    python3 l281_extract.py --what obs --record R --out obs.json [--pages 0,1]
"""
import argparse
import collections
import json
import sys
import time
from pathlib import Path

import ijson

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged.record import Q  # noqa: E402

LIST_CAP = 12


def compact(d):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, (list, tuple)) and len(v) > LIST_CAP:
            out[k] = f"<list {len(v)}>"
        elif isinstance(v, dict) and len(json.dumps(v, default=str)) > 400:
            out[k] = f"<dict {len(v)}>"
        else:
            out[k] = v
    return out


def key_page(subject):
    p = subject.split("/")
    try:
        return int(p[1])
    except (IndexError, ValueError):
        return None


def want_page(subject, pages):
    return pages is None or key_page(subject) in pages


def cell_of(glyph_key):
    p = glyph_key.split("/")
    return "cell/" + "/".join(p[1:5])


def pass_obs(path, pages):
    heads, stems, tips, slashes, reach = {}, {}, collections.defaultdict(list), {}, {}
    beams, beam_ink, space = {}, {}, {}
    n = 0
    t0 = time.time()
    with open(path, "rb") as fh:
        for o in ijson.items(fh, "record.observations.item", use_float=True):
            n += 1
            q = o["quantity"]
            s = o["subject"]
            if q == Q.GLYPH_BOX:
                v = o["value"]
                if not (isinstance(v, list) and v and isinstance(v[0], str)
                        and v[0].startswith("notehead")):
                    continue
                if not want_page(s, pages):
                    continue
                d = o.get("detail") or {}
                heads[s] = {"cls": v[0], "canon": v[1:5], "page": d.get("bbox_page_px"),
                            "score": o.get("score"), "frame": o.get("frame"),
                            "obs": o["id"]}
            elif q == Q.STEM:
                if want_page(s, pages):
                    stems.setdefault(s, {})[o["id"]] = o["value"]
            elif q == Q.STEM_TIP_INK:
                if want_page(s, pages):
                    d = o.get("detail") or {}
                    tips[s].append({"id": o["id"], "stem": d.get("stem_row_id"),
                                    "end": d.get("end"), "value": o["value"],
                                    "right": d.get("right"), "left": d.get("left"),
                                    "hooks": d.get("hooks"), "hmin": d.get("hooks_min"),
                                    "hmax": d.get("hooks_max"),
                                    "hwhy": d.get("hooks_reason"),
                                    "window": d.get("window_canonical")})
            elif q == Q.STEM_SLASH:
                if want_page(s, pages):
                    d = o.get("detail") or {}
                    slashes.setdefault(s, {})[d.get("stem_row_id")] = o["value"]
            elif q == Q.HEAD_STEM_REACH:
                if want_page(s, pages):
                    reach[s] = o["value"]
            elif q == Q.BEAM_STROKE:
                if want_page(s, pages):
                    beams.setdefault(s, {})[o["id"]] = {"box": o["value"], "reader": o.get("reader")}
            elif q == Q.BEAM_STROKE_INK:
                if want_page(s, pages):
                    d = o.get("detail") or {}
                    beam_ink[d.get("beam_row_id")] = {
                        "thickness_ratio": d.get("thickness_ratio"),
                        "sagitta": d.get("sagitta_spaces"),
                        "end_stems": [bool(e.get("found")) for e in (d.get("end_stems") or [])]}
            elif q == Q.CELL_STAFF_SPACE:
                if want_page(s, pages) and s not in space:
                    space[s] = o["value"]
    print(f"obs pass: {n} rows, {len(heads)} heads, {len(stems)} cells with stems, "
          f"{sum(len(v) for v in tips.values())} tip rows, {time.time() - t0:.0f}s", flush=True)
    return {"heads": heads, "stems": stems, "tips": dict(tips), "slashes": slashes,
            "reach": reach, "beams": beams, "beam_ink": beam_ink, "space": space}


def pass_abs(path, pages):
    tips = collections.defaultdict(list)
    n = 0
    t0 = time.time()
    with open(path, "rb") as fh:
        for o in ijson.items(fh, "record.abstentions.item", use_float=True):
            n += 1
            if o["quantity"] != Q.STEM_TIP_INK:
                continue
            s = o["subject"]
            if not want_page(s, pages):
                continue
            d = o.get("detail") or {}
            tips[s].append({"id": o["id"], "stem": d.get("stem_row_id"),
                            "end": d.get("end"), "reason": o.get("reason")})
    print(f"abs pass: {n} rows, {sum(len(v) for v in tips.values())} tip abstentions, "
          f"{time.time() - t0:.0f}s", flush=True)
    return {"tips_abs": dict(tips)}


KEEP_Q = {Q.HEAD_STEM, Q.STEM_DIRECTION, Q.STEM_VALUE, Q.GLYPH_OWNER,
          Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.NOTEHEAD_IS_A_WHOLE_REST, Q.DURATION}


def stage_of(decider):
    from tools.omr.staged import trace
    return trace.stage_of_decider(decider)


def pass_ver(path, pages):
    out = collections.defaultdict(list)
    n = 0
    t0 = time.time()
    stage_cache = {}
    with open(path, "rb") as fh:
        for v in ijson.items(fh, "record.verdicts.item", use_float=True):
            n += 1
            q = v["quantity"]
            if q not in KEEP_Q:
                continue
            s = v["subject"]
            if not s.startswith("glyph/") or not want_page(s, pages):
                continue
            dec = v["decider"]
            if dec not in stage_cache:
                stage_cache[dec] = stage_of(dec)
            st = stage_cache[dec]
            row = {"id": v["id"], "q": q, "stage": st, "decider": dec,
                   "outcome": v["outcome"], "reason": v.get("reason"),
                   "supersedes": v.get("supersedes")}
            if q == Q.DURATION:
                row["value"] = v.get("value")
                row["cands"] = [c.get("value") for c in (v.get("candidates") or [])]
                row["detail"] = compact(v.get("detail"))
            elif q in (Q.HEAD_STEM, Q.GLYPH_OWNER, Q.STEM_DIRECTION):
                row["value"] = v.get("value")
            elif q == Q.NOTEHEAD_IS_NOT_A_NOTEHEAD or q == Q.NOTEHEAD_IS_A_WHOLE_REST:
                row["value"] = v.get("value")
            elif q == Q.STEM_VALUE:
                row["value"] = v.get("value")
            out[s].append(row)
    print(f"ver pass: {n} rows, {len(out)} head subjects, {time.time() - t0:.0f}s", flush=True)
    return {"verdicts": dict(out)}


def provenance(path):
    with open(path, "rb") as fh:
        for p in ijson.items(fh, "provenance", use_float=True):
            return {"commit": p.get("commit"), "dirty": p.get("dirty"),
                    "args": (p.get("settings") or {}).get("args")}
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", choices=("obs", "abs", "ver", "prov"), required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default=None, help="comma list of PDF page indices; default all")
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",")} if a.pages else None
    fn = {"obs": pass_obs, "abs": pass_abs, "ver": pass_ver}.get(a.what)
    res = provenance(a.record) if a.what == "prov" else fn(a.record, pages)
    Path(a.out).write_text(json.dumps(res, separators=(",", ":"), default=str))
    print(f"wrote {a.out} ({Path(a.out).stat().st_size / 1e6:.1f} MB)", flush=True)


if __name__ == "__main__":
    main()
