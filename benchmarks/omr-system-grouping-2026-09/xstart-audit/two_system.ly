\version "2.24.4"

%% Same 8-staff structure, but a forced \break puts TWO systems on one page.
%% The gap BETWEEN the two systems must read 0 bridging (nothing crosses it) in
%% BOTH the pipeline and the independent scan. This is the "must stay 0" control
%% for any proposed fix.

\paper {
  indent = 14\mm
  ragged-right = ##f
  print-page-number = ##f
  oddHeaderMarkup = ##f
  evenHeaderMarkup = ##f
  oddFooterMarkup = ##f
  evenFooterMarkup = ##f
  top-margin = 10\mm
  bottom-margin = 10\mm
  left-margin = 16\mm
  right-margin = 16\mm
  paper-width = 210\mm
  paper-height = 300\mm
  system-system-spacing = #'((basic-distance . 18) (minimum-distance . 14) (padding . 6))
}
\header { tagline = ##f }

music = { \clef treble \time 4/4 b'1 b'1 \break b'1 b'1 \bar "|." }

\score {
  <<
    \new StaffGroup <<
      \new Staff { \set Staff.instrumentName = "Fl" \music }
      \new Staff { \set Staff.instrumentName = "Ob" \music }
      \new Staff { \set Staff.instrumentName = "Cl" \music }
    >>
    \new ChoirStaff <<
      \new Staff { \set Staff.instrumentName = "S" \music }
      \new Staff { \set Staff.instrumentName = "A" \music }
    >>
    \new StaffGroup <<
      \new Staff { \set Staff.instrumentName = "Vn" \music }
      \new Staff { \set Staff.instrumentName = "Va" \music }
      \new Staff { \set Staff.instrumentName = "Vc" \music }
    >>
  >>
  \layout { }
}
