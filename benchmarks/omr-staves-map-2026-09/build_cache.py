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


def staff_bands(omr_json: Path) -> dict:
    """Detected staff bands, per system, in the DESKEWED 600 dpi page frame."""
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


def write_images(page_img, geom: dict, out_dir: Path, force: bool) -> dict:
    from PIL import Image, ImageDraw

    out_dir.mkdir(parents=True, exist_ok=True)
    full = Image.fromarray(page_img.rgb)
    W, H = full.size
    crop_w = int(W * CROP_WIDTH_FRACTION)

    files = {"staves": {}, "systems": {}}

    for sysi, s in enumerate(geom["systems"]):
        # ---- the system's whole margin strip, every band boxed and indexed
        top = int(min(st["y0"] for st in s["staves"]))
        bot = int(max(st["y1"] for st in s["staves"]))
        band_h = max(1.0, (bot - top) / max(1, len(s["staves"])))
        pad = int(band_h * 0.6)
        y_off = max(0, top - pad)
        strip = full.crop((0, y_off, crop_w, min(H, bot + pad)))
        # ⚠️ Box and label AFTER the downscale, not before: drawing at full
        # resolution and then halving makes the index labels unreadable, which
        # is the one thing the strip exists to say.
        strip = strip.resize((max(1, strip.width // 2), max(1, strip.height // 2)))
        d = ImageDraw.Draw(strip)
        font = _font(26)
        for k, st in enumerate(s["staves"]):
            y0 = (int(st["y0"]) - y_off) // 2
            y1 = (int(st["y1"]) - y_off) // 2
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

    geom = staff_bands(omr)
    geom["artefact_origin"] = origin
    refs = reference_parts(truth)

    prop = propose(row, refs["n_parts_music21"])

    pdf = MAIN / "library" / row["edition"]["catalog_path"]
    page_index = row["page"]["pdf_page_index"]
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
        "n_staves_note": row["page"].get("n_staves_note"),
        "window": {k: row["window"].get(k)
                   for k in ("first_ref_measure", "last_ref_measure",
                             "confidence", "established_by")},
        "reference": {"catalog_path": row["reference"]["catalog_path"], **refs},
        "detected": geom,
        "systems_as_printed": systems_of(row),
        "systems_as_printed_note": (row.get("systems_as_printed") or {}).get("_purpose"),
        "same_as": (row.get("_same_as") or {}).get("systems_as_printed"),
        "proposal": prop,
        "images": files,
        "notes": row.get("notes"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", nargs="+", default=ROWS)
    ap.add_argument("--cache-dir", default=str(default_cache()))
    ap.add_argument("--force", action="store_true",
                    help="re-render the PNGs even where they exist")
    args = ap.parse_args(argv)

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
