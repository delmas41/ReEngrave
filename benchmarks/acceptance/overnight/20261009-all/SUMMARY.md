# Re-gather 2026-10-09 (`20261009-all`): all stages, main `00473387`

Both acceptance movements gathered through INFER (Litolff p1-16 45 min, Brahms p0-26 121 min, exit 0), with the
direction-word reader on scans. Compared two ways (Sean, 2026-10-08 night).

## A. First two stages vs last night (`20261008-night`, main `178d1035`, through ADJUDICATE)

`*-first-two-stages.txt` (`readout diff --arm code --arm settings --arm env`; env = last night had
`OMR_DIRECTION_TEXT_SCAN_GATE=1`, i.e. no words on scans).
- **Every glyph family identical** on both movements (notes, rests, accidentals, clefs, keys, slurs, ties, ...): 0 boxes
  only in one run, 0 changed answers. Expected -- 10-08's work after last night is text only.
- **Direction words: new.** Last night 0 words (the gate). Tonight Litolff 69 words, 10 word+dynamic markings; Brahms 334
  words, 89 markings (`text-words-and-markings.txt`).
- **Dynamics: Litolff 19 bars, Brahms 215 bars changed**, all by the 2.68 rule "a dynamic letter inside a word the OCR
  read is that word's letter". `dynamics-absorbed-or-lost.txt`: Litolff 1 of 19 removed tokens absorbed into a marking,
  Brahms 20 of 191. The rest are NOT lost dynamics on the evidence so far: a random sample of 12 removed letters
  (`out/print/2.68-inside-word/sample_01..12.png`, red = the removed letter, green = the word) shows **12 of 12 are
  letters of the word** (`p` of `sempre`/`più`/`pizz.`/`espr.`, `m`/`d` of `dim.`, `r` of `espr.` read as `f`) or the
  word's own read-together dynamic (`p espr.`). Last night those letters were spelled into dynamics (`p`, `f`, `fz`,
  `ff`) and written to the file. Judged by the session's eye, NOT yet by Sean.

## B. All stages vs the last all-stages acceptance (2026-09-30, `0e9fe8c5`)

`all-stages-vs-20260930.txt` (`current.json` written with `--force`: dirty only by acceptance's own output files from a
crashed first attempt + the temporary manifest; no code changed). Nine days of work, not tonight's alone:
- Litolff: notes reaching the file 4,480 -> 5,107 (0.385 -> 0.448); bars held out 1,732 -> 1,323 (0.388 -> 0.270);
  `staff_not_identified` 213 -> 137; empty bars padded 951 -> 626; bars add up 6,060 / 6,060.
- Brahms: notes 5,225 -> 5,483 (0.213 -> 0.226); bars held out 4,283 -> 4,180 (0.707 -> 0.670); empty bars padded
  613 -> 424; tacet bars not padded 328 -> 527; bars add up 6,669 / 6,669.
- Files (machine-local, `library/_shared-records/overnight-20261009-all/compare/`): MusicXML, LilyPond and compiled PDF
  per movement; LilyPond 0 errors, warnings Litolff 48 / Brahms 725 (unterminated ties, bar checks, slurs; 577 Brahms
  "mid..." warnings not yet read).

## Seen, not fixed
- `Basso p` paired: a PART name took a dynamic (the pairing should skip category `part`, as `a 2 f` was refused).
- `sempre più p` read as `sempre p` (Litolff p8): the box stops after the `p` of `più`; a wrong partial reading.
- Staged export writes every word `placement="below"`, including tempo/technique words filed above their staff.
