#!/usr/bin/env python3
"""Generate a self-contained HTML page for visually verdicting a run.

Open the resulting verdicts.html in any browser. For each cell, you see:
  - The overlay PNG inline
  - A toggle row per CV detection: green = correct, red = wrong
  - Two number inputs: stems_missed, beams_missed (defaults to 0)

When you've gone through all the cells, click "Download verdicts.json".
That file is the same shape as the template and can be fed into
`score_verdicts.py` to compute precision/recall/F1.

No server, no dependencies — just open the file.

Usage:
    python3 make_verdict_page.py path/to/run-001/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


HTML_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Stem/Beam Verdict — __TITLE__</title>
<style>
  body { font-family: -apple-system, sans-serif; margin: 20px; max-width: 1200px; }
  h1 { font-size: 22px; }
  h2 { font-size: 18px; margin-top: 30px; padding-top: 10px; border-top: 2px solid #999; }
  .cell { margin-bottom: 40px; }
  .overlay { max-width: 100%; border: 1px solid #ccc; }
  .verdicts { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 6px; margin-top: 10px; }
  .det { padding: 6px 8px; border: 1px solid #ccc; border-radius: 6px; font-size: 13px; cursor: pointer; user-select: none; background: #f9f9f9; }
  .det.correct { background: #c8e6c9; border-color: #4caf50; }
  .det.wrong   { background: #ffcdd2; border-color: #c62828; }
  .det .label { font-weight: bold; }
  .det .ink { font-size: 11px; color: #555; }
  .missed-row { margin-top: 12px; }
  .missed-row label { margin-right: 16px; }
  .missed-row input { width: 50px; padding: 4px; }
  .summary { position: fixed; top: 10px; right: 10px; padding: 12px 16px; background: #fff; border: 2px solid #333; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); font-size: 13px; min-width: 220px; }
  .summary button { display: block; margin-top: 8px; padding: 6px 10px; font-size: 13px; cursor: pointer; }
  .help { color: #555; margin-bottom: 20px; font-size: 14px; }
  kbd { padding: 1px 6px; border: 1px solid #ccc; border-radius: 3px; background: #f4f4f4; font-family: monospace; font-size: 11px; }
</style>
</head>
<body>

<h1>Stem & Beam Verdicts — __TITLE__</h1>
<div class="help">
  <p><strong>How to judge each detection:</strong></p>
  <ul>
    <li><span style="color:#2e7d32;font-weight:bold;">Green boxes (stems):</span>
      <span class="det correct" style="display:inline-block;padding:1px 6px;">correct</span> if the box is on an actual <em>note stem</em> (a thin vertical line connecting a notehead to a beam or flag).
      <span class="det wrong" style="display:inline-block;padding:1px 6px;">wrong</span> if it's on a clef stroke, a letter in text, the bar of a sharp/flat/natural, the inner stroke of a double barline, or any other non-stem vertical ink.
    </li>
    <li><span style="color:#0d47a1;font-weight:bold;">Blue boxes (beams):</span>
      <span class="det correct" style="display:inline-block;padding:1px 6px;">correct</span> if the box is on an actual <em>beam stroke</em> (a thick black horizontal/diagonal bar connecting two or more stems — what marks eighth-notes-as-a-group).
      <span class="det wrong" style="display:inline-block;padding:1px 6px;">wrong</span> if it's on a slur, tie, hairpin, staff line residue, ledger line, non-beam horizontal mark, <em>or</em> if it's a duplicate of a real beam that's already been counted (see below).
    </li>
  </ul>
  <p><strong>For stacked beams (16th, 32nd notes):</strong> each <em>visible</em> beam stroke is one real beam. A 32nd-note group has 3 real beams (triple-beam); a 16th-note group has 2 (double-beam); an 8th-note group has 1. If the detector emits more boxes than real beams in the same cluster, mark only the matching number as correct and the rest as wrong. Example: 5 boxes piled on a clearly-triple-beam group → 3 correct, 2 wrong.</p>
  <p><strong>Workflow:</strong> chips default to <span class="det correct" style="display:inline-block;padding:1px 6px;">correct</span>. Click each one to flip to <span class="det wrong" style="display:inline-block;padding:1px 6px;">wrong</span>. <em>Hover</em> a chip to highlight its box on the image. Count any real stems/beams that have NO box and enter the count in the missed fields. When done, click <strong>Download verdicts.json</strong> in the top-right.</p>
  <p><em>If unsure about a box, leave it as <span class="det correct" style="display:inline-block;padding:1px 6px;">correct</span> and skip — being thorough on the obvious ones is more useful than getting paralyzed on edge cases.</em></p>
  <p><strong>Note:</strong> small <span style="color:#dc1414;font-weight:bold;">red boxes</span> on the overlay are YOLO noteheads (not graded — for context only). They show you which notes the system thinks are present. Real stems should attach to one of these red boxes.</p>
</div>

<div class="summary" id="summary">
  Cells: __NCELLS__<br>
  Stems: <span id="s-correct">0</span> ok / <span id="s-wrong">0</span> wrong<br>
  Beams: <span id="b-correct">0</span> ok / <span id="b-wrong">0</span> wrong<br>
  <button onclick="downloadJSON()">Download verdicts.json</button>
  <button onclick="markAllCorrect()">Mark all correct</button>
</div>

__CELL_BLOCKS__

<script>
const data = __DATA__;

function det(cellId, kind, idx) {
  return document.querySelector(`[data-cell="${cellId}"][data-kind="${kind}"][data-idx="${idx}"]`);
}

function setJudgment(el, value) {
  el.classList.remove('correct', 'wrong');
  if (value) el.classList.add(value);
  el.dataset.judgment = value || '';
  updateSummary();
}

function toggle(el) {
  const cur = el.dataset.judgment;
  if (cur === 'correct') setJudgment(el, 'wrong');
  else setJudgment(el, 'correct');
}

function updateSummary() {
  let sCorrect = 0, sWrong = 0, bCorrect = 0, bWrong = 0;
  document.querySelectorAll('.det[data-kind="stems"]').forEach(el => {
    if (el.dataset.judgment === 'correct') sCorrect++;
    else if (el.dataset.judgment === 'wrong') sWrong++;
  });
  document.querySelectorAll('.det[data-kind="beams"]').forEach(el => {
    if (el.dataset.judgment === 'correct') bCorrect++;
    else if (el.dataset.judgment === 'wrong') bWrong++;
  });
  document.getElementById('s-correct').textContent = sCorrect;
  document.getElementById('s-wrong').textContent = sWrong;
  document.getElementById('b-correct').textContent = bCorrect;
  document.getElementById('b-wrong').textContent = bWrong;
}

function markAllCorrect() {
  document.querySelectorAll('.det').forEach(el => setJudgment(el, 'correct'));
}

function buildVerdicts() {
  const out = { cells: [], legend: data.legend };
  for (const c of data.cells) {
    const stemsV = c.stems_verdicts.map(v => {
      const el = det(c.cell_id, 'stems', v.idx);
      return { idx: v.idx, judgment: el.dataset.judgment || 'correct', ink_fill_ratio: v.ink_fill_ratio };
    });
    const beamsV = c.beams_verdicts.map(v => {
      const el = det(c.cell_id, 'beams', v.idx);
      return { idx: v.idx, judgment: el.dataset.judgment || 'correct', ink_fill_ratio: v.ink_fill_ratio };
    });
    const sMissed = parseInt(document.querySelector(`[data-missed="stems"][data-cell="${c.cell_id}"]`).value, 10) || 0;
    const bMissed = parseInt(document.querySelector(`[data-missed="beams"][data-cell="${c.cell_id}"]`).value, 10) || 0;
    out.cells.push({
      cell_id: c.cell_id, overlay_path: c.overlay_path,
      stems_count_cv: c.stems_count_cv,
      stems_verdicts: stemsV, stems_missed: sMissed,
      beams_count_cv: c.beams_count_cv,
      beams_verdicts: beamsV, beams_missed: bMissed,
    });
  }
  return out;
}

function downloadJSON() {
  const verdicts = buildVerdicts();
  const blob = new Blob([JSON.stringify(verdicts, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'verdicts.json';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Initialize: default everything to 'correct'.
window.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.det').forEach(el => {
    setJudgment(el, 'correct');
    el.addEventListener('click', () => toggle(el));
  });
});
</script>

</body>
</html>
"""


def build_cell_block(cell: dict, base_path: Path) -> str:
    """One <h2> + overlay <img> + verdict chips + missed inputs."""
    cell_id = cell["cell_id"]
    overlay_rel = Path("overlays") / Path(cell["overlay_path"]).name
    lines = [f'<div class="cell">']
    lines.append(f'  <h2>{cell_id}</h2>')
    lines.append(f'  <img class="overlay" src="{overlay_rel}" alt="{cell_id}">')

    def chips(kind: str, verdicts: list[dict]) -> str:
        if not verdicts:
            return f'  <div style="color:#888;font-size:13px;">no {kind} detections</div>'
        out = [f'  <div style="margin-top:8px;"><strong>{kind}</strong>:</div>']
        out.append('  <div class="verdicts">')
        for v in verdicts:
            prefix = "s" if kind == "stems" else "b"
            out.append(
                f'    <div class="det" data-cell="{cell_id}" data-kind="{kind}" data-idx="{v["idx"]}">'
                f'<span class="label">{prefix}{v["idx"]}</span> '
                f'<span class="ink">ink {v["ink_fill_ratio"]:.2f}</span>'
                f'</div>'
            )
        out.append('  </div>')
        return "\n".join(out)

    lines.append(chips("stems", cell["stems_verdicts"]))
    lines.append(chips("beams", cell["beams_verdicts"]))
    lines.append('  <div class="missed-row">')
    lines.append(f'    <label>stems missed: <input type="number" min="0" value="0" data-missed="stems" data-cell="{cell_id}"></label>')
    lines.append(f'    <label>beams missed: <input type="number" min="0" value="0" data-missed="beams" data-cell="{cell_id}"></label>')
    lines.append('  </div>')
    lines.append('</div>')
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", help="Path to benchmarks/omr-stem-precision/run-NNN/")
    ap.add_argument("--out", default=None, help="Output html (default: <run_dir>/verdicts.html)")
    args = ap.parse_args(argv[1:])

    run_dir = Path(args.run_dir).resolve()
    template_path = run_dir / "verdicts_template.json"
    template = json.loads(template_path.read_text())
    cells = template["cells"]

    cell_blocks = "\n".join(build_cell_block(c, run_dir) for c in cells)

    html = HTML_TEMPLATE
    html = html.replace("__TITLE__", run_dir.name)
    html = html.replace("__NCELLS__", str(len(cells)))
    html = html.replace("__CELL_BLOCKS__", cell_blocks)
    html = html.replace("__DATA__", json.dumps(template))

    out_path = Path(args.out) if args.out else (run_dir / "verdicts.html")
    out_path.write_text(html)
    print(f"Wrote {out_path}")
    print(f"  Open in browser to verdict, then click 'Download verdicts.json'.")
    print(f"  Then: python3 score_verdicts.py path/to/verdicts.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
