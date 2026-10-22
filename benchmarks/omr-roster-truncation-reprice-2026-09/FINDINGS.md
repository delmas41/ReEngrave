# The truncated margin label, re-priced — and the brief's premise REFUTED

**2026-09-22, Lane C.** The 2026-09-21 fact-sheet handoff ranked this second,
on the strength of a *"second, independent instance"* of truncation found on
the primary Breitkopf document. **Measured: that instance is not a truncation,
and the rule fires ZERO times on all 209 Brahms margin labels.** Nothing was
flipped; no default changed. `tools/` changes are a docstring and two tests.

⚠️ **PROVENANCE.** The harness blocks subagents from writing `.md` report files
— the **eighth** time in this repo. This is the measuring session's own report
transposed at integration; `[mgr]` marks a managing-session check.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

**ASSUMED** — an engraver labels a **braced PAIR** of like instruments **once**
and distinguishes the members by their transposing KEY, so a staff carrying a
key and no noun is printed that way **by design, not by damage**.

**WHAT WOULD FALSIFY IT** — a Brahms 1 plate where the two horn staves carry
two different instruments, or where the parenthesised key belongs to the
staff's own name rather than to a pair. **One crop of p0/p1 settles it, and it
was not cut.**

**NOT CONFIRMED WITH SEAN.**

---

## 0. [mgr] Checked against the tree

| claim | check | result |
|---|---|---|
| the staged path calls `decide` UNGATED | `grep` `identity.py` | **CONFIRMED** — `WR.decide(...)` at `:96`, no `enabled()` anywhere in the file |
| `enabled()` has one non-test caller | `grep -rn "work_roster.enabled()" tools/` | **CONFIRMED** — `contextual.py:629`, the legacy reader, and nothing else |
| the lane changed no behaviour | `git diff -- tools/omr/work_roster.py` | **docstring only**; the predicate is byte-identical |

## 1. THE HEADLINE — the brief's premise 3 is refuted, and my brief carried it

`recover_truncated` accepts a token only where it is a proper **SUFFIX of a
roster alias**, keeping ≥3 letters and ≥half the alias. The survivors the
handoff names carry **no instrument tail at all**: `'(C)'` → `c`, `'(Es)'` →
`es`, `'(E)'` → `e`, `'in C \frac{1}{2}'` → `in`, `c`. **Every token is under
three letters, so none reaches the suffix test.** ⚠️ **No threshold makes it
reachable**: admitting two-letter tails admits `es`, `in`, `ni`, `hr` and every
other syllable.

And the other half of the sentence fails too — **every Brahms label that
carries the noun already resolves**: `'Hr.'`, `'(C) Hr.'`, `'Hr. (E)'`,
`'Hr. (Es)'`, `'Hr. 1. (C) 2.'`, `'(E) Hr.'`, `'(F) Hr.'`, `'. (C) Hr.'`,
`'(C) Hr'`, `'Hr.1. (Es)2.'` — **ten distinct spellings, all → Horn.**

⚠️⚠️ **CLAUDE.md ALREADY DIAGNOSED THIS, IN TERMS**, in its lexicon section:
*"the page prints `Hörner` once braced across them, so abstaining is right and
**no lexicon can recover them**."* Brahms 1 sets **four horns on two staves** —
1 & 2 in C, 3 & 4 in E♭ — which is exactly what `in C 1/2` and `in Es 3/4`
**say**. **It is a braced-pair label, not a truncation.** The handoff re-found
the symptom and attributed it to the wrong mechanism; **so did the brief built
on it.**

## 2. The published figures reproduce; one drift, proved rather than guessed

`probe_roster_reach.py` unmodified: readers **17 recovered / 3 disambiguated /
0 vetoed = 20**; fixtures 5/2/1 = **8**; reference 0. **28 firings, label for
label.**

⚠️ Labels-with-a-roster read **1,255** against the published **1,251**. Diffing
`catalog.json` across `83fcfce4` shows the `bach-wtc1` edition (exactly 4
labels) **absent before, present after** — editions 235 → 289. **The published
figure is stale by exactly the catalog-gap lane, not wrong**, and the `works`
tier is unchanged at 223, which is why nothing else moved.

## 3. ⚠️⚠️ ON REAL PAGES NOT ONE RECOVERY IS A TRUNCATION

| source | firings | what they are |
|---|--:|---|
| `ravel-bolero-textlayer` | **17 recovered** | `V elles`, `V^{\text{elles}}` … → **Cello**, every one |
| `beethoven5-575951` / `-984073` | **3 disambiguated** | `Basso.` → Contrabass |
| everything else | **0** | — |

The real-corpus recovery half is **one instrument on one document**, and it is
**a superscript, not a cut**: `Violoncelles` recovered via the alias `vcelles`
(0.714 kept), not `violoncelles` (0.417, under the floor). The
`larinetti` / `orni` / `mpani` / `mbone Basso` cases exist **only on the
engraved fixtures**, which `omr-margin-window-truncation-2026-09` §4 already
proved is a LilyPond `indent` artefact with **zero real-world exposure** (289
editions, 141 pages of margin text, **0 spans at the sheet edge**).

## 4. ⚠️⚠️ THE FLAG GOVERNS THE LEGACY PATH ONLY — the INVERSE of this repo's usual direction

```
grep -rn "work_roster.enabled" --include='*.py' tools/    # minus tests
tools/omr/contextual.py:629:    if not work_roster.enabled() or not labels:
```

**One non-test caller, the legacy reader.** `staged/adjudicators/identity.
adjudicate_instrument` calls `WR.decide(...)` **with no reference to the flag**;
what gates it there is a `Q.ROSTER_ENTRY` row, and **the staged CLI supplies
one BY DEFAULT** (`--no-roster` turns it off). Verified: `roster_for_pdf`
returns a **complete** roster today for Brahms 1 (9 instruments), Beethoven 5
(10) and Boléro (17).

⚠️⚠️ **That is the INVERSE of the symbol-dossier sweep's *"shipped means the
LEGACY path"*, so a reader who assumes the usual direction gets it backwards in
BOTH halves.**

⚠️ **It has nonetheless never acted on the artefacts every lane measures on**:
the shared Brahms record carries, once per page,
`{"quantity":"roster_entry","reason":"out_of_scope","note":"no work id / roster
supplied"}`. **Structurally live, practically dormant — the state in which
nobody notices a default.** The route to a file effect is real:
`_names_by_system` / `_reference_names` read `Q.INSTRUMENT` and feed
`adjudicate_slot_index`'s `paired_by_name` — **the part join.**

**Documentation defect**: CLAUDE.md's knobs row called it *"Measured,
deliberately dormant"* — **false on the staged path**. `enabled()`'s docstring
said only *"Default OFF"*. **Both corrected**, and the scope is pinned by two
derived tests (`test_the_flag_governs_the_legacy_path_only` and
`test_the_staged_identity_decision_is_ungated`, the latter failing both if
`decide` leaves **and** if a gate appears).

## 5. The cost side, which the prior lane never measured

- **It changes no right answer, structurally.** 968 of 1,422 labels are
  `resolved_already` and **none is touched**; **0 vetoes** fire on the whole
  reader corpus.
- **The false-positive surface is BYTE-IDENTICAL.** 1,651 strings × 223 rosters
  = **368,173 decisions**: 19,995 / 1,911 / 1,553, **1,141 distinct claims, 0
  new, 0 gone.**
- **The veto's worst case still cannot fire**: 37 vocal-looking, 38 admitting,
  **1 flag** (Boléro, which has no singers) — identical to committed.
- **No OMR-NED claimed, deliberately** — musicdiff does not score
  `<part-name>` (measured previously at 0 edits for 15 rewritten names).

## 6. What WOULD reach it — one candidate, one refusal

The real class is a **BARE KEY**: the lexicon abstains, `parse_in_key`
*succeeds*, and no token survives the roster floors. **15 of 1,422 (1.1%), 6
distinct, on two documents.**

**(A) SLOT CARRY — survives.** `contextual.py:1527` already stamps one name per
**SLOT** onto every staff of that slot on every page. ⚠️ **The staged path has
no equivalent**: `adjudicate_instrument` is `Kind.STAFF` reading
`Q.MARGIN_LABEL` at default `Scope.EXACT`, so a bare-key staff abstains
`not_in_lexicon` and nothing carries a name to it. **A sixth instance of
"shipped means the LEGACY path", in the same file as the inverted flag.** Not
built; per-slot reach unmeasured, because the dump numbers staves across the
PAGE rather than per system.

**(B) ADJACENCY — ⚠️⚠️ REFUSED, 0 of 4, and wrong where it looks safest.**
SPLIT 11, "unanimous" 4 — **and all four are wrong**:

| page/staff | label | adjacency says | truth |
|---|---|---|---|
| p0 s5 | `in C \frac{1}{2}` | **Contrabassoon** | Horn 1–2 in C |
| p0 s6 | `in Es \frac{3}{4}` | **Trumpet** | Horn 3–4 in E♭ |
| p1 s5 | `(C)` | **Contrabassoon** | Horn 1–2 in C |
| p1 s6 | `(Es)` | **Trumpet** | Horn 3–4 in E♭ |

⚠️ **The mechanism is general**: adjacency fails precisely when **both** members
of the pair are bare, because then neither neighbour is a horn — they are the
instruments *above and below the pair*. **A rule that abstains on 11 and is
confidently wrong on 4 is worse than one that abstains on 15.**

## 7. RECOMMENDATION — a refusal with numbers; the call is Sean's

**Do not flip `OMR_ROSTER_LABELS`, and stop treating the flag as the
question.** Its whole legacy reach is 20 labels (17 Boléro cellos, 3 `Basso.`);
the truncation it is named for has zero real-world exposure; and on the staged
path — the one producing cleanup artefacts — it **already runs ungated**, so a
flip changes only the legacy reader.

Ranked instead: **(1)** correct the documentation (done); **(2)** the
cross-system **slot carry** on the staged path, measuring per-slot reach on a
staged record first; **(3)** **do not build adjacency.**

> **What would have to be true for this to be wrong:** that some held edition
> truncates instrument nouns at the left margin. The 289-edition control says
> none does — but it measures **text-layer spans on p1–p3 only**, so an edition
> truncating on later pages, or one with no text layer where Surya's crop clips
> the noun (**which has happened**: `Clarinetti` → `arinetti`), would not be in
> it. One run of `probe_edge_separation.py --library` over all pages settles it.

## 8. What is NOT established

**No print was consulted** — §6B's truth column is the weakest claim here and
one crop settles it. No staged run, no export, no file effect, no OMR-NED.
⚠️ §4's *"staged is live"* is **structural (source + roster lookup), not
observed in a record.** n = 13 editions / 1,422 labels / 2 documents for the
bare-key class. The 28 existing firings were **reproduced, not re-adjudicated
against a print.** Mahler 5 has no catalogued roster, so its one bare-key row
is outside the layer entirely.
