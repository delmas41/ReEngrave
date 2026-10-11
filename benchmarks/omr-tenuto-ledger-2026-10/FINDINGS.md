# ROADMAP 2.84 — a ledger line the detector boxed as a tenuto

**STAGED, ADJUDICATE** (`adjudicators/family_precision.py`,
`adjudicate_articulation_is_not_an_articulation`; ORDER moved after
`Q.GLYPH_OWNER`). Lane `lane-tenuto-ledger`, off `origin/main` `40ab373a`.

## 0. The convention, and whose it is

Sean, 2026-10-10: *"handle ledger lines read as articulations - tenuto vs ledger
lines. There will never be another ledger line or note above a tenuto… right?"*
— after answering "Ledger line" on 2.12f round-2 tiles 1, 4 and 7
(`out/print/2.12f-r2-review/answers.json`, branch
`claude/roadmap-continuation-q883`).

General form, as built: a **ledger line lies between a staff and its note** —
a notehead stands ON it or FARTHER from that staff in its column. An
**articulation outside the staff lies BEYOND its note**. Above the staff nothing
is above a tenuto; below it is mirrored.

CONVENTION ASSUMED (the mirror) / WHAT WOULD FALSIFY IT: Sean answering N on
tile 12 of `out/print/2.84-review/` / NOT CONFIRMED until he answers. The
above-the-staff half is his own statement.

## 1. The population first (census, before any code)

`probe/census.py` over every `Q.ARTICULATION_MARK` row, GATHER rows only. The
record totals reproduce 2.12f's own count (Brahms 1,263, Litolff 18), which is
the census's control.

| record | marks | `articTenuto*` | tenuto with an x-overlapping head ON/beyond it, vs the FILING staff |
|---|--:|--:|--:|
| Brahms 1/i Breitkopf, whole (shared `20261009-all`) | 1,263 | 30 | 7 |
| Beethoven 5/i Litolff, whole (shared `20261010-night`) | 18 | 12 | 11 |
| Brahms count pages (small re-gather, pdf 0–1, this tree) | 4 | 1 | 1 |
| Litolff count pages (small re-gather, pdf 1–3, this tree) | 2 | 1 | 1 |

**All 42 tenuto boxes of the two whole movements were cropped and read against
the print** (`probe/tiles.py`, 600 dpi in the gather's frame, a corner bracket on
the box; frame control 42 of 42 real boxes pass, 2 of 42 boxes shifted (40,40)
px pass): **37 are ledger lines, 5 are other ink, and NONE is a real tenuto.**
The 5: the `e` of *espr.* (Brahms `glyph/7/1/2/6/16`), a beam end
(`10/0/10/4/27`), a slur (`12/1/9/6/10`), a *p* (`25/1/9/8/7`), and the rim of
a half note (Litolff `8/0/7/0/6`).

**Sean's hand-truth page** (Brahms 317803 p0, 1,345 boxes, 0 articulation
labels): the one articulation box we draw on it, `glyph/0/0/11/6/27`, IS his
ledger line `q1425` (IoU 0.997). 1 of 1.

**What the census changed in the design.** Against the staff a mark is FILED
on, only 18 of the 37 ledgers have a head beyond them. The other 19 are the
neighbour staff's ledgers padded into this cell (CLAUDE.md §10: the pad reaches
the next staff's ink): seen from the filing staff the head is staffward, seen
from the staff that OWNS the head it is beyond. So the rule asks **the head's
own staff**, `Q.GLYPH_OWNER` — which is why the decision now runs after the
ownership contest.

## 2. The rule

For an `articTenuto*` box only (SHAPE FROM THE CLASS, ROLE FROM THE GEOMETRY —
2.12: an accent, staccatissimo or marcato is not a dash), after the human
witness:

1. Every notehead box of the same bar (the mark's cell, and the same cell index
   on the two neighbour staves, PAGE pixels) that x-overlaps the dash. A head
   `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` refuses as not-a-head is skipped; one refused
   only as belonging elsewhere or as a duplicate box is still a head.
2. Its owner: a DECIDED `Q.GLYPH_OWNER`; else 2.7b's `belongs_to_a_nearer_staff`
   refusal, which names the staff; else the staff it is filed on (no contest).
   A NARROWED/ABSTAINED contest is not read.
3. Against the owner's own lines: the dash outside that staff's band, and the
   head's centre no more than `ON_A_STAFF_LINE_TOL_SPACES` (0.25, the measured
   registration scatter, reused) staffward of the dash's → **DECIDED True,
   `ledger_between_staff_and_note`**.
4. If only a head whose owner is unread could make it one →
   **ABSTAINED `head_owner_unread`**. No page box / no staff →
   **ABSTAINED `no_staff_geometry`**. Otherwise **False, `articulation`** as
   before.

**The grid is RECORDED, NOT GATING** (`rung_offset_spaces` in the detail), and
this contradicts the brief, so it is stated: (a) on Litolff the printed ledgers
stand ~1.1 spaces apart, so 6 of its 11 print-confirmed ledgers sit 0.30–0.41
spaces off the staff's space grid — measured both on the staff's page lines and
on the cell's own per-bar grid (via the head's `Q.NOTEHEAD_STAFF_POSITION`) —
and a 0.25 grid gate would have refused them; (b) the population holds NO real
tenuto, so a grid threshold has no negative to be calibrated or shown to fail
against (rule 7) — the same reason `RUNG_STEP_SHIPS` is False for ledger boxes.
What would make the grid ship: real tenutos with a head beyond them, which by
Sean's convention do not exist.

## 3. Base vs arm, one tree (ADJUDICATE replay; GATHER fixed)

`probe/readjudicate.py`: base = a clean worktree at `origin/main` `40ab373a`, arm
= this branch, the same saved GATHER, every decision the refusal reads
transitively. **Control that can fail:** rebuilt `Q.GLYPH_OWNER` == saved —
Litolff whole 9,423/9,423, Litolff count pages 1,135/1,135, and broken on
purpose (`RA_BREAK_CONTROL=1`, band distances dropped) 0/1,135. Brahms's older
shared record reproduces 33,780/34,106 and its count-page record 1,773/1,778
(CLAUDE.md §6b: shared records do not reproduce on today's tree) — identical in
base and arm, so the diff is still one tree against itself.

| record | tenuto → ledger | tenuto → abstained | tenuto kept | other marks changed |
|---|--:|--:|--:|--:|
| Brahms whole | 23 | 2 (`head_owner_unread`) | 5 | 0 of 1,233 |
| Litolff whole | 11 | 0 | 1 | 0 of 6 |
| Brahms count pages | 1 | 0 | 0 | 0 of 3 |
| Litolff count pages | 1 | 0 | 0 | 0 of 1 |

**Scored against the 42 crops (my reading of the print, §1):** 34 refused, **34
ledger lines (0 wrong)**; 5 non-ledger inks all kept (5 of 5); **3 ledgers not
refused**:

* `glyph/3/0/1/2/14` (= Sean's 2.12f tile 1) and `glyph/24/1/3/2/15` abstain
  `head_owner_unread`: the head's own ownership contest is NARROWED, and only
  one candidate staff makes the dash a ledger. Honest by rule 8.
* `glyph/24/1/2/7/20`: the head on it was boxed only in staff 3's cell and is
  owned, uncontested, by staff 3; by the print it hangs under staff 2's ledger.
  An upstream OWNERSHIP miss. **The dash itself is the evidence that would
  name the owner (Sean §10: the ledgers name the owner), but because it is
  tenuto-classed, GATHER's ladder (`gather._observe_ladder`, built from
  `ledgerLine` boxes only) never counts it** — a GATHER follow-up, not built
  here (two full re-gathers to price).

Sean's three tiles: 4 and 7 now decided ledger; 1 abstains (above).

**Downstream (named, not changed):** `export._place_articulations` already drops
a DECIDED refusal (`not_an_articulation:ledger_between_staff_and_note`), so the
34 stop being written as tenutos; an ABSTAINED refusal still falls through to
the owner, as every unrefused mark does today. `adjudicate_articulation_owner`
does not read this refusal — fenced (lane `2.12g-long-stem` owns that
function); it still files an owner verdict on a refused dash, which nothing
writes.

**The small re-gathers (`acceptance_quick`, GATHER+ADJUDICATE, base and arm, both
on `40ab373a`, dirty — iteration only).** The count-page stage summaries are
identical (articulation family 22/18/4 Brahms, 10/10 Litolff): the two tenutos
the census found sit on pdf p0 and p2, not the count pages. Read off the records
themselves: base decides both `articulation`; arm decides both
`ledger_between_staff_and_note` (Brahms `glyph/0/0/11/6/27` = Sean's hand-truth
ledger `q1425`; Litolff `glyph/2/1/0/5/4`); the other 4 marks are unchanged.

## 4. Tests

`tools/omr/tests/test_staged_tenuto_ledger.py`, 23 tests. **RED against
`origin/main`'s two source files: 10 failed, 11 passed** (the 11 are the
positive controls and the kept cases, which must pass on both; the two
neighbour-cell tests were added after the RED run — the positive one fails on
`origin/main` by construction, which only ever decides `False`). Every refusal
has a control in its class: a real tenuto beyond its note above and below the
staff, a tenuto whose box touches its note, a head in another column / another
bar, a dash inside the staff, an accent with a head beyond it. `staged.check`
192 → 192. Fast tier: 7,140 passed, 0 failed.

## 5. Blind tiles for Sean

`out/print/2.84-review/` (12, phone-sized, big number, nothing of ours drawn;
frame control 12 of 12 real pass, 1 of 12 shifted). Tiles 1–11 ask "L ledger,
T tenuto, N neither"; tile 12 asks the below-the-staff mirror (Y/N).
`manifest.json` carries what we read (hidden from him).
