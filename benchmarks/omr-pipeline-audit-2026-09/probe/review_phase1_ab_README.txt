review_phase1_ab.py — reviewer's independent inertness check for
`claude/fix-barline-evidence` (Agent I, review of Fix Agent B).

Verifies the change moved no verdict by comparing PHASE 1 ONLY across two
trees, which is where the risk actually lives: measure_extractor is upstream of
everything, so a moved barline moves a cell, which moves every detection.
Needs NO YOLO weights, so it covers many more pages than a full-transcribe arm.

Compared per page: staff count; each staff's (system, group, line_ys, x_start,
x_end); the sorted per-system barline list; every cell's bbox_page_px and
canonical staff-line ys.

  git archive <before-sha> tools | tar -x -C /tmp/before
  git archive HEAD          tools | tar -x -C /tmp/after
  python3 review_phase1_ab.py /tmp/before fp_before.json jobs.json
  python3 review_phase1_ab.py /tmp/after  fp_after.json  jobs.json
  # jobs.json = [[name, pdf_path, page_index], ...]

RESULT 2026-09-07, 974971e3 vs 342dc03b, 16 pages (12 scan-gate rows + 4
engraved fixtures): 305 staves, 313 barlines, 3558 cells — BIT-IDENTICAL.
