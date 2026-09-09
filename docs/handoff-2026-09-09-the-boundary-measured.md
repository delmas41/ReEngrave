# Handoff — the boundary case is measured, and a `C` was being detected and dropped

⚠️ **READ THIS FIRST.** It replaces
[docs/handoff-2026-09-09-bars-name-a-length.md](handoff-2026-09-09-bars-name-a-length.md)
as the entry point. That file's redirect still governs — **the metric is not
the goal, the staged pipeline is** — and its §5 task **1** is what this session
did.

⚠️ Its §3 and §4 stand unamended and are still the honest account of what
`OMR_METER_CARRY` / `OMR_METER_FROM_BARS` rest on. **One claim in them is now
superseded and only one**: *"the case that separates them — a movement
boundary on a page that READS WELL — is unmeasured"*. It is measured. Nothing
else changed.

---

## 1. WHAT LANDED

**A measurement**, and **one fix it found**.

* `benchmarks/omr-staged-meter-boundary-2026-09/` — two engraved fixtures
  carrying a REAL meter change, the four arms over each, the reports, the
  controls, and `FINDINGS.md`.
* `rhythm._meter_from_letter` — **no flag**, because it adds a reading where
  there was none. A meter change engraved as a common-time `C` was DETECTED on
  every staff and proposed nothing.

## 2. THE MEASUREMENT — the bars discriminate by 14.0

`beethoven-sym5-mvt4` (4/4 → **3/4 at bar 155** → 4/4 at bar 209) rendered
through LilyPond at 23 parts, so the ink is clean and a bar that fails to sum
is the reader's fault. An engraver prints a time signature at the CHANGE and at
nothing after it, so a system lying wholly inside the new meter prints none,
abstains honestly, and is exactly what both mechanisms are for. **Nothing was
suppressed to produce that.**

Page 3 of the forward fixture (m172+, 3/4, no meter printed), asked twice — the
runs differ ONLY in which earlier page is in the window:

| candidate offered | bars | support | outcome |
|---|---|--:|---|
| **3/4**, the true meter | 7 fit / 2 not | **+6.0** | **`carried` 3/4 — CORRECT** |
| **4/4**, across the boundary | 0 fit / 9 not | **−8.0** | **refused** |

On the *Andante* the true meter scored −1.0 and the false one −1.0. Here they
are +6.0 and −8.0 **on the same nine bars**. `OMR_METER_FROM_BARS` reaches the
same page independently (length 3.0 at +5.0; `derived_from_bars` **3/4** where
a 3/4 is available to borrow the spelling from, and
`bars_name_a_length_without_a_form` with `['3/4','6/8','12/16']` where only a
`C` precedes — the truth in the shortlist).

**In the file** (exported from the saved records, no re-transcription): whole
rests written at 4.0 ql inside a 3.0 ql bar **196 → 38**, proper measure rests
**305 → 463**, quarter and half rests untouched, and the CARRY and BARS exports
**byte-identical**. All 38 residuals are bars holding more than one note, which
`size_measure_rest` refuses by design.

## 3. ⚠️ WHAT IS *NOT* ESTABLISHED

* **Still one document.** A different movement and a different engraving, which
  removes the LEGIBILITY confound and nothing else. **Ranked task 2 — a second
  document and publisher — is untouched and is now the top open item.**
* **n = 4 systems**; the discrimination result is ONE page asked twice.
* ⚠️ **`METER_CARRY_MIN_BARS = 2` refused a CORRECT carry here** — the
  one-bar fermata system, truth 4/4, its single bar reading 4.0. First time
  that constant's cost has been seen rather than only its benefit.
* ⚠️ **Bar assessability falls with DENSITY, not with print quality**: over the
  four systems asked, 100% / 100% / 78% / **33%** against 1.0 / 1.5 / 3.1 /
  **4.5** events per bar. A dense bar needs every duration right to sum, so
  these mechanisms are strongest where the music is SPARSE — which is also
  where the measure-rest payoff is largest. n = 4; suggestive, not established.
* **Neither flag is flipped.** For the carry, objection (1) of its knobs-table
  entry is now closed and (2) and (3) stand.

## 4. ⚠️ THE FIX — a `C` change was detected on 23 staves of 23 and dropped

`_meter_from_digits` needs two stacked digits and says so in its own comment
(*"timeSigCommon and friends: no pair"*), so a system whose meter changes to
common time formed no candidate at all. Measured at the 3/4 → 4/4 change of bar
209: **`timeSigCommon` on 23 staves of 23, unanimous, and nothing proposed.**
Detected then dropped, inside the meter.

⚠️ **`Q.METER_GLYPH` already carries `letter=True`, written by GATHER and read
by NOTHING.** It cannot be the input either — a boolean cannot tell a `C` from
a `¢`. ⚠️ **And the change detector had NO unit tests at all**: `grep -c
METER_GLYPH tools/omr/tests/*.py` was zero across the suite while
`_meter_changes`, `_change_only` and the whole `segments` mechanism shipped
default-on. `TestAMeterChangeIsReadFromTheInk` (10 tests, **8 mutation arms,
all red**) is that gap closed.

⚠️⚠️ **THE FIX PRODUCES A FALSE POSITIVE ON A SCAN AND IT IS REPORTED, NOT
SMOOTHED OVER.** Litolff p.61 prints bar 140 and no time signature anywhere
(rendered and looked at); one `timeSigCommon` at confidence **0.377** on one
staff of seventeen now proposes a change. It names 4/4, which IS that page's
meter, so the record got better *here* — by accident of which meter the false
glyph named. **The hazard is `METER_CHANGE_FLOOR`, not the letter path**, and
the previous session's headline `3/4` on p.62 rests on the identical
one-staff-clears-the-floor property. What a letter adds is that it is cheaper
to fake than a digit pair. The bars refused the OTHER false letter on the same
document. Confidence separates the four populations cleanly (0.887-0.927
engraved, 0.377-0.560 scan) and is deliberately **not** gated on: four rows on
two documents is not a threshold.

Everything else is unchanged: the forward fixture identical on all 4 pages,
Litolff `--pages 0-2` identical on every subject, outcome, reason and value,
and p.62's `3/4` at cell 8 preserved to the unit.

## 5. THE NEXT WORK, RANKED

### 1. A SECOND DOCUMENT AND PUBLISHER

Promoted from task 2 and now the only thing between the carry and a default.
230 reference works encode a mid-piece `<time>` change and the library holds
editions for many; `render_boundary.py` makes an engraved arm out of any of
them in ~15 s, and the scan arm is the same PDF.

### 2. ⚠️ TWO CARRY-SOURCE GAPS, FOUND AND NOT BUILT

One `grep` each, both demonstrable on the reverse fixture, and they are ONE
piece of work because fixing either alone is wrong in the same direction:

* a system that READ a change cannot be a carry source (`found.reason !=
  "voted"`, `rhythm.py:1206` and `:1321`) — so the system that read `C` on
  23 staves at support 66.0 cannot tell the very next system, which is in that
  meter, anything;
* a carry takes the source's OPENING and drops its segments
  (`rhythm.py:1246`), so carrying across a system that changed meter carries
  the pre-change meter.

**Carry the meter in force at the END of the nearest preceding system whose
meter came from INK.** ⚠️ Needs a corpus that can show it going wrong first: a
false `change_only` (§4 has one) would then propagate forward instead of
staying put.

### 3. UNCHANGED FROM THE LAST HANDOFF

`A-DUR-6` items 6 and 7 — beat subdivision, and `A-DUR-5`'s **unclassified
ink**, Sean's standing request, still needing a RASTER pass in GATHER. Unify
the two chord groupings (export consuming `Q.EVENT`). `arc_kind` / `arc_owner`
still stubs (843 arcs). Calibration from the score library, which bar sums make
possible with no truth files and which nothing has built.

⚠️ The double barline is still **not** the cheap win `A-DUR-6` calls it — see
the previous handoff.

## 6. OPERATIONAL

* Four symlinks in a worktree: `library`, `tools/omr/training/data/weights`,
  `.venv-surya`, `.venv-omrned`. The staged pipeline needs only the weights;
  the SUITE needs `.venv-surya` or a direction-text test FAILS rather than
  skipping.
* ⚠️ **`omr-weights/` does not exist in a worktree.** Use
  `tools/omr/training/data/weights/...`; the CLAUDE.md examples use the other
  path and fail with `FileNotFoundError` inside ultralytics.
* ⚠️ **The staged CLI does no weight routing.** Engraved fixtures want
  `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`, scans want the hollow graft;
  `run_arms.py` takes `--weights` and records the choice.
* ⚠️ **A duration-level A/B across meter arms is invalid by construction** — a
  decided meter is consumed by `size_measure_rest` and `reconcile_duration`
  (159 of 314 duration verdicts move on one page). Control on the meter
  decision's own `bar_lengths_seen` instead.
* ⚠️ Do not edit a source file while the suite runs (`inspect.getsource` reads
  through `linecache`); markdown is safe.
* `OMR_SURYA_KEEP_ALIVE=0` for unattended runs; **never `pkill` the shared
  `llama-server`.**
