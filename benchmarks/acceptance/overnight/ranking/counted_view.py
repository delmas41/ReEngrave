"""ROADMAP 2.265 (ranking hygiene): the COUNTED view of a saved record, for the 2.229 product ranking. STAGED tooling; no reader, no record row.

A ranking row is evidence only if it counts what it names (CLAUDE rule 7). Two counting mistakes lived in `export_saved.py` /
`rank_counts.py` / `rank_table.py`:

1. THE CONTEXT PAGE WAS COUNTED. `lane_report` loads each plate's opening page so the header (meter, key, clef) is inherited, and
   "context pages are loaded but never counted" (`benchmarks/lane-report/sample.json`, `lane_report.run_arm`). The ranking exported the
   LOADED pages (sample + context) and divided by the loaded count, so Litolff p1 was counted as a ninth page (Brahms' context page 0
   is also a sample page, so it was never affected). The exporter's family totals (`arcs_not_written`, `dot_role_not_placed`) carry no
   page, so the fix cannot filter them afterwards: `drop_context_marks` removes the ARC and DOT family rows of the context pages from
   the in-memory record BEFORE the export (the notes, bars, header and every other family stay, so the counted pages export as before).
2. A SPECK WAS COUNTED AS AN ABSTAINED DOT. `adjudicate_dot_role` abstains `dot_role_ambiguous` for every dot-class box no window fits,
   and the ranking row counted every such abstention, so a box over ink too small to be a dot was "a dot never placed". The size test is
   the stroke map's own floor, `stroke_map.MIN_AREA_SP2` (0.05 staff spaces squared: "sits under an augmentation dot (~0.12)", the area
   under which GATHER does not file a stroke at all), applied to the box's own `Q.MARK_SHAPE` ink (width x height x fill, in spaces).
   No number is new. A box with no `Q.MARK_SHAPE` row is NOT a speck (rule 8: cannot tell stays counted).

Nothing is removed from any record on disk and no verdict changes; every excluded item is listed (`dot_specks` rows, the context pages
named in the summary) so it can be looked at.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))  # repo root, so `tools` imports
from tools.omr.staged import stroke_map                      # noqa: E402
from tools.omr.staged.lane_report import page_of             # noqa: E402

#: the stroke map's own floor: a piece of ink under this many staff-spaces squared is not filed as a stroke (`stroke_map`, module doc).
SPECK_FLOOR_SP2 = stroke_map.MIN_AREA_SP2

#: every quantity the exporter reads to count `arcs_not_written` and `dot_role_not_placed`. A context page's rows of these are dropped.
ARC_QUANTITIES = ("arc_box", "arc_ink_shape", "arc_kind", "arc_owner", "arc_is_not_an_arc", "tie_pair", "system_arc")
DOT_QUANTITIES = ("aug_dot", "dot_role", "dot_staff_position", "dot_stroke_ink")
FAMILY_QUANTITIES = frozenset(ARC_QUANTITIES + DOT_QUANTITIES)


def drop_context_marks(record, context_pages):
    """Remove, IN PLACE, the ARC and DOT family rows (observations, abstentions, verdicts) of `context_pages` from `record`
    (`{"observations", "abstentions", "verdicts"}`). Returns `{quantity: rows dropped}` so the caller can print what was left out.
    Rows of any other quantity, and every row of a counted page, are untouched."""
    ctx = set(context_pages)
    dropped = {}
    if not ctx:
        return dropped
    for kind in ("observations", "abstentions", "verdicts"):
        keep = []
        for it in record[kind]:
            if it.get("quantity") in FAMILY_QUANTITIES and page_of(it.get("subject")) in ctx:
                key = "%s:%s" % (kind, it["quantity"])
                dropped[key] = dropped.get(key, 0) + 1
            else:
                keep.append(it)
        record[kind] = keep
    return dropped


def mark_ink_area_sp2(rec, subject):
    """The box's own ink in staff spaces squared from GATHER's `Q.MARK_SHAPE` (w_spaces x h_spaces x fill), or None when it has no
    such row (cannot tell)."""
    rows = rec.obs("mark_shape", subject)
    if not rows:
        return None
    d = rows[-1].get("detail") or {}
    try:
        return float(d["w_spaces"]) * float(d["h_spaces"]) * float(d["fill"])
    except (KeyError, TypeError, ValueError):
        return None


def dot_specks(rec, count_pages, floor=SPECK_FLOOR_SP2):
    """Every counted-page dot-class box whose own ink is under the stroke floor, with the standing dot-role verdict it got:
    `[{subject, page, outcome, reason, area_sp2}]`. `rec` is an `export.Record`."""
    cp = set(count_pages)
    out = []
    for o in rec.obs_of("aug_dot"):
        sub = o["subject"]
        pg = page_of(sub)
        if pg not in cp:
            continue
        area = mark_ink_area_sp2(rec, sub)
        if area is None or area >= floor:
            continue
        v = rec.verdict("dot_role", sub)
        out.append(dict(subject=sub, page=pg, outcome=(v or {}).get("outcome"), reason=(v or {}).get("reason"),
                        area_sp2=round(area, 4)))
    return out


def specks_in_row(specks):
    """How many specks the ranking's dots row counts: the row is `dot_role_not_placed["abstained_dot_role_ambiguous"]`, one count per
    dot-class box whose standing verdict is an abstention with that reason (`export._place_dot_role_marks`)."""
    return sum(1 for s in specks if s["outcome"] == "abstained" and s["reason"] == "dot_role_ambiguous")


def counted_symbols(hosts, loose, report, count_pages):
    """The three per-file totals `compare.py` prints, over the counted pages only: `(hosts, loose, red_bars, blue_marks,
    notes_not_written)`. Hosts and loose are filtered by page; red bars come from the exporter's bar list (each carries its page);
    notes not written from the per-system accounting (keyed `page/system`)."""
    cp = set(count_pages)
    hosts = [h for h in hosts if h["page"] is None or h["page"] in cp]
    loose = [d for d in loose if d.get("page") is None or d.get("page") in cp]
    red = report.get("bars_written_red") or {}
    red_bars = sum(1 for b in (red.get("bars_list") or ()) if b.get("page") in cp)
    nnw = 0
    for k, d in (report.get("notes_not_written_by_system") or {}).items():
        if int(k.split("/")[0]) in cp:
            nnw += sum(int(v) for v in d.values())
    blue = sum(1 for h in hosts if h.get("blue"))
    return hosts, loose, red_bars, blue, nnw


def write_json(path, obj):
    pathlib.Path(path).write_text(json.dumps(obj, default=str))
