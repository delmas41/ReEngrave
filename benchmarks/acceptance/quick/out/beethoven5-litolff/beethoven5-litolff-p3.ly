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
      d'''2~ |
      <d''' g'''>2 |
      <ees''' f'''>4 <d''' f'''>4 |
      <c''' f'''>2 |
      <ees''' f'''>2 |
      c'''2 |
      f'''2 |
      <b'' aes'''>4 r4 |
      r1 |
      c'''4 r4 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r1 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r1 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      bes''4 ees'''4 |
      <d''' ees'''>4 ees'''4 |
      f'''8 |
      c'''4( bes''4) |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
    }
    \new Staff \with {
      instrumentName = "Oboe"
    } {
      \clef treble
      \key ees \major
      g''2 |
      f''2 g''2 |
      f''4 g''4 <ees'' g''>4 |
      <ees' ees'' ges''>2 |
      aes''2 |
      g''2~ |
      <ees'' g''>2 |
      <ees'' ges''>4 r4 |
      r1 |
      <bes' f''>4 r4 |
      r1 |
      r1 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r1 |
    }
    \new Staff \with {
      instrumentName = "Clarinet"
    } {
      \clef treble
      \key f \major
      <e' a' a'>2 |
      a'2 |
      <e' g'>4 <d' f'>4 |
      aes'2 |
      a'2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      f''2 |
      <a' f''>4 r4 |
      r1 |
      c''4 r4 |
      r1 |
      r1 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r1 |
      r1 |
      c''4 f''4 |
      e''4 f''4 |
      g''8 |
      d''4 c''4 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Bassoon"
    } {
      \clef bass
      \key ees \major
      g1 b,2 |
      bes,2 |
      <c ees>4 |
      <ees b>2~ |
      <ees bes>2 |
      aes2~ |
      aes2 |
      <ees aes>4 r4 |
      r1 |
      <d f>4 r4 |
      r1 |
      r1 |
      r1 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r1 |
      r1 |
      aes2 |
      bes2 |
      <bes, f>2 |
      <ees g>2 |
      <g bes>2 |
      <f bes>2 |
      <c f>2 |
      g2 |
      <g bes>2 |
      <f aes>2 |
      d2 |
      <f g aes>2 |
      aes2 |
      bes2 |
      <ees g>2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Horn"
    } {
      \clef treble
      \key c \major
      d''2(\=2( e''4)\=2) |
      e''2~ |
      d''8 e''4 <c'' e''>4 |
      <c'' ees'' e''>2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      e''2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      <c'' ees''>4 r4 |
      r1 |
      <g' d''>4 r4 |
      g''8 g''8 g''8 |
      c''2 |
      d''4 |
      g'2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      g'2 |
      g'2 |
      g'2 |
      <f' g'>2~ |
      g'2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      f'2 |
      g'2 |
      g'2 |
      g'2 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
    }
    \new Staff \with {
      instrumentName = "Trumpet"
    } {
      \clef treble
      \key c \major
      \once \override Rest.color = #red r1^\markup { "unread" } |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r4 <c' c''>16 <c' c''>8 |
      c'2 |
      c'2~ |
      c'2~ |
      c'4 |
      <c' c''>4 r4 |
      r1 |
      r1 |
      r1 |
      r4 r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Timpani"
    } {
      \clef bass
      \key c \major
      \once \override Rest.color = #red r1^\markup { "unread" } |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r4 c8 c8 |
      c2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      b4 |
      c2~ |
      c4 r4 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      \once \override Rest.color = #red r1^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Staff p3-s0-7"
    } {
      \clef treble
      \key ees \major
      b''8 g''4 f''4 f''4 |
      d''8 bes'8 g'8 f'8 |
      d'8 b16 c'8 c'16 |
      ees'''8 ees'''8 ees'''8 |
      c'''4 a''8 <bes' a''>4 a''8 |
      ges''8 ees''8 ees''8 ees''8 |
      c''8 <a a'>8 <a a'>8 <a a'>8 |
      <a aes'>4 r4 |
      r1 |
      <aes f' bes' d''>4 r4 |
      r1 |
      r1 |
      r1 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      d''4 ees''4 |
      f''4( c''4) |
      c''4 bes'4 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      bes'4 ees''4 |
      d''4 ees''4 |
      f''4 c''4 |
      c''4( bes'4) |
      bes'4( c''4) |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      bes'4( c''4) |
      bes'8 aes'8 |
      des''4( |
      f''4 ees''4) |
      des''4( |
      des''4 c''4) |
    }
    \new Staff \with {
      instrumentName = "Staff p3-s0-8"
    } {
      \clef treble
      \key bes \major
      bes'8 g'8 f'8 f'8 |
      d'8 b8 g8 f'8 |
      d'8 a16 c'16 c'16 |
      c''8 ees''8 ees''8 ees''8 |
      a'8 a'8 a'8 |
      ges'8 ees'8 ees'8 ees'8 |
      bes4 <g a'>16 <a a'>8 <a a'>8 |
      <a a'>4 r4 |
      r1 |
      <a f' bes'>4 r4 |
      r1 |
      r1 |
      r1 |
      r1 |
      g'2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      \key ees \major
      r8 f'2 |
      g'4 |
      g'2 |
      <d' d'>2 aes'2 |
      aes'2 |
      aes'2 |
      g'2 |
      aes'2 |
      aes'2 |
      g'2 |
      g'2 |
      g'2 |
      g'2 |
      f'4 |
      aes'2 |
      <ees' bes'>2 |
      bes'2 |
      aes'2 |
    }
    \new Staff \with {
      instrumentName = "Staff p3-s0-9"
    } {
      \clef alto
      \key ees \major
      <d f ees'>2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      <d f>8 <bes, ees>8 <c ees>8 |
      <bes, ees>8 ees8 <ees g>8 <ees g>8 |
      ees2 |
      <ees ges>2 |
      <ees f ees'>2 |
      <ees g>4 r4 |
      r1 |
      f4 r4 |
      r1 |
      r4 r1 |
      r1 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      ees'2 |
      <f' f'>2 |
      d'4 |
      f'2 |
      ees'2 |
      f'2 |
      d'2 |
      ees'2 |
      ees'2 |
      f'2 |
      d'2 |
      ees'2 |
      ees'2 |
      ees'2 |
      <ees' ees'>2 |
      c'2 |
      f'2 |
      g'2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      ees'2 |
    }
    \new Staff \with {
      instrumentName = "Staff p3-s0-10"
    } {
      \clef bass
      \key ees \major
      g,2 |
      g,2 |
      g,8 g,8 c8 c8 |
      <c aes>2 |
      g4 |
      c2 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      c4 r4 |
      \once \override Rest.color = #red r1^\markup { "unread" } |
      d4 r4 |
      r1 |
      r4 r1 |
      r1 |
      r1 |
      r1 |
      r1 |
      r8 bes,8 bes,8 bes,8 |
      ees4 r4 c4 |
      r1 |
      r1 |
      r8 bes,8 bes,8 bes,8 |
      ees4 |
      r1 |
      r1 |
      r8 bes,8 bes,8 bes,8 |
      ees4 r4 |
      r1 |
      r1 |
      r8 c8 |
      f4 r4 |
      r1 |
      r1 |
      ees8 |
      aes4 g1 |
    }
  >>
  \layout { }
}
