"""ROADMAP 2.292 -- why a key / clef is INFERRED when it is printed.  MEASURE ONLY.

    python3 benchmarks/why-key-clef-inferred-2026-11/analyze.py PLATE PAGES TAG OUT.json

PATH: STAGED. Replays the saved gather slice (`conservation.load_pages`) through ADJUDICATE..EXPORT on main's defaults, exactly as
`conservation.export_pages` does, with ONE addition: `export._guess_fields` is wrapped (read-only; same return value) so that for
every written head/rest the script sees EVERY reason it could be blue, not only the first one `_guess_fields` returns.
Output JSON: per written symbol {sub, page, system, staff, is_rest, blue, reasons[]}, and per (page, system, staff) the standing
KEY_SIGNATURE / CLEF verdicts with their supersession chains (prior abstention reason, what the staff itself read), slot, instrument,
margin label.  Nothing is decided here.
"""
from __future__ import annotations
import json, sys, collections

from tools.omr.staged import conservation as C
from tools.omr.staged import export as E
from tools.omr.staged.record import Q
from tools.omr.staged.review import rerun as RR

CAP = {}      # sub -> {"reasons": [...], "first": rule}


def reasons_of(rec, sub):
    """Every independent reason the symbol is blue.  Pitch reasons are read from the PITCH / ACCIDENTAL basis chain."""
    R = []
    dur = rec.verdict(Q.DURATION, sub)
    if dur is not None and dur["outcome"] == "decided":
        g = E._guess_in_chain(rec, dur)
        if g is not None:
            R.append("value:" + g["rule"])
    h = E.head_ink_guess_of(rec, sub)
    if h:
        R.append("value:" + h["rule"])
    for q in (Q.PITCH, Q.ACCIDENTAL):
        v = rec.verdict(q, sub)
        if v is None or v["outcome"] != "decided":
            continue
        for bid in v.get("basis") or ():
            b = rec.verdict_by_id(bid)
            if b is not None and b["outcome"] == "decided" and (b.get("decider") or "").startswith("infer:"):
                rule = b["decider"][len("infer:"):]
                tag = {"fill_part_key": "key_fill", "fill_clef_gap": "clef_fill"}.get(rule, "pitch_infer:" + rule)
                R.append("%s[%s]" % (tag, q))
    c = E.claim_guess_of(rec, sub)
    if c:
        R.append("claim:" + str(c["rule"]))
    o = E.one_ink_guess_of(rec, sub)
    if o:
        R.append("accidental_or_oneink:" + str(o["rule"]))
    f = E.far_unread_guess_of(rec, sub)
    if f:
        R.append("far:" + str(f["rule"]))
    return R


def main(plate, pages, tag, out_path):
    pages = [int(x) for x in pages.split(",")]
    rec_in = C.load_pages(plate, pages, tag)
    log, _ = RR.rebuild_gather(rec_in)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    rec = E.Record(result)
    orig = E._guess_fields

    def wrapped(r, sub):
        CAP.setdefault(sub, {"reasons": reasons_of(r, sub),
                             "first": (orig(r, sub).get("guess") or {}).get("rule")})
        return orig(r, sub)
    FINAL = {}      # sub -> (final guess rule, is_rest) as WRITTEN (after partial-bar / voice / claimed-gap marks)
    orig_cg = E._count_guess

    def cg(counters, guess, is_rest):
        f = sys._getframe(1).f_locals
        h = f.get("head") if not is_rest else f.get("det")
        sub = (h or {}).get("glyph")
        if sub is not None:
            prev = FINAL.get(sub)
            FINAL[sub] = ((guess or {}).get("rule") or (prev[0] if prev else None), is_rest)
        return orig_cg(counters, guess, is_rest)
    E._guess_fields = wrapped
    E._count_guess = cg
    try:
        xml, report = E.to_musicxml(result)
    finally:
        E._guess_fields = orig
        E._count_guess = orig_cg

    def parts(sub):
        p = sub.split("/")
        return p

    symbols = []
    for sub, d in CAP.items():
        gb = rec.obs(Q.GLYPH_BOX, sub)
        cls = gb[0]["value"][0] if gb else None
        p = sub.split("/")
        # glyph subject: kind/page/system/staff/cell/glyph (see record.Subject.to_key)
        prow = rec.obs(Q.NOTEHEAD_STAFF_POSITION, sub)
        far = rec.verdict(Q.NOTEHEAD_POSITION, sub)
        pv = rec.verdict(Q.PITCH, sub)
        symbols.append({"pos": (prow[0]["value"] if prow else None),
                        "far_pos": (far["value"] if far is not None and far["outcome"] == "decided" else None),
                        "pitch": (pv["value"] if pv is not None and pv["outcome"] == "decided" else None),
                        "sub": sub, "cls": cls, "box": (gb[0]["value"][1:5] if gb else None), "page_box": ((gb[0].get("detail") or {}).get("bbox_page_px") if gb else None), "is_rest": bool(cls and str(cls).lower().startswith("rest")),
                        "blue": bool(FINAL.get(sub, (None,))[0]), "first": FINAL.get(sub, (None,))[0], "pre": d["first"], "reasons": d["reasons"]})
    # staff-level standing verdicts
    staffs = {}
    seen = set()
    for v in rec.verdicts:
        if v["quantity"] in (Q.KEY_SIGNATURE, Q.CLEF, Q.SLOT_INDEX, Q.INSTRUMENT) and v["subject"].startswith("staff/"):
            seen.add(v["subject"])
    def chain(q, s):
        v = rec.verdict(q, s)
        out = []
        guard = set()
        while v is not None and v["id"] not in guard:
            guard.add(v["id"])
            out.append({"id": v["id"], "outcome": v["outcome"], "decider": v.get("decider"), "reason": v.get("reason"),
                        "value": v.get("value") if not isinstance(v.get("value"), (dict, list)) else str(v.get("value"))[:200],
                        "detail": json.loads(json.dumps(v.get("detail"), default=str))[:0] if False else _slim(v.get("detail")),
                        "candidates": [(c.get("value"), c.get("support")) for c in (v.get("candidates") or ())][:5]})
            v = rec.verdict_by_id(v["supersedes"]) if v.get("supersedes") else None
        return out
    for s in sorted(seen):
        ml = rec.obs(Q.MARGIN_LABEL, s)
        staffs[s] = {"key": chain(Q.KEY_SIGNATURE, s), "clef": chain(Q.CLEF, s), "slot": chain(Q.SLOT_INDEX, s)[:1],
                     "instrument": chain(Q.INSTRUMENT, s)[:1],
                     "margin": [m["value"] for m in ml][-1:] }
    # evidence behind each staff's header (observations only; GATHER rows)
    by_staff = collections.defaultdict(lambda: collections.defaultdict(list))
    wanted = (Q.KEYSIG_MARKER, Q.CLEF_GLYPH, Q.CLEF_LOCATED, Q.CLAIMED_AREA, Q.KEYSIG_CLEF_FIT, Q.KEYSIG_TEMPLATE_FIT,
              Q.CLEF_POSITION, Q.CLEF_SEED, Q.STAFF_LINES, Q.STAFF_EXTENT, Q.CELL_BOX, Q.STAFF_SPACING)
    for o in rec.observations:
        if o["quantity"] == Q.CLAIMED_AREA and o.get("reader") == "cv_claimed_register":
            continue                      # the barline register: 14 rows a staff, not header evidence
        if o["quantity"] in wanted:
            sj = o["subject"].split("/")
            if len(sj) >= 4:
                key = "staff/" + "/".join(sj[1:4])
                by_staff[key][o["quantity"]].append({
                    "subject": o["subject"], "value": _slim(o.get("value"), 400), "reader": o.get("reader"),
                    "detail": _slim(o.get("detail"), 3000) if o["quantity"] == Q.CLAIMED_AREA else None})
    for s_, st in staffs.items():
        st["evidence"] = {q: rows[:14] for q, rows in by_staff.get(s_, {}).items()}
    part_key = [v for v in rec.verdicts if v["quantity"] == Q.PART_KEY]
    json.dump({"plate": plate, "pages": pages, "tag": tag, "symbols": symbols, "staffs": staffs,
               "part_key": [{"subject": v["subject"], "outcome": v["outcome"], "value": _slim(v.get("value"), 4000)} for v in part_key],
               "report_guessed": report.get("guessed"), "conservation": report.get("conservation")},
              open(out_path, "w"), default=str)
    n = len(symbols)
    print(plate, pages, "symbols", n, "blue", sum(1 for s in symbols if s["blue"]))


def _slim(d, n=1500):
    if d is None:
        return None
    s = json.dumps(d, default=str)
    return json.loads(s) if len(s) <= n else s[:n]


if __name__ == "__main__":
    main(*sys.argv[1:5])
