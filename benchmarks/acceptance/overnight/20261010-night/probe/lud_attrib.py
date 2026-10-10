#!/usr/bin/env python3
"""lud_attrib: attribute the note kept->narrowed / narrowed->kept transitions.

Two layers.

  1. From the saved first-two-stages diff ALONE (`why[0]` = last night's
     ADJUDICATE answer in words, `why[1]` = tonight's): tonight's narrowing
     REASON word and last night's value -> tonight's candidates; for
     narrowed->kept, last night's reason and candidates -> tonight's value.
  2. With lud_extract.py's JSON for BOTH nights (each record read once):
     the duration verdict of each changed note carries the counters the
     decision branched on (`beams_not_by_ink` + `_why`, `beams_neighbour_staff`,
     `beams_decided_arc`, `beams_far_side`, `beam_side`, `stems_attached`,
     `cv_beams`, `yolo_beams`, `levels_certain/possible`). The PAIR of
     counters (last night -> tonight) on the same note says which input
     changed, which is a read of the two records, not of the commit log.

Mapping a guard to the commit that introduced it is `git log -S` and is written
in UNDECIDED.md. Nothing here counts a commit.
"""
import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lud_bars  # noqa: E402  (numbering + parse)

COMPARE = lud_bars.COMPARE
OPEN = re.compile(r"^length still open: (.*?) -- (.+)$")
BEATS = re.compile(r"\(([\d.]+) beats?\)")


def parse_open(s):
    m = OPEN.match(s)
    if not m:
        return None, None
    cands = [BEATS.search(c).group(1) if BEATS.search(c) else c for c in m.group(1).split(" | ")]
    return cands, m.group(2)


def value_beats(s):
    m = BEATS.search(s)
    return m.group(1) if m else s


def n(x):
    return int(x or 0)


def counters(v):
    d = (v or {}).get("detail") or {}
    return {
        "ink": n(d.get("beams_not_by_ink")), "nb": n(d.get("beams_neighbour_staff")),
        "arc": n(d.get("beams_decided_arc")), "far": n(d.get("beams_far_side")),
        "side": d.get("beam_side"), "stems": n(d.get("stems_attached")),
        "cv": n(d.get("cv_beams")), "yolo": n(d.get("yolo_beams")),
        "lc": d.get("levels_certain"), "lp": d.get("levels_possible"),
        "flags": n(d.get("flags_attached")), "flag_levels": n(d.get("flag_levels")),
        "ink_why": sorted((d.get("beams_not_by_ink_why") or {}).keys()),
        "reach": bool((v or {}).get("basis_has_head_stem_reach")),
        "ev": d.get("beam_evidence"), "hollow": bool(d.get("head_is_open")),
        "bybeam": n(d.get("beams_by_stem")),
    }


def signature(a, b):
    """What differs between the two nights' counters on the guard inputs."""
    s = []
    if b["ink"] > a["ink"]:
        s.append("ink refused " + "/".join(b["ink_why"]) + f" ({a['ink']}->{b['ink']})")
    elif b["ink"] < a["ink"]:
        s.append(f"ink refusals fewer ({a['ink']}->{b['ink']})")
    if b["arc"] != a["arc"]:
        s.append(f"decided-arc strokes {a['arc']}->{b['arc']}")
    if b["nb"] != a["nb"]:
        s.append(f"neighbour-staff strokes {a['nb']}->{b['nb']}")
    if b["far"] != a["far"]:
        s.append(f"far-side strokes {a['far']}->{b['far']}")
    if a["side"] != b["side"]:
        s.append(f"stem side {a['side']}->{b['side']}")
    if not s:
        s.append("no guard counter changed")
    return " + ".join(s)


def gather_side(a, b):
    s = []
    for k, nm in (("cv", "cv_beams"), ("yolo", "yolo_beams"), ("stems", "stems_attached"),
                  ("flags", "flags_attached"), ("bybeam", "beams_by_stem")):
        if a[k] != b[k]:
            s.append(f"{nm} {a[k]}->{b[k]}")
    return ", ".join(s) or "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--extract-b", help="lud_extract.py JSON of TONIGHT")
    ap.add_argument("--extract-a", help="lud_extract.py --dur-only JSON of LAST NIGHT")
    ap.add_argument("--out")
    ap.add_argument("--csv")
    ap.add_argument("--systems", help="page/system,... for a per-system table")
    a = ap.parse_args()
    d = json.load(open(COMPARE / f"{a.doc}-first-two-stages.json"))
    exb = json.load(open(a.extract_b))["dur"] if a.extract_b else None
    exa = json.load(open(a.extract_a))["dur"] if a.extract_a else None
    off, _nb, _chk, _h = lud_bars.numbering(a.doc)
    out = []
    P = out.append

    k2n = [p for p in d["changed_pairs"] if p["family"] == "note" and p["status"] == ["kept", "narrowed"]]
    n2k = [p for p in d["changed_pairs"] if p["family"] == "note" and p["status"] == ["narrowed", "kept"]]
    P(f"=== {a.doc}: kept -> narrowed notes: {len(k2n)};  narrowed -> kept: {len(n2k)}")

    # --- layer 1
    P("\n-- tonight's narrowing REASON (kept -> narrowed)")
    byr = collections.Counter()
    pair = collections.defaultdict(collections.Counter)
    for p in k2n:
        cands, reason = parse_open(p["why"][1][0])
        byr[reason] += 1
        pair[reason][(value_beats(p["why"][0][0]), " | ".join(cands))] += 1
    for r, c in byr.most_common():
        P(f"   {c:5d}  {r}")
    inside = collections.Counter()
    for p in k2n:
        cands, reason = parse_open(p["why"][1][0])
        last = float(value_beats(p["why"][0][0]))
        inside["last night's answer is still one of tonight's candidates" if any(abs(float(c) - last) < 1e-9 for c in cands)
               else "last night's answer is ruled out by tonight's candidates"] += 1
    P("\n-- is last night's value among tonight's candidates?")
    for k, c in inside.most_common():
        P(f"   {c:5d}  {k}")
    P("\n-- last night's decided value (beats) -> tonight's candidates (beats), by reason")
    for r, c in byr.most_common():
        P(f"   [{r}] {c}")
        for (last, cs), k in pair[r].most_common(12):
            P(f"      {k:5d}  {last:>8} -> {cs}")

    P("\n-- narrowed -> kept: last night's REASON, then last night's candidates -> tonight's value")
    byr2 = collections.Counter()
    pair2 = collections.defaultdict(collections.Counter)
    for p in n2k:
        cands, reason = parse_open(p["why"][0][0])
        byr2[reason] += 1
        pair2[reason][(" | ".join(cands or ["?"]), value_beats(p["why"][1][0]) if p["why"][1] else "?")] += 1
    for r, c in byr2.most_common():
        P(f"   {c:5d}  {r}")
    for r, c in byr2.most_common():
        P(f"   [{r}] {c}")
        for (cs, now), k in pair2[r].most_common(10):
            P(f"      {k:5d}  {cs} -> {now}")

    # --- layer 2 (paired)
    rows = []
    if exb and exa:
        P("\n=== layer 2: the same note's duration-verdict counters, last night -> tonight")
        P("    (a counter absent in last night's verdict is 0: the guard did not exist)")
        sig_k2n = collections.Counter()
        sig_reason = collections.defaultdict(collections.Counter)
        gat = collections.Counter()
        missing = 0
        for p in k2n:
            va, vb = exa.get(p["a"]), exb.get(p["b"])
            if not va or not vb or va.get("none") or vb.get("none"):
                missing += 1
                continue
            ca, cb = counters(va), counters(vb)
            sg = signature(ca, cb)
            sig_k2n[sg] += 1
            sig_reason[sg][vb["reason"]] += 1
            gat[gather_side(ca, cb)] += 1
            page, sysi, staff, cell, _g = lud_bars.parse(p["b"])
            cands, reason = parse_open(p["why"][1][0])
            rows.append({
                "kind": "kept_to_narrowed", "subject": p["b"], "page": page, "system": sysi,
                "staff": staff, "cell": cell, "export_bar": off.get((page, sysi), -1) + cell + 1,
                "last_night_value_beats": value_beats(p["why"][0][0]),
                "tonight_candidates_beats": " | ".join(cands), "tonight_reason": reason,
                "what_changed": sg, "gather_side_changes": gather_side(ca, cb),
                "ink_refusal_why": "/".join(cb["ink_why"]),
                "last_night_beam_levels": (va.get("value") or {}).get("beam_levels"),
            })
        P(f"   (notes without a verdict row on one side: {missing})")
        P("\n-- kept -> narrowed: what differs between the nights' guard counters")
        for sg, c in sig_k2n.most_common():
            rs = ", ".join(f"{r} {k}" for r, k in sig_reason[sg].most_common())
            P(f"   {c:5d}  {sg}   [{rs}]")
        P("\n-- kept -> narrowed: other inputs that also differ on the same notes (GATHER-side readings)")
        for sg, c in gat.most_common(10):
            P(f"   {c:5d}  {sg}")

        # ink refusal reasons as a table over notes
        why = collections.Counter()
        for r in rows:
            if r["ink_refusal_why"]:
                why[r["ink_refusal_why"]] += 1
        if why:
            P("\n-- notes whose strokes the ink newly refused, by the ink's reason(s) (tonight's verdict)")
            for w, c in why.most_common():
                P(f"   {c:5d}  {w}")

        P("\n=== layer 2: narrowed -> kept")
        sig_n2k = collections.Counter()
        for p in n2k:
            va, vb = exa.get(p["a"]), exb.get(p["b"])
            if not va or not vb or va.get("none") or vb.get("none"):
                continue
            ca, cb = counters(va), counters(vb)
            sg = f"tonight decided by `{vb['reason']}`; last night `{va['reason']}`; " + signature(ca, cb)
            sig_n2k[sg] += 1
            page, sysi, staff, cell, _g = lud_bars.parse(p["b"])
            rows.append({
                "kind": "narrowed_to_kept", "subject": p["b"], "page": page, "system": sysi,
                "staff": staff, "cell": cell, "export_bar": off.get((page, sysi), -1) + cell + 1,
                "last_night_value_beats": " | ".join(parse_open(p["why"][0][0])[0] or []),
                "tonight_candidates_beats": value_beats(p["why"][1][0]), "tonight_reason": vb["reason"],
                "what_changed": sg, "gather_side_changes": gather_side(ca, cb),
                "ink_refusal_why": "/".join(cb["ink_why"]), "last_night_beam_levels": "",
            })
        for sg, c in sig_n2k.most_common(25):
            P(f"   {c:5d}  {sg}")
    elif exb:
        P("\n(no --extract-a: layer 2 pair table skipped)")

    if a.systems and rows:
        P("\n=== the drawn systems: kept -> narrowed notes by the guard input that differs")
        for spec in a.systems.split(","):
            pg, sy = (int(x) for x in spec.split("/"))
            sub = [r for r in rows if r["kind"] == "kept_to_narrowed" and r["page"] == pg and r["system"] == sy]
            tally = collections.Counter()
            for r in sub:
                w = r["ink_refusal_why"]
                tally["ink refused: " + w if w else r["what_changed"]] += 1
            P(f"   p{pg} s{sy}: {len(sub)} notes: " + "; ".join(f"{k} x{v}" for k, v in tally.most_common()))
    txt = "\n".join(out)
    print(txt)
    if a.out:
        Path(a.out).write_text(txt + "\n")
    if a.csv and rows:
        with open(a.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
