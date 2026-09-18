# Handoff: the brakes, the unnamed staves, and five unmerged branches

**Nothing is merged.** Read §1 before touching anything: the session's own
headline is a FAILURE CLASS, and it caught this session's author twice.

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

## 3. FIVE UNMERGED BRANCHES

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
