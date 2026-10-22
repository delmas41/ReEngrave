# Handoff — the staged pipeline exports, gathers, and answers "which decision"

⚠️ **READ THIS FIRST.** It replaces
[docs/handoff-2026-09-09-staged-accounting.md](handoff-2026-09-09-staged-accounting.md)
as the entry point. That file's §1 redirect is still the governing instruction
and is untouched; its §4 tasks are **done**, and **five of its claims are
corrected** (§6 below).

Everything here is on `claude/reengraved-staged-pipeline-068163`,
`b2494cbc..9dec5cb6`, 18 commits, pushed and verified against the remote.
**Suite 3,259 passed, 11 skipped, 0 failed.** `inventory --check` and
`health --check` both exit 0.

---

## 1. THE REDIRECT STILL STANDS

Sean, 2026-09-08: *"the numbers … dont feel like they have represented much
that has been helpful … I just want to get everything accounted for and figure
out our system."* **No benchmark was run as a goal this session.** Every number
below is a control or a diagnosis, never a score.

And Sean's own summary of what the work IS, 2026-09-09:

> *"adding more labels to things we didn't have labels for and explaining more
> detail in what we don't know"*

That is right, with one addition: it is **not only** accounting. Rests now
reach the file, 187 more pitches are decided, and two things that were
straightforwardly **wrong** were caught because the pipeline was made to say
what it did with each piece of ink.

---

## 2. WHAT THE STAGED PIPELINE CAN DO NOW THAT IT COULD NOT

```bash
python3 -m tools.omr.staged <pdf> --pages 2 --weights <...> --musicxml out.musicxml
python3 -m tools.omr.staged.inventory --check      # the 21 decisions, derived
python3 -m tools.omr.staged.health --check         # decides / abstains / records
python3 -m tools.omr.staged.export run.json --coverage cov.json
python3 benchmarks/omr-staged-beam-mix-2026-09/probe_beam_mix.py run.json
```

* **It produces a file.** `tools/omr/staged/export.py`, wired as `--musicxml`.
  Four real conductor's pages export and parse under music21.
* **It gathers five families it used to drop**: rests, arcs, wedges, dynamic
  letters, articulation marks. `Q.REST` is new.
* **Rests go end to end** — gathered, adjudicated, exported, with the
  bar-length convention as a CONSEQUENCE.
* **It says which decision held a note back**, per note, with a reason.

Findings, one directory each:
`benchmarks/omr-staged-inventory-2026-09/` (inventory + health),
`omr-staged-export-2026-09/`, `omr-staged-gather-2026-09/`,
`omr-staged-clef-position-2026-09/`, `omr-staged-meter-2026-09/`,
`omr-staged-beam-mix-2026-09/`.

## 3. THE MEASURED STATE OF TWO REAL PAGES

Beethoven 5 / Litolff `984073` `--pages 2` (11+11 staves) and Brahms 1 /
Breitkopf `317803` `--pages 1` (14+13).

| | beet5 p2 | brahms p2 |
|---|--:|--:|
| notes written | 516 → **527** | 664 → **707** |
| rests written | 0 → **209 + 19** | 0 → **338 + 11** |
| clef decided | 20 → **21** of 22 | 23 → **27 of 27** |
| pitches decided | 835 → **881** | 1,329 → **1,470** |
| `no_pitch` held back | 67 → **54** | 75 → **0** |
| bars padded because we read NOTHING | 148 → **47** | 60 → **1** |
| detected glyphs the record cannot carry | 761 → **533** | 1,270 → **920** |

Both files balance (every notehead and rest is written or counted) and both
parse under music21.

## 4. ⚠️ THE FOUR FINDINGS WORTH CARRYING

**(a) Rests had NO QUANTITY, which is worse than a stub.** 838 detected over
four pages, reaching `glyph_box` and nothing else — and unlike the four starved
stubs, *nothing anywhere declared the absence*. A stub at least abstains
`not_implemented` 2,728 times a page.

**(b) A staff's clef detections are ONE correlated group.** Every `CLEF_GLYPH`
row on a staff shares a reader, a frame and a quantity, so `tally` counts the
group once and takes its strongest term — a 1.5 added beside a 3.0 is 3.0.
**No refinement of the detector's own evidence can break a clef contest; a
tie-breaker must come from another reader.** That is the correlation rule
working as designed and it is invisible until you try.

**(c) "Two spurious readings that happen to agree are unanimous among
themselves."** `adjudicate_meter` divided its agreement share by the staves
that SPOKE, so 3 staves of 11 shipped a 4/4 at share 1.0 on a page that prints
no meter. The legacy reader states this in its own docstring and requires half
the page's staves as well; the staged vote had dropped that half.

**(d) A derived check beats a hand list, and it proved it twice.**
`coverage()` derives what no family claims and found `arpeggiato` firing ~90×
a page at median 56×388 px and confidence 0.39 — a stem or barline misread,
which nobody was looking for. `inventory --check` evicted ten now-stale
`KNOWN_GAPS` entries by itself.

## 5. ⚠️⚠️ THREE OF MY OWN INFERENCES WERE WRONG, ALL CAUGHT BY LOOKING

Recorded because each was one step from being reported as a result.

1. **"The written-range test is the fix for an abstaining clef."** It needs the
   INSTRUMENT, which abstains on 22 of 22 and 27 of 27 staves of these pages.
   It would have fired **zero** times. `KNOWN_GAPS` now says so.
2. **"The staff-line erasure is destroying the beam rung"** — 98 strokes on the
   erased images against **609** on the originals, and `reader_declined` on 230
   of 247 black noteheads read as plain quarters. **Rendering ONE CELL killed
   it**: the five "beams" were the five staff lines. Measured, **557 of 609
   (91%) sit within a third of a space of a staff line** and exactly **one cell
   in 341** loses a real off-line stroke.
3. **"The durations are systematically doubled"** — bar sums peaked at 4.0
   against a true 2.0. **The sum counted every chord member separately.**
   Grouped, 2.0 is a strong mode (81) beside 4.0 (94), and **83 of those 94 are
   a lone whole rest valued at 4.0**.

**The rule this session earns: a number large enough to be convincing is not
evidence about its own cause.** All three were settled by looking at ink or at
one image, none by more counting. Sean read the crop independently and reported
*"a treble clef, 3 flats and a whole note rest"* — the finding, from the print,
in one line.

## 6. ⚠️ FIVE CLAIMS OF THE PREVIOUS HANDOFF, CORRECTED

1. *"There is no exporter"* — closed for MusicXML.
2. *"`tuplet_ratio` produced no row — page or wiring?"* — **the page**, with a
   positive control (`984073 --pages 2` reads 1 marker, decides 1 ratio).
3. *"Beethoven 5 / Litolff p.2 (`--pages 1` of `984073`) is two systems"* —
   **it is one**; `works.json` says the two-system page is `pdf_page_index` 2.
4. *"153 tests"* — **226** at `b2494cbc` (322 staged tests now).
5. *"Everything else is a stub that can be filled incrementally"* — was true of
   **one** of the six; five were starved of input one stage earlier. **All five
   are now fed.**

⚠️ And §7's *"suite 3,081 passed"* was already stale: two
`test_works_json_staff_lineup.py` tests failed on a clean archive of
`b2494cbc`. Fixed in `62eb59cd` by transcribing four `lines: 1` flags the row's
own hand-verified note names verbatim.

## 7. THE NEXT THREE, RANKED

### 1. THE METER CARRY — the biggest single unlock, and it is measured

A meter is a fact of the **MOVEMENT**, printed at its start and nowhere else.
Beethoven p2 prints none. **Measured directly: pages 0–2 in ONE call read the
true `2/4` on page 1 from 12 of 12 staves, and page 2's systems still see
nothing** — the right answer is in the same log, one page earlier, and nothing
looks for it. `transcribe` carries it (`source="carried_from_previous_page"`);
the staged pipeline has no carry at all.

What it unlocks: **83 lone whole rests sized 4.0 instead of 2.0** on that page
alone; `size_measure_rest` can fire; the bar sum gets a target (it has none on
~50% of bars today).

⚠️ **Two design hazards, both already paid for elsewhere.**
* **Carrying a WRONG meter propagates it.** That is why the coverage floor had
  to land first — it did (`9dec5cb6`), so a 3-of-11 misread can no longer be
  the thing that carries.
* **A carry needs to know where a MOVEMENT starts.** Carrying across a movement
  boundary is worse than not carrying. The scan gate transcribes ONE PAGE PER
  ROW, which CLAUDE.md warns silently disables every page-spanning mechanism —
  so this must be measured on a multi-page run, never on the gate.

### 2. THE ARC ADJUDICATORS — the biggest unrepresented mass

`arc_kind` (tie vs slur) and `arc_owner` (which staff, and pairing across the
barline). **843 arcs over the two pages**, gathered since `c54bb345` and now
one piece of work each rather than two.

Positions already paid for, to carry rather than rediscover: pairing runs over
the **STAFF** in page pixels, not the cell, because a barline cuts every arc in
two (120 arcs against 82 truth slurs on one fixture); the three constants each
sit on a measured plateau; the arc is **narrower** than the run it binds, so
the box is padded by a notehead width; `OMR_ARC_ATTRIBUTION` gives an arc to
the staff whose noteheads it hugs; and the tie/slur grammar veto was measured
on both families and **refused** on scans (+130 edits) — do not re-try it.

### 3. THE DYNAMICS ADJUDICATOR — 489 letters, and a measured placement band

`f`+`f` → `ff` by x-adjacency, then placement. The band is measured over 1,246
letters on 18 pages of 9 publishers: 73% stand in their own staff's band, 24%
in the band of the staff **immediately above** — distance exactly 1, no
exceptions.

⚠️ **A GATE IS THE WRONG FIX** and this is written down: an out-of-band letter
is usually the neighbour's ink, and 83% of re-attributed letters are the target
staff's SOLE evidence. It belongs in ownership as another evidence tier.
⚠️ And on SCANS we **under**-emit (376 words against 491), so the dominant scan
error is a mark never found, not one on the wrong staff.

### Also on the list, smaller or blocked

* **`fermata` (35) and `ornament` (6) still have NO QUANTITY** — the last two
  families in that state. Cheap; completes the accounting.
* **Brahms p2 reads `9/4` where the truth is `9/8`** — the denominator digit,
  at a winning NCC of 0.42–0.53 with `9/8` not even the runner-up although it
  IS a candidate. ⚠️ A digit-template question, and the standing rule is that
  this family is **never tuned on one edition**.
* **One Beethoven staff (54 notes) where nothing read a clef at all** —
  `no_candidates`, not a tie. Neither geometry nor identity reaches it.
* **`duration_narrowed` (392 over two pages)** is mostly the honest
  outer-note-of-a-beam-group case, and the beam thread above is largely dead.
  Do not open it expecting a bug.
* **A LilyPond exporter** — deliberately not built; it would need rules for
  facts the record cannot yet express.

## 8. OPERATIONAL

* `OMR_SURYA_KEEP_ALIVE=0` for unattended runs; **never `pkill` the shared
  daemon**.
* The staged pipeline needs **only the weights** — none of the four venv
  symlinks. A worktree also needs a `library` symlink for the PDFs; ⚠️ it is
  now correctly gitignored (`/library`, no trailing slash — the old pattern
  matched a directory and not a symlink, and one got committed).
* `| tail` eats git exit codes — verify a push by re-reading the remote ref.
* The full suite takes ~8:40 and sits a long while around 64% in
  `test_roster.py`. That is normal.
