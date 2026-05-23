\version "2.20.0"

\header {
  title = "OMR transcription"
  subtitle = "From: Haendel_Messiah_reduction.pdf"
  tagline = ##f
}

\score {
  <<
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      a'8 |
      <a' c''>8 e''8 |
      a'8 <a a>8 |
      <a'' a''>2 r1 e''4 d''4 f''32 e''32 d''32 |
      c''8 |
      r1 |
      }
      \new Voice {
      \voiceTwo
      <e'' f''>4 c''4 |
      <a' c''>8 e''8 |
      a'8 <a a>8 |
      <a'' a''>2 r1 e''4 d''4 f''32 e''32 d''32 |
      c''8 |
      r1 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 4/4
    <a' a'>8 |
    r1 |
    r1 |
    r4 g,4 c4 b,4 a,8 g,4 c4 c4 g,4 |
    c,8 |
    c4 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      c''4 c''4 |
      r1 |
      r1 |
      r4 a'4 f'''1 f'''1 |
      g16 |
      r1 |
      }
      \new Voice {
      \voiceTwo
      c''4 c''4 |
      r1 |
      r1 |
      r4 c''4 b'4.. b'8 c''4 d''4 d''4 b'4 |
      g16 |
      r1 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      f8 |
      r1 |
      r1 |
      r4 c4 a,4 c4 b'1 |
      b,,8 |
      r1 |
      }
      \new Voice {
      \voiceTwo
      f8 |
      r1 |
      r1 |
      r4 e4.. d8 f4 f4 g4 |
      b,,8 |
      r1 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      <c'' c'' c''>4 <a' a'>4 |
      <a' c''>8 e''8 |
      a'8 |
      <e' a>8 <c' a'>8 <g' b>8.. <b' f'>8 <e'' e'>4 <d'' a'>4 f''8 d''8 |
      <c' c' d' c'>8 c''8 |
      <a' c''>8 f''8 |
      }
      \new Voice {
      \voiceTwo
      <e'' f''>4 |
      <a' c''>8 e''8 |
      a'8 |
      a''8 a'4 <b' e'' e'>8 |
      <c' c' d' c'>8 c''8 |
      <a' c''>8 f''8 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      d''8 g'''1 <e'' f'' a'' f''>8 <f' f'>4 |
      r1 |
      r1 |
      r4 <a' f'''>4 f'4 g'''4 a'4 |
      g'''4 |
      r1 |
      }
      \new Voice {
      \voiceTwo
      d''8 g'''1 <e'' f'' a'' f''>8 <f' f'>4 |
      r1 |
      r1 |
      r4 <f''' c''>4 b'8 d''4 d''4 e''4 |
      g'''4 |
      r1 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    r1 |
    r1 |
    r1 |
    r1 |
    r1 |
    r1 |
    r1 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <f' f' f'>64 <g' a' a'>32 <g' g'>64 <f' f'>64 |
    r1 |
    a'1 |
    r1 |
    r1 |
    r1 |
    r1 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    r1 |
    r1 |
    r1 |
    c''4 |
    r1 |
    r1 |
    r1 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    d''4 <b' b'>4 d''8 <c'' d''>8 <b' b'>8 |
    a'4 |
    r1 |
    r1 |
    r1 |
    g'''8 c''4 |
    r1 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <f' f' f'>64 <g' a' a' a'>32 <g' g'>64 <f' f'' f'>64 |
    r1 |
    d'8 |
    r1 d''16 |
    r1 |
    r1 |
    r1 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <d'' g'''>4 <b' b'>4 d''8 <c'' d''>8 b'8 |
    a'16 |
    r1 |
    r1 |
    r1 |
    c''4 |
    r1 |
  }
  >>
  \layout { }
  \midi { }
}
