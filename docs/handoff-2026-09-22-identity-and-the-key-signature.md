# Handoff, 2026-09-22 (evening) — the printing is gathered, and the key signature reads it

**Branch:** `claude/identity-conditions-key-signature-b510b3`, pushed. **Both
flags default ON**, the second by Sean's own call at the end of the session.

**Verified on the final tree:** full suite **4,833 passed / 12 skipped / 0
failed**; mutation battery **21 RED / 0 SURVIVED / 0 BAD ANCHORS**, restore
verified by md5; all eight derived checks exit 0 (`inventory`, `health`,
`wiring`, `gather_coverage`, `reach`, `capture`, `brakes`, `no_producer`);
`verify_findings.py` exit 0. ⚠️ **One commit on this branch shipped a
mutation-battery arm to the remote and was reverted — §7 item 10, and it is
the thing to read first if you are about to run a battery.**

**Read first:**
[benchmarks/omr-document-identity-2026-09/FINDINGS.md](../benchmarks/omr-document-identity-2026-09/FINDINGS.md).
Every figure in it is re-derived by `verify_findings.py`, which needs **no
weights, no score library and no PDF** — so a cloud session can check the
write-up without reproducing it.

The work order this executes is
[docs/NEXT-2026-09-22-identity-conditions-the-key-signature.md](NEXT-2026-09-22-identity-conditions-the-key-signature.md),
now stamped DONE at its head. ⚠️ **Read that brief only as history: two of its
own claims are refuted below.**

---

## 1. ⚠️⚠️ SEAN'S OFF-HAND GUESS WAS RIGHT AND THE BRIEF'S WARNING WAS WRONG

The brief called the catalog's `image_type` *"almost certainly wrong about the
engraved population"* because it reads `Typeset` on only 7 of 289. Sean's
reaction, in passing: *"Or maybe they are all scans because they came from
IMSLP..."*

**Measured over all 289 committed editions, every PDF on disk, 16 s, no
weights** (`classify_library.py`):

| IMSLP `image_type` | MEASURED verdict | n |
|---|---|--:|
| `Normal Scan` | scanned | **272** |
| `Typeset` | engraved | **7** |
| *(absent)* | scanned | 7 |
| *(absent)* | engraved | 3 |

**Wherever the label exists the two agree 279 of 279 — zero disagreements.**
The seven typesets are modern re-engravings (Snortum 2024, Renioult 2025,
Shaw 2024, NielsenComplete 1998, Wolfson, Chang 2019, a 2016 *Boléro*), which
is exactly what the word means on IMSLP; the three unlabelled engraved files
are `--local.pdf` and not IMSLP downloads at all. **The label's failing is
ABSENCE, not error.**

> **A warning written from a number's SHAPE — "seven, that can't be right" —
> against a guess from knowing where the files came from. The guess won, and
> it cost 16 seconds to settle.**

## 2. ⚠️⚠️ BUT THE REASON TO KEY ON THE MEASUREMENT IS STRUCTURAL, AND STRONGER

The engraved fixture the entire key-signature failure is proven on is a
**Verovio render** — a build product under `benchmarks/`, in no catalog. So
`edition_for_pdf` returns `{}`, `gather_document_identity` **ABSTAINS
`not_in_catalog`** on it, and the container reader answers `engraved` (raster
coverage **0.000**, **1188-1655** drawings, 3 pages of 3). Read off the real
record:

```
Q.INPUT_DOMAIN       observed 1  abstained 0  value ['engraved']
Q.DOCUMENT_IDENTITY  observed 0  abstained 1  ['not_in_catalog']
```

**A domain filed as a FIELD of the catalog row would have had a reach of ZERO
on the one input where the rule it conditions is proven.** That is why they
are two quantities — a measurement, not a taxonomy preference — and it is what
`test_the_catalog_is_SILENT_where_the_container_ANSWERS` pins.

## 3. WHAT LANDED

| piece | state |
|---|---|
| `gather_document_identity` carries `publisher_year`, `plate`, `has_text_layer` | NEW — Sean asked for the year by name |
| `OMR_DOCUMENT_IDENTITY` | **default ON**, deny-list (was OFF, allow-list) |
| `gather_input_domain` → `Q.INPUT_DOMAIN` | NEW producer, `source_kind: "container"`, `READERS.CONTAINER` |
| `ABSTAIN.NO_DOMAIN_SIGNAL` | NEW word — neither raster-dominant nor drawing-rich |
| `adjudicate_key_signature`'s engraved tier | NEW, `OMR_ENGRAVED_KEYSIG`, **default ON**, deny-list |
| `positional_store._edition_projection` | unified — two lookups had hand-listed one tuple twice |

⚠️⚠️ **`Q.INPUT_DOMAIN` WAS ALREADY DECLARED AND ALREADY CLAIM-CLASSIFIED**,
produced by nothing and reported a GHOST by `reach --check` every run.
`OMR_WEIGHT_ROUTING` has classified every document since 2026-09-03 and the
staged path never wrote the answer down. **This session reached the same
design independently and then declared the quantity a SECOND time**; the
derived checks caught the duplicate. The brief's *"roughly half of it already
exists"* was true of **more than its own table named** — `ls benchmarks/` is
not enough, **`grep Q\.` the vocabulary too.**

**`source_kind: "container"` is a FOURTH kind**, named deliberately: not
`catalog` (no external authority speaks), not `encoding`, and emphatically not
`page` — *an OMR output of the same raster*, refused as a second witness
because it falls silent exactly when the reading it would arbitrate does. This
counts vector drawing operations against raster coverage, so **a bad scan is
still unambiguously a raster**: `catalog`'s independence from print quality
without `catalog`'s dependence on the file having been catalogued.

## 4. THE RESULT — one gather, adjudicated twice

Engraved fixture, 3 pages, 18 parts, **54 staff-systems, 50 decided**. The
canonical `readjudicate --control` reproduces **688 of 688** duration verdicts
on that record first. ⚠️ Worth noting against the shared scan records, which
**no longer** reproduce (CLAUDE.md records 2,760 of 2,993, seven commits of
`rhythm.py` since): a record gathered on the tree you are measuring does.

| | right | wrong |
|---|--:|--:|
| **OFF** — the shipped precedence | **26** | **24** |
| **ON** — the engraved tier | **47** | **3** |

⚠️⚠️ **IT REPRODUCES THE 09-22 HANDOFF'S §1 TABLE FROM A FRESH GATHER, A
DIFFERENT TREE AND A DIFFERENT SCORER** — split by reason the OFF arm reads
`fitted_by_template` **20 / 0** and `fitted` **6 / 24**, to the unit. **The
template is 67 of 67 right wherever it speaks**, over-counting nowhere.

⚠️ **The 3 still wrong are template SILENCES, not errors** (all read `fitted`:
no template fit for that staff's settled clef, so the tier fell through).
⚠️ **And it is not "always answer −3"** — B♭ clarinets at −1 and E♭ horns at 0
are right in both arms.

**In the file**: bars exact **313 → 322 of 360**, **4 parts better and 0
worse**, `<alter>` **44 → 67** of a truth 100, `<fifths> -3` landing on the
truth's **14**. **CONTROL: of 29 quantities exactly 2 move** — `key_signature`
and its downstream `accidental`.

⚠️⚠️ **THE RESIDUE IS NO LONGER THE KEY, AND THAT NAMES THE NEXT JOB.**
`same count, differs ONLY by an accidental` is **43 of 47** disagreements in
the OFF arm (the earlier lane's 91%, reproduced) and the tier takes it to
**34**. Of the 38 bars still not exact, only **8** are on the two parts with a
wrong key; **30 are on parts whose key is now CORRECT** — the worst being
`Bassoon 1` at 12 of 20, whose key is right in both arms and whose count does
not move. **That is the IN-BAR accidental, which reaches no quantity at all.**

## 5. THE FLIP — what it rests on, and what it does NOT

Sean, at the end of the session: *"flip OMR_ENGRAVED_KEYSIG on by default."*
Done, with the OFF test converted to a **deny-list** per *A flag's OFF test
must follow its DEFAULT*.

⚠️⚠️ **IT RESOLVES NONE OF THE LIMITS IN §6 AND DOES NOT PRETEND TO.** n is
still 1 engraved document, 1 renderer, 24 bars, and **no print has been
consulted**. What it rests on is that the rule is **ONE-SIDED**: a scan, a
classifier abstention, a record with no identity row, and the flag off all
keep the shipped precedence exactly.

**Verified at the flip rather than asserted**: `test_keysig_second_reader.py`,
whose fixtures file no `Q.INPUT_DOMAIN` row, passes **unmodified**. So every
record gathered before this rung existed, and every run with
`OMR_DOCUMENT_IDENTITY=0`, is untouched.

⚠️ **The two flags interact in the safe direction**: the domain row is written
by `OMR_DOCUMENT_IDENTITY`, so switching that off leaves the tier with nothing
to read and it falls through. There is no combination in which the tier acts
on a domain nobody measured.

**The scan side is proved a no-op on a real gather** (`scan_is_untouched.py`):
`OFF == ON`, with a **forged-`engraved` control that moves all 12 verdicts** —
so the tier is silent there because the DOMAIN GATE stops it, not because the
template has nothing to say. ⚠️ That last clause is the reason the gate must
stay: on that page the template WOULD speak on every staff, and whether it
would be right is exactly what is unmeasured.

## 6. WHAT IS NOT ESTABLISHED, AND THE RANKED NEXT WORK

- **n = 1 engraved document, 1 renderer, 24 bars.** A render is not a scan and
  not a publisher's engraving.
- **No print was consulted.** The truth is the encoding's `<key><fifths>` on a
  render where the ordinal join is true by construction. No crop was cut.
- **The scan side is not measured for accuracy** — only shown to be a no-op.
- **Nothing reads `Q.DOCUMENT_IDENTITY`.** Publisher, year and plate are
  gathered and no decision consumes them; its `reach.KNOWN_GAPS` entry stays,
  corrected to say the flag is ON and the READ is what is open.
- **No OMR-NED**, deliberately: the metric is symmetric and pairs by pitch,
  and a key signature moves pitches wholesale.

**Ranked:**

1. ⚠️ **A SECOND ENGRAVED DOCUMENT**, and it is now a one-line query rather
   than a hunt: `out/library-domains.json` names the **10 held editions the
   container reader measures engraved**. That is the cheapest thing that moves
   the n.
2. **The IN-BAR accidental** — §4's residue, 30 bars on correct-key parts and
   33 missing `<alter>`. Scoped in `docs/symbol-dossiers/accidentals-keys.md`
   and blocked on a record-shape decision (*the record has nowhere to put a
   span*) that is Sean's.
3. **The alternative shape the brief names and this lane did NOT measure**:
   lowering `key_signature_locator.min_height_spaces` for engraved input.
   Its ceiling is higher — it could reach the 3 staves the template is silent
   on — and it is a GATHER change, so every arm costs a full re-gather. ⚠️ The
   floor is shared with the scan path, where the erasure is what makes the
   locator work at all, so it needs the same one-sided gating. **That gating
   is now cheap, because the domain is on the record.**
4. **A consumer for `Q.DOCUMENT_IDENTITY`.** The conditioning variable Sean
   asked for is gathered and read by nothing.

## 7. ⚠️ THIS SESSION'S OWN FAILURES

1. ⚠️⚠️ **THE ACCURACY TABLE REPORTED A CLEAN 0 RIGHT / 0 WRONG ON BOTH ARMS.**
   `str(Outcome.DECIDED)` is `'Outcome.DECIDED'` on this Python, so an
   `== "decided"` test could never be true. A believable zero from a
   comparison that cannot fire. The scorer now REFUSES a run in which it
   scored nothing.
2. ⚠️⚠️ **THE DERIVED-CHECK CONTROL MEASURED THE SHELL.** `for t in
   "staged.capture --check"; do python3 -m tools.omr.$t` — **zsh does not
   word-split an unquoted parameter**, so every check ran as a module name
   containing a space and returned 1 **on both trees**, which reads exactly
   like eight legitimate pre-existing failures. `${=t}` gives the truth: all
   eight pass on both. CLAUDE.md already records this trap for `env $3`.
3. **The new test file skipped 5 of 18 assertions silently** — `REPO` computed
   with three `dirname`s where the file sits four levels down. **A skip is the
   one outcome that looks like a pass**; the path is asserted at import now.
4. **A bad anchor, twice.** The catalog projection appears **twice** in
   `positional_store.py`. Repaired by writing it ONCE, which is also what
   makes the new fields reach both lookups.
5. **A shared helper defeated a derived check.** Factoring the two template
   returns into one function taking the reason word as a PARAMETER made
   `brakes --check` report both reasons UNRESOLVED — the trade INFER refused.
   The lookup is shared; the literal reasons stay at their call sites.
6. ⚠️⚠️ **THE BATTERY TOOK FIVE RUNS TO BECOME ONE**, and two of its survivors
   were **the battery itself**: `if target == "arm"` selected the judge by
   NAME, so a second instrument under the same directory fell through to a
   judge that could not see it. **A selector that silently stops matching
   blames the thing it was pointed at** — the BAD ANCHOR family one level up.
   Sequence: 15/3 → 15/5 → 19/1 → 20/0 → (flag arm added) 21 arms.
7. ⚠️⚠️ **THREE CONTROLS COULD NOT FAIL, AND THE FIRST REPAIR WAS HALF RIGHT.**
   Adding the scan record fixed the DEAD branch and **not** the ordinal-join
   refusal, because the scan run exits DEAD *before* the scorer — that needed a
   five-part stub that does not divide 54. And the last survivor was
   **second-order**: `return 0 if (same and moved)` only does anything once the
   FORGING breaks, so it needed `--no-forge`, a flag that breaks the forge
   deliberately.

   > **A control can only be mutation-tested in a state where it FAILS; "add a
   > second fixture" is not automatically that state; and a guard whose
   > failing state is another guard's failure needs the COMPOSITION, not a
   > fixture.**
8. ⚠️ **A `tools/` FILE WAS EDITED WHILE THE BATTERY HELD A SNAPSHOT** and was
   silently restored away at the next arm. Recovered from a copy taken
   immediately after writing it, with all anchors re-checked. **The failure is
   silent: `git status` showed the file clean, because the battery had put back
   exactly what git had.**
9. ⚠️ **THE `origin/main` CONTROL TREE WAS BUILT WITH `git archive` AND IS NOT
   A CHECKOUT.** Its full suite reports 6 failures, all environmental (five
   `label_contradiction` artefact tests and one that cannot pass outside a git
   repository). It was a sound control for the DERIVED CHECKS — verified
   individually on both trees — and **not** for the suite. Do not quote its 6
   as *"main is failing six tests"*.

10. ⚠️⚠️⚠️ **I COMMITTED AND PUSHED A MUTATION-BATTERY ARM.** Running
    `git add -A && git commit && git push` while the battery was live captured
    `header.py` mid-arm, carrying *"the precedence is flipped GLOBALLY, not
    one-sided"* — `if True:` in place of `if _proved_engraved(ev):`. **What
    went to the remote was the key-signature tier preferring the template on
    EVERY document, scans included** — the exact behaviour this lane's design
    refuses and which is unmeasured for accuracy there.

    **It is silent in both directions.** The commit looks clean, because
    committing reads the working tree and the working tree was the battery's
    at that instant. Then the battery restores from its own snapshot, so
    afterwards `git status` shows **one modified file that looks like an
    ordinary edit** — I nearly read it as one.

    **What caught it** was checking `git status` against the battery's
    *"restore VERIFIED by md5"*: the battery had verified its restore, so a
    dirty file could only mean the COMMIT was wrong, not the restore. Scope
    then checked rather than assumed — `git log -S "    if True:"` names
    exactly one commit, nothing else differs from HEAD, and the restored file
    is byte-identical to the flip commit. **Reverted in `c97b6f5f`,
    and the guards were verified against the pushed blob rather than trusted:
    6 tests fail on it**, including `test_the_LOCATOR_wins_where_both_speak`
    and `test_a_SCAN_is_UNCHANGED`, and the battery's own arm for that
    mutation was RED in the very run that produced it.

    > **CLAUDE.md says *do not EDIT `tools/` while a suite is running*. The
    > clause it did not have: DO NOT COMMIT EITHER. A battery owns the working
    > tree while it runs, and `git add -A` is a read of the working tree.**

11. ⚠️ **I HANDED A PEER A PATCH AGAINST A BRANCH SNAPSHOT AND DID NOT NAME
    THE SHA.** The doc entries for roadmap 2.2 were diffed against
    `origin/claude/build-process-system-design-e8d64a` **as I had fetched it**
    (`2b441cb3`); that branch had moved to `964a9598` by the time the patch
    arrived, and the newer commit touched **all three** of the files the patch
    covers (ROADMAP −1/+1, DECISIONS +6, flags +1). **Applied whole it would
    have reverted a roadmap line, a decision and a flag row.** The peer caught
    it and took the additive parts by hand.

    ⚠️ The message did say *"diffed against
    `origin/claude/build-process-system-design-e8d64a`"* — **which is the
    error, not the mitigation**: that names a BRANCH, and a branch is a moving
    reference. It is this repo's own recorded shape, in a new place —
    *"`tree clean at <sha>` is a claim about a BRANCH and not about main"* —
    and the fix is the same one: **name the SHA, and re-fetch immediately
    before generating a cross-branch patch.**

## 8. OPERATIONAL

- ⚠️ **`timeout` does not exist on macOS.** It exits 127 and the command never
  runs.
- ⚠️ **`pgrep -f <pattern>` matches the waiting shell that contains the
  pattern**, so an `until ! pgrep -f ...` loop can never exit. Wait on a PID.
- **Gather costs, measured**: the engraved 3-page fixture **~4 min**, a 1-page
  600-dpi Litolff scan **~2 min** — so the brief's *"budget 1-2 hours"* was
  pessimistic and both arms were re-gathered rather than injected.
- **Another session's mutation batteries were running in a different
  worktree** throughout. Separate working trees, so no collision — but real
  CPU contention, and a battery here took ~35-45 min rather than ~20.
