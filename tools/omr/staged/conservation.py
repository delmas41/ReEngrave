"""ROADMAP 2.286 -- NOTE CONSERVATION, IN MINUTES, ON REAL PAGES.

    python3 -m tools.omr.staged.conservation [--plates litolff,brahms] [--pages 1,2] [--tag 20261029-night] [--ink]

PATH: STAGED, ADJUDICATE..EXPORT replay. Reads, decides nothing, changes no verdict and no byte of the exported file.

WHAT IT RUNS. The saved GATHER rows of the night record, as `lane_report` slices them
(`library/_shared-records/lane-report-slices-<tag>/<plate>/{observations,abstentions}.jsonl`), cut here to the asked
pages (streamed; the slice's 1.7 GB verdict file is never opened -- a replay discards verdicts anyway), replayed through
ADJUDICATE, GROUPS, EVALUATE, INFER and EXPORT exactly as `lane_report --from adjudicate` does, on main's defaults. No
detector, no OCR. Default pages: the plate's OPENING page (whose meter/key every later bar inherits; it is counted, so
the block says what it counted) and one more -- Litolff 1,2; Brahms 0,4.

WHAT IT PRINTS, per plate (every number comes from the export's own REPORT, `report["conservation"]`, `report["balance"]`):
  read by ADJUDICATE (heads + rests) -- the denominator; written plain; written GUESSED (blue); INSIDE a red bar (counted
  written by the balance, listed by bar so it can be found); inside a partial-bar gap and inside a held bar (counted not
  written, listed by bar); not written by named reason, largest first; UNACCOUNTED (must be 0); and the ink never boxed,
  which no count here can see (`--ink` runs `claim_readout` on the same slice; otherwise "not measured").

THE INVARIANT (`check`): every read head/rest is exactly one of written, in a marked bar, or not written under a NAMED
reason; no reason is empty or unknown; the places listed add up to their counters; the totals balance. `to_musicxml`
already RAISES `Unbalanced` on the totals; `check` adds the two things the raise cannot see (an unnamed reason; a bar-level
row that cannot be located), and a doctored report fails it (tests: `test_conservation_2_286.py`).

CONVENTION ASSUMED: a head inside a red bar is written (the bar keeps every event it read, drawn red), so it is listed
apart but not subtracted from written. WHAT WOULD FALSIFY IT: Sean calling a red bar's notes "not written". NOT CONFIRMED.
Counts per VOICE copy (a rest written once per voice) are netted by the balance, not here.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_TAG = "20261029-night"
DEFAULT_PAGES = {"litolff": [1, 2], "brahms": [0, 4]}
#: A reason string that names nothing.
UNNAMED = frozenset({"", "unknown", "unspecified", "other", "none", "?"})


def load_pages(plate: str, pages: Sequence[int], tag: str) -> Dict[str, List[dict]]:
    """The slice's gather rows for `pages` (+ every document-level row); verdicts are not read."""
    from . import lane_report as LR
    d = LR.slice_dir(plate, tag)
    keep = set(pages)
    out: Dict[str, List[dict]] = {"verdicts": []}
    for kind in ("observations", "abstentions"):
        rows = []
        with open(d / ("%s.jsonl" % kind)) as fh:
            for line in fh:
                # cheap test first: the page number sits in the subject; parse only rows that can matter
                it = json.loads(line)
                pg = LR.page_of(it.get("subject"))
                if pg is None or pg in keep:
                    rows.append(it)
        out[kind] = rows
    return out


def export_pages(rec: Dict[str, List[dict]]) -> Dict[str, Any]:
    """ADJUDICATE..EXPORT on the rows; returns {report, xml, seconds}."""
    from . import export as E
    from .review import rerun as RR
    t0 = time.time()
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log
    xml, report = E.to_musicxml(result)
    return {"xml": xml, "report": report, "seconds": round(time.time() - t0, 1)}


def check(report: Dict[str, Any]) -> List[str]:
    """The invariant. Returns the list of problems; empty means every read head/rest is accounted for."""
    bad: List[str] = []
    c = report.get("conservation")
    b = report.get("balance")
    if not c or not b:
        return ["the report carries no conservation / balance section"]
    if not b.get("balanced"):
        bad.append("balance says not balanced")
    unacc = c["read_by_adjudicate"] - c["written"] - c["not_written_total"]
    if unacc:
        bad.append("%d read head(s)/rest(s) are neither written nor counted not-written" % unacc)
    for reason, n in c["not_written"].items():
        if str(reason).strip().lower() in UNNAMED:
            bad.append("%d row(s) not written under an unnamed reason %r" % (n, reason))
        if n < 0:
            bad.append("reason %r counted %d" % (reason, n))
    if sum(c["not_written"].values()) != c["not_written_total"]:
        bad.append("reasons sum to %d, total says %d" % (sum(c["not_written"].values()), c["not_written_total"]))
    for key in ("in_red_bars", "in_partial_gaps", "in_held_bars"):
        sec = c[key]
        listed = sum(p["rows"] for p in sec["places"])
        if listed != sec["rows"]:
            bad.append("%s: %d row(s) counted, %d located by bar" % (key, sec["rows"], listed))
        if sec["rows"] and not all(p.get("page") is not None and p.get("system") is not None
                                   and p.get("cell") is not None for p in sec["places"]):
            bad.append("%s: a bar has no (page, system, cell)" % key)
    # a bar-level row is counted not-written under ONE reason: the bars listed must equal that reason's count
    for key, reason in (("in_held_bars", "bar_does_not_add_up"), ("in_partial_gaps", "unread_gap_in_partial_bar")):
        if c[key]["rows"] != c["not_written"].get(reason, 0):
            bad.append("%s: %d row(s) in bars but %d counted not written under %r (a gap/held head counted as written?)"
                       % (key, c[key]["rows"], c["not_written"].get(reason, 0), reason))
    if c["in_red_bars"]["rows"] > c["written"]:
        bad.append("more rows in red bars (%d) than written (%d)" % (c["in_red_bars"]["rows"], c["written"]))
    if c["written_guessed"] > c["written"]:
        bad.append("more GUESSED (%d) than written (%d)" % (c["written_guessed"], c["written"]))
    return bad


def _places(places: Sequence[Dict[str, Any]], limit: int = 12) -> str:
    one = ["p%s s%s c%s%s" % (p["page"], p["system"], p["cell"], "" if p["rows"] == 1 else " x%d" % p["rows"]) for p in places]
    return ", ".join(one[:limit]) + (" ... +%d bars" % (len(one) - limit) if len(one) > limit else "")


def block(plate: str, pages: Sequence[int], out: Dict[str, Any], ink: Optional[str] = None) -> str:
    rep = out["report"]
    c = rep["conservation"]
    red = c["in_red_bars"]
    plain_outside = c["written"] - c["written_guessed"] - (red["rows"] - red["guessed"])
    gues_outside = c["written_guessed"] - red["guessed"]
    unacc = c["read_by_adjudicate"] - c["written"] - c["not_written_total"]
    unboxed = rep["balance"]["unboxed_rests_placed"]
    L = ["%s  pages %s  (ADJUDICATE..EXPORT replay of the saved gather, %.0f s)" % (plate.upper(), ",".join(str(p) for p in pages), out["seconds"])]
    L.append("  read by ADJUDICATE (heads + rests)      %6d%s" % (c["read_by_adjudicate"],
             "   (incl. %d rests read off unboxed ink)" % unboxed if unboxed else ""))
    L.append("  written plain                           %6d" % plain_outside)
    L.append("  written GUESSED (blue)                  %6d" % gues_outside)
    L.append("  written INSIDE a red bar                %6d   in %d bars: %s" % (red["rows"], len(red["places"]), _places(red["places"]) or "-"))
    gap, held = c["in_partial_gaps"], c["in_held_bars"]
    L.append("  inside a partial-bar gap (not written)  %6d   in %d bars: %s" % (gap["rows"], len(gap["places"]), _places(gap["places"]) or "-"))
    L.append("  inside a held bar (not written)         %6d   in %d bars: %s" % (held["rows"], len(held["places"]), _places(held["places"]) or "-"))
    L.append("  not written, by reason (both lines above included):")
    for reason, n in sorted(c["not_written"].items(), key=lambda kv: -kv[1]):
        L.append("      %6d  %s" % (n, reason))
    if not c["not_written"]:
        L.append("           0  -")
    L.append("  UNACCOUNTED (must be 0)                 %6d" % unacc)
    L.append("  places located (bars add up to counters)  %s" % ("yes" if c["located"] else "NO"))
    L.append("  ink never boxed: outside this count     %s" % (ink or "not measured (--ink runs claim_readout on this slice)"))
    problems = check(rep)
    L.append("  invariant: %s" % ("HOLDS" if not problems else "FAILS -- " + "; ".join(problems)))
    return "\n".join(L)


def ink_line(plate: str, pages: Sequence[int], tag: str) -> str:
    """The plate's unclaimed-ink share from `claim_readout` on the same slice; never a guess."""
    try:
        from . import claim_readout as CR
        rep = CR.run("%s:%s" % (plate, tag), list(pages), truth=None, tiles=None, out=None, log=lambda *_: None)
        tot = rep["total"]
        sp = tot["state_px"]
        unc = sum(v for k, v in sp.items() if k.startswith(("unclaimed", "refused", "residue", "weak_claim", "debris", "outside_cells")))
        return "%d of %d ink px in claim_readout's unclaimed/debris bucket (%.1f%%; ink, not a note count), pages %s" % (unc, tot["ink_px"], 100.0 * unc / max(1, tot["ink_px"]), list(pages))
    except Exception as e:           # a failed measure is "not measured", never a number
        return "not measured (%s: %s)" % (type(e).__name__, str(e)[:80])


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="conservation", description=__doc__.split("\n")[2].strip())
    ap.add_argument("--plates", default="litolff,brahms")
    ap.add_argument("--pages", default="", help="comma list, applied to every plate asked (default: per plate, %s)" % DEFAULT_PAGES)
    ap.add_argument("--tag", default=DEFAULT_TAG)
    ap.add_argument("--ink", action="store_true", help="also run claim_readout on the same slice (needs the page render + cell map)")
    ap.add_argument("--save", default=None, help="write the exported MusicXML per plate to DIR (for the byte-identity control)")
    a = ap.parse_args(argv)
    os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
    rc = 0
    for plate in [p for p in a.plates.split(",") if p]:
        pages = [int(x) for x in a.pages.split(",") if x] or DEFAULT_PAGES[plate]
        rec = load_pages(plate, pages, a.tag)
        from . import export as E
        try:
            out = export_pages(rec)
        except E.Unbalanced as e:
            print("%s  pages %s\n  UNBALANCED -- the export raised: %s" % (plate.upper(), pages, str(e)[:400]))
            rc = 1
            continue
        if a.save:
            d = pathlib.Path(a.save)
            d.mkdir(parents=True, exist_ok=True)
            (d / ("%s.musicxml" % plate)).write_text(out["xml"])
        print(block(plate, pages, out, ink_line(plate, pages, a.tag) if a.ink else None))
        rc = rc or (1 if check(out["report"]) else 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
