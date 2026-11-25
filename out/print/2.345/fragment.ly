\version "2.24.0"
guessedColor = #(rgb-color 0.12 0.44 0.92)
\paper { indent=0 paper-width=190\mm paper-height=40\mm tagline=##f }
\score { \new Staff { \clef treble \time 4/4 f'2^\markup { \with-color #red "tie to unread note" } f'2^\markup { \with-color #red "tie from unread note" } | f'1^\markup { \with-color #red "unread note" } | f'2^\markup { \with-color #red "slur to unread note" } f'2^\markup { \with-color #red "arc: tie or slur unread" } | } \layout { } }
