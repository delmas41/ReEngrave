# The span composition step — measured, and the mechanism was none of the three

2026-09-06. Opened by the veto-refusal-pricing session's finding (`7ae5035d`)
that `OMR_MOVEMENT_REFERENCE`, default-ON on the strength of one work, makes a
**second** whole work four times worse:

| Brahms 1 / Breitkopf, pre-finale IMPOSSIBLE names | |
|---|--:|
| spans-off / veto-off | 36 |
| spans-off / veto-on | 14 |
| **spans-on / veto-off** | **149** |
| spans-on / veto-on | 133 |

That session traced it to `slots._align_by_span`'s composition step and named
four candidate mechanisms. **It is the fourth.** The three obvious ones are each
measured false here, which is the part worth keeping: the composition call is
not starved of labels, the document slots are not anonymous, and monotonicity
does not force the answer. The reference it was handed was wrong.

---

## 1. The measurement

`probe/diagnose_composition.py` dumps, for the composition call of every span:
which PAGE the span reference was read off with each staff's raw margin text,
whether `view.labels` is populated, whether the document slots carry
instruments, the monotone envelope, and the chosen embedding scored term by
term. Run against the veto session's committed Brahms read cache
(`out/diagnose-brahms.txt`).

    document reference (16 slots): Flute Oboe Clarinet Bassoon Contrabassoon
      Horn - Trumpet Trombone - Timpani Violin Violin Viola Cello Contrabass

    SPAN 0: pages 0-44
      reference system: page 35 system#1, size=14
      MECHANISM 1 CHECK: view.labels has 14 entries
      MECHANISM 2 CHECK: document slots WITH an instrument: 14 of 16
      MECHANISM 3 CHECK: local 7 can reach globals 7..9

| mechanism the handoff named | verdict | the number |
|---|---|---|
| 1. the label term is not live in that call | **FALSE** | `view.labels` has 14 of 14 entries, keyed on `staff_index` exactly as `align` reads them; the trace shows `+6.0` firing on eleven pairs |
| 2. the document slots carry no `instrument` | **FALSE** | 14 of 16 slots are named, including global 8 `Trombone` and global 10 `Timpani` |
| 3. monotonicity forces it | **FALSE, but only just** | local 7's envelope is 7..9, so global 10 is out of reach *for that reference* — but in the RIGHT reference Timpani is local **8**, whose envelope is 8..10 and does contain it. Monotonicity is not the constraint; the reference is |
| 4. something else | **THIS** | see below |

### The reference itself is a lineup the document reference cannot express

Page 35 system 1's own margin text, read straight out of the cache:

    local  5 raw='Hr. (E)'      -> Horn
    local  6 raw='Trpt. (E)'    -> Trumpet
    local  7 raw='Pk.'          -> Timpani
    local  8 raw='Viol. Solo'   -> Violin      <-- the second movement's SOLO VIOLIN
    local  9 raw='1Viol.'       -> Violin
    local 10 raw='2Viol.'       -> Violin

That system carries **six string staves and one horn staff**. The document
reference — the finale's lineup — has **five string slots and two horn slots**.
So the span reference is not a subsequence of the document reference: it holds a
part the document reference has no slot for. Nothing in the DP can place it
correctly, and the cheapest thing it can do is slide:

    l 7->g 8  label=Timpani  slot=Trombone  lab= -8.0   <-- LABEL CONFLICT
    l 8->g 9  label=Violin   slot=None      lab= +0.0

paying the module's only hard negative because every alternative costs more.
Every one of the span's **89 systems** then inherits that one placement, which
is why a single bad composition is 149 wrong staff records.

**It is a tie-break loss, not a mystery.** Thirty systems in the span have
fourteen staves. Seventeen of them share one ordinary movement-1 lineup and
label **thirteen** staves (the second horn staff carries only a crook — `(E)`,
`(C)` — which the lexicon correctly declines). Page 35 system 1 labels
**fourteen**, because a solo-violin staff is labelled. `reference_view` breaks
its size tie on label count, so the one-off wins.

`probe/span_candidates.py` prices every candidate (`out/candidates-brahms.txt`).
The seventeen siblings compose with **zero** contradictions, onto
`[0,1,2,3,4,5,6,7,10,11,12,13,14,15]` — skipping exactly the two trombone slots,
which is the right answer.

### A second signal was already computed and thrown away

`map_groups(span_view, document)` returns **None** for this span, and not for a
tie: the six-staff string block cannot be given room in the five-slot string
block, so *no* monotone assignment survives the `sz < sb[i][1]` guard. That
refusal is a structural statement — this lineup does not fit — and the current
code reads it as "withhold the group term". Recorded here rather than built on:
the label check below is stricter evidence and needs no bracket detection.

---

## 2. The change

`slots.py`, guarded by **`OMR_SPAN_REFERENCE_FIT`** (`search` default / `refuse`
/ `off`), following the `OMR_SLOT_GROUP_MAP` precedent — the fix is the default,
the old behaviour stays reachable to reproduce the measurement that refused it.

* **`_compose(span_view, reference)`** does the placement and counts
  CONTRADICTIONS: a local slot named X landing on a document slot named Y != X.
  Placed-whole (`align` returned no `-1`) was the only question the step used to
  ask, and it cannot fail here — the reference is bigger than the system, so
  something always fits.
* **`reference_candidates(views)`** exposes the ordered list `reference_view`
  was choosing from. ⚠️ **Element 0 is exactly what `reference_view` returned
  before**, asserted by a test, because the document-wide path reads the head and
  nothing else — a change there is a change to every score. The tail is new and
  has one consumer.
* **`_align_by_span`** walks the list and takes the first candidate that
  composes without contradicting a label; if none does, it refuses and leaves
  the caller on the document-wide path, which is what its docstring already
  promised for a span reference that "cannot be placed whole".

It counts contradictions, not doubts. An **unlabelled** local slot landing on a
named global one is not evidence of anything — it is the ordinary case for a
publisher that labels only its winds — and refusing on it would refuse almost
every Litolff span.

---

## 3. The numbers

⚠️ **Every arm below runs off ONE shared read pass per work** (the committed
caches; the margin read is flag-independent by construction), so the arms are
comparable to each other. ⚠️ **They are NOT comparable to the historical
figures.** `score_2x2.py`'s baseline guard fires on the Beethoven cache —
spans-off/veto-off impossible is **43**, against the 91 the whole-work session
recorded — because this is a different read pass. The guard is doing its job and
the guarded reading is honoured: no cross-run comparison is made anywhere here.

### Brahms 1 / Breitkopf, 86 pages, 1927 staff records (`out/brahms-ab.log`)

Pre-finale staves named `Trombone` or `Tuba`, the veto session's own rule.

| `OMR_SPAN_REFERENCE_FIT` | spans | veto | IMPOSSIBLE | self-contradicting |
|---|---|---|--:|--:|
| `off` (pre-fix) | off | off | 36 | 44 |
| `off` | off | on | 14 | 44 |
| `off` | **on** | off | **149** | 167 |
| `off` | on | on | 133 | 167 |
| `refuse` | on | off | **36** | 44 |
| `refuse` | on | on | 14 | 44 |
| **`search`** | **on** | off | **0** | 48 |
| **`search`** | on | on | **0** | 48 |

`off` reproduces the recorded 36 / 14 / 149 / 133 exactly — that is the harness
assertion, not a result. `refuse` collapses spans-on onto spans-off (the whole
span path is declined, on this work). `search` finds the sibling and takes the
work to **zero**, which is below the 36 of spans-off.

*Self-contradicting* is a staff whose own margin label the reader RESOLVED and
which is exported as something else — the veto session's reported-not-built
number, used here as the cost column `impossible` cannot be, since `impossible`
can only fall and would score a categorically-wrong name traded for an
ordinarily-wrong one as free. ⚠️ It is counted over ALL 1927 staff records here,
not over the impossible ones, so it is not the "132 of the 149" the commit
message quotes. Its detail is in `out/contradictions-brahms.txt`: `search`
spans-on fixes 2 (`Horn -> Tuba`), turns 12 impossible names into ordinary wrong
ones (`Timpani -> Trombone` becomes `Timpani -> Trumpet`), and adds 6 new
`Trumpet -> Horn` on pages 33-35 — the solo-violin pages, see section 4.

### Beethoven 5 / Litolff, 88 pages, 1616 staff records (`out/beet5-ab.log`)

**All three arms are BYTE-IDENTICAL, both spans settings** (`out/md5s.txt`):

| | IMPOSSIBLE | correct | wrong | unnamed | of 807 judgeable |
|---|--:|--:|--:|--:|---|
| spans-off / veto-off | 43 | 756 | 51 | 0 | |
| spans-off / veto-on | 0 | 756 | 50 | 1 | |
| **spans-on / veto-off** | **0** | **756** | **51** | **0** | every arm |
| spans-on / veto-on | 0 | 756 | 51 | 0 | |

The control is preserved by CONSTRUCTION, not by adjudication:
`probe/which_reference.py` shows both Beethoven spans pick candidate #0 and
compose with zero contradictions, so `search` never reaches candidate #1 and
`refuse` never refuses.

### The three regimes (`out/regimes.txt`)

| work | regime | pages | spans taken | flag reaches it | all three arms |
|---|---|---|--:|---|---|
| Brahms | narrow-at-the-front | 0-4 | 1 | no | identical |
| Brahms | narrow-anywhere, crossing | 40-49 | 2 | **yes**, composes clean | identical (spans help: 4 -> 0) |
| Brahms | ad-hoc two pages | 30,45 | 1 | no | identical |
| Brahms | whole work | 0-85 | 2 | **yes**, contradicted | 149 / 36 / **0** |
| Beethoven | narrow-at-the-front | 0-4 | 1 | no | identical |
| Beethoven | narrow-anywhere, crossing | 39-48 | 1 | no | identical |
| Beethoven | ad-hoc two pages | 23,44 | 1 | no | identical |
| Beethoven | whole work | 0-87 | 2 | **yes**, composes clean | identical |

The web app's own `OMR_MAX_PAGES=5` regime is untouched for both works: no
boundary is provable in five pages, so `_align_by_span` never runs.

### Reach: n=2 is the whole population, not a sample

`probe/reach.py` asks `movement_reference.lineup_spans` the reach question of
every work the boundary session left a committed staff profile for
(`out/reach.txt`):

| work | pages | spans | reach |
|---|--:|--:|---|
| beethoven 5 / Litolff | 88 | 2 | `_align_by_span` RUNS |
| brahms 1 / Breitkopf | 86 | 2 | `_align_by_span` RUNS |
| dvorak 9 / Simrock | 80 | **1** | flag unreachable |
| mozart 41 | 56 | **1** | flag unreachable |

So "measured on two works" is not a sample anybody chose — Dvorak 9 and Mozart
41 take no lineup boundary at all and this code cannot execute on them. Widening
the evidence needs a **new** whole-work read pass on a work whose lineup grows,
which is ~26 minutes per work and was not done here.

---

## 4. What was measured and REFUSED

**Refusing on the group-block infeasibility instead** (`map_groups` returning
None because no assignment gives every block room). It is the same fact from a
weaker direction: it needs the bracket detection, which this repo already
records as unstable across pages of one movement, and it returns None for three
other reasons (a tie, too many blocks, more system blocks than reference
blocks). The label check needs none of that. Recorded above, not built on.

**`refuse` as the default.** It is honest and it fixes the regression — Brahms
149 -> 36 — but it throws the span path away on this work entirely, including
the part of it that works: `search` shows the same span composed correctly is
worth 36 -> 0. `refuse` ships as an arm so the refusal can be priced apart from
the search, which is the only reason its row is in the table.

**Dropping the shape-recurrence tie-break in the candidate tail.** Priced rather
than kept on taste (`out/brahms1/-noshape-*`): without it the search picks page
0 system 0 instead of page 2 system 0 — same size, same 13 labels, but a
one-off lineup that labels the SECOND horn staff rather than the first. Same
`impossible` (0), self-contradiction **52 against 48**. Kept, worth 4, and it is
the module's own merge argument one level finer (`reference_view` prefers a
recurring SIZE because a merged system is a one-off; a lineup recurs for the
same reason). ⚠️ The unit tests do NOT exercise it — verified by mutation, they
stay green without it — so this measurement is the only thing holding it up.

**Relaxing the second alignment** (`align(view, span_reference)`), which is
forced one-to-one whenever a system has as many staves as the reference has
slots. That is where the residual +4 self-contradictions live: Brahms pages
33-35 print the solo-violin lineup, fourteen staves like everything else, so
against a fourteen-slot reference every staff is forced onto a slot and
`Trumpet` comes out `Horn` six times. Not built. It is a change to the DP that
every span and every document-wide alignment would inherit, on evidence from
three pages of one work, and spans-off gets the same pages wrong in a *worse*
way (there they come out `Trombone` and `Tuba` — categorically impossible rather
than merely wrong).

**Flipping `OMR_MOVEMENT_REFERENCE`.** Not this session's call. It is left
default-ON, untouched.

---

## 5. What this does NOT settle

* **`OMR_MOVEMENT_REFERENCE`'s own default.** With this fix Brahms goes 149 -> 0
  and Beethoven is unchanged at 0, so on the two works that can reach the code
  spans are now a benefit on both. That is n=2, and the pre-registered standard
  the veto session set — *a second whole work disagreeing reverses the call* —
  was met by that work and is now met in the other direction by the same work.
  Sean's call.
* **Whether a solo-violin page is its own lineup.** `movement_reference` finds
  boundaries from the size series, and Brahms's second-movement coda changes the
  lineup **without changing the staff count** (a horn staff out, a solo violin
  in). That is invisible to the rule by construction, and it is the residue this
  fix leaves behind.
* **Anything about scans, OMR-NED, or note recognition.** All 20 scan-gate rows
  and every `orchestral_eval` excerpt are single-page, so `_align_by_span` never
  runs on either and both are no-ops by construction — the same blindness
  `movement_reference.enabled()` already records for the flag it guards.

---

## Reproducing

    # the mechanism, cache-only, seconds
    python3 benchmarks/omr-span-composition-2026-09/probe/diagnose_composition.py CACHE --pages 0-85
    python3 benchmarks/omr-span-composition-2026-09/probe/span_candidates.py    CACHE --pages 0-85
    python3 benchmarks/omr-span-composition-2026-09/probe/which_reference.py    CACHE --pages 0-85

    # the numbers, ~30s per work off the committed caches
    bash benchmarks/omr-span-composition-2026-09/probe/run_brahms.sh
    bash benchmarks/omr-span-composition-2026-09/probe/run_beet5.sh
    bash benchmarks/omr-span-composition-2026-09/probe/run_regimes.sh

Brahms cache: the veto session's `benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/cache600`.
Beethoven cache: `benchmarks/omr-slot-alignment-2026-09/out/cache-beet5`. dpi 600 throughout.
