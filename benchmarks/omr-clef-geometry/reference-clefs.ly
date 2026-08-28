\version "2.24.0"
\header { tagline = ##f }
\paper { indent = 0 ; ragged-right = ##f ; paper-width = 180 ; line-width = 170 ; top-margin = 8 ; bottom-margin = 8 }
\score {
  <<
    \new Staff { \clef soprano \override Staff.TimeSignature.stencil = ##f c'4 d'4 e'4 f'4 | g'4 a'4 b'4 c''4 }
    \new Staff { \clef mezzosoprano \override Staff.TimeSignature.stencil = ##f c'4 d'4 e'4 f'4 | g'4 a'4 b'4 c''4 }
    \new Staff { \clef alto \override Staff.TimeSignature.stencil = ##f c'4 d'4 e'4 f'4 | g'4 a'4 b'4 c''4 }
    \new Staff { \clef tenor \override Staff.TimeSignature.stencil = ##f c'4 d'4 e'4 f'4 | g'4 a'4 b'4 c''4 }
    \new Staff { \clef baritone \override Staff.TimeSignature.stencil = ##f c'4 d'4 e'4 f'4 | g'4 a'4 b'4 c''4 }
    \new Staff { \clef treble \override Staff.TimeSignature.stencil = ##f c'4 d'4 e'4 f'4 | g'4 a'4 b'4 c''4 }
    \new Staff { \clef bass \override Staff.TimeSignature.stencil = ##f c'4 d'4 e'4 f'4 | g'4 a'4 b'4 c''4 }
  >>
  \layout { \context { \Score \omit BarNumber } }
}
