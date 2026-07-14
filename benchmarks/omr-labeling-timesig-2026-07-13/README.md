# Time-signature labeling batch (2026-07-13)

Trains a **time-signature specialist** for the decoupled staff-header reader
(`transcribe._read_staff_header`, `--clef-weights` / `OMR_CLEF_WEIGHTS`). That
reader already reads clefs well; it reads **no** time-sig digits today because
neither the production model nor the clef specialist detects them (the DSv2
time-sig domain gap — verified on Beethoven 5 p.1). This batch is the fix.

Full backstory: `benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`.

## What's here

68 staff-header cells (first measure of each staff-row) — **7 meters** across
orchestral (scanned) and keyboard (clean) engravings, covering both digit meters
and both shortcut glyphs (C, ¢):

| source | meter | glyph classes | style | cells |
|---|---|---|---|---|
| Beethoven 5 p.1 | **2/4** | timeSig2, timeSig4 | scanned (Peters) | 12 |
| Bolero p.1 | **3/4** | timeSig3, timeSig4 | clean (Sceaux) | 24 |
| Mahler 5 p.1 | **2/2** | timeSig2 | scanned (Peters) | 18 |
| WTC I Prelude 1 (p.2) | **C** | **timeSigCommon** | clean (Snortum) | 2 |
| Kirchhoff Praeludium 1 (p.1) | **6/8** | timeSig6, timeSig8 | clean (Kremes) | 2 |
| Kirchhoff Praeludium 3 (p.6) | **¢ cut-C** | **timeSigCutCommon** | clean (Kremes) | 8¹ |
| Kirchhoff Praeludium 5 (p.9) | **3/2** | timeSig3, timeSig2 | clean (Kremes) | 2 |

¹ On the cut-C page the OMR merged four keyboard lines into one "system", so 8
cells came through — only the **first two** (staves 0, 1) actually carry the ¢;
staves 2–7 are continuation lines with no meter (box nothing → hard negatives).

Cells were cut with `tools/omr/annotate/select_timesig_cells.py`, which runs the
**exact `transcribe` phase-1** (no orchestral padding patch, dpi 300) so they are
byte-for-byte what the reader sees at inference — a specialist trained on them
transfers. The canvas is **blank** (`detections/` are empty — draw-from-scratch):
you box only the time signatures; nothing else clutters the view. Non-time-sig
symbols are self-distilled from the production model at build time, so nothing is
lost. `cells.json` is complete (no `verdicts_to_yolo_labels` manifest patch).

Two source-specific notes:
- **Keyboard pages** (WTC, Kirchhoff) print the meter only on the first line;
  they were cut with `--first-system-tags wtc,kirchhoff` so only the first
  "system" is kept. Orchestral movement-start pages keep every bracket-group
  system (all show the meter). Keyboard meters have few real examples each — bulk
  them up by adding pages (§ Expand).
- **Kirchhoff is figured-bass-heavy** — the bass staff is peppered with digits
  (6, 5, 6/4, 7…) that look like time-sig digits but AREN'T. Box **only** the
  header meter; leave the figured bass alone (valuable hard negative — real
  scores have figured bass, and the specialist must not fire on it).

## What to label

The time signature sits at the **far left of the measure, right after the clef
and key signature, before the first note**, vertically centred on the staff.

**One TIGHT box per glyph** — the model's classes are per-digit, not per-meter:
- **Stacked digits** → box each digit *separately*. `2/4` = one box on the **2**
  (class `timeSig2`) + one box on the **4** (class `timeSig4`). `2/2` = two boxes,
  both `timeSig2`.
- **C** (common) → one box, class `timeSigCommon`.
- **¢** (cut) → one box, class `timeSigCutCommon`.

Per page (verify against the actual cell — hints, not gospel):

| cell prefix | meter | boxes to draw |
|---|---|---|
| `beet5-p2-*` | 2/4 | `timeSig2` + `timeSig4` |
| `bolero-p2-*` | 3/4 | `timeSig3` + `timeSig4` |
| `mahler5-p2-*` | 2/2 | `timeSig2` + `timeSig2` |
| `wtc-p3-*` | C | `timeSigCommon` (1 box) |
| `kirchhoff-p2-*` | 6/8 | `timeSig6` + `timeSig8` |
| `kirchhoff-p6-*` | ¢ | `timeSigCutCommon` (1 box) — **only `s0`/`s1`; `s2`–`s7` have none** |
| `kirchhoff-p10-*` | 3/2 | `timeSig3` + `timeSig2` |

**Do NOT box anything else** (all self-distilled later): clefs, key-sig sharps/
flats, noteheads, rests, stems, notes, tempo words, dynamics. **Especially skip
Kirchhoff's figured-bass digits** — the 6 / 5 / 7 / ⁶₄ under the bass-staff notes
look like meter digits but are NOT; only the glyph at the measure start counts.

**Cells with no time signature** (continuation lines — the `kirchhoff-p6` staves
2–7, and any staff whose header the meter isn't reprinted on) → box nothing, just
`Tab` past. Empty is correct data (hard negative).

UI hotkeys: `a` = draw a new box (stays in draw mode; `Esc` to stop) · `c` = set
class (`/` searches — type "timeSig") · `b` = redraw a box · `Del` = remove ·
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

Add pages (more meters — 12/8, 3/8, 6/4; more examples per meter) by re-running
the selector with a longer `--plan` (`tag=/abs/file.pdf:PAGE:METER,...`, PAGE
1-based; add keyboard tags to `--first-system-tags`). Rich sources: the WTC book
(48 pieces — 12/8, 3/8, 6/4, 24/16) and Handel Messiah (12/8 Pastoral). Note
compound meters often appear as mid-piece changes (e.g. Kirchhoff p.21 Presto =
3/8), which the header selector doesn't reach — pick a page whose FIRST measure
prints the meter. Then re-run `run_yolo` and COMMIT `cells.json`, `detections/`,
`verdicts/` (cells/ PNGs are gitignored).
