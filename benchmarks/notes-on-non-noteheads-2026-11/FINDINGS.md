# Notes written where no notehead is printed -- small test (ROADMAP 2.320, 2026-11-19)

STAGED, read-only, no build. A lane agent's report filed by the manager; "look" is the agent's look, not truth,
and Sean has seen none of the crops. Records 20261117-night, frozen sample pages; written notes taken from the
saved export (`overnight-20261117-night/compare/rank/*.tag-all.symbols.json`). Scratch and crops:
`out/print/2.320-notes-on-non-noteheads/` (untracked).

**Cause and lesson.** The problem is small: by look at least 12 of 4,308 written Litolff notes and 4 of 4,562
Brahms notes sit on no head (a wide-interval guess adds about 25 Litolff from one sampled group). The count that
prompted this (2.318's "46 / 11 stemless boxes written as quarters") was mostly real heads whose stem is hidden
in a barline or chord -- an agent's count checked before it opened a lane (rule 7). What it does show about the
process: claim-once is enforced only as a SHARE of the head's box, and a box that owns any stroke of its own is
never refused, so a head box can sit mostly on another mark's ink and still be written. No refusal is ever
undone later (0 re-admitted; all 8,870 notes carry one unsuperseded `notehead_is_not_a_notehead` verdict).

**Suspect measures** (from record fields): (a) box ink held by another mark's decided stroke at 25% or more --
Litolff 72 (17 at 50%+), Brahms 38 (13); mostly arc or tremolo ink inside real hollow heads. (b) stemless, not a
whole-note shape -- 138 / 72; real black heads in the sample. (c) head ink not head-sized -- 77 / 71; 4 of 12
Litolff sampled are beam ends or a slab. (D) claimed by something other than an arc or tremolo -- 8 of 33
Litolff and 4 of 10 Brahms are not heads (a `p`, an empty box, barline/stem slivers and tangles, a beam end, a
wedge after the key signature; two sharps, a flag tail, a slur end).

**Why the 16 were not stopped:** claim held under the 50% cut 8 (barline 26-41%, accidental 36%;
`claim_final.py:CUT`); at or over the cut but not refused 3 (a sharp at 85% whose box owns a stroke --
`ink_consult` refuses only boxes that own nothing; two held by key/clef rules that only narrow, written blue);
no claim exists 2 (beam strokes nobody owns -- the beam is a consumer, not a claimant, `stroke_owner.py:78`);
ink owned by a head 2 (beam end and slab read as heads); claimed by a LATER tier 1 (the dynamic `p`:
`stroke_owner.py:65-77` puts dynamic, mark and arc after head, and `held_by_earlier` counts only earlier tiers).

**Control that can fail.** The measures do flag true heads: judged-right durations (67 Litolff / 63 Brahms) --
any measure flags 5 and 2; hand-labelled Brahms page 0 (398 heads) -- any measure flags 20, about 5%. None of
the three is usable as a refusal as it stands.

**Not measured:** recall (non-heads outside all three groups); only 12 of 138 and 12 of 77 looked at in (b), (c).

**Outcome:** no lane. The two structural points -- beams claim no ink, and dynamics/words claim after heads --
belong with the claim-once gaps already listed in `benchmarks/no-value-notes-2026-11/FINDINGS.md` and with the
page beam reader (M4b-e), not a refusal bucket downstream.
