\version "2.20.0"

\header {
  title = "OMR transcription"
  subtitle = "From: beethoven--symphony-3-op55--henry-litolff-s-verlag-1870--imslp504077.pdf"
  tagline = ##f
}

\score {
  <<
  \new Staff {
    \clef treble
    \key d \major
    \time 6/4
    <ces'' ees''>4 <ces'' ees''>4 fis'''4 r4 r4 |
    <b'' cis''' fis'''>4-. cis''4 r4 |
    r1 |
    r1 <fis' g' a' b' cis''>4 |
    r1 |
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
    \key f \major
    \time 6/4
    <<
      \new Voice {
      \voiceOne
      r8 <g' ces'' ces'' ees'' ees''>4 <ees'' g''>4-. |
      <e'' g''>4-. c''4 r4 |
      r1 |
      r1 c''4 |
      r1 |
      r1 |
      r1 |
      r1 |
      c''4 |
      r4 r1 g'4 |
      r4 r1 |
      r1 |
      }
      \new Voice {
      \voiceTwo
      r8 ces''4 |
      <e'' g''>4-. c''4 r4 |
      r1 |
      r1 c''4 |
      r1 |
      r1 |
      r1 |
      r1 |
      c''4 |
      r4 r1 g'4 |
      r4 r1 |
      r1 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 6/4
    <<
      \new Voice {
      \voiceOne
      <c'' e''>4 r4 |
      <a' f''>4-. r4 c''4 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      <e' g' b' d'' f''>4 r1 |
      r1 |
      <e' g' f''>4 r1 |
      r1 |
      }
      \new Voice {
      \voiceTwo
      <f' a'>4 g'4 <a' f''>4-. c''4 r4 |
      <a' f''>4-. r4 c''4 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      <e' g' b' d'' f''>4 r1 |
      r1 |
      <e' g' f''>4 r1 |
      r1 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 6/4
    <<
      \new Voice {
      \voiceOne
      <e a>4 <aes, ees ges g>4 <c ees>4 r4 |
      e4 <c e>4 |
      r1 |
      r1 <c e g>4 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      }
      \new Voice {
      \voiceTwo
      <ees e'>4 r4 |
      e4 |
      r1 |
      r1 <c e g>4 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 6/4
    <c'' e''>4 <f' g' c'' e''>4 e'4-. g'4~ <g' c''>4 <f' a' c''>4 |
    e'4-. r4 r4 |
    r1 |
    r1 <e' f' a'>4 |
    r1 |
    r1 |
    r1 |
    r1 |
    r1 |
    r1 |
    r1 |
    f''4 r1 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 6/4
    <<
      \new Voice {
      \voiceOne
      <c'' e''>4 <g' c'' e''>4 r4 |
      <c'' f''>4 c''4 r4 |
      r1 |
      r1 <f' a' c''>4 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      }
      \new Voice {
      \voiceTwo
      c''4-. c''4 r4 |
      <c'' f''>4 c''4 r4 |
      r1 |
      r1 <f' a' c''>4 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 6/4
    <<
      \new Voice {
      \voiceOne
      e''4 d'4 c''4-. r4 r4 |
      <c' c'>4-. r4 r4 |
      r1 |
      r1 <d' f' f' a' a' c'' d'' e''>4 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      }
      \new Voice {
      \voiceTwo
      c''4 r4 r4 |
      <c' c'>4-. r4 r4 |
      r1 |
      r1 <d' f' f' a' a' c'' d'' e''>4 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 6/4
    <<
      \new Voice {
      \voiceOne
      <a, c>4 <f g>4 <e g>4 <a, e g>4 b,4 c4 c4~ |
      <e a>4 r4 e4 |
      r1 |
      r1 <c e e g>4 |
      c4 r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      }
      \new Voice {
      \voiceTwo
      e4 |
      <e a>4 r4 e4 |
      r1 |
      r1 <c e e g>4 |
      c4 r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 6/4
    <<
      \new Voice {
      \voiceOne
      c''4 aes'4 <c'' ees''>4 <c'' ees''>4 <g e' e' b' b' g''>4~-. r4 r4 |
      <g e' b' g''>4-. r4 c''4 |
      r1 |
      r1 <f' f' b'>4 |
      r1 |
      r1 |
      r8 g''4 g''4 g''4 |
      b4 b4 b4 b8 |
      b4 |
      r1. |
      b8 |
      a4 b4 |
      }
      \new Voice {
      \voiceTwo
      a'4 <g' aes'>4 c''4 r4 r4 |
      <g e' b' g''>4-. r4 c''4 |
      r1 |
      r1 <f' f' b'>4 |
      r1 |
      r1 |
      r8 g''4 g''4 g''4 |
      b4 b4 b4 b8 |
      b4 |
      r1. |
      b8 |
      a4 b4 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 6/4
    ees''4 <ces'' ees''>4 <g e' e' ees''>4~-. r4 r4 b'4 |
    <f e'>4 c''4 r4 |
    g'2 |
    <f' a'>2 a'4 <f' a'>4 |
    <f' g'>2 |
    f'2 |
    g'4 |
    <b, b, c>4 c4 |
    b,8( d,8 <b, b,>8 d,8 d,8) |
    b8( f'8 b8 f'8 b8) |
    e'8( b8 e'8 b8 e'8 b8) |
    d'8 e'8 b8 e'8 a8 e'8 |
  }
  \new Staff {
    \clef alto
    \key bes \major
    \time 6/4
    <<
      \new Voice {
      \voiceOne
      <d' f' a'>4 <bes bes d' ees' f'>4 c'4 a4 <g ees'>4~-. r4 r4 <g bes c' d'>4 |
      <g ees'>4 r4 |
      bes2 r2 |
      r2 bes4 <ees g g bes bes c' d' ees' f' a'>4 |
      r1. |
      r1. |
      r1. |
      bes4 |
      bes4 |
      r1. |
      <g' a'>8 |
      r1 g'4 a'4 |
      }
      \new Voice {
      \voiceTwo
      <des' fes'>4 <d' f'>4 r4 r4 |
      d'4 r4 |
      bes2 r2 |
      r2 bes4 <ees g g bes bes c' d' ees' f' a'>4 |
      r1. |
      r1. |
      r1. |
      bes4 |
      d'4 d'4 |
      r1. |
      <g' a'>8 |
      r1 g'4 a'4 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key f \major
    \time 6/4
    a,4 e4 r8 <ees ges>4 <ees ges>4 ees4~ r4 ees4 |
    e4 r4 r4 |
    r1 g4 |
    e2 r1 <bes, bes,>4 <a, c e g>4 |
    e4 g4( bes4) |
    e2 r1 <d d>4 |
    r1. |
    r1 |
    <d e>1 e4 r1 |
    e4 r1 <d e>4 |
    r1 r1 |
    a,4( <bes, bes,>4 c4) |
  }
  >>
  \layout { }
  \midi { }
}
