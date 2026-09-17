# `local_arm.sh` on the ABSTAINING document — Litolff Beethoven 5 mvt 1, pdf p1-3

**Measured 2026-09-16 by session `meter-pricing-abstaining-a5daee`**, 34 min,
exit 0, tree `916cfcb6`, `tools/` verified byte-identical across both arms.
**Written up here by a different session** (`reengrave-duration-reader-191f40`)
because the measuring session ended before it could commit, leaving the result
in two transcripts and a worktree. ⚠️ **Provenance matters more than usual
here: I did not take these measurements.** What I checked myself is marked
VERIFIED; everything else is RELAYED from that session's own report and should
be treated as its claim, not as a second reading.

⚠️⚠️ **THE TWO EXPORTS IN THIS DIRECTORY ARE MISNAMED `brahms1-*` AND HOLD A
LITOLFF RUN.** The arm's output name is fixed by the script, not by the
document, so `brahms1-OFF.musicxml` / `brahms1-ON.musicxml` are **Beethoven 5 /
Litolff p1-3** — their own `<part-name>` elements read `Staff p2-s0-*`. They
are kept under the name the arm gave them so nothing that reads them breaks.
**Do not infer the document from the filename in this directory.** The
sibling `RUN_2026-09-16_brahms1.md` really is Brahms.

⚠️ The two `.json` records (**82 MB + 83 MB**) are deliberately NOT committed,
following `benchmarks/omr-shared-records-2026-09/`: record machine-local,
everything derived committed. The two `.musicxml` exports ARE committed — ~1 MB
— because they are what makes the `<time>` claim below checkable without them.

---

## The question this answers

PR #39's body names its own open question: *"It does not price the flip. A
2-system fixture says nothing about a misread propagating across a movement;
that is still `local_arm.sh`'s question."* This is that arm, on the document
that ABSTAINS.

## The numbers

**RELAYED** unless marked:

```
OFF  systems=5  decided=1  {'voted':1, 'no_evidence':2, 'too_few_staves_read_it':2}
ON   systems=5  decided=5  {'voted':1, 'carried':4}    support +6.0 +13.0 +9.0 +18.0
```

| | OFF | ON |
|---|--:|--:|
| systems decided | 1 of 5 | **5 of 5** |
| `<time>` elements — **VERIFIED** | **28** | **54** |
| …all `2/4` in both — **VERIFIED** | 28 × `2/4` | 54 × `2/4` |
| bars that add up, **like-for-like** over the 1,109 bars present in BOTH arms | 54.4% | **81.2%** |

**298 wrong → exact, 0 exact → wrong.**

⚠️⚠️ **DO NOT QUOTE 90.8%.** The raw figure is 90.8% and it is an artefact:
it includes **1,159 tacet bars the ON arm adds**, which are exact BY
CONSTRUCTION. The like-for-like 54.4% → 81.2% is the honest pair, and the
measuring session flagged this against its own result before anyone asked.

⚠️ **`carry sources SKIPPED = 0` in both arms, and the two zeros are NOT the
same fact.** OFF's is **structural** — the field is `None` and the function
returns before populating it. ON's is a **genuine `[]`**. Only the second is
evidence, and it says **A-METER-6's reach is zero here — second document
running.**

**VERIFIED independently by the writing session**, from the committed exports
rather than from the report: `brahms1-OFF.musicxml` carries 28 `<time>`
elements, all `<beats>2</beats>` / `<beat-type>4</beat-type>`;
`brahms1-ON.musicxml` carries 54, likewise all `2/4`. **The ON arm adds 26
declarations and changes no meter.**

## The suppressed misreads — two of them

```
system/2/1   too_few_staves_read_it   coverage 0.455   5/11 staves   would_have_been = C
system/3/0   too_few_staves_read_it   coverage 0.364   4/11 staves   would_have_been = 4/4
```

Both are **4.0 quarters on a 2/4 document** — *length* misreads, the arbitrable
kind. So **Litolff p1-3 abstains AND holds misreads.** But every exported meter
is still the correct `2/4`, and the reason is the mechanism rather than the
music: **the misreads are SUPPRESSED by the coverage gate before the carry
runs, so the carry is never handed one.** That distinction is the whole value
of this run — *"the carry handled it"* and *"the carry never saw it"* produce
the same file.

---

## ⚠️⚠️ THE THREE SHAPES, AND THE CELL THAT IS STILL EMPTY

The most transferable thing either session produced today, and it exists
nowhere else:

| shape | document | what happens |
|---|---|---|
| misread **VOTED**, a neighbour abstains | Brahms `p0p3` | hazard present — but **2 systems, no propagation** |
| abstains, misreads **SUPPRESSED** | **Litolff p1-3 (this run)** | carry runs across a real movement and propagates **only the correct meter** |
| **a VOTED misread propagating across many systems** | **— none —** | ⚠️ **the cell neither document fills** |

**So `local_arm.sh`'s question is ANSWERED for the suppressed-misread shape and
OPEN for the voted one. It is not closed.**

**The experiment that would close it, named by the measuring session:** run the
arm on `p0p3` — where `system/0/0` reads `C` at **`voted`** — with
**`--bar-beats 3.0`**. ⚠️ The old default of `2.0` is what made the
2026-09-16 Brahms run's *96.3% OVERFULL* meaningless; that default is now a
required argument precisely so this cannot recur.

---

## What is NOT established

* **These are one session's measurements and this is another session's
  write-up.** Only the `<time>` counts were re-derived here.
* **Nothing was checked against the print**, and no OMR-NED figure is claimed.
* **The flip is still not priced** — that is what the empty cell above means.
* The 1,109-bar like-for-like denominator is the part join's, and this repo
  already records that no bar-fill figure crosses documents comparably.
