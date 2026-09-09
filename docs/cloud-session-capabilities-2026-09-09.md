# What a cloud session can and cannot measure

*2026-09-09. Established by inventory in a Claude Code web session, not from
memory — every line below was run.*

A cloud container clones the repo and nothing else. **`omr-weights/` and
`library/` are both gitignored**, so the two things most OMR work needs are
absent and cannot be fetched. That rules out more than it sounds like, and
rules in more than expected.

---

## 1. The dependency floor

The container starts as bare **Python 3.11** with no third-party packages and
no venvs. `pip` works through the agent proxy.

```bash
pip install music21 musicdiff numpy opencv-python-headless scipy \
            scikit-image pymupdf pytest httpx
```

That is the whole floor. `tools.omr.export`, `tools.omr.staged.*` and
`tools.omr.symbol_ledger` then import and run.

⚠️ **`fastapi` + `uvicorn` + `httpx` are needed only by
`test_annotate_server.py`**, which otherwise fails collection and takes the
whole suite down with it.

The floor was arrived at by iterating on collection errors, and the sequence is
worth recording because each layer hides the next: **44 collection errors →
`fitz`/`scipy` → 29 → `skimage` → 1 → `httpx`/`starlette.testclient` → 0.**
⚠️ What is verified here is that the suite **collects and runs green**, not a
full-suite pass count — it takes long enough that this inventory recorded it
mid-run rather than waiting. Re-run it yourself before trusting a green claim:

```bash
python3 -m pytest tools/omr/tests/ -q
```

---

## 2. ⚠️ musicdiff runs NATIVELY here, and that is a real difference

CLAUDE.md's OMR-NED section exists around a workaround: *"musicdiff needs
Python ≥ 3.10 + music21 ≥ 9.9.1 and the host is 3.9, so it runs out of process
in a gitignored `.venv-omrned` and talks JSON."* It then documents **four
symlinks**, three of which fail on the scan side only.

**A cloud container is Python 3.11.** None of that applies: `pip install
music21 musicdiff` and the scorer is importable in-process. Verified on a
committed pair —

```
benchmarks/omr-first-run-2026-08/out/beet5-p1-shift09.omr.musicxml
  vs  benchmarks/omr-first-run-2026-08/truth/beet5-mm1-16.musicxml
  -> OMR-NED 0.7152, 1286 edits, 734 pred / 1064 truth symbols
```

⚠️ **One trap, and it is the reason `_omrned_worker.py` is documented as never
importing from `tools.*`**: run it from the repo root and `tools/omr/types.py`
**shadows the stdlib `types` module**, producing a circular-import failure deep
inside `weakref`. Run the worker from any other directory. The protocol is one
JSON job on stdin:

```bash
cd /tmp/scratch && echo '{"detail":"AllObjects","pairs":[
  {"name":"row","pred":"/abs/pred.musicxml","truth":"/abs/truth.musicxml"}]}' \
  | python3 _omrned_worker.py
```

---

## 3. ⚠️ THREE SCAN-GATE ROWS ARE FULLY REPRODUCIBLE FROM COMMITTED FILES

This is the finding that changes what a cloud session is for. Everything an
**export-side** A/B needs on Brahms 1 / Breitkopf is in git:

| what | where | size |
|---|---|---|
| the transcription | `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json` | 3 pages, 83 staves, **10,523 detections** |
| the ground truth | `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/reference.mxl` | 21 parts, 1173 `<dynamics>`, 683 hairpins |
| hand-verified windows | `benchmarks/omr-scan-e2e-2026-09/works.json` rows `brahms-sym1-mvt1-317803-p1..p4` | measure windows + staves→parts maps |

So the loop **transcription → `export.py` → MusicXML → musicdiff → OMR-NED**
closes here, on rows the 20-row scan gate actually contains. Verified:

```bash
python3 -m tools.omr.export \
  benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json \
  --format musicxml --out /tmp/brahms.musicxml
# 28 parts, 706 measures, 159 <dynamics>, 0 <wedge>, 7 <words>
```

⚠️ **`transcription.json` is committed but `cells/` is not** — see CLAUDE.md's
"A checked-out batch has no images until you re-cut them". The detections and
their page coordinates are all present; the rasters are not.

⚠️ **There are 28 re-exportable transcriptions in `benchmarks/`**, but this is
the only one paired with a committed truth AND a hand-verified window. The
others can be re-exported and diffed against each other, not scored.

### And it reproduced the dynamics finding rather than quoting it

That transcription carries **265 dynamic letter detections and ZERO of either
hairpin class**, and its export emits **159 `<dynamics>` and 0 `<wedge>`.**
The ledger's `hairpin matched_exact = 0` is not an artefact of the ledger: the
detector sees the letters and is blind to the wedges, confirmed end to end on
committed data with no weights present.

---

## 4. What is impossible, and why it cannot be worked around

| | why |
|---|---|
| **any transcription from a PDF** | `omr-weights/*.pt` (~88 MB each) are gitignored |
| **`scan_eval` / `orchestral_eval`** | both transcribe first |
| **re-pricing `OMR_CV_HAIRPINS`** | `hairpin_detection.read_hairpins_for_page` takes `page.binary` — the raster |
| **anything CV or detector-side** | no page images |
| **Bravura template work end-to-end** | the library can be BUILT (freetype + the font), but reading templates off a page needs the page |
| **the other 17 scan-gate rows** | their editions live in `library/`, gitignored |

**The line is exactly: a change that acts on an already-made transcription can
be measured here; a change that acts on the page cannot.**

---

## 5. ⚠️ One row is not the gate

An export-side A/B on Brahms p1–p3 is a signal, not a verdict. The gate is 20
rows for the reason CLAUDE.md gives repeatedly — a threshold measured on one
edition is not a threshold, and adding a second edition to the clef sweep took
reported false positives 7 → 48 with no regression. Treat a cloud result as
*worth running the real arm for*, never as the arm.

⚠️ And the 20-row gate has a noise floor of roughly **±6 edits**; a single
Brahms row's delta smaller than that is not evidence.
