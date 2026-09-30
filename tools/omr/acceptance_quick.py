"""ROADMAP 1.6 / 1.6b — the SMALL re-gather (Sean 2026-09-30, CLAUDE.md §6b).

    python3 -m tools.omr.acceptance_quick --doc beethoven5-litolff
    python3 -m tools.omr.acceptance_quick --doc brahms1-breitkopf
    python3 -m tools.omr.acceptance_quick --doc beethoven5-litolff --against <record.json>
    python3 -m tools.omr.acceptance_quick --doc beethoven5-litolff --full
    python3 -m tools.omr.acceptance_quick --self-control
    python3 -m tools.omr.acceptance_quick --corrupted-control

ITERATION ONLY. A whole-movement re-gather (the FULL re-gather,
`benchmarks/acceptance/overnight/regather_20260930.sh`) takes hours and is
the only thing that feeds `benchmarks/acceptance/current.json`
(`tools.omr.acceptance`, roadmap 1.3) — carries, identity and roster effects
only show up there. This tool gathers from one acceptance scan document's
movement's FIRST PAGE through its fixed count page (Litolff p3 or Breitkopf
p1, `manifest.json`'s `count_page.pdf_page_index`) on the CURRENT tree, in
minutes, so a lane can tell whether a change helped BEFORE spending a
whole-movement run on it.

DEFAULT MODE (ROADMAP 1.6b, Sean 2026-09-30): *"I don't want to chase down
where it is getting lost before we refine what we are reading in the first
2 stages"* and *"for all of our initial tests I want to be comparing the
output of just the first two stages."* The gather stops `--through
adjudicate` — no EVALUATE, no INFER, no EXPORT — and this tool reports, for
the COUNT PAGE only, what GATHER and ADJUDICATE read and decided, per symbol
family: gathered boxes; kept vs refused, with each refusal reason and its
count; for noteheads, owner decided/abstained and duration decided/narrowed/
abstained by reason; staff position observed/abstained and the clef decided
on each staff; meter per system, decided/abstained with its reason. The
counting is `tools.omr.staged.readout`'s own `Run`/`Glyph`/`adjudicate_status`
— this module aggregates their answers, it does not re-read the record.
The picture page is `readout html`, unmodified. Nothing here exports a file
or touches the reference encoding.

`--full` (ROADMAP 1.6's original shape): once a change looks right at the
first two stages, `--full` re-gathers through INFER, exports MusicXML +
LilyPond + a compiled PDF with the SAME CLI (`tools.omr.staged`'s own
`--musicxml --lilypond --pdf`), and additionally reports:
    (a) the page proxies, reusing `tools.omr.acceptance.machine_proxies`
        against the export's own coverage report — never re-derived;
    (b) the stage-readout HTML for the page (ROADMAP 1.5);
    (c) print vs ours for the page's systems, reusing
        `tools.omr.acceptance.build_side_by_side`;
    (d) a per-part, per-bar score against the reference encoding for the
        page's printed bar range (`tools.omr.acceptance_barscore`).
This is the second view, for after the first-two-stages read is trusted —
not where an initial test of a change should start (DECISIONS 2026-09-30).

`--against <record.json>` reads a SECOND already-built record for the SAME
page (from another tree/commit — built by a second `--doc ...` run, or an
older tree's own `tools.omr.staged` CLI, whose `--out` you point here) and
adds the GATHER+ADJUDICATE readout diff (ROADMAP 1.5, `--force` since the
two records come from different commits — provenance is reported, never
silently assumed equal). In default mode both records being compared are
GATHER+ADJUDICATE (this tool's arm always is; the base may go further and
the diff simply never reads past ADJUDICATE). `--full --against` additionally
reports the change in the page proxies and the per-bar score, as before.

Writes `benchmarks/acceptance/quick/<doc>-<date>.json` and one HTML index
linking the readout, the side-by-side (full mode) and the per-bar report
(full mode). Never writes `benchmarks/acceptance/current.json` — that number
is the FULL RE-GATHER's, only (`tools.omr.acceptance`, roadmap 1.3) — not to
be confused with this module's `--full`, which is still the SMALL re-gather,
just carried one page further than the default.
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
import os
import subprocess
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr import acceptance as ACC  # noqa: E402
from tools.omr.acceptance_barscore import (  # noqa: E402
    align_and_score, parse_part_bars, sum_scores,
)
from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

QUICK_DIR = REPO / "benchmarks" / "acceptance" / "quick"
WORKS_JSON_PATH = REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"

DEFAULT_STEP_TIMEOUT_S = 900.0


class QuickError(RuntimeError):
    """A whole-run refusal (bad doc id, no works.json row, gather failed)."""


# ─────────────────────────────────────────────────────────────────────────
# per-document family maps: (our exported part id(s)) -> (reference part ids)
#
# Hand-built, once, from each page's own margin labels (CLAUDE.md §10: "the
# condensed count cannot come from the page") and the exported part-list —
# the same kind of table `benchmarks/omr-notehead-precision-2026-09/probe/
# 2.40/dyad_measure.py`'s own `FAMILIES` used, generalised to every family
# on the page rather than just the condensed winds. A part our exporter
# left at its coordinate default (`Staff p…`, `tools.omr.acceptance.
# parts_named`'s own detector) is named here by its PRINTED POSITION, read
# off `page.n_staves_note` in works.json (never guessed): Litolff system 1
# margins run Fl/Ob/Cl/Fag/Cor/Tr/Tp then Vln I/Vln II/Viola/Vc-e-Cb;
# Breitkopf's two unnamed staves are its two Horn crooks (Hr.(C), Hr.(Es)),
# and its two "Violin"-named parts are Violin I/II in print order.
# ─────────────────────────────────────────────────────────────────────────

_FAMILY_MAPS: Dict[str, Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...]]]] = {
    "beethoven5-litolff": {
        # family: (our part ids, reference part ids)
        "Flute":                (("P1",), ("P1", "P2")),
        "Oboe":                 (("P2",), ("P3", "P4")),
        "Clarinet":             (("P3",), ("P5", "P6")),
        "Bassoon":              (("P4",), ("P7", "P8")),
        "Horn":                 (("P5",), ("P9", "P10")),
        "Trumpet":              (("P6",), ("P11", "P12")),
        "Timpani":              (("P7",), ("P13",)),
        "Violin I":             (("P8",), ("P14",)),
        "Violin II":            (("P9",), ("P15",)),
        "Viola":                (("P10",), ("P16",)),
        "Violoncello e Basso":  (("P11",), ("P17", "P18")),
    },
    "brahms1-breitkopf": {
        "Flute":      (("P1",), ("P1", "P2")),
        "Oboe":       (("P2",), ("P3", "P4")),
        "Clarinet":   (("P3",), ("P5", "P6")),
        "Bassoon":    (("P4",), ("P7", "P8")),
        "Contrabassoon": (("P5",), ("P9",)),
        "Horn (C)":   (("P6",), ("P10", "P11")),
        "Horn (Es)":  (("P7",), ("P12", "P13")),
        "Trumpet":    (("P8",), ("P14", "P15")),
        "Timpani":    (("P9",), ("P16",)),
        "Violin I":   (("P10",), ("P17",)),
        "Violin II":  (("P11",), ("P18",)),
        "Viola":      (("P12",), ("P19",)),
        "Violoncello": (("P13",), ("P20",)),
        "Contrabass": (("P14",), ("P21",)),
    },
}


# ─────────────────────────────────────────────────────────────────────────
# small utilities
# ─────────────────────────────────────────────────────────────────────────

def _load_works_row(row_id: str) -> Dict[str, Any]:
    rows = json.loads(WORKS_JSON_PATH.read_text()).get("rows", [])
    row = next((r for r in rows if r.get("row_id") == row_id), None)
    if row is None:
        raise QuickError(f"no works.json row {row_id!r}")
    return row


def _reference_root(catalog_path: str) -> ET.Element:
    """A `reference.catalog_path`-named `.mxl` -> its `score.xml` root,
    parsed straight out of the zip (no unzip-to-tmp step, unlike the ad hoc
    `/tmp/scratch_2_40/score.xml` this generalises — CLAUDE.md §8: a
    `source_kind: encoding` truth file is read here, by MEASUREMENT code
    only, never by the pipeline)."""
    path = library_root() / catalog_path
    if not path.is_file():
        raise QuickError(f"no reference encoding at {path}")
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".xml")
                 and "container" not in n.lower()]
        if not names:
            raise QuickError(f"{path} has no score.xml-like member")
        return ET.fromstring(zf.read(names[0]))


def _our_root(xml_text: str) -> ET.Element:
    return ET.fromstring(xml_text)


def _part_by_id(root: ET.Element, part_id: str) -> Optional[ET.Element]:
    return root.find(f"part[@id='{part_id}']")


def _union_bars(part_ids: Sequence[str], root: ET.Element
               ) -> Dict[str, List]:
    """Several parts' bar->events dicts, unioned per bar (a condensed
    family on the REFERENCE side, e.g. Flute 1 + Flute 2 both printed on
    one Litolff staff)."""
    merged: Dict[str, List] = {}
    for pid in part_ids:
        part_el = _part_by_id(root, pid)
        if part_el is None:
            continue
        for bar, events in parse_part_bars(part_el).items():
            merged.setdefault(bar, []).extend(events)
    return merged


def _bar_range(works_row: Dict[str, Any]) -> Tuple[int, int]:
    window = works_row.get("window") or {}
    lo, hi = window.get("first_ref_measure"), window.get("last_ref_measure")
    if lo is None or hi is None:
        raise QuickError(f"works.json row {works_row.get('row_id')!r} has no window")
    return int(lo), int(hi)


_PDF_PAGES_RE = __import__("re").compile(r"pdf pages? (\d+)-(\d+)")


def first_movement_page(doc: Dict[str, Any]) -> int:
    """The PDF page index the document's MOVEMENT starts on — never the
    count page itself. Read from the manifest, never guessed: Litolff
    names it structurally (`doc["whole_movement"]["pages"]`, e.g.
    `"1-16"`); Brahms names it only in prose inside `caveats` (e.g. "Whole
    movement, pdf pages 0-26 (27 pages)"), so that is parsed as a fallback.
    Manager review, 2026-09-30: a lone count page loses the meter/key CARRY
    from earlier pages (DECISIONS 2026-09-28: a meter or key prints at the
    movement's start and HOLDS) — gathering from here through the count
    page is the fix, not a cosmetic change."""
    wm = doc.get("whole_movement") or {}
    pages = wm.get("pages")
    if pages and "-" in pages:
        return int(pages.split("-")[0])
    for cav in doc.get("caveats") or ():
        m = _PDF_PAGES_RE.search(cav)
        if m:
            return int(m.group(1))
    raise QuickError(f"{doc['id']!r} names no movement start page in the "
                     "manifest (whole_movement.pages or a caveats line)")


# ─────────────────────────────────────────────────────────────────────────
# ROADMAP 1.6b: the GATHER+ADJUDICATE stage summary, per symbol family
#
# Built entirely on `tools.omr.staged.readout`'s own reading of a record
# (`Run`, `Glyph`, `adjudicate_status`) — this aggregates what that module
# already exposes, it never re-parses `record.json` (CLAUDE.md rule 9: no
# derived check restates a record's own counting). The picture page for the
# same record is `readout html`, unmodified.
# ─────────────────────────────────────────────────────────────────────────

def _key_nums(key: str) -> Tuple[int, ...]:
    """Sort subjects numerically (`staff/3/0/10` after `staff/3/0/2`),
    without reaching into `readout`'s own private sort helper."""
    try:
        return tuple(int(p) for p in key.split("/")[1:])
    except ValueError:
        return ()


def _verdict_brief(v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if v is None:
        return {"outcome": "no_verdict"}
    return {"outcome": v.get("outcome"), "value": v.get("value"),
           "reason": v.get("reason")}


def stage_summary(run: RD.Run, page_index: int) -> Dict[str, Any]:
    """What GATHER + ADJUDICATE read and decided for ONE page, per symbol
    family, plus the two decisions a family count cannot show: the clef on
    each staff and the meter on each system (both filed on the STAFF/SYSTEM
    subject, never the glyph).
    """
    where = RD.Where(page=page_index)
    glyphs = [g for g in run.glyphs.values() if where.admits(g.key)]

    by_family: Dict[str, List[RD.Glyph]] = collections.defaultdict(list)
    for g in glyphs:
        by_family[g.family or f"class:{g.cls}"].append(g)

    families: Dict[str, Any] = {}
    for family, gs in sorted(by_family.items()):
        status_counts: collections.Counter = collections.Counter()
        reasons: collections.Counter = collections.Counter()
        for g in gs:
            status, why = RD.adjudicate_status(run, g)
            status_counts[status] += 1
            if status != RD.KEPT:
                reasons[(status, why[0] if why else "(no reason given)")] += 1
        entry: Dict[str, Any] = {
            "gathered": len(gs),
            "status": dict(sorted(status_counts.items())),
            "reasons": {f"{s}: {r}": n
                       for (s, r), n in sorted(reasons.items(),
                                               key=lambda kv: -kv[1])},
        }
        if family == "note":
            owner = collections.Counter()
            owner_reasons: collections.Counter = collections.Counter()
            duration = collections.Counter()
            duration_reasons: collections.Counter = collections.Counter()
            position = collections.Counter()
            position_reasons: collections.Counter = collections.Counter()
            for g in gs:
                own = run.standing(g.key, Q.GLYPH_OWNER, "ADJUDICATE")
                oc = own["outcome"] if own else "no_verdict"
                owner[oc] += 1
                if own and oc != "decided":
                    owner_reasons[own.get("reason")] += 1
                dur = run.standing(g.key, Q.DURATION, "ADJUDICATE")
                dc = dur["outcome"] if dur else "no_verdict"
                duration[dc] += 1
                if dur and dc != "decided":
                    duration_reasons[dur.get("reason")] += 1
                obs = run.obs_at(g.key, Q.NOTEHEAD_STAFF_POSITION)
                abst = [r for s, k, r in run.rows_at(g.key)
                       if s == "GATHER" and k == "abstention"
                       and r["quantity"] == Q.NOTEHEAD_STAFF_POSITION]
                if obs:
                    position["observed"] += 1
                elif abst:
                    position["abstained"] += 1
                    position_reasons[abst[0].get("reason")] += 1
                else:
                    position["no_reading"] += 1
            entry["owner"] = {"by_outcome": dict(owner),
                              "reasons": dict(owner_reasons)}
            entry["duration"] = {"by_outcome": dict(duration),
                                 "reasons": dict(duration_reasons)}
            entry["staff_position"] = {"by_outcome": dict(position),
                                       "reasons": dict(position_reasons)}
        families[family] = entry

    staff_keys = sorted({g.staff_key for g in glyphs}, key=_key_nums)
    clef_by_staff = {sk: _verdict_brief(run.standing(sk, Q.CLEF, "ADJUDICATE"))
                     for sk in staff_keys}

    system_keys = sorted({f"system/{g.page}/{g.system}" for g in glyphs},
                        key=_key_nums)
    meter_by_system = {sk: _verdict_brief(run.standing(sk, Q.METER, "ADJUDICATE"))
                       for sk in system_keys}

    return {"page": page_index, "gathered_total": len(glyphs),
           "families": families, "clef_by_staff": clef_by_staff,
           "meter_by_system": meter_by_system}


def render_stage_table(doc_id: str, summary: Dict[str, Any]) -> str:
    """A compact text table — one line per family, then clef/meter."""
    L = [f"GATHER+ADJUDICATE stage summary -- {doc_id} page {summary['page']}"
        f" ({summary['gathered_total']} boxes gathered)",
        f"{'family':<14}{'gathered':>9}{'kept':>7}{'refused':>9}"
        f"{'narrowed':>10}{'abstained':>11}{'given_away':>12}{'undecided':>11}"]
    for family, entry in sorted(summary["families"].items()):
        st = entry["status"]
        L.append(f"{family:<14}{entry['gathered']:>9}{st.get(RD.KEPT, 0):>7}"
                f"{st.get(RD.REFUSED, 0):>9}{st.get(RD.NARROWED, 0):>10}"
                f"{st.get(RD.ABSTAINED, 0):>11}{st.get(RD.GIVEN_AWAY, 0):>12}"
                f"{st.get(RD.UNDECIDED, 0):>11}")
        for reason, n in entry["reasons"].items():
            L.append(f"    {n:>4}x  {reason}")
    note = summary["families"].get("note")
    if note:
        L.append("")
        L.append(f"note owner:    {note['owner']['by_outcome']}"
                f"  reasons {note['owner']['reasons']}")
        L.append(f"note duration: {note['duration']['by_outcome']}"
                f"  reasons {note['duration']['reasons']}")
        L.append(f"note position: {note['staff_position']['by_outcome']}"
                f"  reasons {note['staff_position']['reasons']}")
    L.append("")
    L.append("clef by staff:")
    for sk, v in summary["clef_by_staff"].items():
        L.append(f"  {sk}: {v}")
    L.append("meter by system:")
    for sk, v in summary["meter_by_system"].items():
        L.append(f"  {sk}: {v}")
    return "\n".join(L) + "\n"


# ─────────────────────────────────────────────────────────────────────────
# step 1: gather from the MOVEMENT'S FIRST PAGE through the count page
# ─────────────────────────────────────────────────────────────────────────

def gather_count_page(doc: Dict[str, Any], out_dir: Path, *,
                      weights: str = "auto",
                      step_timeout_s: float = DEFAULT_STEP_TIMEOUT_S,
                      full: bool = False,
                      ) -> Dict[str, Any]:
    """`python3 -m tools.omr.staged <pdf> --pages <first_page>-<count page>
    --weights auto --out [--musicxml --lilypond --pdf | --through adjudicate]`,
    timed. NOT just the count page alone (that was this tool's first
    version, and it is wrong: a lone page's `Q.METER`/`Q.KEY_SIGNATURE` have
    no carry to read, so the exporter either falsely holds out nothing where
    the whole movement holds out plenty, or falsely holds out everything —
    manager review, 2026-09-30, proved against the committed whole-movement
    records). The SAME CLI the FULL re-gather and `tools.omr.acceptance`
    both build on — nothing here re-implements a gather.

    `full=False` (the default, ROADMAP 1.6b, Sean 2026-09-30: *"for all of
    our initial tests I want to be comparing the output of just the first
    two stages"*): `--through adjudicate` — no EVALUATE/INFER/EXPORT, so no
    `--musicxml`/`--lilypond`/`--pdf` (the CLI refuses those together with
    `--through`). `full=True`: today's whole-pipeline gather plus export,
    exactly as this tool's first (1.6) version always ran."""
    pdf_path = ACC.resolve_path(doc["pdf"])
    if pdf_path is None or not pdf_path.is_file():
        raise QuickError(f"no PDF at {doc.get('pdf')}")
    page_index = doc["count_page"]["pdf_page_index"]
    start_page = first_movement_page(doc)
    pages_spec = f"{start_page}-{page_index}" if start_page != page_index else str(page_index)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{doc['id']}-p{page_index}"
    record_path = out_dir / f"{stem}.record.json"
    xml_path = out_dir / f"{stem}.musicxml"
    ly_path = out_dir / f"{stem}.ly"
    pdf_out_path = out_dir / f"{stem}.pdf"

    cmd = [sys.executable, "-m", "tools.omr.staged", str(pdf_path),
           "--pages", pages_spec, "--weights", weights,
           "--out", str(record_path)]
    if full:
        cmd += ["--musicxml", str(xml_path), "--lilypond", str(ly_path),
               "--pdf", str(pdf_out_path)]
    else:
        cmd += ["--through", "adjudicate"]
    env = dict(os.environ)
    env.setdefault("OMR_DIRECTION_TEXT_SCAN_GATE", "1")
    env.setdefault("OMR_SURYA_KEEP_ALIVE", "0")

    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(REPO), env=env, capture_output=True,
                          text=True, timeout=step_timeout_s)
    wall_time_s = round(time.time() - t0, 3)
    log_path = out_dir / f"{stem}.gather.log"
    log_path.write_text((proc.stdout or "") + "\n" + (proc.stderr or ""))

    ok = proc.returncode == 0 and record_path.is_file() and (
        not full or xml_path.is_file())
    return {
        "ok": ok, "wall_time_s": wall_time_s, "page_index": page_index,
        "start_page": start_page, "pages_gathered": pages_spec, "full": full,
        "returncode": proc.returncode,
        "record_path": str(record_path),
        "xml_path": str(xml_path) if full and xml_path.is_file() else None,
        "ly_path": str(ly_path) if full and ly_path.is_file() else None,
        "pdf_path": str(pdf_out_path) if full and pdf_out_path.is_file() else None,
        "log_path": str(log_path),
        "log_tail": ((proc.stdout or "") + (proc.stderr or ""))[-2000:],
    }


# ─────────────────────────────────────────────────────────────────────────
# step 4: per-part, per-bar score against the reference encoding
# ─────────────────────────────────────────────────────────────────────────

def score_document(doc_id: str, xml_text: str, works_row: Dict[str, Any],
                   export_report: Dict[str, Any], *,
                   absolute_numbering: bool = True) -> Dict[str, Any]:
    """`absolute_numbering=True` (the default, and what `run_quick` always
    uses since the fix below): the gather ran from the MOVEMENT'S FIRST
    PAGE through the count page, so MusicXML's own `<measure number="N">`
    already IS the reference's bar number — a measure count is never lost
    or restarted mid-movement, so no offset arithmetic is needed or safe to
    guess. `absolute_numbering=False` is kept only for scoring an EXISTING
    export that was built some other way (e.g. a whole-movement record's
    own musicxml, which is ALSO absolute — see the docstring note below —
    or, historically, a lone-page-only gather whose local numbering
    restarts at 1 and needs `bar_lo - 1` added back; that lone-page mode
    was found to silently drop the meter/key CARRY from earlier pages
    (DECISIONS 2026-09-30, manager review) and `run_quick` no longer uses
    it)."""
    family_map = _FAMILY_MAPS.get(doc_id)
    if family_map is None:
        return {"status": "skipped",
               "reason": f"no family map declared for {doc_id!r}"}

    bar_lo, bar_hi = _bar_range(works_row)
    ref_root = _reference_root(works_row["reference"]["catalog_path"])
    our_root = _our_root(xml_text)

    # bars the exporter itself held out, so this scorer skips the SAME bars
    # the machine proxies already charge for, rather than double-counting
    # them as a new kind of miss (CLAUDE.md §6a: `bars_held_out_sum`). Each
    # entry names a LOCAL measure number and OUR part id (export.py's own
    # per-(part, measure) unit); a family-level held set is a mapping
    # rebuilt below, once the reference-number offset is known.
    held_by_part: Dict[str, set] = {}
    for h in (export_report.get("bars_held_out_sum") or {}).get("held") or ():
        part = h.get("part")
        measure = h.get("measure")
        if part is not None and measure is not None:
            held_by_part.setdefault(part, set()).add(str(measure))

    # `offset`: our bar N == reference bar N + offset. Zero under absolute
    # numbering (the movement's own bar count, unbroken from page 1); only
    # the deprecated lone-page mode needs `bar_lo - 1` added back.
    offset = 0 if absolute_numbering else (bar_lo - 1)

    per_family: Dict[str, Any] = {}
    all_scores = []
    worst: List[Dict[str, Any]] = []
    total_comparable = 0
    total_skipped = 0

    for family, (our_ids, ref_ids) in family_map.items():
        ref_bars = _union_bars(ref_ids, ref_root)
        our_bars = _union_bars(our_ids, our_root)
        # translate: this family's bar_numbers are REFERENCE numbers;
        # our_bars is keyed by OUR local numbers (1-based on the page)
        our_bars_by_ref_num = {str(int(k) + offset): v for k, v in our_bars.items()}
        held_locals = set()
        for pid in our_ids:
            held_locals |= held_by_part.get(pid, set())
        held = {str(int(m) + offset) for m in held_locals}
        bar_numbers = [str(b) for b in range(bar_lo, bar_hi + 1)]
        scores, skipped = align_and_score(ref_bars, our_bars_by_ref_num,
                                          bar_numbers, held_out=held)
        total_comparable += len(scores)
        total_skipped += len(skipped)
        family_total = sum_scores(list(scores.values())) if scores else None
        per_family[family] = {
            "comparable_bars": len(scores), "skipped_bars": len(skipped),
            "skipped": skipped,
            "total": family_total.as_dict() if family_total else None,
            "by_bar": {bar: s.as_dict() for bar, s in scores.items()},
        }
        for bar, s in scores.items():
            all_scores.append(s)
            n_wrong = s.pitch_wrong + s.duration_wrong + s.missing + s.extra
            if n_wrong:
                worst.append({"family": family, "bar": bar, "n_wrong": n_wrong,
                             **s.as_dict()})

    worst.sort(key=lambda d: -d["n_wrong"])
    totals = sum_scores(all_scores).as_dict() if all_scores else None
    return {
        "status": "ok", "bar_range": [bar_lo, bar_hi],
        "comparable_cells": total_comparable, "skipped_cells": total_skipped,
        "totals": totals, "per_family": per_family,
        "worst_10": worst[:10],
    }


# ─────────────────────────────────────────────────────────────────────────
# whole small-re-gather orchestration, per document
# ─────────────────────────────────────────────────────────────────────────

def _readout_html(record_path: str, page_index: int, out_path: Path, *,
                  against: Optional[str] = None) -> Dict[str, Any]:
    argv = ["html", record_path, "--page", str(page_index), "--out", str(out_path)]
    if against:
        argv += ["--against", against, "--force"]
    try:
        rc = RD.main(argv)
        return {"ok": rc == 0, "path": str(out_path) if out_path.is_file() else None}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}


def _readout_diff(base_record: str, arm_record: str, out_path: Path
                  ) -> Dict[str, Any]:
    argv = ["diff", base_record, arm_record, "--force", "--out", str(out_path)]
    try:
        rc = RD.main(argv)
        # `readout diff`'s own convention (`_cmd_diff`): 0 = no differences,
        # 1 = differences found (the USUAL, expected case for two different
        # trees), 2 = a hard refusal (NoGatheredGlyphs/ProvenanceRefused).
        # Only 2 is a failure here.
        return {"ok": rc in (0, 1), "differences_found": rc == 1,
               "path": str(out_path) if out_path.is_file() else None}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}


def run_quick(doc_id: str, *, weights: str = "auto",
             against_record: Optional[str] = None,
             step_timeout_s: float = DEFAULT_STEP_TIMEOUT_S,
             out_root: Path = QUICK_DIR,
             full: bool = False) -> Dict[str, Any]:
    """`full=False` (the default, ROADMAP 1.6b): GATHER+ADJUDICATE only —
    `stage_summary` plus the readout HTML/diff, nothing exported. `full=True`
    (ROADMAP 1.6's original shape): also exports and reports the page
    proxies, print-vs-ours and the per-part per-bar score."""
    manifest = ACC.load_manifest()
    doc = next((d for d in manifest["documents"] if d["id"] == doc_id), None)
    if doc is None:
        raise QuickError(f"no document {doc_id!r} in manifest.json")
    if doc["kind"] != "scan":
        raise QuickError("the small re-gather is for the two SCAN count "
                         "pages only (ROADMAP 1.6) — the engraved document "
                         "already has its own 3-page/3-minute test")
    works_row_id = doc["count_page"].get("works_row_id")
    if not works_row_id:
        raise QuickError(f"{doc_id!r} has no works_row_id in the manifest")
    works_row = _load_works_row(works_row_id) if full else None

    out_dir = out_root / "out" / doc_id
    gather = gather_count_page(doc, out_dir, weights=weights,
                               step_timeout_s=step_timeout_s, full=full)
    result: Dict[str, Any] = {"id": doc_id, "gather": gather, "full": full}
    if not gather["ok"]:
        result["status"] = "error"
        return result

    page_index = gather["page_index"]
    run = RD.load_run(gather["record_path"])
    result["stage_summary"] = stage_summary(run, page_index)

    readout_path = out_dir / f"{doc_id}-p{page_index}.readout.html"
    result["readout_html"] = _readout_html(gather["record_path"], page_index,
                                           readout_path,
                                           against=against_record)

    if against_record:
        diff_path = out_dir / f"{doc_id}-p{page_index}.diff.html"
        result["against"] = {
            "record": against_record,
            "readout_diff": _readout_diff(against_record, gather["record_path"],
                                          diff_path),
        }
        try:
            base_run = RD.load_run(against_record)
            result["against"]["stage_summary"] = stage_summary(
                base_run, page_index)
        except Exception as exc:  # noqa: BLE001
            result["against"]["stage_summary_error"] = (
                f"{type(exc).__name__}: {exc}")

    if not full:
        result["status"] = "ok"
        return result

    xml_text = Path(gather["xml_path"]).read_text()
    report = json.loads((Path(gather["xml_path"]).with_name(
        Path(gather["xml_path"]).name + ".coverage.json")).read_text())

    result["machine_proxies"] = ACC.machine_proxies(xml_text, report)

    sbs_dir = out_dir / "side-by-side"
    try:
        result["side_by_side"] = ACC.build_side_by_side(doc, xml_text, sbs_dir)
    except Exception as exc:  # noqa: BLE001
        result["side_by_side"] = {"status": "error",
                                  "reason": f"{type(exc).__name__}: {exc}"}

    try:
        result["bar_score"] = score_document(doc_id, xml_text, works_row, report)
    except Exception as exc:  # noqa: BLE001
        result["bar_score"] = {"status": "error",
                               "reason": f"{type(exc).__name__}: {exc}"}

    if against_record:
        try:
            base_result_mod = __import__("tools.omr.staged.record_io",
                                         fromlist=["load_record"])
            base_result = base_result_mod.load_record(Path(against_record))
            from tools.omr.staged import export as X
            base_xml, base_report = X.to_musicxml(base_result)
            result["against"]["machine_proxies"] = ACC.machine_proxies(
                base_xml, base_report)
            # `--against` records built by an OLDER tree may predate this
            # fix and be a lone-page gather (local numbering restarts at
            # 1); detect that from the base record's OWN recorded --pages
            # rather than assume — a base gathered from the movement's
            # first page scores under `absolute_numbering=True` like the
            # arm; anything else falls back to the pre-fix offset, flagged.
            base_pages = (base_result.get("provenance", {}).get("settings", {})
                         .get("args", {}).get("pages"))
            base_absolute = (base_pages is not None
                            and str(base_pages).startswith(str(first_movement_page(doc))))
            result["against"]["bar_score"] = score_document(
                doc_id, base_xml, works_row, base_report,
                absolute_numbering=base_absolute)
            if not base_absolute:
                result["against"]["caveats"] = [
                    f"base record's own --pages was {base_pages!r}, not "
                    "starting at the movement's first page — scored with "
                    "the lone-page offset (absolute_numbering=False), not "
                    "directly comparable bar-for-bar to the arm's totals"]
        except Exception as exc:  # noqa: BLE001
            result["against"]["error"] = f"{type(exc).__name__}: {exc}"

    result["status"] = "ok"
    return result


def build_index_html(doc_id: str, result: Dict[str, Any], out_path: Path) -> None:
    def rel(p):
        if not p:
            return None
        try:
            return str(Path(p).relative_to(out_path.parent))
        except ValueError:
            return str(p)

    full = result.get("full", False)
    parts = [
        f"<h1>small re-gather — {doc_id} ({'full' if full else 'GATHER+ADJUDICATE'})</h1>",
        f"<p>gather wall time: {result['gather']['wall_time_s']}s, "
        f"page index {result['gather']['page_index']}</p>",
        "<h2>stage summary (GATHER+ADJUDICATE)</h2>",
        f"<pre>{render_stage_table(doc_id, result['stage_summary'])}</pre>",
        "<h2>stage readout</h2>",
        f"<p><a href='{rel(result.get('readout_html', {}).get('path'))}'>readout.html</a></p>",
    ]
    if "against" in result:
        parts.append("<h2>--against diff</h2>")
        parts.append(f"<p><a href='{rel(result['against']['readout_diff'].get('path'))}'>"
                    "diff.html</a></p>")
    if full:
        bs = result.get("bar_score", {})
        totals = bs.get("totals") or {}
        mp = result.get("machine_proxies", {})
        nrf = mp.get("notes_reaching_file", {})
        parts += [
            "<h2>(a) page proxies</h2>",
            f"<p>notes reaching file: {nrf.get('n')} / {nrf.get('of')} "
            f"({nrf.get('fraction')})</p>",
            f"<p>held out: {mp.get('held_out', {})}</p>",
            f"<p>unread bars: {mp.get('unread_bars', {})}</p>",
            f"<p>parts named: {mp.get('parts_named', {})}</p>",
            "<h2>(c) print vs ours</h2>",
            f"<p>{result.get('side_by_side')}</p>",
            "<h2>(d) per-part per-bar score vs reference encoding</h2>",
            f"<p>bar range {bs.get('bar_range')}, comparable cells "
            f"{bs.get('comparable_cells')}, skipped {bs.get('skipped_cells')}</p>",
            f"<p>totals: {totals}</p>",
            "<h3>worst 10 cells</h3>",
            "<ul>" + "".join(f"<li>{w}</li>" for w in bs.get("worst_10", [])) + "</ul>",
        ]
    out_path.write_text("\n".join(parts))


# ─────────────────────────────────────────────────────────────────────────
# proof controls (CLAUDE.md rule 7: a control must be able to fail)
# ─────────────────────────────────────────────────────────────────────────

def self_control(doc_id: str) -> Dict[str, Any]:
    """Score the reference encoding against ITSELF: every comparable cell
    must come back with zero pitch_wrong/duration_wrong/missing/extra."""
    manifest = ACC.load_manifest()
    doc = next(d for d in manifest["documents"] if d["id"] == doc_id)
    works_row = _load_works_row(doc["count_page"]["works_row_id"])
    ref_root = _reference_root(works_row["reference"]["catalog_path"])
    bar_lo, bar_hi = _bar_range(works_row)
    family_map = _FAMILY_MAPS[doc_id]
    bad = {}
    for family, (_our_ids, ref_ids) in family_map.items():
        ref_bars = _union_bars(ref_ids, ref_root)
        bar_numbers = [str(b) for b in range(bar_lo, bar_hi + 1)]
        scores, _skipped = align_and_score(ref_bars, ref_bars, bar_numbers)
        for bar, s in scores.items():
            if s.pitch_wrong or s.duration_wrong or s.missing or s.extra:
                bad[f"{family}/{bar}"] = s.as_dict()
    return {"ok": not bad, "bad_cells": bad}


def corrupted_control(doc_id: str, family: str, bar: str) -> Dict[str, Any]:
    """Shift one (family, bar) cell's pitches a diatonic step and require
    the scorer to flag EXACTLY that cell as pitch_wrong."""
    from tools.omr.acceptance_barscore import Event
    manifest = ACC.load_manifest()
    doc = next(d for d in manifest["documents"] if d["id"] == doc_id)
    works_row = _load_works_row(doc["count_page"]["works_row_id"])
    ref_root = _reference_root(works_row["reference"]["catalog_path"])
    bar_lo, bar_hi = _bar_range(works_row)
    our_ids, ref_ids = _FAMILY_MAPS[doc_id][family]
    ref_bars = _union_bars(ref_ids, ref_root)

    ladder = {"C": "D", "D": "E", "E": "F", "F": "G", "G": "A", "A": "B", "B": "C"}
    corrupted = dict(ref_bars)
    shifted = []
    for e in ref_bars.get(bar, []):
        if e.pitch is None:
            shifted.append(e)
            continue
        step, rest = e.pitch[0], e.pitch[1:]
        shifted.append(Event(e.onset, e.duration, ladder[step] + rest, e.voice))
    corrupted[bar] = shifted

    bar_numbers = [str(b) for b in range(bar_lo, bar_hi + 1)]
    scores, _skipped = align_and_score(ref_bars, corrupted, bar_numbers)
    flagged = {b: s.as_dict() for b, s in scores.items()
              if s.pitch_wrong or s.duration_wrong or s.missing or s.extra}
    return {"expected_only": bar, "flagged": flagged,
           "ok": set(flagged) == {bar} and flagged.get(bar, {}).get("pitch_wrong", 0) > 0}


# ─────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc", help="beethoven5-litolff or brahms1-breitkopf")
    ap.add_argument("--against", default=None,
                    help="a second already-built record for the SAME page, "
                         "from another tree/commit")
    ap.add_argument("--weights", default="auto")
    ap.add_argument("--full", action="store_true",
                    help="run through INFER and export a file, reporting the "
                         "page proxies, print-vs-ours and the per-part "
                         "per-bar score against the reference encoding, as "
                         "a SECOND view -- for AFTER a change looks right at "
                         "the default GATHER+ADJUDICATE stage summary "
                         "(ROADMAP 1.6b, DECISIONS 2026-09-30); whole-"
                         "movement effects (carries, identity, roster) still "
                         "need the overnight FULL re-gather, a different "
                         "thing from this flag's name")
    ap.add_argument("--self-control", action="store_true",
                    help="score the reference encoding against itself (needs --doc)")
    ap.add_argument("--corrupted-control", action="store_true",
                    help="shift one bar's pitches and check the scorer catches "
                         "exactly it (needs --doc, --family, --bar)")
    ap.add_argument("--family", default=None)
    ap.add_argument("--bar", default=None)
    ap.add_argument("--step-timeout", type=float, default=DEFAULT_STEP_TIMEOUT_S)
    ap.add_argument("--out-root", type=Path, default=QUICK_DIR)
    args = ap.parse_args(argv)

    if args.self_control:
        if not args.doc:
            print("--self-control needs --doc", file=sys.stderr)
            return 2
        out = self_control(args.doc)
        print(json.dumps(out, indent=2, default=str))
        return 0 if out["ok"] else 1

    if args.corrupted_control:
        if not (args.doc and args.family and args.bar):
            print("--corrupted-control needs --doc --family --bar", file=sys.stderr)
            return 2
        out = corrupted_control(args.doc, args.family, args.bar)
        print(json.dumps(out, indent=2, default=str))
        return 0 if out["ok"] else 1

    if not args.doc:
        print("need --doc (or --self-control / --corrupted-control)", file=sys.stderr)
        return 2

    try:
        result = run_quick(args.doc, weights=args.weights,
                           against_record=args.against,
                           step_timeout_s=args.step_timeout,
                           out_root=args.out_root, full=args.full)
    except QuickError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    date = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    summary_path = args.out_root / f"{args.doc}-{date}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(result, indent=2, default=str))

    index_path = args.out_root / "out" / args.doc / f"{args.doc}-index.html"
    build_index_html(args.doc, result, index_path)

    print(f"gather: {result['gather']['wall_time_s']}s "
         f"(pages {result['gather'].get('pages_gathered')}, "
         f"{'full' if args.full else 'GATHER+ADJUDICATE only'})")
    if "stage_summary" in result:
        print(render_stage_table(args.doc, result["stage_summary"]))
    if "against" in result and "stage_summary" in result["against"]:
        print(render_stage_table(f"{args.doc} (--against base)",
                                 result["against"]["stage_summary"]))
    print(f"wrote {summary_path}")
    print(f"wrote {index_path}")
    if args.full:
        print(json.dumps({k: v for k, v in result.items()
                          if k not in ("gather", "stage_summary")},
                         indent=2, default=str)[:4000])
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
