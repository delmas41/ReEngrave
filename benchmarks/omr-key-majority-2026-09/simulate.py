"""Price the marker-primary key rule against today's verdicts, OFFLINE.

    python3 benchmarks/omr-key-majority-2026-09/simulate.py <record.json> <truth>

`truth` is `beethoven5` (C minor throughout mvt 1: every concert-pitch staff
−3, a B-flat clarinet −1, natural horn/trumpet/timpani 0) or `brahms1`
(`data/dossiers/brahms-sym1-mvt1.json`'s opening keys, by instrument) or
`engraved` (the fixture's own MusicXML, by part name).

⚠️ THIS DECIDES NOTHING AND SHIPS NOTHING. It reads a saved record and
reports what a marker-primary rule WOULD have said, so the rule is priced
before it is written — the "reach before accuracy" discipline, and the reason
the answer here changed the design.

⚠️ THE TRUTH USED FOR THE TWO SCANS IS A DOCUMENT-LEVEL FACT, not a page
truth: the movement has one key and no key changes, so every staff's printed
signature is known from its instrument alone. A staff whose instrument we
could not name is counted separately and never scored.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged.record_io import load_record   # noqa: E402
from tools.omr import instruments as _inst           # noqa: E402
from tools.omr import key_consensus as KC            # noqa: E402

#: Beethoven 5 mvt 1 and Brahms 1 mvt 1 are both in C minor; the difference is
#: which staves print the signature. Keyed on the lexicon's instrument NAME.
BEETHOVEN5 = {"Horn": 0, "Trumpet": 0, "Timpani": 0, "Clarinet": -1}
#: Brahms 1 mvt 1 opening. ⚠️ Horn is TWO keys on that page (C horns, E-flat
#: horns), so a horn staff cannot be scored from its instrument alone and is
#: left unscored.
#:
#: ⚠️⚠️ TIMPANI IS **0**, AND THE DOSSIER SAYS -3. `data/dossiers/
#: brahms-sym1-mvt1.json` is generated from a MusicXML encoding, and
#: CLAUDE.md §8 refuses an `encoding` fact in any measurement path -- this is
#: the concrete instance of why. The Breitkopf plate is in
#: `out/print/breitkopf-p1-system0-header.png`: `Pk.` carries an F clef and
#: NO accidentals, exactly as [C81] says a 19th-century timpani staff does,
#: while the modern encoding writes the three flats. Scoring the plate
#: against the encoding would have charged every timpani staff of the
#: movement as wrong.
BRAHMS1 = {"Horn": None, "Trumpet": 0, "Timpani": 0, "Clarinet": -1}
#: The Verovio fixture is a MODERN encoding: its C trumpets and its timpani
#: DO print the three flats, which is the 19th-century plate's difference from
#: it and the reason the two scans get their own table.
ENGRAVED = {"Horn": 0, "Trumpet": -3, "Timpani": -3, "Clarinet": -1}
TRUTHS = {"beethoven5": BEETHOVEN5, "brahms1": BRAHMS1, "engraved": ENGRAVED}
CONCERT = -3


def fields(key: str):
    head, *rest = key.split("/")
    nums = [int(x) if x.isdigit() else None for x in rest]
    while len(nums) < 4:
        nums.append(None)
    return head, nums[0], nums[1], nums[2], nums[3]


def marker_reading(marks, space):
    """(fifths, reason) from the detector's key accidentals at cell 0.

    ⚠️ SLOTS, NOT BOXES (convention C21: the accidentals stand at fixed slots
    in a fixed order). Two boxes within half a staff space of one another in x
    are ONE slot — on the engraved fixture Violin 1 carries four boxes at
    x 375/461/463/545, and the pair is one slot plus a neighbour's ink bled in
    through the cell's 4-space pad.
    """
    if not marks:
        return None, "no_markers"
    kinds = {m["value"] for m in marks}
    if len(kinds) > 1:
        return None, "mixed_marker_kinds"
    xs = sorted(float(m["detail"].get("x", 0)) for m in marks)
    sp = space if space else 12.0
    tol = 0.5 * sp
    centres = [xs[0]]
    for a, b in zip(xs, xs[1:]):
        if b - a > tol:
            centres.append(b)
    # ⚠️ THE RUN IS A LADDER, NOT A POPULATION. The signature's slots stand
    # about one staff space apart; an accidental printed INSIDE the first bar
    # is also in cell 0 and must not be counted. Keep the leading chain and
    # stop at the first gap wider than two spaces.
    slots = 1
    for a, b in zip(centres, centres[1:]):
        if b - a > 2.0 * sp:
            break
        slots += 1
    if len(centres) > 7:
        return None, "too_many_markers"
    kind = next(iter(kinds))
    if kind == "keyNatural":
        return None, "natural_markers"
    return (-slots if kind == "keyFlat" else slots), "markers"


def main(path: str, truth_kind: str) -> None:
    r = load_record(path)
    rec = r["record"]
    label, clef, keyv, space = {}, {}, {}, {}
    marks = collections.defaultdict(list)
    fitrows = collections.defaultdict(list)
    tplrows = collections.defaultdict(list)
    runstate = {}
    for o in rec["observations"]:
        q = o["quantity"]
        _, p, s, st, _ = fields(o["subject"])
        k = (p, s, st)
        if q == "margin_label":
            label[k] = o["value"]
        elif q == "keysig_marker":
            marks[k].append(o)
        elif q == "keysig_clef_fit":
            fitrows[k].append(o)
        elif q == "keysig_template_fit":
            tplrows[k].append(o)
        elif q == "keysig_run_position":
            runstate[k] = True
        elif q == "cell_staff_space" and fields(o["subject"])[4] == 0:
            # ⚠️ THE MARKER'S x IS `x_canonical` — the CELL's frame — so the
            # tolerance must be the CELL's staff space, never the page's
            # `staff_spacing`. Two frames under one name is how a consumer
            # comes to compare lengths that were never in the same units
            # (record.py, `CELL_STAFF_SPACE`).
            try:
                space[k] = float(o["value"])
            except (TypeError, ValueError):
                pass
    for v in rec["verdicts"]:
        _, p, s, st, _ = fields(v["subject"])
        if v["quantity"] == "clef":
            clef[(p, s, st)] = v.get("value")
        elif v["quantity"] == "key_signature":
            keyv[(p, s, st)] = v

    # the label a staff inherits: a continuation system reprints no label, so
    # the part's name comes from the first staff of its slot that carried one.
    # Here we only score staves that carry their OWN label.
    def truth_for(k):
        text = label.get(k)
        if not text:
            return None, None
        m = _inst.lookup(str(text))
        if m is None:
            return None, None
        name = m.instrument.name
        table = TRUTHS[truth_kind]
        if name in table:
            return table[name], name
        return CONCERT, name

    today_right = today_wrong = today_abst = 0
    mark_right = mark_wrong = mark_abst = 0
    unscored = 0
    branch = collections.Counter()
    agree_fit = collections.Counter()
    rows = []
    for k in sorted(keyv):
        v = keyv[k]
        sp = space.get(k)
        mk, why = marker_reading(marks.get(k, []), sp)
        fit = None
        c = clef.get(k)
        for o in fitrows.get(k, []):
            if str(o["value"]) == str(c):
                fit = o["detail"].get("fifths")
        tpl = None
        for o in tplrows.get(k, []):
            if str(o["value"]) == str(c):
                tpl = o["detail"].get("fifths")
        # the proposed rule
        if c is None:
            prop, preason = None, "needs_clef"
        elif mk is not None:
            prop, preason = mk, "markers"
            if fit is not None:
                agree_fit["fit_agrees" if fit == mk else "fit_disagrees"] += 1
        elif why in ("no_markers",):
            if fit is not None:
                prop, preason = fit, "fitted_no_markers"
            elif tpl is not None:
                prop, preason = tpl, "fitted_no_markers_template"
            else:
                prop, preason = None, "no_evidence"
        else:
            prop, preason = None, why
        branch[preason] += 1

        t, iname = truth_for(k)
        today = v.get("value") if v["outcome"] == "decided" else None
        # concert normalisation, for the system check
        name, offset, known = KC.resolve_label(label.get(k))
        eligible = (name is not None and offset is not None and known
                    and name not in KC.NO_SIGNATURE_CONVENTION
                    and name not in KC.MAY_DIFFER_NOT_A_WITNESS)
        concert = (prop - offset) if (eligible and prop is not None) else None
        rows.append(dict(subject=f"{k[0]}/{k[1]}/{k[2]}", system=f"{k[0]}/{k[1]}",
                         label=label.get(k),
                         instrument=iname, truth=t, today=today,
                         today_reason=v.get("reason"), markers=len(marks.get(k, [])),
                         marker_fifths=mk, marker_reason=why, fit=fit,
                         template=tpl, proposed=prop, proposed_reason=preason,
                         offset=offset if eligible else None, concert=concert))

    # ── the SYSTEM CHECK: a lone dissenter is a misreading, not music ───────
    # ⚠️ A CHECK THAT CAN FAIL, NOT A VOTE. A staff whose concert key has NO
    # peer on its own system is superseded to an abstention; where two staves
    # share a value neither is touched, however many disagree.
    by_system = collections.defaultdict(list)
    for row in rows:
        if row["concert"] is not None:
            by_system[row["system"]].append(row)
    superseded = 0
    for sysrows in by_system.values():
        tally = collections.Counter(r["concert"] for r in sysrows)
        if len(sysrows) < 2:
            continue
        for r in sysrows:
            if tally[r["concert"]] == 1:
                r["checked"] = None
                r["checked_reason"] = "disagrees_with_system"
                superseded += 1
    for row in rows:
        row.setdefault("checked", row["proposed"])
        row.setdefault("checked_reason", row["proposed_reason"])

    def score(field):
        right = wrong = abst = 0
        for row in rows:
            if row["truth"] is None:
                continue
            got = row[field]
            if got is None:
                abst += 1
            elif got == row["truth"]:
                right += 1
            else:
                wrong += 1
        return right, wrong, abst

    unscored = sum(1 for row in rows if row["truth"] is None)
    print(f"== {path}  truth={truth_kind}")
    print(f"staves with a key verdict: {len(keyv)}; scored: {len(keyv)-unscored}; "
          f"unscored (no resolvable label): {unscored}")
    print("TODAY   right %d  wrong %d  abstained %d" % score("today"))
    print("MARKERS right %d  wrong %d  abstained %d" % score("proposed"))
    print("MARKERS+SYSTEM right %d  wrong %d  abstained %d" % score("checked")
          + f"   (superseded {superseded})")
    print("proposed branches:", dict(branch))
    print("fit vs markers:", dict(agree_fit))
    out = pathlib.Path(path).name.replace(".record.json", "")
    dest = (pathlib.Path(__file__).parent / "out" / f"simulate-{out}.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(rows, indent=1, default=str))
    print("rows ->", dest)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
