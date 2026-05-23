\version "2.20.0"

\header {
  title = "OMR transcription"
  subtitle = "From: IMSLP421137-PMLP03667-Ravel_Bolero.pdf"
  tagline = ##f
}

\score {
  <<
  \new Staff {
    \clef treble
    \key b \major
    \time 4/4
    b''8 b''8 cis'''8 dis'''8 cis'''8 b''64 ais''64 gis''64 fis''32 |
    gis''16 fis''8 e''8 e''8 e''8 fis''8 gis''8 ais''8 |
    fis''4 b''2 |
    b''2 b''8 r8 |
    <fis''' e>8 <fis''' e>16.. e'''8 dis'''8 cis'''8 dis'''8 e'''8 |
    fis'''8 e'''8 dis'''8 dis'''8 e'''8 dis'''8 cis'''8 e'''16 dis'''16 cis'''8 ais''8 |
  }
  \new Staff {
    \clef treble
    \key g \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      d''8 d''8 e''8 fis''16 e''16 d''16 c''8 b'8 a'8 |
      b'8 a'16 g'8 g'8 g'16 a'8 |
      a'8 |
      d''2 d''8 r8 |
      a''16 a''16.. g''8 fis''8 e''8 fis''16 g''16 |
      a''16 g''8 fis''8 fis''8 g''8 fis''8 e''8 g''16 fis''8 e''8 c''8 |
      }
      \new Voice {
      \voiceTwo
      d''8 d''8 e''8 fis''16 e''16 d''16 c''8 b'8 a'8 |
      b'16 c''16 |
      <d'' d''>2 |
      d''2 d''8 r8 |
      a''16 a''16.. g''8 fis''8 e''8 fis''16 g''16 |
      a''16 g''8 fis''8 fis''8 g''8 fis''8 e''8 g''16 fis''8 e''8 c''8 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 |
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'16 g'16 g'16 g'16 g'16 |
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 |
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'16 g'16 g'16 g'16 g'16 g'16 |
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 |
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 |
  }
  \new Staff {
    \clef treble
    \key d \major
    \time 4/4
    d'8 r8 r4 a8 r8 |
    d'8 r8 r4 a8 r8 |
    d'8 r8 r4 a8 r8 |
    d'8 r8 r4 a8 r8 |
    d'8 r8 r4 a8 r8 |
    d'8 r8 r4 a8 r8 |
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 4/4
    r4 <e' c'>8 r8 c'16 d'16 r8 |
    r4 <e' c'>8 r8 <e' b>8 r8 |
    r4 <f' d'>8 r8 <d' b>8 r8 |
    r4 <f' d'>8 r8 <d' b>8 r8 |
    r4 <f' d'>8 r8 <d' b>8 r8 |
    r4 <f' d'>8 r8 <d' b>8 r8 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      <d'' d'>4 <d'' d'>32 e''32 <fis'' d'>32 e''16 <d'' d'>8 c''8 <b' d'>16 a'16 |
      a'16 <g' d'>8 <g' d'>8 a'8 <b' d'>32 <c'' d'>32 |
      <a' d'>8 |
      <d'' d'>64 |
      <a'' d'>8 <a'' d'>32 g''32 <fis'' d'>64 e''64 <fis'' d'>64 g''32 |
      <a'' d'>8 g''16 <fis'' d'>8 <fis'' d'>8 g''16 <fis'' d'>16 e''16 <g'' d'>8 fis''8 <e'' d'>16 c''16 |
      }
      \new Voice {
      \voiceTwo
      d'16 d'16 d'16 d'16 d'16 |
      <d' b'>16 d'16 d'16 <d' g'>16 d'16 d'16 d'8 d'8 d'8 d'8 |
      d'16 d'16 d'16 <d' d''>16 d'16 d'16 d'16 d'16 d'16 |
      <d' d''>16 d'16 d'16 d'16 d'16 d'16 d'16 d'16 d'8 d'8 d'8 d'8 d'8 |
      d'16 d'16 d'16 d'16 d'16 d'16 |
      d'16 d'16 d'16 d'16 d'16 d'16 d'16 d'16 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    g''16 g''8 a''8 b''16 a''16 g''64 f''64 e''64 d''32 |
    e''16 d''8 c''8 c''16 c''16 d''16 e''8 f''8 |
    d''16 g''2 |
    g''2 g''8 r8 |
    d'''8 d'''16.. c'''8 b''8 a''8 b''8 c'''8 |
    d'''16 c'''8 b''8 b''16 c'''16 b''8 a''8 c'''16 b''8 a''8 f''8 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      g'16 g'16 a'16 b'16 a'16 g'64 f'64 e'64 d'64 |
      e'32 d'64 c'32 c'8 c'16 d'8 e'8 f'8 |
      d'8 g'2 |
      g'2 g'8 r8 |
      d''4 d''16 c''16 b'16 a'16 b'16 c''16 |
      c''8 b'8 a'16 f'16 |
      }
      \new Voice {
      \voiceTwo
      g'16 g'16 a'16 b'16 a'16 g'64 f'64 e'64 d'64 |
      e'32 d'64 c'32 c'8 c'16 d'8 e'8 f'8 |
      d'8 g'2 |
      g'2 g'8 r8 |
      d''4 d''16 c''16 b'16 a'16 b'16 c''16 |
      d''16 c''8 b'8 b'16 c''16 b'8 a'8 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    r4 g'2 |
    r4 g'2 |
    r4 g'2 |
    r4 g'2 |
    r4 g'2 |
    r4 g'2 |
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 4/4
    r4 g2 |
    r4 g2 |
    r4 g2 |
    r4 g2 |
    r4 g2 |
    r4 g2 |
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
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    r4 <e' c'>8 c'16 d'16 |
    r4 <e' c'>8 <e' c'>8 |
    r4 <f' d'>4 <d' b>8 |
    r4 <f' d'>4 <d' b>8 |
    r4 <f' d'>4 <d' b>8 |
    r4 <f' d'>4 <d' b>8 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    r4 d'4 <f''' b>8 |
    r4 d'4 b8 |
    r4 c'8 <c' f'''>8 |
    r4 c'8 <f''' c'>8 |
    r4 c'8 <f''' c'>8 |
    r4 c'8 <c' f'''>8 |
  }
  \new Staff {
    \clef alto
    \key c \major
    \time 4/4
    <g c>8 g8 <g' g>8 <g g' c>8 |
    <c g>8 g8 <g' g>8 <g g' c>8 |
    <g c>8 g8 <g' g>8 <g g' c>8 |
    <g c>8 g8 <g g'>8 <g g' c>8 |
    <g c>8 g8 <g' g>8 <g g' c>8 |
    <g c>8 g8 <g' g>8 <g' g c>8 |
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 4/4
    <e g, c,>16 r4 <g g,>4 |
    <g, c, e>16 r4 <g, g>4 g16 |
    <d g, c,>16 r4 <g, g>4 |
    <g, d c,>16 r4 <g g,>16 g16 |
    <c, d g,>16 r4 <g, g>4 |
    <g, d c,>16 r4 <g g,>16 g16 |
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 4/4
    c4 r4 g,16 |
    c4 r4 g,4 |
    c4 r4 g,4 |
    c4 r4 g,4 |
    c4 r4 g,4 |
    c4 r4 g,4 |
  }
  \new Staff {
    \clef treble
    \key e \major
    \time 4/4
    a''8 a''8 a''8 a''8 cis'''8 e'''8 cis'''8 dis'''8 b''8 |
    a''64 a''8 a''8 a''8 cis'''8 dis'''16 b''16 cis'''8 a''8 fis''8 |
    fis''16 fis''8 e''8 fis''32 fis''8 fis''8 fis''8 |
    fis''32 a''32 cis'''16 a''16 b''16 gis''8 fis''8 fis''16 e''2 |
    e''8 fis''16 fis''8 fis''8 e''8 fis''8 gis''8 a''64 |
    a''4 b''2 b''16 a''8 gis''8 fis''8 |
  }
  \new Staff {
    \clef treble
    \key g \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      c''16 c''16 c''16 c''32 e''32 g''64 e''64 fis''64 d''64 |
      c''8 c''8 c''8 c''32 e''32 fis''16 d''8 e''8 c''8 a'4 |
      a'16 a'8 g'8 a'32 a'16 a'16 a'16 |
      a'8 a'8 g'2 |
      g'64 a'32 a'32 a'32 g'64 c''2 |
      c''4 d''2 d''16 c''8 b'8 a'8 |
      }
      \new Voice {
      \voiceTwo
      c''16 c''16 c''16 c''32 e''32 g''64 e''64 fis''64 d''64 |
      c''8 c''8 c''8 c''32 e''32 fis''16 d''8 e''8 c''8 a'4 |
      a'16 a'8 g'8 a'32 a'16 a'16 a'16 |
      a'32 c''32 e''64 c''64 d''64 b'32 |
      a'32 b'64 |
      c''4 d''2 d''16 c''8 b'8 a'8 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 |
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'16 g'16 g'16 g'16 g'16 g'4 |
    g'16 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 |
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'16 g'16 g'16 g'16 |
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 |
    g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 g'8 |
  }
  \new Staff {
    \clef treble
    \key d \major
    \time 4/4
    d'8 r8 r4 a8 r8 |
    d'8 r8 r4 a8 r8 d'8 |
    d'8 r8 r4 a8 r8 |
    d'8 r8 r4 a8 r8 |
    d'8 r8 r4 a8 r8 |
    d'8 r8 r4 a8 r8 |
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 4/4
    r4 <f' d'>8 r8 <d' b>8 r8 r4 |
    r4 <f' d'>8 r8 <d' b>8 r8 r4 |
    <f' d'>8 r8 <d' b>8 r8 |
    r4 <f' d'>8 r8 <d' b>8 r8 |
    r4 <f' d'>8 r8 <d' b>8 r8 f,,1 |
    f,,1 r4 <e' c'>8 r8 c'16 d'16 r8 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    <<
      \new Voice {
      \voiceOne
      <c'' d'>16 <c'' d'>16 c''16 <c'' d'>32 <e'' d'>32 <g'' d'>32 e''64 <fis'' d'>64 d''64 |
      <d' c''>8 <c'' d'>8 c''8 <c'' d'>16 <e'' d'>16 <fis'' d'>32 d''64 <e'' d'>64 c''64 |
      <d' a'>32 <a' d'>8 g'8 <a' d'>16 <a' d'>16 <a' d'>16 a'16 |
      <a' d'>32 <c'' d'>32 <e'' d'>32 c''64 <d'' d'>64 b'64 <a' d'>8 <a' d'>8 |
      g'8 <a' d'>32 <a' d'>16 <a' d'>16 g'16 <a' d'>16 <b' d'>16 c''64 |
      c''8 <d'' d'>2 <d'' d'>8 c''8 <b' d'>32 a'16 |
      }
      \new Voice {
      \voiceTwo
      d'8 d'8 d'8 d'8 |
      d'16 d'8 d'8 d'8 d'16 d'16 d'16 d'8 <d' a'>8 |
      d'16 d'8 d'8 d'8 d'8 |
      d'8 d'8 d'8 d'8 d'32 d'32 <d' g'>32 |
      d'8 d'16 d'16 d'16 d'16 d'16 |
      d'8 d'8 d'8 d'8 d'8 d'8 d'8 d'8 d'8 d'8 d'8 |
      }
    >>
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    f''8 f''8 f''8 f''32 a''32 c'''16 a''8 b''8 g''8 |
    f''8 f''8 f''8 f''32 a''32 b''16 g''8 a''8 f''8 |
    d''8 d''8 c''8 d''16 d''8 d''8 d''8 |
    d''8 f''8 a''16 f''16 g''16 e''8 d''8 d''16 c''8 |
    d''16 d''8 d''8 c''8 d''8 e''8 f''8 |
    g''2 g''16 f''8 e''8 d''8 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    f'8 f'8 f'8 f'16 a'16 c''16 a'16 b'32 g'64 |
    f'8 f'8 f'8 f'32 a'32 b'64 g'64 a'64 f'64 |
    d'8 d'8 c'16 d'8 d'8 d'8 d'8 |
    d'32 f'32 a'8 f'8 g'8 e'16 d'8 d'8 c'8 |
    d'32 d'16 d'16 c'16 d'16 e'16 f'16 |
    g'2 g'8 f'8 e'16 d'16 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    r4 g'2 |
    r4 g'2 |
    r4 g'2 |
    r4 g'2 |
    r4 <g' g'>2 |
    r4 g'2 |
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 4/4
    r4 g2 |
    r4 g2 |
    r4 g2 |
    r4 g2 |
    r4 g2 |
    r4 g2 |
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
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    r4 <f' d'>4 <d' b>8 |
    r4 <d' f'>4 <d' b>8 |
    r4 <f' d'>4 <d' b>8 |
    r4 <d' f'>4 <d' b>8 |
    r4 <f' d'>4 <d' b>8 |
    r4 <e' c'>8 c'8 d'8 |
  }
  \new Staff {
    \clef treble
    \key c \major
    \time 4/4
    r4 c'8 <f''' c'>8 |
    r4 c'8 <c' f'''>8 |
    r4 c'8 <c' f'''>8 |
    r4 c'8 <c' f'''>8 |
    r4 c'8 <c' f'''>8 |
    r4 c'8 <f''' c'>8 d'16 |
  }
  \new Staff {
    \clef alto
    \key c \major
    \time 4/4
    <g c>8 g8 <g' g>8 <g' g c>8 |
    <g c>8 g8 <g' g>8 <g c g'>8 |
    <c g>8 g8 <g' g>8 <g' g c>8 |
    <c g>8 g16 <g' g>16 <g g' c>16 |
    <c g>8 g8 <g' g>8 <g g' c>8 |
    <c g>8 g8 <g' g>8 <c g' g>8 |
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 4/4
    <g, d c,>16 r4 <g, g>4 |
    <g, c, d>16 r4 <g g,>16 g16 |
    <d c, g,>16 r4 <g g,>4 |
    <d g, c,>16 r4 <g g,>16 g16 |
    <g, d c,>16 r4 <g g,>4 |
    <g, e c,>16 r4 <g, g>4 g16 |
  }
  \new Staff {
    \clef bass
    \key c \major
    \time 4/4
    c8 r4 g,4 |
    c4 r4 g,4 |
    c4 r4 g,4 |
    c8 r4 g,8 |
    c4 r4 g,4 |
    c4 r4 g,4 |
  }
  >>
  \layout { }
  \midi { }
}
