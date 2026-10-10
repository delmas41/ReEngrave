#!/usr/bin/env python3
"""l281_miss_rebuild: for given note heads, WHICH stroke was refused as a beam, BY WHICH TEST. A reading
probe (no product code changed): it re-runs ADJUDICATE over ONE page's saved GATHER rows and records, per
head, the strokes `adjudicate_duration` considered and what each filter did to each.

WHY THIS AND NOT THE RECORD. The saved verdict carries only COUNTS (`beams_not_by_ink_why`,
`beams_decided_arc`, ...), not which stroke each count was. The per-stroke answer exists only inside
`rhythm.adjudicate_duration`'s filters, so this wraps them (`rhythm._not_a_ledger_line`,
`_not_a_slash`, `_not_the_neighbours_beam`, `_not_a_decided_arc`, `_on_stem_side`, `_beyond_own_stem`,
`_not_a_beam_by_ink`, `_kept_beams`) and notes what each was given and what it dropped. The wrappers
call the originals and return their results UNCHANGED.

THE REBUILD (the pattern of `review/rerun.py`'s `rebuild_gather`, with the id remap its detail needs):
`Log.observe` assigns dense ids and the saved ones are sparse, so every `*_row_id` in a row's detail (a
`Q.BEAM_STROKE_INK` row's `beam_row_id`, a tip row's `stem_row_id`) is remapped to the new ids as the log
is built. FINDINGS 2.77b: without that a rebuild reproduces nothing that joins through them.

THE CONTROL, FIRST AND ABLE TO FAIL. Every head on the page that has a saved `adjudicate_duration`
verdict is compared with the rebuilt one (outcome, reason, candidate beats). The run reports the
count that differ and exits 1 if any head THE CALLER ASKED FOR differs; `--break-control` perturbs one
stroke-ink row and must then report a difference.

    python3 l281_miss_rebuild.py --rows rows.json --page 0 --keys glyph/0/0/0/3/3,... --out cap.json
"""
import argparse
import collections
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import adjudicate                       # noqa: E402
from tools.omr.staged import adjudicators, consequences      # noqa: E402,F401
from tools.omr.staged.adjudicators import rhythm as RH       # noqa: E402
from tools.omr.staged.record import Log, Q, Subject          # noqa: E402

ID_RE = re.compile(r"^(obs|abs|vrd):\d{6}$")


def row_no(rid):
    try:
        return int(str(rid).split(":")[-1])
    except (TypeError, ValueError):
        return 0


def remap(v, id_map, stats):
    if isinstance(v, str):
        if ID_RE.match(v):
            if v in id_map:
                return id_map[v]
            stats["unmapped"] += 1
        return v
    if isinstance(v, list):
        return [remap(x, id_map, stats) for x in v]
    if isinstance(v, dict):
        return {k: remap(x, id_map, stats) for k, x in v.items()}
    return v


def rebuild(data, perturb=False):
    log = Log()
    rows = [(r, "obs") for r in data["observations"]]
    rows += [(r, "abs") for r in data["abstentions"]]
    rows.sort(key=lambda t: row_no(t[0]["id"]))
    id_map, stats = {}, collections.Counter()
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = remap(dict(r.get("detail") or {}), id_map, stats)
        if kind == "obs":
            basis = tuple(id_map[b] for b in (r.get("basis") or ()) if b in id_map)
            value = r["value"]
            if perturb and r["quantity"] == Q.BEAM_STROKE_INK and detail.get("thickness_ratio") is not None:
                # the break: every stroke on the page now measures a thick beam, so no `too_thin`
                # refusal can fire and the page's narrowed heads MUST move
                detail["thickness_ratio"] = 9.0
            new = log.observe(sub, r["quantity"], value, reader=r["reader"], frame=r["frame"],
                              score=r.get("score"), derived_from=basis, **detail)
        else:
            new = log.abstain(sub, r["quantity"], reader=r["reader"], frame=r["frame"],
                              reason=r["reason"], **detail)
        id_map[r["id"]] = new.id
    return log, id_map, stats


# ─── the capture ─────────────────────────────────────────────────────────────

CUR = {"subject": None}
CALLS = collections.defaultdict(list)


def rid(x):
    return getattr(x, "id", x)


def install():
    def wrap(name, in_arg, kind):
        orig = getattr(RH, name)

        def w(*a, **k):
            res = orig(*a, **k)
            subj = CUR["subject"]
            if subj is not None:
                CALLS[subj].append({"fn": name, "kind": kind,
                                    "in": [rid(x) for x in (a[in_arg] if in_arg is not None else ())],
                                    "res": res})
            return res
        setattr(RH, name, w)

    wrap("_not_a_ledger_line", 0, "drop")
    wrap("_not_a_slash", 2, "drop")
    wrap("_not_the_neighbours_beam", 2, "drop")
    wrap("_not_a_decided_arc", 2, "drop")
    wrap("_on_stem_side", 0, "side")
    wrap("_beyond_own_stem", 0, "beyond")
    wrap("_not_a_beam_by_ink", 2, "ink")

    ko = RH._kept_beams

    def kept_w(ev, cell):
        res = ko(ev, cell)
        subj = CUR["subject"]
        if subj is not None:
            CALLS[subj].append({"fn": "_kept_beams", "kind": "start", "in": [],
                                "res": res})
        return res
    RH._kept_beams = kept_w

    spec = adjudicate.REGISTRY[Q.DURATION]
    fn = spec.fn

    def fn_w(ev):
        CUR["subject"] = ev.subject.to_key()
        CALLS[CUR["subject"]] = []
        try:
            return fn(ev)
        finally:
            CUR["subject"] = None
    import dataclasses
    adjudicate.REGISTRY[Q.DURATION] = dataclasses.replace(spec, fn=fn_w)


def strokes_story(calls, detail):
    """Per stroke id: its reader, whether it was a candidate, and the FIRST filter that removed it for good."""
    story = {}
    start = next((c for c in calls if c["kind"] == "start"), None)
    if start is None:
        return story
    kept, cv, yolo = start["res"]
    for r in cv:
        story[r.id] = {"reader": "cv", "candidate": True, "refused_by": None, "why": None}
    for r in yolo:
        story[r.id] = {"reader": "detector", "candidate": r in kept, "refused_by": None,
                       "why": None if r in kept else "covered_by_a_cv_stroke"}
    undone_beyond = bool(detail.get("beyond_stem_kept_no_other_mark"))
    ink_calls = [c for c in calls if c["kind"] == "ink"]
    last_ink = ink_calls[-1] if ink_calls else None
    for c in calls:
        if c["kind"] == "drop":
            for r in c["res"][1]:
                s = story.get(rid(r))
                if s is not None and s["refused_by"] is None:
                    s["refused_by"] = c["fn"]
                    s["why"] = {"_not_a_ledger_line": "ledger_line", "_not_a_slash": "tremolo_slash",
                                "_not_the_neighbours_beam": "neighbour_staff_beam",
                                "_not_a_decided_arc": "decided_arc_ink"}[c["fn"]]
        elif c["kind"] == "side":
            for r in c["res"][1]:
                s = story.get(rid(r))
                if s is not None and s["refused_by"] is None and c is not None:
                    s["refused_by"] = c["fn"]
                    s["why"] = "far_side_of_the_head"
        elif c["kind"] == "beyond" and not undone_beyond:
            for r in c["res"][1]:
                s = story.get(rid(r))
                if s is not None and s["refused_by"] is None:
                    s["refused_by"] = c["fn"]
                    s["why"] = "past_the_stem_tip"
    if last_ink is not None:
        for sid, why in (last_ink["res"][1] or {}).items():
            s = story.get(sid)
            if s is not None and s["refused_by"] is None:
                s["refused_by"] = "_not_a_beam_by_ink"
                s["why"] = why
    # kept at the end: a candidate nobody refused
    for sid, s in story.items():
        if s["candidate"] and s["refused_by"] is None:
            s["why"] = "kept"
    return story


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--keys", required=True, help="comma list of head keys to report")
    ap.add_argument("--out", required=True)
    ap.add_argument("--break-control", action="store_true")
    a = ap.parse_args()
    keys = [k for k in a.keys.split(",") if k]
    data = json.loads(Path(a.rows).read_text())
    # one page only: the page's rows plus the document-level rows
    def pg(s):
        p = s.split("/")
        return int(p[1]) if len(p) >= 2 and p[0] != "document" else None
    data = {"observations": [o for o in data["observations"] if pg(o["subject"]) in (None, a.page)],
            "abstentions": [o for o in data["abstentions"] if pg(o["subject"]) in (None, a.page)],
            "saved_duration": {k: v for k, v in data["saved_duration"].items() if pg(k) == a.page}}
    t0 = time.time()
    log, id_map, stats = rebuild(data, perturb=a.break_control)
    print(f"rebuilt {len(id_map)} rows, {stats['unmapped']} id-like detail values with no mapped row "
          f"({time.time() - t0:.0f}s)", flush=True)
    adjudicate._ensure_decisions()
    install()
    adjudicate.run(log)
    print(f"re-adjudicated ({time.time() - t0:.0f}s)", flush=True)
    # the control: every saved ADJUDICATE duration verdict on the page against the rebuilt one
    diff, same, missing = [], 0, 0
    for key, w in data["saved_duration"].items():
        v = log.verdict(Q.DURATION, Subject.from_key(key))
        if v is None:
            missing += 1
            continue
        got_c = sorted(round(((c.value or {}).get("beats") or 0), 4) for c in (v.candidates or ()))
        want_c = sorted(round(((c or {}).get("beats") or 0), 4) for c in w["cands"])
        got_val = round(((v.value or {}).get("beats") or 0), 4) if v.value else None
        want_val = round(((w["value"] or {}).get("beats") or 0), 4) if w["value"] else None
        if (v.outcome.value if hasattr(v.outcome, "value") else str(v.outcome)) == w["outcome"] \
                and v.reason == w["reason"] and got_c == want_c and got_val == want_val:
            same += 1
        else:
            diff.append(key)
    print(f"CONTROL page {a.page}: {same} of {len(data['saved_duration'])} duration verdicts reproduced "
          f"exactly, {len(diff)} differ, {missing} absent from the rebuild", flush=True)
    asked_diff = [k for k in keys if k in diff]
    out = {"page": a.page, "control": {"same": same, "n": len(data["saved_duration"]), "differ": diff[:50],
                                       "asked_that_differ": asked_diff},
           "heads": {}}
    for k in keys:
        calls = CALLS.get(k) or []
        v = log.verdict(Q.DURATION, Subject.from_key(k))
        detail = dict(v.detail) if v is not None else {}
        story = strokes_story(calls, detail)
        # enrich each stroke with its box and ink row (in the REBUILT log: ids are the new ones; map back)
        inv = {new: old for old, new in id_map.items()}
        strokes = {}
        for sid, s in story.items():
            strokes[inv.get(sid, sid)] = dict(s)
        others = {}
        for q in (Q.HEAD_STEM, Q.STEM_DIRECTION, Q.STEM_VALUE, Q.NOTEHEAD_IS_A_WHOLE_REST,
                  Q.NOTEHEAD_IS_NOT_A_NOTEHEAD):
            ov = log.verdict(q, Subject.from_key(k))
            if ov is None:
                continue

            def back(x):
                return inv.get(x, x) if isinstance(x, str) else x
            others[q] = {"outcome": str(getattr(ov.outcome, "value", ov.outcome)), "reason": ov.reason,
                         "value": back(ov.value) if not isinstance(ov.value, dict) else
                         {kk: back(vv) for kk, vv in ov.value.items()},
                         "candidates": [back(getattr(c, "value", c)) for c in (ov.candidates or ())]}
        out["heads"][k] = {"verdict": {"outcome": str(getattr(v.outcome, "value", v.outcome)) if v else None,
                                       "reason": v.reason if v else None,
                                       "candidates": [dict(getattr(c, "value", {}) or {}) for c in
                                                      ((v.candidates or ()) if v else ())]},
                           "others": others,
                           "detail": {x: detail.get(x) for x in (
                               "beam_side", "stems_attached", "beams_not_by_ink", "beams_not_by_ink_why",
                               "beams_neighbour_staff", "beams_decided_arc", "beams_far_side",
                               "beams_beyond_stem", "beyond_stem_kept_no_other_mark", "beams_ledger_line",
                               "beams_slash", "levels_certain", "levels_possible", "head_is_open",
                               "yolo_beams", "cv_beams", "dots_attached", "flags_attached")},
                           "strokes": strokes,
                           "calls": [c["fn"] for c in calls]}
    Path(a.out).write_text(json.dumps(out, separators=(",", ":"), default=str))
    print(f"wrote {a.out}")
    if a.break_control:
        print("BREAK-CONTROL: differ =", len(diff))
        sys.exit(0 if diff else 2)
    if asked_diff:
        print("CONTROL FAILED for asked heads:", asked_diff)
        sys.exit(1)


if __name__ == "__main__":
    main()
