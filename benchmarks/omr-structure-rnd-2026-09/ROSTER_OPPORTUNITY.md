# H2 — is class (a) a wall for a PAGE, or for a DOCUMENT?

**2026-09-05. AN OPPORTUNITY COUNT, NOT A GAIN, AND NOT A FEATURE.** Nothing
under `tools/` or `backend/` is touched; no roster pre-pass exists. One
question, asked of the corpus the labels workstream already classified:

> Of the staves that print **no margin label at all**, how many sit in a
> document whose **earlier pages** print a label for the **corresponding**
> staff?

Probe: [`probe_roster_reach.py`](probe_roster_reach.py) → [`roster-reach.json`](roster-reach.json).

## ⚠️ THE KILL CRITERION, PRE-REGISTERED BEFORE THE RUN

> If **fewer than half** of the class-(a) staves sit in a document whose
> earlier page labels the corresponding position, the wall is real at
> document scope too and H2 dies.

Population 117 ⇒ the bar is **59**.

## The answer: 52 of 117. THE BAR WAS NOT MET.

```
REACHABLE                     52   (44.4%)
ABSTAIN_ALIGNMENT             28
UNREACHABLE_DONOR_BLANK       24
UNREACHABLE_NO_EARLIER_PAGE   13
                             ---
                             117
```

**H2 dies as stated.** But it dies *unevenly*, and the shape of the failure is
worth more than the verdict — see "per publisher" below, and read the
abstentions before concluding that the remaining 65 are unreachable in
principle. 52 of them are not: 28 are a join this probe declines to make, and
24 are a nearer-donor artefact of how the best donor is chosen.

## ⚠️ COVERAGE BEFORE GAIN — every number here is an UPPER BOUND

A name that arrives from a roster still has to survive everything downstream.
The standing counter-example is **class 6** in
[`docs/discussion-detector-right-output-wrong-2026-09-04.md`](../../docs/discussion-detector-right-output-wrong-2026-09-04.md):
a correctly-read `Tp.` → Timpani was **overturned to Trumpet** by
`contextual.resolve_ambiguous_label`, because a mis-joined layout fit named a
trumpet at that slot — and the wrong instrument then read as independent
evidence for the wrong join. A roster name entering that same consumer is
exposed to exactly the same circularity. **52 is what could be offered, not
what would be kept.**

## Per publisher — the pooled figure hides two opposite regimes

| publisher / edition | class (a) | REACHABLE | abstain | donor blank | no earlier page |
|---|--:|--:|--:|--:|--:|
| **N. Simrock** (Dvořák 9, Dover reprint) | 45 | **45** | 0 | 0 | 0 |
| **Henry Litolff's Verlag** (Beethoven 5, ×2 editions) | 50 | **2** | 24 | 24 | 0 |
| **Edition Peters** (Mahler 5) | 9 | **5** | 4 | 0 | 0 |
| **Edition Peters Nr. 4412** (Bach BWV1048) | 13 | **0** | 0 | 0 | 13 |
| pooled | 117 | **52** | 28 | 24 | 13 |

**Simrock is the whole positive result and it is a clean 100%.** Its convention
is exactly the one the labels workstream measured: the movement's first page
prints all fifteen names, every continuation page prints none, and the lineup
does not change. All 45 are joined to `dvorak-...-p5` (printed 183).

**Litolff is the whole negative result, and its cause is CONDENSATION, not
absence.** Beethoven 5 p.1 prints twelve staves ending `Violoncello`, `Basso`;
every continuation system prints **eleven**, ending `Violoncello e Basso`. So
the anchored join has seven anchors (the winds and brass, which Litolff *does*
label on every system) and then a **four-against-five** string block with no
anchor in it — the probe abstains, by design, rather than impute. ⚠️ **The same
engraving decision that removes the label also breaks the join**: the staff that
lost its name is the staff that was merged. This is not incidental to H2, it is
H2's central obstacle on this publisher.

**Bach is unreachable by construction.** `bach-...-p1` is pdf page 0 of a PDF
that begins at printed 59 — the movement's first page. There is no earlier page
to read. ⚠️ That row also carries a known phase-1 segmentation failure (this
tree re-detects `[12, 12]` where the committed `..graft09` fixtures have
`[12, 3, 3, 3, 1, 2]`), so its 13 should be treated as *unreachable and
structurally doubtful*, not as 13 clean negatives.

## The abstentions, and why they are abstentions

| n | reason |
|--:|---|
| 28 | `segment_size_mismatch` — the run of staves between two label anchors has a different length on the two pages, so no 1:1 correspondence exists. 24 Litolff (4-vs-5 strings), 4 Mahler (1-vs-0 and 2-vs-1 runs). |
| 13 | `INK_look` staves, **excluded from the population entirely**. The labels workstream's ink test is trusted only in the negative; these read non-zero ink and are not established as class (a) at all. |
| 24 | `UNREACHABLE_DONOR_BLANK` is **not** an abstention but is easy to misread: it means the chosen donor prints nothing there either. On Litolff p3/p4 the chosen donor is the *nearest* earlier page (p2, p3), which is itself unlabelled in the strings. The page that does print those names — p1 — abstains on the same 4-vs-5 mismatch, so the outcome is unchanged; only the reason label differs. |

## Which OCR rung produced the numbers

Both free rungs were live in this worktree: `.venv-surya` symlinked to the main
checkout (a worktree has none of its own), Tesseract 5.5.2 from Homebrew. The
paid rung was not used and is closed here anyway (the labels workstream priced
it: an unlabelled staff is what the vision prompt is told to answer `null` for).

```
donor labels behind the 52 REACHABLE verdicts:   surya 51,  text_layer 1
all 407 corpus staves, by resolving rung:        surya 206, tesseract 38,
                                                 text_layer 37, none 126
```

⚠️ **51 of the 52 come from Surya.** On a machine with no `.venv-surya` this
count is not merely smaller — it is *unmeasured*, because Tesseract's reach on
those specific donor pages was not scored. A run that silently loses the OCR
rung looks like a normal run.

The six non-corpus donor pages were read fresh here (Beethoven 984073 p0,
Dvořák p0–p3, Mahler p0). All six detect **zero staves** — and that zero is
established by **rendering them and looking**, not by the detector's silence:
they are a Dover series title, a Dover copyright page, the Dover **contents**
page, a Dover half-title, a Dover Beethoven title and the *Edition Peters
No. 3087b* Mahler title. PNGs in [`fresh-donor-pages/`](fresh-donor-pages/).
The contents page is load-bearing evidence in its own right: it prints
`I. Adagio ... 183`, which independently confirms that printed 183 — corpus row
`dvorak-...-p5` — **is** the movement's first page, so Dvořák's donor is not an
assumption.

*(Side finding, free: works.json calls the Mahler edition
`unidentified-scan-2016`. Its title page says **Edition Peters No. 3087b**.)*

## Verification — 45 of 45 imputed names agree with the hand-read truth

`works.json["staves"]` is the SCORING KEY. **No verdict above reads it.** It is
opened once, after every verdict is fixed, purely to check the names:

```
checked 45   agree 45   disagree 0   no truth 7
```

The 7 unchecked are the 5 Mahler and 2 Beethoven reachable staves, on rows that
carry no hand-read staff list.

## Three secondary arms, all deliberately more generous

| arm | result |
|---|---|
| **per-staff best donor** — let every staff pick its own donor *system* (a real roster pass picks one per system, so this is an upper bound on the upper bound) | **53** reachable + 2 text-only. Moves the pooled figure by one staff. |
| **forced top-alignment** — where a segment's counts disagree, join from the top and drop the tail (the obvious "do it anyway" policy) | reaches a further **48**, taking the total to **100 of 117 (85%)**; of the 48, 16 have hand-read truth and **16/16 are correct**. |
| **same-page earlier system** — donor is an earlier system on the *same* page; not "an earlier page", so never folded into the headline, but it is the only route open to a movement's first page | **5** of 117. On Bach it reaches only the 5 positions system 1 already resolves; the other 7 donor positions are the group-label fragments (`I`, `III`) the lexicon refuses — class (d), already priced by the labels workstream. |

⚠️ **The forced arm is the interesting one and it must not be read as a result.**
16/16 is 16 checks, all on Litolff `p2`, all in one 4-vs-5 string block, and the
one it gets "right" by name is `Violoncello e Basso` → `Violoncello` — correct
at the instrument level and **wrong at the part level**, since that staff
carries two parts. It is a demonstration that the abstentions are not obviously
irrecoverable; it is not evidence that forcing them is safe. Pricing it needs a
corpus where a suppressed staff sits in the *middle* of a block, which this one
does not contain.

## ⚠️ Four ways this method could have produced a falsely encouraging number

1. **The Dvořák verification may be partly circular.** `works.json` carries a
   *separate* hand-read staff list for p5, p6 and p7 — but all three are
   **identical**, so a human who assumed the lineup continues would produce the
   same file as one who checked. Mitigated, not eliminated, by looking: printed
   184 was rendered and inspected, and its fifteen staves reproduce printed
   183's bracket grouping and clef sequence exactly (3 treble, bass, 3 treble,
   C-clef, 2 bass, 2 treble, C-clef, 2 bass). That is corroboration independent
   of the truth file.
2. **44 of the 52 are joined by staff count with ZERO label anchors.** Dvořák's
   continuation pages resolve no labels at all, so there is nothing to anchor
   on; `equal_staff_counts` is the entire join, and it is the same rule
   `export._stitch_slots` already makes. Its failure mode — a page that
   suppresses one staff *and* adds another, holding the count — is invisible to
   this probe and to that rule.
3. **The population is the committed data's, not FINDINGS.md's.** This counts
   **117** `a_NO_INK` staves from the labels workstream's `margin-ink.json`;
   `FINDINGS.md` states **115**. The two are different vintages of the same
   classification (the committed data is post-(ii-a)), not a discrepancy to
   resolve here — but the denominator moves the percentage, and 115 would put
   the bar at 58 and the result at 45.2%. **The verdict is unchanged either
   way.** Had the answer landed at 58–59, the choice of denominator would have
   decided it, and it would not have been decidable from these files.
4. **"Reachable" is measured on the labels workstream's answers, which are the
   LADDER's answers, taken as given.** Where a donor page's label was resolved
   wrongly, this probe inherits the error and scores it reachable. The class-(e)
   lexicon errors are reported as 0 on current main, so this is a small risk
   today — but it is a dependency, not an independent measurement.

## What this leaves for H4

[`H4_ROSTER_QUESTION_DRAFT.md`](H4_ROSTER_QUESTION_DRAFT.md) proposes the
one-per-document roster question **pre-filled by an H2 pre-pass**. The count
above says what that pre-fill would arrive with:

* on a **Simrock-shaped** document (roster once, stable lineup) the pre-fill is
  complete — 45 of 45, names verified — and the human is confirming a draft;
* on a **Litolff-shaped** document the pre-fill arrives with the winds and brass
  and stops at the string block, because the page condensed it. The human is
  supplying precisely the fact no page-side signal carries — which is the same
  fact H4 is on the table for.

Read that way the negative result is not a refutation of the roster idea. It is
a measurement of how much of the roster a machine can pre-fill: **all of it on
one publisher, none of the hard half on another**, and the residue is
condensation — H4's own subject.
