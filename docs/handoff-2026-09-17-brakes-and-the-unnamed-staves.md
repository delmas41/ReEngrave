# Handoff: the brakes, the unnamed staves, and the merge

**START HERE. EVERYTHING IS ON MAIN** — `c9582f6d`, six branches landed,
`4428 passed / 11 skipped`, eleven derived checks green ON THE MERGED TREE. Read §1 before touching anything: the session's headline is a
FAILURE CLASS, and it caught this session's author twice.

⚠️⚠️ **THE BIGGEST SINGLE FINDING IS §2a, NOT ANY BRAKE: of 28 decisions,
ONE can hand work to INFER and 27 CANNOT.** 2,289 abstentions on one document
and 1,656 on another say *"I cannot"* into a pipeline whose fourth stage is
defined to answer exactly that, with no rule to receive them. The repair is
almost never *loosen the refusal* — it is *wire the outcome to the stage that
may act on it*.

## 1. THE GOVERNING FINDING — now in CLAUDE.md

**A PREMISE ENCODED IN A REFUSAL OUTLIVES ITS REASON.** Sean, after four
instances in one session: *"We have rules that are stopping things too soon or
disregarding the information... when those statements were made we didn't have
everything we have now."* Third named family beside *the value existed and
nothing read it* and *a rule described in a docstring and never built*, and
the hardest to see, because the code is not wrong and the tests pass.

⚠️⚠️ **NOTHING MAY BE EXEMPTED FROM BEING ASKED.** My first audit brief named
four refusals as *"load-bearing, leave them alone"* — the audited pattern,
committed inside the audit. Sean: *"It's not as simple as opening the flood
gates, but everything that may have had a justifiable reason before may not
apply anymore."* Two of my four had visibly expired reasons (the exporter's
argmax refusal predates `OMR_INFER`; EVALUATE's silence predates a stage for
*best rather than forced*).

⚠️ **THE YARDSTICK IS SEAN'S, AND IT IS WIDER THAN "is the data there":**
*"Every brake should be evaluated against the conceptual possibilities of the
new staged architecture."* Most brakes predate the record entirely, written
when the only options were ANSWER or DISCARD. Six capabilities that now
dissolve whole classes: an abstention is DATA; a PARTIAL answer has somewhere
to live (`Ruling.narrow`); evidence CONTRIBUTES (`Mode.ADDITIVE`); provenance
distinguishes derived from read (`basis`); correlated witnesses are
REPRESENTABLE (`Verdict.correlated`); and a FOURTH STAGE exists for best-not-
forced.

⚠️ **THE COROLLARY, probably larger than any single gate:** a brake whose
reason was *"no stage may do this"*, where a stage now exists, is not a brake
to remove — it is a **HANDOFF THAT MAY NOT BE WIRED**. INFER collapses 17 of
357 narrowed durations.

## 2a. THE MISSING HANDOFF — the brake audit's headline

`benchmarks/omr-brake-audit-2026-09` + `tools/omr/staged/brakes.py`
(`python3 -m tools.omr.staged.brakes --check`).

**`infer.RULES` registers TWO rules and both target `duration`.** Verified
independently: 2 rules, 1 of 28 decisions can hand on, 27 cannot.

| | Beethoven 5 | Brahms 1 |
|---|--:|--:|
| unresolved (abstained + narrowed) | 2,646 | 2,202 |
| reach a registered INFER rule | 357 (13.5%) | 546 (24.8%) |
| **stop — no stage may take them** | **2,289** | **1,656** |

⚠️ NOT an argument for writing 27 rules; it says which deserve one. And 13.5%
is an upper bound on REACH, not on effect — INFER collapses 17 of 357.

⚠️⚠️ **VERIFYING THIS RETURNED ZERO ON THE FIRST TRY**, because `infer.RULES`
is empty on a bare import — the rules register by decorator and need
`staged.inferences` imported, exactly as `adjudicate.REGISTRY` needs
`adjudicators`. **Four people have now been caught by that import, including
two auditors auditing vacuity.** `import tools.omr.staged.inferences` first.

**Ranked, each naming the capability its premise was written against:**
**R1** `adjudicate_instrument` returns before consulting evidence it DECLARES
— on all 25 unnamed staves `considered=[] used=[] declined=['margin_label']`
while `roster_entry`/`staff_ordinal`/`staff_group` are present 25/25, declared
in `wants`, untouched; cascade measured to 25 unnamed parts. ⚠️ The abstention
is CORRECT; the EARLY RETURN is the brake.
**R2** the circularity premise (see §2). **R3** `stem_direction/no_stem` —
904 and 1,546, the largest population on both and the only one larger on the
second publisher; evidence exists SIDEWAYS and no rule takes it.
**R4** `glyph_owner/tied` consults neither thing it declares (21 rows) —
CLAUDE.md's standing observation, now with a reach number.
**R5-R7**: a reason word that misdescribes its row; two declared reasons no
site can return; a narrowed CLEF silencing a staff's pitches.

⚠️ **THE CONTROL LIST MATTERS AS MUCH**: 12 of 18 brakes judged SOUND and
stay, including all four the manager had wrongly tried to exempt. Two results
there: the exporter's argmax refusal is sound AND its handoff IS wired;
**EVALUATE's silence is sound and its handoff is NOT** — refusing leaves the
duration DECIDED, and `INFERABLE` excludes DECIDED, so INFER may never revisit
it. ⚠️ That one is UNMEASURABLE today: `reconcile_duration` records no skip
reason, so its refusals appear in no record.

## 2. THE UNNAMED STAVES — cause found, rule measured, NOT shipped

Sean opened the cleanup artefact and stopped: *"our version is still too far
off to be worth counting"*, *"the first system had twice as many staffs as the
pdf"*, *"all of them empty"*.

**Cause:** 30 of 37 parts were on ONE system. Two correct repairs never
measured together — the part join stopped grafting (right) and the tacet
padding writes a part into every system it is absent from (right); composed,
every fragment was padded across six systems. When the padding landed it
reached ZERO bars here because the meter was not yet carried.

**Shipped (my branch):** fragments are not padded (first system 37 rows → 12,
matching the print; 2,924 → 544 padded bars; notes UNCHANGED), and
`OMR_HOLD_OUT_UNIDENTIFIED` (default ON, Sean: *"hold out - I want truth"*)
holds unidentified staves out of the file — parts 37 → 12, with **783 notes
counted under `staff_not_identified`** rather than silently lost.

⚠️ **The hold-out governs the OUTPUT, not the ENQUIRY, and the first version
conflated them.** A staff still exits identification after ONE channel.

**Why they are unnamed:** the plate labels the strings on the opening system
only — common engraving practice (Sean). Verified: named staves are always a
prefix, unnamed always a suffix, never interleaved, all 25 are strings.

⚠️⚠️ **SEAN'S RULE IS MEASURED AND IT IS THE STRONGEST RESULT OF THE DAY**
(branch `claude/unnamed-staves-alignment`, 3 commits, `tools/` untouched):
a bottom-contiguous unnamed block of 4-5 staves is the string section —
**fires 6 of 6 systems, 25 of 25 correct, ZERO grafts**, and **invariant under
scrambling every `clef_glyph` in the record**, while the clef-dependent arm it
replaces had robust reach ZERO and grafted on 19 of 128 perturbations.
⚠️ 5 abstentions are the condensed `Violoncello e Basso` (two slots, one
staff) — abstained, not picked.
⚠️ **THE BOUND: the record holds 74 `clefG`, 17 `clefF` and ZERO C clefs.**
The alto clef never appears, so the corroboration that would catch a NON-
standard block (a tacet Violino II grafts three staves) is half-blind. Ship
the clef as a support term that can pull into abstention, NEVER as a gate.

⚠️ **The circularity that blocked this for months dissolves**: the objection
is true of `Q.CLEF` (a VERDICT, ORDER 9, while `instrument` is 5) and FALSE of
`Q.CLEF_GLYPH` / `Q.CLEF_POSITION` (GATHER facts, `gather.py:1687`/`:1705`),
verified — `inventory --check` raises on the verdict and not on the reading.
The brake read as *"this cannot be done"*; it was *"not THAT way"*.

⚠️ Cheapest separate fix: **the catalog roster names zero strings** while
listing `string` among its families (`tools/library/ingest.py`). Reach 0 of 25
today; fixing it forces p4/s0 by counting alone.

## 3. THE MERGE — `claude/integration-2026-09-17`

Five branches merged in this order (the only order tested):

| # | branch | what |
|--:|---|---|
| 1 | `claude/data-flow-stages-handoff-5c1e07` | identity run, settings stamp, padding + hold-out, flag-docs check, the failure family |
| 2 | `worktree-agent-a0c804088cff5d4f9` | `record.CLAIMS` — every fact carries its claim kind, DERIVED so records stay byte-identical. **Already contains `claude/family-position-facts`** (11 commits of position facts) — one merge, not two |
| 3 | `worktree-agent-a3b616ad6dc60a313` | the measurement-meaning audit + `staged/meaning.py` |
| 4 | `claude/unnamed-staves-alignment` | the string-block measurement; `tools/` diff EMPTY |
| 5 | `claude/brake-audit-2026-09-17` | §2a + `staged/brakes.py` |

**ONE conflict, in `tools/omr/staged/reach.py`**, purely additive — two audits
each registering themselves in `NOT_A_STAGE`. Both kept.

⚠️⚠️ **AND THE MERGE MADE A COMMENT FALSE, WHICH IS WHAT MERGES DO HERE.** The
brake audit found that `reach --check` does not enforce its own documented
rule and REPORTED it; branch 1 had FIXED it the same afternoon. Neither branch
could see the other and only the merged tree has both. Corrected in the
resolution — *the merged tree is the one thing nobody runs*, caught on
schedule.

⚠️⚠️ **AND THE MERGED SUITE FAILED FIRST — 3 failed / 4425 passed — WHICH IS
THE WHOLE REASON TO RUN IT.** No branch could see any of the three; each was a
contract changed on one side. **The task harness reported "exit code 0" while
pytest returned 1**, and the only reason it was caught is an explicit
`echo $?`. *Read the OUTPUT, not the STATUS.*

1. `CLAIM_OF_MEMBERSHIP_KIND` stopped being TOTAL when branch 1 added
   `KIND_UNNAMED`. ⚠️ Both obvious fixes are wrong: a claim word files
   UNCLAIMED ink under an identification, and `None` puts a non-claim in a
   table of claims (a sibling test correctly rejects it). It belongs OUTSIDE
   the map; the exclusion is now STATED as `CLAIMLESS_KINDS`, itself asserted
   to name only kinds the store declares.
2. The flag-docs check went red on `OMR_FAMILY_POSITIONS` — undocumented.
   Working across a merge, the case it was built for.
3. The accounting-control stub needed `held_out=` — second signature today.

**ELEVEN derived checks exit 0 on the merged tree** (`capture`, `wiring`,
`inventory`, `gather_coverage`, `health`, `reach`, `meaning`, `brakes`,
`no_producer`, `export_coverage`, `accuracy_record`). ⚠️ The manager PREDICTED
the audits would go red on success — several assert gaps that sibling branches
closed. They did not. Do not read that as proof they cannot; it is one merge.

## 3b. THE BRANCHES AS THEY WERE

| branch | commits | what |
|---|--:|---|
| `claude/data-flow-stages-handoff-5c1e07` | 14 | this session: identity run, settings stamp, padding + hold-out, flag-docs check, the failure family |
| `claude/family-position-facts` | 11 | position facts for 11 families, producers only |
| `worktree-agent-a3b616ad6dc60a313` | 8 | measurement-meaning audit (FRAME/SUBJECT/CLAIM/COMPARABILITY) |
| `worktree-agent-a0c804088cff5d4f9` | 20 | `record.CLAIMS` — every fact carries what KIND of claim, DERIVED not stored, records byte-identical |
| `claude/unnamed-staves-alignment` | 3 | the string-block measurement above; `tools/` empty diff |

**One agent still running**: the brakes audit (§1), briefed with Sean's
yardstick.

## 4. WHAT SEAN DECIDED

1. Every fact carries what kind of claim it makes — **built** (derived, so no
   record changes).
2. Records stamp their SETTINGS, not just their tree — **built**; the first
   stamp caught `OMR_SURYA_KEEP_ALIVE=1` in force during the session's own
   gather, unknown to its author.
3. Unidentified staves are **held out**: *"I want truth"*.
4. Rename the misleading `FRAME` question; make `reach --check` enforce what
   its docstring promises — **both done, the second proven to fire.**

## 5. WHAT IS NOT ESTABLISHED

**There is still no cleanup count** — Sean judged the output too far off to
itemise, which is the instrument working. n = 1 document, 1 publisher, 4 pages
of ~16, the pessimistic low-res bitonal Litolff. No OMR-NED, no accuracy claim
on any note. The string rule is measured and **not shipped**. The 4-5 window's
real job — refusing a block of 1-2 — is untested, because this plate never
prints one.

⚠️ **A reading of the file against the reference was attempted and produced a
FALSE finding within minutes** (it reported zero key signatures; there are 36)
— the fragment parts break a measure-range assumption. Any such comparison
needs the hand-verified staff→parts map, not a naive diff.

## 6. GOTCHAS PAID FOR TODAY

* **zsh does not word-split an unquoted `$var`** — it turned eight passing
  derived checks into a believable ALL-RED.
* **`| tail` swallows an exit code** — it reported success for a pytest run
  that never started. Capture with an explicit `echo $?`.
* **`_provenance()` reads git at the END of a run**, so an untracked benchmark
  file written mid-run stamps the record dirty.
* **A stale CLAUDE.md row cost a killed 15-minute gather**: `OMR_INK` went
  default-ON and EIGHT ledgers still said OFF. Now derived-checked.
