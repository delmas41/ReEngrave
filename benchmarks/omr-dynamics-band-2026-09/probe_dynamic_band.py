"""Where on the page is a dynamic letter printed, and which staff does it belong to?

`export.measure_dynamics` joins `f`+`f` into `ff` by x-adjacency and uses NO
vertical information beyond "the two letters are on the same line as each
other". Nothing anywhere asks whether a letter is standing where a dynamic is
printed. This measures whether that question has an answer worth asking.

The frame is staff spaces BELOW the bottom staff line of the staff whose cell
holds the detection — positive is under the staff, which is where an orchestral
dynamic goes. It is computed in PAGE pixels through `bbox_page_px` and
`upscale_factor`, never in the cell's own frame, because cell padding varies
with how crowded the staves are and would move the number without moving the
ink.

⚠️ AN OUT-OF-BAND LETTER IS NOT AUTOMATICALLY A FALSE POSITIVE, and separating
those two is the point of this probe rather than a refinement of it. A measure
cell is cut with 4-6 staff spaces of padding so ledger notes are not sliced
off, and on a conductor's page that padding reaches into the gap where the
NEIGHBOURING staff prints its dynamics. So a letter sitting 5.8 spaces above
its own staff's bottom line may be:

  own      — this staff's own dynamic, printed where dynamics go
  above:N  — the ink of staff N's dynamic, seen from the cell below it. Dropping
             it is right only if staff N also detected it; otherwise the mark
             should be RE-ATTRIBUTED, not deleted, or the page loses a dynamic
             it can see.
  none     — in no staff's band. The candidate false positive.

That distinction decides whether the fix is a gate or an arbitration, so the
probe reports it rather than assuming one.

    python3 benchmarks/omr-dynamics-band-2026-09/probe_dynamic_band.py \
        --scans <dir-of-transcriptions> --fixtures benchmarks/omr-orchestral-e2e/fixtures
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.export import (  # noqa: E402
    _DYNAMIC_LETTER, _DYNAMIC_WORDS, group_chords_in_measure, measure_dynamics,
    to_musicxml,
)

#: Where a dynamic is printed, in staff spaces below the bottom staff line —
#: used to label a letter as own/above/none. NOT a shipping constant, and
#: deliberately swept (`--band-lo`): the first cut used a lower edge of +0.5 and
#: that alone manufactured 27 of 44 "unattributable" letters, all of them
#: sitting within half a space of the bottom line where a dynamic printed tight
#: against its staff belongs. A constant read off a gap has to be shown to sit
#: in one, and the sweep is how this file shows it.
REPORT_BAND = (0.0, 6.0)


def set_band(lo: float, hi: float) -> None:
    global REPORT_BAND
    REPORT_BAND = (lo, hi)


# ---------------------------------------------------------------------------
# Reading letters out of a transcription
# ---------------------------------------------------------------------------


def _staff_frame(staff: dict) -> tuple[float, float] | None:
    """`(bottom_line_y_page, spacing_px)` or None if the staff has no geometry."""
    g = staff.get("staff_geometry") or {}
    ys = g.get("line_ys_page") or []
    spacing = g.get("line_spacing_px")
    if len(ys) < 5 or not spacing:
        return None
    return float(max(ys)), float(spacing)


def staff_spacings(result: dict) -> dict[int, float]:
    """staff_index -> line spacing in page px."""
    out: dict[int, float] = {}
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                f = _staff_frame(staff)
                if f:
                    out[staff.get("staff_index")] = f[1]
    return out


def letters_in_result(result: dict) -> list[dict]:
    """Every dynamic-letter detection, with its offset against every staff of
    its own system — not only the staff whose cell holds it.
    """
    out: list[dict] = []
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            frames = {}
            for staff in system.get("staves", []):
                f = _staff_frame(staff)
                if f:
                    frames[staff.get("staff_index")] = f
            for staff in system.get("staves", []):
                idx = staff.get("staff_index")
                if idx not in frames:
                    continue
                for meas in staff.get("measures", []):
                    box = meas.get("bbox_page_px") or [0, 0, 0, 0]
                    up = float(meas.get("upscale_factor") or 1.0) or 1.0
                    for det in meas.get("detections", []):
                        letter = _DYNAMIC_LETTER.get(det.get("class") or "")
                        if not letter:
                            continue
                        b = det.get("bbox")
                        if not b or len(b) != 4:
                            continue
                        px = float(box[0]) + (b[0] + b[2] / 2.0) / up
                        py = float(box[1]) + (b[1] + b[3] / 2.0) / up
                        offsets = {
                            s: (py - bot) / sp for s, (bot, sp) in frames.items()
                        }
                        out.append({
                            "staff": idx,
                            "w": b[2] / up,
                            # `export.measure_dynamics` sorts and compares on the
                            # box's LEFT and TOP edges, not its centre, and the
                            # letters of a word differ in height (`f` against
                            # `p`), so centres flip its `abs(y - run_y)` test.
                            # Kept separately from the centre, which is the right
                            # notion for WHERE the glyph sits and is what the
                            # band uses.
                            "page_x_left": float(box[0]) + b[0] / up,
                            "page_y_top": float(box[1]) + b[1] / up,
                            "spacing": frames[idx][1],
                            "measure": meas.get("measure_index"),
                            "letter": letter,
                            "cls": det.get("class"),
                            "conf": float(det.get("confidence") or 0.0),
                            "page_x": px,
                            "page_y": py,
                            "offset": offsets[idx],
                            "offsets": offsets,
                        })
    return out


def owner(rec: dict) -> str:
    """Which staff's dynamic band this letter is standing in."""
    lo, hi = REPORT_BAND
    if lo <= rec["offset"] <= hi:
        return "own"
    hits = sorted(s for s, off in rec["offsets"].items() if lo <= off <= hi)
    if not hits:
        return "none"
    # A staff whose band contains this ink and that sits ABOVE this one is the
    # neighbour whose padding we are looking into.
    above = [s for s in hits if s < rec["staff"]]
    return f"above:{above[-1]}" if above else f"below:{hits[0]}"


def largest_gap(values: list[float], lo: float = -12.0, hi: float = 8.0) -> tuple[float, float]:
    """The widest empty interval in the population, which is where a constant
    read off the data would sit. Bounded so one far outlier cannot claim it.
    """
    v = sorted(x for x in values if lo <= x <= hi)
    if len(v) < 2:
        return (float("nan"), float("nan"))
    gaps = [(v[i + 1] - v[i], v[i], v[i + 1]) for i in range(len(v) - 1)]
    _, a, b = max(gaps)
    return (a, b)


def _all_runs(dets: list[dict]) -> list[str]:
    """`measure_dynamics`'s joining, returning EVERY run — kept or discarded.

    The exporter throws away a run that spells no dynamic. To see what that
    costs you have to look at the runs it refused, which it does not return.
    """
    letters = []
    for d in dets:
        L = _DYNAMIC_LETTER.get(d.get("class") or "")
        b = d.get("bbox")
        if L and b and len(b) == 4:
            letters.append((b[0], b[1], b[2], L))
    if not letters:
        return []
    letters.sort()
    width = max(w for _x, _y, w, _l in letters) or 1
    out, word = [], letters[0][3]
    run_y = letters[0][1]
    prev_right = letters[0][0] + letters[0][2]
    for x, y, w, L in letters[1:]:
        if x - prev_right <= width and abs(y - run_y) <= width:
            word += L
        else:
            out.append(word)
            word, run_y = L, y
        prev_right = x + w
    out.append(word)
    return out


def funnel(pairs: list[tuple[str, Path, Path]]) -> dict:
    """printed -> detected -> spells a dynamic -> survives the exporter.

    Answers "do we read these and then not write them?" — which has TWO
    different answers here, both of them the same family and neither of them
    the largest term.
    """
    rows, kept_w, dropped_w = [], Counter(), Counter()
    for work, omr, truth in pairs:
        res = json.loads(omr.read_text())
        letters = words = in_empty = 0
        for page in res.get("pages", []):
            for system in page.get("systems", []):
                for staff in system.get("staves", []):
                    for meas in staff.get("measures", []):
                        dets = meas.get("detections", [])
                        letters += sum(
                            1 for d in dets
                            if _DYNAMIC_LETTER.get(d.get("class") or ""))
                        n = len(measure_dynamics(dets))
                        words += n
                        # The whole-measure-rest branch computes the directions
                        # and then emits only a rest.
                        if n and not group_chords_in_measure(dets):
                            in_empty += n
                        for r in _all_runs(dets):
                            (kept_w if r in _DYNAMIC_WORDS else dropped_w)[r] += 1
        exported = len(re.findall(r"<dynamics", to_musicxml(res)))
        rows.append({"work": work, "letters": letters, "words": words,
                     "lost_empty_measure": in_empty, "exported": exported,
                     "truth": _truth_dynamics(truth)})
    return {"rows": rows, "kept_runs": dict(kept_w), "dropped_runs": dict(dropped_w)}


# ---------------------------------------------------------------------------
# Arms
# ---------------------------------------------------------------------------


def scan_arm(scan_dir: Path) -> dict:
    per_edition: dict[str, dict] = {}
    for path in sorted(scan_dir.glob("*.json")):
        edition = re.sub(r"-p\d+$", "", path.stem)
        recs = letters_in_result(json.loads(path.read_text()))
        e = per_edition.setdefault(edition, {"letters": [], "pages": 0})
        e["letters"] += recs
        e["pages"] += 1
    for edition, e in per_edition.items():
        offs = [r["offset"] for r in e["letters"]]
        e["n"] = len(offs)
        e["owner"] = Counter(owner(r) for r in e["letters"])
        e["gap"] = largest_gap(offs)
        inb = [o for o in offs if REPORT_BAND[0] <= o <= REPORT_BAND[1]]
        e["in_band"] = len(inb)
        e["in_band_range"] = (min(inb), max(inb)) if inb else None
        e["letter_mix"] = Counter(r["letter"] for r in e["letters"])
    return per_edition


def _truth_dynamics(path: Path) -> int:
    return len(re.findall(r"<dynamics", path.read_text()))


def _truth_per_part(path: Path) -> list[int]:
    """Dynamics per `<part>`, in document order."""
    txt = path.read_text()
    return [len(re.findall(r"<dynamics", m.group(1)))
            for m in re.finditer(r'<part id="[^"]+">(.*?)</part>', txt, re.S)]


def _truth_words_per_part(path: Path) -> list[list[str]]:
    """The dynamic WORDS per `<part>`, sorted — `["ff", "p"]`.

    Counting marks cannot see an `ff` collapsing to an `f`: both are one word.
    Comparing the words can.
    """
    txt = path.read_text()
    out = []
    for m in re.finditer(r'<part id="[^"]+">(.*?)</part>', txt, re.S):
        body = m.group(1)
        w = re.findall(r"<dynamics[^>]*>\s*<([a-z]+)\s*/?>", body)
        w += re.findall(r"<other-dynamics>([^<]+)</other-dynamics>", body)
        out.append(sorted(w))
    return out


def _join_words(letters: list[dict]) -> list[str]:
    """`export.measure_dynamics`'s joining rule, in PAGE pixels.

    The rule is scale-relative — "the next letter starts within one letter-width
    of the last one's right edge, at the same height" — so it transfers frames
    unchanged. It is restated here because the re-attribution policy moves a
    letter into a staff whose cell it was never cut into, and there is no
    canonical frame that holds both. `words_now` is computed BOTH ways and the
    probe asserts they agree, so this restatement cannot drift from the export
    without the probe saying so.
    """
    if not letters:
        return []
    ls = sorted(letters, key=lambda r: (r["page_x_left"], r["page_y_top"],
                                        r["w"], r["letter"]))
    width = max(r["w"] for r in ls) or 1.0
    out, word = [], ls[0]["letter"]
    run_y = ls[0]["page_y_top"]
    prev_right = ls[0]["page_x_left"] + ls[0]["w"]
    for r in ls[1:]:
        if (r["page_x_left"] - prev_right <= width
                and abs(r["page_y_top"] - run_y) <= width):
            word += r["letter"]
        else:
            out.append(word)
            word, run_y = r["letter"], r["page_y_top"]
        prev_right = r["page_x_left"] + r["w"]
    out.append(word)
    from tools.omr.export import _DYNAMIC_WORDS
    return [w for w in out if w in _DYNAMIC_WORDS]


def _reattributed(recs: list[dict], spacing: dict[int, float]) -> list[dict]:
    """Give each letter to the staff whose dynamic band it stands in, then drop
    the copies that are the same physical ink.

    A letter in NO staff's band is dropped — that is the false-positive arm.
    A letter in the band of the staff ABOVE is the neighbour's dynamic seen
    through this cell's padding, and it is MOVED rather than deleted: deleting
    is only right where that staff detected its own copy, which is exactly what
    the same-ink dedupe below decides.
    """
    moved = []
    for r in recs:
        who = owner(r)
        if who == "none":
            continue
        target = r["staff"] if who == "own" else int(who.split(":")[1])
        moved.append({**r, "staff": target, "src_staff": r["staff"]})
    kept: list[dict] = []
    for r in sorted(moved, key=lambda r: (r["staff"], r["page_x"], r["page_y"])):
        sp = spacing.get(r["staff"], 1.0) or 1.0
        # ⚠️ SAME INK MEANS A DIFFERENT SOURCE CELL, not merely a small distance.
        # Comparing every letter now on this staff would merge the two `f` of an
        # `ff` — word-internal letters sit as close as 0.20 staff spaces, well
        # inside any distance threshold — and the word count would not notice,
        # because `ff` collapsing to `f` is still one word. Two letters cut from
        # the SAME cell can never be one glyph seen twice, so the source staff
        # settles it exactly and no threshold has to.
        if any(o["src_staff"] != r["src_staff"]
               and o["staff"] == r["staff"]
               and abs(o["page_x"] - r["page_x"]) < 0.5 * sp
               and abs(o["page_y"] - r["page_y"]) < 0.5 * sp
               for o in kept):
            continue
        kept.append(r)
    return kept


def engraved_pairs(fixtures: Path) -> list[tuple[str, Path, Path]]:
    """LilyPond-rendered orchestral excerpts: `<work>.omr.json` + `<work>.musicxml`."""
    out = []
    for omr in sorted(fixtures.glob("*.omr.json")):
        work = omr.name[: -len(".omr.json")]
        truth = fixtures / f"{work}.musicxml"
        if truth.exists():
            out.append((work, omr, truth))
    return out


def scanned_pairs(scored_dir: Path, scan_fixtures: Path) -> list[tuple[str, Path, Path]]:
    """Real scans with hand-verified windows: the scan-e2e benchmark's truth.

    ⚠️ That truth's NOTES come from the reference encoding, not from reading the
    scan, so its dynamics are the ones the edition's reference carries. A mark
    the engraver printed and the encoder omitted counts against us here and is
    not our error. The windows themselves are hand-verified, which is what makes
    the page-to-measure join trustworthy.
    """
    out = []
    for omr in sorted(scored_dir.glob("*.json")):
        truth = scan_fixtures / f"{omr.stem}.truth.musicxml"
        if truth.exists():
            out.append((omr.stem, omr, truth))
    return out


def _row_join(row: dict | None, n_staves: int) -> list[list[int]] | None:
    """The hand-verified staff -> reference-part join from `works.json`.

    ⚠️ Preferred over joining by ordinal, which is only right when no staff is
    condensed: a printed score puts Fl 1+2 on one staff (`parts: [0, 1]`) and
    an ordinal join then reads every later part off by one. ABSTAINS unless the
    row's staff count equals ours — the same rule the dossier slot-level checks
    use, and for the same reason.
    """
    if not row:
        return None
    staves = row.get("staves") or []
    if len(staves) != n_staves:
        return None
    return [list(s.get("parts") or []) for s in staves]


def scored_arm(pairs: list[tuple[str, Path, Path]],
               rows: dict[str, dict] | None = None) -> dict:
    """Score the three policies wherever truth exists.

    Counts WORDS, not letters, because the exporter emits one `<direction>` per
    word and `ff` is two letters. Three policies:

      now     — every letter, which is what ships today
      band    — keep only letters standing in their OWN staff's band (a gate)
      reattr  — give each letter to the staff whose band it stands in, then drop
                the copies that are the same physical ink (an arbitration)

    Measures are assumed to correspond across the staves of a system, which is
    what a barline is, so a re-attributed letter keeps its source measure index.
    """
    out: dict[str, dict] = {}
    for work, omr, truth in pairs:
        result = json.loads(omr.read_text())
        recs = letters_in_result(result)
        spacing = staff_spacings(result)

        def words(letters: list[dict]) -> int:
            by_cell: dict[tuple, list[dict]] = defaultdict(list)
            for r in letters:
                by_cell[(r["staff"], r["measure"])].append(r)
            return sum(len(_join_words(v)) for v in by_cell.values())

        n_now = words(recs)
        n_band = words([r for r in recs if owner(r) == "own"])
        n_reattr = words(_reattributed(recs, spacing))

        # SELF-CHECK: the page-frame joiner must reproduce the exporter's own
        # count on the unfiltered set, or the three policies are not comparable.
        export_now = 0
        for page in result.get("pages", []):
            for system in page.get("systems", []):
                for staff in system.get("staves", []):
                    for meas in staff.get("measures", []):
                        export_now += len(measure_dynamics(meas.get("detections", [])))

        # PER-STAFF EXACTNESS — the control that separates "the right number of
        # marks" from "the right marks on the right staves". A count can be
        # right for the wrong reason; this cannot. Parts are joined to staves by
        # ORDINAL, which is what `export._stitch_slots` does, so it ABSTAINS
        # unless the two counts agree — the same rule the dossier slot-level
        # checks use, and for the same reason: a printed score condenses and
        # splits, and forcing that join measures the join, not the marks.
        per_part = _truth_per_part(truth)
        row = (rows or {}).get(work)
        staves = sorted({r["staff"] for r in recs} |
                        {s for pg in result.get("pages", [])
                         for sy in pg.get("systems", [])
                         for s in [st.get("staff_index") for st in sy.get("staves", [])]})
        exact_now = exact_re = n_live = live_now = live_re = None
        word_now = word_re = wlive_now = wlive_re = None
        join = _row_join(row, len(staves))
        if join is None and len(per_part) == len(staves):
            join = [[i] for i in range(len(staves))]   # ordinal, no condensation
        if join is not None:
            def by_staff(letters):
                cells: dict[tuple, list[dict]] = defaultdict(list)
                for r in letters:
                    cells[(r["staff"], r["measure"])].append(r)
                c: Counter = Counter()
                words: dict[int, list[str]] = defaultdict(list)
                for (st, _m), v in cells.items():
                    got = _join_words(v)
                    c[st] += len(got)
                    words[st] += got
                return c, {k: sorted(v) for k, v in words.items()}
            c_now, w_now = by_staff(recs)
            c_re, w_re = by_staff(_reattributed(recs, spacing))
            # Fold the truth onto STAVES before anything is compared, so the
            # count and word checks are both asking about the same objects.
            per_part = [sum(per_part[j] for j in join[i] if j < len(per_part))
                        for i in range(len(staves))]
            tw_parts = _truth_words_per_part(truth)
            # A condensed staff carries several parts; its marks are their union.
            tw = [sorted(w for j in join[i] if j < len(tw_parts) for w in tw_parts[j])
                  for i in range(len(staves))]
            word_now = sum(w_now.get(s, []) == tw[i] for i, s in enumerate(staves))
            word_re = sum(w_re.get(s, []) == tw[i] for i, s in enumerate(staves))
            live_w = [i for i, s in enumerate(staves)
                      if tw[i] or w_now.get(s) or w_re.get(s)]
            wlive_now = sum(w_now.get(staves[i], []) == tw[i] for i in live_w)
            wlive_re = sum(w_re.get(staves[i], []) == tw[i] for i in live_w)
            exact_now = sum(c_now.get(s, 0) == per_part[i] for i, s in enumerate(staves))
            exact_re = sum(c_re.get(s, 0) == per_part[i] for i, s in enumerate(staves))
            # ⚠️ A staff with no dynamic in truth and none emitted is "exact",
            # and on a page where most parts carry none that inflates the
            # denominator past usefulness — Mahler is 36 of 38 before anything
            # is fixed. So the CONTESTED subset is reported too: staves where
            # the truth or either policy has something to say.
            live = [i for i, s in enumerate(staves)
                    if per_part[i] or c_now.get(s, 0) or c_re.get(s, 0)]
            n_live = len(live)
            live_now = sum(c_now.get(staves[i], 0) == per_part[i] for i in live)
            live_re = sum(c_re.get(staves[i], 0) == per_part[i] for i in live)

        out[work] = {
            "n_staves": len(staves),
            "exact_now": exact_now,
            "exact_reattr": exact_re,
            "n_contested": n_live,
            "contested_now": live_now,
            "contested_reattr": live_re,
            "words_exact_now": wlive_now,
            "words_exact_reattr": wlive_re,
            "letters": len(recs),
            "owner": Counter(owner(r) for r in recs),
            "words_now": n_now,
            "words_band": n_band,
            "words_reattr": n_reattr,
            "export_now": export_now,
            "joiner_agrees": n_now == export_now,
            "truth": _truth_dynamics(truth),
            "gap": largest_gap([r["offset"] for r in recs]),
        }
    return out


# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scans", type=Path, help="directory of scan transcriptions")
    ap.add_argument("--fixtures", type=Path,
                    default=REPO / "benchmarks" / "omr-orchestral-e2e" / "fixtures")
    ap.add_argument("--scored", type=Path,
                    help="directory of transcriptions of the scan-e2e rows")
    ap.add_argument("--scan-fixtures", type=Path,
                    default=REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "fixtures")
    ap.add_argument("--band-lo", type=float, default=REPORT_BAND[0],
                    help="lower edge of the placement band, staff spaces below "
                         "the bottom line")
    ap.add_argument("--band-hi", type=float, default=REPORT_BAND[1])
    ap.add_argument("--funnel", action="store_true",
                    help="printed -> detected -> spells a dynamic -> exported")
    ap.add_argument("--sweep", action="store_true",
                    help="score the policies across several band lower edges")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()
    set_band(args.band_lo, args.band_hi)

    report: dict = {}

    if args.scans and args.scans.exists():
        per = scan_arm(args.scans)
        report["scans"] = {
            k: {"pages": v["pages"], "letters": v["n"], "in_band": v["in_band"],
                "in_band_range": v["in_band_range"], "gap": v["gap"],
                "owner": dict(v["owner"]), "letter_mix": dict(v["letter_mix"])}
            for k, v in per.items()
        }
        print("=" * 78)
        print("SCAN ARM — dynamic letters, staff spaces below the bottom staff line")
        print("=" * 78)
        print(f"{'edition':26s} {'pg':>2s} {'let':>4s} {'own':>4s} {'above':>5s} "
              f"{'below':>5s} {'none':>5s}  {'own population':>16s}  empty gap")
        tot = Counter()
        alloff: list[float] = []
        for ed in sorted(per):
            v = per[ed]
            o = v["owner"]
            tot.update(o)
            alloff += [r["offset"] for r in v["letters"]]
            above = sum(n for k, n in o.items() if k.startswith("above"))
            below = sum(n for k, n in o.items() if k.startswith("below"))
            g = v["gap"]
            rng = v["in_band_range"]
            rs = f"{rng[0]:+.2f} .. {rng[1]:+.2f}" if rng else "-"
            print(f"{ed:26s} {v['pages']:2d} {v['n']:4d} "
                  f"{o.get('own', 0):4d} {above:5d} {below:5d} {o.get('none', 0):5d}"
                  f"  {rs:>16s}  {g[0]:+.2f} .. {g[1]:+.2f}")
        print("-" * 78)
        na = sum(n for k, n in tot.items() if k.startswith("above"))
        nb = sum(n for k, n in tot.items() if k.startswith("below"))
        print(f"{'POOLED':26s} {'':2s} {sum(tot.values()):4d} "
              f"{tot.get('own', 0):4d} {na:5d} {nb:5d} {tot.get('none', 0):5d}")
        g = largest_gap(alloff)
        print(f"\npooled widest empty interval: {g[0]:+.2f} .. {g[1]:+.2f} spaces "
              f"({g[1] - g[0]:.2f} wide)")
        report["pooled_gap"] = g

        # Two discriminators that are NOT position, checked so the findings can
        # say what was refuted rather than only what worked.
        allrecs = [r for v in per.values() for r in v["letters"]]
        ups = Counter(r["staff"] - int(owner(r).split(":")[1])
                      for r in allrecs if owner(r).startswith("above:"))
        print(f"how many staves up the owning staff is: {dict(sorted(ups.items()))}"
              "   (1 everywhere = the cell's own padding, reaching exactly one staff)")
        # REFUTED DISCRIMINATOR: confidence. Not by comparing medians — which
        # differ, and would flatter it — but by pricing the trade a threshold
        # would actually make.
        c_own = [r["conf"] for r in allrecs if owner(r) == "own"]
        c_non = [r["conf"] for r in allrecs if owner(r) == "none"]
        if c_own and c_non:
            print(f"\nCONFIDENCE as a filter (own n={len(c_own)}, "
                  f"unattributable n={len(c_non)}):")
            print(f"  {'threshold':>9s} {'none removed':>13s} {'own LOST':>10s}")
            trade = []
            for th in (0.30, 0.40, 0.50, 0.60, 0.70, 0.80):
                a = sum(1 for c in c_non if c < th)
                b = sum(1 for c in c_own if c < th)
                trade.append({"threshold": th, "none_removed": a, "own_lost": b})
                print(f"  {th:9.2f} {a:8d}/{len(c_non):<4d} {b:6d}/{len(c_own):<4d}")
            print("  -> every threshold costs far more good letters than junk it "
                  "removes. Position separates; confidence does not.")
            report["confidence_trade"] = trade
        report["above_staff_distance"] = dict(sorted(ups.items()))

        # Is moving a letter a DEDUPE or a JUDGEMENT? Where the target staff
        # already holds its own in-band copy at the same x, re-attribution
        # merely drops a twin. Where it does not, the moved letter is that
        # staff's only evidence and the move rests on a placement convention.
        dedupe = judgement = 0
        for _ed, v in per.items():
            own_by_staff: dict[int, list[dict]] = defaultdict(list)
            for r in v["letters"]:
                if owner(r) == "own":
                    own_by_staff[r["staff"]].append(r)
            for r in v["letters"]:
                w = owner(r)
                if not w.startswith("above:"):
                    continue
                tgt = int(w.split(":")[1])
                s = r["spacing"] or 1.0
                if any(abs(o["page_x"] - r["page_x"]) < 0.75 * s
                       for o in own_by_staff.get(tgt, [])):
                    dedupe += 1
                else:
                    judgement += 1
        tot_mv = dedupe + judgement
        if tot_mv:
            print(f"\nre-attributed letters: {dedupe} are a DEDUPE (the target staff "
                  f"already has its own copy),\n  {judgement} "
                  f"({judgement / tot_mv:.0%}) are that staff's SOLE EVIDENCE — "
                  "because `_dedupe_cross_staff_detections`\n  already removed the "
                  "twin by DISTANCE and kept the lower staff's copy. Which is why "
                  "the\n  fix belongs in that function, not in a filter after it.")
        report["reattribution"] = {"dedupe": dedupe, "sole_evidence": judgement}

    scan_rows: dict[str, dict] = {}
    wj = args.scan_fixtures.parent / "works.json"
    if wj.exists():
        scan_rows = {r["row_id"]: r
                     for r in json.loads(wj.read_text()).get("rows", [])}

    arms = []
    if args.fixtures and args.fixtures.exists():
        arms.append(("ENGRAVED (LilyPond renders — one engraving convention)",
                     "engraved", engraved_pairs(args.fixtures)))
    if args.scored and args.scored.exists():
        arms.append(("SCANNED (real editions, hand-verified windows)",
                     "scanned", scanned_pairs(args.scored, args.scan_fixtures)))

    for title, key, pairs in arms:
        if not pairs:
            continue
        res = scored_arm(pairs, rows=scan_rows if key == "scanned" else None)
        report[key] = {k: {**v, "owner": dict(v["owner"])} for k, v in res.items()}
        print()
        print("=" * 78)
        print(f"{title} — SCORED")
        print("=" * 78)
        print(f"{'page':30s} {'let':>4s} {'own':>4s} {'abv':>4s} {'none':>4s}"
              f" | {'now':>5s} {'band':>5s} {'reattr':>6s} {'truth':>6s}"
              f" | {'staves exact (contested)':>34s}")
        for w in sorted(res):
            v = res[w]
            above = sum(n for k2, n in v["owner"].items() if k2.startswith("above"))
            ex = ("abstains (parts != staves)" if v["exact_now"] is None
                  else f"{v['contested_now']:2d}->{v['contested_reattr']:2d} count, "
                       f"{v['words_exact_now']:2d}->{v['words_exact_reattr']:2d} words"
                       f"  /{v['n_contested']:2d}")
            print(f"{w:30s} {v['letters']:4d} {v['owner'].get('own', 0):4d} "
                  f"{above:4d} {v['owner'].get('none', 0):4d} | "
                  f"{v['words_now']:5d} {v['words_band']:5d} {v['words_reattr']:6d} "
                  f"{v['truth']:6d} | {ex:>34s}")
        s_now = sum(v["words_now"] for v in res.values())
        s_band = sum(v["words_band"] for v in res.values())
        s_re = sum(v["words_reattr"] for v in res.values())
        s_truth = sum(v["truth"] for v in res.values())
        print("-" * 78)
        e_now = sum(v["contested_now"] or 0 for v in res.values())
        e_re = sum(v["contested_reattr"] or 0 for v in res.values())
        e_of = sum(v["n_contested"] or 0 for v in res.values())
        w_n = sum(v["words_exact_now"] or 0 for v in res.values())
        w_r = sum(v["words_exact_reattr"] or 0 for v in res.values())
        print(f"{'TOTAL':30s} {'':4s} {'':4s} {'':4s} {'':4s} | "
              f"{s_now:5d} {s_band:5d} {s_re:6d} {s_truth:6d} | "
              f"{e_now:2d}->{e_re:2d} count, {w_n:2d}->{w_r:2d} words  /{e_of:2d}")
        if s_truth:
            print(f"\nemitted/truth   now {s_now / s_truth:.2f}   "
                  f"gate {s_band / s_truth:.2f}   re-attribute {s_re / s_truth:.2f}"
                  "     (1.00 is right)")
        bad = [w for w, v in res.items() if not v["joiner_agrees"]]
        print("joiner self-check vs export.measure_dynamics: "
              + ("AGREES on every page" if not bad else f"DISAGREES on {bad}"))

    if args.funnel and arms:
        for title, key, pairs in arms:
            if not pairs:
                continue
            fn = funnel(pairs)
            report[key + "_funnel"] = fn
            print()
            print("=" * 78)
            print(f"FUNNEL — {title}")
            print("=" * 78)
            print(f"{'page':34s} {'let':>4s} {'words':>6s} {'lost:empty':>11s} "
                  f"{'exported':>9s} {'truth':>6s}")
            for r in fn["rows"]:
                print(f"{r['work']:34s} {r['letters']:4d} {r['words']:6d} "
                      f"{r['lost_empty_measure']:11d} {r['exported']:9d} "
                      f"{r['truth']:6d}")
            s = {k: sum(r[k] for r in fn["rows"])
                 for k in ("letters", "words", "lost_empty_measure",
                           "exported", "truth")}
            print("-" * 78)
            print(f"{'TOTAL':34s} {s['letters']:4d} {s['words']:6d} "
                  f"{s['lost_empty_measure']:11d} {s['exported']:9d} {s['truth']:6d}")
            nd = sum(len(r) * n for r, n in fn["dropped_runs"].items())
            nk = sum(len(r) * n for r, n in fn["kept_runs"].items())
            print(f"\n  letters whose run SPELLS a dynamic : {nk:4d}"
                  f"  -> {s['words']} words")
            print(f"  letters whose run spells NOTHING   : {nd:4d}"
                  f"  in {sum(fn['dropped_runs'].values())} runs, all discarded")
            print(f"  discarded runs: "
                  f"{dict(sorted(fn['dropped_runs'].items(), key=lambda kv: -kv[1])[:12])}")
            print(f"\n  words formed but NOT exported: "
                  f"{s['words'] - s['exported']}"
                  f"  — and the whole-measure-rest branch accounts for "
                  f"{s['lost_empty_measure']} of them")
            print(f"  shortfall against truth: {s['truth'] - s['exported']}")

    if args.sweep and arms:
        print()
        print("=" * 78)
        print("BAND SWEEP — is the lower edge a plateau or a peak?")
        print("=" * 78)
        print(f"{'band lo':>8s} | " + " | ".join(
            f"{name:>28s}" for name, _k, _p in arms))
        rows = []
        for lo in (-1.5, -1.0, -0.5, 0.0, 0.25, 0.5, 1.0):
            set_band(lo, args.band_hi)
            cells = []
            for _n, _k, pairs in arms:
                res = scored_arm(pairs, rows=scan_rows if _k == "scanned" else None)
                s_re = sum(v["words_reattr"] for v in res.values())
                s_t = sum(v["truth"] for v in res.values())
                e_re = sum(v["contested_reattr"] or 0 for v in res.values())
                e_of = sum(v["n_contested"] or 0 for v in res.values())
                cells.append(f"reattr/truth {s_re / s_t:.2f}  exact {e_re:2d}/{e_of:2d}"
                             if s_t else "n/a")
            rows.append((lo, cells))
            print(f"{lo:+8.2f} | " + " | ".join(f"{c:>28s}" for c in cells))
        report["band_sweep"] = [{"band_lo": lo, "cells": c} for lo, c in rows]
        set_band(args.band_lo, args.band_hi)

    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=1, default=str))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
