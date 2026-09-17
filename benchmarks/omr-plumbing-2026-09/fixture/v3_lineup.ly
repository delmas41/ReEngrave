\version "2.24.0"
\header { title = "Lineup" tagline = ##f }
\paper { indent = 28\mm systems-per-page = #2 }
flauti = \relative c'' { \key f \major \time 4/4 c4 d e f | g1 | \break a4 g f e | d1 \bar "|." }
oboi = \relative c'' { \key f \major \time 4/4 a4 bes c d | e1 | \break R1 | R1 \bar "|." }
corni = \relative c'  { \key f \major \time 4/4 f4 g a bes | c1 | \break R1 | R1 \bar "|." }
viola = \relative c'  { \clef alto \key f \major \time 4/4 c4 d e f | g1 | \break f4 e d c | bes1 \bar "|." }
bassi = \relative c   { \clef bass \key f \major \time 4/4 f4 a c f | c1 | \break f,4 g a bes | f1 \bar "|." }
\score { <<
  \new StaffGroup << \new Staff \with { instrumentName = "Flauti" } \flauti
                     \new Staff \with { instrumentName = "Oboi" } \oboi >>
  \new StaffGroup << \new Staff \with { instrumentName = "Corni" } \corni >>
  \new StaffGroup << \new Staff \with { instrumentName = "Viola" } \viola
                     \new Staff \with { instrumentName = "Bassi" } \bassi >>
>> \layout { } }
