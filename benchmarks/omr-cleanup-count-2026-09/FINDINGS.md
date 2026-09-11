# The first cleanup count — the instrument and the artefact, not the count

2026-09-11. **Phase 2** of
[docs/plan-2026-09-10-wire-first-then-reconcile.md](../../docs/plan-2026-09-10-wire-first-then-reconcile.md),
whose §6 defines it as *one movement, one human pass, categories fixed in
advance*. This session built the two halves a human pass needs and **stopped
where judgement begins**.

⚠️⚠️ **THERE IS NO COUNT IN THIS DOCUMENT AND THERE MUST NOT BE.** Every
machine figure below is either a REACH figure — how much there is to look at —
or a PROPOSAL about absence. The count is Sean's, on the sheet. The plan is
explicit that it is a RANKING instrument and never a number to drive down:
*the moment it becomes a number to drive down it will be gamed the way OMR-NED
was*, and the two are gamed in **opposite directions** — that metric rewards
emitting MORE symbols and a cleanup count rewards emitting FEWER.

**Nothing in `tools/omr/` was edited and no constant was touched.** The whole
deliverable is under `benchmarks/` and `docs/`.

---

## 0. Order of work, and why the commits are the evidence

`CATEGORIES.md` is **committed alone, and first**, before a single page had
been gathered. The plan says twice that the categories must be fixed before
looking, *"or the count fits itself to what was found"* — and a claim about
what somebody knew when is only checkable if the tree records it. It does: that
commit is an ancestor of every commit that produced output, it touches one
file, and it was never amended.

⚠️ Its §4 worked examples come **only from findings already committed in this
repo** — the `arpeggiato` misread, the chord-tie relocation, the `entire staff`
fragmentation — so no example could have been chosen to fit this artefact. Real
examples from the artefact belong in a later commit, marked as such.

⚠️ One decision was left on the table BECAUSE of that ordering, and it is worth
seeing: §3 fixes the machine's contribution as being about **absence only**, so
when the printed BAR count turned out to be hand-read (and therefore able to
support a `spurious` proposal where we emit more bars than the page prints),
that was recorded as a **fact** on each row rather than promoted into a
pre-filled category. Widening the machine's remit after seeing the data is
precisely the fitting the commit order exists to rule out.

---

## 1. ⚠️⚠️ REACH AND LIMITS, BEFORE ANY NUMBER

### 1a. This is PART of the movement, and the boundary is not arbitrary

| | |
|---|--:|
| pdf pages gathered | **1-4** of the ~16 that carry movement 1 |
| printed systems | **7** |
| printed bars | **mm 1-112** of the reference's **502** — **22.3%** |
| staves per system | 12, 11, 11, 11, 8, 11, 11 |

The boundary sits exactly at the last **hand-verified window row**
(`benchmarks/omr-scan-e2e-2026-09/works.json`, `…-p1` … `-p4`). Past p.4 nobody
has checked which printed bar each system starts at, so past p.4 the artefact
could not tell the human *which bars they are looking at* — and a side-by-side
that mislabels its bars is worse than no side-by-side.

⚠️ It is a real boundary and not a soft edge: the four pages cover **all four
structural shapes this plate prints** — a one-system page, a two-system page, a
page whose second system SUPPRESSES three staves, and a page whose two systems
print the same COUNT with different LINEUPS. The fifth shape (a movement
boundary) is not in movement 1 at all.

### 1b. This is the PESSIMISTIC end of the corpus, and it must be said first

Litolff `984073` is catalogued *"low-res bitonal"*. CLAUDE.md already records it
firing **49 flag boxes and 35 dots** where the Breitkopf Brahms scan fires
**371 and 656**, and the dotted-rest work already measured a change on it that
moved **zero** verdicts purely because the page holds almost no dots. So:

> **A Breitkopf count would be a different number, and it might be a different
> RANKING.** Nothing here generalises to a second publisher, and this thread
> has now been corrected by a second publisher at least five times.

### 1c. What the machine may propose, and what it may not

`proposed_spurious` is **null on every row, by design**. Spurious means *the
file has something the print does not*; deciding it needs the print, and the
machine has the record and the file, neither of which is the print. The whole
column is the human's.

Both proposals it does make are **lower bounds on `missing` and neither is a
lower bound on the COUNT**: a note the detector never saw appears in neither,
and on a scan that is the larger population.

### 1d. The cost of the run, measured, because it bounds the next one

**26 min 18 s for four pages** — about 6.6 minutes a page, of which the
detection half is well under one. The rest is the Surya rung, and §6 explains
why that cannot currently be budgeted.

---

## 2. THE ARTEFACT

| file | what it is |
|---|---|
| `out/side-by-side-p1-p4.html` | the print beside our output, **one printed system at a time**, ordered by proposed attention. 6.4 MB, **self-contained** — crops are embedded, because the repo's root `.gitignore` excludes `benchmarks/**/crops/` and a linked crop would show a committed reader seven broken images |
| `out/beethoven5-mvt1-p1-p4.musicxml` | the staged pipeline's output, 12 parts, 1,183 measures |
| `out/counting-sheet-p1-p4.csv` | one row per staff per system, **in the HTML's order**, with the four category columns empty |
| `out/system-map-p1-p4.json` | which exported measures belong to which PRINTED system — it exists nowhere else, see §4 |
| `out/proposals-p1-p4.json`, `out/coverage-p1-p4.json` | the machine's proposals; the exporter's own coverage report |

**The ordering is by proposed attention, not by page**, which is the whole
instruction: a system that failed STRUCTURALLY sorts above one that is 95%
right. Today that puts **page 4 first and page 1 sixth**. The weights
(`30 × missing staff-systems + 30 × parts-out-of-sync + 3 × unread bars +
notes held back`) are DISPLAY ORDER and nothing else reads them; they are not a
claim that a staff costs thirty notes.

### What the file actually contains, for the four pages

| | |
|---|--:|
| parts / measures | 12 / 1,183 |
| notes / rests written | **1,793** / 657 |
| noteheads the record holds | **2,347** |
| notes held out of the file | **554** — `duration_narrowed` 339, `no_pitch` 215 |
| slurs / ties written | 32 / 84 |
| arc rows decided | 365 slur + 414 tie = **779** |
| arcs not written | **605**, of which **538 bind fewer than two notes** |
| dynamics written | 174, from **485** letter rows (35 `unspellable`) |
| fermatas / articulations written | 41 of 67 marks / 64 of 98 |
| direction words written | **6** |
| bars exported with nothing read in them | **66** (no ink at all) |
| bars exported with no event written | **178** (`empty_bars_padded`) |

⚠️ **Those last two are different facts and the gap between them is the
finding.** 66 bars hold no gathered ink at all. 178 bars come out with no
event. So on **112 bars the page gave us ink and no event came out of it** —
which is `missing` to the human either way, and a completely different repair
for us.

---

## 3. FOUR THINGS THE INSTRUMENT FOUND WHILE BEING BUILT

All four are **reported and none is fixed** — Phase 3 is ranked by the count,
and *a wiring pass may not change behaviour it has not priced* applies at least
as strongly to an instrument pass.

### 3a. ⚠️⚠️ THE PARTS OF THE FILE DISAGREE ABOUT WHICH BAR THEY ARE IN

A part whose staff is SUPPRESSED on a system gets **no measures at all** for
those bars. On p.3 system 2 the plate suppresses Oboi, Trombe and Timpani, so
from p.4 onward those three parts are **eighteen bars behind** the other eight:

| part | measures in the file |
|---|--:|
| P1-P8 | 111 |
| P9, P10, P11 | **93** |
| P12 | **16** |

`<measure number="82">` therefore names a different instant in different parts
of one file, and any consumer reading it vertically gets garbage from p.4 on.
**Verovio says so out loud** — `Mismatching measure number 87` — and would drop
measures rather than render them, which is how this was found.

⚠️ **P12 is the same defect in its other form**: the 12-staff lineup condenses
to 11 from p.2, so part 12 simply STOPS after bar 16. A reader sees an
instrument that stops playing.

⚠️ The side-by-side renumbers each slice 1..n to work around it. **That is not
a repair** — the file still carries the defect — and the renumbering
deliberately does NOT hide a staff that genuinely read a different *number* of
bars, which still comes out visibly short.

### 3b. The meter is decided on ONE system of seven

`time`: **1 decided, 6 abstained** (`no_evidence` 2, `too_few_staves_read_it`
4), and `empty_bars_padded_without_meter` is **162**. A meter is printed at a
movement's start and nowhere else; `OMR_METER_CARRY` is the mechanism for that
and is **default-off on `n`**. So six systems of seven carry no `<time>`, no
bar length, and therefore no `measure="yes"` on their measure rests.

⚠️ **This is the cleanest thing the count can rank, and it is exactly what the
count is FOR**: a flag that is off for want of a second document is visibly
costing the human on the first.

### 3c. No part has a name

All twelve `<part-name>` elements read `Staff p1-s0-N`. `instrument` produced
nothing on any of the 22 staves, so the exporter fell back to coordinates —
which CLAUDE.md already records for `group_symbol` (`no_identity` on 22 of 22)
and is here confirmed to reach the FILE.

### 3d. `arpeggiato` is still 377 boxes on four pages

`unclaimed_classes` reports `arpeggiato: 377` and `stringsDownBow: 1`. The
first is the misread stems and barlines CLAUDE.md already names. **It costs the
human nothing** — no quantity claims it, so none of it reaches the file — and
it is exactly the `page_has_none` / `not_detected` distinction that
`CATEGORIES.md` §3 exists to keep.

⚠️ And the headline the exit condition cares about holds on this document:
**`detected_and_unrepresented_total` is 0**, and `status_census` reports
`stub: []`, `starved: []`, `NO_QUANTITY: []`, `unaccounted: []`.
Phase 1 is standing up on a real four-page run.

---

## 4. THE CONTROLS, AND WHY EACH ONE EXISTS

Three, each of which **refuses** rather than warning, because in this repo a
control that cannot fail has failed at least seven times.

1. **The system map against the file.** The map is derived by calling
   `export.build` — the exporter's own `StaffRun`s — and then asserted against
   the emitted XML: every `(part, measure)` it names must exist, and every
   measure in the file must be named exactly once. **1,183 pairs, all present
   exactly once.** A map that quietly disagreed would send the human to the
   wrong bars, and they would count real music as wrong.
2. **The per-system decomposition against the exporter.** `build_sheet`
   re-derives `_place_notes`' three refusals per system, which is drift risk,
   so the per-system reasons must sum to the exporter's OWN
   `notes_not_written`. They do: 339 + 215.
3. **The engraved half against the file.** Verovio drops what it cannot place,
   silently, so each row compares the glyph count in the SVG with the count in
   the file for exactly those bars. **7 of 7 rows draw exactly what the file
   holds.** ⚠️ This control is the reason 3a was found rather than shipped: it
   was RED on every page-4 row before the slice was renumbered.

⚠️ **The crop's frame is the fourth control and it is structural rather than
asserted.** The crop is cut from the pipeline's OWN page raster
(`preprocessing.render_page`, which DESKEWS) rather than a fresh render at the
same nominal DPI — those are different images, and a mis-framed crop does not
raise, it just looks like a slightly wrong reading of the music, which is the
one thing the human is being asked to judge.

---

## 5. WHAT IS NOT ESTABLISHED

* **No count exists.** Nothing here says how much work the cleanup is.
* **One document, one publisher, one movement, 22% of it.** §1b.
* **Inter-counter agreement is unmeasured.** The definitions are written so two
  people would agree; whether they do is a fact about people.
* **The attention ORDER is unvalidated.** It is the machine's guess at where
  the human's time goes, and the human's own sheet is the first evidence about
  whether it was right. If row 7 turns out to be the expensive one, that is a
  finding about this instrument.
* **`would-not-notice` has no machine estimate at all** and cannot have one.
* **The proposals are lower bounds on `missing` only** — §1c.
* **No OMR-NED figure is claimed**, deliberately. The metric was retired as the
  organising goal on 2026-09-08 and this artefact exists because of that.

---

## 6. ⚠️ TWO CORRECTIONS, ONE OF THEM OPERATIONAL AND EXPENSIVE

### 6a. `OMR_SURYA_KEEP_ALIVE=0` does NOT give an unattended run its own worker

CLAUDE.md says:

> ✅ **The escape for an UNATTENDED run: `OMR_SURYA_KEEP_ALIVE=0`.** A worker
> per page costs ~15 s/page and owns its own process, so the run can repair
> itself by killing its own PID.

**Not when a resident server already exists, and one did.** Surya attaches
through its OWN sentinel, `~/.cache/datalab/surya/llamacpp_server.json`, which
named a four-day-old `llama-server` belonging to another session; our worker
attached to it and queued behind that session's work. The flag controls whether
we ask for the server to be KEPT — not whether we get our own.

Measured here: one page cost **~6 minutes** in the Surya rung while the main
process sat at a **frozen CPU clock** — precisely the picture CLAUDE.md warns
reads as a hang. It was not a hang; the CHILD's clock was ticking, at 0.75 s of
CPU per two minutes, because the model work happens in the shared server.

The run was left alone, which is the standing rule and was right — *never
blanket-kill by name*. The consequence is that **an unattended whole-movement
run cannot currently be budgeted**, because its cost depends on whose work is
in front of it. That, and not the page count, is what bounded this artefact.

### 6b. A background job started from a tool call can be reaped, and it looks like a crash

The first gather was launched with `nohup … &` and its log simply stopped
mid-page with **no error, no traceback and an exit status nobody saw**. The
second launch then wrote to the same paths as the first, which was still alive
— two gathers, one output file. Found by listing processes by their real
`Python.app` argv rather than by `python3`, which matched nothing and had
already been read once as *"the run died"*.

⚠️ **Both halves of that are the same lesson in different clothes:** a
`grep python3` that matches nothing is not evidence a process is gone, and a
log that stops is not evidence a run stopped.

---

## 7. WHAT THE NEXT SESSION SHOULD DO WITH THIS

1. **Get the count taken.** Everything else here is scaffolding for it, and the
   first five rows of the HTML are worth more than the last two.
2. **Do not fix 3a-3d before the count.** The plan ranks Phase 3 BY the count;
   fixing the loudest thing first is the ranking-by-cheapness this plan exists
   to replace.
3. **The second document is Breitkopf Brahms 1**, for the reason §1b gives and
   for the reason the meter floors have been waiting on it for three sessions.
4. **Budget the Surya rung before promising a whole movement**, per §6a.
