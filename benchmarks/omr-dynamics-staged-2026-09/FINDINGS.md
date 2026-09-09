# Dynamics into the staged pipeline, and what a partial letter run is worth

*2026-09-08. Two of the three dynamics decisions had nothing behind them; the
third question — what a letter run that spells nothing should export as — was
measured and the answer is **not what the standing note said**.*

---

## 1. The two gatherers, and why the FRAME is the whole of it

`Q.DYNAMIC_LETTER` and `Q.WEDGE_BOX` were declared observation quantities in
`staged/record.py` that **no gatherer emitted** — the schema was wired and the
evidence side was empty, so implementing `adjudicate_dynamic` first would have
produced rulings with no basis. Both are now gathered.

They are gathered **in page pixels against the staff's own bottom line**, and
that is not a tidiness preference:

| | frame | consequence |
|---|---|---|
| `export.measure_dynamics` (today) | per-**measure cell**, padded 4–6 staff spaces | 24% of letters land in the staff ABOVE — distance exactly 1, no exceptions |
| `hairpin_detection` | **page pixels, per staff** | attribution right **by construction** |
| both new gatherers | **page pixels, per staff** | comparable to each other for the first time |

`measure_extractor` pads a cell by four staff spaces, or six where the
neighbouring staff is more than six spaces off — so **the same ink sits at a
different height in the cell frame depending on how crowded its neighbours
are.** A band number taken there moves when the page's crowding changes and the
ink does not. `TestTheLetterIsMeasuredAgainstTheSTAFFNotTheCell` builds two
cells holding identical page ink under two paddings and asserts the offset does
not notice; it goes RED when the offset is taken from `d.y_center`.

⚠️ **`READERS.CV_HAIRPINS` is a new reader, not a mode of `CV_LINES`.** Two rows
from one reader on one crop are ONE signal (`Evidence.independent`), and this
rung reads the WHOLE page with staff lines INTACT while `line_detection` reads
an ERASED cell. Filing them together would collapse two genuinely independent
readings of one band.

⚠️ **The CV rung is gathered whatever `OMR_CV_HAIRPINS` says.** That flag guards
what the legacy EXPORTER does with a hairpin. A reader silenced by an
export-side flag would make the log a record of a configuration rather than of
the page — and that flag's own cost is under-attributed, which is a question
only a record can settle.

⚠️ **Every cell gets a row, including one with no dynamic letter in it, and
that is LOAD-BEARING.** A decision's subjects come from the rows in the log, so
a staff carrying no letter of its own has no `Q.DYNAMIC` subject — and a letter
that ownership moves ONTO it would be silently lost. The test pins exactly that
line and says so.

## 2. `adjudicate_dynamic` — the fix is the ownership query, not the spelling

The composition `adjudicate.py` already declared is the right one, and
`Q.GLYPH_OWNER` is the one piece of it that was never a stub:

```
Q.DYNAMIC_LETTER ─┐
                  ├─> Q.GLYPH_OWNER ──> Q.DYNAMIC
Q.WEDGE_BOX ──────┴─> Q.WEDGE_ANCHOR   (still a stub; now has evidence)
```

A letter belongs to a cell when the ownership verdict names that cell's STAFF,
whatever cell it was cut from — **both directions of the same move**, so a
letter cut from this cell and owned elsewhere leaves it. A band GATE is refused
and stays refused: it under-emits on both arms (0.63 engraved, 0.59 scanned)
because **83% of re-attributed letters are the target staff's SOLE evidence**,
the twin having already been deleted by `_dedupe_cross_staff_detections` on
distance. Deleting it a second time is not a fix.

An unspellable run returns `Ruling.narrow`, not `abstain`: *"there is a mark
here and I cannot spell it"* is a different answer from *"I saw nothing"*, and
the candidates are every dynamic word the run could still become.

⚠️ **The assembly rule is deliberately the exporter's, unchanged**, so the only
difference between the staged path and the shipped one is the ownership query
and the frame. It is not a good rule (§3), and every run now carries its own
`band_offsets` — the vertical evidence the exporter has never had — so a
replacement can be measured rather than argued.

## 3. ⚠️ What a dropped run actually is — the standing note was wrong

The note this work started from said the discarded population is *"dominated by
a lone `s` (15 of 31)"*. That is true of the **11-page band corpus**
(`omr-dynamics-band-2026-09/FINDINGS.md:349`) and **not** of the committed
Brahms 1 / Breitkopf transcription, where the same code
(`probe/probe_partial_runs.py`, which calls `export.measure_dynamics`'s own
assembly loop rather than re-implementing it) reports:

```
kept   159 runs / 216 letters
dropped 20 runs /  49 letters
   m 3 · ffp 2 · z 2 · s 2 · fsf 1 · fmm 1 · mm 1 · pmff 1 · pf 1 · pz 1
   mmf 1 · ppmsf 1 · ppzmf 1 · pfsf 1 · psf 1
   → a prefix of NOTHING: 15 of 20
```

**`ppmsf` is five letters run together, and no dynamic is.** Those are an
ASSEMBLY failure, not one unreadable mark, and exporting
`<other-dynamics>ppmsf` would be worse than silence. So the obvious fix — emit
the run's own text — is refused.

⚠️ **And re-assembling on the MEDIAN letter width instead of the max is not the
lever**, which was the natural suspicion (`width = max(w …)` makes one wide box
declare everything adjacent). Measured on the same transcription: kept runs
159 → 162, dropped still 20, `ppmsf` intact. Recorded so nobody re-tries it.

## 4. So what a partial run may export as — measured, and REFUSED

`OMR_PARTIAL_DYNAMICS`, three modes, graded by how much they assert:

| mode | rule |
|---|---|
| `off` (default) | the run is dropped — today |
| `complete` | export only what **every surviving completion agrees on**: `s` → `sf`, because all of `sf`/`sfp`/`sfz` begin `sf`. `m` stays dropped: `mf` and `mp` agree on nothing further |
| `other` | `complete`, plus `<other-dynamics>` carrying the run's own text |

A prefix of NOTHING is dropped under every mode. Flag-off is **byte-identical
to `main`**, verified by md5 against `main`'s own `export.py` on the committed
Brahms transcription.

Priced over the **20-row scan gate** with `probe/reexport_arm.py` — the arm's
own `.omr.json` files re-exported and re-scored, so the transcribe half is held
byte-identical and the delta is the export change and nothing else:

| mode | summed edits, 20 rows | rows worse | unchanged | **better** |
|---|--:|--:|--:|--:|
| `off` | 74,608 | — | — | — |
| `complete` | 74,623 (**+15**) | 6 | 14 | **0** |
| `other` | 74,638 (**+30**) | 11 | 9 | **0** |

**Not one row improves under either mode.** `complete` adds 19 dynamics for +15
edits — 0.79 edits per added symbol, so roughly **4 of 19 paired** and the rest
were charged as insertions.

⚠️ **The buckets are reported and NOT used for attribution.** `wrong dynamic`
rises on four rows (7→8, 57→60, 3→4, 32→33) which reads like "the mark paired
and we spelled it wrong", and on the two big Beethoven rows `entire measure
insert/delete` FALLS (1850→1812, 1662→1642) while `wrong note` RISES
(679→722, 756→782) — that is the block diff re-planning around an added symbol,
not a claim about notes. OMR-NED establishes correspondence by pitch and 92.5%
of scan edits are unpaired bulk, so the direction of an A/B is valid and the
category breakdown is not evidence about cause.

**Decision: `off` stays the default.** The recovery is real ink and the metric
will not pay for it *in the legacy exporter*, which has no ownership — and the
placement fault is exactly what would stop a correctly-recovered `sf` from
pairing. It is worth re-pricing on the staged path, where ownership is decided
before the word is spelled; it is not worth shipping in the path that cannot
use it.

## 5. What this does not know

- **No staged EXPORT exists**, so `Q.DYNAMIC`'s ruling reaches no file. The
  gathering and adjudication are measured by their own tests, not by OMR-NED.
  (⚠️ A session ledger claimed the staged pipeline "exports a file now"; there
  is no exporter in `tools/omr/staged/` on this branch — the tree outranks the
  ledger.)
- **`Q.WEDGE_ANCHOR` and `Q.DIRECTION` remain stubs.** `Q.WEDGE_BOX` now has
  evidence behind it, which is what an anchor rule needs; the anchor rule
  itself is untouched, and its documented blindness to `duration_beats` is
  still untested.
- **The dropped-run census is one work.** Brahms 1 / Breitkopf disagrees with
  the 11-page band corpus about the SHAPE of the population, which is itself
  the finding — do not quote either as *the* mix.
- The scan truth's dynamics come from the reference **encoding**. A dynamic the
  engraver printed and the encoder omitted counts against us and is not our
  error.
