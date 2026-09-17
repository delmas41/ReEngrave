\version "2.24.0"
\header { title = "Plumbing" tagline = ##f }
\paper { indent = 30\mm system-system-spacing.basic-distance = #14 }

flauto = \relative c'' {
  \clef treble \key ees \major \time 2/4
  \tempo "Allegro con brio"
  c8\p( d ees f) | g4.\< a8 | \time 3/4 bes2.\! |
  \tuplet 3/2 { c8 bes aes } g4 f | ees2\fermata r4 |
  a'4\trill^"legato" g8. f16 ees4 | f2.~ | f2 r4 \bar "|."
}
oboe = \relative c'' {
  \clef treble \key ees \major \time 2/4
  ees4\mf d | c8-. bes-. aes4\> | \time 3/4 g2.\! |
  R2. | bes4\sf aes g | <ees g bes>2. |
  d'8[ c bes aes] g4 | ees2. \bar "|."
}
viola = \relative c' {
  \clef alto \key ees \major \time 2/4
  << { g4 aes } \\ { ees4 c } >> | bes2 | \time 3/4 ees4-> f g |
  aes2. | g4 f ees | r2. | d2.\ff | ees2. \bar "|."
}
basso = \relative c {
  \clef bass \key ees \major \time 2/4
  ees4 g | bes,2 | \time 3/4 ees2. |
  c2. | g'4 aes bes | ees,2. | bes2. | ees2. \bar "|."
}

\score {
  \new StaffGroup <<
    \new Staff \with { instrumentName = "Flauti" } \flauto
    \new Staff \with { instrumentName = "Oboi" } \oboe
    \new Staff \with { instrumentName = "Viola" } \viola
    \new Staff \with { instrumentName = "Basso" } \basso
  >>
  \layout { }
}
