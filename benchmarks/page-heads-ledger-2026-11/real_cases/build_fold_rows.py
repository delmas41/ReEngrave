"""ROADMAP 2.290 round 4 -- the REAL ROWS of every page head the one identity folds from boxes that write different pitches (CLAUDE rule 7: a control from real rows).

    python3 benchmarks/page-heads-ledger-2026-11/real_cases/build_fold_rows.py WORKDIR   # a lane-report work dir (`<plate>.on.gathered.record.json`, `.on.symbols.json`)

Writes `fold_rows.json` beside this file: per fold (page head group) its members' `Q.GLYPH_BOX`, `Q.NOTEHEAD_STAFF_POSITION` (value + detail), `Q.MARK_GROUP` detail,
detector confidence, the pitch each member wrote OFF, and what `expect` the test holds the export to: `settle` (the ink witness names one member: Litolff p2 m7, the
tie F3 -> F3) or `guess` (no witness: the most confident member stands, GUESSED) or `ignore` (a tall box / a sliver is no witness: nothing changes).
`test_fold_pitch_2_290_r4.py` replays them through `export._settle_folded_pitches`.
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
FOLDS = {   # group id -> (plate, expect, what)
    "mg/2/0/245": ("litolff", "settle", "p2 m7 half note: boxes 7.04 / 8.28 steps, hole 7.81 -> F3; the tie F3 (m7) -> F3 (m8) is kept"),
    "mg/11/1/321": ("litolff", "guess", "p11 m107: B4 box and a thin A4 box, no ink witness"),
    "mg/8/1/100": ("litolff", "guess", "p8 D4 fold, no ink witness"),
    "mg/8/1/124": ("litolff", "guess", "p8 Ab2 fold, no ink witness"),
    "mg/8/1/233": ("litolff", "guess", "p8 C3 fold, no ink witness"),
    "mg/14/1/43": ("brahms", "guess", "Brahms p14 G4 fold, no ink witness"),
    "mg/19/0/775": ("brahms", "guess", "Brahms p19 Ab5 fold, no ink witness"),
    "mg/2/0/148": ("litolff", "ignore", "p2 m4: a head-sized box and a tall (7 sp) box: the tall box is no witness, nothing changes"),
}


#: the pitch the EXPORT built for a member where it is not the decided `Q.PITCH` verdict (the key / accidental alteration is applied in export: one box owns the flat, its
#: sibling box does not) -- read off `export._settle_folded_pitches`' own queue on the five pages
EXPORT_PITCH = {"glyph/8/1/10/3/1": "Ab2", "glyph/8/1/10/3/2": "A2", "glyph/19/0/0/10/5": "Ab5", "glyph/19/0/0/10/12": "C6"}


def main(work):
    out = {}
    for plate in ("litolff", "brahms"):
        d = json.load(open("%s/%s.on.gathered.record.json" % (work, plate)))
        rec = d.get("record", d)
        sj = json.load(open("%s/%s.off.symbols.json" % (work, plate)))
        off_p = collections.defaultdict(list)
        for h in sj["hosts"]:
            if h["kind"] == "note":
                off_p[h["rg"]].append(h["pitch"])
        rows = collections.defaultdict(lambda: collections.defaultdict(dict))
        pitch = {}
        for o in rec["observations"]:
            q, s = o.get("quantity"), o.get("subject", "")
            if q in ("glyph_box", "notehead_staff_position", "glyph_conf", "mark_group"):
                rows[s][q] = dict(value=o.get("value"), detail=o.get("detail") or {})
        for v in rec["verdicts"]:
            if v.get("quantity") == "pitch" and v.get("outcome") == "decided":
                pitch[v["subject"]] = v["value"]
        groups = collections.defaultdict(list)
        for s, r in rows.items():
            if "mark_group" in r:
                groups[r["mark_group"]["value"]].append(s)
        for gid, (pl, expect, what) in FOLDS.items():
            if pl != plate:
                continue
            out[gid] = dict(plate=plate, expect=expect, what=what, members=[dict(sub=m, rows=rows[m], pitch=EXPORT_PITCH.get(m, pitch.get(m)), off_pitches=off_p.get(m, [])) for m in sorted(groups[gid])])
    (HERE / "fold_rows.json").write_text(json.dumps(out, indent=1, default=str))
    print({k: len(v["members"]) for k, v in out.items()})


if __name__ == "__main__":
    main(sys.argv[1])
