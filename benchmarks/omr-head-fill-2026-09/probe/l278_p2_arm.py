"""ROADMAP 2.78 Phase 2 -- re-adjudicate a saved GATHER with the stem decisions, score, and tabulate.

PATH: STAGED, GATHER + ADJUDICATE only (CLAUDE.md §6b). A saved record's GATHER rows are replayed
(`review.rerun.rebuild_gather`) and ADJUDICATE is run on them with the CURRENT tree. That is valid
for an ADJUDICATE-only change and BLIND to any GATHER change (the module docstring of `rerun`
says so); this lane changes no GATHER code.

    python3 benchmarks/omr-head-fill-2026-09/probe/l278_p2_arm.py DOC RECORD.json --out arm.json

THE CONTROL COMES FIRST AND CAN FAIL: before the new quantities are read, the replay's standing
verdicts for the quantities the stem rule READS (duration, stem direction, the two notehead
refusals, glyph owner) are compared with the record's own. A replay that does not reproduce them
makes every number below a measurement of the replay. `--break-control` perturbs one GATHER row and
the control then fails (run it once; the result is in FINDINGS).

Writes a small JSON: the control, the 14-stem scoring (lit/brahms), every kept head's own reading
beside its stem value, and the before/after stem tables.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())

QUANTITIES_READ = ("duration", "stem_direction", "notehead_is_not_a_notehead",
                   "notehead_is_a_whole_rest", "glyph_owner")

# Sean's 14 blind tiles, by (doc, the PHASE-1 stem row id) -> (tile number, expected written value)
TILES = {("lit", "obs:037466"): (1, 0.5), ("lit", "obs:037039"): (2, 2.0),
         ("brahms", "obs:009128"): (3, 3.0), ("brahms", "obs:009105"): (4, 3.0),
         ("brahms", "obs:035946"): (5, 3.0), ("lit", "obs:038306"): (6, 2.0),
         ("lit", "obs:023868"): (7, 2.0), ("brahms", "obs:039384"): (8, 3.0),
         ("brahms", "obs:034176"): (9, 0.5), ("lit", "obs:023587"): (10, 2.0),
         ("lit", "obs:023597"): (11, 2.0), ("brahms", "obs:008879"): (12, 3.0),
         ("brahms", "obs:008886"): (13, 3.0), ("lit", "obs:023410"): (14, 2.0)}


def _summ(v):
    """One verdict -> a small comparable dict."""
    if v is None:
        return None
    out = {"outcome": v["outcome"], "reason": v["reason"]}
    if v["outcome"] == "decided":
        out["value"] = v.get("value")
    elif v["outcome"] == "narrowed":
        out["candidates"] = [c.get("value") for c in v.get("candidates") or ()]
    return out


def readjudicate(record_path, break_control=False):
    from tools.omr.staged import adjudicate, adjudicators  # noqa: F401
    from tools.omr.staged import readout
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun
    t0 = time.time()
    result = load_record(record_path)
    rec = result["record"]
    if break_control:
        # perturb ONE GATHER row the stem rule reads: every `glyph_box` of one head moves 40 px
        for o in rec["observations"]:
            if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/3/0/5/2/"):
                v = list(o["value"])
                v[1] = float(v[1]) + 400.0
                o["value"] = v
                break
    log, id_map = rerun.rebuild_gather(rec)
    adjudicate.run(log)
    new = log.to_json()
    arm = dict(result)
    arm["record"] = new
    run_new = readout.run_from_result(arm, path="<readjudicated>")
    run_old = readout.run_from_result(result, path=record_path)
    print(f"re-adjudicated in {time.time() - t0:.0f}s: {len(new['verdicts'])} verdicts "
          f"(record had {len(rec['verdicts'])})", file=sys.stderr)
    return run_old, run_new, id_map


def control(run_old, run_new):
    """The replay must reproduce the record's own standing verdicts for what the rule reads."""
    rows = {}
    for q in QUANTITIES_READ:
        n = same = 0
        diff = []
        old = {}
        for v in run_old.verdicts:
            if v["quantity"] == q:
                old[v["subject"]] = v
        new = {}
        for v in run_new.verdicts:
            if v["quantity"] == q:
                new[v["subject"]] = v
        for sub, ov in old.items():
            nv = new.get(sub)
            n += 1
            a, b = _summ(ov), _summ(nv)
            if a == b:
                same += 1
            elif len(diff) < 3:
                diff.append((sub, a, b))
        rows[q] = {"old": len(old), "new": len(new), "compared": n, "identical": same,
                   "only_new": len(set(new) - set(old)), "examples": diff}
    return rows


def _kept(run, g):
    from tools.omr.staged import readout
    st, _ = readout.adjudicate_status(run, g)
    return st in ("kept", "narrowed", "abstained")


def _stem_of(run, key):
    v = run.standing(key, "head_stem", "ADJUDICATE")
    return v


def head_table(run_old, run_new, doc, pages=None):
    """Per kept notehead: its own duration reading and its stem value."""
    out = {}
    for key, g in run_new.glyphs.items():
        if g.family != "note" or (pages is not None and g.page not in pages):
            continue
        if not _kept(run_new, g):
            continue
        own = _summ(run_new.standing(key, "duration", "ADJUDICATE"))
        sv = _summ(run_new.standing(key, "stem_value", "ADJUDICATE"))
        hs = run_new.standing(key, "head_stem", "ADJUDICATE")
        out[key] = {"own": own, "stem_value": sv,
                    "join": None if hs is None else {"outcome": hs["outcome"], "reason": hs["reason"],
                                                     "stem": hs.get("value"),
                                                     "stem_box": (hs.get("detail") or {}).get("stem_box")},
                    "cls": g.cls, "page": g.page, "cell": g.cell_key,
                    "box_page": list(g.box_page) if g.box_page else None,
                    "box_canon": list(g.box_canon) if g.box_canon else None}
    return out


def _vals(s):
    """A summary -> the set of (written, dots, beam_levels) it admits (None = unread)."""
    if not s:
        return None
    if s["outcome"] == "decided" and isinstance(s.get("value"), dict):
        v = s["value"]
        return {(round(float(v["written"]), 4), int(v.get("dots") or 0), int(v.get("beam_levels") or 0))}
    if s["outcome"] == "narrowed":
        return {(round(float(c["written"]), 4), int(c.get("dots") or 0), int(c.get("beam_levels") or 0))
                for c in s["candidates"] if isinstance(c, dict) and "written" in c}
    return None


def score_tiles(doc, run_old, run_new, id_map, manifest):
    rows = []
    for t in manifest["tiles"]:
        stem_old = t["stem_row"]
        key = (doc, stem_old)
        if key not in TILES:
            continue
        n, want = TILES[key]
        for head in t["subject"]:
            g = run_new.glyphs.get(head)
            if g is None:
                continue
            refused = not _kept(run_new, g)
            sv = _summ(run_new.standing(head, "stem_value", "ADJUDICATE"))
            own = _summ(run_new.standing(head, "duration", "ADJUDICATE"))
            vals = _vals(sv)
            if refused:
                verdict = "refused (not scored: not a member)"
            elif sv is None:
                verdict = "no verdict"
            elif sv["outcome"] == "decided":
                verdict = "RIGHT" if any(abs(v[0] - want) < 1e-6 for v in vals) else "WRONG"
            elif sv["outcome"] == "narrowed":
                inside = any(abs(v[0] - want) < 1e-6 for v in vals)
                verdict = "NARROWED, answer inside" if inside else "NARROWED, answer NOT inside"
            else:
                verdict = f"ABSTAINED ({sv['reason']})"
            rows.append({"tile": n, "doc": doc, "head": head, "want": want, "cls": g.cls,
                         "status": "refused" if refused else "kept", "own": own, "stem_value": sv,
                         "verdict": verdict})
    return rows


def stem_tables(heads):
    """Group kept heads by the stem their join names; before = their OWN readings, after = stem_value."""
    by_stem = collections.defaultdict(list)
    for key, h in heads.items():
        j = h["join"]
        if j and j["outcome"] == "decided":
            by_stem[(h["cell"], j["stem"])].append((key, h))
    multi = {k: v for k, v in by_stem.items() if len(v) >= 2}

    def klass(readings):
        """readings: list of summaries -> a partition word (the Phase-1 partition, coarse)."""
        dec = [_vals(r) for r in readings if r and r["outcome"] == "decided"]
        nar = [r for r in readings if r and r["outcome"] == "narrowed"]
        un = [r for r in readings if not r or r["outcome"] not in ("decided", "narrowed")]
        dv = {next(iter(d)) for d in dec if d}
        if len(dv) >= 2:
            fills = {(d[0] / (2 ** d[2])) for d in dv}
            return "decided heads DISAGREE"
        if len(dv) == 1 and not nar and not un:
            return "agree (all decided, one value)"
        if len(dv) == 1:
            return "one value decided, others narrowed/unread"
        if nar and not un:
            sets = {frozenset(_vals(r) or ()) for r in nar}
            return "all narrowed, identical" if len(sets) == 1 else "all narrowed, differ"
        return "unread"

    before, after = collections.Counter(), collections.Counter()
    changed = []
    for (cell, stem), members in sorted(multi.items()):
        before[klass([h["own"] for _k, h in members])] += 1
        after[klass([h["stem_value"] for _k, h in members])] += 1
        for key, h in members:
            if _vals(h["own"]) != _vals(h["stem_value"]):
                changed.append({"head": key, "cell": cell, "stem": stem, "own": h["own"],
                                "stem_value": h["stem_value"], "cls": h["cls"], "page": h["page"],
                                "box_page": h["box_page"],
                                "members": [k for k, _h in members]})
    # every multi-member stem, changed or not, for the tile pool and its controls
    stems_out = []
    for (cell, stem), members in sorted(multi.items()):
        stems_out.append({"cell": cell, "stem": stem, "page": members[0][1]["page"],
                          "stem_box": members[0][1]["join"].get("stem_box"),
                          "changed": any(_vals(h["own"]) != _vals(h["stem_value"]) for _k, h in members),
                          "heads": [{"key": k, **{kk: h[kk] for kk in ("own", "stem_value", "cls", "box_page",
                                                                       "box_canon")}} for k, h in members]})
    tables_extra = {"stems": stems_out}
    reasons = collections.Counter()
    for _k, members in multi.items():
        for _kk, h in members:
            if h["stem_value"]:
                reasons[(h["stem_value"]["outcome"], h["stem_value"]["reason"])] += 1
    return {"multi_member_stems": len(multi), "before": dict(before), "after": dict(after),
            "reasons": {f"{a}:{b}": n for (a, b), n in sorted(reasons.items())},
            **tables_extra}, changed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("doc", choices=("lit", "brahms"))
    ap.add_argument("record")
    ap.add_argument("--manifest", default="out/print/2.78-review/manifest.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--break-control", action="store_true")
    a = ap.parse_args(argv)
    run_old, run_new, id_map = readjudicate(a.record, a.break_control)
    ctl = control(run_old, run_new)
    print("== control: the replay reproduces the record's own verdicts for what the rule reads ==")
    bad = 0
    for q, r in ctl.items():
        print(f"   {q:<30} compared {r['compared']:>5}  identical {r['identical']:>5}  "
              f"(record {r['old']}, replay {r['new']}, replay-only {r['only_new']})")
        bad += r["compared"] - r["identical"]
    print("   CONTROL", "PASSED" if bad == 0 else f"FAILED: {bad} verdicts differ")
    manifest = json.load(open(a.manifest))
    tiles = score_tiles(a.doc, run_old, run_new, id_map, manifest)
    print("== Sean's 14 stems (this document's tiles) ==")
    for r in tiles:
        print(f"   T{r['tile']:<2} {r['head']:<22}{r['cls'].replace('notehead', ''):<18}{r['status']:<8}"
              f"want {r['want']:<4} own {_vals(r['own'])}  ->  stem value {_vals(r['stem_value'])}  "
              f"[{(r['stem_value'] or {}).get('reason')}]  {r['verdict']}")
    heads = head_table(run_old, run_new, a.doc)
    tables, changed = stem_tables(heads)
    print("== population (kept heads on a stem with >= 2 kept members) ==")
    print("   multi-member stems:", tables["multi_member_stems"])
    print("   BEFORE (the heads' own readings):", tables["before"])
    print("   AFTER  (the stem value):         ", tables["after"])
    print("   stem_value reasons over those heads:", tables["reasons"])
    print(f"   heads whose value CHANGED: {len(changed)}")
    json.dump({"doc": a.doc, "control": ctl, "tiles": tiles, "tables": tables, "changed": changed,
               "heads": heads}, open(a.out, "w"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
