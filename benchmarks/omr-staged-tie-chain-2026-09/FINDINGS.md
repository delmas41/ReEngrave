# The tie CHAIN — an argued negative, and two defects found on the way

2026-09-10/11. Phase 1 **item 5** of
[docs/plan-2026-09-10-wire-first-then-reconcile.md](../../docs/plan-2026-09-10-wire-first-then-reconcile.md).

⚠️⚠️ **THIS ITEM RUNS THE OPPOSITE DIRECTION FROM EVERY OTHER ONE AND THAT IS
WHY IT ENDS DIFFERENTLY.** Every other wiring item is *the record knows
something and no file carries it*. Here **the exporter already does the job
and the record cannot name it** — `staged/export.py` has set
`tied_to_next` / `tied_from_prev` from `_pair_arcs` since the arc-export
landing, and those two are the last two entries in
`gather_coverage.NO_VOCABULARY`.

**They stay there. No `Q.TIE_LINK` was built, deliberately**, and §3 is the
argument. What shipped instead is that the exporter now *says what it did*,
and two real defects found while measuring it.

---

## 1. REACH FIRST

⚠️ *A change that moves nothing because it is inert and one that moves nothing
because the page holds nothing to move are the same number.* So the population
comes before every other figure here.

Measured by `tie_chain_arm.py`, which calls `_flatten_part`, `_arcs_by_kind`
and `tools.omr.export._paired_spans` — **the same functions
`staged.export._pair_arcs` calls** — so a reach figure cannot drift from what
the exporter does.

Both documents gathered **fresh** for this work with the production scan
weights (`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04`): Litolff
`--pages 1-3`, Brahms `--pages 0-3`. ⚠️ `provenance.dirty` is `true` on both,
because the arms ran from an edited tree; that forbids comparing two RECORDS
and nothing here does — every arm is one record read or exported twice.

⚠️ **A side observation, recorded and NOT relied on:** the same probe run
against a *previous* session's Brahms record (`46c3ac00`, before `Q.VOICES`)
reproduces every reach figure below **to the unit**, while on Litolff the
pre-voices record reads **60** links against the fresh **59** — the one-voice
filter in `_paired_spans` removing exactly one there and nothing here. That is
one document each and says nothing about determinism in general.

| | Litolff Beethoven 5 `984073` p1-3 | Breitkopf Brahms 1 `317803` p0-3 |
|---|--:|--:|
| arc boxes detected | 514 | 2207 |
| …classed **tie** by `Q.ARC_KIND` | **270** | **1658** |
| tie groups after the cross-barline merge | 261 | 1227 |
| …merged from two detected halves | 31 | 329 |
| **tie LINKS** (a bound pair) | **59** | **632** |
| **tie CHAINS** | **46** | **275** |
| …longer than two notes | **4** | **82** |
| links crossing a **barline** | **10** | **140** |
| links crossing a **system break** | **0** | **2** |
| chain length in notes | 2 ×42, 3 ×3, 4 ×1 | 2 ×193, 3 ×52, 4 ×19, 5 ×9, 9 ×2 |
| tie ends landing in a chord | 80 | 776 |
| …on a chord member that is **not** the lowest | **42** | **436** |

⚠️ **The dominant number is a READING shortfall, not a chain one.** 270 tie
arcs become 261 merged groups and only **59 links**: 362 merged arcs of both
kinds bind fewer than two noteheads and are refused, which is the 76% figure
[the arc-export findings](../omr-staged-arc-export-2026-09/FINDINGS.md) already
records as **the detector's**, arriving again from the tie side. Do not read
"59 links" as a recovery rate.

⚠️ **A chain is not a link and the two differ by one per chain.** Quoting
links as "ties" over-counts every chain of three or more — 4 of 46 chains on
Litolff and **82 of 275** on Brahms, which is not a rounding error on the
second document.

⚠️ **Litolff alone would have made the system-break case look impossible** —
it has **zero** — and Brahms has **two**. The same shape as `wedge_anchor`'s
zero reach on Litolff, one family over, and the reason both documents were
gathered rather than one.

⚠️ **THE SECOND DOCUMENT CHANGES THE SHAPE OF THE CHAIN, NOT JUST ITS SIZE.**
Litolff's longest chain is 4 notes and 4 of 46 chains exceed two; Brahms runs
to **nine** and **82 of 275** exceed two. A rule or a report calibrated on
Litolff's histogram would have been calibrated on a document where the chain
is almost always a pair.

**What the exporter WROTE, beside that reach** (`written`, both documents):

| | Litolff p1-3 | Brahms p0-3 |
|---|--:|--:|
| `ties` (`<tie type="start">` written) | 48 | 349 |
| `tie_links_marked` | 59 | 632 |
| `slurs` / `slur_spans_marked` | 23 / 55 | 227 / 272 |
| `arc_binds_fewer_than_two_notes` | 362 | 762 |
| `arc_ends_in_one_chord` | 43 | 328 |
| notes / rests | 1075 / 443 | 2687 / 989 |

---

## 2. WHAT SHIPPED

No flag. `staged/export.py` and `staged/gather_coverage.py` only.

### 2a. The chain is COUNTED, where the marks are made

`_pair_arcs`'s tie branch now fills `tie_links_marked`,
`tie_links_crossing_a_barline`, `tie_links_crossing_a_system_break`,
`tie_chains_marked` and `tie_chains_over_two_notes`.

`_chain_sizes` is **union-find over shared ends**, and that is not fussiness:
⚠️ **the first cut of the reach probe keyed the closure on a `start -> stop`
dict, which loses a head that begins two links** — a chord member tied onward
while the head beside it starts another — and it read `{2: 50}` on a page whose
chains run to four notes. A plausible histogram is not evidence that its parts
are real; the tell was that **not one chain exceeded two notes** on a document
that plainly holds longer ones.

### 2b. ⚠️⚠️ `tie` AND `slur` WERE REPORTING EACH OTHER'S VERDICTS AS THEIR OWN

`FAMILIES` maps **both** families to `Q.ARC_KIND`, and `coverage()` counted
every decided verdict of that quantity **for each**. On Litolff p1-3 both rows
read:

```
{'family': 'slur', 'detector_glyphs': 244, 'decided': 514, 'written': 23}
{'family': 'tie',  'detector_glyphs': 270, 'decided': 514, 'written': 49}
```

**514 is 270 + 244**, stated twice — and `detector_glyphs`, one column to the
left, had the split right all along. A reader comparing `decided 514` with
`written 49` would conclude the exporter drops 465 ties. After:

```
{'family': 'slur', 'detector_glyphs': 244, 'decided': 244, 'written': 23}
{'family': 'tie',  'detector_glyphs': 270, 'decided': 270, 'written': 48}
```

⚠️ **The split is DERIVED from `FAMILIES` itself** — a quantity claimed by more
than one family is attributed by VALUE, and the family names *are* the values
`adjudicate_arc_kind` returns. A fourth hand-written column would be one more
thing to keep in step, and this repo's history says hand lists rot. The
partition is **asserted**, not hoped for.

⚠️ **An abstention on a shared quantity names no family.** `arc_kind` abstains
`no_arc_box` precisely when it could not say which kind, so filing it under
`tie` and again under `slur` is the same double count one row up. It is
reported ONCE, at the top of the report, as `abstained_without_a_family`, and
the row carries `abstentions_name_no_family: true` so `abstained: {}` cannot be
misread as *none*.

### 2c. ⚠️⚠️ A TIE ON A CHORD CAN LAND ON A NOTE THAT CARRIES NO TIE

The brief asked whether the fermata work's *"the hoist reads only the chord's
FIRST head"* shape is present here. **It is present in the mirror image, and it
is worse.** The fermata bug LOST a mark; this one puts a mark on the **wrong
note**.

* `<slur>` carries a `number=` and hangs off the chord's representative
  `<note>`. `<tied>` carries **none** and joins *the two notes it names* —
  `_pair_arcs` says exactly this in its own docstring: *"the one place a tie
  and a slur are genuinely different spanners rather than the same one under
  two names."*
* `voicing.group_chords_in_measure` hoists the flag onto the EVENT with
  `any()`; the renderer writes it at `n == 0`. So a chord whose **upper**
  member is tied gets `<tie>` on its **lowest** note — a tie between two
  different pitches.

**MEASURED, on both documents:**

| | Litolff p1-3 | Brahms p0-3 |
|---|--:|--:|
| `<tie type="start">` written | 48 | 349 |
| …**onto a note that carries no tie** | **17** | **103** |
| `<tie type="stop">` …the same | **15** | **101** |
| share of written ties on the wrong note | **35%** | **29%** |

Under-emission — a chord with two genuinely tied members getting one
`<tied>` — is the **smaller** half at 1 event on Litolff, so the failure is
overwhelmingly *wrong note*, not *missing note*. ⚠️ **Two publishers, two
documents, and the rate agrees to within six points**, which is the first
thing this repo asks of a defect measured on one page.

⚠️ **NOT FIXED, DELIBERATELY, AND THE REASON IS A CONSTRAINT NOT A PREFERENCE.**
The hoist is in `voicing.py`, shared with the LEGACY exporter and therefore
with the 11-work engraved benchmark; the repair moves hundreds of elements on a
scan, far more than can be adjudicated against the print in one pass. **A
wiring pass may connect a decision; it may not change behaviour it has not
priced.** It is counted so the size of it appears on every run instead of in
one probe.

⚠️ **The previous session already flagged the question and declined it for a
different reason** — `test_a_TIE_on_a_chord_also_marks_one_note` says first-note
is *"the LEGACY position, MATCHED rather than RE-DECIDED"*, because a staged
exporter disagreeing with the legacy one would export the same record two ways.
That argument stands. What is new is the **price**.

---

## 3. ⚠️⚠️ WHY THERE IS NO `Q.TIE_LINK` — the argued negative

The bar set for this job: *the quantity must be READ by something, or you must
declare in writing why it cannot be.* Here is the declaration.

**A tie chain is a fact about a PART.** 10 of 59 links cross a barline on
Litolff and 140 of 632 on Brahms; **2 cross a system break**. Merging the
detected halves is what makes them one tie, and the merge runs along a part —
`to_musicxml` says so at its call site: *"A part is what an arc is merged
along — the junction between two systems is a junction of one PART."*

**The part is built in EXPORT, and EXPORT cannot contribute a record row.**
`staged/export.build` turns `Q.PART_PARTITION` into `StaffRun`s, and
`staged/__main__.py` **writes the record JSON before the exporter is imported
at all** (`json.dumps(result)` at :140, `from . import export` at :148).
Anything the exporter decided could never reach the file that the record is.

**Three routes were considered and each is refused for a stated reason:**

| route | why not |
|---|---|
| an EVALUATE consequence at `Kind.DOCUMENT` (like `join_parts`) | needs the part structure, i.e. `export.build` — EVALUATE would depend on EXPORT, backwards. And `_paired_spans` prefers the first head's VOICE over dropping the span, which is choosing between two viable readings: ⚠️ the plan's own testable boundary is *no EVALUATE consequence may contain a tie-break.* Neither `Q.ARC_KIND` nor any arc quantity is in `DOWNHILL` either. |
| a per-arc decision at `Kind.GLYPH`, like `arc_kind` | ⚠️ **it would add nothing.** `adjudicate_arc_kind` already computes the flanked head pair *within one cell* and records `flanked_heads` / `first_step` / `last_step` in `detail["grammar"]`. Within a cell the pair is already recoverable; **the cross-cell chain is the only thing missing**, and that is precisely what a per-arc decision cannot see. |
| a `Kind.STAFF` decision over one staff run | reaches **630 of 632** links (the 2 system-break crossings are out of scope by construction) — but it would be a **SECOND pairing that can disagree with the exporter's**, with the FILE following the exporter. Two copies of a number this project paid to measure once is the drift `LETTER_METERS` and the arc constants are imported to prevent. |

**And the shape that would have made it non-decorative — the exporter reading
the record's links instead of computing its own — requires extracting
`build` / `StaffRun` / `_flatten_part` / `_arcs_by_kind` out of `export.py`
into a module both EXPORT and the pipeline can import.** That is the right
refactor and it is **not a wiring pass**: ~250 lines moved out of a file a
parallel session was editing the same night.

⚠️ **A quantity that no decision and no export reads would have made
`gather_coverage` report green while changing nothing** — `NO_VOCABULARY`
2 → 0 for free. CLAUDE.md already names that anti-pattern under *"A `wants`
entry the decision never reads is INERT"*. **The honest gap is worth more than
the green line**, and the `NO_VOCABULARY` entry now carries the measured
boundary so the next session starts from it rather than from the question.

---

## 4. CONTROLS

**The exported file did not move, on EITHER document.** One gather, exported
twice — this `export.py` against `origin/main`'s, everything else identical:

```
Litolff p1-3   BYTE-IDENTICAL   md5 3f9bb446abf3a88ef67685ff1beda849   17,448 lines
Brahms  p0-3   BYTE-IDENTICAL   md5 e10efe1da771ed023dd5a01bdb614d23   41,269 lines
```

⚠️ Brahms is the arm that matters for the merge, because it is the only one of
the two that exercises a **system-break** crossing (2 links); Litolff has none.

⚠️ **A byte-identical file is exactly the result that hid a bug in a sibling
session**, so the positive control is stated beside it: on both documents the
two **coverage reports differ**, and on Litolff they differ exactly where
intended (`decided` 514/514 → **270/244**; `abstained_without_a_family` absent
→ `{}`). Both arms genuinely ran. On Brahms the same split reads
**1658/549** where both rows previously read 2207.

**Mutation battery: 8 arms, ALL RED** (`probe/battery.sh`). ⚠️ *One red arm is
not a battery*; and a battery of refusal arms can pass by refusing everything,
so `wrong-note-never` is the positive control in the same class — break the
case that must NOT be counted and the suite still goes red.

⚠️ **A NINTH ARM SURVIVED AND IT WAS RIGHT TO.** An
`if quantity not in unattributed:` guard in front of an **assignment** cannot
change the outcome — an equivalent mutant, i.e. a check that cannot fail. The
guard was **deleted** rather than tested around: making the double count
unrepresentable beats checking for it. (Same call as
`METER_FROM_BARS_MIN_ASSESSABLE`, deleted for the same reason.)

**21 new tests; 16 RED against `origin/main`.** The 5 that pass there are the
absence-asserting controls, which is their job — each is paired with a
same-class arm that goes red.

Full suite **3,682 passed / 11 skipped** (baseline 3,661 / 11).
`health --check`, `inventory --check`, `gather_coverage` all exit 0;
`status_census.unaccounted` empty and the note balance holds on both documents.

---

## 5. WHAT IS **NOT** ESTABLISHED

* **Nothing about reading quality.** Not one tie was hand-checked against the
  print. `tie_links_marked` counts what the exporter bound, not what the page
  prints — and 362 merged arcs bind fewer than two notes on Litolff alone, so
  the tie inventory is known to be short by an unmeasured amount.
* **The 17 + 15 wrong-note ties are the exporter's own accounting, not a
  truth-checked figure.** A "chord" here is `group_chords_in_measure`'s, and on
  a scan two heads at one x can be a duplicate detection rather than a chord.
  The number bounds the defect above and bounds nothing below.
* **No OMR-NED figure is claimed**, on the arc-export session's reasoning: the
  metric is symmetric and rewards emitting more symbols — and nothing here
  changes what is emitted anyway.
* **`provenance.dirty` is `true` on both records** because the arms were run
  from an edited tree. That does not spoil a single-record arm — one record
  exported twice — and **no two records are compared anywhere in this file.**
* **n = 2 documents, 2 publishers, 7 pages.** Every share above is that
  corpus's.

---

## 6. REFUTED / REFUSED, so nobody re-tries them

1. **"Name the chain per arc, in ADJUDICATE."** Refused as *duplicative*, not
   merely limited: `adjudicate_arc_kind` already records the flanked head pair
   within the cell. §3.
2. **"Point `FAMILIES['tie']` at a new quantity to make it non-decorative."**
   That would make the census read the new quantity — but the census defect
   (§2b) is fixed correctly by attributing the SHARED quantity by value, which
   needs no new quantity at all. Inventing one to give it a reader is the
   decorative outcome wearing a consumer.
3. **A `start -> stop` dict for the chain closure.** Loses a head that begins
   two links, and reports every chain as a pair. §2a.
4. **Guarding the shared-quantity abstention write with `if not in`.** An
   equivalent mutant in front of an assignment. §4.

---

## 7. WHAT A NEXT SESSION SHOULD DO, ranked

1. **Price the chord tie.** `_note_xml` can write `<tied>` per tied HEAD in
   four lines — the staged renderer already does exactly that for
   articulations and ornaments, and `_mxl_note` takes the flag per note. What
   is missing is the adjudication: the moved elements must be looked at against
   the print, and the legacy side must be priced on the engraved 11-work
   benchmark too, because the hoist is shared. **Brahms is the document**:
   103 + 101 wrong-note ties against Litolff's 17 + 15.
2. **Extract the part structure out of `export.py`.** `build`, `StaffRun`,
   `_flatten_part`, `_arcs_by_kind` into a module the pipeline can import. That
   single refactor unblocks `Q.TIE_LINK`, and it is the same thing every other
   part-level fact will need.
3. ⚠️ **A tie is the one place the pitch reading checks itself** —
   `record.Checkable`'s own docstring: *"A tie's two ends must be the same
   pitch, so C vs C# IS checkable at a tie and nowhere else."* 59 links on
   Litolff and 632 on Brahms is a real population for a **no-truth-file**
   check, on a corpus where `wrong note` is 26% of scan edits. It needs
   `Q.TIE_LINK` (item 2), and it is the strongest argument for building it.
