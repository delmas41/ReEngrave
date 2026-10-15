# What can a mark be? — the elimination table, round 2 (for Sean to correct)

You asked whether the reader does general deduction: *"this is a mostly oval shaped note on the staff —
therefore it can only be a few things."* This table is that deduction written down. Every mark gets four
rough facts: its **size** (in staff spaces), how much of its box is **ink**, where it stands **up and down**
(in the staff / just outside / far), and where it stands **along the bar** (clef-key slots, bar head, middle,
on a barline, left edge of the system). Each line below says what a mark of that shape in that place can
still be. Nothing here is wired into the reader yet.

## What changed since your answers (2026-10-14)

**Your answers, applied.** Only where you said *never* does the table rule something out:
- *Hairpin inside the staff* (Q5): ruled out. *Brace / bracket anywhere but the left edge of a system* (Q11): ruled out.
- *Dynamics on the staff, direction words on the staff, arpeggio lines* (Q3, Q4, Q10): **kept, marked "(rare)"**.
  They are never ruled out; they are only listed last, so a reader would want stronger evidence before choosing one.
  Instrument names in the left margin are NOT rare: they stand level with their staff all the time.
- *Rests outside the staff, whole/half rests off their usual lines, a second voice's rest hanging off the bottom* (Q6, Q7): kept. *Clef in mid-bar* (Q8): kept.
  *A courtesy accidental right after the clef and key* (Q9): kept.
- Your two label rulings: `q751` is an augmentation dot, `q880` is only a barline. I changed them in the **measurement only**
  (`truth_overrides.json`, with your words); your labelled file is untouched.

**My own numbers that were too tight, widened.** Round 1 lost 29 of your 1,566 marks to numbers I had set too narrow.
I widened them from what your marks actually measure, plus 15%: a dynamic *word* boxed as one mark (up to 14 sp wide),
a long thin box over a tilted barline, a wide flag, a barline fragment. Two shapes I did **not** widen for everything,
because it would have let hundreds of other marks in: a *short tie end that lies on a staff line* and a *long high tie*
now have their own allowance, and so does a *very wide flat beam piece*. After looking at the detector's own boxes
I also let time-signature digits and eighth rests be a little shorter/wider, because the detector boxes them partially.
And one number from the Litolff page (below).

## How it did

**Your Brahms page, 1,566 marks:** the right answer is still in the list for **1,563 (99.8%)**, up from 1,538 (98.2%).
The 3 that are not: the three marks you labelled `brace` at the far right of the system (`b4230`, `b4041`, `b4023`).
The table now says a brace is only at the left edge (your Q11), so it rules them out. The crops show a double
vertical line at the right end of the system, running through the staff — it looks like a closing barline, not a brace.
**Please say what those three are.**

**Your Litolff page (50 hollow half notes you drew in the test cells):** with the Brahms-measured numbers the right
answer was in the list for **46 of 49 (94%)**. Litolff's hollow heads read very dark (the hole is a sliver), darker than
I allowed. I widened that one number and now it is 49 of 49 — but I measured it on those same 49, so that is not a
fair test. The honest finding: on Litolff, **ink alone cannot tell a half note from a black one** (a third of the half
notes read solid in the middle).

**How many things a mark can still be** (median): Brahms 3 before; 4 now when the "(rare)" extras are left out,
5 with them. Stems, dots, barlines and beams are still 1-3; accidentals, rests, time-signature digits, tremolos and
half notes are still 8-12. Size and place alone cannot tell a sharp from an 8 from a quarter rest.

## The lists (what a shape in a place can still be; "(rare)" = possible but unusual, kept on purpose)

### A small round dot

- in the staff, mid-bar: dot (augmentation or staccato); text (word, label, direction) (rare)
- just outside the staff (ledger range): dot (augmentation or staccato); text (word, label, direction)
- far from any staff: text (word, label, direction)
- in the clef/key slots: text (word, label, direction) (rare)
- at the head of a bar: dot (augmentation or staccato); text (word, label, direction) (rare)
- on a barline: dot (augmentation or staccato); text (word, label, direction) (rare)
- at the far right of a system: dot (augmentation or staccato); text (word, label, direction) (rare)
- in the left margin / at the system's left edge: text (word, label, direction)

### A filled oval

- in the staff, mid-bar: beam; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; filled notehead; half-note head (hollow, stemmed); text (word, label, direction) (rare); tremolo slash; whole / half rest (the block); whole-note head (hollow, no stem)
- just outside the staff (ledger range): beam; dynamic letter (f, p, m, s, z); eighth / sixteenth rest; filled notehead; half-note head (hollow, stemmed); text (word, label, direction); tremolo slash; tuplet number; whole / half rest (the block); whole-note head (hollow, no stem)
- far from any staff: beam; dynamic letter (f, p, m, s, z); text (word, label, direction); tremolo slash; tuplet number
- in the clef/key slots: text (word, label, direction) (rare); time-signature digit
- at the head of a bar: beam; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; filled notehead; half-note head (hollow, stemmed); text (word, label, direction) (rare); time-signature digit; tremolo slash; whole / half rest (the block); whole-note head (hollow, no stem)
- on a barline: beam; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; filled notehead; half-note head (hollow, stemmed); text (word, label, direction) (rare); tremolo slash; whole / half rest (the block); whole-note head (hollow, no stem)
- at the far right of a system: beam; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; filled notehead; half-note head (hollow, stemmed); text (word, label, direction) (rare); time-signature digit; tremolo slash; whole / half rest (the block); whole-note head (hollow, no stem)
- in the left margin / at the system's left edge: text (word, label, direction)

### A hollow oval

- in the staff, mid-bar: accent / marcato; beam; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; fermata; half-note head (hollow, stemmed); slur; text (word, label, direction) (rare); tie; tremolo slash; whole-note head (hollow, no stem)
- just outside the staff (ledger range): accent / marcato; beam; dynamic letter (f, p, m, s, z); eighth / sixteenth rest; fermata; half-note head (hollow, stemmed); slur; text (word, label, direction); tie; tremolo slash; tuplet number; whole-note head (hollow, no stem)
- far from any staff: accent / marcato; beam; dynamic letter (f, p, m, s, z); fermata; slur; text (word, label, direction); tie; tremolo slash; tuplet number
- in the clef/key slots: fermata; slur; text (word, label, direction) (rare); tie; time-signature digit
- at the head of a bar: accent / marcato; beam; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; fermata; half-note head (hollow, stemmed); slur; text (word, label, direction) (rare); tie; time-signature digit; tremolo slash; whole-note head (hollow, no stem)
- on a barline: accent / marcato; beam; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; fermata; half-note head (hollow, stemmed); slur; text (word, label, direction) (rare); tie; tremolo slash; whole-note head (hollow, no stem)
- at the far right of a system: accent / marcato; beam; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; fermata; half-note head (hollow, stemmed); slur; text (word, label, direction) (rare); tie; time-signature digit; tremolo slash; whole-note head (hollow, no stem)
- in the left margin / at the system's left edge: text (word, label, direction)

### A flat filled block

- in the staff, mid-bar: beam; filled notehead; half-note head (hollow, stemmed); tenuto dash; tremolo slash; whole / half rest (the block)
- just outside the staff (ledger range): beam; filled notehead; half-note head (hollow, stemmed); ledger line; tenuto dash; tremolo slash; whole / half rest (the block)
- far from any staff: beam; tenuto dash; tremolo slash
- in the clef/key slots: **nothing** (a piece of something, or unread)
- at the head of a bar: beam; filled notehead; half-note head (hollow, stemmed); tenuto dash; tremolo slash; whole / half rest (the block)
- on a barline: beam; filled notehead; half-note head (hollow, stemmed); tenuto dash; tremolo slash; whole / half rest (the block)
- at the far right of a system: beam; filled notehead; half-note head (hollow, stemmed); tenuto dash; tremolo slash; whole / half rest (the block)
- in the left margin / at the system's left edge: **nothing** (a piece of something, or unread)

### A short flat stroke

- in the staff, mid-bar: beam; filled notehead; half-note head (hollow, stemmed); slur; tenuto dash; tie; tremolo slash; whole / half rest (the block); whole-note head (hollow, no stem)
- just outside the staff (ledger range): beam; filled notehead; half-note head (hollow, stemmed); ledger line; slur; tenuto dash; tie; tremolo slash; whole / half rest (the block); whole-note head (hollow, no stem)
- far from any staff: beam; slur; tenuto dash; tie; tremolo slash
- in the clef/key slots: slur; tie
- at the head of a bar: beam; filled notehead; half-note head (hollow, stemmed); slur; tenuto dash; tie; tremolo slash; whole / half rest (the block); whole-note head (hollow, no stem)
- on a barline: beam; filled notehead; half-note head (hollow, stemmed); slur; tenuto dash; tie; tremolo slash; whole / half rest (the block); whole-note head (hollow, no stem)
- at the far right of a system: beam; filled notehead; half-note head (hollow, stemmed); slur; tenuto dash; tie; tremolo slash; whole / half rest (the block); whole-note head (hollow, no stem)
- in the left margin / at the system's left edge: **nothing** (a piece of something, or unread)

### A thin tall stroke

- in the staff, mid-bar: stem
- just outside the staff (ledger range): stem
- far from any staff: stem
- in the clef/key slots: **nothing** (a piece of something, or unread)
- at the head of a bar: stem
- on a barline: barline; stem
- at the far right of a system: barline; stem
- in the left margin / at the system's left edge: brace / bracket

### A long thin curve or wedge

- in the staff, mid-bar: dynamic letter (f, p, m, s, z) (rare); slur; text (word, label, direction) (rare); tie
- just outside the staff (ledger range): dynamic letter (f, p, m, s, z); hairpin (cresc./dim. wedge); slur; text (word, label, direction); tie
- far from any staff: dynamic letter (f, p, m, s, z); hairpin (cresc./dim. wedge); slur; text (word, label, direction); tie
- in the clef/key slots: slur; text (word, label, direction) (rare); tie
- at the head of a bar: dynamic letter (f, p, m, s, z) (rare); slur; text (word, label, direction) (rare); tie
- on a barline: dynamic letter (f, p, m, s, z) (rare); slur; text (word, label, direction) (rare); tie
- at the far right of a system: dynamic letter (f, p, m, s, z) (rare); slur; text (word, label, direction) (rare); tie
- in the left margin / at the system's left edge: text (word, label, direction)

### A tall glyph, accidental-sized

- in the staff, mid-bar: accidental (sharp/flat/natural); arpeggio wavy line (rare); beam; clef; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; flag; quarter rest; slur; text (word, label, direction) (rare)
- just outside the staff (ledger range): accidental (sharp/flat/natural); arpeggio wavy line (rare); beam; clef; dynamic letter (f, p, m, s, z); eighth / sixteenth rest; flag; quarter rest; slur; text (word, label, direction)
- far from any staff: beam; dynamic letter (f, p, m, s, z); flag; slur; text (word, label, direction)
- in the clef/key slots: accidental (sharp/flat/natural); clef; key-signature accidental; slur; text (word, label, direction) (rare); time-signature digit
- at the head of a bar: accidental (sharp/flat/natural); arpeggio wavy line (rare); beam; clef; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; flag; key-signature accidental; quarter rest; slur; text (word, label, direction) (rare); time-signature digit
- on a barline: accidental (sharp/flat/natural); arpeggio wavy line (rare); beam; clef; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; flag; quarter rest; slur; text (word, label, direction) (rare)
- at the far right of a system: accidental (sharp/flat/natural); arpeggio wavy line (rare); beam; clef; dynamic letter (f, p, m, s, z) (rare); eighth / sixteenth rest; flag; key-signature accidental; quarter rest; slur; text (word, label, direction) (rare); time-signature digit
- in the left margin / at the system's left edge: text (word, label, direction)

### A big tall glyph, clef-sized

- in the staff, mid-bar: beam; clef; slur; text (word, label, direction) (rare)
- just outside the staff (ledger range): beam; clef; slur; text (word, label, direction)
- far from any staff: beam; slur; text (word, label, direction)
- in the clef/key slots: clef; slur; text (word, label, direction) (rare)
- at the head of a bar: beam; clef; slur; text (word, label, direction) (rare)
- on a barline: beam; clef; slur; text (word, label, direction) (rare)
- at the far right of a system: beam; clef; slur; text (word, label, direction) (rare)
- in the left margin / at the system's left edge: brace / bracket; text (word, label, direction)

## Questions (one line each)

1. The three right-edge "braces" (`b4230`, `b4041`, `b4023`, crops D1-D3): what are they — the closing barline?
2. A dynamic word (cresc., dim., "p dolce") you box as one mark: should the table treat it as a dynamic, as a direction word, or either?
3. For the table to be tested on Litolff for more than half notes, I need one **whole Litolff page** labelled like your Brahms page (every mark, not only hollow heads). Is that worth your time?

## Crops (nothing is drawn on the music except small red corners around the mark)

- D1-D3 (`b4230`, `b4041`, `b4023`): the three marks the table now rules out as "brace at the right edge".
- D4 (`b3027`): the top of the left-edge brace you boxed beside the first staff (the table keeps it).
