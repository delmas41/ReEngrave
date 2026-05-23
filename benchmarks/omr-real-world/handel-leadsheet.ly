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
    \key e \major
    \time 4/4
    r8 cis''8 fis''4 r2 |
    b'4 cis''4 dis''8 fis''8 fis''4 |
    r1 |
    r8 cis''8 dis''8 cis''8 dis''8 cis''8 dis''8 cis''8 |
  }
  \new Staff {
    \clef treble
    \key e \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      r8 ais'4 r2 |
      b8 ais'8 |
      r1 |
      r8 ais'16 b'16 ais'16 b'8 ais'8 b'8 ais'8 |
      }
      \new Voice {
      \voiceTwo
      r8 cis''8 r2 |
      b'4 b'32 dis''32 dis''4 |
      r1 |
      r8 ais'16 b'16 ais'16 b'8 ais'8 b'8 ais'8 |
      }
    >>
  }
  \new Staff {
    \clef alto
    \key e \major
    \time 4/4
    r8 fis'8 cis''8 r2 |
    fis'8 gis'16 fis'16 fis'8 r4 |
    r1 |
    r8 fis'8 fis'8 fis'8 fis'8 fis'8 fis'8 fis'8 |
  }
  \new Staff {
    \clef treble
    \key e \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      cis''16 b'16 ais'8 ais'8 cis''8 dis''8 e''16 dis''16 cis''16 b'16 dis''16 e''8 dis''8 cis''8 e''8 |
      r2 r4 r8 fis'8 |
      fis'8 |
      fis'2 |
      }
      \new Voice {
      \voiceTwo
      cis''16 b'16 ais'8 ais'8 cis''8 dis''8 e''16 dis''16 cis''16 b'16 dis''16 e''8 dis''8 cis''8 e''8 |
      r2 fis''4 b'8 r4 r8 b'8 dis''8 |
      fis''4 e''8 dis''8 e''8 dis''8 cis''8 b'8 |
      fis'2 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key e \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      ais4 r8 ais8 b16 dis16 cis16 fis16 |
      b,8 r8 |
      ais8 gis8 ais8 fis8 b4 b,8 cis8 e8 |
      fis,2 |
      }
      \new Voice {
      \voiceTwo
      ais4 r8 ais8 b16 dis16 cis16 fis16 |
      dis16 e16 fis16 r8 b16 |
      ais8 gis8 ais8 fis8 b4 b,8 cis8 e8 |
      fis,2 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key e \major
    \time 4/4
    dis''16 cis''16 r4 r2 |
    r4 r8 b''8 cis'''8 b''8 cis'''8 b''8 |
    b''8.. fis''8 gis''8 fis''8 gis''8 fis''8 |
    gis''8 fis''8 gis''16 fis''16 e''8 dis''8 e''8 dis''8 |
  }
  \new Staff {
    \clef treble
    \key e \major
    \time 4/4
    b'16 ais'16 r4 r2 |
    r4 r8 dis''8 e''8 dis''8 e''8 dis''8 |
    gis''8 fis''8 r8 dis''8 e''8 dis''8 e''8 dis''8 |
    e''8 dis''8 e''8 dis''8 cis''8 b'8 cis''8 b'8 |
  }
  \new Staff {
    \clef alto
    \key e \major
    \time 4/4
    fis'8 fis'8 r4 r2 |
    r2 r4 r8 b8 |
    e'16 dis'16 r8 b'8 b'8 b'8 b'8 b'8 |
    b'8 b'8 r8 b'8 gis'8 gis'8 gis'8 gis'8 |
  }
  \new Staff {
    \clef treble
    \key e \major
    \time 4/4
    r4 r8 b'8 cis''16 b'16 cis''16 b'16 |
    b'2 r2 |
    r4 b'8 b'8 b'4 b'8 b'8 |
    b'2 e''2 |
  }
  \new Staff {
    \clef bass
    \key e \major
    \time 4/4
    r4 r8 dis8 e16 dis16 e16 dis16 |
    e8 dis8 r4 r2 |
    r4 r8 b,8 e8 b,8 e8 b,8 |
    e16 b,16 r8 b,8 cis8 gis,8 cis8 e8 |
  }
  \new Staff {
    \clef treble
    \key e \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      cis''4 r4 ais''8 b''8 cis'''8 b''8 |
      ais''8 r4 ais'32 b'32 cis''32 b'32 |
      ais'8 b'8 cis''8 fis'8 dis'4 r8 |
      r8 cis'8 |
      }
      \new Voice {
      \voiceTwo
      cis''4 r4 ais''8 b''8 cis'''8 b''8 |
      ais''8 r4 ais'32 b'32 cis''32 b'32 |
      r8 cis''8 |
      dis''8 gis''8 fis''8 ais'8 b'4 r8 |
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
      ais'4 r4 |
      r4 cis'8 b8 ais8 b8 |
      cis'8 b8 fis'8 fis'8 fis'4 r8 ais'8 |
      fis'8 e'8 b'8 cis'16 dis'8 gis'8 fis'8 ais16 |
      }
      \new Voice {
      \voiceTwo
      r4 cis''8 b'8 ais'8 b'8 |
      cis''4 r4 |
      cis'8 b8 fis'8 fis'8 fis'4 r8 ais'8 |
      fis'8 e'8 b'8 cis'16 dis'8 gis'8 fis'8 ais16 |
      }
    >>
  }
  \new Staff {
    \clef alto
    \key e \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      cis'4 r4 e'8 e'8 e'8 e'8 |
      e'4 r4 e'8 e'8 e'8 e'8 |
      b4 r8 |
      b4.. r8 fis8 |
      }
      \new Voice {
      \voiceTwo
      cis'4 r4 e'8 e'8 e'8 e'8 |
      e'4 r4 e'8 e'8 e'8 e'8 |
      e'64 e'64 e'64 cis'32 r8 cis'8 |
      fis'8 fis'4 r8 |
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
      e''8 dis''8 e''8 dis''8 e''2 |
      e''8 dis''8 e''8 dis''8 e''2 |
      r8 ais'8 |
      r8 ais'8 |
      }
      \new Voice {
      \voiceTwo
      e''8 dis''8 e''8 dis''8 e''2 |
      e''8 dis''8 e''8 dis''8 e''2 |
      e''4 r8 cis''8 dis''64 gis''64 fis''64 |
      b'4 r8 cis''8 dis''8 gis''8 fis''8 |
      }
    >>
  }
  \new Staff {
    \clef bass
    \key e \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      fis4 r4 fis8 gis8 ais8 gis8 |
      fis4 r4 fis8 gis8 ais8 gis8 |
      ais8 |
      <b, b'>8 e8 dis8 fis8 b,8 e8 dis8 fis8 |
      }
      \new Voice {
      \voiceTwo
      fis4 r4 fis8 gis8 ais8 gis8 |
      fis4 r4 fis8 gis8 ais8 gis8 |
      fis8 gis8 ais,8 b,8 e8 dis8 fis8 |
      <b, b'>8 e8 dis8 fis8 b,8 e8 dis8 fis8 |
      }
    >>
  }
  >>
  \layout { }
  \midi { }
}
