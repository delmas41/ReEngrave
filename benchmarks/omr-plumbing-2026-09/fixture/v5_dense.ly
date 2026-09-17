\version "2.24.0"
\header { title = "Dense" tagline = ##f }
\paper { indent = 22\mm }
flpart = \relative c'' { \key bes \major \time 2/4 \repeat unfold 2 { c8 d ees f | g4 f | } }
obpart = \relative c'' { \key bes \major \time 2/4 \repeat unfold 2 { ees8 f g aes | bes4 aes | } }
vlpart = \relative c'  { \key bes \major \time 2/4 \repeat unfold 2 { g8 aes bes c | d4 c | } }
vcpart = \relative c   { \clef bass \key bes \major \time 2/4 \repeat unfold 2 { ees8 f g aes | bes4 aes | } }
\score { \new StaffGroup << \new Staff \with { instrumentName = "Fl." } \flpart
  \new Staff \with { instrumentName = "Ob." } \obpart
  \new Staff \with { instrumentName = "Vla." } \vlpart
  \new Staff \with { instrumentName = "Vc." } \vcpart >> \layout { } }
