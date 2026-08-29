% Braced piano music in all fifteen key signatures — a false-positive corpus
% for the CV C-clef locator.
%
% Piano music has no C clefs, so any read at all is a false positive. Two
% properties are deliberate. The BRACE, because a brace's waist survives rule
% stripping as a compact symmetric blob that reads as a C clef unless something
% stops it. And a KEY SIGNATURE behind every clef, because the locator's one
% historic false-positive mode was skipping an oversized treble clef and
% reading the sharp behind it — the accidentals have to be there for the
% "never scan past the first glyph" rule to be under test at all. The "Nr. N."
% headings put text directly above each system, which is the ink that fuses
% with the clef on the material this layer exists for.
%
% This stands in for the ten pages of scanned Bach WTC the earlier rounds used,
% which are not in the repo. It is engraved rather than scanned, so it does not
% replace a scan-domain check; it is the part of the constraint that can be
% rebuilt anywhere.
%
%   lilypond piano-false-positives.ly
%   python3 benchmarks/omr-clef-geometry/check_clef_precision.py
%
\version "2.24.0"
\header { tagline = ##f }
\paper { indent = 15\mm ; ragged-last-bottom = ##f ; top-margin = 12\mm }

\score {
  \header { piece = "Nr. 1." }
  \new PianoStaff <<
    \new Staff { \clef treble \key c \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key c \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 2." }
  \new PianoStaff <<
    \new Staff { \clef treble \key g \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key g \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 3." }
  \new PianoStaff <<
    \new Staff { \clef treble \key d \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key d \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 4." }
  \new PianoStaff <<
    \new Staff { \clef treble \key a \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key a \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 5." }
  \new PianoStaff <<
    \new Staff { \clef treble \key e \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key e \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 6." }
  \new PianoStaff <<
    \new Staff { \clef treble \key b \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key b \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 7." }
  \new PianoStaff <<
    \new Staff { \clef treble \key fis \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key fis \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 8." }
  \new PianoStaff <<
    \new Staff { \clef treble \key cis \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key cis \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 9." }
  \new PianoStaff <<
    \new Staff { \clef treble \key f \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key f \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 10." }
  \new PianoStaff <<
    \new Staff { \clef treble \key bes \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key bes \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 11." }
  \new PianoStaff <<
    \new Staff { \clef treble \key ees \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key ees \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 12." }
  \new PianoStaff <<
    \new Staff { \clef treble \key aes \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key aes \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 13." }
  \new PianoStaff <<
    \new Staff { \clef treble \key des \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key des \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 14." }
  \new PianoStaff <<
    \new Staff { \clef treble \key ges \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key ges \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}

\score {
  \header { piece = "Nr. 15." }
  \new PianoStaff <<
    \new Staff { \clef treble \key ces \major \time 4/4
      \relative c'' { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
    \new Staff { \clef bass \key ces \major \time 4/4
      \relative c { c8 d e f g a b c | d c b a g f e d | c4 e g e | c1 \bar "|." } }
  >>
}