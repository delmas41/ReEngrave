%% Stem/beam ground-truth reference sheet.
%%
%% The counts are known by construction, so this ground truth needs no human
%% counting and cannot drift. Per measure, per staff:
%%
%%   bar   upper staff                          stems beams | lower staff                    stems beams
%%   1     four quarter notes                     4     0   | two half notes                   2     0
%%   2     one whole note                         0     0   | one whole note                   0     0
%%   3     eight eighths, beamed in pairs         8     4   | four quarters                    4     0
%%   4     sixteen 16ths in four beamed groups   16     8   | 2 beamed pairs + 2 quarters      6     2
%%         (each group carries a primary AND a secondary bar)
%%   5     four three-note chords                 4     0   | two two-note chords              2     0
%%   6     two half notes                         2     0   | one whole note                   0     0
%%
%% The two staves deliberately carry DIFFERENT music. With identical music the
%% stems line up vertically across both staves, and barline detection — which
%% votes on exactly that alignment — reads them as barlines: the sheet
%% segmented into 19 measures instead of 6.
%%
%% Staff-line thickness is substituted in by the eval tool (#THICKNESS), because
%% thick lines are the regime where staff-line removal used to fail outright.

\version "2.24.0"
\header { tagline = ##f }
#(set-global-staff-size 22)
\paper {
  indent = 0
  ragged-right = ##f
  paper-width = 260\mm
  line-width = 245\mm
  top-margin = 14\mm
  bottom-margin = 14\mm
}

upper = {
  \override Staff.TimeSignature.stencil = ##f
  c'4 d'4 e'4 f'4 |
  c'1 |
  c'8[ d'8] e'8[ f'8] g'8[ a'8] b'8[ c''8] |
  c'16[ d'16 e'16 f'16] g'16[ a'16 b'16 c''16] d''16[ c''16 b'16 a'16] g'16[ f'16 e'16 d'16] |
  <c' e' g'>4 <d' f' a'>4 <e' g' b'>4 <f' a' c''>4 |
  c'2 d'2 |
}

lower = {
  \override Staff.TimeSignature.stencil = ##f
  g2 b2 |
  g1 |
  g4 a4 b4 c'4 |
  g8[ a8] b8[ c'8] d'4 e'4 |
  <g b>2 <a c'>2 |
  g1 |
}

\score {
  <<
    \new Staff \with { \override StaffSymbol.thickness = #THICKNESS } { \clef treble \upper }
    \new Staff \with { \override StaffSymbol.thickness = #THICKNESS } { \clef bass \lower }
  >>
  \layout { \context { \Score \omit BarNumber \override SystemStartBar.collapse-height = #1 } }
}
