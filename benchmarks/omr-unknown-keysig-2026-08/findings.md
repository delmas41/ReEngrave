# An unread key signature is silently exported as C major — and it flattens the notes

**2026-08-30.** The pipeline knows perfectly well when it has not read a staff's
key signature: it sets `key_signature_read: false` and records
`key_signature_unread_reason`. It then discards that at the one place it
matters, substitutes C major, and resolves every pitch on the staff against it.

This is not a reporting problem. **It changes the notes.**

## The chain

```
_page_key_signatures()  ->  a staff the vote did not speak for is simply absent
transcribe             ->  seeded_fifths = voted_fifths.get(staff_idx)      # None
                           active_key_sig = alterations_for_fifths(seeded_fifths or 0)
                                                                            # {} — C major
pitch resolution       ->  elif letter in active_key_sig: final_alt = ...   # never fires
export.py              ->  staff.get("key_signature")  ->  0 sharps, 0 flats
```

`export.py` never mentions `key_signature_read` or `key_signature_unread_reason`
— grep it — so nothing downstream can tell "this staff is in C major" from
"nobody could read this staff". Both arrive as `<fifths>0</fifths>`.

## Measured on Beethoven 5 p.2, a page in C minor

22 staves carrying notes, across two systems. The pipeline read a signature on
**10**; the other **12** were resolved and exported as C major.

The consequence is visible without any ground truth at all — just count how many
resolved pitches carry an alteration in their spelling:

| staff group | notes altered |
|---|---|
| key signature **read** (3 flats) | 21%, 35%, 37%, 46%, 53%, 54%, 56%, 62% |
| key signature **unread** (C major) | **0%, 0%, 0%, 0%, 0%, 0%, 0%**, 4%, 5%, 9%, 11%, 28% |

Seven of the twelve unread staves emit **not one altered note** on a page in
three flats.

## How much of that is wrong, exactly

Not all of it, and the difference matters. The hand-read ground truth for this
page (`benchmarks/omr-key-signature/ground_truth.json`) gives 11 parts:

- **8 carry a real signature** — 3 flats for the flutes, oboes, bassoons and all
  the strings; 1 flat for the B♭ clarinets.
- **3 genuinely print none** — Corni, Trombe, Timpani. For those, C major is the
  right answer and the default is accidentally correct.

So of the 12 staves defaulted to C major, at most 6 (three parts across two
systems) are legitimately C. The rest are asserted wrongly, and every B, E and A
on them comes out natural where the page prints it flat.

## Why this is worth more than it looks

The clef work that has occupied this repository is measured at 50/52 staves —
96%. This costs roughly **half the staves on the same kind of page**, and it does
so silently: no warning fires, because from the pipeline's point of view nothing
went wrong. A staff simply has no key signature, and C major is what no key
signature means.

It also means the headline key-signature numbers understate the problem. "18
correct / 0 wrong / 16 missed" reads like an abstention. Downstream there is no
abstention — a missed signature is a C major assertion, and it is wrong on any
page not actually in C.

## The candidate fix, and why it is not applied here

The obvious repair is the one this pipeline already uses twice: **fall back to
the system's majority.** A page's parts share one concert key modulo
transposition, `key_signature_vote` already computes a per-system reference, and
check (b) already carries the circle-of-fifths machinery to compare a written
signature against a concert key. A staff nobody could read is far better served
by "whatever the other seventeen staves say, transposed" than by C major.

Not attempted in this commit, deliberately. Three plausible improvements were
built and rejected on evidence in the last two days, and the lesson each time was
that the mechanism has to be measured rather than argued. This one has what those
lacked — ground truth on three pages, an existing harness
(`eval_key_signatures.py`), and a prevalence measurement arriving from
`benchmarks/omr-corpus-sweep-2026-08` — so it should be built against those and
not before them.

The one thing that should NOT be done is to widen the defaulting. If the majority
fallback also cannot speak, the honest output is an absent key signature, not a
confident C.

### The machinery exists, and so does the trap

Checked before proposing it. `VoteResult.reference_written_by_system` already
holds each system's modal **written** signature, and
`key_signature_vote.consistent_written_set(reference)` already carries check
(b)'s circle-of-fifths logic. Nothing new has to be computed.

**But the reference is a WRITTEN signature, and a naive fallback would apply it
to transposing parts unchanged.** On this page that trade is close to a wash:

| ground-truth parts on beet5 p.2 | count |
|---|---:|
| 3 flats — flutes, oboes, bassoons, both violins, viola, cello/bass | 7 |
| 1 flat — clarinets in B♭ | 1 |
| **none — Corni, Trombe, Timpani** | **3** |

The modal written signature is 3 flats. Assigning it to every unread staff fixes
the unread members of the first group and **breaks all three of the second**,
which print no signature and are the staves the C-major default happens to get
right. A fallback that gains six staves and loses three has not obviously gained
anything, and this is exactly the shape of the three ideas already rejected this
week.

What makes it more than a wash is the transposition, and that is available:
`instruments.lookup` carries `default_fifths_offset` per instrument (clarinet 2,
horn 1), and contextual analysis supplies the identity — from the text layer, the
margin reader, or the score-order prior. Written = concert + offset, so a staff
whose instrument is known can take the concert key from the majority and print
its own correct signature rather than the majority's.

So the fix is really two: the fallback, and the transposition that stops it
being a wash. Build it against `eval_key_signatures.py` on all three
ground-truth pages, and check the horns and trumpets specifically — they are the
staves it can most easily make worse.
