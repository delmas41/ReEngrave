# Can the reference MusicXML be ground truth? A per-row answer

**Sean, 2026-09-05:** *"I am not sure our MXL will work as a ground truth —
unless we can determine that the amount of staves matches."*

**Answer: the counts do not match, they were never going to, and where we can
check it the mismatch decomposes cleanly.** On every row with a hand-read
part→staff map, condensation plus tacet suppression explain the whole
difference — **residual exactly 0** — and **detected staves equal the hand-read
printed count on all 10.** So the encoding is not wrong and neither are we; they
are counting different things.

*(Written up by the coordinating session from the measurement agent's report —
its harness refused it a `.md` file. Every number is reproducible from
`divergence.json`, `ambiguous_audit.json` and `ab_roster_ambiguity.json` on this
branch.)*

---

## The partition Sean asked for

**Usable as per-staff truth — 10 rows.** Both Beethoven editions p1/p2, all
three Dvořák, Brahms p1/p3/p4. Difference fully attributed, residual 0.

**Aggregate only — 10 rows.** Beethoven p3/p4 in both editions, Brahms p2, all
four Mahler, Bach. No hand-read map exists, and for Bach and Mahler one cannot
be built by position at all.

Representative rows:

| row | enc parts | printed (hand) | detected | condensed | tacet | resid |
|---|--:|--:|--:|--:|--:|--:|
| `beethoven-5-984073-p1` | 18 | 12 | 12 | 6 | 0 | **0** |
| `beethoven-5-984073-p2` | 18 | 11 | 11/11 | 7 | 0 | **0** |
| `dvorak-9-405834-p5` | 15 | 15 | 15 | **0** | 0 | **0** |
| `brahms-1-317803-p1` | 21 | 14 | 14 | 7 | 0 | **0** |
| `mahler-5-local-p2` | **25** | — | 17 | — | — | — |
| `bach-brandenburg3-p1` | 11 | — | 12/12 | — | — | — |

## Three causes, and they run in BOTH directions

- **parts > staves — condensation.** `Flauti` is one printed staff carrying two
  encoded parts. Beethoven, Brahms.
- **staves > parts — a grand staff.** Bach encodes **11** parts and prints
  **12** staves; `works.json`'s own note says the `Cembalo` grand staff "breaks
  the one-staff-one-entry pairing".
- ⚠️ **`works.json`'s `n_parts` is WRONG for Mahler.** It says 38; the file has
  **25 parts and 38 declared staves** (`Sechs Hörner in F.` declares 3, nine
  others declare 2). Every other reference has parts == staves, so the field was
  right *by coincidence* on 16 rows. The *engraved* Mahler truth genuinely has
  38 parts, because the LilyPond round-trip flattens multi-staff parts — so our
  two truth files disagree about how many parts one movement has.

## ⚠️ The engraved 11-work pool CANNOT answer this question

Every row is 1:1 (only `dvorak-sym9-mvt4` 18/19 and `tchaikovsky-sym6-mvt2`
16/17 differ, via one 2-staff part). **That is by construction, not by
measurement** — the page is rendered *from* the truth file. Do not cite the
engraved pool as evidence that the MXL works as ground truth.

## The Mahler "19 vs 17" — resolved, and it is not tree-vs-fixture

It is **pre-filter versus post-filter inside one run**. The stored fixture, a
fresh run, and `works.json` all say **17**; the roster's evidence block says
**19** because it counts raw `detect_staves` output.

The extra bands have **zero height** (`top_y == bottom_y`) and are **real
one-line percussion staves** — the region was rendered and confirmed: single
rules crossed by barlines, carrying whole-measure rests. The margin reader names
them (`Grosse Trommel…`, `Kleine Trommel Tamtam`) and the reference encodes them
as four of its 25 parts.

Zero-height counts match the raw-vs-detected gap exactly: **p2 2, p3 2, p4 3,
p5 4 — 11 real printed staves lost.** `staff_index` is preserved across the
filter, so the roster's ordinal join is **not** misaligned; only its coverage
denominator is. ⚠️ **The four Mahler rows the roster session excluded as
unmeasurable were excluded for a conflict that does not exist.**

⚠️ And the hand-read truth undercounts them too — both we and `works.json` count
five-line staves and call that the staff count. A one-line percussion staff is a
staff.

## ⚠️ A regression this found, and it is FIXED (`c0a80ae7`)

`OMR_ROSTER` went default-on the same day, and **12 staves across 9 orchestral
rows exported as `Bass voice` — a singer** — at the foot of the string section.
Seven were caused by the roster; five predate it. One is `'mbone Basso'`, a
truncated bass **trombone**.

`contextual` withholds an ambiguous slot from the score-order prior on purpose,
then the roster refill put it back with `setdefault` — on the reasoning that a
roster name IS a label, which is true and is not the point. **The ambiguity
lives in the lexicon, not in the reading:** `Basso.` resolves to `Bass voice`
whichever page it came from.

| | slot handed to prior | support | final |
|---|---|---|---|
| `OMR_ROSTER=1` | `Bass voice` | `[]` | **Bass voice** ✗ |
| `OMR_ROSTER=0` | *withheld* | `Contrabass 0.643 / Cello 0.357` | **Contrabass** ✓ |

reproducing `_ambiguous_label_slots`' own docstring figure to the digit.

⚠️ **Nothing in the metric could have caught it.** The roster shipped on a
measured 0 edits, correctly argued — musicdiff does not score `<part-name>` —
and that same blindness hides this. **A consumer the metric cannot see needs a
check the metric is not.** Guarded now by
`tools/omr/tests/test_contextual_roster_ambiguity.py`, verified to fail when the
guard is removed.

## The readings (deliverable 2)

31 of 31 rows transcribed, 0 failures. `show_readings.py` prints per-staff
instrument + provenance, clef, key and meter.

Provenance corpus-wide: **label 462, score_order 102, roster 45, ambiguity 2,
unnamed 9 — coverage 0.985.**

Identity against hand-read names: **128/133 = 0.962**, corroborating the roster
session's 0.955. ⚠️ **That figure is optimistic by construction** — the truth
names go through the *same* lexicon, so `Basso` → `Bass voice` scores as correct
on both sides. The honest figure is **126/133 = 0.947**.

The 5 outright mismatches are all `score_order`, none from a label or a roster:
`Viola`→`Violin` ×2 (Beethoven p2) and `4 Hörner in Es 3./4.`→`Trumpet` ×3
(Brahms's second horn staff — multiplicity again).

## Three things that look wrong to a musician's eye

- ⚠️ **Meter is not uniform within a system.** Beethoven 5 p.1 prints 2/4 on all
  twelve staves; we read 2/4 on nine and **4/4 on three** (Timpani, Viola,
  Basso). Mahler p2 (2/2) reads 2/2, 2/4, 4/4 and nothing across six of 17
  staves. **A meter is a system-wide fact being read per staff** — and
  `rhythm._dominant_detected_meter` already votes one per page, so this is a
  reconciliation that exists and is not reaching these staves.
- **Key signatures are the weak reading**: on the only two rows carrying
  hand-read keys, **clef 23/24 = 0.958 against key 14/24 = 0.583** — and two
  errors are *wrong* rather than absent (2 flats where the page prints 3, on
  Oboe and Cello in C minor).
- Mahler's **Contrabassoon reads treble clef**.
