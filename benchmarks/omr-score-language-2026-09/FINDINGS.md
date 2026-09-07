# The language a score is printed in, as evidence about its abbreviations

**2026-09-07. The reach is large and the firing rate is tiny, and both numbers
are the answer.** Over the 1,422-label margin corpus, **167 labels (11.7%) are
ambiguous and 167 of 167 sit on a document whose language its OTHER labels
reveal** — but the reading **re-decides 9 of them**, because on every family
where language could speak, either another channel already owns the question or
the lexicon's standing answer was already right.

The 9 are the case this was commissioned for: **`Tb.` → Tuba on Litolff's
Beethoven 6, where `Tb.` is *Tromboni***. The work's IMSLP roster
(`source_kind: catalog`, independent of any encoding and of any page reading)
lists **2 trombones and no tuba**.

Nothing here changes a default. `tools/omr/instruments.py` is **byte-identical
to `origin/main`** and all three lexicon corpora score identically.

**It is WIRED IN** — `contextual.apply_contextual_analysis` reads the
document's language from the whole run's labels and, behind
`OMR_SCORE_LANGUAGE` (**default off**), re-decides the labels it settles. §7.1
has the shape and why it is document-scoped.

---

## 1. Reach — the number that decides whether the rest matters

`probe/measure_reach.py`, off the committed 1,422-label dump
(`benchmarks/omr-lexicon-2026-09/labels.json`, 12 documents, 5 publishers,
3 readers). No transcription, no weights, no network.

| | margin labels only | + head-page escalation |
|---|--:|--:|
| ambiguous labels | 167 / 1422 = **0.1174** | 167 / 1422 |
| …on a document whose language is read | 126 (**0.755** of ambiguous) | **167 (1.000)** |
| …the reading RE-DECIDES | **0** | **9** (0.0063 of corpus) |

**So "the reach is too small to matter" is NOT the answer.** Three quarters of
the ambiguous population is reachable from the sampled margin labels alone, all
of it once the document's head page is read. What is small is the **firing**
rate, and §4 says exactly why: language *confirms* 158 readings and *overturns*
9.

⚠️ **Read reach and firing apart.** A signal that agrees with the incumbent on
158 labels has not done nothing — it has said "no evidence of a fault here" on
158 labels, from a direction nothing else was looking from. But it must not be
credited with them, because nothing changed.

### 1.1 ⚠️ The regime flips the answer on the one document that matters

`beethoven6-504082` — the document carrying the `Tb.` fault — reads
**`--` (no diagnostic evidence at all)** from the dump and **`it` at share
1.00** from its own page 0. Same document, same code, two page sets.

The dump samples ten pages, roughly every ninth, **and page 0 is not among
them** — and page 0 is where a score prints its roster in full. This is a
second independent instance of the identity harness's regime rule
(`benchmarks/omr-identity-harness-2026-09`, which refuses to pool across
page-set regimes). **A reach figure without its regime is not a reach figure**,
and the two regimes here differ by "absent" versus "unanimous".

Both regimes are stated on every row of `out/reach-labels.json` (10 sampled
pages per document) and `out/reach-head3.json` (the same, escalating to pages
0-2 where the sample is silent).

---

## 2. Determinability — and one third of the "mixing" was MY BUG

| | documents | share |
|---|--:|--:|
| language read, margin labels only | **9 / 12** | 0.750 |
| language read, + head-page escalation | **11 / 12** | 0.917 |
| genuinely MIXED evidence | **1 / 12** | 0.083 |

Every document that reads at all reads at share **0.96–1.00**. The single mixed
row is Mahler 5 at `{de: 49, it: 1, fr: 1}` — which is not really mixing either;
it is a German score with two stray reads.

⚠️⚠️ **The first revision of this module reported mixing at 4 / 12 = 0.333, and
three of those four were false votes cast by my own tagging.** The corpus
caught all three, and each is now a test that has been run RED
(`probe/red_check.py`):

| false vote | where | why |
|---|--:|---|
| `flutes` tagged **English only** | 2 EN votes on Ravel and Debussy | normalization strips the circumflex, so French `Flûtes` and English `Flutes` are ONE string |
| `basse` tagged **French only** | **12 FR votes on Mahler 5**, 19% of that document's evidence | German `Bässe` normalizes to `basse` — the accent that carries the language is gone before this sees the string |
| `trpt` tagged **English** | **8 EN votes on Brahms 1 / BREITKOPF** | `Trpt.` is printed on a German edition, which `instruments.py` already records. A Latin consonant skeleton carries no language |

**The lesson is the one this project keeps paying for**: the module's own
docstring warned against exactly this ("a spelling several traditions share …
listing it in one language would be the fault this module exists to fix, one
row further down") and I committed it three times anyway. **Only the 1,422
labels found it.** `tpt`, `vln`, `vla` and `tbn` were dropped alongside `trpt`
on the same reasoning, before they could be measured doing damage.

---

## 3. The exclusion framing survives — but it has to be about LANGUAGES

Sean's constraint is the right one:

> if a score labels its timpani `Pk.`, then `Tp.` on that score cannot be the
> timpani

⚠️ **The naive form of it — *"this instrument is already named elsewhere, so
this alias is something else"* — is FALSIFIED by the first document in the
corpus.** Beethoven 5 / Litolff prints `Timpani in C.G.` on its opening page
and `Tp.` on the pages after it. Same instrument, same language, two lengths of
the same word; a bare co-occurrence rule fires and is wrong.

What excludes is a rival spelling **from another tradition**, which is what the
language reading detects and why the signal is document-scoped rather than
page- or system-scoped.

---

## 4. What it decides, and the ownership boundary that is most of the design

⚠️ **`Tp.` is NOT in the deciding table, and removing it was the single most
important design change here.**

An alias `instruments.AMBIGUOUS_ALIASES` DECLARES already has an owner:
`contextual._resolve_ambiguous_labels` (`contextual.py:329`) withholds the slot
from the layout fit (`_ambiguous_label_slots`, `:272`), asks the fit what sits
at that ordinal, and takes whichever CANDIDATE it proposes. On 2026-09-07 that
channel was measured to turn on the **clef**
(`benchmarks/omr-readpass-monotonicity-2026-09/FINDINGS.md` §4): clef-blind it
proposes `Trumpet` and overturns a correct label document-wide; clef-informed
it proposes `Trombone`, which is not a `Tp.` candidate, so it declines and the
label stands — **worth 51 records on Beethoven 5, where the label channel was
worth 0**.

A language reading of the same slot would be a **second mechanism aimed at a
case that already has one**, and both are computed from the document's own
labels. The governing rule (`docs/architecture-decision-map.md` §4.1) is
explicit: *two signals sharing an ancestor are ONE signal, not corroboration.*

So the deciding table holds exactly the population **no channel can reach**:

| alias | status | why |
|---|---|---|
| **`tb`** | **DECIDED** | the lexicon resolves it to Tuba and declares NO ambiguity, so nothing tells the fit there is a question to ask |
| `tp`, `altos` | quarantined in `CORROBORATION_ONLY` | separable by language, but owned by the clef-informed position channel |
| `basso`, `basse`, `bassi`, `bass` | ABSTAIN in every language | the bass VOICE and the double basses are the same word in Italian, French and English alike |
| `tr bas` | ABSTAIN | `Trombone basso` and `Tromba bassa` are both Italian |
| `cor` | ABSTAIN | Horn in French AND the standard Italian abbreviation of `Corni` — no reading changes the answer |

`test_language_never_decides_an_alias_the_lexicon_declared_ambiguous` and
`test_corroboration_entries_are_exactly_the_ones_owned_elsewhere` assert the
boundary in both directions, so it cannot drift.

### 4.1 The nine, and their independent confirmation

All 9 changes in the whole corpus are one alias on one document:

    9  beethoven6-504082-textlayer   'tb'   Tuba -> Trombone

Beethoven 6 / Litolff is Italian by its own page 0 (`Flauti. / Oboi. /
Clarinetti in B. / Fagotti. / Corni in F. / Violino I. / Violino II. / Viola. /
Violoncello e Basso.` — 8 diagnostic votes, share 1.00). Confirmation is
**independent of the labels and of any encoding**: the work's IMSLP roster in
`data/score-library/catalog.json` (`source_kind: "catalog"`) reads
*"2 horns, 2 trumpets, 2 trombones, timpani, strings"*. **There is no tuba in
Beethoven 6.**

And the corpus corroborates from the other side: **every bare `Tb.` in all
1,422 labels is that one Italian document**, while every real tuba in the
corpus — Ravel, Mahler, Debussy — is spelled `Tuba` in full.

---

## 5. What it must not break, and the proof it does not

**Handel.** `handel-messiah-leadsheet` prints `BASSO` (the voice) and `Bassi`
(the strings) on the same page and the current first answers are right for
both. Measured: **0 changes on that document**, and
`test_handel_is_untouched_in_every_tradition` asserts that `basso`, `bassi`,
`basse`, `bass`, `tr bas` and `cor` abstain under **all four** traditions, so a
future table entry that breaks Handel fails a test rather than a score.

**The lexicon.** `git diff origin/main -- tools/omr/instruments.py` is **empty**.
All three standing corpora agree:

| corpus | result |
|---|---|
| 1,422 margin labels (`resolve_labels.py --base origin/main`) | **0 changed**, resolved 1112 → 1112 |
| 1,271 reference part names | 0 changed |
| substring capture (`probe_substring_capture.py --base origin/main`) | HEAD == BASE: 230 containment pairs / 0 unrescued; 58 external names / 0 captured cross-family |

**A pool is not a document.** The 1,271 reference part names are many works'
names concatenated, and the module **abstains** on them
(`{en: 126, it: 88, de: 58, fr: 11}`, share 0.45) despite 283 diagnostic votes.
That is the safety property stated as a control: pooled evidence is exactly the
shape that would otherwise launder four traditions into one confident answer.
Pinned by `test_a_pool_of_many_documents_gets_no_language`.

**The identity harness.** `bash benchmarks/omr-identity-harness-2026-09/probe/run_all.sh`
→ **GATE exit=0** and every committed output file **byte-identical**
(`git diff` on that directory is empty). The change is inert, as a default-off
unwired module must be. ⚠️ Regime note: 58 of that harness's 59 arms are
**clef-blind replays**, so its absolute identity figures understate the real
pipeline — but this run is a pure A/A control, where that handicap is
irrelevant because both sides are the same side.

---

## 6. Can the pipeline actually SEE the evidence? Measured, and the rungs differ

The signal rests on a document printing its roster in full somewhere, and in an
orchestral score that somewhere is a movement's first page. So the question
that decides buildability is not "is the language determinable" but **"does the
pipeline's own reader see the words"**. `probe/reader_reach_page0.py`, on
Beethoven 6 / Litolff page 0:

| rung | labels | verdict |
|---|--:|---|
| text layer (`staff_labels.read_staff_labels`) | **0** | ABSTAINS |
| Surya (`staff_labels_surya`) — 5.0 s | **11** | **`it`, 8 votes, share 1.00** |

**YES — the production ladder reaches it**, via exactly the rung
`_read_labels_for_page` escalates to when the text layer comes back thin.

⚠️ **AND AN INDEPENDENT DEFECT, offered to the architecture map's Stage 9.**
That page's text layer *plainly holds* `Oboi. / Clarinetti inB / Fagotti. /
Corni in F. / Violino J. / Violino II. / Viola. / Violoncello e Basso.` — I read
it straight out of PyMuPDF — and `read_staff_labels` returns **nothing**. A
movement-head page indents its first system and carries a title block, and
`detect_staves` finds **15 staves where the music has twelve**. This is a
reader-reach fault on the single most information-dense page of every
orchestral document, it is not in the map's Stage 9 blindness column, and it is
not mine to fix. Recorded in `out/reader-reach-beet6-p0.{txt,json}`.

⚠️ **A design property worth keeping**, and it is why the fault above does not
block this work: **language detection has a lower evidential bar than
identity.** A name must be joined to the right staff to name it; a language only
has to be READ. The vote needs no staff join, no ordering and no position — which
is also why it stays out of the position channel's lane.

---

## 7. The architecture map, applied to this work

`docs/architecture-decision-map.md`, per the coordinator's checkpoint.

**1. What does my decision already have available that it does not use?**
The map's own row for my decision is `instruments.lookup` — *"blind to
everything except the string. A pure function with zero context — every
contextual repair downstream exists to patch this deliberate blindness."* This
signal is one more such repair: it supplies **the document**. What it still
does not use, all available at the same seam:
* **`Match.coverage`** past the `0.6` quantisation — the map's *"cleanest
  Class-B site"*. Every diagnostic label casts one equal vote whether its
  coverage is 0.61 or 1.00.
* **`Match.ocr_folded`** — a fold-matched string is a guess by construction and
  a weaker language witness than a clean text-layer read, and the flag is right
  there on the Match. **The cheapest named improvement to this module.**
* **`staff_index` / `system_index`** — deliberately unused. Using position would
  put this in the position channel's lane, which is §4's whole point.

**2. What consumes my output?** `contextual.apply_contextual_analysis` does —
see §7.2. It was NOBODY when this section was first drafted, which is the
project's most-repeated defect, so it was wired rather than reported.

**3. What do I depend on, and is it SATISFIABLE?** Yes — and deliberately
narrowly. The only input is the label strings `_read_labels_for_page` already
produces. **No `OMR_WORK_ID`** (unlike `OMR_ROSTER_LABELS`, whose production
reach §9.4 records as nil for exactly that reason), **no dossier** (unlike the
`_dedupe` written-range tier, dead on every scan), **no clef, no roster, no
score order.** The one conditional dependency — that the run reads a page
carrying a spelled-out roster — is measured satisfiable in §6 at 5 s, on the
very document in question.

**4. Am I inside a cycle?** ⚠️ **The sharpest possible version of the question:
language is inferred FROM labels and then used to decide A label.** It is not
circular, and the guarantee is **structural, not conventional**: the vote is
cast only by aliases tagged with exactly ONE tradition, while an alias this
module decides is by definition ambiguous BETWEEN traditions and so is tagged
with **none**. The two alias sets are **disjoint**, so a decided alias can never
contribute to the reading that judges it.
`test_a_decided_alias_never_votes_for_the_language_that_decides_it` **is** that
disjointness, and `probe/red_check.py` restores the cycle (tagging `tb` Italian)
and confirms the test sees it. This is the same move as the codebase's three
verbatim refusals in §4.2 — the difference is that here the loop can be cut by
construction rather than declined. The identity⇄clef cycle is untouched: this
reads no clef and proposes none.

**5. Is this information already gathered elsewhere?** For `tp` and `altos`,
**yes** — the clef-informed position channel — which is why they are quarantined
in `CORROBORATION_ONLY` and cannot decide anything (§4). For `tb`, **no**: no
channel questions it, because the lexicon declares no ambiguity for it to
question.

### 7.1 The consumer, and why it is document-scoped

`contextual.apply_contextual_analysis`, immediately after the page loop and
**before `assign_slots`** — the last moment where every page's labels are in
hand and nothing downstream has read them yet.

    language = _read_score_language(staff_labels_per_page)   # unconditional
    summary["score_language"] = {…, "applied": enabled(), "changes": []}
    if score_language.enabled() and language.language is not None:
        staff_labels_per_page, changes = _apply_score_language(…)

**DETECTION IS UNCONDITIONAL AND RECORDED; only its USE is behind the flag** —
copied deliberately from the roster block eighty lines below it, whose comment
gives the reason: *"recording what the margin said changes no music, and a
signal read correctly and then discarded is the shape this project has paid for
nine times."* So a default run now carries `contextual.score_language` — the
verdict, the per-tradition votes, the share, and an empty `changes` list — and
a future session can ask what the language channel WOULD have done without
turning anything on.

⚠️⚠️ **The unconditional detection is free only because it votes off
`StaffLabel.alias`, and the first version did not.** Voting by re-resolving the
label text costs a measured **21.98 s on Ravel's 427 labels** (162 distinct;
`instruments.lookup` is 23-136 ms per string, and a garbled label pays the
OCR-fold second pass) and 2.77 s on Brahms's 209 — which would have made "record
it unconditionally" a real wall-clock regression for a signal that is off by
default. **Recording a signal is only free when it IS free.** Every reader in
the ladder has already resolved each label and kept the alias, so
`detect_from_aliases` votes off a field the caller is holding:
**0.01–0.04 ms per document**, with the verdict and the per-tradition vote
counts **identical on all 12 documents** (pinned by
`test_voting_off_the_alias_is_the_same_answer_as_voting_off_the_text`).

⚠️ **It pools the whole run's labels rather than deciding per page, and that is
the load-bearing choice.** `_labels_for_page` is per page and a language is per
document; a per-page verdict makes the answer depend on which page you are
looking at, and a vote that GREW page by page makes it depend on how many pages
have been read. Both are the regime fault of §1.1. It remains regime-dependent
in the honest sense — a run that never reads a page carrying a spelled-out
roster abstains — which is exactly `roster.acquire_roster`'s property, and
abstention is the safe direction.

**It moves `instrument` and nothing else.** `text`, `alias`, `confidence` and
`fifths_offset` are carried across untouched — the contract the roster pass
states in the same file: *a reader is never made to "read" something it did not
see*. Carrying `fifths_offset` is safe only while every reachable instrument is
non-transposing, so that is a test
(`test_a_re_decided_instrument_never_transposes`) rather than a comment: a
future entry naming a horn fails there before it can silently transpose a
staff.

### 7.2 On the map’s accuracy — an independent check

Verified at the merge commit, **before** this branch's `contextual.py` change
shifted that file's line numbers — my `_read_score_language` /
`_apply_score_language` insert moves everything below `:603` down by ~60 lines,
so the map's Stage 9/10 `contextual.py` citations need re-deriving after this
lands. Everything I had cause to verify was **exact**:
`Match.confidence:77-81` (including the unnamed bare `0.6` literal),
`staff_labels.read_staff_labels:189` (the nearest-staff `min`),
`contextual._ambiguous_label_slots:272` and `_resolve_ambiguous_labels:329`.
**Its correction of CLAUDE.md is right**: `_labels_for_page` (`:549`) is the
roster wrapper and the reader cascade is `_read_labels_for_page` (`:605`) —
CLAUDE.md names the wrapper. One cosmetic nit: `instruments.lookup` is *defined*
at `:852`; `:873` is a line inside it.
One **addition** rather than a correction: the Stage 9 reader-reach fault in §6.

---

## 8. Reproducing

```bash
# reach + determinability, 1422 labels, 12 documents  (~4 min: lookup is ~23 ms)
python3 benchmarks/omr-score-language-2026-09/probe/measure_reach.py
python3 benchmarks/omr-score-language-2026-09/probe/measure_reach.py --head-fallback 3

# the same, on the second corpus — must ABSTAIN
python3 benchmarks/omr-score-language-2026-09/probe/measure_reach.py \
    --labels benchmarks/omr-lexicon-2026-09/part-names.json

# THE GATE — restore 7 faults, prove each test sees it, and passes without it
python3 benchmarks/omr-score-language-2026-09/probe/red_check.py

# does the production reader ladder reach the evidence?  needs .venv-surya
OMR_SURYA_KEEP_ALIVE=0 python3 \
    benchmarks/omr-score-language-2026-09/probe/reader_reach_page0.py

# the lexicon is untouched — all three standing corpora
python3 benchmarks/omr-lexicon-2026-09/resolve_labels.py \
    benchmarks/omr-lexicon-2026-09/labels.json --base origin/main
python3 benchmarks/omr-lexicon-2026-09/probe_substring_capture.py --base origin/main
```

⚠️ `measure_reach.py` and the head probe are minutes rather than seconds
because `instruments.lookup` costs **~23 ms** — the alias index is a few
thousand entries wide after the contrabassoon cross product and the derived
plurals. `score_language` memoizes it per distinct string and shares one
resolution between the vote and the decision; the obvious two-pass shape pays it
twice.

⚠️ A fresh worktree has **no `.venv-surya`** (CLAUDE.md's second symlink) and
none of the legacy `tools/omr/training/data/imslp/...` symlinks, so
`reader_reach_page0.py` resolves its PDF against the MAIN checkout on purpose.
⚠️ Adding the `.venv-surya` symlink **changes the suite's skip set** — see §9.

---

## 9. Suite

`tools/omr/tests/test_score_language.py` — **26 tests**, all passing, and every
assertion that guards a real fault is exercised in both directions by
`probe/red_check.py`: **7 faults, each FAILING with the fault restored and
PASSING under the shipped tables** (`out/red-check.txt`). Five of the seven were
live in this module's own first revision.

Full suite (`out/suite.txt`): **1 failed, 2516 passed, 16 skipped**.

⚠️ **The one failure is PRE-EXISTING and order-dependent, and that is a control,
not an assertion.** `test_direction_text.py::TestReaderSelection::test_the_env_var_restricts_the_rungs`
passes when its file runs alone and fails when `test_staff_labels.py` runs
before it. Following §A00's order of enquiry — *is the COMPARISON valid* before
*is the mechanism wrong* — it was reproduced **with my `contextual.py` change
stashed out**, at the merge commit, on the same two files. It fails there too.

⚠️ **Two other things about that number are measurement artefacts and are
called out rather than smoothed over.**
* **The skip count is 16 here against the coordinator's baseline of 1.** This is
  a git WORKTREE: `.venv-omrned`, `.venv-surya` and the weights are
  repo-root-relative and gitignored, so tests gated on them skip. A like-for-like
  count needs the main checkout. **Adding the `.venv-surya` symlink changes the
  set**, which is worth knowing before anyone compares two suite runs made in
  different worktrees.
* **Two `test_staff_labels` failures appeared in two earlier runs and were
  MINE — of the process, not the code.** I edited source while a background
  suite was running, so pytest collected one tree and executed against another.
  Both vanished on a stable tree. A background suite run is invalid the moment
  you touch a file, and neither run's output says so.
