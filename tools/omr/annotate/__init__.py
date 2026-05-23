"""Phase 2.5 annotation framework.

Three pieces:
    - select_cells: pick ~30 representative Phase-1 cells and persist them
      with a JSON manifest, so the human can see each cell PNG.
    - build_template: for each manifest entry, run detect_symbols(), write
      an overlay PNG with numbered detections, and emit a markdown verdict
      template the human fills in.
    - score: parse filled verdicts, compute per-cell / per-piece / overall
      precision, recall, F1, and write a markdown report + CSVs.

This is the scoring infrastructure for Phase 2's template_matcher. It DOES
NOT modify the matcher — it measures it.
"""
