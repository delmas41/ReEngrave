# The Viola read −1 against −3, and it is a READER, not the alto slot table

Answers the one question left open by
[`docs/handoff-2026-09-08-evening-to-local-session.md`](../../docs/handoff-2026-09-08-evening-to-local-session.md).
Measured 2026-09-08 on the local Mac, which — unlike the cloud container that
opened Step 2 — has the weights, the library and the venvs.

Evidence extract: [`out/beet5-p1-keysig-chain.json`](out/beet5-p1-keysig-chain.json).
Regenerate with:

```bash
PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
W=tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
OMR_SURYA_KEEP_ALIVE=0 python3 -u -m tools.omr.staged "$PDF" --pages 1 --weights "$W" --out staged.json --progress
```

⚠️ `OMR_SURYA_KEEP_ALIVE=0` is not decoration — the resident Surya server is
SHARED across sessions and an unattended run must not depend on state it is not
allowed to repair. Nothing here was `pkill`ed.

---

## 1. The answer: `n_accidentals` is **1**

The handoff named the number that splits the two candidates and said what each
would mean. It reads **1**: only one flat was FOUND. **A detection shortfall.
The fit honestly reported what it had, and the alto slot table is not
implicated.**

The same run corroborates that from the inside, which is worth more than the
single field:

| st | staff | truth | clef read | staged | n_acc | outcome |
|--:|---|--:|---|--:|--:|---|
| 2 | Clarinetti in B | −1 | treble ✓ | **−1 ✓** | 1 | fitted |
| 8 | Violino II | −3 | treble ✓ | **−3 ✓** | 3 | fitted |
| 9 | **Viola** | **−3** | **alto ✓** | **−1 ✗** | **1** | fitted |
| 10 | Violoncello | −3 | bass ✓ | **−3 ✓** | 3 | fitted |

Two staves that found three boxes read −3; two that found one read −1. The
Viola behaves exactly like the Clarinet, and the Clarinet is **right** — one
flat is what a B♭ clarinet prints in this movement. There is no arithmetic here
that an alto slot table could be wrong about. **The clef read `alto` correctly
on that staff, and every one of the twelve clefs is correct.**

Sean's musical correction is what made this diagnosable: an alto clef changes
*where* the accidentals are drawn, not *how many*, and the Viola is
non-transposing, so it is −3 like everyone else. That ruled out the cascade and
left the fit — and the fit turns out to have been handed one box.

## 2. And the single box is probably not a flat

The run positions across the system, in header-window px:

| st | staff | truth | run positions |
|--:|---|--:|---|
| 0 | Flauti | −3 | `[580]` |
| 2 | Clarinetti in B | −1 | `[700]` |
| 8 | Violino II | −3 | `[700, 827, 948]` |
| 9 | **Viola** | −3 | **`[1161]`** |
| 10 | Violoncello | −3 | `[664, 808, 922]` |

Every real accidental found anywhere on this system lies in **580–948**. The
Viola's one box sits at **1161** — about 1.7 slot-widths past the last real
flat position on the page (the runs are ~124 px apart). A key signature is
printed at the same place across a system, modulo clef width. So the box the
Viola fitted is most likely ink from further right — the meter, or a first
note — and the −1 is not "two flats missed" so much as **one thing found that
was not a flat**.

⚠️ Stated as the strength it has: this is a POSITION argument over one system,
not a crop I have looked at. It is enough to say the box is anomalous, not
enough to name what it is.

## 3. The finding underneath it — GATHER is wired to the weaker reader

This page has TWO readers available, and their difference on THIS PAGE is
already measured and written down in two places. `transcribe.py:1521`:

> matched on Beethoven 5 p.1, where the locator reads 2 of 12 staves given the
> correct clef and this reads 11

`tools/omr/staged/gather.py:982` imports `locate_key_signature` and nothing
else. **`key_signature_template` is referenced nowhere under `tools/omr/staged/`**
(`grep -rn key_signature_template tools/omr/staged/` → no match), while
`transcribe.py:272` imports it.

And the run reproduces the locator's documented figure. Of twelve staves, the
staged path decided **4** and got **3** right; of the nine staves that print
three flats, **five found no run at all**, one (Flauti) found a single box that
its settled clef refused, and one (Viola) fitted a box outside the band. Only
Violino II and Violoncello read the signature the page prints.

**So the Viola is one symptom of a wired-reader gap, not a bug of its own.**
Fixing the Viola specifically would be fixing the least informative instance.

## 4. Two things the staged path got RIGHT that are easy to miss

* **Flauti abstained `run_fits_no_slot_table`.** One box, fitting the bass,
  alto and tenor tables but not the `treble` its clef settled on. That is the
  contradiction branch working: the guard the handoff describes — *no clef, no
  name; wrong clef, no name either* — refusing to emit a number rather than
  emitting a plausible one. Legacy has no such branch here.
* **The three staves that print NO key signature** (Corni, Trombe, Timpani —
  truth 0) found no run and abstained. Right answer, right reason.
  ⚠️ Though `fifths: 0` is a positive reading and an abstention is not the same
  claim, so this is "not wrong" rather than "correct".

## 5. What this does NOT say

* **No accuracy arm was run.** No `scan_eval`, no `orchestral_eval`, no
  OMR-NED. This is one page of one edition, read once.
* **It says nothing about the clefs being right.** All twelve agree with the
  hand-verified `staves[i].clef` in `works.json`, which is truth — but that is
  the row's truth, not a measurement of the clef path.
* **The 11-of-12 template figure is quoted, not re-measured here.** It is a
  claim in `transcribe.py` and in CLAUDE.md about this exact page. The locator
  half of it I did reproduce.

## 6. The next step, and the constraint on it

Wire the template reader into GATHER as a second witness to
`Q.KEYSIG_CLEF_FIT` / `Q.KEYSIG_RUN_POSITION`, tagged with its own `reader=`.

⚠️ **It may not simply win.** The legacy call site records a MEASURED restraint
that has to survive the port: the template reader speaks **only into gaps**,
because it is the one source here that can OVER-count. Letting the fuller
reading win gains 1 staff on Beethoven 5 p.2 and 2 on the Pastoral and costs a
WRONG reading on WTC I p.17, the cleanest page in the corpus. In `staged/` that
restraint is a **declared precedence in the adjudicator**, not an `if read is
None` chain in a reader — which is the whole reason the stage exists, and is
why this is a design change rather than an import.

Parked as **D20** in [`tools/omr/staged/ASSUMPTIONS.md`](../../tools/omr/staged/ASSUMPTIONS.md)
with its evidence, per that file's rule that a park keeps what was seen.
