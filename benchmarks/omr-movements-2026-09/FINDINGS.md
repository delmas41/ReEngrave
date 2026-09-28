# ROADMAP 4.2b — detecting a movement boundary off the page

2026-09-28. Branch `claude/movement-starts-4.2b`, base `ea3538cb`. Proof
budget per DECISIONS 2026-09-28 (Sean: build and wire, cheap proof only):
RED→GREEN unit tests (`tools/omr/tests/test_staged_movement_start.py`, 23
tests) plus ONE real boundary, gathered at ONE page pair — no whole-work
gather.

## 1. The mechanism

`tools.omr.staged.adjudicators.movement.adjudicate_movement_start`, quantity
`Q.MOVEMENT_SPANS`, scope `Kind.DOCUMENT`, first in `adjudicate.ORDER`. Reads
GATHER only: `Q.DIRECTION_WORD` (tempo heading at a system's own cell 0),
`Q.METER_GLYPH` (a meter statement — glyph at `frame == "cell:0"` — on a
majority of the system's staves, never a mid-system change), `Q.MARGIN_LABEL`
(a reset to fuller names, by coverage and length, vs the immediately
preceding system), `Q.STAFF_EXTENT` (the top staff's left edge, wider than
the document's own median). Requires **2 of these 4** cues before calling a
system a boundary (CLAUDE.md's brief: "at least 2-3"); a single cue alone —
the exact shape a mid-movement tempo change prints — abstains
(`no_boundary_detected`), never invents a split. A human `--movements`
observation always wins outright (`human_spans_supplied`). See the module's
own docstring for the CONVENTION ASSUMED / WHAT WOULD FALSIFY IT block and
the six unmeasured thresholds.

**The fifth cue the brief names is not built:** "the system after a final
double barline" has no quantity in this record at all (no barline-type
vocabulary anywhere in `record.Q`) — the brief's own wording is conditional
("if barlines carry that"), and the tree carries nothing to read.

**Ordering, and why:** `rhythm._movement_spans` / `header._movement_spans`
read `Q.MOVEMENT_SPANS` via `ev.rows()` — the FROZEN gather log — so a human
`--movements` observation reaches them regardless of ORDER. A DETECTED
boundary is a VERDICT, in a different store (`Log._vrd`, not `Log._obs`), so
it reaches those same two functions only through a NEW `ev.verdict()`
fallback added to each, which requires `movement_start` to have already run
— hence first in `adjudicate.ORDER`, ahead of `system_membership` itself.
The same fallback was needed a second place: `movements.spans_from_result`
(the loaded-JSON path `tools.omr.staged`'s own CLI export split and
`tools.omr.staged.export`'s standalone re-export both call) only ever
scanned `observations`; extended to check `verdicts` for a DECIDED
`Q.MOVEMENT_SPANS` too. Both fallbacks check the human observation FIRST,
unconditionally.

## 2. RED→GREEN

`tools/omr/tests/test_staged_movement_start.py`, 23 tests: pure cue
functions (tempo word needs cell 0 AND category=tempo; meter statement needs
a majority AND cell 0; label reset needs coverage AND either absence or
length; indent needs a real widening); the decision over a real (if tiny)
`Log` (several cues together → detected; a human `--movements` → abstain
`human_spans_supplied`, and the meter/key carries provably read the HUMAN
spans over a co-existing detected one; no cues anywhere → `no_boundary_
detected`, and the carries still read `()`); the `movements.spans_from_result`
verdict fallback, independently. **The control that can fail**
(`TestATempoWordAloneIsNotAStart`): a system with the tempo cue ALONE —
exactly Litolff p.62's own mid-movement "Tempo I." + fresh meter, which
`gather._gather_meter_glyphs`'s docstring already names as the shape this
must not trip on — abstains. Verified directly that the control really can
fail: `is_movement_start(cues, min_cues=1)` on that exact cue set returns
`True` where the shipped `min_cues=2` returns `False`.

All 23 pass; full fast tier `pytest tools/omr/tests -m "not slow" -q -x`:
3,542 passed, 3 skipped (was 3,511 on main — the +31 include this file and
`test_reengrave_import.py`'s two renamed tests).

## 3. The one real boundary

Beethoven 5, Litolff `imslp984073`. Rendered pdftoppm pages 16–18 at low DPI
(`-r 50`) and looked before gathering anything (CLAUDE.md's own instruction)
— found the boundary one page later than the brief's own estimate: movement
1 runs through 0-idx page **16** (pdftoppm 17), movement 2 ("Andante con
moto") opens at 0-idx page **17** (pdftoppm 18), matching the brief's
fallback ("or near it") exactly.

Gathered ONLY `--pages 16-17` (0-idx), `--dpi 600`, weights
`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, `--route-weights`,
Surya ON (`OMR_SURYA_KEEP_ALIVE=0`, unattended). Record:
`beethoven--symphony-5.record.json` (not committed — regenerable from the
command above; the PDF and weights are machine-local per CLAUDE.md §5a/§8).

**Cues, read straight off the record** (`system/17/0` = the boundary system,
the true first system of the Andante con moto):

| system | tempo_word | meter_statement | label_reset | wider_indent | fired |
|---|---|---|---|---|---|
| `system/16/1` (continuation, movement 1's own last system) | false | false | false | false | 0 |
| **`system/17/0` (the boundary)** | **true** | false | **true** | **true** | **3** |
| `system/17/1` (continuation, inside movement 2) | false | false | false | false | 0 |
| `system/17/2` (continuation, inside movement 2) | false | false | false | false | 0 |

`meter_statement` did NOT fire on the true boundary: the detector filed one
stray `timeSig1` at cell 0 on a single staff (Basso) — not a majority, so
the cue correctly declined rather than firing on noise. The other three
cues carried it (3 of 4, well past the 2-of-4 floor), and — just as
important — **every continuation system in the gathered window, on both
sides of the real boundary, fired zero cues.** No false positive.

**The decision's actual output** (`adjudicate.run(log, order=(Q.MOVEMENT_
SPANS,))` against the frozen gather log): `Outcome.DECIDED`,
`reason="detected"`, value:
```
[{"number": 1, "first_page": 16, "first_system": 0, "last_page": 16, "last_system": 1},
 {"number": 2, "first_page": 17, "first_system": 0, "last_page": 17, "last_system": 2}]
```
— the same shape `--movements` itself would produce.

**Crops** (`out/print/`, 600 dpi, frame control: min/max/spread reported per
crop, all three at spread 255 — not flat):
- `movements-01-boundary-head.png` — `system/17/0`'s own header: "Andante
  con moto ♩=92" bracketed (red), full instrument names bracketed (blue,
  "Flauti." / "Oboi." / "Clarinetti in B." / … / "Basso.").
- `movements-02-continuation-head.png` — `system/16/1`, the system
  immediately before the boundary: abbreviated labels only ("Fl." / "Ob." /
  "Cl." / "Fag." / "Cor." / "Tr." / "Tp."), no tempo word, mid-fortissimo
  tutti (bar 489 — movement 1's own coda).
- `movements-03-tempo-word-zoom.png` — the exact `Q.DIRECTION_WORD` subject
  (`glyph/17/0/0/0/90000`) corner-bracketed at 3x, reading "Andante con
  moto." (tesseract).

`crop-manifest.json` carries `VERDICT_none_yet: null` on every crop, for
Sean.

## 4. Candidate four-movement Litolff spec (read off the renders — NOT gathered)

Read directly off `pdftoppm -r 50/100/150` renders of the whole 88-page PDF
(`pdfinfo` confirms 88 pages), looking for the same convention (tempo
heading + full names, or an unmistakable orchestration change): piccolo,
contrabassoon and three trombones appear ONLY from the Finale on, and this
edition restarts its own bar numbering at each movement (confirmed at every
boundary below).

| movement | first pdf page (0-idx) | pdftoppm page | what's printed there |
|---|---|---|---|
| 1. Allegro con brio | 0 | 1 | (the work's own opening) |
| 2. Andante con moto | 17 | 18 | "Andante con moto ♩=92" ×3, full names |
| 3. Scherzo: Allegro | 32 | 33 | "Allegro ♩=96" ×3, "Corni in Es" (was "in C"), Violoncello **et Basso** condensed |
| 4. Allegro (Finale) | 44 | 45 | "Allegro ♩=84" ×3, Flauto piccolo / Contrafagotto / 3 Tromboni enter — full names |

Movement 1 → 2's boundary is the one gathered above; 2→3 and 3→4 are
**read off the page only**, per the brief ("do not gather them"). The 3→4
transition is the famous attacca bridge (sustained timpani roll,
crescendo, trumpets/horns) — pdftoppm page 44 (0-idx 43) is still the
Scherzo's own coda, page 45 (0-idx 44) opens the Finale outright, full
orchestra fortissimo, bar 1.

**Candidate `--movements` spec, for Sean to confirm:**

```
1:0-16,2:17-31,3:32-43,4:44-87
```

(88 total pages, 0-indexed inclusive; last page, pdftoppm 88, prints "END OF
EDITION".)

## 5. `staged.check`

251 → **250** on main. The one point of movement: a stale `reach.py`
`KNOWN_GAPS` entry for `Q.STAFF_EXTENT` ("REMOVE THIS ENTRY the day a
consumer lands") — `movement_start` is now that consumer, so the entry
(and the module docstring line naming it) were removed rather than left to
report `stale gap entries` (which `reach --check` scores as BROKEN, not
merely open). No other check moved.
