# Where the OMR work stands — 2026-09-03

Successor to `next-steps-omr-2026-09-02.md`. The change since then: the
hand-labeling → gate → **ship** loop closed for the first time. A better
detector is deployed, and the process that produced it is proven and cheap to
repeat.

## Current state (all on `main`, 5d81ace)

- **Engraved benchmark:** 11 works, pooled OMR-NED **0.1306** (default,
  direction-text on) / 0.1399 (no OCR). Home: CLAUDE.md's OMR-NED section.
- **Production detector: SHIPPED the hollow fine-tune** —
  `deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt` (DEFAULT_WEIGHTS + backend +
  docker + docs repointed). Scan half-notes **8 → 27**, scan duration recall
  **0.388 → 0.435**, dense recall **held at 0.941** (zero forgetting).
  Old weights backed up (`…imgsz2048-ft-30ep.PRE-HOLLOW-2026-09-03.pt`);
  **revert = `git revert 5d81ace`**. ⚠️ Web app needs
  `docker compose build backend && up -d backend`; CLI is live now.
- **The labeling loop is proven:** benchmarks/omr-labeling-survey-2026-09/
  (SURVEY_DESIGN, GATE_RESULTS, SHIP_RESULTS). Hand-labeled scan cells →
  measurably better deployed detector, first time in the project.

## The proven process (quick, painless — the point)

1. **Cut** sparse short-bar cells from hollow-rich pages, ranked by the
   enclosed-white scorer (`hollow_score.py`, ~91% precision). Pure OpenCV,
   no GPU.
2. **Serve** with a single-symbol `batch_config.json` — restricted palette,
   click-to-box that snaps to the staff grid and auto-picks the class. One
   click per note, Tab to advance. (This is the UX Sean called painless.)
3. **Complete** the single-symbol cells via the production detector's own
   non-target detections, AUDITED (sparse cells + conf≥0.5 + NMS give ~97%
   clean completion, unlike the dense round-1's 1/117).
4. **Gate**: fine-tune from production weights (nc unchanged, no head reset),
   pick the earliest checkpoint (Pareto-optimal — dense holds, later epochs
   trade it for hollow), re-gate on `wtc_forgetting_eval` + the scan eval.
5. **Ship** only if dense recall HOLDS and the target detection rises.

⚠️ **Hard lessons baked in:** trainings run STRICTLY SERIALLY and ALONE on the
M1 Max MPS (two concurrent runs thrash); imgsz-2048 and 1280 are INFEASIBLE
locally (~9h and ~2.5h/epoch) — 896 is the feasible ceiling, true 2048 needs a
cloud GPU; single-symbol cells are incomplete and MUST be completed before
training.

## Ranked next steps

### 1. Phase 2 — label the four cut batches (Sean's hands)
On `main`, `benchmarks/omr-labeling-hollow3-2026-09-*`, 224 cells, single-symbol
ready:
- **Universal / Mahler 1** *Langsam* — ~50–70 boxes (whole-note rich)
- **Novello / Elgar 1** *Adagio* — ~35–50
- **Jurgenson / Tchaikovsky 1** *Adagio* — ~25–35 ⚠️ low-res scan, **droppable**
  (substitute for the unusable Tch 4); weigh at catalog-admission
- **Durand / La mer** — ~15–25 (busy texture)

Then convert + **re-ship at a higher dense ratio** (the shipped run was
imgsz-896; more publisher diversity + a cleaner ratio should push the gain and
shrink the engraved wobble). Same process, steps 3–5 above.

### 2. After Phase 2 — one of two escalations (Sean's call)
- **(a) Cloud-GPU imgsz-2048 run** — the true production recipe. The local ship
  is 896-limited; 2048 on a CUDA box (the repo already flags this for the
  RTMDet/yolov8x escalation) should lift the hollow gain further and is the
  natural "do it properly" step. Needs a budgeted cloud run + weights transfer.
- **(b) Extend the same process to the NEXT under-scoring symbol.** The white-
  note loop is general. SURVEY_DESIGN.md ranks the candidates: **grace / small
  noteheads** (0 labeled, flagged on dense scores), **small dynamics glyphs**,
  **ornaments**. ⚠️ Each needs its OWN selector — the enclosed-white ranker is
  hollow-specific; name the selection signal per symbol before cutting.
  **Do NOT** label time-sig digits or accidentals — a geometry reader beats
  more examples there (measured).

### 3. Standing, unchanged
- The engraved 11-work benchmark is the tracking number; `--check` guards it.
- Small queued fixes from the 09-02 doc (lexicon one-liners, staff_header
  bracket-as-window, the Mahler scan +37 attribution) remain open.

## Do not spend time on these
Unchanged from 09-02: system-break threshold rules, detector fine-tuning on
DENSE cells (only sparse hollow cells train cleanly), synthetic augmentation,
VLM transcription, key-signature-from-music, catalog-augmented training.
