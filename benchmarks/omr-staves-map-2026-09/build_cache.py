"""Assemble everything the staves-map confirmation UI shows, ONCE, into a cache.

The UI has to be instant under Sean's fingers, and the three things it shows are
each slow to produce: a 600 dpi deskewed render of a scanned plate, a music21
parse of the trimmed reference, and the detected staff bands of the canonical
run.  So they are produced here, written to a cache directory, and the server
does nothing but serve them.

WHAT EACH FACT COMES FROM, AND WHY IT HAS TO COME FROM THERE
------------------------------------------------------------

  printed staves  ->  the RUN, never the encoding.  `<row>.reconciliation.omr
                      .json` is the canonical 20-row baseline's own artefact
                      (`results-reconciliation.json`, pooled 0.8444), so the
                      staff bands the UI boxes are the bands the benchmark
                      scored.  Taking the staff count from the reference would
                      make the whole exercise circular: the question IS whether
                      the printed staves and the encoded parts correspond.

  reference parts ->  `<row>.truth.musicxml`, enumerated with music21, because
                      `staves[i].parts` indexes `page_normalise`'s `out.parts`
                      and that is `music21`'s part list.  ⚠️ It is NOT the
                      `<score-part>` list: a part declaring `<staves>2</staves>`
                      parses to two `PartStaff`s, and that exact off-by-one made
                      an identity map drop a part and "improve" Dvorak 9 by 42
                      edits (page_normalise.py, the `IncompleteMap` comment).
                      Names and abbreviations are read out of the `<score-part>`
                      elements with ElementTree — a real XML parser, never a
                      regex — and the two counts are CROSS-CHECKED.  They
                      disagree => the row is cached as unusable, loudly.

  the page image  ->  `tools.omr.preprocessing.render_page`, not a plain fitz
                      render.  Four of the five plates are deskewed by 0.25
                      degrees and the staff bands are recorded in the DESKEWED
                      frame; a raw render would put every box a few pixels off
                      its staff at the top of the page and a lot more at the
                      bottom.

  the proposal    ->  the row's own `systems_as_printed`, which is hand-read and
                      verified against the print (see each row's `verified_by`).
                      It is per-SYSTEM; a `staves` map is per-PAGE and has no
                      system dimension, so the proposal picks the system whose
                      lineup names the most reference parts.  That choice is
                      shown to the human as a choice, never as an answer.

    python3 benchmarks/omr-staves-map-2026-09/build_cache.py            # all 5
    python3 benchmarks/omr-staves-map-2026-09/build_cache.py --rows <id> --force
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BENCH = Path(__file__).resolve().parent

#: The MAIN checkout.  The UI reads the shared store and writes Sean's decisions
#: back into it, so a worktree being cleaned up cannot take his work with it.
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")

SCAN = MAIN / "benchmarks" / "omr-scan-e2e-2026-09"
WORKS = SCAN / "works.json"

#: The five rows this tool is for.  ⚠️ NO MAHLER: its printed one-line
#: percussion staves break a positional part->staff join, which is why
#: works.json gives Mahler a `condensation` block instead of a `staves` map.
#: That is research, not confirmation.
ROWS = [
    "beethoven-sym5-mvt1-984073-p3",
    "beethoven-sym5-mvt1-984073-p4",
    "beethoven-sym5-mvt1-575951-p3",
    "beethoven-sym5-mvt1-575951-p4",
    "brahms-sym1-mvt1-317803-p2",
]

# ─── The five rows that were called research, 2026-09-06 ────────────────────
#
# ⚠️ THE COMMENT ABOVE USED TO SAY "NO MAHLER", and the reason it gave —
# "its printed one-line percussion staves break a positional part->staff join"
# — is true of `scan_eval.note_recall` and NOT of `page_normalise`, which is the
# consumer the `entire staff` bucket is about and which never sees the
# prediction at all.  Measured: all four Mahler rows normalise, worth 4,135 of
# their 5,307 `entire staff` edits.  See
# `benchmarks/omr-staves-map-completion-2026-09/FINDINGS.md`.
#
# They are listed apart because THREE things differ from the five above:
#
#   * the proposal comes from `condensation.staves_as_printed` (p2) or from the
#     row's own `notes` (p3/p4/p5), transcribed in `candidate_maps.py`, not
#     from `systems_as_printed`, which these rows do not have;
#   * the one-line percussion staves are NOT in the run's artefact — the
#     detector finds them and `measure_extractor.extract_measures` skips them
#     (`if len(s.line_ys) >= 5`) — so their bands are recovered by re-running
#     `detect_staves` on the same render;
#   * a map entry carries `lines`, because 1 vs 5 is exactly what tells a
#     positional consumer which entries have no predicted part to pair with.
RESEARCH_ROWS = [
    "mahler-sym5-mvt1-local-p2",
    "mahler-sym5-mvt1-local-p3",
    "mahler-sym5-mvt1-local-p4",
    "mahler-sym5-mvt1-local-p5",
    "bach-brandenburg3-mvt1-468678-p1",
]

#: Where a canonical `.reconciliation.omr.json` may live, best first.  The
#: reconciliation worktree holds the artefacts behind the quoted 0.8444; the
#: main fixtures dir holds whatever the last local run left.  Both are read
#: only, and which one supplied a row is recorded per row.
FIXTURE_DIRS = [
    (MAIN / ".claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09"
            "/fixtures", "reconciliation"),
    (SCAN / "fixtures", "main-checkout"),
]

DPI = 600

#: How much of the page width a margin crop keeps.  The instrument name and the
#: clef both live in the first fifth; a bit more gives the first bar or two for
#: context without making the image unreadable at screen size.
CROP_WIDTH_FRACTION = 0.34

#: Padding above and below a staff band, in multiples of the band's own height.
#: Enough that a neighbour is visibly a neighbour, so a wrongly-boxed band is
#: obvious rather than plausible.
CROP_PAD_BANDS = 0.85


def default_cache() -> Path:
    return Path.home() / ".cache" / "reengrave-staves-map"


# ------------------------------------------------------------------ works.json

def load_rows() -> dict[str, dict]:
    doc = json.loads(WORKS.read_text())
    rows = doc["rows"]
    by_id = {r["row_id"]: r for r in rows}
    # `same-as:` deferral, the idiom works.json already uses for two scans of
    # one plate.  Resolved here so the UI never has to know about it.
    for row in rows:
        for key in ("staves", "systems_as_printed", "condensation"):
            v = row.get(key)
            if isinstance(v, str) and v.startswith("same-as:"):
                target = v.split(":", 1)[1]
                resolved = by_id[target].get(key)
                if isinstance(resolved, dict):
                    resolved = {"_same_as": target, **resolved}
                row[key] = resolved
                row.setdefault("_same_as", {})[key] = target
    return by_id


def systems_of(row: dict) -> list[dict]:
    """`systems_as_printed` as an ordered list of {system, staves:[{name,parts}]}."""
    sap = row.get("systems_as_printed") or {}
    out = []
    for key in sorted(k for k in sap if k.startswith("system_")):
        out.append({"system": key, "staves": sap[key]})
    return out


def propose(row: dict, n_parts: int) -> dict:
    """The page-level map to put in front of the human.

    A `staves` map has ONE entry per printed staff of the PAGE and must name
    every reference part (`page_normalise.IncompleteMap`).  `systems_as_printed`
    has one lineup per SYSTEM and those lineups differ — that is exactly why
    these rows have no `staves` map.  So the proposal is the system whose
    lineup names the most distinct parts, and the disagreement with the other
    systems is reported rather than smoothed over.
    """
    systems = systems_of(row)
    if not systems:
        return {"staves": [], "source": None, "note": "no systems_as_printed"}

    def named(sys_) -> set[int]:
        return {i for st in sys_["staves"] for i in st["parts"]}

    best = max(systems, key=lambda s: (len(named(s)), len(s["staves"])))
    covered = named(best)
    conflicts = []
    for s in systems:
        if s is best:
            continue
        missing = sorted(named(s) - covered)
        extra_staves = [st["name"] for st in s["staves"]
                        if st["name"] not in {b["name"] for b in best["staves"]}]
        if missing or extra_staves:
            conflicts.append({
                "system": s["system"],
                "parts_this_system_names_that_the_proposal_does_not": missing,
                "staves_only_in_this_system": extra_staves,
            })
    return {
        "staves": [{"name": st["name"], "parts": list(st["parts"])}
                   for st in best["staves"]],
        "source": best["system"],
        "n_systems": len(systems),
        "parts_named": sorted(covered),
        "parts_unnamed": sorted(set(range(n_parts)) - covered),
        "conflicts": conflicts,
    }


# ------------------------------------------------------------------- fixtures

def find_fixture(row_id: str, suffix: str) -> tuple[Path, str] | tuple[None, None]:
    """The canonical artefact for a row, and which store it came from."""
    for base, origin in FIXTURE_DIRS:
        hits = sorted(base.glob(f"{row_id}*{suffix}"))
        # Prefer the reconciliation tag by name where several arms are present:
        # it is the run behind the quoted pooled figure.
        hits.sort(key=lambda p: (0 if ".reconciliation." in p.name else 1, p.name))
        if hits:
            return hits[0], origin
    return None, None


def one_line_bands(pdf: Path, page_index: int) -> list[dict]:
    """The PRINTED one-line percussion staves, which the run's artefact lacks.

    ⚠️ THEY ARE NOT MISSED BY DETECTION. `staff_detector._single_line_staff_rows`
    finds them on purpose, full width, in the right slots — measured on the four
    Mahler pages: 2, 2, 3 and 4 of them, and their `staff_index` values are
    exactly the gaps in the artefact's own numbering. What drops them is
    `measure_extractor.extract_measures`, whose `if len(s.line_ys) >= 5` is a
    documented decision ("a cell is canonicalised by its staff's five-line span
    and a single rule has none"), so they never reach a measure cell, the
    exported score, or the JSON the UI reads.

    A single rule has ZERO height, so a band drawn at its own extent would crop
    to nothing. The band is opened to the page's own line spacing, which is what
    makes the printed rule and its rest visible in the crop.
    """
    sys.path.insert(0, str(MAIN))
    from tools.omr.preprocessing import render_page                # noqa: E402
    from tools.omr.staff_detector import detect_staves             # noqa: E402

    pws = detect_staves(render_page(str(pdf), page_index, dpi=DPI))
    spacing = None
    for st in pws.staves:
        if len(st.line_ys) >= 5:
            spacing = (max(st.line_ys) - min(st.line_ys)) / 4.0
            break
    spacing = spacing or 20.0
    out = []
    for st in pws.staves:
        if len(st.line_ys) >= 5:
            continue
        y = float(st.line_ys[0])
        out.append({"staff_index": st.staff_index,
                    "y0": y - 2 * spacing, "y1": y + 2 * spacing,
                    "x0": float(st.x_start), "x1": float(st.x_end),
                    "lines": 1, "printed_rule_y": y,
                    "clef": None, "instrument": None,
                    "instrument_source": "one-line percussion rule "
                                         "(recovered by re-running "
                                         "detect_staves; absent from the run's "
                                         "own artefact by design)"})
    return out


def staff_bands(omr_json: Path, extra: list[dict] | None = None) -> dict:
    """Detected staff bands, per system, in the DESKEWED 600 dpi page frame.

    `extra` splices in bands the artefact does not carry — the one-line
    percussion rules — by `staff_index`, which is the artefact's own numbering
    and has the gaps to receive them. Every spliced band is marked `lines: 1`.
    """
    doc = json.loads(omr_json.read_text())
    if doc.get("dpi") != DPI:
        raise SystemExit(f"{omr_json.name}: dpi is {doc.get('dpi')}, expected {DPI}")
    pages = doc["pages"]
    if len(pages) != 1:
        raise SystemExit(f"{omr_json.name}: expected one page, got {len(pages)}")
    page = pages[0]
    systems = []
    for s in page["systems"]:
        staves = []
        for st in s["staves"]:
            g = st["staff_geometry"]
            ys = g["line_ys_page"]
            staves.append({
                "staff_index": st["staff_index"],
                "y0": float(min(ys)), "y1": float(max(ys)),
                "x0": float(g["x_start"]), "x1": float(g["x_end"]),
                "clef": st.get("clef"),
                "instrument": st.get("instrument"),
                "instrument_source": st.get("instrument_source"),
            })
        systems.append({"system_index": s.get("system_index", len(systems)),
                        "staves": staves})
    for band in extra or []:
        # The artefact numbers staves across the PAGE, and a one-line rule's
        # index is a gap in that numbering — so the band goes into the system
        # whose indices bracket it, at the position its index names.
        target = None
        for s in systems:
            idx = [st["staff_index"] for st in s["staves"]]
            if idx and min(idx) <= band["staff_index"] <= max(idx):
                target = s
                break
        if target is None:
            target = systems[-1] if systems else None
        if target is None:
            continue
        target["staves"].append(band)
        target["staves"].sort(key=lambda st: st["staff_index"])
    return {
        "page_index": page["page_index"],
        "page_size_px": page["page_size_px"],
        "skew_corrected_deg": page.get("skew_corrected_deg", 0.0),
        "n_staves": sum(len(s["staves"]) for s in systems),
        "systems": systems,
        "artefact": str(omr_json),
    }


def reference_parts(truth_xml: Path) -> dict:
    """The part list `staves[i].parts` indexes, with names, cross-checked.

    music21 supplies the INDEX SPACE (it is what `page_normalise` iterates);
    ElementTree supplies the printed names.  A count disagreement means the two
    do not index the same thing and the row must not be mapped blind.
    """
    from music21 import converter  # slow import; only the cache pays it

    score = converter.parse(str(truth_xml))
    m21 = list(score.parts)

    root = ET.parse(str(truth_xml)).getroot()
    sp = root.findall(".//{*}part-list/{*}score-part")

    parts = []
    for i, p in enumerate(m21):
        e = sp[i] if i < len(sp) else None
        name = abbrev = None
        if e is not None:
            n = e.find("{*}part-name")
            a = e.find("{*}part-abbreviation")
            name = (n.text or "").strip() if n is not None else None
            abbrev = (a.text or "").strip() if a is not None else None
        parts.append({
            "index": i,
            "name": name or (p.partName or f"part {i}"),
            "abbrev": abbrev,
            "m21_partName": p.partName,
        })
    return {
        "source": str(truth_xml),
        "n_parts_music21": len(m21),
        "n_parts_score_part_elements": len(sp),
        "index_space": "music21 Score.parts — the list page_normalise iterates",
        "agrees": len(m21) == len(sp),
        "parts": parts,
    }


# --------------------------------------------------------------------- images

def render(pdf: Path, page_index: int):
    sys.path.insert(0, str(MAIN))
    from tools.omr.preprocessing import render_page  # noqa: E402
    return render_page(pdf, page_index, dpi=DPI)


def _font(size: int):
    from PIL import ImageFont
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc",
                 "/Library/Fonts/Arial.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def strip_crop_geometry(staves) -> dict:
    """WHERE the system strip was cut, and by how much it was shrunk.

    ⚠️ THE ONE PLACE THIS IS COMPUTED. `write_images` cuts the strip with it and
    the confirmation UI's overlay positions itself with it, so the marker cannot
    drift away from the crop it is drawn on. It used to be reimplemented in
    JavaScript under a comment claiming "same arithmetic build_cache.py used" —
    which was true of the numbers and false of the structure, and a
    reimplementation only has to be right until somebody edits one copy.

    `y_off` is the page-pixel row the strip starts at; `divisor` is the resize
    factor applied afterwards. A band's y in the SAVED strip is therefore
    `(int(y) - y_off) // divisor`, which is exactly what the boxes are drawn at.
    """
    top = int(min(st["y0"] for st in staves))
    bot = int(max(st["y1"] for st in staves))
    band_h = max(1.0, (bot - top) / max(1, len(staves)))
    pad = int(band_h * 0.6)
    return {"y_off": max(0, top - pad), "y_end": bot + pad, "divisor": 2}


def write_images(page_img, geom: dict, out_dir: Path, force: bool) -> dict:
    from PIL import Image, ImageDraw

    out_dir.mkdir(parents=True, exist_ok=True)
    full = Image.fromarray(page_img.rgb)
    W, H = full.size
    crop_w = int(W * CROP_WIDTH_FRACTION)

    files = {"staves": {}, "systems": {}}

    for sysi, s in enumerate(geom["systems"]):
        # ---- the system's whole margin strip, every band boxed and indexed
        crop = strip_crop_geometry(s["staves"])
        y_off = crop["y_off"]
        strip = full.crop((0, y_off, crop_w, min(H, crop["y_end"])))
        # ⚠️ Box and label AFTER the downscale, not before: drawing at full
        # resolution and then halving makes the index labels unreadable, which
        # is the one thing the strip exists to say.
        strip = strip.resize((max(1, strip.width // crop["divisor"]),
                              max(1, strip.height // crop["divisor"])))
        d = ImageDraw.Draw(strip)
        font = _font(26)
        for k, st in enumerate(s["staves"]):
            y0 = (int(st["y0"]) - y_off) // crop["divisor"]
            y1 = (int(st["y1"]) - y_off) // crop["divisor"]
            d.rectangle([44, y0, strip.width - 3, y1],
                        outline=(220, 30, 30), width=3)
            d.text((4, (y0 + y1) // 2 - 14), f"{k}", fill=(220, 30, 30), font=font)
        name = f"system{sysi}.png"
        dest = out_dir / name
        if force or not dest.is_file():
            strip.save(dest)
        files["systems"][str(sysi)] = name

        # ---- one crop per staff, its own band boxed
        for k, st in enumerate(s["staves"]):
            h = st["y1"] - st["y0"]
            t = int(st["y0"] - h * CROP_PAD_BANDS)
            b = int(st["y1"] + h * CROP_PAD_BANDS)
            t, b = max(0, t), min(H, b)
            crop = full.crop((0, t, crop_w, b))
            dd = ImageDraw.Draw(crop)
            dd.rectangle([3, int(st["y0"]) - t, crop_w - 4, int(st["y1"]) - t],
                         outline=(220, 30, 30), width=5)
            name = f"staff{st['staff_index']}.png"
            dest = out_dir / name
            if force or not dest.is_file():
                crop.save(dest)
            files["staves"][str(st["staff_index"])] = name

    return files


# ----------------------------------------------------------------------- main

def research_proposal(row_id: str, n_parts: int) -> dict:
    """The proposal for a RESEARCH_ROW, transcribed from works.json's own prose.

    These rows have no `systems_as_printed`; what they have is a structured
    `condensation.staves_as_printed` (Mahler p2) or an instrument-by-instrument
    allocation written out in the row's `notes` (p3/p4/p5), drafted by the
    sessions that verified those windows against the print.
    `candidate_maps.py` transcribes those, with the source quoted per row, and
    marks its own two conventions (`absent` folds, and the entries dropped
    because the reference has no part for them).

    ⚠️ THE FOLDS ARE SHOWN AS FOLDS. A part with no printed staff on this page
    is listed separately in `absent`, so the human confirms the printed
    allocation and the fold as two different things.
    """
    # Beside THIS file's own checkout, not MAIN's: the maps are this branch's
    # work and the cache must be buildable before anything is merged.
    sys.path.insert(0, str(BENCH.parent / "omr-staves-map-completion-2026-09"))
    import candidate_maps                                        # noqa: E402

    entries = candidate_maps.CANDIDATES[row_id]
    staves = []
    for spec in entries:
        staves.append({
            # SORTED, because `merge_additions.shape_problems` refuses an entry
            # whose `parts` is not sorted-unique and every already-merged row
            # satisfies that. ⚠️ It is not free: `page_normalise` keeps
            # `parts[0]` and merges the rest into it, so sorting a tacet fold
            # ahead of the printed part makes a SILENT part's bar the one that
            # survives a `silent_all` measure. Measured on the three rows that
            # have folds — sorted costs +8 edits of 7,668 (p3 -3, p4 +19,
            # p5 -8), all of it rest spelling — so works.json's convention
            # wins. See price-maps.json, arm `sorted-parts`.
            "name": spec["name"],
            "parts": sorted(list(spec["parts"])
                            + list(spec.get("absent") or [])),
            "printed_parts": list(spec["parts"]),
            "absent_parts": list(spec.get("absent") or []),
            "lines": spec.get("lines", 5),
        })
    covered = {i for s in staves for i in s["parts"]}
    return {
        "staves": staves,
        "source": "candidate_maps (transcribed from works.json's own prose)",
        "n_systems": 1,
        "parts_named": sorted(covered),
        "parts_unnamed": sorted(set(range(n_parts)) - covered),
        "conflicts": [],
        "unrepresentable_printed_staves":
            candidate_maps.UNREPRESENTABLE.get(row_id, []),
    }


def _research_note(row_id: str, row: dict, prop: dict, refs: dict) -> str:
    """The row's own `n_staves_note`, plus what a RESEARCH_ROW's map does extra.

    The UI prints this under the system strips, and it is the only place the
    human is told that some entries carry parts the page does NOT print. Left
    exactly as works.json wrote it for the original five rows.
    """
    base = row["page"].get("n_staves_note") or ""
    if row_id not in RESEARCH_ROWS:
        return base
    names = {p["index"]: p["name"] for p in refs["parts"]}
    folds = []
    for s in prop["staves"]:
        if s.get("absent_parts"):
            folds.append(f"{s['name']} also carries "
                         + ", ".join(f"{i} {names.get(i, '?')}"
                                     for i in s["absent_parts"]))
    extra = []
    if folds:
        extra.append(
            "TACET FOLDS (this branch's convention, not works.json's): a "
            "reference part with NO printed staff on this page is folded onto "
            "a nominated staff, because page_normalise refuses to drop a part. "
            "Every one is silent over this window, and moving them to a "
            "different staff was measured to leave the derived truth "
            "unchanged. Here: " + "; ".join(folds) + ".")
    for u in prop.get("unrepresentable_printed_staves") or []:
        # `candidate_maps.UNREPRESENTABLE` carries {name, after, lines, reason}
        # so the UI can place a greyed row; a bare string is still accepted.
        extra.append("PRINTED BUT UNMAPPABLE: "
                     + (f"{u['name']} — {u['reason']}"
                        if isinstance(u, dict) else str(u)))
    return " ".join(x for x in ([base] + extra) if x)


def build_row(row_id: str, row: dict, cache: Path, force: bool) -> dict:
    out_dir = cache / row_id
    omr, origin = find_fixture(row_id, ".omr.json")
    if omr is None:
        return {"row_id": row_id, "usable": False,
                "reason": "no <row>.omr.json artefact found in any fixture store; "
                          "the printed staff count must come from the run"}
    truth, _ = find_fixture(row_id, ".truth.musicxml")
    if truth is None:
        return {"row_id": row_id, "usable": False,
                "reason": "no <row>.truth.musicxml — cannot enumerate the "
                          "reference parts in page_normalise's index space"}

    pdf = MAIN / "library" / row["edition"]["catalog_path"]
    page_index = row["page"]["pdf_page_index"]
    research = row_id in RESEARCH_ROWS

    extra = one_line_bands(pdf, page_index) if research else None
    geom = staff_bands(omr, extra)
    geom["artefact_origin"] = origin
    geom["one_line_bands_spliced"] = len(extra or [])
    refs = reference_parts(truth)

    prop = (research_proposal(row_id, refs["n_parts_music21"]) if research
            else propose(row, refs["n_parts_music21"]))
    if geom["page_index"] != page_index:
        return {"row_id": row_id, "usable": False,
                "reason": f"artefact is page {geom['page_index']}, works.json "
                          f"says {page_index}"}

    needed = out_dir / "system0.png"
    if force or not needed.is_file():
        page_img = render(pdf, page_index)
        if [page_img.width, page_img.height] != list(geom["page_size_px"]):
            return {"row_id": row_id, "usable": False,
                    "reason": f"render is {page_img.width}x{page_img.height}, "
                              f"the run recorded {geom['page_size_px']} — the "
                              f"staff bands would not land on the ink"}
        files = write_images(page_img, geom, out_dir, force)
    else:
        files = {"staves": {str(st["staff_index"]): f"staff{st['staff_index']}.png"
                            for s in geom["systems"] for st in s["staves"]},
                 "systems": {str(i): f"system{i}.png"
                             for i in range(len(geom["systems"]))}}

    warnings = []
    if not refs["agrees"]:
        warnings.append(
            f"music21 parses {refs['n_parts_music21']} parts but the file "
            f"declares {refs['n_parts_score_part_elements']} <score-part> "
            f"elements. The index space and the names do NOT line up — do not "
            f"map this row until that is resolved.")
    if row["page"]["n_staves"] != geom["n_staves"]:
        warnings.append(
            f"works.json says {row['page']['n_staves']} printed staves, the run "
            f"detected {geom['n_staves']}. The map is over PRINTED staves; "
            f"read the strips before trusting the band boxes.")
    if refs["n_parts_music21"] != row["reference"].get("n_parts"):
        warnings.append(
            f"works.json says the reference has {row['reference'].get('n_parts')} "
            f"parts, the trimmed truth parses {refs['n_parts_music21']}.")

    return {
        "row_id": row_id,
        "usable": not warnings or refs["agrees"],
        "blocking": not refs["agrees"],
        "warnings": warnings,
        "label": row.get("label"),
        "edition": row["edition"]["catalog_path"],
        "pdf": str(pdf),
        "page_index": page_index,
        "printed_page": row["page"].get("printed_page"),
        "n_staves_note": _research_note(row_id, row, prop, refs),
        "window": {k: row["window"].get(k)
                   for k in ("first_ref_measure", "last_ref_measure",
                             "confidence", "established_by")},
        "reference": {"catalog_path": row["reference"]["catalog_path"], **refs},
        "detected": geom,
        # A RESEARCH_ROW has no `systems_as_printed`. Mahler's four pages are one
        # system each, so the proposal IS that system's lineup and is offered
        # under the same key — which is what lets the UI's crop panel join a map
        # entry to its printed instance by PARTS rather than by ordinal.
        # ⚠️ Bach is two systems of the SAME lineup, and both are offered, so a
        # slot shows both printings.
        "systems_as_printed": (
            systems_of(row) if row_id not in RESEARCH_ROWS
            else [{"system": f"system_{i}",
                   "staves": [{"name": s["name"], "parts": s["parts"]}
                              for s in prop["staves"]]}
                  for i in range(len(geom["systems"]))]),
        "systems_as_printed_note": (
            (row.get("systems_as_printed") or {}).get("_purpose")
            if row_id not in RESEARCH_ROWS else
            "SYNTHESISED from the proposal — these rows record their hand-read "
            "allocation as `condensation.staves_as_printed` (Mahler p2) or in "
            "`notes` (p3/p4/p5), not as `systems_as_printed`."),
        "same_as": (row.get("_same_as") or {}).get("systems_as_printed"),
        "proposal": prop,
        "images": files,
        "notes": row.get("notes"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", nargs="+", default=None)
    ap.add_argument("--research", action="store_true",
                    help="build the five rows that were called research "
                         "(the four Mahler pages and Bach Brandenburg 3 p1)")
    ap.add_argument("--all", action="store_true",
                    help="build both sets")
    ap.add_argument("--cache-dir", default=str(default_cache()))
    ap.add_argument("--force", action="store_true",
                    help="re-render the PNGs even where they exist")
    args = ap.parse_args(argv)
    if args.rows is None:
        args.rows = (ROWS + RESEARCH_ROWS if args.all
                     else RESEARCH_ROWS if args.research else ROWS)

    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    by_id = load_rows()

    built = []
    for rid in args.rows:
        if rid not in by_id:
            print(f"  !! {rid}: not a row of works.json", file=sys.stderr)
            continue
        print(f"  .. {rid}", flush=True)
        entry = build_row(rid, by_id[rid], cache, args.force)
        for w in entry.get("warnings") or []:
            print(f"     WARN {w}")
        if not entry.get("usable"):
            print(f"     UNUSABLE: {entry.get('reason') or 'see warnings'}")
        built.append(entry)

    index = {
        "generated_by": "benchmarks/omr-staves-map-2026-09/build_cache.py",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "main_checkout": str(MAIN),
        "works_json": str(WORKS),
        "dpi": DPI,
        "rows": built,
    }
    (cache / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    print(f"\nwrote {cache / 'index.json'}  ({len(built)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
