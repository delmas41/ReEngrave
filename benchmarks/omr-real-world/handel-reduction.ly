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
    \key a \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      b'16 a'16 gis'4 |
      r1 |
      <a' b'>4 e''4 e''4 |
      e''4 |
      <e'' e''>4 e''4 |
      e''8 a4 <cis'' d''>8 cis''16 |
      <a' a'>8 |
      <a' a'>4 <a' a'>4 <a' a'>4 |
      }
      \new Voice {
      \voiceTwo
      e''4 |
      r1 |
      <a' b'>4 e''4 e''4 |
      e''4 |
      <e'' e''>4 e''4 |
      e''8 a4 <cis'' d''>8 cis''16 |
      <d'' d''>4 <b' b'>4 |
      <a' a'>4 <a' a'>4 <a' a'>4 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key a \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      gis'8 fis'8 e'4 |
      b'1 |
      a,4 |
      <d e>8 b,8 cis8 |
      gis,4 <cis, d,>8 gis,4 |
      cis4 |
      cis4 b,4 <cis cis>8 |
      <cis cis>4 <cis cis>4 <cis cis>4 |
      }
      \new Voice {
      \voiceTwo
      b'4 |
      b'1 |
      a,4 |
      <d e>8 b,8 cis8 |
      gis,4 <cis, d,>8 gis,4 |
      cis4 |
      cis4 b,4 <cis cis>8 |
      <cis cis>4 <cis cis>4 <cis cis>4 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key a \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      e''4 b'4 b'4 |
      gis'''1 |
      e''8 |
      cis''8 <a' b'>8 cis''8 |
      gis'8 |
      cis''16 cis''16 <cis'' d''>8 e''16 e''16 |
      <e'' fis''>4 <a' b'>4 e''4 |
      <cis'' cis''>4 gis'''4 cis''4 cis''4 |
      }
      \new Voice {
      \voiceTwo
      e''4 b'4 b'4 |
      gis'''1 |
      e''8 |
      cis''8 <a' b'>8 cis''8 |
      <a' b'>8 <a' b'>8 |
      cis''16 cis''16 <cis'' d''>8 e''16 e''16 |
      <e'' fis''>4 <a' b'>4 e''4 |
      <cis'' cis''>4 gis'''4 cis''4 cis''4 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key a \major
    \time 4/4
    e2 gis4 |
    a4 <gis a>4 |
    <e e>4 |
    e8 e8 <gis a>8 |
    <fis gis gis gis>4 e8 gis8 |
    a4 |
    <cis d>8 e8 <e e>8 |
    b'4 e4 e4 |
  }
  \new Staff {
    \clef treble
    \key a \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      <gis'' b'>4 <fis'' a'>16 <e'' gis'>4 <b' b'' e''>8 |
      b''32 |
      <a' e'' b'>4 |
      <e'' fis'>4 <fis' a' gis' b' gis'>4 <a' cis'' cis'' a' a'>4 |
      <fis' b' gis'>4 <d' b' e'' b' e' e''>4 |
      <e'' cis'' e'' d' cis''>4 <d'' b' b'>8 <d' cis'' a' cis'' a' e' e' cis''>4 |
      <d'' a' fis' a'>4 cis''8 a'8 |
      <a' cis' a' a' cis'>8 <gis'' a'' a''>8 <gis'' a'' a''>8 |
      }
      \new Voice {
      \voiceTwo
      <gis'' b'>4 <fis'' a'>16 <e'' gis'>4 <b' b'' e''>8 |
      b''32 |
      e''4 <d'' e''>4 |
      <e'' fis'>4 <fis' a' gis' b' gis'>4 <a' cis'' cis'' a' a'>4 |
      <d' a' e' b' e''>4 |
      <e'' cis'' e'' d' cis''>4 <d'' b' b'>8 <d' cis'' a' cis'' a' e' e' cis''>4 |
      <a b' gis' b>8 <d' e'>4 |
      <a' cis' a' a' cis'>8 <gis'' a'' a''>8 <gis'' a'' a''>8 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key a \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      e2 gis4 |
      <a, a,>8 |
      <e e>4 <e e>4 |
      <d e>8 e8 <gis a>8 |
      <gis gis>4 e8 gis8 |
      gis4 |
      <e, e,>8 |
      a,4 e4 e4 |
      }
      \new Voice {
      \voiceTwo
      e2 gis4 |
      <a, a,>8 |
      <e e>4 <e e>4 |
      <d e>8 e8 <gis a>8 |
      <gis gis>4 e8 gis8 |
      gis4 |
      <cis d>8 <e a' e>8 |
      a,4 e4 e4 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key a \major
    \time 4/4
    a'2 |
    r1 |
    r1 |
    r1 |
    <cis'' cis''>8 |
    cis''8 d''8 |
    e''8 |
    <cis'' d'' d''>4 |
    r1 |
    r1 |
  }
  \new Staff {
    \clef treble
    \key a \major
    \time 4/4
    a'2 |
    r1 |
    r1 |
    r1 |
    <a' a'>8 <cis'' cis''>8 |
    <a' a' a'>8 |
    r1 |
    <a' a' b'>4 |
    r1 |
    r1 |
  }
  \new Staff {
    \clef treble
    \key a \major
    \time 4/4
    r4 cis''4 fis''4 |
    <e'' e''>4 cis''4 <e'' fis'' fis''>4 |
    e''8 <cis'' d''>8 cis''8 <e'' fis''>4 |
    <e'' e''>4 <cis'' cis''>4 <e'' fis''>4 |
    e''8 <cis'' d''>8 cis''8 <cis'' cis''>8 |
    e''8 |
    r1 |
    <e'' fis''>4 |
    r1 |
    r1 |
  }
  \new Staff {
    \clef bass
    \key a \major
    \time 4/4
    e4 a4 d'8 |
    <b cis' cis'>8 <gis a>4 r2 |
    <cis' cis'>16 b16 <gis a a>32 d'16 |
    <cis' cis'>8 <gis a>4 r2 |
    <b cis'>16 b16 <a a>16 <e e>16 |
    <gis a>8 |
    r1 |
    <cis d>8 |
    r1 |
    r1 |
  }
  \new Staff {
    \clef treble
    \key a \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      a''1 <cis'' e''>4 |
      <e'' cis'' cis''>8 <cis'' e'' fis'' e d'' d''>8 |
      <cis'' e'' cis''>8 <cis'' e'' d'' fis'' d'' d''>4 |
      <cis'' fis'' d'' e d''>4 |
      <d'' a'' e'' a'' e'' a''>8 <cis'' d''>4 <e'' cis'' a' cis''>4 <cis'' cis''>4 |
      <gis' a' b' d'' e'' b'>16 |
      e''64 |
      <a' cis'' gis' e'' cis'' fis'' d'' d'' d'' e'' b'>8 |
      r1 |
      <fis d' cis' fis'' fis fis gis d' cis' e d' b a a cis' a fis' e'' fis' gis gis a' a' e' b' gis' e e' gis' b' cis'' cis'' e d'' d>4 |
      }
      \new Voice {
      \voiceTwo
      <fis'' d''>4 |
      <e'' a'' e''>8 |
      <e'' a'' e''>8 <cis'' d''>8 |
      <b'' e'' e''>8 <e'' cis'' e''>4 |
      <d'' a'' e'' a'' e'' a''>8 <cis'' d''>4 <e'' cis'' a' cis''>4 <cis'' cis''>4 |
      <gis' a' b' d'' e'' b'>16 |
      e''64 |
      <a' cis'' gis' e'' cis'' fis'' d'' d'' d'' e'' b'>8 |
      r1 |
      <fis d' cis' fis'' fis fis gis d' cis' e d' b a a cis' a fis' e'' fis' gis gis a' a' e' b' gis' e e' gis' b' cis'' cis'' e d'' d>4 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key a \major
    \time 4/4
    e4 a4 d'8 |
    <b cis'>8 <gis a>4 r2 |
    <b cis'>16 b16 <gis a>16 <d' d'>16 |
    <b cis' cis'>8 <a a>4 d'8 |
    <b cis' cis'>16 b16 <a a>16 <e e>16 |
    <gis a>8 |
    r1 |
    d8 <cis d>8 |
    r1 |
    <e' d' cis' e e' d' cis' cis' cis' b b fis' fis' gis' a' e cis gis e cis gis d d a b, a, gis b, a' a gis' fis fis gis' gis' b'>4 |
  }
  >>
  \layout { }
  \midi { }
}
