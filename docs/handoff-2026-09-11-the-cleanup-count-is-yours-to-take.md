# Handoff — the cleanup count is built, and the count itself is yours

**For Sean, 2026-09-11.** Phase 2 of
[plan-2026-09-10-wire-first-then-reconcile.md](plan-2026-09-10-wire-first-then-reconcile.md).
This session built the INSTRUMENT and the ARTEFACT and **stopped where
judgement begins**, which is the one thing the job was not allowed to do for
you: *one movement, one human pass*. Nothing here is a count.

---

## 1. What to open, in order

1. **`benchmarks/omr-cleanup-count-2026-09/out/side-by-side-p1-p4.html`** —
   the print beside our output, one printed system at a time, scrollable.
2. **`benchmarks/omr-cleanup-count-2026-09/CATEGORIES.md`** — the four
   categories, and the three hard calls decided in advance with reasons.
   **It is committed alone and first**; that is checkable and is the only
   evidence that the definitions were not fitted to what we found.
3. **`out/counting-sheet-p1-p4.csv`** — one row per staff per system, in the
   HTML's order, with empty `missing` / `wrong` / `spurious` /
   `would_not_notice` / `scope` columns for you.
4. **`benchmarks/omr-cleanup-count-2026-09/FINDINGS.md` §1** — the reach and
   the limits. Read it before the first number or three of the columns will
   look like results.

---

## 2. What the pass actually asks of you

For each printed system, top to bottom of the HTML:

> **How many fix-actions would you make, and in which category?**

A **fix-action** is one editorial gesture — the unit is defined in
`CATEGORIES.md` §0 and the two rules that settle almost every case are:

* **one gesture = one unit**, at the largest scope that gesture repairs.
  Re-entering a whole bar is ONE unit at scope `staff-bar`, however many notes
  are wrong in it.
* **something in roughly the right place with the wrong value is `wrong`,
  never `missing` + `spurious`** — the bound on "roughly" is the same bar of
  the same staff.

Write the scope in the `scope` column: `element`, `chord`, `bar`, `staff-bar`,
`staff-system`, `system`, `page`, or `other` with a note.

**The one judgement only you can make** is `would-not-notice`, and
`CATEGORIES.md` §2c names whose eye it is: **yours, as the editor preparing
the file** — *would you ship it with this in it?* Not the engraver's (who
notices everything) and not the player's (who notices almost nothing). And a
thing you would fix *if you saw it* is `wrong` with the `missable` flag, not
`would-not-notice` — that split is what stops the count rewarding failures
that are easy to overlook.

⚠️ **You do not have to finish it to make it useful.** The HTML is ordered by
where the machine thinks your time goes, worst first. Five systems counted from
the top ranks the work; the number at the bottom of the sheet is the least
interesting thing in it.

---

## 3. What the machine pre-filled, and what it deliberately did not

Every machine cell is in a `proposed_*` column. **Never sum one into a total.**

The machine proposes **only about absence**, which is the only thing the record
knows and your eye does not:

| column | what it means |
|---|---|
| `proposed_missing_bars_nothing_read` | the file wrote a whole-measure rest in that bar and the record gathered NO notehead and NO rest there — *we read nothing, we did not read silence* |
| `proposed_missing_notes_held_back` | ink the record HOLDS and the file does not carry, with the exporter's own reason (`no_pitch`, `duration_narrowed`, …) |

**`proposed_spurious` is null everywhere, and that is a result rather than a
gap.** Spurious means *the file has something the print does not*, and deciding
it needs the print. The machine has the record and the file; neither is the
print. That whole column is yours.

⚠️ Both proposals are LOWER BOUNDS on `missing` and **neither is a lower bound
on the count**: a note the detector never saw is invisible to both, and on a
scan that is the larger population.

---

## 4. The three questions worth more than the total

If you have the patience for only a few systems, these are what the count is
FOR — and the ranking at the top of the HTML is designed to put them in front
of you first:

1. **Is the remaining work dominated by bars we read nothing in, or by bars we
   read wrongly?** Those rank completely differently: the first is detection
   and the second is adjudication.
2. **Is `would-not-notice` large?** If it is, the pipeline's remaining
   differences are cosmetic and the next work is elsewhere entirely.
3. **Which single system costs the most, and why?** Phase 3 is ranked by this
   count, so one well-understood worst case is worth more than a clean average.

---

## 5. What is NOT established, in one place

* **This is the pessimistic end of the corpus.** Litolff `984073` is
  catalogued *low-res bitonal* and CLAUDE.md already records it firing 49 flag
  boxes and 35 dots where Breitkopf fires 371 and 656. A Breitkopf count would
  be a different number and a Breitkopf *ranking* might be a different ranking.
* **It is part of the movement, not all of it** — see FINDINGS §1 for exactly
  where it stops and why. The boundary is at a hand-verified window row, not
  mid-page.
* **Nothing was tuned.** No constant was touched, and no production module in
  `tools/omr/` was edited by this session at all.
* **Inter-counter agreement is unmeasured.** The definitions are written so
  two people would agree; whether they do is a fact about people that nobody
  has tested.

---

## 6. ⚠️ One operational correction, and it will bite the next long run

CLAUDE.md says, of an unattended run:

> ✅ The escape for an UNATTENDED run: `OMR_SURYA_KEEP_ALIVE=0`. A worker per
> page costs ~15 s/page and **owns its own process**, so the run can repair
> itself by killing its own PID.

**That is not true when a resident server already exists, and one did.** Surya
attaches through its own sentinel (`~/.cache/datalab/surya/llamacpp_server.json`),
which named a four-day-old `llama-server` belonging to somebody else; our
worker attached to it and queued behind its other work. `OMR_SURYA_KEEP_ALIVE`
controls whether we ask for the server to be KEPT, not whether we get our own.

Measured here: the pages where the Surya rung ran cost **~6 minutes each**
while the pure-detection half of a page costs well under one, and the main
process sat at a **frozen CPU clock** the whole time — the exact picture
CLAUDE.md warns reads as a hang. It was not a hang; the child's clock was
ticking.

The run was left alone rather than repaired, which is the standing rule and
was the right call — **never blanket-kill by name, and an orphan you cannot
identify is safer left alive.** But the consequence is that an unattended
whole-movement run cannot currently be budgeted, because its cost depends on
whose work is in front of it. That is what bounded this artefact, and it is the
first thing to fix if the count is to be repeated on a second document.
