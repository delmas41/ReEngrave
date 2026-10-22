"""Render a REAL meter change as a clean engraving, over several systems.

⚠️ WHY THIS IS NOT `orchestral_eval.excerpt`. That function shrinks the bar
range until LilyPond returns ONE PAGE, for a reason that is about the
EXPORTER: `export.to_musicxml` emits one `<part>` per (page, system, staff),
so a multi-page render scores the exporter's page handling rather than
recognition. **That reason does not apply here.** Nothing is scored against a
truth file; the question is what `Q.METER` decides per SYSTEM, and the carry
and the bar reader are *between*-system mechanisms — one page with one system
cannot exercise either. So this keeps every page and reuses the rest of
`excerpt`'s recipe verbatim (paper sized to the part count, staff size 16,
`musicxml2ly`).

⚠️ THE POINT OF AN ENGRAVED FIXTURE IS THAT LEGIBILITY IS NOT THE CONFOUND.
Every measurement of the meter mechanisms so far is on one scanned Litolff
print, where a movement start is either sparse or a dense tutti and the bars
cannot speak either way. Here the ink is perfect by construction, so a failure
is a failure of the RULE.

    python3 -m benchmarks.omr-staged-meter-engraved-2026-09.render_meter_change \
        --work beethoven-sym5-mvt4 --first 145 --last 175 --out-dir out/
"""
from __future__ import annotations

import argparse
import subprocess
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path

warnings.filterwarnings("ignore")

SCORE_DIR = Path("/Users/seanjohnson/Desktop/gradus-vercel/public/scores")


def meter_map(xml_path: Path) -> dict:
    """{measure number: "n/d"} for the FIRST part of a MusicXML file.

    ⚠️ Read back off the written file, never assumed from the source. music21's
    `measures()` carries the prevailing meter into the excerpt's first bar on
    WRITE, and a query against the in-memory Measure object says otherwise —
    so the file is the substrate and the object is not.
    """
    root = ET.parse(str(xml_path)).getroot()
    part = root.findall("{*}part")[0]
    out = {}
    for m in part.findall("{*}measure"):
        t = m.find("{*}attributes/{*}time")
        if t is not None:
            out[int(m.get("number"))] = "%s/%s" % (
                t.find("{*}beats").text, t.find("{*}beat-type").text)
    return out


def render(work_id: str, first: int, last: int, out_dir: Path) -> dict:
    from music21 import converter

    src = None
    for suffix in (".mxl", ".musicxml"):
        cand = SCORE_DIR / f"{work_id}{suffix}"
        if cand.is_file():
            src = cand
            break
    if src is None:
        raise FileNotFoundError(f"no score for {work_id} under {SCORE_DIR}")

    out_dir.mkdir(parents=True, exist_ok=True)
    parsed = converter.parse(str(src))
    n_parts = len(parsed.parts)

    score = parsed.measures(first, last)
    xml = out_dir / f"{work_id}-m{first}-{last}.musicxml"
    score.write("musicxml", fp=str(xml))

    ly = out_dir / f"{work_id}-m{first}-{last}.ly"
    subprocess.run(["musicxml2ly", "-o", str(ly), str(xml)],
                   check=True, capture_output=True)
    src_ly = ly.read_text()
    src_ly = src_ly.replace("\\header {", "\\header {\n  tagline = ##f")
    # ⚠️ PAPER SIZED TO THE PART COUNT — `excerpt`'s own measurement: a 38-part
    # page on A4 leaves ~1.0 staff space between staves and becomes a ladder no
    # staff detector can segment. Same rule, not a new one.
    paper = "a4" if n_parts <= 20 else ("a3" if n_parts <= 40 else "a2")
    src_ly = (f'#(set-default-paper-size "{paper}")\n'
              "#(set-global-staff-size 16)\n") + src_ly
    ly.write_text(src_ly)

    stem = ly.stem
    subprocess.run(["lilypond", "-s", "-o", stem, f"{stem}.ly"],
                   cwd=out_dir, check=True, capture_output=True)
    pdf = out_dir / f"{stem}.pdf"

    import fitz
    with fitz.open(pdf) as doc:
        n_pages = doc.page_count

    return {"work_id": work_id, "first": first, "last": last,
            "n_parts": n_parts, "paper": paper, "n_pages": n_pages,
            "pdf": str(pdf), "truth_xml": str(xml),
            "meter_map": meter_map(xml),
            "n_bars": last - first + 1}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--first", type=int, required=True)
    ap.add_argument("--last", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    info = render(a.work, a.first, a.last, Path(a.out_dir))
    for k, v in info.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
