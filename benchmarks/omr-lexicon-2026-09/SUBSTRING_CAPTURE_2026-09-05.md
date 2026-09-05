# The lexicon's dangerous failure is CAPTURE, not absence

**2026-09-05.** Four independent workstreams routed a complaint at
`tools/omr/instruments.py` in one day, none of them owning it. This is what the
evidence turned out to be, what was fixed, and the one thing that had to be
measured before anything could be.

The survey came first and it reframed the request. **An instrument the lexicon
does not hold is harmless when it ABSTAINS and dangerous when a shorter alias
CAPTURES it** — and the capture is usually cross-family, which corrupts the
level the staff-identity workstream measures as its *stronger* one (family
precision 0.955 against instrument 0.873).

    python3 benchmarks/omr-lexicon-2026-09/probe_substring_capture.py --base origin/main

| | base | head |
|---|--:|--:|
| repertoire names **captured cross-family** | **7** | **0** |
| abstaining (safe gap) | 31 | 2 |
| correct | 20 | 56 |
| internal containment pairs NOT rescued by longest-first | 0 | 0 |

---

## 1. The survey, which is the part worth keeping

**Asked in two directions.**

**Internally the table cannot capture itself.** 131 alias-containment pairs
(`horn` inside `english horn`, `bass` inside `bass clarinet`, `tr` inside
`gr tr`) and **every one is rescued** by `_ALIAS_INDEX`'s longest-first order,
because the owner holds an alias at least as long as the thief's. 32 of those
pairs are cross-family and all 32 are rescued. This is the mechanism working
exactly as documented, and it is why the complaint could not be answered by
auditing the table against itself.

**Externally it captures whatever it does not hold.** The rescue depends on the
owner having a longer alias, and an absent instrument has none — so `horn`
inside `Basset horn` wins by default. Seven names in the repertoire screen were
captured cross-family before this batch:

| printed | actually | read as | how |
|---|---|---|---|
| `Basset horn` | woodwind (alto clarinet in F) | **Horn** [brass] | no entry existed, so `horn` had nothing longer to lose to |
| `Corno di bassetto` | woodwind | **Horn** [brass] | same, via `corno` |
| `Contrabass clarinet` | woodwind | **Contrabass** [string] | the QUALIFIER is the ten-letter alias and the noun is short |
| `Contrabass trombone` | brass | **Contrabass** [string] | same |
| `Contrabass tuba` | brass | **Contrabass** [string] | same, at **high** confidence |
| `English horns` | woodwind | **Horn** [brass] | `horns` is listed, `english horns` is not |
| `cors anglais` | woodwind | **Horn** [brass] | `cors` is listed, `cors anglais` is not |

They are three different faults wearing one symptom, and only two of them have
a mechanism.

---

## 2. `Basset horn` — no mechanism, and saying so is the finding

⚠️ **There is nothing here to derive.** That a basset horn is a clarinet, and
that a flugelhorn is not a horn, is lexical knowledge; no rule extracts it from
the string. The `Tr. Alt.` fix generalised because a *qualifier beaten by a
substring* is a shape a rule can see. Here there was no qualifier to lose,
because there was no entry.

So these are four plain entries — `Basset horn`, `Flugelhorn`, `Cornet`,
`Ophicleide` and their siblings — and the mechanism contribution is the SCREEN
above, which is what says these four were the ones that mattered and the other
31 absences were safe.

---

## 3. `Contrabass X` — the qualifier rule, generalised past the voices

This one *is* the `Bb (basso) Horn` mechanism, one family over.
`_prefer_instrument_over_voice` already encoded *"let an instrument noun beat a
register word in the same label"*; its qualifier set was the voices, derived
from their own aliases. **A voice is not the only instrument whose name doubles
as a size word.** `Contrabass` is the string bass AND the qualifier on
`Contrabass clarinet`, and at ten letters it beats every noun it modifies.

Renamed `_prefer_instrument_over_qualifier`, with
`QUALIFIERS = VOICE_QUALIFIERS | SIZE_QUALIFIERS`, both derived.

### ⚠️ The conjunction is the evidence, and `_STRIP_TOKENS` deletes it

Generalising the rule naively turns **every condensed bass staff into a cello**.
`Contrabass clarinet` is one instrument; `Contrabassi e Violoncelli` — the
commonest label at the foot of an orchestral score — is two staves printed on
one. Once `_STRIP_TOKENS` removes the `e`, the two are word-for-word identical.

So the rule tests ADJACENCY on `norm`, **before** the strip: a qualifier
modifies the noun beside it, and anything standing between them means the label
names two things rather than sizing one.

### ⚠️ And the adjacency test does NOT apply to the voice half

This asymmetry is measured, not tidy. A condensed staff pairs two INSTRUMENTS;
it never pairs an instrument with a voice, so the voice half has nothing
adjacency would protect and only loses reach to it. Applied to both halves it
regressed `Horn in B♭ basso` — a real name in the reference part-name corpus —
from Horn to a bass **voice**, because `in Bb` stands between the noun and its
qualifier. **The corpus caught this; no test would have.** The voice half is
left exactly as measured in 2026-08 and the new condition rides only on the
aliases that needed it.

---

## 4. Plurals — the hand-list was DIRECTIONAL, and that made it a wrong answer

The request called plurals a judgement call. They are not: they were producing
cross-family errors, by a mechanism worth stating.

**A word-bounded alias cannot fire inside its own plural** — `oboe` is followed
by an `s` in `oboes`, a letter, so the boundary refuses it. That is why the
table hand-lists `flutes`, `horns`, `cors`. It lists them **for the short
generic nouns and not for the long compounds containing them**, so pluralising
a label systematically DEFEATS the specific compound and hands the staff to the
generic noun inside it:

    English horns  -> Horn   [brass]      `horns` listed, `english horns` not
    cors anglais   -> Horn   [brass]      `cors`  listed, `cors anglais`  not
    bass clarinets -> Clarinet            `clarinets` listed, `bass clarinets` not

`_ALIAS_INDEX` is longest-first and can only do its job if both lengths of alias
have a plural. `_pluralize` derives them uniformly — last word only, ≥ 4
letters, `-es` after a sibilant — which restores the ordering. 303 forms, **0
colliding with an existing alias of a different instrument** (pinned by a test).
It does not widen the gate, for the same reason `_CONTRA_ALIASES` does not:
every generated string still has to appear in the label, word-bounded, exactly.

Plurals not formed on the last word are NOT derivable and stay hand-listed —
`cors anglais` and `corni inglesi` inflect the noun and leave the adjective.

### ⚠️ The derivation is switched OFF for the voices, and the corpus is why

**In French an orchestra's `Altos` are the VIOLAS and its `Basses` are the
double basses.** Deriving `altos` from the voice `alto` invented a cross-family
error on the single commonest French string label: **23 of the 1422-label
margin corpus's `Altos` are Ravel's violas and not one is a singer.** A register
word's plural belongs to whichever instrument the language gives it to, so
`aliases_of` skips the voices and `altos` / `alti` are listed on **Viola**,
declared ambiguous, because a chorus really does have altos.

This was the largest single movement in the first A/B run and it was a
regression. It is the reason a lexicon change is not verifiable by unit test.

---

## 5. `lookup("Basso")` — the answer was always there and nobody asked

`Basso` is the contrabasses at the foot of an orchestral score and the bass
voice under a vocal stave. The lexicon must name one and names the commoner, so
a caller comparing `.instrument.name` to a printed label scores the *other*
reading as an error. **It has now cost three harnesses a correct `Contrabass`
each** — `omr-part-staff-join-2026-08/RESULTS.md`, where it shipped undetected,
and two probes in `omr-staff-identity-2026-09/`.

`candidates_for_alias(m.alias)` always answered it. The failure is that a caller
had to know to ask, and three in a row did not.

⚠️ **`lookup`'s return shape is NOT changed** — it is consumed by 14 modules and
a silent behaviour change there is not worth the fix. `Match` gains two
properties, `alternatives` and `is_ambiguous`, so the ambiguity travels WITH the
answer instead of beside it. No existing call site moves.

`AMBIGUOUS_ALIASES` is now `_DECLARED_AMBIGUOUS_ALIASES` plus the plurals
`_pluralize` derives from it, because **an ambiguity is a property of the word,
not of its number**: `dossier.join_parts_to_slots` reads that dict as the set
that may not PIN a staff, so a plural missing from it is a *wrong pin*, not a
missing one. Declared entries always beat derived ones.

---

## 6. What it measures

**Two label corpora, replayed through both lexicons in one process**
(`resolve_labels.py --base origin/main`). Every change was adjudicated by hand;
**zero instruments were lost and zero resolutions moved to a worse answer.**

| corpus | strings | changed | resolved, base → head |
|---|--:|--:|---|
| margin labels (12 editions, the readers' own output) | 1422 | 27 | 1086 → **1112** |
| reference part names | 1271 | 13 | 866 → **878** |

All 40 changes: `Altos`→Viola ×23+2, `Cornet`→Cornet ×4, `Recorder` ×4,
`Harpes`→Harp ×2, `Oboes`, `Euphonium`, `Wood Blocks`, and two labels that were
resolving to a **voice** and now resolve to the instrument they name
(`3 SAXOPHONES …`→Saxophone, `Soprano Recorder`→Recorder).

**IMSLP instrumentation, 223 works** — a free second corpus with a different
distribution (prose, not margin abbreviations). Run on
`claude/instrumentation-capture-2026-09` with this `instruments.py` overlaid;
both arms re-derived offline with `--reparse`, **zero new IMSLP requests**. The
base arm reproduces the committed figures exactly, so the harness is
deterministic and the A/B is controlled.

| | base | head |
|---|--:|--:|
| fragments parsed | 2419 / 2518 (0.9607) | **2511 / 2560 (0.9809)** |
| abstained | 99 | **49** |
| works parsed COMPLETELY | 171 (0.7668) | **196 (0.8789)** |
| fragments needing the parser's flagged de-pluralisation | **195** | **0** |

That last row answers the request's judgement call with a measurement: the
parser's de-pluralisation workaround is now entirely unnecessary — the lexicon
handles plurals itself, which is where the knowledge belongs, and the workaround
can be retired by that branch at its own pace.

⚠️ **The residual has inverted.** It was "almost entirely lexicon gaps"; what is
left is almost entirely NOT — `orchestra`, `string quartet`, `continuo
(keyboard`, editorial footnotes (`*revised 2nd version (1878/80)`), and a
Rossini cast list read as instruments (`geltrude righetti-giorgi figaro`). Those
are parser scope, not vocabulary. `2 cornets` ×14, the largest single line, is
gone.

**Tests:** 2192 pass. One pre-existing failure,
`test_direction_text.py::TestReaderSelection::test_the_env_var_restricts_the_rungs`,
verified failing identically on a clean `origin/main` — an OCR-environment gate,
unrelated.

---

## 7. Every instrument whose resolution moved

Two workstreams are mid-build against this file
(`claude/staff-identity-layer-2026-09-05`,
`claude/edition-instrumentation-2026-09-05`). **This is the complete list of
behaviour changes**, not only the intended ones:

**Resolutions that CHANGED instrument** (4 strings across both corpora, all
toward the truth): `3 SAXOPHONES Sopranino en Fa …` Soprano→Saxophone;
`Soprano Recorder` Soprano→Recorder; `Basset horn` / `Corno di bassetto`
Horn→Basset horn; `Contrabass {clarinet,trombone,tuba}` Contrabass→the noun;
`English horns` / `cors anglais` Horn→English horn; `bass clarinets`
Clarinet→Bass clarinet.

**Newly resolving, previously abstaining** (nothing to regress): `Altos`/`Alti`
→Viola; `Cornet`/`Cornets`/`Kornett`→Cornet; `Flugelhorn`/`Flicorno`;
`Recorder`/`Recorders`; `Euphonium`; `Ophicleide`; `Serpent`; `Heckelphone`;
`Mandolin`; `Guitar`; `Bells`/`Cowbells`/`Gong`/`Slapstick`/`Wind machine`/
`Crotales`/`Marimba`/`Vibraphone`/`Guiro`/`Ratchet`/`Wood blocks`; and the
derived English plurals (`oboes`, `cellos`, `harps`, `tubas`, `piccolos`,
`saxophones`, `double basses`, `harpes`, …).

**Unchanged and pinned:** every ambiguous alias's first reading (`Basso`→Bass
voice, `Tp.`→Timpani, `Cor.`→Horn, `Tr. Bas.`→Trombone), the whole voice half of
the qualifier rule, the contrabassoon cross product, the OCR fold, and all four
condensed bass-staff forms.

⚠️ **One family decision is arguable and is flagged rather than buried.**
`Mandolin` and `Guitar` are filed **keyboard**, following the `Harp` precedent
in this table, because the families are consumed as SCORE POSITION and these
staves sit with the harp, above the strings. Filing them `string` would be right
about the instrument and wrong about every consumer.
