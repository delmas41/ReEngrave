# Who may disagree about the key, and who may not

Sean, 2026-09-08, in three messages that sharpen each other:

1. *"there will never be a case where one of the string instruments would have
   a different key than the others"*
2. *"only transposing instruments would ever disagree with everything that is
   not — if flute, oboe and all the strings agree then it is a very strong
   assumption that there is an established key"*
3. *"if we know what the key is by consensus and know what the transposing
   instrument is we should be able to know what the transposed key signature is
   by deduction, and evaluate what it reads based on how it compares to the
   whole"*

⚠️ He flagged the risk himself — *"maybe that is bypassing the problem and I
don't want to do that"* — and §5 says where he is right about that.

**Why it matters structurally.** `tools/omr/staged/groups.py:97` REFUSES a
key-signature redundancy across the staves of one system, and the recorded
reason is transposition: *"transposing instruments genuinely carry different
written keys at the same bar — a B-flat clarinet in a 3-flat movement is
`fifths: -1` — so disagreement here is correct engraving."* That refusal is
right about transposing staves and says nothing about the rest. Restricting the
witness set is not a workaround for the refusal; it is **the missing premise
that makes the refused group legitimate.**

---

## 1. Claim 1, measured: 142 agree, 7 disagree

`probe_string_key_agreement.py` reads `<key><fifths>` per part **per measure**
over all 1745 reference encodings. Per measure, not per header: a mid-movement
change reaching one string part and not another is the counter-example that
would matter, and a head-only test cannot see it.

    too_few_string_parts   1596
    agrees                  142
    DISAGREES                 7

⚠️ **COVERAGE, characterised rather than guessed.** Only 149 of 1745 files
carry ≥2 resolvable string parts. The first wording of this paragraph implied
the rest were partly lexicon failures; measured, they are not:

    solo_or_duo (<=2 parts)          1095
    multi-part, <2 strings resolved   501
    >=2 string parts (SCORED)         149

The 501 are dominated by **SATB choral works** — `Alto` 425, `Tenor` 424,
`Bass` 424, `Soprano` 423 — i.e. the library's Bach chorale holdings, which
have no string parts to disagree. So the exclusions are overwhelmingly
LEGITIMATE, and 149 is close to the library's whole orchestral subset rather
than an arbitrary tenth of it. **That strengthens the reading**: it is 142 of
149 orchestral scores, not 142 of 1745 with 1596 unexplained.

⚠️ One genuine unknown remains: **164 part-name occurrences are the EMPTY
STRING**, which resolve to nothing and are invisible to this test. Unquantified
as files.

⚠️ **A disagreement is not automatically a falsification** — it can be genuine
bitonality, scordatura, or an encoding artefact. All seven are printed with
their values so a human adjudicates; the probe never decides that itself.

| score | strings read | reading |
|---|---|---|
| Beethoven 7 mvt2 | Cello 1 = 3, **Cello 2 = 0**, rest 3 | almost certainly an ENCODING artefact — two cellos of one section cannot be in different keys |
| **Holst, Mercury (mvt3)** | Vln I −2, Vln II **3**, Vla −2, Vc **3**, Cb 0 | **GENUINE.** Mercury is explicitly BITONAL — two keys at once |
| Holst, mvt2 + full | Vlns 6, lower strings −3 | unadjudicated |
| Mahler 5 mvt1 | a lone `Violin` −4 vs `Erste/Zweite Violinen` 4 | unadjudicated; the lone part may be solo or mis-parsed |
| Ravel, Boléro | Violons 0, Altos/Celli/Basses −3 | unadjudicated; looks like a change that reached some parts only |
| Tchaikovsky 6 mvt1 | violins 0, violas/celli 2 | unadjudicated; B minor / D major, looks like a missed change |

⚠️ **I have not opened any of these scores.** Bitonality in Mercury is a fact
about the work, not a reading of this encoding. The rest are flagged, not ruled.

⚠️ **One exception this corpus does NOT contain, and theory does:
SCORDATURA.** A retuned string part is written transposed — Mahler 4 mvt 2's
solo violin is the canonical orchestral case. Absence here is a fact about the
corpus.

**So the claim is strong enough to be load-bearing and wrong rarely enough that
the exceptions are NAMEABLE. That is the profile of evidence, not of a gate.**

## 2. Claim 2 is better, and the same page shows its hole

The witness set is not "strings" but **every concert-pitch instrument**, which
takes it from ~5 staves to ~10. `instruments.py` already has the taxonomy:
`family` and `chromatic`.

⚠️ **THE OCTAVE TRAP.** Contrabass is `chromatic: -12`. That is an OCTAVE
transposition and does NOT change the key signature. The test is
`chromatic % 12 == 0`, never `chromatic == 0` — the naive form drops the bass,
the staff a witness rule most wants, being bottom-of-page and often unlabelled.
Piccolo (+12), Contrabassoon, Guitar and Tenor are the same shape.

⚠️ **Harp is `keyboard` in this repo, not `string`** — which is lucky and worth
keeping, because a harp's key signature is chosen for PEDAL and enharmonic
reasons and genuinely may differ. Do not "fix" that classification.

On `beethoven-sym5-mvt1-984073-p1` the concert-pitch set splits **8 to 2**:

| −3 | Flauti, Oboi, Fagotti, Violino I, Violino II, Viola, Violoncello, Basso |
| **0** | **Trombe in C, Timpani in C.G.** |

Both dissenters are concert pitch. **Natural brass and timpani print NO key
signature by 19th-century convention** and write accidentals inline.

**So a UNANIMITY rule breaks on the most famous page in the repertoire; a
MAJORITY rule survives 8–2.** And there is a third category to carry alongside
"transposing" and "not": **prints no signature by convention.**

## 3. Claim 3 is the strongest, and the field already exists

`instruments.py:13` documents `fifths_offset` as, verbatim, *"written key =
concert key + offset"* — exactly the deduction. `Match.fifths_offset` already
resolves it from the label's own `in X` suffix.

Taking concert = −3 by consensus on that page: **10 of 12 staves predicted
exactly.**

| staff | offset | predicted | truth | |
|---|--:|--:|--:|---|
| Clarinetti in B | +2 | −1 | −1 | ✓ |
| Corni in Es | +3 | 0 | 0 | ✓ |
| Flauti / Oboi / Fagotti / 5 strings | 0 | −3 | −3 | ✓ |
| **Trombe in C** | 0 | −3 | **0** | ✗ |
| **Timpani in C.G.** | 0 | −3 | **0** | ✗ |

**The two failures are the SAME single convention, not scattered noise** —
which is what makes this worth building on rather than tuning.

This is the biggest of the three because it converts transposing staves from
*excluded witnesses* into *predicted and therefore checkable*. It also
reframes the Viola from "do the strings agree" into **"the page says this staff
should read −3 and it read −1 — why"**, which is a question rather than a
correction.

## 4. And the clef half is already half-declared

Sean: *a different clef in the same key has the same accidentals in the same
order, just in a different location.* `adjudicate_key_signature`'s own
`checked_by` says it: *"the accidental ORDER is fixed (F#-C#-G#... /
Bb-Eb-Ab...): a run that SKIPS a slot is impossible"*. Order is
clef-invariant; only location moves. **That is why the Viola's failure could
never have been the alto slot table** — see
`benchmarks/omr-staged-shadow-2026-09/FINDINGS.md`.

## 5. ⚠️ Where the bypass worry is RIGHT

**On the Viola, a consensus repair would have produced the correct answer for
the wrong reason and hidden the real finding.** That staff's single box sits at
x 1161 against a system-wide accidental band of 580–948 — the locator found
something that is probably not a flat. Consensus would have overwritten −1 with
−3, scored a win, and left the wired-reader gap (D20) invisible.

**So: EVIDENCE, NOT REPAIR.** Record the contradiction against the disagreeing
staff; do not overwrite its verdict. That is the same call
`label_contradiction` already reaches — *additive evidence, not a gate* — and
it is the difference between a system that gets this page right and one that
knows why it was wrong.

## 6. What this does NOT establish

* 149 scores, not 1745. Six of the seven disagreements are unadjudicated.
* Nothing is wired. No group is declared, no deduction is computed in the
  pipeline, no accuracy arm was run.
* The 10-of-12 deduction is ONE page, and it was given the concert key. Deriving
  the concert key by consensus and deducing from it is a loop this has not run.
* Whether the "prints no signature by convention" set can be identified from the
  page is untested. It may need the era or the publisher, which is a fact about
  the edition and not about the staff.
