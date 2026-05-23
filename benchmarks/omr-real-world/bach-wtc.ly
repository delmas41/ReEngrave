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
        a'4 |
        <e' g'>64 <fis' a'>64 <b' g'>32 |
        <c'' g'>16.. d''16 c''16 <gis' b'>32 <c'' a'>16 <d'' a'>16 <e'' g'>16 <f'' a'>8 g''16 f''16 |
        }
        \new Voice {
        \voiceTwo
        c'32 d'64 e'64 f'16.. g'16 f'16 e'8 a'8 |
        d'16 g'32 g'64 a'64 g'32 f'32 e'16 |
        fis'16 b'16 |
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
        <a a,>4 r4 r8 g8 a16 b16 c'8.. d'16 c'16 |
        b8 <e' g,>16 <a a,>64 <d' b,>32 <d' c>8 g8 |
        <c' a,>32 <a d>32 <e' d>16 <d' b,>8 |
        }
        \new Voice {
        \voiceTwo
        <a a,>4 r4 r8 g8 a16 b16 c'8.. d'16 c'16 |
        d16 c16 <b, d'>16 e32 |
        e64 d32 c32 bes,16 a,16 g,16 |
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
        a''16 <d'' b'>16 <g'' e''>16 <g'' a'>16 a''16 <g'' d''>16 f''16 e''8 d''8 <a'' d''>8 |
        <b' d''>16 <g'' bes''>64 f''16 f''16 e''16 <f'' d''>32 g''16 |
        <f'' g'' f''>16 <e'' f'' f'' f''>16 <g'' a''>16 |
        }
        \new Voice {
        \voiceTwo
        <c'' e''>16.. d''16 c''16 e''16 c''16 |
        <cis'' a''>16 <d'' g''>16 <e'' g''>32 <cis'' g''>32 |
        <f'' g'' f''>16 <e'' f'' f'' f''>16 <g'' a''>16 |
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
        <a fis>8 <g b>16 <cis' e>8 <d' d>8.. e'16 d'8 <c' e>8 |
        e'16 <e' f>16 f'16 <e' bes>16 d'8 <cis' e>8 |
        <g a>32 <g g>8 |
        }
        \new Voice {
        \voiceTwo
        a,8 <f' f>16 |
        <g b>8.. a8 g8 a32 a8 bes8 |
        <g a>32 <g g>8 |
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
        <a'' a'>8 cis''16 d''16 g''16 e''8.. d''8 <d'' fis'>16 |
        <g' e'>16 |
        <a' e'>8 b'8 <c'' d'>16.. d''16 c''16 <b' d'>64 <e'' g'>32 <a' e'>8 <d'' f'>8 |
        }
        \new Voice {
        \voiceTwo
        e'8 g'16 a'16.. b'16 a'16 |
        g'8 c''8 fis'32 b'64 b'16 c''16 b'8 a'8 g'16 fis'8 d'8 |
        a'16 f'16 g'64 a'64 |
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
        <a f>16 <b g>16 <cis' a>16 <d' d>8.. e'16 d'16 c'8 |
        <b d>8 <e' d>16 <e' b,>16 <e' g,>16 <d' fis,>8 |
        <c' g>16 d'16 <a c'>8 <b g>16 <a fis>16 g16 <a d>16 fis16 g8 g2 b8 c'8 d'8 |
        }
        \new Voice {
        \voiceTwo
        f8 e8 d8 fis'16 |
        e16 c8 <fis' a,>16 <e, c'>8 e8 fis8 g8 |
        <c' g>16 d'16 <a c'>8 <b g>16 <a fis>16 g16 <a d>16 fis16 g8 g2 b8 c'8 d'8 |
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
        <d'' g'>8 e''8 d''16 c''16 <b' g'>16 <des'' b'>8 e''8 <f'' c''>16 g''16 a''16 g''16 <f'' des''>8 e''8 <des'' g'>8 c''16 |
        <b' g'>4 c''8 <d'' f'>8 g'16 f'8 b'8 |
        <c'' e'>8 b'16 <bes' g'>16 a'32 g'32 <d'' f'>32 <c'' a'>32 |
        }
        \new Voice {
        \voiceTwo
        <a' c''>32 |
        <e' c''>8 d'4 |
        a'4 g'32 |
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
        <e' g>16.. f'32 e'16 d'8 g'32 <c' a>8 f'16 g'32 e'16 |
        <e' e>16 g4 |
        <g c>8 c8 d8 e8 f16 g16 f16 e32 a16 |
        }
        \new Voice {
        \voiceTwo
        <f' b>32 <f' c'>32 |
        <f d'>16 a16 g16 f16 d8 <c d'>8 b,8 <c d'>8 d8 <e g>8 f16 g,16 |
        <g c>8 c8 d8 e8 f16 g16 f16 e32 a16 |
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
        <des'' b'>16 e''16 <f'' a'>32 <f'' g'>16 a''16 <g'' c''>16 f''16 <f'' des''>16 <e'' c''>16 <des'' b'>16 |
        g'16 a'16 b'8 c''8 <d'' d'>32 e''16 f''16 |
        <f'' a'>64 c''64 d''64 e''64 f''64 g''64 a''8.. b''8 |
        <e' f g' b' e' e d>4 |
        }
        \new Voice {
        \voiceTwo
        c''16 b'16 des''32 <c'' e''>16 |
        <a' c''>64 bes'64 a'32 g'32 f'64 g'64 f'64 e'32 d'4 g'8 |
        f''16 d''8 <c''' g'' e''>2 |
        <e' f g' b' e' e d>4 |
        }
      >>
    }
    \new Staff {
      \clef bass
      \key c \major
      \time 4/4
      d16 c1 g16 g16 a32 g32 f32 e64 d64 e64 f32 g8 a8 bes8 g8 |
      <a c>8 e8 f16 g16 a16 b16 c'16 a16 b2 |
      <c c'>1 b'4 b'4 |
      <d a f b' d>4 |
    }
  >>
  >>
  \layout { }
  \midi { }
}
