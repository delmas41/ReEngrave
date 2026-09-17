\version "2.24.0"
\header { title = "Changes" tagline = ##f }
\paper { indent = 25\mm }
m = \relative c'' { \clef treble \key c \major \time 4/4
  c4 d e f | \time 3/4 g a b | \time 2/4 c2 |
  \key d \major \time 4/4 d4 cis b a | \time 6/8 g8 fis e d cis b | a2. \bar "|." }
n = \relative c  { \clef bass \key c \major \time 4/4
  c4 e g c | \time 3/4 g2. | \time 2/4 c,2 |
  \key d \major \time 4/4 d4 fis a d | \time 6/8 a4. d, | a'2. \bar "|." }
\score { \new StaffGroup << \new Staff \with { instrumentName = "Clarinetti" } \m
  \new Staff \with { instrumentName = "Fagotti" } \n >> \layout { } }
