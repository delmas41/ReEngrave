"""ROADMAP 2.290 build -- the REAL judged cases this lane is held to (CLAUDE rule 7, DECISIONS 2026-11-10 CONTROLS FROM REAL JUDGED CASES).

    python3 benchmarks/page-heads-ledger-2026-11/real_cases/build_cases.py        # writes cases.json beside this file

Every tile in `data/judged-claims/registry.json` whose box Sean named as (part of) a notehead, or which a head box stood on and Sean named as
something else (2.289, 2.290 r1, 2.288's noteheads boxed as rests, 2.285's sharps that had been invented heads, 2.284's eighths, 2.282's heads), plus
the three 2.291 red-bar chords (tiles 7, 10, 11: two heads on one stem / a second, counted as two EVENTS -- each must stay TWO heads here). Each case
carries what Sean said and the expectation this lane tests:

  head          a real notehead: exactly ONE page head stands on the box's ink, with ONE claim
  part_of_head  a box over part of a real note: the note is one head; the box is a member of it or of nothing, never a second head with its own claim
  not_head      ink that is not a head (barline, beam, slash, ledger line, stem, flag, an accidental, a rest, word ink): no head claim on it
  tall_box      a box around several heads (2.290 tile 12): it makes no head of its own; the heads inside stay apart
  chord         a 2.291 bar whose first event is a chord: its heads stay at least two page heads (never joined)
  metronome     the note of a metronome mark (2.289 tile 1): head-shaped ink, not a staff note -- reported, not scored
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NOT_HEAD_KINDS = ("barline", "beam", "tremolo", "ledger_line", "stem", "flag", "word", "dynamic", "arc", "hairpin", "bracket", "clef", "meter", "key")
#: the 2.291 chord bars (out/print-from-worktrees/2.291-r1/key.json): plate, page, system, staff, cell
CHORDS = [("2.291 r1 #7", "litolff", 2, 1, 4, 14, "two half notes a second apart, both with ties"),
          ("2.291 r1 #10", "litolff", 2, 0, 2, 3, "two quarters on a single stem, followed by a quarter rest"),
          ("2.291 r1 #11", "brahms", 4, 1, 2, 0, "two eighth notes on a single stem with a staccato marking above it ...")]


def expectation(t):
    k, w = str(t.get("kind") or ""), str(t.get("words") or "").lower()
    if t.get("lane") == "2.289 r1" and t.get("tile") == 1:
        return "metronome"
    if "large rectangle" in w:
        return "tall_box"
    if k == "notehead":
        return "part_of_head" if (w.startswith("part of") or w.startswith("most of") or "small part" in w) else "head"
    if k.startswith(("accidental", "rest")) or k in NOT_HEAD_KINDS:
        return "not_head"
    return None


def main():
    reg = json.loads((ROOT / "data" / "judged-claims" / "registry.json").read_text())
    cases = []
    for t in reg["tiles"]:
        if not t.get("box"):
            continue
        e = expectation(t)
        if e is None:
            continue
        # only the tiles that are about heads: every notehead tile, and the non-head tiles of the lanes whose boxes were head boxes
        if e == "not_head" and t["lane"] not in ("2.289 r1", "2.290 r1", "2.285 r2", "2.288 r2", "2.288 r3", "2.288 r1"):
            continue
        cases.append(dict(id=t["id"], plate=t["plate"], page=int(t["page"]), box=[float(v) for v in t["box"]], expect=e, sean=t["words"], kind=t["kind"],
                          lane=t["lane"], tile=t["tile"]))
    for cid, plate, page, sy, st, ce, words in CHORDS:
        cases.append(dict(id=cid, plate=plate, page=page, cell=[page, sy, st, ce], expect="chord", sean=words, kind="notehead", lane="2.291 r1",
                          tile=int(cid.split("#")[1])))
    out = dict(what=__doc__.strip().splitlines()[0], cases=cases)
    (HERE / "cases.json").write_text(json.dumps(out, indent=1))
    by = {}
    for c in cases:
        by[(c["plate"], c["expect"])] = by.get((c["plate"], c["expect"]), 0) + 1
    print(len(cases), "cases", sorted(by.items()))
    for plate in ("litolff", "brahms"):
        spec = dict(out_dir=str(HERE / "crops"), plate=plate, cases=[c for c in cases if c["plate"] == plate and c.get("box")])
        (HERE / ("dump-%s.json" % plate)).write_text(json.dumps(spec, indent=1))
    # one spec for a run that gathers both plates (`lane_report`): the plate is picked by the page's staff space (Litolff 15.75 px, Brahms ~22+)
    allspec = dict(out_dir=str(HERE / "crops"), plates={
        "litolff": dict(sp=[10.0, 19.0], cases=[c for c in cases if c["plate"] == "litolff" and c.get("box")]),
        "brahms": dict(sp=[19.0, 45.0], cases=[c for c in cases if c["plate"] == "brahms" and c.get("box")])})
    (HERE / "dump-all.json").write_text(json.dumps(allspec, indent=1))


if __name__ == "__main__":
    main()
