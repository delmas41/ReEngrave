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
      \time 2/4
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2\fermata |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2\fermata |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <b'' aes'''>4 r4\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f''2 |
      f''2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c'''4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <b'' ees'''>4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      aes'''2 |
      d'''2~ |
      <d''' ees''' g'''>2 |
      <ees''' f'''>4 <d''' f'''>4 |
      <c''' f'''>2 |
      <ees''' f'''>2 |
      c'''2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <b'' aes'''>4 r4 |
      r2 |
      c'''4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      bes''4 ees'''4 |
      <d''' ees'''>4 ees'''4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c'''4( bes''4) |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
    }
    \new Staff \with {
      instrumentName = "Oboe"
    } {
      \clef treble
      \key ees \major
      \time 2/4
      r2 |
      r2\fermata |
      r2 |
      r2 |
      r2\fermata |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <bes' g''>4 r4\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <f'' f''>2~ |
      f''2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      ees''4 r4 |
      r2 |
      r2 |
      g''2 |
      <ees'' ees'' g''>4 r4 |
      <f'' aes''>4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <f'' aes''>4 r4 |
      <g'' g'' bes''>4 r4 |
      <f'' aes''>4 r4 |
      <f'' aes''>4 r4 |
      <ees'' g''>2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g''2 |
      aes''2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g''2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      aes''2 |
      g''2~ |
      <ees'' g''>2 |
      <ees'' ges''>4 r4 |
      r2 |
      <bes' f''>4 r4 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
    }
    \new Staff \with {
      instrumentName = "Clarinet"
    } {
      \clef treble
      \key f \major
      \time 2/4
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f'2\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      e'2 |
      f'2\fermata |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c'4 <cisis' cisis' e'>4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <c' e'>4 r4\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d''4 r4 |
      r2 |
      r2 |
      r2 |
      r2 |
      <g' bes'>4 r4 |
      <fis' a'>4 r4 |
      <g' bes'>4 r4 |
      <a' c''>4 r4 |
      <g' bes'>4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f'2 |
      <e' e' a'>2 |
      <e' a' a'>2 |
      a'2 |
      <e' g'>4 <d' f'>4 |
      aes'2 |
      a'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f''2 |
      <a' f''>4 r4 |
      r2 |
      c''4 r4 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      c''4 f''4 |
      e''4 f''4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d''4 c''4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Bassoon"
    } {
      \clef bass
      \key ees \major
      \time 2/4
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2\fermata |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d'2 |
      c'2 |
      d'4 r4 |
      bes2 |
      bes2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      bes2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g,4 r4\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f,2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \clef tenor
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      <ees' aes'>4 |
      <ees' g'>4 c'4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <g fes'>4 r4 |
      ees'4 r4 |
      <aes aes bes>4 r4 |
      <g c'>4 r4 |
      <g g'>4 r4 |
      <aes bes>2~ |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <g bes>2 |
      <g bes>2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \clef bass
      \once \override Rest.color = #red r2^\markup { "unread" } |
      bes,2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <ees b>2~ |
      <ees bes>2 |
      aes2~ |
      aes2 |
      <ees aes>4 r4 |
      r2 |
      <d f>4 r4 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
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
      \once \override Rest.color = #red r2^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Horn"
    } {
      \clef treble
      \key c \major
      \time 2/4
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2\fermata |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2\fermata |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <e' e''>4 r4\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r8 e'8 e'8 e'8 |
      e'4 r4 |
      <d'' g''>4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <c'' e''>2 |
      c''2 |
      <d'' e''>2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      e''4 e''4 |
      d''4(\=2( e''4)\=2) |
      e''2~ |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      e''2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <c'' ees''>4 r4 |
      r2 |
      <g' d''>4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c''2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g'2 |
      g'2 |
      g'2 |
      <f' g'>2~ |
      g'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f'2 |
      g'2 |
      g'2 |
      g'2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
    }
    \new Staff \with {
      instrumentName = "Trumpet"
    } {
      \clef treble
      \key c \major
      \time 2/4
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2\fermata |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c''8 g'8 <g g'>8 <g g'>8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <g g'>4 r4\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <c' c''>4 r4 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r4 <b b c''>4 |
      g'4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c'2 |
      c'2~ |
      c'2~ |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <c' c''>4 r4 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
    }
    \new Staff \with {
      instrumentName = "Timpani"
    } {
      \clef bass
      \key c \major
      \time 2/4
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2\fermata |
      r2 |
      r2 |
      r2\fermata |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g,4\fermata r4\fermata |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      c4 r4 |
      c4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <g, c'>4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r4 c8 c8 |
      c2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c2~ |
      c4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
    }
    \new Staff \with {
      instrumentName = "Violin"
    } {
      \clef treble
      \key ees \major
      \time 2/4
      r8 g'8 g'8 g'8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r8 f'8 f'8 f'8 |
      d'2 |
      d'2\fermata |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c''2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      c''4 f''8 f''16 f''16 |
      d''2 |
      d''8 g''8 g''8 f''8 |
      ees''2 |
      d''8 g''8 g''8 f''8 |
      ees''2 |
      d''8 g''8 <f' g''>8 <f' f''>8 |
      << { <bes fis' c''>4 r4 } \\ { ees''4 r4 } >> |
      <aes' c''>4 <g d' bes' ees'' g''>4\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f'2\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      ees'8 g'8 c''8 c''8 |
      c''2 |
      bes'8 bes'8 bes'8 d''8 |
      d''2 |
      c''8 c''8 c''8 ees''8 |
      ees''8( d''8 d''8) f''8 |
      f''8 e''8 e''8 g''8 |
      g''8(\=2( f''8)\=2) f''8 bes''8 |
      bes''8(\=2( g''8)\=2) g''8 bes''8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d'''8 b''8 b''8 ees'''8 |
      d'''8 f'''8 f'''8 f'''8 |
      d'''8 g''8 g''8 g''8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      a8 g'''8 ees'''8 ees'''8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d''8 bes'8 g'8 f'8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c'8 ees'''8 ees'''8 ees'''8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      ges''8 ees''8 ees''8 ees''8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <a aes'>4 r4 |
      r2 |
      <aes f' bes' d''>4 r4 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d''4 ees''4 |
      f''4( c''4) |
      c''4 bes'4 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      bes'4 ees''4 |
      d''4 ees''4 |
      f''4 c''4 |
      c''4( bes'4) |
      bes'4( c''4) |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      bes'4( c''4) |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f''4 ees''4) |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      des''4 c''4) |
    }
    \new Staff \with {
      instrumentName = "Violin"
    } {
      \clef treble
      \key ees \major
      \time 2/4
      \once \override Rest.color = #red r2^\markup { "unread" } |
      ees'2\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d'2 |
      d'2\fermata |
      r8 g'8 g'8 g'8 |
      <ees' f'>2 |
      f'2~ |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      ees'8 g'8 g'8 g'8 |
      d'2 |
      d'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      aes'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g'8 d''8 d''8 g'8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <g c' bes'>4 cis''4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r8 d'8( d'8 d'8) |
      bes2 |
      bes2 |
      c'4 r4 |
      r8 d'8( d'8 d'8) |
      b2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c'8 g'8 g'8 ees'8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g'8 g'8 g'8 ees'8 |
      aes'8 aes'8 aes'8 f'8 |
      bes'8 bes'8 bes'8 g'8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      ees'8 ees'8 ees'8 aes8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      aes'8 aes'8 aes'8 f'8 |
      g'8 <ees' c''>8 <ees' c''>8 <ees' c''>8 |
      <ees' c'' aes''>2 |
      ees'2 |
      <ees' c'' aes''>2 |
      <d' bes'>8 f''8 d''8 d''8 |
      bes'8 g'8 f'8 f'8 |
      d'8 b8 g8 f'8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c''8 ees''8 ees''8 ees''8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      ges'8 ees'8 ees'8 ees'8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <a a'>4 r4 |
      r2 |
      <aes f' bes'>4 r4 |
      r2 |
      r2 |
      r2 |
      r2 |
      g'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      aes'2 |
      aes'2 |
      g'2 |
      aes'2 |
      aes'2 |
      g'2 |
      g'2 |
      g'2 |
      g'2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      aes'2 |
      <ees' bes'>2 |
      bes'2 |
      aes'2 |
    }
    \new Staff \with {
      instrumentName = "Viola"
    } {
      \clef alto
      \key ees \major
      \time 2/4
      d'8 g8 g8 g8 |
      ees2\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      d'8( aes'8 aes'8 aes'8) |
      aes'2 |
      g'2( |
      g'4) r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      ees'8 ees'8 ees'8 f'8 |
      g'2 |
      g'8 ees'8 ees'8 f'8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g2 |
      g4 r4 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g2 |
      g8 ees'8 ees'8 c'8 |
      d'2 |
      d'8 f'8 f'8 d'8 |
      ees'2 |
      ees'8 ees'8 ees'8 c'8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g'8 g'8 g'8 bes8 |
      aes'8 aes8 aes8 f8 |
      bes8 bes8 bes8 g8 |
      c'8 c'8 c'8 aes8 |
      f'8 f'8 f'8 d'8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <bes, d'>2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <d f ees'>2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      <bes, ees>8 ees8 <ees g>8 <ees g>8 |
      ees2 |
      <ees ges>2 |
      <ees f ees'>2 |
      <ees g>4 r4 |
      r2 |
      f4 r4 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      ees'2 |
      <f' f'>2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
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
      \once \override Rest.color = #red r2^\markup { "unread" } |
      ees'2 |
    }
    \new Staff \with {
      instrumentName = "Cello"
    } {
      \clef bass
      \key ees \major
      \time 2/4
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d,2\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d,2 |
      d,2\fermata |
      r2 |
      c'2 |
      d'2 |
      d'2( |
      c'2) |
      b2 |
      r4 bes4~ |
      bes2 |
      bes2 |
      c'2 |
      bes2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      b8 <bes, b>8 <bes, b>8 bes,8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g,4 r4\fermata |
      r8 aes,8 aes,8 aes,8 |
      f,2 |
      f,2\fermata |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r8 g,8( g,8 g,8) |
      c4 r4 |
      r2 |
      r2 |
      ees8 g,8 g,8 g,8 |
      c4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c4 r4 |
      c4 r4 |
      c4 r4 |
      c4 r4 |
      c4 r4 |
      c4 r4 |
      c4 r4 |
      c2~ |
      c2~ |
      c2~ |
      <c f'>8 c8 c8 c8 |
      g,2 |
      g,2 |
      g,2 |
      g,8 g,8 c8 c8 |
      <c aes>2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d4 r4 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r8 bes,8 bes,8 bes,8 |
      << { r4 c4 } \\ { ees4 r4 } >> |
      r2 |
      r2 |
      r8 bes,8 bes,8 bes,8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r8 bes,8 bes,8 bes,8 |
      ees4 r4 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f4 r4 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
    }
    \new Staff \with {
      instrumentName = "Contrabass"
    } {
      \clef bass
      \key ees \major
      \time 2/4
      r8 g8 g8 g8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      b8 <bes, b>8 <bes, b>8 bes,8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      g,4 r4 |
      r8 aes,8 aes,8 aes,8 |
      f,2 |
      f,2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r8 g,8 g,8 g,8 |
      c4 r4 |
      r2 |
      r2 |
      ees8 g,8 g,8 g,8 |
      c4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c4 r4 |
      c4 r4 |
      c4 r4 |
      c4 r4 |
      c4 r4 |
      c4 r4 |
      c4 r4 |
      c2 |
      c2 |
      c2 |
      <c f'>8 c8 c8 c8 |
      g,2 |
      g,2 |
      g,2 |
      g,8 g,8 c8 c8 |
      <c aes>2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      c4 r4 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      d4 r4 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r2 |
      r2 |
      r8 bes,8 bes,8 bes,8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r8 bes,8 bes,8 bes,8 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      r2 |
      r2 |
      r8 bes,8 bes,8 bes,8 |
      ees4 r4 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      f4 r4 |
      r2 |
      r2 |
      \once \override Rest.color = #red r2^\markup { "unread" } |
      \once \override Rest.color = #red r2^\markup { "unread" } |
    }
  >>
  \layout { }
}
