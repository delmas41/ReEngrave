# The sounding pitch — a SOUNDING fact was written into a DRAWING slot

2026-09-21, no flag. Item 1 of the symbol-dossier sweep's ranked repair list
(§3). Item 2, the beam, is in [BEAM_FINDINGS.md](BEAM_FINDINGS.md).

Branch `claude/sounding-pitch-and-beam-2026-09-21`, base `28749347`
(`origin/claude/part-instrument-check-2026-09` — **not** `origin/main`, which
is four days stale and 169 commits behind).

---

## 1. It is ONE bug, not two

The brief asked whether the missing `<alter>` and the suspicious 334
`<accidental>` were one fault. **They are, and naming it that way is the
finding**: a fact about what a note SOUNDS was routed into the slot that says
what the engraver DREW.

`Q.ACCIDENTAL` is declared at `record.py:937` as `# respelled when the key
settles`, and its **only producer in the tree** is
`consequences.respell_accidental`, whose cause is `Q.KEY_SIGNATURE`. So the row
means *this note is altered by the key*. `staged/export.py` handed it to
`_legacy._mxl_note(accidental=)`, which renders `<accidental>` — and that
renderer's own comment states the distinction the staged path inverted:

> `<accidental>` … is what the engraver DREW; `<alter>` inside `<pitch>` is
> what sounds. The two are independent.

Measured on the record behind the artefact Sean read:

| | Litolff Beethoven 5 pp.1-4 |
|---|--:|
| `Q.ACCIDENTAL` verdicts | **269** |
| …decided by `respell_accidental` | **269 (100%)** |
| …decided by anything else | **0** |
| subjects carrying more than one | **0** |
| accidental glyphs the DETECTOR read | **256** |
| …that become a verdict | **0** |

The two populations are **disjoint**. Every drawn `<accidental>` was a
sounding fact in the wrong slot; every printed accidental was invisible.

⚠️ **A dead guard falls out of this.** `respell_accidental` skips a note that
already carries a `Q.ACCIDENTAL` — correct as written — but with no other
producer that branch **cannot fire on a real record** (0 of 269 subjects carry
two). Left alone: it is right, and becomes live the day a reader lands.

---

## 2. The dossier's description of the symptom is half wrong

The repair list says: *"prints right, sounds wrong"*. Put through the two
renderers this project uses (`probe/renderer_semantics.py`, minimal one-note
files, E in 3 flats):

| arm | Verovio `accid.ges` (SOUNDS) | accidental glyphs DRAWN | music21 MIDI |
|---|---|--:|--:|
| **today** — `<accidental>`, no `<alter>` | *absent* → **E natural** | **4** (3 key + **1 on the note**) | 63 (E-flat) |
| **fixed** — `<alter>`, no `<accidental>` | `f` → E-flat | 3 (key signature only) | 63 (E-flat) |
| bare — neither | *absent* → E natural | 3 | 64 (E natural) |

So **"sounds wrong" is right and "prints right" is not**. Today's file draws a
redundant accidental on *every* key-altered note — 221 on this document —
where an engraver prints the flat once, in the key signature.

⚠️⚠️ **THE TWO READERS DISAGREE ABOUT THE SOUND, WHICH IS A STRONGER REASON TO
FIX IT THAN EITHER ALONE.** music21 **infers** the alteration from
`<accidental>` and reports E-flat; Verovio does not and reports E natural. On
the real artefacts Verovio reads the before-file as **0 sounding alterations /
221 drawn glyphs** and the after-file as **221 sounding / 0 drawn**. *A file
whose meaning depends on the consumer's leniency is a file that is wrong* — and
it is why the music21 delta check in `probe/readback.py` is reported and
deliberately **not** asserted on.

---

## 3. The stage question — the rule ORDER answers it

The brief offered two options. **Both are refused, and the reason is measured.**

- **(i) EVALUATE — `respell_accidental` also revises `Q.PITCH`.** Textbook on
  the stage table (key + letter implies the altered pitch is *forced*, not
  *best*), and `move_glyph` already supersedes `Q.PITCH` in the same file.
  **It is a trap.** Rules dispatch in `DOWNHILL` order by CAUSE:
  `restate_pitch` (`Q.CLEF`, 7) → `respell_accidental` (`Q.KEY_SIGNATURE`, 8)
  → **`move_glyph` (`Q.GLYPH_OWNER`, 9)** — and `move_glyph` re-derives the
  plain letter from position+clef and supersedes. Measured: **629** pitch
  verdicts, **178** superseding a prior, and **8 subjects carry both a
  `move_glyph` pitch and a key-derived accidental**. Under (i) those 8
  alterations are **silently wiped**.
- **(ii) EXPORT — fold it in at the render.** The mechanism, not the reason.

**(iii) — what shipped: the record is already correct and only the EXPORTER's
routing is wrong.** `Q.PITCH` carries letter+octave (position+clef);
`Q.ACCIDENTAL` carries the alteration (the key). Two facts, two rows, two
readers — the separation this repo insists on elsewhere. Jointly they are the
sounding pitch; the exporter must combine them. It survives `move_glyph` by
construction, and **no record is touched**, so the "perturbs upstream by
existing" hazard is avoided outright.

---

## 4. What changed

`tools/omr/staged/export.py` only.

- `_sounding_pitch(pitch, alteration)` — `E4`+`b` → `Eb4`, which
  `_legacy._mxl_pitch_block` renders as `<alter>-1`. It **refuses rather than
  guesses**: an unparseable pitch, an unknown alteration (`natural` is alter
  0), or an already-altered pitch is returned unchanged.
- `_place_notes` folds the alteration in, recording `applied` **only where the
  spelling actually moved the pitch**.
- The render site passes **no `accidental=`**, with the abstention named.
- `counters["accidentals"]` → `counters["pitches_altered_by_the_key"]`.
  **Renamed, not pinned at zero**: the old name counted `<accidental>` elements
  and the exporter now writes none — the *control that computes the wrong
  thing* family.
- `coverage()` gains `accidental_reading`: glyphs detected, glyphs read into a
  verdict (**derived**, not a literal 0), pitches altered.

---

## 5. REACH first, then the numbers

Two publishers, one record each, exported twice by two trees (`export_arm.py`:
byte snapshot of `export.py`, swap to base, export, restore, **verify the
hash**, in-flight sentinel). ~5 s and ~9 s.

| | Litolff Beethoven 5 pp.1-4 | Breitkopf Brahms 1 pp.0-3 |
|---|--:|--:|
| pitched notes in the file | 1,618 | 2,513 |
| **`<accidental>` before → after** | **221 → 0** | **489 → 0** |
| **`<alter>` before → after** | **0 → 221** | **0 → 489** |
| `<note>` / `<rest` | 2460 / 842 — unchanged | 3612 / 1099 — unchanged |
| `<slur` / `<tied` | 80 / 179 — unchanged | 490 / 700 — unchanged |
| printed accidental glyphs detected | 256 | 733 |
| …read into a verdict | **0** | **0** |

The transfer is exact and conserved in both.

### Controls, and what each would have caught

| control | result | what it catches |
|---|---|---|
| byte-identical outside `<alter>`/`<accidental>` | **holds, both documents** | any collateral change |
| …POSITIVE control (files *do* differ unstripped) | holds | a vacuous strip |
| music21: letter+octave sequence | identical | a note re-lettered/added/dropped |
| music21 absolute check on AFTER | **221 / 489 altered, 0 wrong letter, 0 wrong direction** | the wrong SIGN, which every count above would pass |
| …POSITIVE control (population non-empty) | holds | a probe comparing nothing |
| accounting control (`Unbalanced`, an EQUALITY) | holds | notes written vs accounted |
| all seven derived checks | exit **0** | — |

⚠️ **The strip failed nothing and was never widened.**

---

## 6. Three faults in this session's own instruments

1. **The renderer probe measured itself.** Its first version scraped Verovio
   glyphs with a regex matching nothing, and reported "no accidental drawn" and
   "no flags" for **every** arm — a clean, symmetric, empty result that reads
   exactly like a real negative. Verovio names glyphs by SMuFL **codepoint**.
   Every extractor now has a **positive control** (`_require`) that raises
   unless it can see a glyph known to be on the page.
2. **The read-back judged every note against the part's FIRST key signature**
   and reported **19 false faults**. The exporter writes a key per *staff-run*
   and **5 of 12 parts carry more than one** (part 8 goes `-3` then `+1`). A
   key is a fact about a RANGE OF BARS; the probe now tracks the key in force.
3. **The music21 delta check went DEAD and its own positive control said so.**
   Without the "no note moved implies FAIL" clause it would have printed *all
   checks pass* for a probe that compared nothing.

---

## 7. The mutation battery

**13 arms, 13 red, 0 survived, 0 bad anchors.** Judge = pytest's **exit code
plus the set of failing test ids** — never the summary line, which ends
`" in 0.57s"` and differs between two runs of an unmutated tree. A green
baseline is required before arm 1. Byte snapshot on disk, restore verified by
hash, in-flight sentinel. `PYTHONDONTWRITEBYTECODE=1` on every child.

The **positive control** goes red via *different* tests than every arm, which
is what shows the suite reacts to specific behaviour rather than to "the file
changed".

⚠️ **Its first run reported 2 survivors and 1 bad anchor. One was a real test
gap; two were the battery's own faults**:

- **`stacking-guard-removed` SURVIVED — a genuine gap, and the sharpest lesson
  here.** The test used `Eb4`+`b` and `F#4`+`#`, and the rule **replaces** the
  accidental rather than appending — so where the alteration *matches* what is
  there, guarded and unguarded agree. **Both cases were equivalent mutants: the
  test named the hazard and its inputs could not reach it.** The discriminating
  case is a MISMATCH (`F#4`+`b` becomes `Fb4` unguarded, a whole tone below the
  printed note). Added.
- `false-doc-claim-restored` replaced the opening line of a *continued* string
  literal — a SyntaxError, which collects as an error, so the arm read "red,
  wrong test, got `[]`". A mutation that cannot import is not a mutation of the
  behaviour.
- The positive control anchored on a line in the **legacy**
  `tools/omr/export.py` — 0 occurrences, reported as a bad anchor. The battery
  catching its own control is the mechanism working.

---

## 8. Documentation the tree contradicts

⚠️⚠️ **`export.NOT_NOTATION["accidental"]` read "consumed into `pitch` and
`accidental`" and BOTH halves were false.** `restate_pitch` derives the pitch
from POSITION + CLEF and never looks at an accidental glyph, and
`Q.ACCIDENTAL` comes from the KEY. **The tree said so in the other direction
all along**: `gather_coverage.FAMILY_Q_IS_ELSEWHERE["accidental"]` states the
in-bar accidental *"is still filed only as an anonymous `Q.GLYPH_BOX`"*. Two
documents in one tree contradicted each other for as long as both existed, and
the false one sat in the file a reader of this path opens. Corrected and pinned.

⚠️ **`docs/symbol-dossiers/INDEX.md` — the brief's cited source — is not in
this tree**, and finding that out cost a detour. It is reachable read-only from
commit `08f860f1` (`claude/symbol-dossiers-2026-09-20`), which is not an
ancestor of `28749347`; it is also carried by
`origin/claude/integration-2026-09-18`. The manager traced the cause
independently: that branch and this lane's base **DIVERGED at `b600964e` on
2026-09-20** (27 commits against 18), while the 2026-09-21 RESUME-HERE doc
claims its branch is "integration-2026-09-18 PLUS TWO THINGS". *The tree
outranks the ledger*, again. Both figures the index supplies were checked
against the tree here and reproduce exactly.

---

## 9. WHAT IS NOT ESTABLISHED

- **The printed accidental is still unread.** 256 glyphs on Litolff and 733 on
  Breitkopf reach no quantity. A note carrying an inline accidental that
  contradicts the key still exports with the key's alteration — wrong, and
  wrong *before* this change too. Reading it is a GATHER change, outside this
  lane. It is **counted** in `coverage()["accidental_reading"]`, not guessed.
- **No print was consulted.** The alterations are checked against the key
  signature *our own pipeline read*, not against the page. CLAUDE.md already
  records key signatures right on 44 of 75 staff-systems.
- **5 of 12 parts carry disagreeing key signatures** — a real fault this
  measurement surfaced and did not fix.
- **No OMR-NED figure**, deliberately: the metric is symmetric and pairs by
  pitch.
- n = 2 documents, 2 publishers, 7 pages, both SCANS. **The engraved family is
  untouched and unmeasured.**
- The legacy exporter is **byte-identical** (`tools/omr/export.py` is not
  modified), asserted by diff rather than assumed.
