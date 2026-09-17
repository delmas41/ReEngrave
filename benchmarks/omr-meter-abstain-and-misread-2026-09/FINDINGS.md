# The document that ABSTAINS *and* MISREADS — it is already in the corpus

2026-09-16, no code outside `benchmarks/`. The 2026-09-16 pricing arm ended by
naming what `OMR_METER_CARRY` has been waiting for: *"a document that ABSTAINS
**and** MISREADS. Litolff Beethoven 5 abstains on 6 of 7 systems but its one
read meter is CORRECT, so the carry is never handed a wrong candidate.
Breitkopf Brahms 1 misreads badly but abstains nowhere, so the carry never
runs. The two halves of the hazard have never been present in one document."*

**They have. It is `p0p3` — Breitkopf Brahms 1 mvt 1 — and it has been in
`benchmarks/*/out/*.meter.json` the whole time, stable in 11 of 11 arms across
5 generations.**

Run it: `python3 probe/find_fixture.py` (committed output in
`out/find_fixture.txt`); battery `python3 probe/mutate.py`.

## 1 · Reach first, and the generation is named

**105 committed meter records, 28 fixtures, 4 benchmark directories,
generations 1 / 2 / 3 / 4 / 5 / 7.** Nothing was gathered — a cloud container
has no weights and no `library/`, so this probe can only ask whether a fixture
already run holds both halves. **A negative here would have been a statement
about the committed corpus, never about the repertoire.**

⚠️ `out/` holds several generations of the same fixtures and the cautionary +
meter-in-force fixes landed BETWEEN them. Pooling them as repeat runs of one
tree is the error `omr-meter-corroboration-2026-09` records costing a session
its reach figures, so every row NAMES its generation and the default is the
NEWEST per (fixture, arm). Here it does not matter — see §3 — and that is a
result rather than an excuse.

**9 of 28 fixtures carry a hand-read OPENING truth; the other 19 ABSTAIN and
are reported.** An unknown truth is never converted into a definite answer.

## 2 · The answer

| bucket | fixtures |
|---|---|
| **ABSTAINS *and* MISREADS** | **`p0p3`**, `brahms1scan` |
| abstains only | `brahms1eng`, `brahms4eng`, `e209A`, `e209B`, `e209C`, `p012` |
| misreads only | `lit6162` |
| neither | none |

⚠️ **`p012` landing in *abstains only* is the positive control on the truth
table**: that is Litolff Beethoven 5 pp.0-2, and the probe independently
reproduces CLAUDE.md's characterisation of it — abstains, reads its one meter
right. Had the table been wrong, that row is where it would have shown.

## 3 · `p0p3`: the misread is stable and the abstention is real

Brahms 1 mvt 1 is **6/8 = 3.0 quarter notes**, one bar of 9/8 at m8, then 6/8 —
read off the committed dossier (`data/dossiers/brahms-sym1-mvt1.json`,
`starting_meter {6,8}`, 513 bars), not from memory. So a `C` reading is 4.0
against a truth of 3.0: **a LENGTH misread, the kind bar sums can arbitrate.**

    m2p0p3-BARS    system/0/0=C(voted) | system/3/0=ABSTAIN(bars_name_a_length_without_a_form)
    m2p0p3-CARRY   system/0/0=C(voted) | system/3/0=ABSTAIN(carry_outweighed_by_the_bars)
    m3p0p3-BARS    …  m3p0p3-BOTH  …  m3p0p3-CARRY  …
    m7p0p3-BARS    system/0/0=C(voted) | system/3/0=ABSTAIN(bars_name_a_length_without_a_form)
    m7p0p3-BOTH    …
    m7p0p3-CARRY   system/0/0=C(voted) | system/3/0=ABSTAIN(carry_outweighed_by_the_bars)
    p0p3-OFF       system/0/0=C(voted) | system/3/0=ABSTAIN(no_evidence)

**`system/0/0` reads `C` at `voted` in 11 of 11 arms and 5 generations.
`system/3/0` abstains in 11 of 11.** Both halves, one document, every tree.

## 4 · ⚠️⚠️ AND THE NEWEST GENERATION IS THE *DISCRIMINATING* CASE — the bars name the truth

The recorded objection to leaning on bar sums is that the Litolff *Andante*
refusal is **safe but not discriminating**: it refuses the CORRECT meter too,
because a noisy page refuses everything. **That is not what happens here.**
`m7p0p3-CARRY`, `system/3/0`:

    carried_from      system/0/0        <- the system that misread `C`
    support           -8.0   (floor 2.0)
    bars_agree        0
    bars_disagree     9
    bar_lengths_seen  {3.0: 8, 5.0: 1}

**The bars read 3.0 on eight of nine bars — 3.0 IS 6/8, the printed meter.**
So the misread `C` is offered to the carry and thrown out by bars that
positively name the right length. This is the first observation in the thread
of the bar arbitration doing the exact job the flag was held off for, on the
exact hazard shape, rather than falling silent.

⚠️ It does NOT price the flip. It shows the hazard is real, present, and
**refused on this fixture**; a 2-system run says nothing about a misread
propagating across a whole movement, which is what `local_arm.sh` is for.

## 5 · ⚠️⚠️ THE ACTIONABLE FINDING: the bars have the answer and cannot SPELL it

Same system, the BARS arm at the newest generation:

    m7p0p3-BARS  system/3/0  ABSTAIN  bars_name_a_length_without_a_form
                 support +7.0   bars_agree 8 / disagree 1   lens {3.0: 8, 5.0: 1}

`OMR_METER_FROM_BARS` gets **length 3.0 at +7.0 support against a floor of
4.0** — it has the right answer — and abstains anyway, because the printed FORM
is borrowed only from a preceding system whose meter was read AND whose length
already matches, and **the only candidate source is `system/0/0`, which read
`C` = 4.0.** The misread poisons the borrow.

**So on the one document that both abstains and misreads, the thing standing
between the pipeline and the correct meter is the form-borrowing rule, not the
weighing.** That rule is right to refuse — inventing `6/8` from a length is the
laundered guess its own docstring bans, and the abstention already RECORDS the
length and every spelling it could be. What the record shows is that the
recorded abstention `bars_name_a_length_without_a_form` is **not a rare
fallback here: it is the outcome on the fixture the flag has been waiting for.**
⚠️ Whether a form may be borrowed from the DOSSIER — a reader that does not
fail with the raster, which is the `source_kind` doctrine — is INFER-shaped work
and is not proposed here.

## 6 · The weaker second instance, reported apart

`brahms1scan` qualifies too and is **not** the same result: `system/1/0`
misreads `9/4` (the famous one) and `system/1/1` abstains
`carry_outweighed_by_the_bars` at support **−1.0**, `bars_disagree 2`,
`bar_lengths_seen {4.0: 2}`. Two assessable bars, reading **4.0** — neither the
truth (3.0) nor the misread (9.0). **There the bars refuse the carry without
naming anything**, which is the safe-but-not-discriminating shape. Pooling the
two would report the strong case's property of the weak one.

## 7 · ⚠️ Litolff hides a SUPPRESSED misread, and it is not scored

`p012-OFF`, `system/2/1`: abstained `too_few_staves_read_it`, coverage 0.273,
3 staves of 11 — with **`would_have_been: "C"`** on a 2/4 document. So the
abstaining document does contain a latent length misread; the coverage gate
held it back. It is REPORTED and never counted as a reading: scoring a
candidate the pipeline correctly refused to make would score the gate's
success as a failure.

## 8 · ⚠️⚠️ Three faults in this probe, and two were found by a row that was MISSING

1. **A filter that silently emptied 12 files.** Two committed reduction shapes
   exist and the second has **no `quantity` key** —
   `omr-staged-meter-carry-2026-09` and its siblings commit a bare
   `{subject, outcome, reason, value, detail}` list. Filtering on
   `quantity == "meter"` read 12 records as zero rows, **including Litolff
   `p012`, the abstaining document**. ⚠️ The tell was not the table: it was four
   truth-carrying fixtures appearing in NONE of the four buckets. *A filter
   that silently empties a file looks exactly like a file with nothing in it.*
2. **A false positive of my own making.** The first run reported `brahms1eng`
   as abstaining-and-misreading. Its `system/1/0` opens **`9/8`** — which is
   the printed one-bar 9/8, exactly as `report_boundary.TRUTH_CHANGES` records
   (`("brahms1-m1-22", 1): (1, "6/8")`, a change BACK to 6/8 at cell 1). A
   per-DOCUMENT truth cannot score a document with a real mid-document change.
   Found by opening the candidate, not by counting.
3. **A first glob that covered two thirds of the corpus** — the boundary dir
   alone, 68 of 105 records, with the Litolff records invisible.

## 9 · The battery

**5 arms, all red, positive control first, restore VERIFIED**, byte snapshot on
DISK and an in-flight sentinel (an interrupted battery refuses to restart and
names the file with the hash it should have).

⚠️ **Its first run reported 3 survivors and ALL THREE were the battery's own
faults**, which is the recorded pattern arriving again:
- the comparator read only the headline `ABSTAINS *and* MISREADS` line, so an
  arm that moves a *different* bucket read as a survivor;
- one arm **could never fire** — it mutated `C|`'s length while the fixture it
  targeted has an OPENING truth of `C` and only openings are scored. **DELETED
  rather than tested around**, and replaced by one that reaches the length
  comparison the whole finding rests on (`6/8 -> 4.0` takes the answer to NONE
  and exit 3);
- one arm was a **no-op because `{}` is FALSY**: `OPENING_TRUTH = {} or {...}`
  handed back the full dict. The exact hazard CLAUDE.md records for
  `_carry_meter`, in the instrument this time.

## 10 · What is NOT established

- **Nothing was gathered, rendered or exported.** Every figure is a property of
  committed JSON.
- **The flip is still unpriced.** §4 shows the hazard refused on a 2-system
  fixture; propagation across a movement is `local_arm.sh`'s question.
- **Which PDF pages `p0p3` names cannot be confirmed from committed data** —
  the tag is free-form and `run_arms.py` takes `--pages` on the command line.
  The finding survives that: Brahms 1 mvt 1 is 6/8 for 512 of its 513 bars, so
  the truth is 6/8 on any page of it, and the bars on `system/3/0`
  independently read 3.0.
- **No print was consulted**, and no OMR-NED figure is claimed.
- n = 2 fixtures of one document and one publisher (Breitkopf).
- The 19 truth-less fixtures are **unscored, not clean**.

---

# 2026-09-17 — ⚠️⚠️ THE CARRY'S DOMAIN ON THAT DOCUMENT IS 5 OF 7, NOT ZERO

`probe/carry_domain.py`, derived from the tree, no weights, nothing gathered.
**This section corrects a claim this thread committed to main yesterday**, on
this repo's own governing rule — *the tree outranks the ledger, including when
the ledger is mine.*

## 11 · What was claimed, and why it was wrong

The 2026-09-16 pricing-arm write-up read Breitkopf Brahms 1 p0-3's
`decided 7 of 7  {'voted': 2, 'change_only': 5}` and concluded:

> *"`_meter_fallbacks`, whose own docstring opens "Everything to try when this
> system's own READING failed", is reached only from failure paths. **Neither
> flag has a domain on this document.**"*

The premise is correct and the inference runs backwards. **`change_only` IS a
fallback rung — the THIRD of three** — so a `change_only` verdict is positive
evidence that `_meter_fallbacks` ran, and therefore that `_carry_meter` was
called *before* it. The five systems I read as *"nothing failed here"* are the
five where the reading failed and the third rung answered.

| | |
|---|---|
| rung order in `_meter_fallbacks` | `_carry_meter` → `_meter_from_bars` → `_change_only` |
| every call site of all three | inside the fallback chain — **derived, not grepped** |
| carry domain on Breitkopf p0-3 | **5 of 7 systems** |

⚠️ **THE REACHABILITY STEP IS WHY THIS IS AN AST WALK AND NOT A `grep`.**
`_change_only` has TWO call sites — one in `_meter_fallbacks` and one inside
`_meter_from_bars` — and the inference holds only because `_meter_from_bars` is
itself called from nowhere else. A grep shows two sites and says nothing about
whether the second is also downstream of the carry. The probe closes the
transitive set to a fixpoint and **refuses** if any rung becomes reachable from
outside it.

## 12 · ⚠️⚠️ AND THE SHARED RECORD IS A *BEFORE* ARM — the flags were OFF in it

`benchmarks/omr-shared-records-2026-09/` built the Breitkopf staged record three
jobs had been blocked on, and its §3 says in terms: *"this record is the arm
`OMR_METER_CARRY` has been blocked on … That cost is now measurable."* Right
about the document and **not yet true of the record**:

| | |
|---|---|
| record provenance | `e282ae0c`, orphaned by a rebase; its `tools/` tree is **identical to `da2c9c11`**, which is on main |
| `OMR_METER_CARRY` default at `da2c9c11` | **`"0"` — OFF** |
| the same default today | `"1"` — ON |
| what `_carry_meter` does with the flag off | `return None` **before reading any evidence** |

So the carry could not act anywhere in that record. Its `change_only` ×5 is the
**OFF arm, already taken** — which is better than nothing, because it is the
control an A/B needs, but it is not the measurement and must not be quoted as
one. ⚠️ The probe's **positive control is that the two defaults DIFFER**: made
to read alike, it refuses rather than concluding, because a check that cannot
tell a before-arm from an after-arm would report this document's zero as a
result either way.

⚠️ **The desktop run is consistent with both readings and cannot separate
them.** `local_arm.sh`'s ON and OFF arms came back identical in every reported
number, which is what you get whether the carry was *never asked* or *asked on
five systems and refused on all five*. It prints no per-system carry outcome, so
the instrument has no way to say which — the reporting defect §2 of the
corroboration findings already records, now with a concrete cost.

⚠️ **The census independently corroborates the document.** The probe reads
`{'voted': 2, 'change_only': 5}` out of the shared record's committed table;
the desktop arm printed the identical dict from a fresh gather on a different
tree. Two sources, one census — so the pricing arm and the shared record are the
same document and the same window, which no single artefact establishes.

## 13 · The arm that would price it — and it needs no re-gather

⚠️⚠️ **THE FLAGS ARE ADJUDICATE-STAGE, SO A 1 h 44 min RE-GATHER IS THE WRONG
INSTRUMENT.** `benchmarks/omr-rest-sizing-2026-09/rest_sizing_arm.py` already
does exactly this A/B: it rebuilds a `Log` from a **saved record's** GATHER rows
(`readjudicate.rebuild`), re-runs ADJUDICATE and EVALUATE under a named
environment, then exports — the precedent being its own recorded result, *"with
`OMR_METER_CARRY=1` all six abstaining systems decide `carried` 2/4"*. Pointed
at the shared Breitkopf record it prices the flag on a document whose candidate
is **wrong**, in minutes, with the gather held byte-identical between arms.

```
python3 benchmarks/omr-rest-sizing-2026-09/rest_sizing_arm.py \
    library/_shared-records/brahms1-breitkopf-p0-p3.record.json \
    --bar-beats 3.0 --env OMR_METER_CARRY=0
# then the same with --env OMR_METER_CARRY=1
```

⚠️ **READ THE PER-SYSTEM TABLE, NOT THE REACH HEADER.** That arm's header counts
`outcome != decided`, which is **0** on this document — so it would print
`0 abstained` and invite exactly the misreading §11 corrects. What answers the
question is the table underneath it, which prints each system's `reason` and
`support`: the carry's outcome shows up there as `carried` (it won),
`carry_outweighed_by_the_bars` (the bars refused it — the designed behaviour on
a wrong candidate), `carry_source_uncorroborated` (A-METER-6 confined it), or
`change_only` (it was asked and produced nothing).

⚠️ **`--bar-beats 3.0`.** Brahms 1 mvt 1 is 6/8. That argument was made
REQUIRED yesterday precisely because its old default of 2.0 was Litolff's 2/4
and scored this document against the wrong bar.

## 14 · What is NOT established

- **Whether the carry is refused or merely finds no source.** §11 proves it is
  ASKED five times; nothing here says what it answers. Only §13's arm does.
- **Nothing was gathered, adjudicated, exported or scored**, and no print was
  consulted. Every figure is a property of committed text and of the AST.
- **The census is read off another job's prose table**, not off the record. It
  agrees with an independent fresh gather, which is why it is usable — but the
  record itself (443.7 MB, gitignored `library/`) is not present in this
  container and was not opened.
- **`da2c9c11`'s equivalence to the record's stamped tree is that job's claim,
  not a re-derivation**: its §8 records the two `tools/` trees as one object
  (`40b68273`). The probe abstains with a named message where the commit is
  unreadable, rather than guessing.
- n = 1 document, 1 publisher, 4 pages. This says nothing about Litolff, whose
  one read meter is correct and which therefore cannot price the cost side at
  all.

---

# 2026-09-16 (session two) — §15 · THE ARM FROM §13, RUN — AND RUN AGAIN INDEPENDENTLY, BYTE-IDENTICAL, AND STILL NOT THE HAZARD CASE

`benchmarks/omr-meter-carry-breitkopf-330a74`, no weights, one saved record,
two arms, then a second session's independent repetition compared afterward.
Receipts: `out/carry-pricing-p0p3/{p0p3-0,p0p3-1}.musicxml`,
`out/carry-pricing-p0p3/arm-{off,on}.txt`, this section.

## 15.1 · §13's arm, run

```
python3 benchmarks/omr-rest-sizing-2026-09/rest_sizing_arm.py \
    library/_shared-records/brahms1-breitkopf-p0-p3.record.json \
    --bar-beats 3.0 --env OMR_METER_CARRY=0 --out-xml out/p0p3-0.musicxml
# and again with --env OMR_METER_CARRY=1 --out-xml out/p0p3-1.musicxml
```

md5 of the record verified FIRST — `52b98f1cdfee3b39f10e56c592828ea4`, matching
the receipt §13 and the corroboration findings both cite. The per-system table,
identical between arms to the character:

```
REACH: 7 systems carry a meter verdict, 7 DECIDED, 0 abstained   [same in both arms]

   system/0/0     decided   voted                          6/8  support=None
   system/1/0     decided   voted                          9/4  support=None   <- the misread
   system/1/1     decided   change_only                    4/4  support=None
   system/2/0     decided   change_only                    4/4  support=None
   system/2/1     decided   change_only                    4/4  support=None
   system/3/0     decided   change_only                    4/4  support=None
   system/3/1     decided   change_only                    4/4  support=None
```

**None of the five `change_only` systems changes `reason`. No system newly
reads `carried`, in any meter.** `diff arm-off.txt arm-on.txt` — empty, exit 0,
including the rest-length census and every `written` count
(`rests 953`, `measure_rests_read 104`, `empty_bars_padded 38`, `notes 2513`,
`notes_not_written_total 876`). `p0p3-0.musicxml` and `p0p3-1.musicxml` are
both md5 `420136cb25d13ade43ff51ef23f649cf`.

## 15.2 · Corroborated independently, the same day, before either side knew of the other

A second, unrelated session (`reengrave-duration-reader-191f40`, branch
`claude/p0p3-voted-misread`, tree `ab448cc8`) ran the identical instrument
against the identical record — confirmed by `ps` to be a genuinely separate
process in a separate worktree, not a restart of this one — and independently
verified the same record md5 **before reading a byte**, per its own committed
write-up (`benchmarks/omr-meter-corroboration-2026-09/out/p0p3/`).

Every one of its files matches this session's byte for byte:

| | this session | sibling session |
|---|---|---|
| record md5 | `52b98f1c…` | `52b98f1c…` (verified independently) |
| OFF export md5 | `420136cb…` | `420136cb…` |
| ON export md5 | `420136cb…` | `420136cb…` |
| `diff` across sessions, OFF vs OFF | — | exit 0 |
| `diff` across sessions, ON vs ON | — | exit 0 |

The sibling session additionally captured `--json-out` for both arms (this
session did not). `diff p0p3-0.json p0p3-1.json` on its side shows the **only**
differing line between the two arms is the `"env"` field itself — every
`segments`, `cautionary`, `bars_fit`, `bars_contradict`, `staves_reading_it`
and `corroborated` value in the full per-system meter record is identical.
This is a stronger confirmation than a text diff of the console table: it says
the ADJUDICATE-stage record is untouched by the flag field for field, not
merely that the final exported notes happen not to move.

This is real corroboration, not the same measurement counted twice: two
independent worktrees, two independent processes, the record hash checked
by each party on its own before either had seen the other's result.

## 15.3 · What running §13's arm sharpens, and what it does NOT close

§11's inference stands: `change_only` firing on five systems is positive
evidence `_carry_meter` was reached and asked five times. Running the arm adds
a stronger fact than §11 could derive from the AST alone — the flag is asked
and returns **literally nothing distinguishable**, not merely "the wrong
candidate loses the weighing" in a way that would show up as a `support` value
or a `carry_outweighed_by_the_bars` reason. The record produced with the flag
on and the record produced with it off are the same record.

⚠️⚠️ **AND THAT IS EXACTLY THE LIMIT BOTH WRITE-UPS NAME INDEPENDENTLY, NOT A
NEW FINDING.** `rest_sizing_arm.py` prints the WINNING rung's reason only,
never a losing rung's — so *refused* and *never handed a candidate* are
indistinguishable in this output, and `support` reads `None` on every meter
row on this record regardless of the flag. §14's open question — *"whether the
carry is refused or merely finds no source"* — **is not closed by running its
own named arm.** That is the correction to carry forward: §13 promised an
answer this specific instrument cannot supply; a probe reading the carry's own
`Ruling` object directly would be the one that could.

## 15.4 · A second, independent correction: this is not the hazard document

The sibling session also checked whether this record reproduces the
`system/0/0` fixture that motivated `OMR_METER_CARRY` in the first place — a
**voted** misread (`C`, 4.0 quarters) standing beside an **abstaining**
neighbouring system, which is the shape the corroboration guard (A-METER-6)
exists to stop propagating. **It is not what this record holds.** Here
`system/0/0` reads `6/8` and is CORRECT; the voted misread has moved to
`system/1/0` (`9/4`); and **nothing on this record abstains at all** — every
one of the seven systems reaches `decided` on its own voted reading or its own
locally-read change, so no system is ever forced to fall back onto a carried
candidate for want of anything of its own.

So the zero measured here is not "the corroboration guard stopped a
propagating misread." It is "no system on this record ever needed the carry's
answer, because every system already had one of its own" — a narrower and
weaker claim, and one that does not test A-METER-6 at all. **The document this
thread has been trying to build — one that both misreads and abstains on the
same movement — is still not this one.** §7's Litolff suppression (abstains,
reads its one meter right) and this record's total absence of abstention
(misreads on two systems, abstains nowhere) are the same gap, approached from
opposite sides, and neither closes it.

## 15.5 · What IS established

- The carry's domain on this record is real (§11's AST argument holds), and
  exercising it costs **nothing measurable**: byte-identical export, and
  (per the sibling's JSON) field-identical adjudicated record, on every one of
  the 5 systems it reaches.
- That zero is corroborated independently, twice, on two different worktrees,
  with the record hash verified both times before either party read it.
- That zero is **not** evidence the corroboration guard is doing its job on a
  hazard case — this record contains no abstention for a carried candidate to
  reach in the first place.

## 15.6 · What remains NOT established

- **Refused vs. never-handed-a-candidate**, still. Neither session's
  instrument can tell them apart; a probe on `_carry_meter`'s own `Ruling` is
  unbuilt by either.
- **The propagating-misread hazard case itself.** This record isn't it, and no
  document named anywhere in this file yet is — every candidate so far either
  misreads nowhere or abstains nowhere, never both on the same movement.
- Nothing beyond §13's own arm was gathered, re-adjudicated, or scored by
  either session; no print was consulted by either.
- n = 1 document, 2 independent re-adjudications of the same frozen GATHER
  stage. Nothing here says anything about Litolff, about a different
  publisher, or about a document that actually abstains somewhere.
