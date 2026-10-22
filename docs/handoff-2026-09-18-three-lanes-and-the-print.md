# Handoff: the print arrived, and it settled a SHIPPED default against itself

**START HERE.** One branch, **`claude/integration-2026-09-18`**, pushed. It is
`origin/main` plus **five** merged lineages and four integration commits of my
own. Three agents ran overnight in isolated worktrees; **one shipped code
(behind a default-OFF flag), two measured and refused.**

⚠️ **THE FIRST THING THIS SESSION FOUND WAS THAT THE WORK ITS HANDOFF DESCRIBED
WAS NOT IN THE TREE.** `docs/handoff-2026-09-17-the-ink-is-fused.md` names one
branch as PR #56 and does not mention that **two further stem branches were
also unmerged** — and one of them had already SHIPPED a tier for the very
quantity that handoff's §4a proposes building. **Merge before dispatching, and
`git branch -a | grep` the subject first.** §7 of the 09-16 handoff says the
same thing; it cost nothing here only because it was checked.

**Section 3 is the part you must read before quoting anything. Section 4 is
what is waiting for Sean, and it is four decisions, not one.**

---

## 1. WHAT LANDED, AND WHAT EACH LANE CONCLUDED

| lane | outcome | the number |
|---|---|---|
| **§4b the STROKE** — a within-blob column-profile reader | **SHIPPED, `OMR_STEM_STROKE`, default OFF** | falsification did NOT fire: **92.1% / 73.6%** of `too WIDE` components hold a separable band |
| **§6 the CROP PASS** — the print, never done for stems | measured, nothing proposed | **16-0 against a shipped default**; **46 of 180 boxes are not noteheads** |
| **§4a the ATTACHMENT convention** | **REFUSED as a tier** | marginal reach **371 / 483**, not the registry's 1,125 |
| my own | two CLAUDE.md errors corrected; three doc debts paid | — |

**Merged and verified**: both stem lineages, the ledger/stem-ink lineage (PR
#56), Sean's standing-rule doc (PR #55), and the three agent branches. Final
tree: **four derived checks exit 0**, flag guards 10 passed, and the full suite
is recorded at the foot of this document.

⚠️ **The merged tree is the one thing no agent runs**, and the control was run
before any conclusion: the four derived checks exit 0 **identically on
`origin/main`**, so nothing here is masking a pre-existing failure. (My first
reading of them said `exit=1` on all four — **zsh does not word-split an
unquoted variable**, the hazard this file already records, and it bit inside
ten minutes.)

⚠️ **THE CONTROL THAT PROTECTED EVERY OTHER INSTRUMENT**: the whole cell-cutting
and stem-reading path — `preprocessing`, `measure_extractor`, `staff_detector`,
`staff_line_removal`, `line_detection`, `types` — is **byte-identical to the
record's own commit (`9d4ccc85`)** on the merged tree, so every stem arm's
faithfulness assertion still holds. That is why `OMR_STEM_STROKE` being
flag-off-identical is load-bearing and not tidiness: `line_detection.py` is
**on that path**, and a flag-off that drifted would have broken the siblings'
controls and looked like *their* bug. **Asserted directly against both records:
1,920 = 1,920 on 1,183 of 1,183 cells, 2,305 = 2,305 on 818 of 818.**

---

## 2. ⚠️⚠️ THE HEADLINE: THE PRINT BROKE A STANDOFF 16-0 AGAINST A SHIPPED, DEFAULT-ON TIER

The attachment lane refused its tier partly because it could not tell which of
two mechanisms was wrong: *"The beam-mate's 0.984 is Litolff-only,
leave-one-out, and has NEVER been measured on Breitkopf. One of the two is
wrong 15% of the time and no instrument here can say which."*

The crop pass settled it. Of the 26 Breitkopf heads where the raster attachment
convention and the **shipped, default-on beam-mate tier** disagree:

| | n |
|---|--:|
| settled by the print | **16** |
| print agrees with the **ATTACHMENT** reader | **16** |
| print agrees with the **BEAM-MATE** tier | **0** |
| `cannot_tell` | 8 |
| **not a notehead** (both readers gave a direction to a DOT) | 2 |

⚠️ **The adjudication was genuinely BLIND** — opaque tile ids, the manifest
naming which reader said what not opened until every verdict was written — and
the split was **re-derived at integration** from
`ADJUDICATION-standoff.json`, not relayed.

⚠️ **It does not prove the tier is wrong**, and the lane says so against its own
result: **the adjudicating eye is not independent of the attachment reader** —
both measure ink beside the head. So this is properly *"the ink beside the head
behaves as the convention says"*. What makes it more than a count: **in 5 of the
16 the stem ends in a printed FLAG or runs into a BEAM** — the beam-mate's *own*
kind of evidence siding against it — which would put its error in its
**GROUPING** rather than in its convention. **Hypothesis, instances named.**

⚠️⚠️ **AND A SEPARATE LANE FOUND THE MECHANISM THAT WOULD EXPLAIN IT.** The
stroke lane's own crops: Breitkopf's AGREE stratum is 6 of 6 textbook, and its
DISAGREE stratum is **6 of 6 ONE FAULT — the record's notehead box stands
part-way ALONG a NEIGHBOURING note's stem**, so the stroke is real and the
**ATTRIBUTION** is wrong. Two lanes, two instruments, one conclusion, arrived at
independently. **The repair is in `adjudicate_stem_direction` and is the ranked
next work.**

---

## 3. ⚠️ WHAT IS NOT ESTABLISHED — READ THIS BEFORE QUOTING ANYTHING

* **`cannot_tell` is 62.5% for Litolff CONTROLS against 58.9% for its stemless
  SAMPLE — the same.** So *"the stemless heads are the illegible ones"* is
  **FALSE**, and on that plate **~60% of noteheads cannot have their stem
  adjudicated by eye whether we read them or not.** Every Litolff figure in
  this handoff carries that. Breitkopf: 12.5% / 17.8%.
  ⚠️ Litolff is **`bpc: 1`, genuinely BITONAL, and 600 dpi is EXACTLY its
  native resolution** — there is nothing better available, ever, for that plate.
* **One adjudicator. No inter-rater figure.** n = 2 publishers, 8 pages, the
  same two plates this thread has always used.
* **No OMR-NED figure anywhere**, deliberately — the metric is symmetric and
  would pay for emitting fewer stems.
* **No effect on a FILE has been measured by any lane.** `OMR_STEM_STROKE` is a
  GATHER change, so `readjudicate` and `reexport_arm` are structurally blind to
  it; the attachment convention would need a GATHER producer it does not have.
* ⚠️⚠️ **THE METHOD WARNING IS WORTH MORE THAN A NUMBER: at tile magnification
  the adjudicator read two heads WRONG and a wide strip corrected both** — a
  numeral and a dotted half note each read as *a hollow head with no stem*.
  **A crop centred on a head cannot tell you the head is a NUMERAL.** Any
  future crop pass here uses a full-width strip.
* **Why the stroke reader declines the 576 thin Breitkopf boxes is NOT
  DESIGNED** — it may be the edge filter, the height cap or the anchor
  tolerance. **12 of 576 is an observation, not a guarantee.**

### Three claims in the tree that these lanes CORRECTED

1. ⚠️⚠️ **The 8.1-space fused blob was ONE CELL and is now measured: over 2,001
   cells the median component is 4.18 / 3.20 staff spaces**, only 6% past the
   width cap, genuine merges across notes **9.6% / 12.0%**, and ~94% of the
   over-cap mass covers **no notehead at all**. So *"the ink is one blob"* is
   **true of the extreme and false of the median.** The diagnosis survives for a
   different reason: a component reader cannot separate a stem from the notehead
   it is **joined to**, whatever the distribution does. ⚠️ I had written the
   8.1 figure into CLAUDE.md the same morning with a one-cell caveat; **the
   caveat was right and the figure was not.**
2. ⚠️⚠️ **The registry's reach of "1,125 heads" was a DOUBLE COUNT.** Both
   shared records are **pre-tier**, so the published 472/653 still contain the
   heads the shipped tier now serves: overlap 101/170, honest marginal
   **371/483 = 854**. Overstated by 271 (24%). Corrected in place.
3. ⚠️⚠️ **The mixture model is WITHDRAWN BY ITS OWN AUTHOR, by a different
   lane's evidence.** The stroke lane first refused Litolff as
   *"indistinguishable from the 83.6% at which `width_cap_check.py` refused the
   width cap"*, reading both as ~73% real. The crop pass put those very
   recoveries to the print: **33 of 33 REAL, 0 junk** (95% lower bound 0.913).
   So ~83% there meant **~100% real**, the model is refuted, and the convention
   probe **understates** that plate. **Two lanes correcting each other across
   one night is the argument for running them together rather than in series.**

---

## 4. ⚠️⚠️ FOUR DECISIONS WAITING FOR SEAN — none was taken

Every default flip in this repo is his, and **nothing was flipped**.

1. **The beam-mate tier's DEFAULT.** It is default-ON and it just lost **16-0**
   on its first contact with a second publisher. ⚠️ Do not read that as
   *"turn it off"*: the honest reading is that its error looks like
   **ATTRIBUTION** (§2), in which case the repair is a fix and not a flip, and
   its 152-head reach was only ever worth **two `<voice>2</voice>` tags**.
2. **`OMR_STEM_STROKE`, default OFF.** It HOLDS on Breitkopf (96.2% against a
   98.2% bar) and is UNDETERMINED on Litolff. The only remaining objection is
   not quality: **581-1,074 extra strokes enter `detect_beams` and nothing
   prices them.** Two full re-gathers would settle it, and **beams feed
   duration**, which is the prize `A-DUR-8` names (12 assessable / 7 correct →
   **16 / 16**).
3. **The width cap `max_width_lines`.** Its recoveries are **33 of 33 real**.
   ⚠️ But the print settles only **33 of 55** and that subset is **by
   construction the legible one**, so the junk worry is removed and **the cap is
   still not priced.** ⚠️ And the published **217 is a Litolff figure — it
   recovers 345 on Breitkopf.**
4. **A box-width floor at < 1.0 staff spaces.** It catches **39 of the 46
   non-noteheads at a cost of 0 of 63 real stems** — measured and **not
   proposed**, because it is a GATHER change measured only on heads the census
   already abstains on.

**And three one-line questions the lanes put to him directly**: is our `Whole`
class trustworthy enough to refuse a stem on (31 heads, nobody has looked)?
Where a beam says one thing and the ink beside the head says another, which
does he trust? Is **854 heads of RECORD honesty with no expected file change**
worth a GATHER quantity at all?

---

## 5. RANKED NEXT WORK

1. **The ATTRIBUTION repair in `adjudicate_stem_direction`** — *a stroke belongs
   to the head at ONE OF ITS ENDS, not to every head it crosses.* Two
   independent lanes arrived at it, it is 6 of 6 on Breitkopf's disagreements,
   and it is where that plate's whole residual lives. ⚠️ It **cannot** be done
   in `detect_stems`, which emits STROKES and not (stroke, head) pairs — an
   end-at-the-head constraint there moved disagreements **40 → 40 and 14 → 14**,
   the **fifth dead hypothesis** on this thread.
2. **Two re-gathers with `OMR_STEM_STROKE` on**, to price the beam and duration
   effect. The only measurement that can say whether the reader is worth having.
3. **31 crops** for the whole-note contradiction (`V010` cheapest), and the 11
   Breitkopf heads §5 of that lane did not reach.
4. **A third publisher, for the DENOMINATOR rather than the tie.** ⚠️ The
   catalog does **not** answer this — it names only second *scans* of the same
   two publishers, while **Breitkopf 1862 Beethoven 5, Eulenburg 1938 Beethoven
   5 and Simrock 1877 Brahms 1 are on disk and in the catalog NOWHERE.**
   `docs/cloud-session-capabilities-2026-09-09.md` invites the same error. What
   needs a third plate is the **5.5% vs 37.7% non-notehead contamination**,
   which is a DETECTOR property differing **7×** between two editions.
5. **A y-cut for the `TALL` bucket** (476 Breitkopf heads) — out of reach of any
   column profile by construction. ⚠️ **But the crop pass found that bucket is
   12 of 12 BARLINES**, so measure what is in it before building a reader for it.

---

## 6. PROCESS, AND THE THINGS THAT COST TIME

* ⚠️⚠️ **SEAN ISSUED A STANDING INSTRUCTION ON 2026-09-18 AND THIS SESSION
  DISPATCHED WITHOUT IT.** `docs/ask-first-conventions.md` (PR #55, merged
  here): *before building anything, say how a HUMAN would read it off the page
  and what ENGRAVING CONVENTION governs it, and ask in one line.* Its unattended
  clause — **CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH
  SEAN** — applies to an overnight run, and it was sent to all three agents
  mid-flight. **Two of the three wrote the block; it should be in the brief, not
  a correction.** The substantive half was not procedural: the registry's 18
  stem/beam conventions handed the stroke reader its priors, including *a stem
  stands at the SIDE of its notehead* (a profile centred on the head looks in
  the wrong place) and the entry predicting that **an erosion tuned to open the
  beam gaps eats the strokes first.**
* ⚠️ **THE HARNESS REFUSED TWO OF THREE SUBAGENTS A FINDINGS FILE**, so their
  synthesis went into commit messages. This repo's own rule is that **a commit
  message is a LEDGER and the tree outranks a ledger**, and a benchmark
  directory with no `FINDINGS.md` is exactly where the next reader looks first.
  **I transposed both at integration**, with provenance stated so the commits
  stay primary. The third agent wrote its own, so the restriction is not
  universal — **check, and pay the debt if it bites.**
* ⚠️ **`CLAUDE.md` was held by the managing session alone** and the agents
  delivered proposed paragraphs. Four lanes touched it; **zero collisions.**
* ⚠️ **A new clause on the mutation-battery rule, paid for in a hand-debugged
  arm**: `shutil.copy2` **preserves mtime**, so a `.pyc` from one arm satisfies
  Python's `(mtime, size)` check in a later one, which then imports
  **UNMUTATED** code and reports **NOT RED** — indistinguishable from a test
  gap. `PYTHONDONTWRITEBYTECODE=1` took that battery from 10 RED / 2 survived to
  **12 / 0**. The rule now has three clauses; see CLAUDE.md.
* Two CLAUDE.md errors §7 of the previous handoff left for Sean are **corrected
  in place**: the system-grouping rule rested on *"a barline runs a system's
  full height and the bracket encloses exactly it"*, and **both halves are
  false on both publishers** (Litolff's interior barlines cross every gap **0 of
  68**) — ⚠️ **the rule itself is unchanged and still right**, because it is a
  one-sided veto that only needs a crossing column to be *evidence*; and
  `OMR_ARC_RECLASS` **contradicted itself for a week**, its headline carrying
  figures the same row further down calls stale.

---

## 7. THE INSTRUMENTS, AND WHAT EACH IS BLIND TO

| where | asks | blind to |
|---|---|---|
| `benchmarks/omr-stem-stroke-2026-09/` | can a column profile find a stroke inside a blob | the `TALL` bucket, by construction (x not y); any FILE effect |
| `benchmarks/omr-stem-crop-pass-2026-09/` | what does the PRINT show | not independent of the attachment reader; one adjudicator |
| `benchmarks/omr-stem-attachment-2026-09/` | marginal reach over the shipped tier | cannot say which reader is wrong — the print did that |
| `benchmarks/omr-stem-ink-2026-09/` | the rejection census (2 publishers, sums exactly) | a replication; asserts faithfulness per cell |

Every arm re-cuts the cells and proves the re-cut reproduces the record before
reporting a delta. `library/_shared-records/` holds both records; **the
Breitkopf one is 443 MB and `json.load` on it is several GB — stream it with
`recordstream.py`.**
