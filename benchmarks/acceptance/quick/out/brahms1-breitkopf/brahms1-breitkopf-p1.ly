\version "2.24.4"

\header {
  title = "OMR transcription"
  tagline = ##f
}

\score {
  <<
    \new Staff \with {
      instrumentName = "Flute"
    } {
      \clef treble
      \key ees \major
      \time 6/8
      <c'' c'''>4.( <g'' bes''>4. |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      c'''8 f'''4( f'''8) aes''4 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      des''8 r8 r8 r4 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      r4 r8 r4 aes''8~\trill |
      aes''8 g''8 aes''8( aes''8 g''8) aes'''8~ |
      aes'''8 g'''8 f'''8 ees'''8 des'''8 bes''8 |
      aes''8 g''8 f''8 ees''8 des''8 aes'8 |
      g'4 r8 r4 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Oboe"
    } {
      \clef treble
      \key ees \major
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      <d'' f''>4.( <c'' ees''>4.) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      <b' d''>4.~( <b' d''>8 <c'' ees''>8 <d'' f''>8) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      <aes'' c'''>4(\=2( <d'' bes''>8 <ces'' e''>4) <d'' f''>8\=2) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      bes'8 f''4( f''8) aes'4( |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      ees'8 bes'4~( bes'8) des'4 |
      des'8 r8 r8 r4 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Clarinet"
    } {
      \clef treble
      \key f \major
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      <e'' g''>4.( <d'' f''>4.) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      <g' bes'>8 r8 r8 r4 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      <ees' c''>8 r8 r8 r4 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Bassoon"
    } {
      \clef bass
      \key ees \major
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      <d f>4.( <c ees>4.) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      <b, d>4.( <b, d>8 <c ees>8 <d f>8) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      aes8) g8 aes8(\=2(\=3(\=4( aes8\=2)\=4) g8)\=3) ees'8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      aes8 g8 f8 ees8 des8 aes,8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Contrabassoon"
    } {
      \clef bass
      \key ees \major
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      c,2. |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      f4 g,8 r8 r4 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Staff p0-s0-5"
    } {
      \clef treble
      \key c \major
      \time 6/8
      <c c'>2.~ |
      c'2. |
      <c b>2. |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      <c b>2. |
      c'2.~ |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Horn"
    } {
      \clef treble
      \key c \major
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      r2. |
      r2. |
      r2. |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Trumpet"
    } {
      \clef treble
      \key c \major
      \time 6/8
      <c' c''>4.~(\=2(\=3( <c' c''>8)\=2)\=3) r8 r8 |
      r2. |
      r2. |
      r2. |
      r2. |
      r2. |
      r2. |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Timpani"
    } {
      \clef bass
      \key c \major
      \time 6/8
      c8 c8 c8 c8 c8 c8 |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      c2. |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      c2. |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      c2. |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      g,2. |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Violin"
    } {
      \clef treble
      \key ees \major
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      c'''4\=2) d'''8( d'''8.) ees'''16 f'''16 g'''16~\=3) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      aes'''8.\=2) g'''16( g''16 d'''16 g'''4 f'''8~) |
      f'''8. ees'''16 ees''16( c'''16 ees'''4 d'''8)\=2( |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      r8 f''8 f''8 f''8 r8 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      aes''8 g''8 f''8 ees''8 des''8 bes'8 |
      aes'8 g'8 f'8 ees'8 des'8 aes8 |
      g4(\=2( ees'8 g'4.)\=2) |
      ees'8(\=2( g8 ees'8 g'4 ees'8)\=2) |
    }
    \new Staff \with {
      instrumentName = "Violin"
    } {
      \clef treble
      \key ees \major
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      aes''8.\=2)( g''16 g'16 d''16 g''4 f''8~) |
      f''8.( ees''16 ees'16 c''16 ees''4 d''8~) |
      d''16( c''16 c'16 aes'16 c''8 c''16 bes'16 c'16 g'16 bes'8) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      b'8 r8 r8 r8 aes'8 aes'8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      bes8 r8 r8 r8 e'8 e'8 |
      e'8 r8 r8 r8 des'8 des'8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      des'8 des'8 r8 r4 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      g4( ees'8) g'4. |
      ees'8~( g8 ees'8 g'4 ees'8) |
    }
    \new Staff \with {
      instrumentName = "Viola"
    } {
      \clef alto
      \key ees \major
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      <bis d'>4.\=4)( <bis d'>8\=2(\=3( <c' ees'>8 <d' f'>8\=2) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      c''4(\=2(\=3(\=4( d''8 <c' e''>4 <d' f''>8--)\=2)\=3)\=4) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      r8 f'8 f'8 f'8 r8 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      aes8 f'8 aes8~( aes8\> g8) g8\! |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      r8 bes8 bes8 bes8 r8 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      d8 bes8 bes8~(\=2( bes8\> aes8)\=2)\! ees8~ |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      f8 d'8 c'8( bes8 bes8) c'8 |
      aes8 aes8 r8 r4 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Cello"
    } {
      \clef tenor
      \key ees \major
      \time 6/8
      c'4.~(\=2( c'4\=2) cis'8 |
      c'4 d'4 ees'16 <aes f'>16 g'16~) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      aes'8. g'16( g16 d'16 g'4 f'8~ |
      f'8. bes'16 bes16 g'16 bes'4 aes'8~) |
      aes'16 g'16(\=2( g16 ees'16 g'8\=3( g'16\=3) f'16 g16 d'16) f'8\=2) |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \clef bass
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      aes8 des8~ des8 des8 des8 des8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      des8 ges,8~(\=2( ges,8 ges,8 ges,8 ges,8)\=2) |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      ais,8 ais,8 ais,8 bes,8 bes,8~ bes,8 |
      bes,8 bes,8 c8 d8 d8 ees8 |
      f8 f8 r8 r4 r8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Contrabass"
    } {
      \clef bass
      \key ees \major
      \time 6/8
      c8~( c8 c8 c8 c8 c8) |
      <c bes>2. |
      c2. |
      c2. |
      c2.~ |
      c2. |
      <c bes>2. |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      r8 ges,8( ges,8 ges,8 ges,8 ges,8) |
      g,8 g,8 g,8 aes,8 aes,8 aes,8 |
      \time 6/8
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
      \once \override Rest.color = #red r2.^\markup { "unread" } |
    }
  >>
  \layout { }
}
