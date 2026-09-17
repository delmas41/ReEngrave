\version "2.24.0"
\header { title = "Marks" tagline = ##f }
\paper { indent = 25\mm }
up = \relative c'' {
  \clef treble \key g \major \time 4/4
  c4\trill d\turn e\mordent f\prall |
  \tuplet 3/2 { g8 a b } \tuplet 3/2 { c b a } \tuplet 5/4 { g16 a b c d } e4 |
  \acciaccatura d8 c4 \appoggiatura e8 d4 c2 |
  c4-. d-- e-> f-^ | g1\fermata \bar "|."
}
dn = \relative c' {
  \clef bass \key g \major \time 4/4
  g4 a b c | \tuplet 3/2 { d8 c b } a4 g2 |
  e4 fis g a | b4-. a-- g-> fis-^ | g1 \bar "|."
}
\score { \new StaffGroup << \new Staff \with { instrumentName = "Violino" } \up
  \new Staff \with { instrumentName = "Violoncello" } \dn >> \layout { } }
