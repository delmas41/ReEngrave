# The work's roster as a constraint on margin labels — reach, and what it buys

**2026-09-06.** `benchmarks/omr-margin-window-truncation-2026-09/FINDINGS.md`
established that truncated margin labels (`'larinetti in A'`, `'orni in F I II'`)
are the *page's* doing and that neither of the two obvious cures is available:
widening the lexicon is refused (an alias is global; `orni` admitted for
Tchaikovsky is admitted for every score ever read), and widening the rendered
margin moved the pooled figure by 8 edits of 2,362 — noise, at the cost of a
benchmark discontinuity.

Sean's third option, measured here: **match what we CAN read against the roster
the work is already known to have.** Matching `orni` against the open 400-alias
lexicon is dangerous and correctly abstains today; matching it against the ten
instruments Tchaikovsky 6 is actually scored for is a different problem, because
the roster CONSTRAINS the guess instead of widening it.

Shipped **default OFF** behind `OMR_ROSTER_LABELS`. The reach is small and the
headline below says so with the number.

---

## 0. What it does, in one table

`tools/omr/work_roster.py`, applied to every label the ladder produces
(`contextual._labels_for_page`). Four outcomes; the two that INSTALL a name and
the one that only removes one are reported apart throughout, because they carry
different risk.

| outcome | when | risk |
|---|---|---|
| **recovered** | the lexicon abstained (or is family-vetoed) and exactly one instrument the roster admits owns a TAIL of a token | names a staff — a wrong one names it wrongly |
| **disambiguated** | the lexicon resolved into a family the work does not have, and the alias it fired on is one `instruments.AMBIGUOUS_ALIASES` itself declares ambiguous, with exactly one reading the roster admits | names a staff, from the LEXICON's own candidate list |
| **vetoed** | same family miss, nothing to put in its place | only removes a name that was already wrong |
| **unchanged** | everything else | none |

The roster comes from `data/score-library/catalog.json`'s **`works`** map,
`source_kind: "catalog"` — the IMSLP work page, independent of the MusicXML the
benchmarks score against. The `editions` map is `source_kind: "page"`, an OMR
output of the same raster, and `work_roster()` refuses anything that is not
`catalog` (pinned by `test_only_the_catalog_tier_is_read`).

---

## 1. THE REACH — measured first, because that is what decides whether any of
this matters

`probe_roster_reach.py`, three corpora, per the standing rule
(`benchmarks/omr-lexicon-2026-09/FINDINGS.md` "Validation — three corpora").

| corpus | labels | have a roster | unresolved today | recovered | disambiguated | vetoed |
|---|--:|--:|--:|--:|--:|--:|
| **readers** — every raw margin string 13 editions produce | 1422 | 1251 | 310 | 17 | 3 | 0 |
| **reference** — every distinct part name in 1745 encodings | 1271 | 0 | 393 | 0 | 0 | 0 |
| **fixtures** — every label the 11 engraved fixtures hand the lexicon | 223 | 185 | 6 | 5 | 2 | 1 |

**20 of 1422 real margin labels change (1.4%), across 4 of 13 editions. 8 of
223 engraved-fixture labels change (3.6%).** Every one of the 28 firings was
adjudicated by hand and every one is correct — the full list is in §2.

**So: the reach is small, and this is the number that says so.** It is not zero
and it is not noise-shaped either: 6 of the 8 fixture firings are the exact
labels the truncation session reported, including both of the two that resolve
to a SINGER.

Three reach limits, each measured rather than assumed:

- ⚠️ **205 of the 1422 labels (14%) are on works the `works` tier does not
  hold at all** — `mahler--symphony-5` (173 labels, the densest scan in the
  corpus) and `handel--messiah` (32). Both are `--local` editions with no IMSLP
  work page behind them. No roster, no layer.
- ⚠️ **The engraved benchmark is a NO-OP in production without help.**
  `orchestral_eval` renders its fixtures into a gitignored build directory, so
  `work_id_for_pdf` correctly abstains on all eleven and nothing fires. The
  §1 fixture row is measured with the work named explicitly. `OMR_WORK_ID`
  exists for a harness that knows what it just rendered; nothing sets it.
- ⚠️ **The truncation defect itself has no real-world exposure.** The
  truncation session's library control is unchanged by this work: 289 editions,
  141 pages of margin text, zero spans at or past the sheet edge. The recovery
  half is addressed to a defect that lives in generated fixtures. What has real
  exposure is the *other* half — see §3.

## 2. Every firing, adjudicated

Recovery (14 of the 28 across both live corpora):

| firing | reads | becomes | correct? |
|---|---|---|---|
| Boléro `V elles` and 4 LaTeX spellings, ×17 | — | Cello | ✅ `Violoncelles`, superscripted; the lexicon has no spaced/superscript form |
| `larinetti in B.` (Mozart 40), `larinetti in A` (Tch 6) | — | Clarinet | ✅ |
| `orni in F I II` (Tch 6) | — | Horn, offset +1 | ✅ |
| `mpani in C–G` (Mozart 41) | — | Timpani | ✅ |
| `mbone Basso` (Tch 6) | **Bass voice** | Trombone | ✅ the flagship: a captured label, not an absent one |

Disambiguation (5): `Basso.` / `Basso` on Beethoven 5 (both editions), Mozart 41
and Tchaikovsky 6 — **Bass voice → Contrabass**, five times. This is the
`Basso.` ambiguity CLAUDE.md already prices at 35 rows of edition-tier
disagreement ("the only disagreement on 30"), settled here by the one fact that
settles it: these works have no singers.

Veto (1): `Alto e Tenore` (Tch 6) — **Tenor → unlabelled.** The truth is
Trombone and the layer does not reach it (§4), but a staff with no name is
strictly better than a trombone staff named after a singer.

Two truncations are left alone and both abstentions are the designed ones:
`ni in F III IV` (two letters, under the floor) and `ani in A.D.E.` (keeps 0.43
of `timpani`, under the fraction floor).

## 3. The half with real exposure is the VETO, and it is the half that is free

A wrong recovery names a staff wrongly; a veto only ever removes a name the
lexicon had already got wrong. And the population it removes is one this repo
has now recorded four times under different names — `Tr. Alt.` → *Alto*, the
roster regression where "7 staves read as a SINGER", the `Basso.` edition-tier
rows, and the two truncation cases here. **A margin label resolving to a singer
on a work with no singers is not a near miss**: it feeds `clef_correction`, the
written-range veto in `_dedupe_cross_staff_detections`, and the part→staff join,
none of which can tell it from a right answer, and none of which the OMR-NED
metric can see.

`probe_end_to_end.py` runs the production ladder, flag off vs on, on real pages
of both families:

```
beethoven5-575951 p1               scan+textlayer    12 labels  roster=yes  changed=1
    staff 11  'Basso.'          Bass voice [high]  ->  Contrabass  [high]
ravel-bolero p1                    scan+textlayer     0 labels  roster=yes  changed=0
tchaikovsky-sym6-mvt2 (fixture)    engraved          16 labels  roster=yes  changed=5
    staff  3  'larinetti in A'        None [none]  ->  Clarinet    [medium]
    staff  5  'orni in F I II'        None [none]  ->  Horn        [medium]
    staff  8  'Alto e Tenore'        Tenor [medium] ->  None        [none]
    staff  9  'mbone Basso'     Bass voice [medium] ->  Trombone    [medium]
    staff 16  'Basso'           Bass voice [high]  ->  Contrabass   [high]
mozart-sym40-mvt1 (fixture)        engraved          11 labels  roster=yes  changed=1
    staff  2  'larinetti in B.'       None [none]  ->  Clarinet    [medium]
```

⚠️ **No pooled OMR-NED figure is claimed.** The layer changes only what a label
RESOLVES TO, and the roster-wiring session measured directly that musicdiff does
not score `<part-name>` (all 15 of a truth file's part names rewritten to a bogus
value for 0 edits). The paths by which it *could* reach the metric —
`clef_correction`, the written-range veto — are real but narrow, and CLAUDE.md
already records that the range veto has never fired on a scan. Pricing that is a
separate run; the flag is off until someone makes it.

## 4. What is refused, and why

- **Adding `larinetti` / `orni` / `mpani` as aliases.** Refused as instructed
  and refused on evidence: they are not names. Nothing in `instruments.py`
  moved.
- **Matching across a SPACE.** A truncation is the tail of a WORD. `tenore` is
  the tail of the Trombone alias `tr tenore`, so admitting multi-word aliases
  would recover `Alto e Tenore` correctly — and would also read a truncated
  `Fl. Alt.` (an ALTO FLUTE) as a trombone, through `tr alt`. Priced at exactly
  one real recovery and refused.
- **Naming a staff on an ambiguous tail.** 91 distinct tails are owned by more
  than one instrument of the Brahms 1 roster alone (`agotti` is bassoon or
  contrabassoon). Ambiguity abstains.
- **Reading absence as denial at the INSTRUMENT level.** A roster describes the
  work and a page prints part of it; the veto is family-level and only on a
  complete parse.
- **Trusting the parse about a family.** Two ways it loses one, both live —
  see §5.

## 5. Two faults in the catalog's own parse, found by building on it

Neither is a bug in this layer; both would have made it do damage.

**(a) A section word can be dropped.** Tchaikovsky 6's InstrDetail ends
`..., tam-tam ''(ad lib.)'', strings` and `strings` landed in
`segments_ignored`, so that work's parsed roster names **no string instrument at
all** at `parse_rate 1.0`. 13 of 219 rosters have no string presence. A veto
reading the parse alone would delete every violin on the page.

**(b) THE PARSE READS ONE FIELD.** `roster_field` is `InstrDetail` where a work
has one, and a detail line lists the ORCHESTRA. Beethoven's *Egmont* says
`narrator (optional), soprano, orchestra` in `Instrumentation` and its detail
line is winds, brass and strings — **the soprano is nowhere in the roster.**

`probe_voice_admission.py` asks this directly over all 223 works, with an
independent screen (title + raw fields, never the parse). Before the fix, **4
works with real singers admitted no voice family**: Egmont, Mahler 4, Fauré's
*Pelléas*, and Mahler's *Gesellen* songs. The veto would have stripped the name
off every vocal staff in them — by far the worst thing this layer could do.

So families are read off BOTH raw fields, resolved through `instruments.lookup`
per segment rather than by word search (so `bass clarinet` stays a woodwind,
which the longest-alias-first index already knows). After it: **37 of 37
vocal-looking works admit voices**, and the one remaining flag is Boléro, which
my own screen fires on for `soprano saxophone` and which has no singers.

⚠️ The screen was wrong first, and how it was wrong is worth keeping: holding
`bass`, `alto` and `tenor` it flagged 39 works, mostly for `bass clarinet` and
`bass drum`, and the four real ones were buried in the noise. **A screen for a
rare fault has to be specific or its output is not readable.**

## 6. The false-positive surface, measured by a deliberately impossible test

⚠️ **The reference corpus fires ZERO times in §1 and that result is VACUOUS** —
those 1271 part names carry no work, so the layer cannot touch them by
construction. Reporting it as "no regression" would be reporting that a
switched-off thing is off.

`probe_false_positives.py` crosses **1651 distinct strings × 223 rosters =
368,173 decisions**, scoring a Ravel margin string against Bach's roster. That
is strictly harder than anything production faces, and it is the only way to see
the rule's shape rather than the handful of works two corpora happen to name.

Final surface: **19,995 vetoes, 1,911 disambiguations, 1,553 recoveries; 1,141
distinct claims, of which 1,117 are vetoes, 13 disambiguations
(all `Bass voice → Contrabass`) and 11 recoveries.**

The veto's whole population is the VOICE family — `Soprano`, `Tenor`, `Alto`,
`Chorus` part names scored against instrumental rosters — which is exactly what
§5 is about, and why the count fell by ~940 firings when the voice families were
read off the raw fields.

The **11 distinct recovered claims** are the risky half. 8 are correct
(`V elles`→Cello ×5, `High/Low Wood Block`→Percussion, `Side Stick`→Percussion —
all cases where the lexicon holds the closed-up spelling and not the spaced one)
and 3 are wrong: `Parallel mixture lines (12th/17th, 7th partial)`→Violin (via
`violines`) and Mandolin, and `Harmony (tutti chords)`→Piano (via
`harpsichords`). All three are organ-registration strings from a REFERENCE
ENCODING — not margin labels, and not something this layer is ever handed: it
runs at the margin-label boundary only.

**Two guards came directly out of this probe and out of nothing else:**

| found | claim | guard |
|---|---|---|
| `Vier Flöten` → **Piano** | `vier` is a tail of `klavier`, keeping 0.57 | spelled-out COUNTS are not name tokens. A margin prints `Vier Hörner` and `Drei Klarinetten` constantly; `instruments._STRIP_TOKENS` already removes this class and simply lacks the German and French words |
| `Soprano Saxophone` → **Alto** | `soprano` is a tail of `mezzosoprano` | a token the lexicon already holds as a complete alias is a NAME, not a stump |

Together they took the recovered claims **20 → 11** (6 to the count guard, 3 to
the alias guard) and the recovered firings 1,598 → 1,553, and cost **none** of
the 28 real firings in §1. Neither guard was reasoned into existence; both were
read off this table.

⚠️ **The three that remain are only reachable through a foreign roster.** In
production a label is only ever scored against ITS OWN work, which is the §1
measurement: 28 firings, 28 correct.

## 7. Reproducing

```bash
# the reach, three corpora                                       (~3 min)
python3 benchmarks/omr-roster-constrained-labels-2026-09/probe_roster_reach.py

# the fixture corpus it reads, re-read through the PRODUCTION reader (~30 s)
python3 benchmarks/omr-roster-constrained-labels-2026-09/read_fixture_labels.py \
    --fixtures /Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-orchestral-e2e/fixtures

# the false-positive surface, every string against every roster   (~20 min)
python3 benchmarks/omr-roster-constrained-labels-2026-09/probe_false_positives.py

# does any work with singers fail to admit them?                  (~15 min)
python3 benchmarks/omr-roster-constrained-labels-2026-09/probe_voice_admission.py

# the production ladder, flag off vs on, both families            (~2 min)
python3 benchmarks/omr-roster-constrained-labels-2026-09/probe_end_to_end.py \
    --library-root /Users/seanjohnson/Desktop/ReEngrave

# every test verified RED by breaking the mechanism it guards     (~1 min)
bash benchmarks/omr-roster-constrained-labels-2026-09/verify_red.sh
```

`verify_red.sh` breaks one mechanism at a time and confirms exactly the test
that guards it fails — 12 arms, all red. **Two arms were written wrong the first
time and the script is what caught them**, which is the argument for having it
at all: the length floor and the ambiguity rule were perturbed together (and
admitting two-letter tokens makes `in` match everything, so ambiguity saved the
abstention and both tests stayed green), and the flag-off wrapper test passed a
PDF outside the store, so it would have passed with the flag defaulted ON. The
same failure shape as `benchmarks/omr-margin-labels-blob-2026-09/FINDINGS.md`'s
vacuous length assertion.

Suite: **2440 passed, 16 skipped** over `tools/`. One pre-existing failure,
`test_direction_text.py::TestReaderSelection::test_the_env_var_restricts_the_rungs`,
which asserts the Surya rung is selectable and fails in any worktree without the
`.venv-surya` symlink — verified by stashing this branch's changes and running
it on the clean tree.

⚠️ **From a git worktree, `--library-root` and `--fixtures` must point at the
main checkout**: `library/` and `benchmarks/omr-orchestral-e2e/fixtures/` are
machine-local and gitignored, and an absent library reads exactly like "no page
has this fault" — the trap
`benchmarks/omr-margin-window-truncation-2026-09/probe_edge_separation.py`
already records.

⚠️ `read_fixture_labels.py` deliberately does NOT read the truncation session's
`truncation.json`: that dump joins text spans WITHOUT spaces (`'larinettiinB.'`)
and the production reader joins them with (`'larinetti in B.'`). A token rule
sees two different strings, and the span dump is the wrong artifact for asking
what the lexicon is handed.

⚠️ `benchmarks/omr-orchestral-e2e/fixtures/` is a build product regenerated on
every `orchestral_eval` run. The fixture figures here are from the fixtures on
disk on 2026-09-06.

## 8. One thing found in passing, unfixed and out of scope

**`instruments.lookup` costs about 0.6 s on a string that matches NOTHING.** It
walks ~400 aliases twice (exact, then OCR-folded), compiling a fresh regex per
alias, which thrashes `re`'s 512-entry cache. On the 310 unresolved labels of
the readers corpus that is three minutes of a probe's runtime, and in production
it is paid on every unmatched margin string. Nothing here changes it — `decide`
takes the caller's existing `Match` (`hit=`) rather than re-asking, so this
layer does not double it — but it is the reason the probes memoize, and it is
worth someone's afternoon.
