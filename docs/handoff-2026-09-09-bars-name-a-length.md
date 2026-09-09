# Handoff — the bars can name a LENGTH, and only ink can name a METER

⚠️ **READ THIS FIRST.** It replaces
[docs/handoff-2026-09-09-meter-as-a-range-fact.md](handoff-2026-09-09-meter-as-a-range-fact.md)
as the entry point. That file's §1 redirect still governs — **the metric is not
the goal** — and its §5 task **1** is what this session did.

⚠️ Its **§4 still stands unamended** and must be read before quoting anything
about the meter work: n = 1 document, the *Andante* refusal is SAFE but NOT
DISCRIMINATING, and the bar-math half of the CHANGE detector contributed
`0 fit / 0 not` even on the case that works.

---

## 1. WHAT LANDED — `OMR_METER_FROM_BARS`, default `0`

A system that read no meter **and could not carry one** may now take the bar
length its own bars agree on.

**The finding that shaped it, and nobody had made this split:** a bar sum is a
**LENGTH**, and a meter is a length **and an engraving**. 2.0 quarter-notes is
`2/4` and equally `4/8`; 3.0 is `3/4`, `6/8` **and** `12/16`. No arithmetic
separates them, because it is the same arithmetic. So:

* the bars name the **length**, scored in the carry's own currency (`+1.0` per
  bar that fits, `−1.0` per bar that does not, floor `4.0` — the weights are
  **imported** from the carry, not restated, so the two cannot drift);
* the **spelling** is borrowed from the nearest preceding system whose meter
  was `voted` **and whose length already matches**;
* where none exists it abstains **`bars_name_a_length_without_a_form`**,
  recording the length, the support, and every spelling that length could be.

**And a second change, found by hunting the boundary above:**
`adjudicate_meter` chained its fallbacks with `or`, but `_carry_meter` returns
a `Ruling` when it DECIDES *and* when the bars OUTWEIGH it — both truthy — so
**a refusal stopped the chain and the rungs behind it were never asked.**
`_meter_fallbacks` replaces it, ordering by what each rung KNOWS: a
corroborated carry, then this system's own bars, then a printed change, then
the **most informative refusal rather than the last one tried**. ⚠️ Half of
that gap predates `OMR_METER_FROM_BARS`: a system whose carry was refused
could not report a meter change printed on it either.

⚠️ **The LETTER is never borrowed.** `raw` reaches `staged.export` as
`symbol="common"` / `"cut"` — a positive claim that a `C` is PRINTED on a
system that printed nothing we could read. Borrowed meters are spelled in
digits and the source's own `raw` is recorded beside the answer.

---

## 2. THE MEASUREMENTS

Beethoven 5 / Litolff `984073`, weights `hollow-graft-shift09`, one document
throughout. Carry OFF in every arm, so nothing else is in play.

| run | result |
|---|---|
| `--pages 0-2` | both continuation systems go abstaining → **`derived_from_bars` 2/4**, support **+6.0** (8+/2−) and **+7.0** (8+/1−) |
| `--pages 1,17` (*Andante*) | **all three systems unchanged** — the control holds with no special case |
| `--pages 1,63` | two systems record **length 3.0, forms `3/4` `6/8` `12/16`** — **truth `3/4`, hand-read** — while refusing to borrow the `2/4` standing in front of them |
| flag OFF, `--pages 0-2` | matches the artefact committed **before** this session on every subject, outcome, reason and value |
| `--pages 1,63`, **carry ON** | the carried `2/4` is refused at **−6.0** (1 agree/8 disagree) and **−7.0** (0/8) — ⚠️ the discrimination the *Andante* could not give |
| `--pages 1,63`, **both flags** | after the §4 fix: **length 3.0 at +5.0 and +4.0** where before it abstained on the carry's refusal |
| `--pages 1,17`, **both flags** | all three *Andante* systems still refuse — the bars are asked and name nothing |

In the file (pages 0-2): `empty_bars_padded_without_meter` **47 → 0**,
`measure_rests_read` 92 → **169**, `written.notes` 648 → 665,
`not_written.duration_narrowed` 163 → 146.

✅ **Re-measured on the MERGED tree and identical.** 27 commits landed on main
during this session, including 376 changed lines of `staged/gather.py` — where
the `Q.EVENT` / `Q.DURATION` / `Q.REST` rows this reads come from — so all
three arms were re-run after merging rather than assumed to survive it. All
three `.meter.txt` files compare byte-for-byte. Merged-tree suite **3370
passed / 11 skipped / 0 failed**, `inventory --check` and `health --check`
both 0.

---

## 3. ⚠️⚠️ WHAT IS *NOT* ESTABLISHED — read before quoting §2

* ⚠️⚠️ **THOSE FILE NUMBERS ARE THE CARRY'S OWN, TO THE UNIT.** The previous
  handoff's §3 records exactly `648 → 665`, `163 → 146` and the `47`
  disappearing, for `OMR_METER_CARRY=1`. **On this document the DECIDED
  branch never fires on a system the carry does not already serve.** This is
  NOT a gain on top of the carry and must not be reported as one.
* **What is genuinely new is the ABSTAINING branch** — two p.63 systems the
  pipeline previously had nothing at all to say about now carry a length and
  a shortlist, and the truth is in the shortlist.
* **And what differs is what each can be WRONG about.** The carry reaches
  across a movement boundary and is stopped only by the bars refusing it;
  this cannot reach across one at all, because it never looks at another
  system.
* ✅ **THE CASE THAT SEPARATES THEM IS NOW MEASURED — see §2b and §4b.** It was
  never a "movement boundary": the mechanism does not ask whether a movement
  started, only whether the carried meter fits. On **p.63** the carried `2/4`
  is refused at **−6.0 (1 agree / 8 disagree)** and the same bars name **3.0
  at +5.0**, which is the printed `3/4`. ⚠️ What is still unmeasured is a
  movement-START page specifically, and on this document **there is no such
  page to measure** — all three were located and all three read badly.
* ✅ **The `3/4` on p.63 IS hand-read.** It was written up as an inference
  first; the pages were then rendered and looked at, because that row is what
  the abstaining branch rests on. **p.62 prints `147` at top-left and p.63
  prints `160`**, and the reference's 3/4 runs 155-208.
* **n = 24 systems on 17 pages, 1 document, 1 publisher** — and of those, **two**
  systems exercise the deciding branch and **two** the abstaining one.
* ⚠️ **The bars are not fully independent witnesses.** The per-bar cross-staff
  majority is the only thing standing against a systematic duration misread,
  and bars on one staff share that staff's beam and clef regime. `A-DUR-6`
  names this hazard; nothing measures it.

---

## 4. ⚠️ FOUR THINGS THAT COST TIME OR NEARLY SHIPPED WRONG

1. ⚠️⚠️ **A CLEAN, BELIEVABLE ZERO THAT WAS THE HARNESS.** The first
   `OMR_METER_FROM_BARS=1` arm came back **byte-identical to the control** and
   was nearly written up as "no reach". It was **zsh**: `env $3 python3 ...`
   does not word-split an unquoted expansion, so `env` set
   `OMR_METER_FROM_BARS="1 OMR_METER_CARRY=0"` and the flag was off in the arm
   that existed to turn it on. This repo already documents the trap for
   `${=IDS}` in the labeling runbook. **The tell was that a probe reading the
   live log had already said `+6`** — the run disagreed with a measurement
   made an hour earlier on the same tree. *Check the probe against the
   pipeline AND the pipeline against the probe.*
2. ⚠️ **A MUTATION SURVIVED, AND DELETING THE RULE WAS THE RIGHT FIX.**
   `METER_FROM_BARS_MIN_ASSESSABLE = 4` was written on `METER_CARRY_MIN_BARS`'s
   two-questions reasoning. Removing it broke no test — because a bar is worth
   1.0, so a floor of 4.0 already implies four assessable bars. **It could not
   fire.** Deleted rather than left as decoration: a gate that cannot fire
   reads to the next person as a protection that is not there.
3. **"For 6 measures" is not a run.** The literal reading was measured first:
   the longest CONSECUTIVE run of assessable bars is 5 where the meter is
   read, 3 where it is wanted and **1** on the dense finale pages, because a
   run breaks on an *unassessable* bar — legibility, not meter. Run length is
   expressed by the terms accumulating instead.
4. **The first p.63 control was not discriminating.** `--pages 0,63` has no
   system on page 0, so "no form borrowed" only showed there was nothing to
   borrow. `--pages 1,63` puts a `voted` **2/4** in front of bars that say
   **3.0** and is the arm that actually exercises the length gate.

5. ⚠️⚠️ **EDITING A SOURCE FILE WHILE THE SUITE RUNS BREAKS
   `inspect.getsource`, AND IT FAILS AS A FALSE FINDING.** The first full run
   came back with `test_a_CLOSED_gap_must_LEAVE_the_list` failing on
   *"meter declares 'dossier_fact'"* — i.e. claiming a KNOWN_GAPS entry had
   been silently CLOSED by this change. It had not. `inventory._never_read`
   parses the decision's source with `inspect.getsource`, which reads the file
   through `linecache`; comment edits made to `rhythm.py` at ~63% shifted its
   line numbers under the already-imported module, so the parse no longer
   matched and the check reported nothing for that decision. **A stale-gap
   check reads as a REAL finding about your change** — it names a gap and a
   quantity. Re-run on a frozen tree before believing one. Same family as the
   cached bytecode and the cached `scan_eval` A/B; the new part is that the
   cache is `linecache`, invalidated by your own editor.
6. **A worktree needs FOUR symlinks, and the fourth fails LOUDLY in a way the
   others do not.** Without `.venv-surya`,
   `test_direction_text.py::TestReaderSelection::test_the_env_var_restricts_the_rungs`
   **FAILS** rather than skipping — `default_readers()` returns `[]` because
   Surya self-disables. That is a real failure to explain, not an
   environmental skip, and it is easy to mistake for a regression.

**Eleven mutation arms were run**, clearing
`~/Library/Caches/com.apple.python/<abs path>/` between each. Ten turned
tests RED; the eleventh is item 2.

---

## 5. THE NEXT WORK, RANKED

### 1. ✅ DONE — and the answer changed the question. What is left is ENGRAVED.

The case that separates the two mechanisms was found and measured (§2, §4b):
**p.63**, where the carried `2/4` is refused at −6.0 and the same bars name
3.0 at +5.0. It is not a movement boundary and never needed to be — the
mechanism asks whether the carried meter FITS, not whether a movement started.

⚠️ **A movement-START page is a different matter, and on this document there
is not one that reads well.** All three were located (p.17 *Andante*, p.32
Scherzo, p.44 Finale) and all three fail — **for opposite reasons**: an
opening is either sparse (most instruments resting, and a lone whole rest may
never corroborate) or a dense tutti, which is the texture the reader is worst
at. p.32's best system gets 8 assessable bars and still scores **0**.

**So the remaining route is the ENGRAVED one**, unspent since §11 of
`omr-staged-meter-carry-2026-09/FINDINGS.md`: render
`beethoven--symphony-5--mvt4` (4/4 → 3/4 → 4/4 → 2/2) through LilyPond with
`orchestral_eval`, where legibility is not the confound. If the rule fires
there it is a rule; if it does not, no amount of scan work would have said
so.

### 2. A SECOND DOCUMENT AND PUBLISHER

Everything about the meter — the carry, the change detector, and this — rests
on one Litolff Beethoven. 230 reference works encode a mid-piece `<time>`
change (`omr-staged-meter-carry-2026-09` §11 found them); the score library
holds editions for many.

### 3. THE REST OF `A-DUR-6`, UNCHANGED FROM THE LAST HANDOFF

Item 5 (surrounding bars) is now partly built. **Items 6 and 7 do not exist**:
beat subdivision, and `A-DUR-5`'s unclassified ink — Sean's standing request,
still flagged at the head of CLAUDE.md, still needing a RASTER pass in GATHER.

⚠️ **The double barline is NOT the cheap win `A-DUR-6` calls it.** Checked:
`Q.BARLINE_COLUMN` is a per-staff **count of cells**, not barline positions or
types, and the repo has no barline-type classification at all (NOTES.md item
5). Reading a double barline needs new CV plus a new gathered quantity — not
"no new CV". Correct the assumption before anyone budgets for it.

### Also open, unchanged

Unify the two chord groupings (export consuming `Q.EVENT`); `arc_kind` /
`arc_owner` still stubs (843 arcs); calibration from the score library, which
bar sums make possible with no truth files and which nothing has built.

---

## 6. OPERATIONAL

* `OMR_SURYA_KEEP_ALIVE=0` for unattended runs; **never `pkill` the shared
  daemon** (`llama-server`). This session killed only its own
  `tools.omr.staged` arms, by full command match, and verified the daemon
  afterwards.
* A worktree needs **four** symlinks before the suite is trustworthy:
  `library`, `tools/omr/training/data/weights`, `.venv-surya` and
  `.venv-omrned`. The staged pipeline itself needs only the weights — but
  **the SUITE needs `.venv-surya` or one direction-text test FAILS** (see §4
  item 6).
* ⚠️ **Do not edit a source file while the suite is running** — see §4 item 5.
* ⚠️ **Multi-page runs only.** A single page has no earlier system to borrow a
  spelling from, so the whole mechanism reads as inert.
* The full suite takes ~9-11 minutes and sits a long while around 64% in
  `test_roster.py`. That is normal.
