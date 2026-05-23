\version "2.20.0"

\header {
  title = "OMR transcription"
  subtitle = "From: Haendel_Messiah_lead-sheet.pdf"
  tagline = ##f
}

\score {
  <<
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    r1 |
    r8 b'8 e''4 e''64 d''64 c''32 b'16 |
    f''16 f''16 e''8 |
    r1 r8 b'8 e''8 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      r1 |
      r4 r8 b'8 f''4 |
      e''32 |
      r1 r8 g'4 |
      }
      \new Voice {
      \voiceTwo
      r1 |
      r4 r8 b'8 f''4 |
      e''32 |
      r1 r8 b'4 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key a \major
    \time 4/4
    r1 |
    r1 r4 r8 fis''8 b''8 b'8 cis''8 |
    gis''8 |
    r1 r8 d''8 fis''4 |
  }
  \new Staff {
    \clef treble
    \key d \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      g'4 a'4 |
      a'8 g'8 fis'16 e'8 r4 r1 |
      cis''4 |
      a'4 g'16 fis'16 e'16 e'8 g'8 fis'8 g'8 |
      }
      \new Voice {
      \voiceTwo
      b'16 e''32 e''4 |
      e''8 d''16 cis''16 b'8 r4 r1 |
      cis''4 |
      e''8 d''8 cis''8 b'8 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key g \major
    \time 1/4
    <<
      \new Voice {
      \voiceOne
      c''4 e'8 |
      fis'4 g'4 r8 fis''4 |
      c''64 g'''1 |
      fis''8 fis'8 g'8 b'8 c''4 r8 <c'' c''>4 |
      }
      \new Voice {
      \voiceTwo
      c''4 d''4 e''4 |
      c''4 r8 e''8 fis'8 g'8 |
      c''64 g'''1 |
      fis''8 fis'8 g'8 b'8 c''4 r8 <c'' c''>4 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key e \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      r8 dis''8 fis''4 r8 e''8 gis''4 |
      r8 fis''8 a''8 r8 fis''8 b''8 |
      r8 a'4 r8 |
      }
      \new Voice {
      \voiceTwo
      r8 dis''8 fis''4 r8 e''8 gis''4 |
      r8 fis''8 a''8 r8 fis''8 b''8 |
      r8 b'8 r8 b'8 fis''4 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key e \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      r8 a'8 r8 |
      r8 cis''8 fis''4 r8 dis''8 fis''4 |
      r8 gis'4 e'4 r8 fis'8 |
      }
      \new Voice {
      \voiceTwo
      r8 dis''4 r8 b'8 e''4 |
      r8 cis''8 fis''4 r8 dis''8 fis''4 |
      r8 r8 b'4 |
      }
    >>
  }
  \new Staff {
    \clef alto
    \key e \major
    \time 4/4
    r8 fis'8 a'4 r8 gis'8 b'8 |
    r8 a'4 cis''8 r8 b'8 dis'4 |
    r8 e'8 cis'4 r8 dis'8 dis'4 |
  }
  \new Staff {
    \clef "treble_8"
    \key e \major
    \time 4/4
    a8 gis16 fis8 fis16 a16 gis16 a16 b8 a16 gis8 gis16 b32 a32 b16 |
    cis'8 b8 a8 a8 cis'8 b8 cis'8 dis'8 cis'8 b8 b8 dis'8 cis'8 dis'8 |
    e'16 dis'8 cis'8 cis'8 e'8 dis'16 e'16 fis'64 e'64 dis'64 cis'32 b8 fis'8 e'32 fis'64 |
  }
  \new Staff {
    \clef bass
    \key e \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      fis4 r8 fis8 gis4 r8 gis8 |
      a4 r8 a8 b4 r8 b8 |
      r8 cis8 r8 |
      }
      \new Voice {
      \voiceTwo
      fis4 r8 fis8 gis4 r8 gis8 |
      a4 r8 a8 b4 r8 b8 |
      cis'8 r8 dis4 r8 dis8 |
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
      e''4 fis''4 gis''4.. r1 b''8 b''8 |
      r8 <fis'' fis''>16 gis''16 fis''16 |
      r4 r8 gis'4 |
      r8 cis''4 d''4 r8 d''8 e''4 |
      }
      \new Voice {
      \voiceTwo
      e''4 fis''4 gis''4.. r1 b''8 b''8 |
      r8 <fis'' fis''>16 gis''16 fis''16 |
      gis''8 fis''8 r4 r8 cis''4 |
      r8 cis''4 d''4 r8 d''8 e''4 |
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
      gis'16 |
      d''8 e''8 d''8 |
      r4 cis''4 e'4 gis'4 |
      r8 ais'4 fis'4 r8 gis'4 |
      }
      \new Voice {
      \voiceTwo
      b'8 e''4 d''8 e''8.. gis''16 gis''4 |
      d''8 e''8 d''8 |
      e''8 d''8 r4 |
      r8 r8 b'8 |
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
      fis''64 a''64 b''64 a''64 a''64 cis''64 |
      r16 a''8 a''8 a''8 |
      r4 r16 a'4 |
      r8 r8 a'4 |
      }
      \new Voice {
      \voiceTwo
      fis''64 a''64 b''64 a''64 a''64 cis''64 |
      r16 a''8 a''8 a''8 |
      a''8 a'8 r4 r16 d''4 |
      r8 e''4 gis''4 r8 a''8 |
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
      r4 r8 e'4 gis'4 r4 |
      <e'' e''>8 fis''16 e''8 d''8 cis''8 b'8 cis''32 |
      r8 fis'8 fis'8 gis'32 fis'64 <e' d''>32 e'16 gis'16 ais'8 <b' fis''>8 |
      ais'32 gis'32 fis'32 fis'16 ais'16 b'8 cis''8 b'32 ais'32 gis'32 |
      }
      \new Voice {
      \voiceTwo
      gis''8 fis''8 e''8 r4 r8 r4 b'8 |
      <e'' e''>8 fis''16 e''8 d''8 cis''8 b'8 cis''32 |
      r8 b'8 |
      gis'32 b'8 cis''16 d''16 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key b \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      e8 b'4 gis8 ais8 b8 e8 e4 |
      b'8 cis'8 ais8 fis16 b16 b'8 b,8 <e e>16 |
      r8 b,16 dis16 b,16 e1 |
      fis4 r8 fis8 gis4 r8 gis4 |
      }
      \new Voice {
      \voiceTwo
      e8 b'4 gis8 ais8 b8 e8 e4 |
      b'8 cis'8 ais8 fis16 b16 b'8 b,8 <e e>16 |
      r8 e4 e4 |
      fis4 r8 fis8 gis4 r8 gis4 |
      }
    >>
  }
  >>
  \layout { }
  \midi { }
}
