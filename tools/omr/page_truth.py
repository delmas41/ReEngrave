"""What is ACTUALLY PRINTED on a page, exactly — for pages we render ourselves.

Every accuracy number this project reports is taken at the far end of the
pipeline: our exported MusicXML against a truth MusicXML. That measures
recognition and serialisation TOGETHER, which is why nine separate "detected,
then dropped on the way out" bugs have had to be found by forensics — a signal
read perfectly and lost in the exporter looks identical, in OMR-NED, to one
never read at all.

Splitting them needs a truth about the PAGE rather than about the encoding, and
for a page we render there is an exact one available for free: Verovio knows
where it put every glyph. With `svgBoundingBoxes` it emits, per notation object,
a `<rect>` in the same frame as the glyph it drew.

⚠️ **A PAGE TRUTH IS NOT AN ENCODING TRUTH, AND THE DIFFERENCE IS THE POINT.**
Measured on the Brahms 1 fixture, rendered from its own truth file:

    dynamics   19 `dynamicForte` glyphs   vs   19 `<dynamics>`      agree
    G clefs    28 `gClef` glyphs          vs   14 `<sign>G</sign>`  differ
    slurs      82 drawn arcs              vs  164 `<slur>` tags     differ

The clefs differ because a clef is PRINTED at the start of every system and
DECLARED once. The slurs differ because MusicXML writes a start and a stop and
the engraver draws one arc. Neither is an error. A reader sees 28 clefs and 82
arcs, and that is the number a recognition score must be taken against.

⚠️ **THIS ONLY WORKS WHERE WE MAKE THE PAGE.** It says nothing about a scanned
IMSLP edition, and there is no public symbol-level ground truth for real
printed scans to borrow — DeepScoresV2 is digitally rendered and MUSCIMA++ is
handwritten. So this separates reading from reproduction on ENGRAVED input and
leaves scan robustness exactly where it was.

    python3 -m tools.omr.page_truth truth.musicxml --out-dir fixtures/ --dpi 300
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

#: Verovio options. Fixed, because the page truth and the rendered page must
#: come from ONE render — a truth measured against a different layout than the
#: one the detector read is not a truth.
VEROVIO_OPTIONS: dict[str, Any] = {
    "pageWidth": 2000,
    "pageHeight": 2800,
    "scale": 40,
    "adjustPageHeight": True,
    "svgBoundingBoxes": True,
    "footer": "none",
    "header": "none",
}

#: The notation classes worth scoring, and what each is called downstream. The
#: value is the FAMILY the detector's own class names collapse to
#: (`_detector_family`), so both sides are compared in one vocabulary.
SCORED_CLASSES: dict[str, str] = {
    "note": "notehead",
    "rest": "rest",
    "mRest": "rest",
    "accid": "accidental",
    "keySig": "key_signature",
    "meterSig": "time_signature",
    "clef": "clef",
    "dynam": "dynamic",
    "hairpin": "hairpin",
    "flag": "flag",
    "dots": "augmentation_dot",
    "slur": "slur",
    "tie": "tie",
    "beam": "beam",
    "barLine": "barline",
}

#: Classes deliberately not scored, with the reason — an inventory, not a
#: silence. `staff`/`system`/`layer` are layout containers, not symbols;
#: `stem` and `beam` are classical-CV territory the detector never boxes;
#: `text`/`label`/`dir` are words, which `direction_text` reads with OCR.
NOT_SCORED: dict[str, str] = {
    "staff": "a layout container, not a printed symbol",
    "system": "a layout container",
    "layer": "a layout container",
    "measure": "a layout container",
    "chord": "a grouping of notes already scored individually",
    "stem": "detected by classical CV, never boxed by the detector",
    "label": "the instrument name — read by the margin-label reader, not YOLO",
    "text": "free text — read by `direction_text` with OCR",
    "dir": "a direction word — read by `direction_text` with OCR",
    "rend": "a text-formatting wrapper",
    "syl": "lyric text",
}

_BBOX_RE = re.compile(
    r'<g id="bbox-[^"]*" class="([^"]*?) bounding-box">\s*'
    r'<rect x="([-\d.]+)" y="([-\d.]+)" height="([-\d.]+)" width="([-\d.]+)"'
)
_USE_RE = re.compile(
    r'<use xlink:href="#(E[0-9A-F]{3})[^"]*" transform="translate\(([-\d.]+),\s*([-\d.]+)\)'
)
_ROOT_RE = re.compile(r'<svg width="([\d.]+)px" height="([\d.]+)px"')
_INNER_VIEWBOX_RE = re.compile(r'<svg[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"')
#: ⚠️ Verovio wraps the whole page in `<g class="page-margin"
#: transform="translate(mx, my)">`, and every bbox and glyph anchor below it is
#: expressed INSIDE that translate. Missing it puts the entire truth a constant
#: distance off the ink — measured on the Brahms fixture, 500 internal units at
#: 300 dpi is 62.5 px, against a staff space of 22.5, so nothing matched at any
#: tolerance while the symbol COUNTS agreed almost exactly (noteheads 259 vs
#: 259). Counts agreeing while positions do not is the signature of a frame
#: error, never of a recognition result.
_DEF_RE = re.compile(
    r'<g id="(E[0-9A-F]{3})[^"]*">\s*<path transform="scale\(1,-1\)" d="([^"]+)"'
)
_USE_FULL_RE = re.compile(
    r'<use xlink:href="#(E[0-9A-F]{3})[^"]*" transform="translate\(([-\d.]+),\s*([-\d.]+)\)'
    r'(?:\s*scale\(([-\d.]+),\s*([-\d.]+)\))?'
)
_NUM_RE = re.compile(r'-?\d+(?:\.\d+)?')
_PAGE_MARGIN_RE = re.compile(
    r'<g class="page-margin" transform="translate\(([-\d.]+),\s*([-\d.]+)\)"'
)


class PageTruthError(RuntimeError):
    pass


def glyph_box_templates(
    rects: list[tuple[str, dict]], glyphs: list[dict]
) -> dict[str, dict[str, float]]:
    """`codepoint -> box offset and size relative to the glyph's anchor`.

    ⚠️ A GLYPH'S ANCHOR IS NOT ITS CENTRE, and assuming it was is a real
    measurement error rather than a rounding one. SMuFL puts a glyph's origin
    where the notation needs it — a notehead's on its own vertical middle, a
    FLAT's down at the staff position it alters, with the body reaching upward.
    Synthesising a square box around the anchor put the key-signature truth 0.59
    staff spaces high and scored a correctly-read signature at **F1 0.078**.

    So the box is CALIBRATED from Verovio's own rects rather than derived. Most
    glyphs appear somewhere as a single-glyph element that does get a rect — a
    flat as an inline `accid`, a digit nowhere, a forte nowhere — and the offset
    from anchor to rect is a property of the glyph, identical at every
    occurrence. Learn it there, apply it inside the group boxes that have no
    rects of their own.

    ⚠️ Deliberately NOT read off the font outline in `<defs>`: those paths use
    RELATIVE curve commands (`c` not `C`), so a min/max over their numbers is
    not a bounding box at all. Measured, that mistake put noteheads 0.66 staff
    spaces right of Verovio's own rect for the same glyph — which is how it was
    caught, because the `note` rects are a free check on any method here.
    """
    singles: dict[str, list[tuple[float, float, float, float]]] = {}
    for _cls, rect in rects:
        inside = [g for g in glyphs
                  if rect["x"] <= g["x"] <= rect["x"] + rect["w"]
                  and rect["y"] <= g["y"] <= rect["y"] + rect["h"]]
        if len(inside) != 1:
            continue
        g = inside[0]
        singles.setdefault(g["smufl"], []).append(
            (rect["x"] - g["x"], rect["y"] - g["y"], rect["w"], rect["h"])
        )
    out: dict[str, dict[str, float]] = {}
    for cp, vals in singles.items():
        vals.sort()
        dx, dy, w, h = vals[len(vals) // 2]
        out[cp] = {"dx": dx, "dy": dy, "w": w, "h": h}
    return out


def _render_svgs(musicxml: Path) -> list[str]:
    try:
        import verovio  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise PageTruthError("verovio is not installed") from exc
    tk = verovio.toolkit()
    tk.setOptions(dict(VEROVIO_OPTIONS))
    if not tk.loadData(musicxml.read_text()):
        raise PageTruthError(f"verovio could not load {musicxml}")
    return [tk.renderToSVG(i + 1) for i in range(tk.getPageCount())]


def _scale_to_css_px(svg: str) -> tuple[float, float, float]:
    """`(units_per_css_px, css_width, css_height)`.

    Verovio draws in an internal unit space and declares the page in CSS px on
    the root element. Everything below is expressed in the internal units, so
    one conversion carries the whole page.
    """
    root = _ROOT_RE.search(svg)
    inner = _INNER_VIEWBOX_RE.search(svg[svg.find("<defs"):] or svg)
    if not root:
        raise PageTruthError("no root <svg width=..px height=..px>")
    css_w, css_h = float(root.group(1)), float(root.group(2))
    if inner:
        units_w = float(inner.group(1))
    else:  # the root itself carries the viewBox (svgViewBox=True)
        m = _INNER_VIEWBOX_RE.search(svg)
        units_w = float(m.group(1)) if m else css_w
    return units_w / css_w, css_w, css_h


#: Groups the engraver boxes as ONE object while the detector boxes each member
#: — a key signature is one `keySig` rect over three flats, and `ff` is one
#: `dynam` rect over two letters. Scoring those against each other would report
#: a recall of 1/3 for a perfectly read signature. They are expanded into their
#: member GLYPHS instead, using the glyph anchors inside the group's box.
#: `(family, allowed SMuFL codepoint range)`. ⚠️ THE RANGE IS LOAD-BEARING, not
#: belt-and-braces. These group boxes sit flush against their neighbours — a key
#: signature abuts the time signature, a dynamic sits under a notehead — so
#: selecting glyphs by POSITION alone leaks: measured on the Brahms fixture it
#: put 30 time-signature digits inside `keySig` and 4 noteheads inside `dynam`.
#: The ranges are SMuFL's own blocks (accidentals E260-E26F, time signatures
#: E080-E09F, dynamics E520-E54F), so this is the standard's structure rather
#: than a threshold.
_EXPAND_TO_GLYPHS: dict[str, tuple[str, tuple[int, int]]] = {
    "keySig": ("key_accidental", (0xE260, 0xE26F)),
    "meterSig": ("time_signature_digit", (0xE080, 0xE09F)),
    "dynam": ("dynamic_letter", (0xE520, 0xE54F)),
}


def symbols_in_svg(
    svg: str, px_per_css: float
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every scored notation object on one page, boxed in IMAGE pixels."""
    units_per_css, _w, _h = _scale_to_css_px(svg)
    k = px_per_css / units_per_css          # internal units -> image px
    m = _PAGE_MARGIN_RE.search(svg)
    mx, my = (float(m.group(1)) * k, float(m.group(2)) * k) if m else (0.0, 0.0)

    glyphs = [
        {"smufl": cp, "x": float(x) * k + mx, "y": float(y) * k + my}
        for cp, x, y in _USE_RE.findall(svg)
    ]

    all_rects = []
    for cls, x, y, h, w in _BBOX_RE.findall(svg):
        all_rects.append((cls.split()[0],
                          {"x": float(x) * k + mx, "y": float(y) * k + my,
                           "w": float(w) * k, "h": float(h) * k}))
    templates = glyph_box_templates(all_rects, glyphs)

    boxed, groups = [], []
    for head, rect in all_rects:
        if head in _EXPAND_TO_GLYPHS:
            groups.append((head, rect))
            continue
        family = SCORED_CLASSES.get(head)
        if family is not None:
            boxed.append({"class": head, "family": family, **rect})

    # A notehead's own box is the unit of size on the page — SMuFL sets it to
    # one staff space tall — so it is what a glyph with only an anchor gets.
    heads = [s["h"] for s in boxed if s["family"] == "notehead"]
    space = sorted(heads)[len(heads) // 2] if heads else 1.0

    for head, rect in groups:
        family, (lo, hi) = _EXPAND_TO_GLYPHS[head]
        inside = [
            g for g in glyphs
            if lo <= int(g["smufl"], 16) <= hi
            and rect["x"] - space <= g["x"] <= rect["x"] + rect["w"] + space
            and rect["y"] - space <= g["y"] <= rect["y"] + rect["h"] + space
        ]
        rows = sorted({round(g["y"], 1) for g in inside})
        for g in inside:
            tpl = templates.get(g["smufl"])
            if tpl is not None:
                boxed.append({
                    "class": g["smufl"], "family": family,
                    "x": g["x"] + tpl["dx"], "y": g["y"] + tpl["dy"],
                    "w": tpl["w"], "h": tpl["h"],
                })
            elif head == "meterSig" and rows:
                # A time-signature digit occurs NOWHERE ELSE on a page, so it
                # never gets a calibrating rect. It does not need one: a meter
                # is by definition its digits stacked and centred inside the
                # group box, which is a fact about the notation rather than a
                # guess about this engraver. One row per digit, split evenly.
                boxed.append({
                    "class": g["smufl"], "family": family,
                    "x": rect["x"], "y": g["y"] - rect["h"] / (2 * len(rows)),
                    "w": rect["w"], "h": rect["h"] / len(rows),
                })
            # else: unknown box, and a guessed one would be scored as measured.
            # ABSTAIN.
    return boxed, glyphs


def _svg_to_pdf(svg_path: Path, pdf_path: Path) -> None:
    """One page of PDF from one SVG, via librsvg.

    ⚠️ The whole point of this module is that the truth lands on the pixels the
    detector reads, so the coordinate chain is VERIFIED rather than assumed:
    librsvg maps CSS px to PDF points at 72/96, and a PDF point rasterises at
    dpi/72 — so image px = css px x dpi/96, which is exactly `px_per_css` in
    `build()`. Checked on the Brahms fixture at both 300 and 600 dpi:
    800 x 1767 css -> 600.00 x 1325.25 pt -> 2500 x 5522 and 5000 x 11044 px,
    all three exact. `test_page_truth.py` pins it.
    """
    exe = shutil.which("rsvg-convert")
    if not exe:
        raise PageTruthError(
            "rsvg-convert is required for the PDF the pipeline reads "
            "(`brew install librsvg`)"
        )
    subprocess.run([exe, "-f", "pdf", "-o", str(pdf_path), str(svg_path)],
                   check=True, capture_output=True)


def _merge_pdfs(parts: list[Path], out: Path) -> None:
    """One document, so a page index means the same thing to both sides."""
    import fitz  # type: ignore
    doc = fitz.open()
    for part in parts:
        with fitz.open(part) as src:
            doc.insert_pdf(src)
    doc.save(out)
    doc.close()


def _rasterize(svg_path: Path, png_path: Path, zoom: float) -> None:
    exe = shutil.which("rsvg-convert")
    if exe:
        subprocess.run(
            [exe, "-z", str(zoom), "-f", "png", "-o", str(png_path), str(svg_path)],
            check=True, capture_output=True,
        )
        return
    try:  # pragma: no cover - optional dependency
        import cairosvg  # type: ignore
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), scale=zoom)
        return
    except ImportError:
        pass
    raise PageTruthError(
        "no SVG rasteriser: install librsvg (`brew install librsvg`) or cairosvg"
    )


#: A family whose DRAWN count must agree with what the source encoding says is
#: printed, or the renderer is not engraving the same music the encoding
#: describes. `element` is the MusicXML element that states it.
_FIDELITY_CHECKS: dict[str, str] = {
    "accidental": "accidental",
}


def render_fidelity(musicxml: str, pages: list[dict]) -> dict[str, Any]:
    """Does the render draw what the encoding says is PRINTED?

    ⚠️ **VEROVIO DRAWS ONE ACCIDENTAL PER `<alter>`, NOT PER `<accidental>`** —
    measured on three fixtures: Brahms 1 has 54 `<accidental>` and 149
    `<alter>`, and Verovio drew 149; Beethoven 5 has **0** `<accidental>` and 13
    `<alter>`, and it drew 13. `<alter>` is the SOUNDING alteration, which a key
    signature already supplies, so a page rendered this way carries accidentals
    a real engraver would never print.

    That page truth is still exactly right about the page — the detector read
    those glyphs or missed them — but it is NOT a statement about real notation,
    and the recall it produces must not be read as one. It nearly was: the
    `accidental` family scored recall 0.257 and was about to be called this
    pipeline's largest reading gap.

    So the disagreement is measured and the family is declared unreliable rather
    than quietly scored. The tell that caught it: `wrong pitch` is zero on these
    works in OMR-NED, which cannot be true of a reader missing three quarters of
    the accidentals.
    """
    drawn: dict[str, int] = {}
    for page in pages:
        for s in page["symbols"]:
            drawn[s["family"]] = drawn.get(s["family"], 0) + 1
    out: dict[str, Any] = {"unreliable": [], "checks": {}}
    for family, element in _FIDELITY_CHECKS.items():
        encoded = len(re.findall(f"<{element}[ />]", musicxml))
        got = drawn.get(family, 0)
        ok = got == encoded
        out["checks"][family] = {"drawn": got, "encoded_as_printed": encoded,
                                 "agrees": ok}
        if not ok:
            out["unreliable"].append(family)
    return out


def build(musicxml: Path, out_dir: Path, dpi: int = 300) -> dict[str, Any]:
    """Render `musicxml` and write, side by side, the page and its truth.

    The zoom is chosen so the rendered page matches the DPI the pipeline
    rasterises at, and the truth is emitted in the SAME pixels — one render,
    one frame, nothing to reconcile afterwards.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = musicxml.name.split(".")[0]
    svgs = _render_svgs(musicxml)
    px_per_css = dpi / 96.0            # CSS px are 1/96 inch by definition

    pages, pdf_parts = [], []
    for i, svg in enumerate(svgs):
        svg_path = out_dir / f"{stem}-p{i + 1}.svg"
        png_path = out_dir / f"{stem}-p{i + 1}.png"
        pdf_part = out_dir / f"{stem}-p{i + 1}.pdf"
        svg_path.write_text(svg)
        _rasterize(svg_path, png_path, px_per_css)
        _svg_to_pdf(svg_path, pdf_part)
        pdf_parts.append(pdf_part)
        boxes, glyphs = symbols_in_svg(svg, px_per_css)
        _units, css_w, css_h = _scale_to_css_px(svg)
        pages.append({
            "page_index": i,
            "png": png_path.name,
            "image_w": round(css_w * px_per_css),
            "image_h": round(css_h * px_per_css),
            "symbols": boxes,
            "glyphs": glyphs,
        })

    pdf_path = out_dir / f"{stem}.pdf"
    _merge_pdfs(pdf_parts, pdf_path)
    for part in pdf_parts:
        part.unlink()

    truth = {
        "source_musicxml": str(musicxml),
        "pdf": pdf_path.name,
        "render_fidelity": render_fidelity(musicxml.read_text(), pages),
        "renderer": "verovio",
        "verovio_options": VEROVIO_OPTIONS,
        "dpi": dpi,
        "not_scored": NOT_SCORED,
        "pages": pages,
    }
    (out_dir / f"{stem}.pagetruth.json").write_text(json.dumps(truth, indent=1))
    return truth


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("musicxml", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()

    t = build(args.musicxml, args.out_dir, args.dpi)
    from collections import Counter
    for p in t["pages"]:
        c = Counter(s["family"] for s in p["symbols"])
        print(f"page {p['page_index'] + 1}: {p['image_w']}x{p['image_h']} px, "
              f"{len(p['symbols'])} symbols, {len(p['glyphs'])} glyphs")
        print("   ", dict(c.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
