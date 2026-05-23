\version "2.20.0"

\header {
  title = "OMR transcription"
  subtitle = "From: IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf"
  tagline = ##f
}

\score {
  <<
  \new PianoStaff <<
    \new Staff {
      \clef treble
      \key c \major
      \time 4/4
      <<
        \new Voice {
        \voiceOne
        f'1 c'32 d'32 e'32 r1 f'16 g'16 f'16 <e' c'''>16 a'32 |
        <e' g'>64 <a' c'>8 <b' c'>8 |
        <c'' a>16.. d''16 c''16 <b' g'>32~ e''32 a'32 g'32 <d'' fis'>32~ <d'' fis'>16 e''16 <d'' d'>32 c''32 |
        }
        \new Voice {
        \voiceTwo
        f'1 c'32 d'32 e'32 r1 f'16 g'16 f'16 <e' c'''>16 a'32 |
        d'8 g'8~ g'64 a'64 g'32 f'32 e'64 f'64 d'32 d'8 b8 |
        fis'8 e'8 |
        }
      >>
    }
    \new Staff {
      \clef bass
      \key c \major
      \time 4/4
      r1 |
      r1 |
      r1 |
    }
  >>
  \new PianoStaff <<
    \new Staff {
      \clef treble
      \key c \major
      \time 4/4
      <<
        \new Voice {
        \voiceOne
        <g' b'>64 g'16 <a' f'>16 b'16 b'64 d''32 <e'' c'>64 d''32 e''32 fis''16 g''8 <b' g'>8 |
        <c'' g'>16 <f' a'>64 <d'' f'>8 c''8 b'16 a'16 g'16.. f'16 g'16 <f' d'>16 e'8 f'8 g'8 |
        g'32 <f' a'>64 b'16 c''2 <b' g'>4 |
        }
        \new Voice {
        \voiceTwo
        <e' c''>8 <d' c''>8 |
        e'8 f'8 e'8 |
        <c' a'>16 g'64 f'64 e'32 f'32 d'32 |
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
        r8 g32 a32 b16 r1 c'8.. d'16 c'16 b8 e'16 |
        a8 d'8~ d'8 e'16 d'8 c'8 b32 <c' c>32~ <c' d>8 <bes e>8 |
        <f a>64 d'16 <a c'>8 a64 <b g>64~ c'32 <d' g>8 |
        }
        \new Voice {
        \voiceTwo
        r8 g32 a32 b16 r1 c'8.. d'16 c'16 b8 e'16 |
        a8 d'8~ d'8 e'16 d'8 c'8 b32 <c' c>32~ <c' d>8 <bes e>8 |
        g16 f16 <e g>16 d32 a8 g8 f8 |
        }
      >>
    }
  >>
  \new PianoStaff <<
    \new Staff {
      \clef treble
      \key c \major
      \time 4/4
      <<
        \new Voice {
        \voiceOne
        c''64 d''64 e''32 f''16.. g''16 f''16 e''16 a''16 |
        d''8 g''8~ g''32 a''32 g''32 f''32 r1 e''8 a''8~ a''16 b''16 a''16 g''16 |
        f''2 fis''8 <g'' b'>8 |
        }
        \new Voice {
        \voiceTwo
        g'4 |
        d''8 g''8~ g''32 a''32 g''32 f''32 r1 e''8 a''8~ a''16 b''16 a''16 g''16 |
        g'8 a'8 b'8 <c'' e''>16.. d''16 c''16 e''8 |
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
        <g c>64 <a c'>8 d'16 c'16 |
        <g b>32 <a cis>8 <d' a>16 e'16 c'16 e'16 |
        <e' a>16 d'8 c'8 c'32 b32 c'32 a32 e'32 d'32 c'32 b32 |
        }
        \new Voice {
        \voiceTwo
        <e g>64 f64 e32 d32 c64 d64 b,32 <a, a>16 <d b>16 fis32 |
        a32 <bes e'>8 g8 <d d'>8~ d'8 <e b>16 |
        b64 c'64 d'64 b64 a64 g64 |
        }
      >>
    }
  >>
  \new PianoStaff <<
    \new Staff {
      \clef treble
      \key c \major
      \time 4/4
      <<
        \new Voice {
        \voiceOne
        <g'' a'>8 <d'' fis''>32 f''8 e''16 d''16 c''16 d''32 <c'' d'>32 b'32 |
        <a' e'>16 c''16 a'16 g'16 r8 c''8 b'16 a'16 <gis' e'>8 <e'' a'>8 |
        }
        \new Voice {
        \voiceTwo
        d''8~ e''16 d''16 c''16 <b' g''>16 |
        <fis' b'>32 r8 a'16 g'16 fis'8 |
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
        c'32 a32 b32 c'32 d'8 c'32 b32 a64 g4 |
        c16.. d16 c16 b,16 e32 a,8 d8~ d64 e64 d32 c32 |
        }
        \new Voice {
        \voiceTwo
        g,16 a,32 b,32 |
        c16.. d16 c16 b,16 e32 a,8 d8~ d64 e64 d32 c32 |
        }
      >>
    }
  >>
  \new PianoStaff <<
    \new Staff {
      \clef treble
      \key c \major
      \time 4/4
      <<
        \new Voice {
        \voiceOne
        <d'' a'>16 <c'' a'>16 <gis' b'>64 <a' fis'>64 gis'64 <a' f'>64 b'32 <c'' e'>16 fis'32 <gis' d'>32~ a'64 <b' d'>16 <a' fis'>32 <b' gis'>32 |
        <c'' a'>8 <f'' a'>8 <d'' gis'>8~ <d'' b'>16 c''32 b'64 b'8 a'8 |
        }
        \new Voice {
        \voiceTwo
        b'64 e'8 |
        gis'8 b'16 <gis' e''>16 fis'16 a'32 |
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
        e8 fis8 b16 a16 gis8 |
        fis8 e8 <b d>8~ b16 c'16 <b e>16 a16 gis64 f64 <a e>64 gis8 |
        }
        \new Voice {
        \voiceTwo
        b,8 <d gis>8 <c a>8 f8 <e c'>16 |
        d32 e4 |
        }
      >>
    }
  >>
  >>
  \layout { }
  \midi { }
}
