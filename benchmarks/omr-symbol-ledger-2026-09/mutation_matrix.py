"""Inject ONE known error. Ask both instruments what it was.

⚠️ **THIS IS THE ONE MEASUREMENT IN THIS DIRECTORY THAT DEPENDS ON NO CLAIM
ABOUT REAL DATA.** Everything else compares a prediction to a truth and has to
argue about what the residual is. Here the residual is CONSTRUCTED: a truth
file is copied, exactly one thing is changed, and the mutant is scored against
the original as if it were a prediction. The right answer is known by
construction, so this is a positive control for both instruments at once —
and it is what `page_truth.render_fidelity` is to the page-truth harness.

It doubles as the RED RUN. A control that has never failed is not known to be
able to fail; every mutation here is asserted to be NAMED by the ledger, and
`--assert` exits non-zero when one is not.

WHAT IT SHOWS
-------------
`musicdiff` under `AllObjects` — the benchmark's own detail level — pairs
notes BY PITCH. So a single changed pitch cannot come back as a pitch error:
the pairing it would have been reported on is the thing the error destroyed.
The mutation matrix makes that visible in one table without any appeal to
what the scan corpus contains.

    python3 benchmarks/omr-symbol-ledger-2026-09/mutation_matrix.py \\
        --truth <a truth .musicxml> --out out/mutation-matrix.json --assert
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Callable

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import omr_ned  # noqa: E402
from tools.omr.symbol_ledger import build_ledger, summarise  # noqa: E402

_ALTER_TEXT = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "##"}


# ---------------------------------------------------------------------------
# Mutations. Each returns (tree, human description of the ONE thing changed).
# ---------------------------------------------------------------------------


def _tag(el: ET.Element) -> str:
    return el.tag.split("}")[-1] if isinstance(el.tag, str) else ""


def _parts(root: ET.Element) -> list[ET.Element]:
    return [p for p in root if _tag(p) == "part"]


def _measures(part: ET.Element) -> list[ET.Element]:
    return [m for m in part if _tag(m) == "measure"]


def _notes(measure: ET.Element) -> list[ET.Element]:
    return [n for n in measure if _tag(n) == "note"]


def _pitched(measure: ET.Element) -> list[ET.Element]:
    return [n for n in _notes(measure)
            if n.find("rest") is None and n.find("grace") is None
            and n.find("chord") is None and n.find("pitch") is not None]


def _first_cell(root: ET.Element, *, need: int = 2,
                pitched_only: bool = True) -> tuple[int, ET.Element, list[ET.Element]]:
    """The first (part, measure) holding at least `need` usable notes.

    Deterministic on purpose — the mutation must be reproducible from the file
    alone, with no seed to record and lose.
    """
    for pi, part in enumerate(_parts(root)):
        for m in _measures(part):
            got = _pitched(m) if pitched_only else _notes(m)
            if len(got) >= need:
                return pi, m, got
    raise SystemExit("no measure with enough notes to mutate")


def mut_pitch(root: ET.Element) -> str:
    """One note's step, nothing else. The bar still sums; only the pitch moved."""
    pi, m, notes = _first_cell(root, need=2)
    n = notes[1]
    p = n.find("pitch")
    step = p.find("step")
    old = step.text
    step.text = "C" if old != "C" else "D"
    for a in list(p.findall("alter")):
        p.remove(a)
    for a in list(n.findall("accidental")):
        n.remove(a)
    return (f"part {pi} measure {m.get('number')}: the 2nd note's step "
            f"{old} -> {step.text}")


def mut_octave(root: ET.Element) -> str:
    """One note an octave down — a pitch error a ledger-line misread makes."""
    pi, m, notes = _first_cell(root, need=2)
    n = notes[1]
    oc = n.find("pitch").find("octave")
    old = int(oc.text)
    oc.text = str(old - 1)
    return f"part {pi} measure {m.get('number')}: the 2nd note's octave {old} -> {old - 1}"


def mut_written_type(root: ET.Element) -> str:
    """One note's WRITTEN type, its sounding duration untouched — the shape a
    misread beam level makes when the bar still adds up."""
    pi, m, notes = _first_cell(root, need=2)
    n = notes[1]
    t = n.find("type")
    old = t.text
    t.text = "16th" if old != "16th" else "eighth"
    return f"part {pi} measure {m.get('number')}: the 2nd note's <type> {old} -> {t.text}"


def mut_duration_swap(root: ET.Element) -> str:
    """Two adjacent notes exchange durations. The bar still sums, no pitch
    moved, and the second note's ONSET moves — which is exactly why `onset`
    is not treated as a duration-blind key."""
    for pi, part in enumerate(_parts(root)):
        for m in _measures(part):
            got = _pitched(m)
            for i in range(len(got) - 1):
                a, b = got[i], got[i + 1]
                da, db = a.find("duration"), b.find("duration")
                ta, tb = a.find("type"), b.find("type")
                if da is None or db is None or da.text == db.text:
                    continue
                if len(a.findall("dot")) or len(b.findall("dot")):
                    continue
                da.text, db.text = db.text, da.text
                if ta is not None and tb is not None:
                    ta.text, tb.text = tb.text, ta.text
                return (f"part {pi} measure {m.get('number')}: notes {i} and "
                        f"{i+1} exchange durations")
    return "SKIPPED: no adjacent pair of undotted notes with different durations"


def mut_delete_note(root: ET.Element) -> str:
    """One note gone. The bar is now short — the commonest real failure."""
    pi, m, notes = _first_cell(root, need=3)
    n = notes[1]
    m.remove(n)
    return f"part {pi} measure {m.get('number')}: the 2nd note deleted"


def mut_insert_note(root: ET.Element) -> str:
    """One note too many — a doubled detection."""
    pi, m, notes = _first_cell(root, need=2)
    dup = copy.deepcopy(notes[1])
    idx = list(m).index(notes[1])
    m.insert(idx + 1, dup)
    return f"part {pi} measure {m.get('number')}: the 2nd note duplicated"


def mut_accidental(root: ET.Element) -> str:
    """The PRINTED accidental only — the pitch is unchanged, so this separates
    'spelled wrong' from 'sounds wrong'."""
    for pi, part in enumerate(_parts(root)):
        for m in _measures(part):
            for n in _notes(m):
                a = n.find("accidental")
                if a is not None and a.text:
                    old = a.text
                    a.text = "natural" if old != "natural" else "sharp"
                    return (f"part {pi} measure {m.get('number')}: a printed "
                            f"<accidental> {old} -> {a.text} (pitch untouched)")
    return "SKIPPED: this file prints no <accidental>"


def mut_dynamic(root: ET.Element) -> str:
    for pi, part in enumerate(_parts(root)):
        for m in _measures(part):
            for d in m:
                if _tag(d) != "direction":
                    continue
                for dt in d.findall("direction-type"):
                    dyn = dt.find("dynamics")
                    if dyn is not None and len(dyn):
                        old = _tag(dyn[0])
                        dyn.remove(dyn[0])
                        dyn.append(ET.Element("pp"))
                        return (f"part {pi} measure {m.get('number')}: a dynamic "
                                f"{old} -> pp")
    return "SKIPPED: this file carries no <dynamics>"


def mut_delete_slur(root: ET.Element) -> str:
    for pi, part in enumerate(_parts(root)):
        for m in _measures(part):
            for n in _notes(m):
                nt = n.find("notations")
                if nt is None:
                    continue
                for s in list(nt):
                    if _tag(s) == "slur":
                        nt.remove(s)
                        return (f"part {pi} measure {m.get('number')}: one "
                                f"<slur> endpoint deleted")
    return "SKIPPED: this file carries no <slur>"


def mut_delete_measure(root: ET.Element) -> str:
    """One bar gone from ONE part — the bar counts now disagree, which is the
    condition tier 2 is built to declare rather than absorb."""
    part = _parts(root)[0]
    ms = _measures(part)
    if len(ms) < 3:
        return "SKIPPED: fewer than 3 measures"
    victim = ms[1]
    part.remove(victim)
    return f"part 0: measure {victim.get('number')} deleted"


def _normalised(measures: list[ET.Element]) -> bytes:
    """The measures' markup with layout whitespace AND `<print>` gone, so a
    vacuity test compares MUSIC and not page furniture.

    ⚠️ Both were needed and the second was the surprise: Mahler 5 p.3's first
    two reference parts differ ONLY in `<print><system-layout>` — where the
    page break falls — so swapping them changes no symbol, and the ledger and
    musicdiff both correctly report nothing. Read off raw markup the swap
    looks real and the instrument looks blind.
    """
    out = []
    for m in measures:
        c = copy.deepcopy(m)
        for parent in [c] + list(c.iter()):
            for child in list(parent):
                if _tag(child) == "print":
                    parent.remove(child)
        for el in c.iter():
            el.text = (el.text or "").strip() or None
            el.tail = None
        out.append(ET.tostring(c))
    return b"".join(out)


def mut_swap_parts(root: ET.Element) -> str:
    """Two parts exchange their music — the staff-identity error, and the one
    the `entire staff insert/delete` bucket is full of."""
    parts = _parts(root)
    if len(parts) < 2:
        return "SKIPPED: fewer than 2 parts"
    a, b = parts[0], parts[1]
    if _normalised(_measures(a)) == _normalised(_measures(b)):
        # ⚠️ A VACUOUS MUTATION IS NOT A FAILED INSTRUMENT. Mahler 5 p.3 prints
        # two parts whose bars are byte-identical (both tacet), so swapping
        # them changes nothing and BOTH instruments correctly report nothing.
        # Detected here rather than read as a miss.
        return "SKIPPED: parts 0 and 1 carry identical music — the swap is a no-op"
    am = _measures(a)
    bm = _measures(b)
    for x in am:
        a.remove(x)
    for x in bm:
        b.remove(x)
    for x in bm:
        a.append(x)
    for x in am:
        b.append(x)
    return "parts 0 and 1 exchange all their music"


#: `accepts` — answers that are TRUE of this mutation. `forbids` — answers
#: that would be a MISATTRIBUTION, which is the property this matrix actually
#: tests. ⚠️ "declared ambiguous" is an acceptable answer to a deletion or an
#: insertion and is NOT a failure: removing a note from the middle of a bar
#: leaves two readings genuinely consistent with the encoding ("note 2 is
#: gone and the rest shifted" / "note 2 has the wrong pitch and length"), and
#: an instrument that picks one silently is the thing being replaced.
MUTATIONS: dict[str, tuple[Callable[[ET.Element], str], set[str], set[str]]] = {
    "pitch_step":     (mut_pitch,          {"note.pitch"},
                       {"note.duration_ql", "note.type", "note.dots"}),
    "pitch_octave":   (mut_octave,         {"note.pitch"},
                       {"note.duration_ql", "note.type", "note.dots"}),
    "written_type":   (mut_written_type,   {"note.type"},
                       {"note.pitch", "note.accidental"}),
    "duration_swap":  (mut_duration_swap,  {"note.duration_ql", "note.type"},
                       {"note.pitch", "note.accidental"}),
    "delete_note":    (mut_delete_note,    {"note:missing", "ambiguous"},
                       {"note.pitch", "note.duration_ql"}),
    "insert_note":    (mut_insert_note,    {"note:spurious", "ambiguous"},
                       {"note.pitch", "note.duration_ql"}),
    "accidental":     (mut_accidental,     {"note.accidental"},
                       {"note.pitch", "note.duration_ql", "note.type"}),
    "dynamic_text":   (mut_dynamic,        {"dynamic.text"},
                       {"note.pitch", "note.duration_ql"}),
    "delete_slur":    (mut_delete_slur,    {"slur:missing", "ambiguous"},
                       {"note.pitch", "note.duration_ql",
                        "uncorresponded:measure_unresolved"}),
    "delete_measure": (mut_delete_measure, {"note:missing", "rest:missing",
                                            "clef:missing", "key:missing",
                                            "time:missing", "ambiguous",
                                            "uncorresponded:measure_unresolved"},
                       {"note.pitch", "note.duration_ql"}),
    # ⚠️ `accepts=ANY`. A part swap's signature depends entirely on how far
    # apart the two parts' music is: swap two resting flutes and the only
    # honest answer is a handful of rests and words. Naming a specific
    # expectation here would have been fitting the control to one file.
    "swap_parts":     (mut_swap_parts,     {"ANY"}, set()),
}


# ---------------------------------------------------------------------------
# Running the two instruments over one mutant
# ---------------------------------------------------------------------------


def ledger_verdict(mutant: Path, truth: Path) -> dict[str, Any]:
    res = build_ledger(row_id=mutant.stem, pred_path=mutant, truth_path=truth)
    s = summarise(res)
    cov = s["coverage"]
    named = Counter()
    weak = Counter()
    for r in res.rows:
        tgt = named if r.basis_strength != "single_key" else weak
        for a in r.attrs_wrong:
            tgt[f"{r.family}.{a}"] += 1
    for r in res.rows:
        if r.outcome in ("missing", "spurious"):
            named[f"{r.family}:{r.outcome}"] += 1
        elif r.outcome == "uncorresponded":
            named[f"uncorresponded:{r.reason}"] += 1
        elif r.outcome == "ambiguous":
            named["ambiguous"] += 1
    return {
        "outcomes": s["outcomes"],
        "named": dict(named.most_common(8)),
        "named_single_key": dict(weak.most_common(8)),
        "coverage_balanced": cov["balanced"],
        "measure_map": s["measure_map"]["status"],
        "not_assessable": s["attributes_not_assessable"],
    }


def musicdiff_verdict(mutant: Path, truth: Path, detail: str) -> dict[str, Any]:
    try:
        r = omr_ned.score_pair(pred=mutant, truth=truth, detail=detail,
                               name=mutant.stem)
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed
        return {"error": str(exc)[:400]}
    cats = {k: v for k, v in (r.get("categories") or {}).items() if v}
    return {"omr_ned": r.get("omr_ned"), "omr_ed": r.get("omr_ed"),
            "categories": dict(sorted(cats.items(), key=lambda kv: -kv[1])[:8])}


def run(truth: Path, out: Path | None, detail: str, do_assert: bool,
        skip_musicdiff: bool) -> int:
    raw = truth.read_bytes()
    rows: list[dict[str, Any]] = []
    tmp = Path(tempfile.mkdtemp(prefix="mutation-matrix-"))
    failures: list[str] = []
    try:
        # control: the unmutated copy. Both instruments must report NOTHING.
        control = tmp / "control.musicxml"
        control.write_bytes(raw)
        rows.append({
            "mutation": "(control: no change)", "expects": "nothing",
            "what": "the file, copied",
            "ledger": ledger_verdict(control, truth),
            "musicdiff": {} if skip_musicdiff else musicdiff_verdict(control, truth, detail),
        })
        for name, (fn, accepts, forbids) in MUTATIONS.items():
            root = ET.fromstring(raw)
            what = fn(root)
            path = tmp / f"{name}.musicxml"
            path.write_bytes(ET.tostring(root, encoding="utf-8",
                                         xml_declaration=True))
            entry = {
                "mutation": name,
                "expects": "/".join(sorted(accepts)),
                "forbids": "/".join(sorted(forbids)) or "(nothing)",
                "what": what,
                "ledger": ledger_verdict(path, truth),
                "musicdiff": {} if skip_musicdiff else musicdiff_verdict(path, truth, detail),
            }
            rows.append(entry)
            if what.startswith("SKIPPED"):
                continue
            named = set(entry["ledger"]["named"])
            weak_named = set(entry["ledger"]["named_single_key"])
            entry["named_correctly"] = sorted(named & accepts)
            entry["misattributed"] = sorted(named & forbids)
            if not named:
                failures.append(f"{name}: the ledger noticed NOTHING")
            elif "ANY" not in accepts and not (named & accepts):
                failures.append(f"{name}: expected one of {sorted(accepts)}, "
                                f"ledger named {sorted(named)}")
            if named & forbids:
                failures.append(f"{name}: MISATTRIBUTED as {sorted(named & forbids)}")
            entry["misattributed_single_key"] = sorted(weak_named & forbids)
            if not entry["ledger"]["coverage_balanced"]:
                failures.append(f"{name}: ledger coverage did not balance")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    ctl = rows[0]["ledger"]
    if set(ctl["outcomes"]) - {"matched_exact"}:
        failures.append(f"control was not clean: {ctl['outcomes']}")

    report = {"truth": str(truth), "detail": detail, "rows": rows,
              "failures": failures}
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=1))
    _print(report, skip_musicdiff)
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
    return 1 if (do_assert and failures) else 0


def _print(report: dict[str, Any], skip_musicdiff: bool) -> None:
    print(f"truth: {report['truth']}")
    print(f"musicdiff detail level: {report['detail']}\n")
    w = 17
    for r in report["rows"]:
        print(f"── {r['mutation']}  (accepts: {r['expects']}; must not say: {r.get('forbids', '')})")
        print(f"   what        {r['what']}")
        lg = r["ledger"]
        print(f"   {'LEDGER':<{w}}{lg['named'] or 'nothing — clean'}")
        if lg.get("named_single_key"):
            print(f"   {'  single-key':<{w}}{lg['named_single_key']}  (uncorroborated pairing)")
        print(f"   {'  outcomes':<{w}}{lg['outcomes']}")
        if not skip_musicdiff:
            md = r["musicdiff"]
            if "error" in md:
                print(f"   {'MUSICDIFF':<{w}}ERROR {md['error'][:120]}")
            else:
                print(f"   {'MUSICDIFF':<{w}}{md.get('categories') or 'nothing — clean'}")
                print(f"   {'  omr_ed':<{w}}{md.get('omr_ed')}   omr_ned {md.get('omr_ned')}")
        print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--truth", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--detail", default="AllObjects",
                    help="musicdiff detail level. AllObjects is the benchmark's own; "
                         "changing it changes what every historical figure means, so "
                         "this only ever reports beside it, never replaces it.")
    ap.add_argument("--assert", dest="do_assert", action="store_true")
    ap.add_argument("--no-musicdiff", action="store_true")
    a = ap.parse_args(argv)
    return run(a.truth, a.out, a.detail, a.do_assert, a.no_musicdiff)


if __name__ == "__main__":
    sys.exit(main())
