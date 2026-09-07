# The decision-TYPE axis — round 1

**Agent II, 2026-09-07 overnight audit.** Sean's question: *"analyze each decision
point … to determine effectiveness as well as explore what other information could
be helpful … Ask again if the type of decision — gating / probability etc — is the
best way to decide, and what are the downstream implications of the decision
type."*

⚠️ **This is a SCOPING round.** The schema (§1) plus two slices worked completely
(§3 the clef precedence ladder, §4 glyph ownership). The rest of the pipeline is
not covered and is not guessed at — §7 says what was left out, and §7.1 names the
round-2 candidate the coordinator's verify pass surfaced.

⚠️ **No pipeline behaviour changed.** Everything is a read-only probe over
committed artefacts plus source read against the tree. Probes and captured output
are under `probe/` and `out/`; each runs in seconds and writes nothing.

⚠️ **Tree stamp, and one correction to my own working copy.** All source reads and
all line numbers below were re-derived from the main checkout at **`350f0532`**
(after the coordinator's rebase: `docs/architecture-decision-map.md` at 1,629
lines, `tools/omr/transcribe.py` at 5,314). **Several line numbers in my brief had
drifted and are corrected here** — `_drop_clipped_notehead_fragments` is `:539`
not `:558`, `_drop_unladdered_noteheads` is `:3070` not `:3098`, the ownership
call sites are `:4715`/`:4722` not `:4682`/`:4689`. The clef-ladder numbers
(`:1594/:1604/:1656/:1708/:1769/:1789`) are correct as given.

⚠️ **Artefact stamp.** The committed transcriptions I measure were built by an
earlier tree. That is the normal substrate for this kind of probe (the
additive-vs-gated survey used the same files) and it is load-bearing exactly once
— in §3.2, where a guard landed after the fixtures were stamped. That case is
reconciled against the current code, not assumed.

⚠️ **What this round does NOT do.** It does not rebuild the decision map, and it
re-recommends no conversion
[`benchmarks/omr-additive-vs-gated-2026-09/FINDINGS.md`](../omr-additive-vs-gated-2026-09/FINDINGS.md)
measured and refused. I disagree with that survey nowhere. It also does not
re-report anything corrected by the map's own verification pass (`fbbd09c1`) — I
read that commit in full before writing.

---

## 0. The one-line answer

> **The pipeline's house style is the PRECEDENCE LADDER writing into a SCALAR
> SLOT, and its cost is not the ranking — it is the container. Both slices are
> dominated by one property no existing document classifies: IRREVERSIBILITY.
> Measured, `_dedupe_cross_staff_detections` parks 12.2% of its 4,521 verdicts
> for possible reversal and 0% in the shipped default; and the clef argmax
> overturns a staff's clef mid-page on 11 of 193 scan staves from a single
> detection at confidence as low as 0.32, of which the existing guard reaches
> 3 — and 0 with the shipped defaults.**
>
> **The type question has an answer the additive/gated framing cannot reach.**
> At neither of this round's worst sites is the right change gate → additive or
> gate → probability. A cell needs one clef and a glyph needs one owner, so the
> *commitment* is right. Two other things are wrong, and they are different
> repairs:
>
> 1. **SCALAR → RECORD.** The commitment overwrites its own evidence instead of
>    standing beside it. (`clef_final` is the counter-example that proves the
>    point: the one place a record IS kept, it is kept badly — 9 of its 20
>    occurrences are stale — and its only reader is its own keeper.)
> 2. **ALLOWLIST → SELF-CONTRADICTION TEST.** Where a guard exists, it is a
>    hand-listed set of two `(instrument, from-clef, to-clef)` triples. The
>    signal it is standing in for — *this staff contradicted its own header
>    reading, at confidence 0.32* — needs no instrument, and therefore is not
>    subject to the identity gate that (correctly) blocks the instrument route.

---

## 1. The schema, and the three changes I argue for

The brief's eleven fields are the right axes. Three changes, each forced by
something measured in §3 or §4 rather than by taste.

### 1.1 The schema as used here

| # | field | notes |
|---|---|---|
| 1 | **DECISION** + `file:line`, one sentence | |
| 2 | **TYPE** | hard gate · veto · threshold · raw argmax · precedence ladder · unweighted vote · additive score · abstention · deferral · **allowlist** |
| 3 | **CONSTRAINT or OPINION** | the additive-vs-gated §1 test — what licenses or condemns a gate |
| 4 | **EFFECTIVENESS** = reach × precision | reach MEASURED wherever an artefact can answer it, else `UNMEASURED` + the probe that would |
| **4b** | ⚠️ **MEASURED-ON vs FIRES-ON** | **NEW.** Which family the rule's evidence came from, and which family it fires on |
| 5 | **WHAT THE TYPE DESTROYS** | one of four named quantities (§1.4), never "information" |
| **6** | ⚠️ **REVERSIBILITY** | REVERSIBLE · IRREVERSIBLE-BY-DELETION · IRREVERSIBLE-BY-QUANTISATION |
| **6b** | ⚠️ **RECOVERY PATH, and is it ON** | **NEW.** A distinct state: reversible in principle, irreversible as shipped |
| 7 | **RECORDS ITS REFUSAL?** | yes / no / **yes-but-unreliable** (§3.3 forced the third value) |
| 8 | **DOWNSTREAM IMPLICATIONS OF THE TYPE** | who would have used what was destroyed; does a later stage re-derive it; does it make a later decision *look* unambiguous |
| 9 | **BETTER TYPE, and what must be TRUE for it to pay** | a specific condition, not a preference |
| 10 | **BLAST RADIUS + an A/B that can FAIL** | flag-off byte-identity is the project standard |
| 11 | **PRIORITY** = reach × per-firing cost × cheapness | |

### 1.2 Change 1 — REVERSIBILITY needs a companion field, because "reversible" has two states

`_dedupe_cross_staff_detections` parks rank-0 notehead verdicts in `deferred`
(`transcribe.py:2770-2790`) so `_apply_roster_range_veto` can reverse them once
identity exists. That path is real code and is measured — and it is
`OMR_ROSTER_RANGE_VETO`, **default `off`** (`transcribe.py:2619`), shipped off at
52 swaps for +24 edits. The honest classification of those 550 verdicts is
neither "reversible" nor "irreversible": it is *reversible in principle,
irreversible as shipped*. One field would have to pick one and would mislead
either way.

The same shape appears twice more in this round — the mid-staff clef veto behind
`OMR_INSTRUMENT_CLEF_DEFAULT` (§3.2) and `OMR_CONTEST_DUMP` (§4.3c). Three
independent instances is enough to make it a field.

### 1.3 Change 2 — MEASURED-ON vs FIRES-ON, because I found a live case where they are opposite

`_UNLADDERED_NOTEHEAD_MAX_CONF = 0.65` (`transcribe.py:2963`) is justified by an
empty gap: *"fakes 0.45-0.53 against 0.76+ for every real one"*. That gap was
measured on **three ENGRAVED works** —
[`benchmarks/omr-ned-2026-08/LADDER_EVIDENCE_2026-09-01.md:72-85`](../omr-ned-2026-08/LADDER_EVIDENCE_2026-09-01.md)
names them. Measured here, the rule fires **351 times on scans and 28 on
engravings**: 12.5× more often on the family it was *not* measured on, where the
surviving population is continuous through the constant (§4.4). A schema
recording only "sits on a measured gap" marks this green. It is not green.

The field generalises: this project's recurring trap is a rule priced on one
family or publisher and shipped for all — *"document roster transfer scored
Simrock 45/45 and Litolff 2/50, same rule"*
(`docs/handoff-probability-gates-2026-09-05.md` §2).

### 1.4 Change 3 — field 5 must name the quantity, and there are exactly four kinds

Making this closed rather than free-text is what let §3 and §4 be compared at all:

| destroyed | what it was |
|---|---|
| **the margin** | how far the winner beat the runner-up |
| **the runner-up** | the second candidate itself |
| **the disagreement** | that two readers said different things at all |
| **the object** | the detection / reading, deleted |

The first three are recoverable by writing them down — byte-identical to output.
The fourth is not, and that is why §6 ranks deletion sites above quantisation
sites at equal reach.

### 1.5 One thing I deliberately do NOT add

A "should this be a probability" column. The standard is settled and I apply it
rather than re-litigate it: **P(name) ECE 0.1277, P(set) 0.1301, top bin
promising 0.989 and delivering 0.692.** Every recommendation below is either
*record the number* or *accumulate signed evidence in arbitrary units with a
threshold*, which is what `slots._pair_score` already does. Neither is a
probability and neither is called one.

---

## 2. Method and substrate

| substrate | what it is | size |
|---|---|--:|
| `benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json` | committed scan transcriptions | 11 files, **193 staves**, 2,235 cells, 16,706 kept detections |
| `benchmarks/omr-orchestral-e2e/fixtures/*.omr.json` | committed engraved transcriptions | 11 files, **224 staves**, 1,517 cells, 8,523 kept detections |
| `benchmarks/omr-additive-vs-gated-2026-09/out/contests/*.contests.json` | the 20-row scan gate under `OMR_CONTEST_DUMP=1` | 20 rows, **4,521 contested pairs** |
| `benchmarks/omr-scan-e2e-2026-09/fixtures/*.truth.musicxml` | hand-verified truth windows | used only in §3.2 |

⚠️ **Two denominators, not mixed.** "of 193 staves" is the 11-file scan set; "of
4,521 pairs" is the 20-row set — the same convention as the additive-vs-gated
survey, for the same reason.

⚠️ **A survivor sample is biased and I say so at each use.** A committed
transcription holds what the pipeline KEPT. It can prove a population is
continuous across a threshold (§4.4); it cannot show what was deleted, because
those objects are gone. That asymmetry is itself a finding about the type (§5.3).

⚠️ **A00 applied.** Nothing here concludes a mechanism is wrong from a score.
§3.2 is the only place a decision is called wrong, and it is called wrong against
hand-verified truth MusicXML — not against a metric.

---

## 3. SLICE A — the clef precedence ladder

### 3.1 Reach of every rung, measured

`out/probe_clef_ladder_reach.txt`. Rung order in code: argmax over clef
detections (`transcribe.py:1594-1617`) → CV locator (`:1656`) → detector-on-header
(`:1708`) → specialist (`:1769`) → dossier (`:1789`).

| rung | scan (193 staves) | engraved (224) |
|---|--:|--:|
| **detector argmax** | **144 (74.6%)** | **212 (94.6%)** |
| CV locator | 5 (2.6%) | 0 |
| detector-on-header | 14 (7.3%) | 0 |
| specialist | 0 (not configured) | 0 |
| dossier | 0 (gate runs dossier-free) | 10 (4.5%) |
| **nothing read → positional default** | **30 (15.5%)** | 2 (0.9%) |

The 30 defaulted scan staves come out `treble` 20, `bass` 8, `alto` 2.

**Reading:** five rungs, and rung 1 answers three quarters of scan staves and
nineteen twentieths of engraved ones; everything below it is a 9.8% / 4.5% tail.
So the ladder's *ordering* is nearly irrelevant to the outcome. **The
consequential decision is rung 1's own internal one — a raw argmax at `:1604`.**

### 3.2 ⚠️⚠️ THE FINDING — a single mid-staff detection overturns a staff's clef, and the guard that exists reaches 3 of 11 (0 as shipped)

`transcribe.py:1594` initialises `best_clef_conf = -1.0`; `:1604` takes the
maximum with no floor. That function runs **once per measure cell**, and its own
comment (`:1610-1614`) says the per-cell tracking is deliberate: *"it tracks THIS
cell's reading, not the inherited `active_clef`"*. Consequence: a clef detection
in a **non-first** cell overwrites `active_clef` for the rest of the staff, at
any confidence, with no comparison against what that staff's own header already
read.

Every occurrence in the 11 committed scan transcriptions
(`out/probe_clef_midstaff_flips.txt`) — each triggered by exactly ONE detection,
the only clef detection in its cell:

```
row                    staff  instrument   change            at   class       conf   identity src
beethoven-575951-p2     s8    Violin       treble -> bass    m7   clefF       0.68   score_order
beethoven-575951-p2     s20   Violin       alto   -> treble  m1   clefG       0.58   score_order
beethoven-984073-p1     s9    Viola        alto   -> bass    m4   clefF       0.59   label
beethoven-984073-p1     s11   Contrabass   bass   -> treble  m3   clefG       0.66   score_order_ambiguity
beethoven-984073-p2     s8    Violin       treble -> bass    m6   clefF       0.73   score_order
brahms-317803-p1        s9    Violin       treble -> bass    m3   clefF       0.32   label
brahms-317803-p1        s12   Cello        tenor  -> bass    m5   clefF       0.82   label
brahms-317803-p2        s2    Clarinet     treble -> bass    m3   clefF       0.35   label
brahms-317803-p2        s11   Viola        alto   -> bass    m5   clefF       0.41   label
mahler-p3               s6    Trombone     bass   -> tenor   m3   clefCTenor  0.60   label
mahler-p3               s10   Violin       treble -> tenor   m3   clefCTenor  0.55   label
```

**11 of 193 scan staves (5.7%). 0 of 224 engraved staves.**

**Adjudicated against the truth MusicXML** — the same hand-verified windows the
scan gate scores against:

| row | mid-part clef changes in TRUTH | verdict |
|---|---|---|
| `beethoven-984073-p1` | **none, across 18 parts × 16 measures** | both flips **WRONG** |
| `brahms-317803-p1` | exactly one: measure index **5**, sign **F** (bass) | s12 Cello tenor→bass at **m5** — **CORRECT** on index and target. s9 Violin treble→bass at m3 matches nothing — **WRONG** |
| `mahler-p3` | one: measure index 4, C clef line 4 (tenor) | one of the two m3 tenor flips is plausibly it, the other is not — **not adjudicated**, the part↔staff join is not established |
| `beethoven-575951-p2`, `-984073-p2`, `brahms-317803-p2` | changes exist, at measure indices past the window's usable range | **not adjudicated** |

**At least one flip is right, at least three are demonstrably wrong, and nine of
eleven are musically implausible on their face** (Violin → bass ×3, Violin →
tenor, Viola → bass ×2, Contrabass → treble, Clarinet → bass).

#### ⚠️ A guard EXISTS, and its reach is the finding

`git log --all -S "MID_STAFF_CHANGE_VETOES" -- tools/omr/` → one commit
(`9051487b`). `clef_correction.veto_implausible_clef_changes` (`:460`) walks each
staff's measures and undoes a mid-staff change whose
`(instrument, from, to)` triple is listed. The table is
`clef_correction.py:444-447` and it has **two entries**:

```python
MID_STAFF_CHANGE_VETOES = {
    ("Violin", "treble", "bass"),
    ("Viola",  "alto",   "bass"),
}
```

Two further conditions: the staff's `instrument_source` must be `"label"`, and
the whole tier is behind `OMR_INSTRUMENT_CLEF_DEFAULT`, **default off**
(`contextual.py:1003`, call site `:1517-1521`).

Applied to the eleven measured flips:

| gate | flips it reaches |
|---|--:|
| triple is in the table | 5 of 11 |
| … **and** `instrument_source == "label"` | **3 of 11** (beet984073-p1 s9, brahms-p1 s9, brahms-p2 s11) |
| … **and** `OMR_INSTRUMENT_CLEF_DEFAULT` on | **0 of 11 as shipped** |

Of the eight it does not reach, **two are correct** and the table is right to
omit them (Cello tenor→bass, Trombone bass→tenor). The remaining **six are
implausible and escape**: three because the triple is not listed (Violin
alto→treble, Clarinet treble→bass, Violin treble→tenor), two because the
identity source is `score_order` although the triple IS listed, one for both
reasons.

⚠️ **The identity gate is CORRECT and I am not proposing to widen it.** It is
defended by held-out evidence reproduced twice independently — *Viola read as
Violin ×3* — and by a measured regression when a `score_order` identity was
admitted next door. `clef_correction.py:476-497` states this at length and the
statement holds.

**That is precisely why the repair is a different decision.** The evidence that
covers all six escapees names no instrument at all: *this cell's clef reading
contradicts the reading this same staff's own header produced, and it does so at
confidence 0.32*. It needs no identity, so the identity gate does not apply to
it — and the shape is one the codebase already uses:
`contextual._fill_defaulted_clefs` takes a staff's clef from the same part's
reading on another system (measured 48/52 → 49/52), i.e. two independent looks at
one fact, which the map's §4.1 provenance rule expressly permits.

**What a confidence floor would do on this sample:** 0.40 blocks 2, 0.60 blocks
6, 0.70 blocks 9, 0.80 blocks 10. The one flip corroborated correct against truth
is the **highest-confidence of the eleven** (0.82). ⚠️ **n=1 correct. That is the
observation that ranks the item; it is NOT a proposal for a constant**, and the
corpus is the prerequisite.

⚠️ **A00 discipline, explicitly.** (1) The comparison is valid — the shipped
fixtures, read against their own committed truth. (2) No metric is charging: the
claim is that a Violin staff is pitched in bass clef for four measures, a fact
about the output. (3) A downstream consumer can use the right answer —
`pitch_resolver` uses whatever `active_clef` holds. (4) Only then, the mechanism —
and the mechanism is *not* "the detector is wrong". The detector is allowed to be
wrong. **The mechanism is that an unfloored scalar overwrite is the wrong TYPE
for a decision this consequential, and that its existing guard is an allowlist
where the available evidence is a contradiction.**

### 3.3 ⚠️ `clef_final` is the record — and 9 of its 20 occurrences are stale

The map's newly-added stage-8a row is right that a mid-staff change is recorded:
`transcribe.py:4674-4679` writes `clef_final` when the staff's end clef differs
from its first-cell clef. Measured, **20 of 193 scan staves carry it**, and it
covers all 11 flips. So "the flip goes unrecorded" would be false and I do not
claim it.

What is true is worse in a more specific way:

- **9 of the 20 are stale.** On those staves `clef_final == staff["clef"]` and
  *every* measure carries the same clef — the field announces a change that no
  surviving measure shows (Dvořák p5 ×7, Mahler p3 ×2). Both of those systems
  report `n_measures_dropped_as_furniture = 1`, and
  `_drop_furniture_measures` reassigns `staff[field] = kept[0][field]` for
  `clef`/`key_signature`/`time_signature` when a LEADING measure is dropped
  (`transcribe.py:3062-3065`) — which makes `staff["clef"]` agree with the
  post-change measures while `clef_final` keeps its earlier value.
  ⚠️ **Strongly indicated, not proven by a controlled run**: the correlation is
  2 of 2 systems and the mechanism is in the code, but I did not A/B it.
- **Its only reader is its own keeper.** The map's new CONSUMED BY column states
  it and I verified it: `grep -rn clef_final tools/omr/ backend/ frontend/src`
  outside tests returns `clef_correction.py:550-552`, which reads it *solely to
  keep it consistent* after a veto, plus the two write sites. Not `export.py`,
  not the backend, not the frontend.
- **It records the fact and not the evidence.** No measure index, no confidence,
  no runner-up. So the record cannot distinguish the Brahms Cello's correct
  0.82 change from the Brahms Violin's spurious 0.32 one — which is exactly the
  discrimination a consumer would need.

This is why field 7 needed a third value. *"Records its refusal"* is not binary:
a record that is stale 45% of the time, carries no evidence, and is read only by
its own maintainer is closer to no record than to one.

### 3.4 The argmax's contest population — the margin, the runner-up and the disagreement

`out/probe_clef_argmax_contests.txt`, per cell:

| | scan | engraved |
|---|--:|--:|
| cells with ≥1 clef detection | 197 | 230 |
| cells with **≥2** — a genuine contest | **39** | **90** |
| … margin < 0.05 | 9 | 14 |
| … margin < 0.10 | 17 | 25 |
| … **runner-up a DIFFERENT class** | **12 of 39** | **19 of 90** |

Different-class contests include `clefG 0.90 / clefF 0.90` — a dead heat between
treble and bass — plus `clefCAlto 0.40 / clefG 0.34` and `clefF 0.92 /
clefCTenor 0.88`. **Nothing is recorded.** There is no `clef_candidates` list,
unlike `pitch_candidates` at the sibling site, and
`git log --all -S "clef_candidates" -- tools/omr/` returns **zero commits on any
branch** — never built, never removed. `git log --all -S "min_clef_conf"` is
likewise empty: no confidence floor for a clef has ever existed here.
`best_clef_conf` appears in exactly one commit (`14087860`, Phase 4a) and has
never been revisited.

### 3.5 The locator gate is a PRESENCE gate, and ≥22 scan cells silence it on sub-0.60 evidence

`transcribe.py:1656` — `if read_clef and locate_c_clefs and clef_source is None`.
The gate is the *existence* of a detector clef, not its strength
(`out/probe_clef_winner_confidence.txt`):

| winning clef detection confidence | scan (n=197) | engraved (n=230) |
|---|--:|--:|
| median | 0.904 | 0.969 |
| **under 0.60** | **22** | 5 |
| under 0.40 | 10 | 3 |

So on at least 22 scan cells a detector clef under 0.60 silences three downstream
readers at once — the CV locator (which reads C clefs by *geometry*, not by a
training distribution), the header-detector rung and the specialist. On ten of
them the silencing evidence is under 0.40.

⚠️ **Reach, not accuracy**, per this project's own reach-before-accuracy rule. It
says how many staves a floor could reach. It does **not** say the locator would
have been right on them; the locator's own recorded trade is *"8 false positives
removed for 20 declined C clefs"*, and its five firings are its entire production
reach.

### 3.6 `clef_geometry.resolve_clef` — a measurement and a guess return the same shape

`clef_geometry.py:239`. The good path returns
`ClefRead(source="geometry", residual=…)` (`:292`); where the family is unknown,
the anchor is missing, the snap fails, or `residual > max_residual`, it returns
`ClefRead(name=fallback, source="class", line=None)` (`:275`, `:279`, `:288`).
The argmax at `:1604` inspects **neither `source` nor `residual`** — a geometry
read that measured the named line and a class-label fallback that measured
nothing are the same object to the caller, ranked purely by the detector's
confidence in the *box*.

**UNMEASURED, and measurable:** record `source` and `residual` at `:1607`; the
question is what share of the 144 scan / 212 engraved detector-supplied clefs are
fallbacks rather than measurements. The map's new CONSUMED BY column already
states the consumer side (`ClefRead.residual` and `.line` → `probe`; `.family` →
`NOBODY`).

### 3.7 Slice A rows

| # | 1 DECISION | 2 TYPE | 3 C/O | 4 REACH (measured) | 4b measured-on / fires-on | 5 DESTROYS | 6 REVERSIBILITY | 6b RECOVERY | 7 RECORDS REFUSAL |
|--:|---|---|---|---|---|---|---|---|---|
| **A1** | `transcribe.py:1604` — the cell's clef, argmax with no floor, re-run per cell | **raw argmax** | OPINION | supplies 144/193 scan, 212/224 engraved; contested in 39 / 90 cells; **overturns a staff mid-page 11×** | n/a / flips are 11 scan : 0 engraved | **the margin, the runner-up, the disagreement**, and by overwriting `active_clef`, **the object** | **IRREVERSIBLE-BY-DELETION** for the pitches already resolved; the staff-scope clef pair survives | `clef_final` (§3.3) — no consumer | **yes-but-unreliable**: 9 of 20 stale, no evidence carried |
| **A1b** | `clef_correction.py:460` — undo an implausible mid-staff change | **allowlist** of 2 `(instrument, from, to)` triples + identity gate + a default-off flag | OPINION (the triples), CONSTRAINT (the identity gate — measured, keep) | **3 of 11** flips by triple+source; **0 as shipped** | Beethoven/Brahms string staves / both | the change it undoes is restated; the *unlisted* changes leave no trace | REVERSIBLE (it is itself the reversal) | `OMR_INSTRUMENT_CLEF_DEFAULT`, **off** | yes — `clef_change_veto` on the staff |
| **A2** | `transcribe.py:1656` — may the CV locator speak | **hard gate on presence** | OPINION dressed as structure | locator supplies 5/193; **≥22** scan cells silence it on conf < 0.60, 10 under 0.40 | n/a | the losing reader's entire opinion | IRREVERSIBLE-BY-DELETION (the locator never runs) | none | **no** |
| **A3** | `:1708` header rung, `:1769` specialist rung | precedence ladder, gap-fill | OPINION | header rung 14/193 scan, 0 engraved; specialist 0/0 | n/a | **agreement** — two rungs saying the same thing is worth nothing | REVERSIBLE (nothing deleted; a rung simply never runs) | none | **no** |
| **A4** | `:1789` dossier override — overwrites even a read clef | **veto / override** | **CONSTRAINT** (external truth about the work) | 10/224 engraved, 0 scan | n/a | nothing | n/a | n/a | **YES — `clef_overridden_by_dossier`, the only real record in the slice** |
| **A5** | `clef_geometry.py:239` — geometry read or class fallback | abstention **collapsed into the same return type** | OPINION | UNMEASURED (§3.6) | n/a | the reading's **provenance** and its residual | IRREVERSIBLE-BY-QUANTISATION | none | partially — `residual` is on the object and no caller reads it |
| **A6** | `clef_locator` veto chain — `header_ink.py:314`; `clef_locator.py:480`, `:771`, `:795`, `:804`, `:821`, `:843`, `:850` (`_has_f_clef_dots`, def `:547`), `:865` | **chain of hard vetoes**, each destroying its own measurement in the expression that forms it | OPINION | 5 located staves; the *rejections* are unmeasured in production | n/a | **the margin at seven continuous quantities** (`bw`,`bh`,`aspect`,`cx/w`,`dx`,`dy`,`dw`), plus `symmetry` computed at `:840` and dropped at the `:843`/`:850` refusals | IRREVERSIBLE-BY-DELETION | none | **the recorder EXISTS and no pipeline call site switches it on** — `grep -rn "trace=" tools/omr/*.py` returns nothing; sites are `transcribe.py:1677`, `:4286` |

**Fields 8–11 for the two that matter.**

**A1 / A1b — downstream implications of the type.** Every note after the flip is
pitched against the new clef. `staff_dict["clef"]` is the *first* cell's
(`transcribe.py:4551`), so the staff record and the measures disagree, and
`export._staff_measures_xml` takes `measure.get("clef") or clef` — the measure
wins, and the exported part changes clef with nothing distinguishing a real
change from an overwrite. Further downstream, `clef_correction.propose_clef` is
later asked whether this staff's clef is wrong and has access to none of it: not
the runner-up, not the margin, not that the staff contradicted itself. It
re-derives an answer from register instead — the map's "forces a later stage to
re-derive the same fact" pattern — and the additive survey measured that path
producing **5 proposals on 193 scan staves and applying 0**.
**9 — better type.** *Not additive, not a probability.* A cell needs one clef. The
type that fits is **argmax + an ASYMMETRIC floor + a record**: establishing a
clef where none is in effect is the cheap case; **overturning one already in
effect on this staff is the expensive case** and should carry a higher bar,
because the staff has already spoken. **What must be TRUE for it to pay:** that
correct mid-staff flips carry systematically higher confidence than spurious
ones. On this sample they do (the one corroborated flip is the maximum of
eleven) — **n=1, so this is a hypothesis and the corpus is the prerequisite.**
An equally cheap variant needs no confidence at all and is worth pricing beside
it: *require a mid-staff change to be corroborated by more than one cell.* Nine
of the eleven flips rest on a single detection in a single cell.
**10 — blast radius + an A/B that can fail.** `OMR_CLEF_MIDSTAFF_MIN_CONF`,
default `0.0` ⇒ byte-identical (assert on both families' MusicXML). An arm at
0.75 changes the measure-level clef on 9 of 193 scan staves and nothing else.
**The control that can fail: the Brahms p1 s12 flip is CORRECT against truth and
must survive.** A floor that loses it is disqualified whatever the pooled number
does. Price on per-row **note recall**, not OMR-NED — a clef restates pitches and
the gate's noise floor is ±6 edits.
**11 — priority: HIGHEST in the slice.** 5.7% of scan staves × the pipeline's
highest per-error cost (a whole staff of wrong pitches) × one comparison and one
dict key. And ⚠️ it is **coupled to the held `OMR_INSTRUMENT_CLEF_DEFAULT`
decision** — a floor would reduce what A1b has to catch, so the two should be
priced together, not unilaterally.

**A6 — downstream implications of the type.** Seven vetoes collapse real numbers
to bools, and the one that survives to the end (`LocatedClef.symmetry`, rounded
to 4dp) is `probe`-only. The vetoes are not thereby wrong —
`dot_single_clear_is_enough` is a *recorded, deliberate* trade. The cost is that
the trade cannot be re-priced without re-running the pipeline, which is why the
additive survey had to reimplement `propose_clef` next door.
**9:** unchanged type, plus the trace. **10:** passing `trace={}` at `:1677` and
`:4286` and stashing it is byte-identical by construction (the trace is
write-only). **11 — the cheapest item in the whole audit**: the recorder is
written and tested and two call sites do not pass it.

---

## 4. SLICE B — glyph ownership

Three decisions delete detections: `_drop_clipped_notehead_fragments:539` (at
detection time, inside the cell pass), `_drop_unladdered_noteheads:3070` (called
at `:4715`) and `_dedupe_cross_staff_detections:2645` (called at `:4722`).

### 4.1 Reach, measured (`out/probe_ownership_reach.txt`)

| | scan (11 files) | engraved (11 files) |
|---|--:|--:|
| detections KEPT | 16,706 | 8,523 |
| noteheads KEPT | 4,339 | 1,557 |
| cross-staff duplicates removed | **1,446** = 8.0% of all detections made | **2,592** = **23.3% of all detections made** |
| clipped notehead fragments dropped | 101 (2.3% of kept noteheads) | 46 (3.0%) |
| unladdered noteheads dropped | **351** (8.1% of kept noteheads) | 28 (1.8%) |

⚠️ **The engraved figure is the surprise, and it is in no existing document.**
Nearly a quarter of every detection made on a conductor's engraving is deleted by
one rule whose bottom tier is distance to a staff band. The scan figure is a third
of that. (Denominators are *made* = kept + removed.)

### 4.2 ⚠️ Reversibility — 87.8% by construction, 100% as shipped

`out/probe_ownership_reversibility.txt`, over the 20-row contest dump (4,521
pairs, reproducing the recorded figure exactly). `transcribe.py:2770` parks a
pair only when `deferred is not None and is_note and rank == 0`, so the only
verdicts that can ever be revisited are noteheads decided by distance:

| category | contests | ladder | distance | **reversible** |
|---|--:|--:|--:|--:|
| structural (beam/tie/slur/staff/ledger) | 2,197 | 0 | 2,197 | **0** |
| dynamic | 869 | 0 | 869 | **0** |
| notehead | 816 | 266 | 550 | **550** |
| ornament | 215 | 0 | 215 | **0** |
| accidental | 198 | 0 | 198 | **0** |
| flag | 102 | 0 | 102 | **0** |
| rest | 91 | 0 | 91 | **0** |
| clef | 24 | 0 | 24 | **0** |
| time-sig digit | 7 | 0 | 7 | **0** |
| stem | 2 | 0 | 2 | **0** |
| **total** | **4,521** | 266 | 4,255 | **550 = 12.2%** |

**IRREVERSIBLE-BY-DELETION by construction: 3,971 = 87.8%.** And the recovery
path for the other 12.2% is `OMR_ROSTER_RANGE_VETO` (`transcribe.py:2619`),
default `off`, shipped off at 52 swaps for +24 edits. **So in the configuration
that actually runs, 0 of 4,521 ownership verdicts are ever revisited.**

That is the round's cleanest type-level statement: the pipeline's largest
overlapping population is resolved by its weakest evidence, and its one reversal
mechanism was built for 18% of that population and is off.

### 4.3 What the type destroys, quantified three ways

**(a) The higher-confidence copy, 44.8% of the time.** Both confidences are in
hand at the moment of decision — fetched at `transcribe.py:2801-2802` *only* for
the instrumentation blob. Over all 4,521 pairs the **deleted** copy scored higher
than the survivor **2,026 times (44.8%)**, 24 exact ties, |Δconf| median 0.064,
p95 0.343. This is **not** an argument that confidence should decide — the
additive survey measured it agreeing with the trusted ladder only **0.617
[0.558, 0.674]** and I do not dispute that. It is the *size of the quantity
thrown away*: on nearly half of four and a half thousand deletions, the surviving
record is the one the detector believed less.

**(b) The class disagreement — 436 pairs, and it is not what the framing
assumes.** The deduper requires the same *category*, not the same *class*. 436 of
4,521 contests (9.6%) carry different classes, and only **17** are the expected
`…OnLine`/`…InSpace` artefact of one glyph at two staff positions. The rest are
genuine reading disagreements:

```
beam / tie                118      dynamicF / dynamicP                 22
slur / tie                 74      flag16thUp / flag8thUp              18
beam / slur                71      accidentalFlat / accidentalNatural  15
staff / tie                18      flag16thDown / flag32ndDown         12
```

**An ownership rule is silently settling a classification dispute.**
`flag16thUp` vs `flag8thUp` decides a duration; `accidentalFlat` vs
`accidentalNatural` decides a pitch; `dynamicF` vs `dynamicP` decides an exported
dynamic. The deciding criterion is distance to a staff band, which has no opinion
about any of them, and the disagreement is recorded nowhere outside
`OMR_CONTEST_DUMP`.

⚠️ I make **no claim** that the disagreement predicts which side is right. It is
untested and testable — against the ladder as an internal gold standard, exactly
as confidence was tested (that survey's §1.3, n=266). That probe does not exist.

**(c) The band distances.** `OMR_CONTEST_DUMP` (`transcribe.py:2789-2812`)
records both confidences, both classes, both pitches and the deciding tier — and
**not the distances**, the single quantity that decided 94.1% of the verdicts and
that this project has already caught being a coin flip (5-62 px). Confirmed by
reading the write block: there is no distance field.

### 4.4 ⚠️ `_drop_unladdered_noteheads` — the constant's gap is real on the family it barely fires on

`transcribe.py:2963`, `_UNLADDERED_NOTEHEAD_MAX_CONF = 0.65` — the pipeline's one
confidence threshold outside `OMR_CONF_THRESHOLD`. Justified by an empty gap
measured on three ENGRAVED works
(`LADDER_EVIDENCE_2026-09-01.md:72-85`: fakes 0.45-0.53, lowest real 0.76).

Fires **351×** on scans, **28×** on engravings.

Confidence histogram of the **surviving** outside-staff noteheads
(`out/probe_unladdered_threshold_neighbourhood.txt`, 0.05 buckets):

```
scan (n=756 kept outside the band)
  0.50: 12   0.55: 19   0.60: 27   0.65: 35   0.70: 62   0.75: 132   0.80: 261
engraved (n=357)
  0.60:  1   0.65:  2   0.70:  0   0.75:   8   0.80:  27   0.85: 184
```

**On engravings the population is essentially empty across the constant; on scans
it rises monotonically straight through it.** A hard threshold on a continuum, in
the family where it does 92.6% of its work.

⚠️ **Survivor bias, stated.** Sub-0.65 survivors are those that found a ladder
rung, so this cannot show what was deleted. It is sufficient for the T1 claim —
the populations *overlap* at the constant on scans — and insufficient for any
claim about whether the deletions were right. What would settle that is an
`OMR_UNLADDERED_DUMP` recording every refused notehead with its confidence, rung
count and band distance: byte-identical, and the same *record the refusal* item
as everywhere else.

⚠️ **A00, deliberately: I am NOT proposing the constant move.** It may be exactly
right. The finding is that its stated justification — an empty gap — does not hold
on the family it fires on, so its *type* is currently unlicensed there and nobody
can tell, because the refusals are not recorded.

### 4.5 `_drop_clipped_notehead_fragments` — the one gate in the slice I would leave alone

`transcribe.py:539`, constant at `:532`. Height < 0.6 staff spaces AND touching
the crop edge. Interior noteheads 0.61-1.12, edge-grazed real notes 0.77-0.99,
fragments 0.29-0.56 — **T1 fails by construction**, exactly as the
probability-gates handoff requires. It is a CONSTRAINT in the useful sense: a
notehead is one staff space tall because that is what a notehead is.

One note on its type. It is blind to `confidence` — a 0.95 detection dies on
geometry alone — while its sibling `_drop_unladdered_noteheads` is built entirely
on confidence. The map flags that asymmetry; measured, the asymmetry is
**correct**, because the two rules answer different questions (*is this shape a
notehead* vs *is this thing on this staff*). Recording the dropped fragment's
confidence is still free and would let anyone re-check that.

### 4.6 Slice B rows

| # | 1 DECISION | 2 TYPE | 3 C/O | 4 REACH | 4b measured-on / fires-on | 5 DESTROYS | 6 REVERSIBILITY | 6b RECOVERY | 7 RECORDS REFUSAL |
|--:|---|---|---|---|---|---|---|---|---|
| B1 | `_dedupe:2645` **rank 2 — ledger ladder** | veto, completeness only | **CONSTRAINT** (an unbroken rung run physically joins glyph to staff) | 266/4,521 = 5.9% | both / both | the rung counts (only completeness survives) | IRREVERSIBLE-BY-DELETION | **none — ladder pairs are deliberately not parked** (`:2779-2784`, correctly) | no |
| B2 | `_dedupe:2645` **rank 1 — written range / hairpin-has-notes** | veto on the impossible | **CONSTRAINT** | **0 of 4,521 on scans** — `_staff_written_ranges` returns `{}` dossier-free | dossier runs / never on the gate | nothing (never fires) | n/a | `OMR_ROSTER_RANGE_VETO`, **off** | n/a |
| **B3** | `_dedupe:2645` **rank 0 — distance to band** | **tie-break promoted to the whole rule** | OPINION, a documented coin flip (5-62 px) | **4,255/4,521 = 94.1%**; 82% in categories no higher tier can reach | n/a / both | **the object**; plus the margin, both confidences, the class disagreement (436), and the band distances themselves | **IRREVERSIBLE-BY-DELETION** | 550 parked (12.2%) behind a default-off flag ⇒ **0 as shipped** | **no** — `OMR_CONTEST_DUMP` is off, and omits the distances even when on |
| **B4** | `_drop_unladdered_noteheads:3070` | **hard confidence threshold** 0.65 | OPINION (a detector score) | **351 scan / 28 engraved noteheads deleted** | **engraved / overwhelmingly scan** | the object, its confidence, its rung count, its band distance | IRREVERSIBLE-BY-DELETION | none | **no** — an integer counter only, and `n_unladdered_noteheads_dropped` is SERIALISED-ONLY |
| B5 | `_drop_clipped_notehead_fragments:539` | hard gate on an empty gap | **CONSTRAINT** | 101 scan / 46 engraved | engraved 3-work / both | the object; its confidence | IRREVERSIBLE-BY-DELETION | none | **no** |
| B6 | the doomed-set application loop `:2807-2811` | greedy, strongest-first | CONSTRAINT (avoids the non-transitive-IoU cluster fault, measured 0.2275 vs 0.2263) | every verdict | n/a | which verdicts were *skipped* because a side was already doomed | REVERSIBLE in principle (nothing new is decided) | n/a | no |

**Fields 8–11 for B3 and B4.**

**B3 — downstream implications of the type.** A deleted detection never existed
for `pitch_resolver`, `rhythm`, `voicing`, the consistency checks, the contextual
pass or the exporter. Every later stage sees a page that looks unambiguous: one
glyph, one staff, no record that two staves claimed it. **That mechanism was
already found from the other end** — CLAUDE.md records that 83% of re-attributed
dynamic letters are the target staff's *sole* evidence *because* distance had
already removed the twin. The 869 dynamic contests here are that population, and
their reversibility is zero.
**9 — better type.** The pairwise structure and the tier order are both
CONSTRAINTS and should not move (the cluster-winner refactor measured worse; the
ladder is a physical join). What is wrong is that the *bottom* tier is a deletion
at all: a coin flip that commits. The fitting type is **deletion + a record of
the contest on the SURVIVOR** — a `contested_with` field carrying the loser's
staff, class, confidence and band distance. Not additive, not a probability: it
is the P(set) half of the project's own standard, and *"an abstention is not a
dead end"* applied to a deletion.
**What must be TRUE for it to pay:** that a later stage can use the loser. Two
already exist — the roster range veto (needs identity, which runs later) and
`export._arbitrate_arcs_in_system`, which re-decides arc ownership at export time
and would benefit from knowing an arc was contested. ⚠️ Note **263 of the 436
different-class contests are arc classes** (beam/tie/slur), and
`OMR_ARC_ATTRIBUTION` is already default-**on** — so a consumer for exactly that
subset is already shipping.
**10 — A/B.** `OMR_CONTEST_RECORD=1` writing `contested_with` onto survivors:
byte-identical MusicXML by construction, asserted on both families. Nothing is
priced until a consumer exists.
**11 — priority: HIGHEST in the slice**, on reach alone.

**B4 — downstream implications of the type.** 351 scan noteheads are deleted at
page scope *after* pitch resolution, so the resolved `pitch` goes with them;
`n_unladdered_noteheads_dropped` reaches the JSON and nothing reads it. It is
also the only place a per-class or per-family confidence floor could be
prototyped cheaply, which matters because `OMR_CONF_THRESHOLD` — one global number
for 208 classes — is the probability-gates handoff's strongest candidate.
**9 — better type.** ⚠️ **Not additive.** The rule already combines two signals
(confidence AND rung count) and CLAUDE.md records that *"neither signal is
sufficient alone"* — a conjunction of two weak opinions. The honest upgrade is a
**two-dimensional record before any change to the rule**, because the current
form cannot tell "0.64 with zero rungs" from "0.30 with zero rungs".
**10 — A/B.** Record first (byte-identical). Any later threshold arm must be
priced on scan-gate **note recall**, and ⚠️ the metric will mislead: OMR-NED is
symmetric and rewards emitting fewer symbols, so deleting *more* noteheads can
improve it. The worked precedent is `OMR_ARC_ATTRIBUTION`'s `drop` arm, which
scored better by emitting 20 fewer slurs — 12 of them real — and was REFUSED.
**11 — priority: high, and cheap** — the record is one dict append.

---

## 5. TYPE as a systemic property

### 5.1 The house style is a precedence ladder over a scalar slot — the wrong *container*, not the wrong *ranking*

The shape recurs: an ordered list of readers, each gated on `X is None`, writing
into one variable. Clef (`:1604/:1656/:1708/:1769/:1789`); ownership (`_dedupe`'s
rank 2 → 1 → 0); meter (`backfill_page_time_signatures`); identity
(`_read_labels_for_page`'s rungs).

Measured, the ranking is nearly always right and nearly always irrelevant: rung 1
answers 74.6% / 94.6% of clef staves and rank 0 answers 94.1% of ownership
contests. **The real cost is structural rather than ordinal:**

- **A ladder cannot express agreement.** Two rungs agreeing is worth exactly
  nothing — the second never runs. On the clef ladder this is not hypothetical:
  25 scan cells carry a clef detection in a non-first cell; **14 agree with the
  staff's established clef and are worth zero, and 11 disagree and are executed
  with no floor.** Agreement is discarded; disagreement is acted on. That is
  backwards for a page where one fact is printed once and read many times.
- **A ladder writes into a slot, so the loser is not merely unused — it is
  unaddressable.** `pitch_candidates` exists at the sibling site; clefs have no
  equivalent and never have (`git log --all -S "clef_candidates"` → nothing,
  ever). A later stage that wants to reconsider has nothing to reconsider *from*,
  which is why `clef_correction` re-derives from register and reaches 5 proposals
  on 193 staves.
- **A ladder makes the output look unanimous.** After `_dedupe`, every surviving
  detection looks uncontested; after the clef argmax, every staff looks like it
  read one clef. Nine of the map's export gaps are the same shape one layer down.

**So the systemic recommendation is not "make the ladders additive".** It is:
*a ladder may keep its ordering and must stop overwriting.* Write the winner AND
the field it beat. That is the additive-vs-gated survey's shortlist item 1 stated
as an architectural property instead of a list of sites — and both of this round's
slices land on it independently.

### 5.2 Three costumes, not two

The map names `SCORE_LABEL_CONFLICT = −8.0` dominating a scorer whose maximum
non-label positive is +2.5 — a gate in additive clothing. This round adds two
more, and I think both are more dangerous:

**A gate wearing a TIERED-EVIDENCE coat.** `_dedupe`'s rank ladder reads like a
hierarchy of evidence strengths (ladder > range > distance), which is sound. But
the tiers are **mutually exclusive**: rank 2 firing means distance is never even
computed for comparison, and rank 0 firing means the ladder said nothing rather
than said "unbroken on neither side". A pair where a ladder and a distance point
the *same* way scores identically to one where the ladder alone spoke. That costs
nothing today (rank 1 never fires, rank 2 fires 5.9%), and it is why the
confidence-vs-ladder agreement test had n=266 rather than n=4,521.

**An evidence-free rule wearing an EXPERTISE coat.** `MID_STAFF_CHANGE_VETOES` is
two hand-listed `(instrument, from, to)` triples; `TREBLE_OVERRIDE_INSTRUMENTS`
is a four-name allowlist the additive survey already recommends replacing with an
additive margin term. Both read like domain knowledge and both are enumerations
standing in for a measurement that is available: in A1b's case, *the staff
contradicting its own header at 0.32*. **An allowlist's failure mode is
invisible by construction** — it does not decline, it simply never fires, so the
six escaping flips produce no signal of any kind.

**And a fourth, adjacent: a gate wearing a REPORT's coat.** `OMR_CONTEST_DUMP` is
documented as verdict-neutral reach instrumentation. It is also the *only* place
the pipeline records that two staves claimed one glyph — and it is off by default
and omits the deciding quantity. `clef_locator`'s `trace` is the same shape: a
complete recorder, written and tested, that no call site passes. **An instrument
that is off is not a record.**

### 5.3 Reversibility is orthogonal to the A–E taxonomy, which is why it is worth adding

A–E classifies what happens to the *number*. It does not classify what happens to
the *object*, and the two come apart in both directions:

| | number survives | number destroyed |
|---|---|---|
| **object survives** | (healthy) | Class B — `Match.coverage` → high/medium/low. Recoverable by re-reading the string |
| **object deleted** | not observed | Class A/E — `_dedupe` rank 0, `_drop_unladdered`, the clef overwrite. **Not recoverable at any cost short of re-running the pipeline** |

The bottom-right cell is where this audit's leverage is and it is invisible to
A–E. It is also what makes *record the refusal* more than tidiness: at a
quantisation site the number can be re-derived later; at a deletion site it
cannot, because the input is gone. **At equal reach, record deletion sites
first.**

### 5.4 Two properties the type analysis kept surfacing that no column captures

**(a) Scope mismatch.** A per-cell decision writing a per-staff fact (the clef
argmax); a per-pair decision writing a per-page fact (`_dedupe`); the map's own
§4.3 hazard, a per-system refusal guarding a document-wide write. In each case
the decision's evidence is narrower than its blast radius, and in each case the
error is invisible at the scope where it was made. On this round's evidence that
predicts where a bad decision hurts better than the A–E class does.

**(b) The evidence's family provenance** (§1.3). Two of this round's four
worst-behaved constants are engraved-measured and scan-fired.

---

## 6. Ranked conclusions

Priority = reach × per-firing cost × cheapness. Each names the measurement that
would settle it and whether an existing harness can SEE it.

⚠️ **Part names do not reach musicdiff at all**, so nothing scored on identity is
visible to OMR-NED, the 20-row scan gate or `orchestral_eval`. None of the seven
below is an identity item — deliberately, which is why they are measurable today.

| # | conclusion | evidence | what would settle it | harness can see it? |
|--:|---|---|---|---|
| **1** | **The clef argmax overturns a staff's clef mid-page from ONE detection at conf 0.32-0.82 — 11 of 193 scan staves, 0 of 224 engraved. ≥1 right, ≥3 demonstrably wrong against truth. The existing veto reaches 3 of 11, and 0 with shipped defaults.** | §3.2; `out/probe_clef_midstaff_flips.txt`; truth adjudication vs `*.truth.musicxml`; `clef_correction.py:444-447`, `contextual.py:1003` | `OMR_CLEF_MIDSTAFF_MIN_CONF` (and/or a two-cell corroboration rule) A/B on per-row **note recall**. ⚠️ Control that must not fail: the Brahms p1 s12 flip is CORRECT and must survive | **YES** — a clef restates pitches, so `scan_eval` note recall moves. ⚠️ give each arm its own `--tag=`; a cached A/B reports "identical" and the tell is wall time |
| **2** | **87.8% of ownership deletions are irreversible by construction; 100% as shipped.** The one recovery path covers noteheads only and is default-off | §4.2, 4,521 pairs | structural — nothing to settle. The action is `contested_with` on survivors, byte-identical | n/a until a consumer exists; ⚠️ one exists in outline (`OMR_ARC_ATTRIBUTION`, already on, and 263 of the 436 class-disagreements are arcs) |
| **3** | **`clef_final` is the pipeline's only mid-staff-change record and it is unreliable: 9 of 20 occurrences are stale, it carries no evidence, and its only reader is its own keeper** | §3.3; `transcribe.py:3062-3065`, `:4674-4679`; `clef_correction.py:548-552` | write the measure index and the triggering confidence alongside it; and A/B `_drop_furniture_measures`' clef reassignment against `clef_final` | n/a — it is a record |
| **4** | **`_UNLADDERED_NOTEHEAD_MAX_CONF = 0.65` was measured on engravings and fires 12.5× more on scans, where the surviving population is continuous through it** | §4.4; `LADDER_EVIDENCE_2026-09-01.md:72-85` | a refusal dump (confidence × rung count × band distance) for the 351 scan deletions, then hand-adjudicate a sample | ⚠️ **not safely** — OMR-NED is symmetric and rewards deleting noteheads. Price on note recall, and treat a pooled *improvement* as suspect (the `OMR_ARC_ATTRIBUTION` `drop` arm is the precedent) |
| **5** | **436 of 4,521 ownership contests are two DIFFERENT readings, not one glyph seen twice** — 263 arc-class, 47 flag (a duration), 38 dynamic, 31 accidental (a pitch) — and an ownership rule settles the classification silently | §4.3(b) | test the class disagreement against the ladder gold standard, exactly as confidence was tested (n=266) | partly — the probe needs no harness; acting on it would |
| **6** | **`clef_locator`'s trace recorder is complete and no pipeline call site passes it.** `grep -rn "trace=" tools/omr/*.py` → nothing | §3.7 A6 | pass `trace={}` at `transcribe.py:1677` and `:4286`. Byte-identical by construction | n/a |
| **7** | **The clef argmax cannot tell a geometry measurement from a class-label fallback** — `ClefRead.source` and `.residual` are on the object and no caller reads them | §3.6 | one-line probe recording `source`/`residual` at `:1607` | n/a — UNMEASURED, and the probe is free |

**And one conclusion about the audit itself.** Every item above is *record the
refusal*, except #1, which is *record the refusal plus one comparison*. The
additive-vs-gated survey reached that from the additive side; this round reaches
it from the reversibility side, on different sites and different data. **Two
roads, one destination — and it is not corroboration**, because the substrates
differ: §3 and §4.4 share nothing with that survey, and only §4.2-4.3 share its
contest dump.

---

## 7. What round 1 does NOT cover

- **Most of the pipeline.** Stages 1, 2, 3, 5, 7, 8b, 8c, 9, 10 and 11 are
  untouched. The map's §5 rows for them stand.
- **Precision, everywhere except §3.2.** Reach is measured throughout; only the
  eleven clef flips were adjudicated.
- **Whether the CV locator would be RIGHT on the ≥22 staves it is silenced on.**
  Reach only, per the reach-before-accuracy rule.
- **How often the two independent clef readings (`:4286` header vs `:1604`
  measure) disagree** — the map's own §10.1 UNMEASURED item. It needs a run, not
  an artefact: the header read is not written to the output.
- **The deleted objects' distributions** at all three ownership sites. §4.4's
  histogram is survivor-biased and says so.
- **A controlled A/B of the `_drop_furniture_measures` → `clef_final` mechanism**
  (§3.3). Correlation 2 of 2 systems plus the code path; not proven by a run.
- **Anything requiring `scan_eval` or `orchestral_eval`.** Not run — coordinator
  permission required, and not needed for a scoping round.

### 7.1 Round-2 candidates, in the order I would take them

1. ⚠️ **`direction_text`'s `accepted[0]` argmax (`direction_text.py:801`) over a
   `Reader` interface that carries no confidence at all.** Surfaced by the map's
   verification pass (72 uncatalogued decision points in that module) and it is a
   decision-TYPE finding of exactly this round's kind: a raw argmax whose ranking
   quantity *does not exist in the type it ranks*. Not diverted into here, at the
   coordinator's instruction. It also sits on ~75% of whole-work wall clock, so
   its blast radius is cost as well as correctness.
2. **Tie pairing (25 decision points) and slur pairing (46)** — in the spine with
   zero §5 rows, and §4.3(b) shows 263 of the ownership class-disagreements are
   arc classes, so the two slices meet there.
3. **`export.py`'s decision surface**, which the map calls the longest dead-signal
   list in the pipeline and where the reversibility question is trivial (nothing
   downstream at all) but the *quantisation* question is not.
4. **The meter chain** (`backfill_page_time_signatures` and the asymmetric
   specialist override at `:1777`) — the one precedence ladder in the pipeline
   whose later rung overwrites *unconditionally*, the opposite convention from the
   clef ladder in the same function.

---

## 8. Reproducing

```bash
cd /Users/seanjohnson/Desktop/ReEngrave
P=.claude/worktrees/nice-nash-085307/benchmarks/omr-pipeline-audit-2026-09/probe

python3 $P/probe_clef_ladder_reach.py                    # 3.1  rung reach, both families
python3 $P/probe_clef_argmax_contests.py                 # 3.4  contests + different-class pairs
python3 $P/probe_clef_midstaff_flips.py                  # 3.2  every mid-staff clef overwrite
python3 $P/probe_clef_winner_confidence.py               # 3.5  what silences the lower rungs
python3 $P/probe_ownership_reach.py                      # 4.1  the three deletion rules' reach
python3 $P/probe_ownership_reversibility.py              # 4.2  tier x category x reversibility
python3 $P/probe_unladdered_threshold_neighbourhood.py   # 4.4  the 0.65 constant's neighbourhood
```

Read-only; seconds each; committed artefacts only. Outputs captured under `out/`.
Fixtures are gitignored build products, so in a worktree the probes point at the
main checkout.

The two adjudications in §3.2 and §3.3 were done inline rather than in a script
and are reproduced by these:

```python
# §3.2 — mid-part clef changes in the truth
import xml.etree.ElementTree as ET, glob, os
for f in sorted(glob.glob("benchmarks/omr-scan-e2e-2026-09/fixtures/*.truth.musicxml")):
    r = ET.parse(f).getroot()
    late = [(p.get("id"), mi, c.findtext("sign"), c.findtext("line"))
            for p in r.iter("part")
            for mi, m in enumerate(p.findall("measure"))
            for c in m.iter("clef") if mi > 0]
    print(os.path.basename(f), late or "NONE")

# §3.3 — stale clef_final
import json
for f in sorted(glob.glob("benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json")):
    for pg in json.load(open(f))["pages"]:
        for sy in pg["systems"]:
            for st in sy["staves"]:
                seq = {m.get("clef") for m in st.get("measures", [])}
                if st.get("clef_final") and len(seq) == 1:
                    print(f, st["staff_index"], st.get("clef"), st["clef_final"],
                          sy.get("n_measures_dropped_as_furniture"))
```
