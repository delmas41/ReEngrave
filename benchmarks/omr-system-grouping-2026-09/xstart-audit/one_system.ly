\version "2.24.4"

%% 8 staves, ONE system, mixed groups:
%%   StaffGroup{S1 S2 S3}  - barlines connected across the group
%%   ChoirStaff{S4 S5}     - bracket, barlines NOT connected
%%   StaffGroup{S6 S7 S8}  - barlines connected across the group
%%
%% Whole notes => NO stems, so the only vertical ink crossing any inter-staff
%% gap is structural: the systemic bar (SystemStartBar, full system height, at
%% x_start), the per-group brackets, and the connected barlines inside each
%% StaffGroup. The two BETWEEN-GROUP gaps (S3-S4, S5-S6) are family boundaries
%% bridged ONLY by the systemic bar. The ChoirStaff internal gap (S4-S5) is
%% bridged by bracket + systemic bar but NOT by a barline.

\paper {
  indent = 14\mm
  ragged-right = ##f
  print-page-number = ##f
  oddHeaderMarkup = ##f
  evenHeaderMarkup = ##f
  oddFooterMarkup = ##f
  evenFooterMarkup = ##f
  top-margin = 12\mm
  bottom-margin = 12\mm
  left-margin = 16\mm
  right-margin = 16\mm
  paper-width = 210\mm
  paper-height = 160\mm
}
\header { tagline = ##f }

music = { \clef treble \time 4/4 b'1 b'1 b'1 b'1 \bar "|." }

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
