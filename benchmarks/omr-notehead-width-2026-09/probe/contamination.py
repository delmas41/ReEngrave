"""HOW MUCH OF ISSUES 1 AND 2 IS A BOX THAT IS NOT A NOTEHEAD?

Sean picked this job and gave the reason: *"I feel like the previous issues
(1 and 2) will be affected by this."* This is that question, and it is asked
where it can be ANSWERED rather than inferred -- against the crop pass's own
blind print verdicts, joined on the subject address.

Two things this can do that the width table alone cannot:

  1. VALIDATE the floor against the print. The crop pass adjudicated 180
     sampled boxes plus the 26-head standoff and the 31 whole-note
     contradictions, blind, with opaque tile ids. Every one of those verdicts
     carries a subject, so the floor's confusion matrix against the PRINT is a
     join and not a new measurement. ⚠️ This is the only place in this job
     where "is it a notehead" has a truth value.
  2. SAY WHETHER THE 16-0 SURVIVES. The standoff's 16-0 was over the 16 heads
     the print SETTLED. If the narrow boxes are among the two the print
     already called `not a notehead`, the contamination is already priced and
     the 16-0 stands; if a narrow box is among the settled 16, it does not.

⚠️ EVERY CLAIM HERE INHERITS n = 180 + 26 + 31 BOXES, ONE ADJUDICATOR, TWO
PUBLISHERS. The width is measured on 5,684 boxes; the truth is not.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
CROPDIR = BENCH.parent / "omr-stem-crop-pass-2026-09"
FLOOR = 1.0


def q(vals, p):
    s = sorted(vals)
    return s[min(len(s) - 1, int(p * len(s)))] if s else float("nan")

# The verdict vocabulary the crop pass used, and the three-way split this job
# needs out of it.
#
# ⚠️⚠️ THE FIRST VERSION OF THIS PROBE COLLAPSED `cannot_tell` INTO
# "IS a notehead" AND REPORTED 5 FALSE ALARMS. Every one of the five is a
# `cannot_tell` -- the print could not settle it -- so that collapse turned
# *we do not know* into *the floor is wrong*, which is the ABSENT/DECLINED
# collapse `record.py` exists to prevent, committed inside the instrument
# built to price a filter. The matrix is THREE-WAY and stays three-way.
NOT_A_HEAD = "not_a_notehead"
CONFIRMED_HEAD = ("stem_printed_up", "stem_printed_down", "no_stem_printed")

# ⚠️⚠️ AND THE SECOND VERSION HAD A WORSE BUG THAN THE FIRST: the whole-note
# file uses a DIFFERENT vocabulary -- `print_shows` / `which_claim_is_false`,
# not `verdict` -- so all 17 of its rows, every one of which the print
# SETTLED, fell through `r.get("verdict")` as None and were filed
# `cannot tell`. A join that silently reads 17 settled verdicts as
# "unadjudicated" is this repo's own *a filter that empties a file looks
# exactly like an empty file*, and nothing about the output invited suspicion.
# Found by printing the joined rows rather than the totals.
PRINT_SHOWS_NOT_A_HEAD = {
    "time_signature_digit_8", "staff_line_gap", "hairpin_or_beam_wedge",
}
PRINT_SHOWS_IS_A_HEAD = {"dotted_half_note", "possibly_a_real_whole_note"}


def truth_of(r) -> str:
    v = r.get("verdict")
    if v is not None:
        if v == NOT_A_HEAD:
            return "NOT a notehead"
        if v in CONFIRMED_HEAD:
            return "IS a notehead"
        return "cannot tell"
    ps = r.get("print_shows")
    if ps in PRINT_SHOWS_NOT_A_HEAD:
        return "NOT a notehead"
    if ps in PRINT_SHOWS_IS_A_HEAD:
        return "IS a notehead"
    # ⚠️ An unknown vocabulary word is REPORTED, never defaulted to either
    # side -- the whole reason the bug above was possible.
    return "UNKNOWN VERDICT WORD: " + repr(ps)


def load_widths():
    w = {}
    for pub in ("litolff", "breitkopf"):
        d = json.loads((BENCH / "out" / f"{pub}-widths.json").read_text())
        for r in d["rows"]:
            w[(pub, r["subject"])] = r
    return w


# ⚠️ THE ADJUDICATION FILES CARRY NO SUBJECT, BY DESIGN -- the protocol was
# BLIND, so a verdict names only an opaque tile id (`L001`, `S014`, `V010`).
# The tile -> subject map lives in the CROP MANIFESTS, which is also where the
# publisher is DECLARED in the label. So the publisher is read off the
# manifest rather than inferred from the subject's page number -- pdf pages
# 1-3 exist in BOTH records and a page-number rule silently drops every
# overlapping address (it dropped 4 of the standoff's 26 on the first run,
# turning the published 16-0 into 12-0 and looking exactly like a real result).
MANIFESTS = {
    "ADJUDICATION-litolff.json": [("crop-manifest-litolff.json", "litolff")],
    "ADJUDICATION-breitkopf.json": [
        ("crop-manifest-breitkopf.json", "breitkopf")],
    "ADJUDICATION-standoff.json": [
        ("crop-manifest-standoff.json", "breitkopf")],
    "ADJUDICATION-wholenotes.json": [
        ("crop-manifest-wholenotes-B.json", "breitkopf"),
        ("crop-manifest-wholenotes-L.json", "litolff")],
}


def adjudications():
    """Every blind print verdict the crop pass committed, with its publisher.

    Returns `(source_file, publisher, verdict_row, subject)`. A tile id in no
    manifest is REPORTED, never guessed at.
    """
    out = []
    for name, mans in MANIFESTS.items():
        p = CROPDIR / name
        if not p.exists():
            continue
        tile2 = {}
        for mname, pub in mans:
            mp = CROPDIR / "out" / mname
            if not mp.exists():
                continue
            m = json.loads(mp.read_text())
            for t in m["tiles"]:
                tile2[t["id"]] = (pub, t["subject"])
        d = json.loads(p.read_text())
        rows = d["rows"] if isinstance(d, dict) else d
        for r in rows:
            pub, subj = tile2.get(r.get("id"), (None, r.get("subject")))
            out.append((name, pub, r, subj))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    W = load_widths()
    held = collections.defaultdict(set)
    for (pub, s) in W:
        held[s].add(pub)

    adj = adjudications()
    if not adj:
        print("DEAD: no adjudication file found")
        return 2
    print(f"adjudicated rows found: {len(adj)}")

    # ---- resolve each verdict to (pub, subject, width) ----
    resolved, unresolved = [], []
    for src, pub, r, s in adj:
        if not s:
            unresolved.append((src, r.get("id"), "tile id in no manifest"))
            continue
        if pub is None:
            unresolved.append((src, r.get("id"), "no publisher declared"))
            continue
        if pub not in held.get(s, set()):
            unresolved.append((src, r.get("id"),
                               f"{s} not in the {pub} record"))
            continue
        resolved.append((src, pub, r, W[(pub, s)]))

    print(f"resolved to a width: {len(resolved)}   unresolved: "
          f"{len(unresolved)}")
    for u in unresolved[:10]:
        print("   unresolved:", u)
    if not resolved:
        print("DEAD: nothing joined")
        return 2

    out = {"floor": FLOOR, "adjudicated_rows": len(adj),
           "resolved": len(resolved), "unresolved": len(unresolved),
           "unresolved_detail": [list(map(str, u)) for u in unresolved]}

    # ---- 1. THE FLOOR AGAINST THE PRINT, per publisher, THREE-WAY ----
    conf = {}
    for pub in ("litolff", "breitkopf"):
        rr = [(r, w) for src, p, r, w in resolved if p == pub]
        m = collections.Counter()
        for r, w in rr:
            m[(truth_of(r), "flag" if w["w_page"] < FLOOR else "keep")] += 1
        c = {"n": len(rr)}
        for t in ("NOT a notehead", "IS a notehead", "cannot tell"):
            c[t] = {"flagged": m[(t, "flag")], "kept": m[(t, "keep")]}
        # ⚠️ a vocabulary word this probe does not know must be LOUD.
        unknown = {k[0]: v for k, v in m.items()
                   if k[0].startswith("UNKNOWN")}
        c["unknown_verdict_words"] = unknown
        # the only cost that is a COST: a box the print CONFIRMS is a head.
        c["cost_on_confirmed_heads"] = m[("IS a notehead", "flag")]
        c["caught_of_not_a_notehead"] = m[("NOT a notehead", "flag")]
        c["missed_of_not_a_notehead"] = m[("NOT a notehead", "keep")]
        c["flagged_cannot_tell"] = m[("cannot tell", "flag")]
        c["subjects_flagged_but_confirmed"] = sorted(
            w["subject"] for r, w in rr
            if truth_of(r) == "IS a notehead" and w["w_page"] < FLOOR)
        c["missed_detail"] = [
            {"subject": w["subject"], "w": round(w["w_page"], 3),
             "h": round(w["h_page"], 3), "cls": w["cls"],
             "what": (r.get("reason") or "")[:140]}
            for r, w in rr
            if truth_of(r) == "NOT a notehead" and w["w_page"] >= FLOOR]
        conf[pub] = c
    out["floor_vs_print"] = conf

    # ---- 1b. THE SHAPE PICTURE. The misses are not narrow, they are WIDE --
    # printed letters, a bass clef, and whole rests that are wide and SHORT.
    # So the width floor's residue is a HEIGHT question, and `[C1 + L3]`'s
    # RIGID half is the height. Reported as a distribution; no threshold is
    # fitted here and none is proposed from it.
    shape = {}
    for pub in ("litolff", "breitkopf"):
        rr = [(r, w) for src, p, r, w in resolved if p == pub]
        d = collections.defaultdict(list)
        for r, w in rr:
            d[truth_of(r)].append(w)
        shape[pub] = {}
        for t, v in d.items():
            shape[pub][t] = {
                "n": len(v),
                "w": {k: round(x, 3) for k, x in
                      (("p5", q([z["w_page"] for z in v], .05)),
                       ("median", q([z["w_page"] for z in v], .50)),
                       ("p95", q([z["w_page"] for z in v], .95)))},
                "h": {k: round(x, 3) for k, x in
                      (("p5", q([z["h_page"] for z in v], .05)),
                       ("median", q([z["h_page"] for z in v], .50)),
                       ("p95", q([z["h_page"] for z in v], .95)))},
            }
    out["shape_vs_print"] = shape

    # ---- 2. DOES THE 16-0 SURVIVE? ----
    st = [(r, w) for src, p, r, w in resolved
          if src == "ADJUDICATION-standoff.json"]
    rows = []
    for r, w in st:
        rows.append({"subject": w["subject"], "id": r.get("id"),
                     "verdict": r.get("verdict"),
                     "arbitration": r.get("arbitration"),
                     "w_page": round(w["w_page"], 3),
                     "under_floor": w["w_page"] < FLOOR})
    settled = [x for x in rows
               if x["verdict"] in ("stem_printed_up", "stem_printed_down")]
    out["issue1_standoff"] = {
        "n": len(rows),
        "verdicts": dict(collections.Counter(x["verdict"] for x in rows)),
        "under_floor": sum(1 for x in rows if x["under_floor"]),
        "settled_n": len(settled),
        "settled_under_floor": sum(1 for x in settled if x["under_floor"]),
        "attachment_wins_among_settled": sum(
            1 for x in settled
            if x["arbitration"] and "ATTACHMENT" in x["arbitration"]),
        "beam_mate_wins_among_settled": sum(
            1 for x in settled
            if x["arbitration"] and "BEAM" in x["arbitration"].upper()),
        "rows": rows,
    }

    # ---- 3. the whole-note contradictions, by width ----
    wn = [(r, w) for src, p, r, w in resolved
          if src == "ADJUDICATION-wholenotes.json"]
    out["wholenotes"] = {
        "n": len(wn),
        "verdicts": dict(collections.Counter(r.get("verdict") for r, _ in wn)),
        "rows": sorted(({"subject": w["subject"], "id": r.get("id"),
                         "verdict": r.get("verdict"),
                         "what": (r.get("reason") or r.get("what") or "")[:90],
                         "cls": w["cls"],
                         "w_page": round(w["w_page"], 3)}
                        for r, w in wn), key=lambda x: x["w_page"]),
    }

    Path(a.json).write_text(json.dumps(out, indent=1))

    print("\n-- the floor against the PRINT (THREE-WAY: `cannot tell` is not "
          "a cost and is not a win)")
    print(f"   {'':<11} {'n':>4} | {'NOT a head':>16} | "
          f"{'IS a head':>16} | {'cannot tell':>16}")
    print(f"   {'':<11} {'':>4} | {'flag':>7} {'keep':>8} | "
          f"{'flag':>7} {'keep':>8} | {'flag':>7} {'keep':>8}")
    for pub, c in conf.items():
        n = c["NOT a notehead"]
        i = c["IS a notehead"]
        u = c["cannot tell"]
        print(f"   {pub:<11} {c['n']:>4} | {n['flagged']:>7} {n['kept']:>8} | "
              f"{i['flagged']:>7} {i['kept']:>8} | "
              f"{u['flagged']:>7} {u['kept']:>8}")
    print("\n-- shape, in staff spaces (w median / h median)")
    for pub, s in shape.items():
        for t, v in sorted(s.items()):
            print(f"   {pub:<11} {t:<16} n={v['n']:>4}  "
                  f"w {v['w']['p5']:.2f}/{v['w']['median']:.2f}/"
                  f"{v['w']['p95']:.2f}   "
                  f"h {v['h']['p5']:.2f}/{v['h']['median']:.2f}/"
                  f"{v['h']['p95']:.2f}")
    i1 = out["issue1_standoff"]
    print(f"\n-- issue 1, the 26-head standoff")
    print(f"   verdicts: {i1['verdicts']}")
    print(f"   under the floor: {i1['under_floor']} of {i1['n']}")
    print(f"   of the {i1['settled_n']} the print SETTLED, under the floor: "
          f"{i1['settled_under_floor']}")
    print(f"   attachment {i1['attachment_wins_among_settled']} - "
          f"{i1['beam_mate_wins_among_settled']} beam-mate (among settled)")
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
