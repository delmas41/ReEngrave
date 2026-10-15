# Augmentation dot after a note on a line: above or below? (research, 2026-10-14)

Sean (2026-10-14): "I don't know. Send a sonnet research agent out on that." Web/reading research only; Gould, Read and
Ross were NOT opened directly -- every Gould citation is second-hand (quoted in forum posts).

* CONFIRMED by Sean: an augmentation dot stands in a space, never on a line.
* CONFIRMED by several sources: a lone note on a line, single voice, takes its dot in the space ABOVE
  (Wikipedia "Dotted note"; LilyPond's dot-column priorities end with "move up").
* SOURCED, second-hand: in two voices on one staff, a LOWER-voice (stems-down) note on a line takes its dot BELOW
  (Gould p. 56, "Lower part on a line: Drop the dot into the space below", quoted at musescore.org/en/node/332713;
  MuseScore devs: voice 1 above, voice 2 below; Steinberg forum: Henle / NMA / Barenreiter put it below, OUP an
  exception -- practice is split).
* SOURCED: notes a second apart in a chord take their dots in ADJACENT spaces -- upper above, lower below
  (Dorico behaviour per Steinberg forum; Finale "places dots below the staff line when necessary"; LilyPond
  `DotColumn.direction`, `chord-dots-limit`).
* GUESS: 19th-century Breitkopf / Litolff plates follow the same split -- no period source found.
* Test to run: split Sean's 19 below-dots on Brahms p0 by stem direction and chord membership; they should fall on
  lower-voice notes or the lower member of a second. A single-voice single note with its dot below would contradict
  the sources -- crop it for Sean.
* Consequence: the old "never below" wording (engraving-conventions C50) and `DOT_BELOW_NOTE_MAX_SPACES = 0.25` are
  wrong for those cases.

Sources: en.wikipedia.org/wiki/Dotted_note; forums.steinberg.net/t/recommended-placement-of-dot/820660;
musescore.org/en/node/332713, /32921, /303346, /299264; usermanuals.finalemusic.com (IDD_AUGDOTOPTIONS);
lilypond.org/doc/v2.24/Documentation/internals/dot_002dcolumn_002dinterface
