"""ROADMAP START HERE #2 — the NOTEHEAD FUNNEL for one staff, every stage.

Sean, 2026-09-23, on the Litolff count page (Beethoven 5 mvt 1, imslp984073,
pdf page index 3), Viola, system 1 (the upper system, printed bars 49-64):
*"there are a lot of notes on the original scan and almost nothing shows up
on our version."*

This answers WHERE THE HEADS GO, per bar, with rows that SUM:

    detector notehead boxes = written + Σ refused + (no verdict at all)

⚠️⚠️ THE REFUSAL BUCKETS ARE NOT RESTATED HERE. `export._place_notes` holds
the rule and this probe INSTRUMENTS it rather than re-deciding: `_drop` files
one refusal per head under `(page, system)` and this script hangs a logging
Counter on that call so the same event is also filed under its STAFF and its
CELL. The repo has paid for the other choice once already --
`omr-cleanup-count-2026-09/build_sheet.py` held its own copy of "the three
refusals" and reported 542 where the exporter refused 738, because two
refusals had been added since. One rule, one place, read from where it lives.

⚠️ THE CONTROL THAT CAN FAIL: this script's per-cell decomposition is summed
back up per system and compared to the exporter's OWN
`notes_not_written_by_system`, and to its flat `notes_not_written`. A
mismatch raises. Run once against a deliberately wrong page filter to see it
fail (it does: every bucket goes to zero and the assert fires).

Usage (from the worktree root):

    python3 benchmarks/omr-notehead-funnel-2026-09/probe/funnel.py \
        --record library/_shared-records/beethoven5-litolff-mvt1-whole-20260923.record.json \
        --page 3 --system 0 --staff 9 \
        --ref-part Viola --ref-first 49 --ref-last 64 \
        --out-json <scratchpad>/funnel.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as EXPORT          # noqa: E402
from tools.omr.staged.record_io import load_record      # noqa: E402
from tools.omr.yolo_detector import _class_name_to_category  # noqa: E402
from tools.library.score_library import library_root    # noqa: E402


# ─────────────────────────────────────────────────────────────────────────
# 1. Instrumenting the exporter's own refusals, per SUBJECT
# ─────────────────────────────────────────────────────────────────────────

REFUSALS: list = []          # (glyph subject, reason)
PLACED: list = []            # (glyph subject, category) — what reached a Cell
_LAST = {"sub": None}


class _LoggingCounter(collections.Counter):
    """A real Counter (so `build`'s own sum assertion still holds) that also
    files each increment against the glyph `_place_notes` is looking at."""

    def __setitem__(self, key, value):
        if value > self.get(key, 0):
            REFUSALS.append((_LAST["sub"], key))
        super().__setitem__(key, value)


class _ProbeBySystem(dict):
    def setdefault(self, key, default=None):
        if key not in self:
            super().__setitem__(key, _LoggingCounter())
        return self[key]


def instrument() -> None:
    """Wrap `_parse_subject` and `_place_notes` — no edit to `tools/`.

    `_place_notes` calls `_parse_subject` EXACTLY ONCE per `Q.GLYPH_BOX` row,
    at the top of its loop (export.py:848; the only other call sites are
    outside this function, at 513, 554 and 1121). So at the moment `_drop`
    fires, the last subject parsed IS the head being refused. Asserted below:
    every logged subject must be a glyph subject carrying a notehead or rest
    row, and the per-reason totals must equal the exporter's own.
    """
    orig_parse = EXPORT._parse_subject

    def parse(key):
        s = orig_parse(key)
        _LAST["sub"] = key
        return s

    EXPORT._parse_subject = parse

    orig_place = EXPORT._place_notes

    def place(rec, runs, by_system=None, held_out=None):
        probe = _ProbeBySystem()
        dropped = orig_place(rec, runs, by_system=probe, held_out=held_out)
        for run in runs.values():
            for ci, cell in run.cells.items():
                for det in cell.detections:
                    PLACED.append((det.get("glyph"), det.get("category")))
        if by_system is not None:
            by_system.update(probe)
        return dropped

    EXPORT._place_notes = place


# ─────────────────────────────────────────────────────────────────────────
# 2. Reading the record
# ─────────────────────────────────────────────────────────────────────────

def is_notehead_class(name: str) -> bool:
    return _class_name_to_category(name) == "notehead"


def subject_parts(key: str):
    p = key.split("/")
    return p[0], p[1:]


# ─────────────────────────────────────────────────────────────────────────
# 3. The reference encoding
# ─────────────────────────────────────────────────────────────────────────

def reference_heads(mxl: Path, part_name: str, first: int, last: int):
    """{measure number -> sounding noteheads} for one part.

    A chord member is a head. A `<rest>` is not. A grace note IS a head the
    reader sees on the page, and is counted separately so the comparison can
    be made either way.
    """
    with zipfile.ZipFile(mxl) as z:
        names = [n for n in z.namelist()
                 if n.endswith(".xml") and not n.startswith("META-INF")]
        root = None
        for n in names:
            r = ET.fromstring(z.read(n))
            if r.tag.endswith("score-partwise"):
                root = r
                break
        if root is None:
            raise SystemExit(f"no score-partwise in {mxl}")
    ids = {}
    for sp in root.iter("score-part"):
        pn = sp.find("part-name")
        ids[sp.get("id")] = (pn.text or "").strip() if pn is not None else ""
    want = [pid for pid, nm in ids.items() if nm.strip().lower() == part_name.lower()]
    if not want:
        raise SystemExit(f"part {part_name!r} not in {sorted(ids.values())}")
    out, graces = {}, {}
    for part in root.iter("part"):
        if part.get("id") not in want:
            continue
        for m in part.iter("measure"):
            try:
                num = int(m.get("number"))
            except (TypeError, ValueError):
                continue
            if not (first <= num <= last):
                continue
            h = g = 0
            for note in m.iter("note"):
                if note.find("rest") is not None:
                    continue
                if note.find("grace") is not None:
                    g += 1
                else:
                    h += 1
            out[num] = out.get(num, 0) + h
            graces[num] = graces.get(num, 0) + g
    return out, graces, sorted(ids.values())


# ─────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--page", type=int, default=3)
    ap.add_argument("--system", type=int, default=0)
    ap.add_argument("--staff", type=int, default=9)
    ap.add_argument("--ref-part", default="Viola")
    ap.add_argument("--ref-first", type=int, default=49)
    ap.add_argument("--ref-last", type=int, default=64)
    ap.add_argument("--musicxml", default=None)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--break-control", action="store_true",
                    help="RULE 7: drop one logged refusal on purpose, so the "
                         "control is seen failing before it is believed")
    a = ap.parse_args()

    instrument()
    d = load_record(a.record)
    rec = d["record"]

    xml, report = EXPORT.to_musicxml(d)
    if a.musicxml:
        Path(a.musicxml).write_text(xml)

    # ── the control: our per-subject log must reproduce the exporter's own
    if a.break_control and REFUSALS:
        REFUSALS.pop()
    flat = collections.Counter(r for _, r in REFUSALS)
    theirs = collections.Counter(report["notes_not_written"])
    if flat != theirs:
        raise SystemExit(f"CONTROL FAILED: per-subject refusals {dict(flat)} "
                         f"!= exporter's {dict(theirs)}")
    per_system = collections.defaultdict(collections.Counter)
    for sub, reason in REFUSALS:
        _, c = subject_parts(sub)
        per_system[(int(c[0]), int(c[1]))][reason] += 1
    for key, cnt in report["notes_not_written_by_system"].items():
        p, s = (int(x) for x in key.split("/")) if "/" in key else key
        if dict(per_system[(p, s)]) != dict(cnt):
            raise SystemExit(f"CONTROL FAILED at system {key}: "
                             f"{dict(per_system[(p, s)])} != {dict(cnt)}")

    # ── index the record for this page
    PAGE = str(a.page)
    obs_by_qs = {}
    for o in rec["observations"]:
        sub = o["subject"]
        c = sub.split("/")
        if len(c) > 1 and c[1] == PAGE:
            obs_by_qs.setdefault((o["quantity"], sub), []).append(o)
    vrd_by_qs = {}
    for v in rec["verdicts"]:
        sub = v["subject"]
        c = sub.split("/")
        if len(c) > 1 and c[1] == PAGE:
            vrd_by_qs.setdefault((v["quantity"], sub), []).append(v)

    refusal_of = {}
    for sub, reason in REFUSALS:
        refusal_of.setdefault(sub, []).append(reason)
    placed_of = collections.Counter()
    for sub, cat in PLACED:
        if sub:
            placed_of[(sub, cat)] += 1

    def staff_funnel(page, system, staff):
        """One staff: per-cell counts that sum."""
        pref = f"glyph/{page}/{system}/{staff}/"
        cells = collections.defaultdict(lambda: collections.Counter())
        heads = collections.defaultdict(list)
        for (q, sub), rows in obs_by_qs.items():
            if q != "glyph_box" or not sub.startswith(pref):
                continue
            ci = int(sub.split("/")[4])
            name = rows[0]["value"][0]
            cells[ci]["boxes_all"] += 1
            if is_notehead_class(name):
                cells[ci]["boxes_notehead"] += 1
                heads[ci].append(sub)
        for ci in range(0, 64):
            ink = obs_by_qs.get(("ink", f"cell/{page}/{system}/{staff}/{ci}"))
            if ink:
                cells[ci]["ink_components"] = ink[0]["detail"].get("ink_n_components", 0)
        out = {}
        for ci in sorted(set(list(cells) + list(heads))):
            row = collections.Counter()
            row["ink_components"] = cells[ci].get("ink_components", 0)
            row["boxes_notehead"] = cells[ci].get("boxes_notehead", 0)
            row["boxes_all"] = cells[ci].get("boxes_all", 0)
            for sub in heads[ci]:
                nc = obs_by_qs.get(("notehead_class", sub))
                if nc:
                    row["notehead_class_row"] += 1
                dv = vrd_by_qs.get(("duration", sub))
                if dv and dv[-1]["outcome"] == "decided":
                    row["duration_decided"] += 1
                elif dv:
                    row["duration_" + dv[-1]["outcome"]] += 1
                else:
                    row["duration_absent"] += 1
                pv = vrd_by_qs.get(("pitch", sub))
                if pv and pv[-1]["outcome"] == "decided":
                    row["pitch_decided"] += 1
                ev = vrd_by_qs.get(("event", sub))
                if ev:
                    row["event_row"] += 1
                ow = vrd_by_qs.get(("glyph_owner", sub))
                if ow and ow[-1].get("value") is not None:
                    ov = ow[-1]["value"]
                    home = f"staff/{page}/{system}/{staff}"
                    if isinstance(ov, str) and ov != home:
                        row["owner_elsewhere"] += 1
                    elif isinstance(ov, str):
                        row["owner_self"] += 1
                for reason in refusal_of.get(sub, ()):
                    row["refused:" + reason] += 1
                row["written"] += placed_of.get((sub, "notehead"), 0)
            # the balance: every notehead box is written, refused, or fell
            # out before the exporter ever asked (no notehead_class row, so
            # `_place_notes` `continue`s at its second test)
            refused = sum(v for k, v in row.items() if k.startswith("refused:"))
            row["unexplained"] = (row["boxes_notehead"] - row["written"]
                                  - refused - (row["boxes_notehead"]
                                               - row["notehead_class_row"]))
            row["no_notehead_class"] = row["boxes_notehead"] - row["notehead_class_row"]
            out[ci] = dict(row)
        return out

    # the subject staff
    subject = staff_funnel(a.page, a.system, a.staff)

    # ── every notehead box on the subject staff, with its PAGE box and its
    # disposition, so the crop can draw exactly what this table counts.
    pref = f"glyph/{a.page}/{a.system}/{a.staff}/"
    subject_glyphs = {}
    for (q, sub), rows in obs_by_qs.items():
        if q != "glyph_box" or not sub.startswith(pref):
            continue
        name = rows[0]["value"][0]
        if not is_notehead_class(name):
            continue
        reasons = refusal_of.get(sub, [])
        subject_glyphs[sub] = {
            "class": name,
            "cell": int(sub.split("/")[4]),
            "page_box_corners": rows[0]["detail"].get("bbox_page_px"),
            "conf": (obs_by_qs.get(("glyph_conf", sub)) or [{}])[0].get("value"),
            "refused": reasons,
            "written": placed_of.get((sub, "notehead"), 0),
        }

    # every staff on the page
    staves = sorted({tuple(int(x) for x in sub.split("/")[1:4])
                     for (q, sub) in obs_by_qs if q == "staff_lines"})
    page_table = {f"{p}/{s}/{st}": staff_funnel(p, s, st) for p, s, st in staves}

    # ── neighbours: who owns what
    def owners(page, system, staff):
        pref = f"glyph/{page}/{system}/{staff}/"
        c = collections.Counter()
        for (q, sub), rows in vrd_by_qs.items():
            if q != "glyph_owner" or not sub.startswith(pref):
                continue
            v = rows[-1].get("value")
            c[str(v)] += 1
        return dict(c)

    neigh = {f"{a.page}/{a.system}/{st}": owners(a.page, a.system, st)
             for st in range(0, 12)}

    # ── the reference
    mxl = library_root() / "reference/beethoven/symphony-5/beethoven--symphony-5--mvt1--gradus.mxl"
    ref, graces, all_parts = reference_heads(mxl, a.ref_part, a.ref_first, a.ref_last)

    # ── staff identity, so the reader knows what the staff IS
    ident = {}
    for q in ("instrument", "slot_index", "clef", "key_signature",
              "measure_partition", "staff_ordinal", "part_name"):
        for p, s, st in staves:
            v = vrd_by_qs.get((q, f"staff/{p}/{s}/{st}"))
            if v:
                ident.setdefault(f"{p}/{s}/{st}", {})[q] = {
                    "outcome": v[-1]["outcome"], "value": v[-1].get("value"),
                    "reason": v[-1].get("reason")}

    out = {
        "provenance": d.get("provenance"),
        "export_report": {
            "written": report.get("written"),
            "notes_not_written": report.get("notes_not_written"),
            "notes_not_written_total": report.get("notes_not_written_total"),
            "notes_not_written_by_system": report.get("notes_not_written_by_system"),
            "held_out": report.get("held_out"),
            "part_join": report.get("part_join"),
            "accounting": report.get("accounting"),
            "status_census": report.get("status_census"),
        },
        "subject_staff": f"staff/{a.page}/{a.system}/{a.staff}",
        "subject_funnel": subject,
        "subject_glyphs": subject_glyphs,
        # every refusal on this PAGE, by glyph, so a consumer (neighbours.py)
        # can price a cross-staff row without re-deciding anything.
        "page_glyph_refusals": {k: v for k, v in refusal_of.items()
                                if k.split("/")[1] == PAGE},
        "page_funnel": page_table,
        "identity": ident,
        "neighbour_owners": neigh,
        "reference": {"part": a.ref_part, "heads": ref, "graces": graces,
                      "parts": all_parts,
                      "first": a.ref_first, "last": a.ref_last},
        "control": "per-subject refusals reproduce export's own totals",
    }
    Path(a.out_json).write_text(json.dumps(out, indent=1))
    print("wrote", a.out_json)
    print("CONTROL PASSED:", dict(flat))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
