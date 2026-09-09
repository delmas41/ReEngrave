"""Render a REAL meter change, ENGRAVED, so reading quality is not the confound.

⚠️ WHY THIS FIXTURE EXISTS, and it is the one measurement two shipped
mechanisms cannot be told apart without. `OMR_METER_CARRY` hands an abstaining
system the last meter that was READ and lets its bars weigh it;
`OMR_METER_FROM_BARS` lets a system's own bars name a LENGTH and never reaches
past itself. On Beethoven 5 / Litolff the only movement boundary available is
page 17, whose bars are noise -- so the carry's refusal there is SAFE but NOT
DISCRIMINATING (it refuses the CORRECT meter too), and nothing separates the
two mechanisms. `benchmarks/omr-staged-meter-carry-2026-09/FINDINGS.md` §11
names the route out and this is it.

`beethoven-sym5-mvt4` encodes 4/4 -> 3/4 at bar 155 -> 4/4 at bar 209. Rendered
through LilyPond the ink is clean, so a bar that fails to sum is the reader's
fault and not the print's.

⚠️ THE STRUCTURE IS THE POINT, NOT THE PAGE COUNT. An engraver -- and LilyPond
-- prints a time signature at the CHANGE and at nothing after it. So a system
lying wholly inside the 3/4 stretch prints NO meter, abstains honestly, and is
handed a `4/4` by the carry. That system is the discriminating case, and it is
a real engraving convention rather than an ablation.

    python3 -m benchmarks... --first 150 --last 180 --out-dir <dir>

Modelled on `orchestral_eval.excerpt()` and reusing its paper sizing and its
`_apply_indent_override`, but it does NOT shrink to one page: this fixture
wants several systems on purpose.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import fitz
from music21 import converter

from tools.omr.training.orchestral_eval import (
    SCORE_DIR,
    _apply_indent_override,
    _restore_rest_fermatas,
    rest_fermata_ordinals,
)


def render(work_id: str, first: int, last: int, out_dir: Path,
           tag: str) -> tuple[Path, Path]:
    src = None
    for suffix in (".mxl", ".musicxml"):
        candidate = SCORE_DIR / f"{work_id}{suffix}"
        if candidate.is_file():
            src = candidate
            break
    if src is None:
        raise FileNotFoundError(f"no score for {work_id} under {SCORE_DIR}")

    out_dir.mkdir(parents=True, exist_ok=True)
    parsed = converter.parse(str(src))
    n_parts = len(parsed.parts)
    score = parsed.measures(first, last)

    xml = out_dir / f"{tag}.musicxml"
    score.write("musicxml", fp=str(xml))

    ly = out_dir / f"{tag}.ly"
    subprocess.run(["musicxml2ly", "-o", str(ly), str(xml)],
                   check=True, capture_output=True)
    src_ly = ly.read_text()
    src_ly = src_ly.replace("\\header {", "\\header {\n  tagline = ##f")
    fermatas = rest_fermata_ordinals(score)
    if fermatas:
        src_ly = _restore_rest_fermatas(src_ly, fermatas, n_parts=n_parts)
    paper = "a4" if n_parts <= 20 else ("a3" if n_parts <= 40 else "a2")
    src_ly = (f'#(set-default-paper-size "{paper}")\n'
              "#(set-global-staff-size 16)\n") + src_ly
    src_ly = _apply_indent_override(src_ly)
    ly.write_text(src_ly)
    subprocess.run(["lilypond", "-s", "-o", tag, f"{tag}.ly"],
                   cwd=out_dir, check=True, capture_output=True)
    pdf = out_dir / f"{tag}.pdf"
    with fitz.open(pdf) as doc:
        pages = doc.page_count
    print(f"{tag}: parts={n_parts} paper={paper} measures {first}-{last} "
          f"-> {pages} page(s)  {pdf}")
    return xml, pdf


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-id", default="beethoven-sym5-mvt4")
    ap.add_argument("--first", type=int, required=True)
    ap.add_argument("--last", type=int, required=True)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--out-dir", default=None)
    a = ap.parse_args()
    tag = a.tag or f"{a.work_id}-m{a.first}-{a.last}"
    out = Path(a.out_dir or (Path(__file__).parent / "fixtures"))
    render(a.work_id, a.first, a.last, out, tag)
