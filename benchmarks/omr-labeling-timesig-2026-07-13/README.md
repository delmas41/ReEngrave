# Time-signature labeling batch (2026-07-13)

Trains a **time-signature specialist** for the decoupled staff-header reader
(`transcribe._read_staff_header`, `--clef-weights` / `OMR_CLEF_WEIGHTS`). That
reader already reads clefs well; it reads **no** time-sig digits today because
neither the production model nor the clef specialist detects them (the DSv2
time-sig domain gap — verified on Beethoven 5 p.1). This batch is the fix.

Full backstory: `benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`.

## What's here

60 staff-header cells (first measure of each staff-row) — **6 meters** across
orchestral (scanned) and keyboard (clean) engravings:

| source | meter | glyph classes | style | cells |
|---|---|---|---|---|
| Beethoven 5 p.1 | **2/4** | timeSig2, timeSig4 | scanned (Peters) | 12 |
| Bolero p.1 | **3/4** | timeSig3, timeSig4 | clean (Sceaux) | 24 |
| Mahler 5 p.1 | **2/2** | timeSig2 | scanned (Peters) | 18 |
| WTC I Prelude 1 (p.2) | **C** | **timeSigCommon** | clean (Snortum) | 2 |
| Kirchhoff Praeludium 1 (p.1) | **6/8** | timeSig6, timeSig8 | clean (Kremes) | 2 |
| Kirchhoff Praeludium 5 (p.9) | **3/2** | timeSig3, timeSig2 | clean (Kremes) | 2 |

Cells were cut with `tools/omr/annotate/select_timesig_cells.py`, which runs the
**exact `transcribe` phase-1** (no orchestral padding patch, dpi 300) so they are
byte-for-byte what the reader sees at inference — a specialist trained on them
transfers. They're pre-labeled with the production model (noteheads/clefs) for
context; `detections/` + `cells.json` are complete (no `verdicts_to_yolo_labels`
manifest patch needed).

Two source-specific notes:
- **Keyboard pages** (WTC, Kirchhoff) print the meter only on the first line;
  they were cut with `--first-system-tags wtc,kirchhoff` so only that line's two
  staves are included (all positives). Orchestral movement-start pages keep every
  bracket-group system (all show the meter). The keyboard meters have just 2
  examples each — bulk them up by adding more prelude/fugue pages (§ Expand).
- **Kirchhoff is figured-bass-heavy** — the bass staff is peppered with digits
  (6, 5, 6/4, 7…) that look like time-sig digits but AREN'T. Box **only** the
  header meter; leave the figured bass alone (it becomes a valuable hard
  negative — real scores have figured bass, and the specialist must not fire on
  it).

## What to label

**Box ONLY the time-signature glyphs** — that's the one thing no model detects:
- digits → class `timeSig0` … `timeSig9` (numerator on top, denominator below)
- common time (C) → `timeSigCommon`; cut time → `timeSigCutCommon`

You do **not** need to confirm noteheads/clefs — the build step self-distills
every non-time-sig symbol from the production model (see below), so leave them
pending. Some cells (a continuation system lower on an orchestral page) have a
clef but **no** time signature — box nothing there; they're useful hard
negatives.

`TIMESIG_HINTS.txt` lists the meter printed on each page. Verify against the cell
— hints are aids, not ground truth.

UI hotkeys: `a` = draw a new box (stays in draw mode; `Esc` to stop) · `c` = set
class (`/` searches, type "timeSig") · `b` = redraw a box · `Del` = remove ·
`Tab` / `Shift+Tab` = next / prev cell (autosaves).

## Serve

```bash
python3 -m tools.omr.annotate.server \
    --bench-dir benchmarks/omr-labeling-timesig-2026-07-13
# → http://127.0.0.1:5050
```

NB a stale annotate server from an earlier session may still hold :5050 (it was
serving the `omr-labeling-clef-diverse` batch). Either stop it (that clef batch is
done) or serve this one on another port: add `--port 5051`.

## After labeling → train → deploy

1. **Build the training set (self-distilled, NOT plain verdicts_to_yolo_labels).**
   Labeling only time-sigs would leave noteheads unlabeled → trained as
   background → notehead suppression (the exact failure the clef retrain hit).
   So mirror `tools/omr/training/build_clef_fix_dataset.py`: keep the human
   **time-sig** boxes, fill every other symbol with production's own detections
   (tight, complete), and add a few dense anti-forgetting cells. (Adapt that
   script's `is_clef` → an `is_time_sig` target; a `build_timesig_dataset.py` is
   the natural next artifact.)

2. **Fine-tune** from the production checkpoint (or from the clef box-fix model,
   to get a combined clef+time-sig header specialist) with the proven recipe:
   `--extra-kwargs '{"lr0":0.001,"optimizer":"AdamW","freeze":10,"warmup_epochs":2,"cos_lr":true}' --epochs 30 --imgsz 1280 --batch 8 --device mps`,
   take `last.pt` → a new `omr-weights/*.pt` (never overwrite production).

3. **Validate**: transcribe Beethoven 5 p.1 with `--clef-weights <new>` and check
   `time_signature` now reads 2/4 (and Bolero 3/4, Mahler 2/2, WTC C, …), with
   noteheads still ≈ production. The reader plumbing is already done + unit-tested
   (`tools/omr/tests/test_header_reader.py`) — it lights up the moment the
   specialist detects the digits.

4. **Deploy**: `OMR_CLEF_WEIGHTS=omr-weights/<new>.pt` (CLI `--clef-weights`).

## Expand

Add pages (more meters — 12/8, 3/8, cut-C, 6/4; more examples per meter) by
re-running the selector with a longer `--plan`
(`tag=/abs/file.pdf:PAGE:METER,...`, PAGE 1-based; add keyboard tags to
`--first-system-tags`). Rich sources: the WTC book (48 pieces — 12/8, 3/8, 6/4,
24/16, cut-C) and Handel Messiah (12/8 Pastoral, cut-C choruses). Then re-run
`run_yolo` to pre-label and COMMIT `cells.json`, `detections/`, `verdicts/`
(cells/ PNGs are gitignored).
