#(set-default-paper-size "a2")
#(set-global-staff-size 16)
\version "2.24.4"
% automatically converted by musicxml2ly from benchmarks/omr-corpus-widening-2026-09/fixtures/boulanger-printemps-mvt1.musicxml
\pointAndClickOff

\header {
  tagline = ##f
    title =  "D'un matin de printemps"
    copyright =  "Score: CC0 1.0 Universal; Annotations: CC-By-SA"
    composer =  "Lili Boulanger"
    encodingsoftware =  "music21 v.8.3.0"
    encodingdate =  "2026-09-01"
    }

#(set-global-staff-size 20.0)
\paper {
    
    }
\layout {
    \context { \Score
        skipBars = ##t
        autoBeaming = ##f
        }
    }
PartPOneVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key c \major \transposition c'' | % 1
    R2.*8 ^\markup{ \bold {Assez animé, léger, gai} } }

PartPTwoVoiceOne =  \relative e' {
    \clef "treble" \time 3/4 \key c \major | % 1
    R2.*2 | % 3
    \stemUp e4 ~ _\mp \stemUp e8. [ \stemUp g16 -. ] \stemUp e8 -. r16
    \stemUp d16 -. | % 4
    \stemUp e4 ~ \stemUp e8. [ \stemUp g16 -. ] \stemUp e8 -. r16
    \stemUp d16 -. | % 5
    \stemUp e4 ( ~ _\< \stemUp e16 [ \stemUp f16 \stemUp g16 \stemUp a16
    ] \stemDown b8 [ \stemDown c16 \stemDown d16 ] | % 6
    \stemDown e8 ) ( -. [ _\! _\> \stemDown d16 \stemDown c16 ]
    \stemDown b4. ) ( \stemUp a8 ) _\! | % 7
    \stemUp gis4. ( \stemUp b8 ) \stemUp ais8 ( -. [ \stemUp gis16
    \stemUp fis16 ) ] | % 8
    \stemUp gis4. ( \stemUp b8 ) \stemUp ais8 ( -. [ \stemUp gis16
    \stemUp fis16 ) ] }

PartPTwoVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata = ##t
    a\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 \skip1
    }

PartPThreeVoiceOne =  \relative e' {
    \clef "treble" \time 3/4 \key c \major | % 1
    R2.*2 | % 3
    \stemUp e4 ~ _\mp \stemUp e8. [ \stemUp g16 -. ] \stemUp e8 -. r16
    \stemUp d16 -. | % 4
    \stemUp e4 ~ \stemUp e8. [ \stemUp g16 -. ] \stemUp e8 -. r16
    \stemUp d16 -. | % 5
    \stemUp e4 ( ~ _\< \stemUp e16 [ \stemUp f16 \stemUp g16 \stemUp a16
    ] \stemDown b8 [ \stemDown c16 \stemDown d16 ] | % 6
    \stemDown e8 ) ( -. [ _\! _\> \stemDown d16 \stemDown c16 ]
    \stemDown b4. ) ( \stemUp a8 ) _\! | % 7
    \stemUp gis4. ( \stemUp b8 ) \stemUp ais8 ( -. [ \stemUp gis16
    \stemUp fis16 ) ] | % 8
    \stemUp gis4. ( \stemUp b8 ) \stemUp ais8 ( -. [ \stemUp gis16
    \stemUp fis16 ) ] }

PartPFourVoiceOne =  \relative b'' {
    \clef "treble" \time 3/4 \key c \major | % 1
    \stemDown b8 ^ "1." _\pp r8 r4 \stemDown a8 r8 | % 2
    \stemDown b8 r8 r4 \stemDown d8 r8 | % 3
    \stemDown b8 r8 r4 r4 | % 4
    R2. | % 5
    \stemDown b8 r8 r4 \stemDown d8 r8 | % 6
    \stemDown b8 r8 r4 \stemDown a8 r8 | % 7
    \stemDown gis8 r8 r4 r4 | % 8
    R2. }

PartPFourVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata = ##t
    x\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    }

PartPFiveVoiceOne =  \relative cis'' {
    \clef "treble" \time 3/4 \key c \major | % 1
    R2.*6 | % 7
    \once \override TextSpanner.style = #'trill \stemDown cis2.
    \startTextSpan ^\trill _\pp | % 8
    \stemDown cis2. \stopTextSpan }

PartPSixVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key g \major \transposition f | % 1
    R2.*8 }

PartPSevenVoiceOne =  \relative d'' {
    \clef "treble" \time 3/4 \key es \major \transposition a | % 1
    \stemDown d8 ^ "1." _\pp r8 r4 \stemDown c8 r8 | % 2
    \stemDown d8 r8 r4 \stemDown f8 r8 | % 3
    \stemDown d8 r8 r4 r4 | % 4
    R2. | % 5
    \stemDown d8 _\< r8 r4 \stemDown f8 r8 | % 6
    \stemDown d8 _\! _\p _\> r8 r4 \stemDown c8 r8 | % 7
    \stemDown b8 _\! r8 r4 r4 | % 8
    R2. }

PartPEightVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key es \major \transposition a | % 1
    R2.*8 }

PartPNineVoiceOne =  \relative c' {
    \clef "bass" \time 3/4 \key es \major \transposition a, | % 1
    R2.*8 }

PartPOneZeroVoiceOne =  \relative c' {
    \clef "bass" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPOneOneVoiceOne =  \relative c' {
    \clef "bass" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPOneTwoVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key d \major \transposition bes,, | % 1
    R2.*8 }

PartPOneThreeVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key c \major \transposition f | % 1
    R2.*8 }

PartPOneFourVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key g \major \transposition f | % 1
    R2.*8 }

PartPOneFiveVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key c \major \transposition f | % 1
    R2.*8 }

PartPOneSixVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key g \major \transposition f | % 1
    R2.*8 }

PartPOneSevenVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key c \major \transposition c' | % 1
    R2.*8 }

PartPOneEightVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key d \major \transposition bes | % 1
    R2.*8 }

PartPOneNineVoiceOne =  \relative c' {
    \clef "tenor" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPTwoZeroVoiceOne =  \relative c' {
    \clef "bass" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPTwoOneVoiceOne =  \relative c' {
    \clef "bass" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPTwoTwoVoiceOne =  \relative c' {
    \clef "bass" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPTwoThreeVoiceOne =  \relative c' {
    \clef "percussion" \time 3/4 \key c \major \stopStaff \override
    Staff.StaffSymbol.line-count = #1 \startStaff | % 1
    R2.*8 ^ "baguette d’éponges" }

PartPTwoFourVoiceOne =  \relative c' {
    \clef "percussion" \time 3/4 \key c \major \stopStaff \override
    Staff.StaffSymbol.line-count = #1 \startStaff | % 1
    R2.*8 ^ "petit tambourine et castagnettes" }

PartPTwoFiveVoiceOne =  \relative e' {
    \clef "percussion" \time 3/4 \key c \major \stopStaff \override
    Staff.StaffSymbol.line-count = #1 \startStaff | % 1
    \stemUp e4 _\p r4 \stemUp e4 | % 2
    \stemUp e4 r4 \stemUp e4 | % 3
    \stemUp e4 r4 r4 | % 4
    R2. | % 5
    r4 r4 \stemUp e4 | % 6
    \stemUp e4 r4 r4 | % 7
    \stemUp e4 r4 r4 | % 8
    \stemUp e4 r4 r4 }

PartPTwoSixVoiceOne =  \relative fis' {
    \clef "treble" \time 3/4 \key c \major \transposition c'' | % 1
    \stemUp fis4 -- _\p r4 \stemUp e4 -- _\pp | % 2
    \stemUp fis4 -- r4 \stemUp e4 -- | % 3
    \stemUp fis4 -- r4 r4 | % 4
    R2. | % 5
    \stemUp fis4 -- r4 \stemUp a4 -- | % 6
    \stemUp fis4 -- r4 \stemUp e4 -- | % 7
    \stemUp dis4 -- r4 \stemUp cis4 -- | % 8
    \stemUp dis4 -- r4 \stemUp cis4 -- }

PartPTwoSixVoiceTwo =  \relative c' {
    \clef "bass" \time 3/4 \key c \major \transposition c'' | % 1
    \stemDown c4 r4 \stemDown b4 | % 2
    \stemDown c4 r4 \stemDown b4 | % 3
    \stemDown c4 r4 r4 | % 4
    R2. | % 5
    \stemDown c4 r4 \stemDown e4 | % 6
    \stemDown c4 r4 \stemDown b4 | % 7
    \stemDown ais4 r4 \stemDown gis4 | % 8
    \stemDown ais4 r4 \stemDown gis4 }

PartPTwoSevenVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPTwoSevenVoiceTwo =  \relative c' {
    \clef "bass" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPTwoEightVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPTwoNineVoiceOne =  \relative e'' {
    \clef "treble" \time 3/4 \key c \major | % 1
    \stemDown <e b'>8 ( -. [ ^ "Div." _\p \stemDown <e b'>8 -. \stemDown
    <e b'>8 -. \stemDown <e b'>8 -. \stemDown <d a'>8 -. \stemDown <d
        a'>8 ) -. ] | % 2
    \stemDown <e b'>8 ( -. [ \stemDown <e b'>8 -. \stemDown <e b'>8 -.
    \stemDown <e b'>8 -. \stemDown <d a'>8 -. \stemDown <d a'>8 ) -. ] | % 3
    \stemDown <e b'>8 ( -. [ \stemDown <e b'>8 -. \stemDown <e b'>8 -.
    \stemDown <e b'>8 -. \stemDown <d a'>8 -. \stemDown <d a'>8 ) -. ] | % 4
    \stemDown <e b'>8 ( -. [ \stemDown <e b'>8 -. \stemDown <e b'>8 -.
    \stemDown <e b'>8 -. \stemDown <d a'>8 -. \stemDown <d a'>8 ) -. ] | % 5
    \stemDown <e b'>8 ( -. [ \stemDown <e b'>8 -. \stemDown <e b'>8 -.
    \stemDown <e b'>8 -. \stemDown <g d'>8 -. \stemDown <g d'>8 ) -. ] | % 6
    \stemDown <e b'>8 ( -. [ \stemDown <e b'>8 -. \stemDown <e b'>8 -.
    \stemDown <e b'>8 -. \stemDown <d a'>8 -. \stemDown <d a'>8 ) -. ] | % 7
    \stemDown <cis gis'>8 ( -. [ _\pp \stemDown <cis gis'>8 -. \stemDown
    <cis gis'>8 -. \stemDown <cis gis'>8 -. \stemDown <b fis'>8 -.
    \stemDown <b fis'>8 ) -. ] | % 8
    \stemDown <cis gis'>8 ( -. [ \stemDown <cis gis'>8 -. \stemDown <cis
        gis'>8 -. \stemDown <cis gis'>8 -. \stemDown <b fis'>8 -.
    \stemDown <b fis'>8 ) -. ] }

PartPThreeZeroVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPThreeOneVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPThreeTwoVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPThreeThreeVoiceOne =  \relative b' {
    \clef "treble" \time 3/4 \key c \major | % 1
    \stemDown <b a'>8 ( -. [ ^ "Div." _\p \stemDown <b a'>8 -. \stemDown
    <b a'>8 -. \stemDown <b a'>8 -. \stemDown <a g'>8 -. \stemDown <a
        g'>8 ) -. ] | % 2
    \stemDown <b a'>8 ( -. [ \stemDown <b a'>8 -. \stemDown <b a'>8 -.
    \stemDown <b a'>8 -. \stemDown <a g'>8 -. \stemDown <a g'>8 ) -. ] | % 3
    \stemDown <b a'>8 ( -. [ \stemDown <b a'>8 -. \stemDown <b a'>8 -.
    \stemDown <b a'>8 -. \stemDown <a g'>8 -. \stemDown <a g'>8 ) -. ] | % 4
    \stemDown <b a'>8 ( -. [ \stemDown <b a'>8 -. \stemDown <b a'>8 -.
    \stemDown <b a'>8 -. \stemDown <a g'>8 -. \stemDown <a g'>8 ) -. ] | % 5
    \stemDown <d a'>8 ( -. [ \stemDown <d a'>8 -. ] \stemDown <d a'>8 -.
    [ \stemDown <d a'>8 -. \stemDown <d c'>8 -. \stemDown <d c'>8 ) -. ]
    | % 6
    \stemDown <b a'>8 ( -. [ \stemDown <b a'>8 -. \stemDown <b a'>8 -.
    \stemDown <b a'>8 -. \stemDown <a g'>8 -. \stemDown <a g'>8 ) -. ] | % 7
    \stemDown <gis dis'>8 ( ^. [ _\pp \stemDown <gis dis'>8 ^. \stemDown
    <gis dis'>8 ^. \stemDown <gis dis'>8 ^. \stemDown <fis cis'>8 ^.
    \stemDown <fis cis'>8 ) ^. ] | % 8
    \stemDown <gis dis'>8 ( ^. [ \stemDown <gis dis'>8 ^. \stemDown <gis
        dis'>8 ^. \stemDown <gis dis'>8 ^. \stemDown <fis cis'>8 ^.
    \stemDown <fis cis'>8 ) ^. ] }

PartPThreeFourVoiceOne =  \relative c' {
    \clef "treble" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPThreeFiveVoiceOne =  \relative c' {
    \clef "alto" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPThreeSixVoiceOne =  \relative c'' {
    \clef "treble" \time 3/4 \key c \major | % 1
    \stemDown <c fis>8 ( -. [ ^ "Div." _\p \stemDown <c fis>8 -.
    \stemDown <c fis>8 -. \stemDown <c fis>8 -. \stemDown <b e>8 -.
    \stemDown <b e>8 ) -. ] | % 2
    \stemDown <c fis>8 ( -. [ \stemDown <c fis>8 -. \stemDown <c fis>8
    -. \stemDown <c fis>8 -. \stemDown <b e>8 -. \stemDown <b e>8 ) -. ]
    | % 3
    \stemDown <c fis>8 ( -. [ \stemDown <c fis>8 -. \stemDown <c fis>8
    -. \stemDown <c fis>8 -. \stemDown <b e>8 -. \stemDown <b e>8 ) -. ]
    | % 4
    \stemDown <c fis>8 ( -. [ \stemDown <c fis>8 -. \stemDown <c fis>8
    -. \stemDown <c fis>8 -. \stemDown <b e>8 -. \stemDown <b e>8 ) -. ]
    | % 5
    \stemDown <c fis>8 ( -. [ \stemDown <c fis>8 -. \stemDown <c fis>8
    -. \stemDown <c fis>8 -. \stemDown <e a>8 -. \stemDown <e a>8 ) -. ]
    | % 6
    \stemDown <c fis>8 ( -. [ \stemDown <c fis>8 -. \stemDown <c fis>8
    -. \stemDown <c fis>8 -. \stemDown <b e>8 -. \stemDown <b e>8 ) -. ]
    | % 7
    \stemDown <b eis>8 ( -. [ _\pp \stemDown <b eis>8 -. \stemDown <b
        eis>8 -. \stemDown <b eis>8 -. \stemDown <ais dis>8 -. \stemDown
    <ais dis>8 ) -. ] | % 8
    \stemDown <b eis>8 ( -. [ \stemDown <b eis>8 -. \stemDown <b eis>8
    -. \stemDown <b eis>8 -. \stemDown <ais dis>8 -. \stemDown <ais dis>8
    ) -. ] }

PartPThreeSixVoiceTwo =  \relative c' {
    \clef "alto" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPThreeSevenVoiceOne =  \relative c' {
    \clef "bass" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPThreeEightVoiceOne =  \relative e' {
    \clef "bass" \time 3/4 \key c \major | % 1
    \stemDown e4 ^ "pizz." _\p r4 r4 | % 2
    R2.*7 }

PartPThreeNineVoiceOne =  \relative c' {
    \clef "bass" \time 3/4 \key c \major | % 1
    R2.*8 }

PartPFourZeroVoiceOne =  \relative c' {
    \clef "bass" \time 3/4 \key c \major \transposition c | % 1
    R2.*8 }

PartPFourOneVoiceOne =  \relative e' {
    \clef "treble" \time 3/4 \key c \major \stopStaff \override
    Staff.StaffSymbol.line-count = #5 \startStaff | % 1
    R2.*2 | % 3
    e4*7/4 ( -\markup{ \small\italic {gai, léger} } _\pp g16 ) \stemUp e8*3/2
    [ \stemUp d16 ] | % 4
    e4*7/4 ( g16 ) \stemUp e8*3/2 [ \stemUp d16 ] | % 5
    e4 ( ~ \stemUp e16 [ \stemUp f16 \stemUp g16 \stemUp a16 ] \stemDown
    b8 [ \stemDown c16 \stemDown d16 ) ] | % 6
    \stemDown e8 [ \stemDown d16 \stemDown c16 ] b4*3/2 ( a8 ) | % 7
    gis4*3/2 ( b8 ) \stemUp ais8 [ \stemUp gis16 \stemUp fis16 ] | % 8
    gis4*3/2 ( b8 ) \stemUp ais8 [ \stemUp gis16 \stemUp fis16 ] }

PartPFourTwoVoiceOne =  \relative e'' {
    \clef "treble" \time 3/4 \key c \major \stopStaff \override
    Staff.StaffSymbol.line-count = #5 \startStaff | % 1
    \stemDown <e f a b>8 -. [ _\pp \stemDown <e f a b>8 -. ] \stemDown
    <e f a b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <d e g a>8 -. [
    \stemDown <d e g a>8 -. ] | % 2
    \stemDown <e f a b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <e f a
        b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <d e g a>8 -. [
    \stemDown <d e g a>8 -. ] | % 3
    \stemDown <e f a b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <e f a
        b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <d e g a>8 -. [
    \stemDown <d e g a>8 -. ] | % 4
    \stemDown <e f a b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <e f a
        b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <d e g a>8 -. [
    \stemDown <d e g a>8 -. ] | % 5
    \stemDown <e f a b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <e f a
        b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <g a c d>8 -. [
    \stemDown <g a c d>8 -. ] | % 6
    \stemDown <e f a b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <e f a
        b>8 -. [ \stemDown <e f a b>8 -. ] \stemDown <d e g a>8 -. [
    \stemDown <d e g a>8 -. ] | % 7
    \stemDown <cis dis eis gis>8 -. [ \stemDown <cis dis eis gis>8 -. ]
    \stemDown <cis dis eis gis>8 -. [ \stemDown <cis dis eis gis>8 -. ]
    \stemDown <b cis dis fis>8 -. [ \stemDown <b cis dis fis>8 -. ] | % 8
    \stemDown <cis dis eis gis>8 -. [ \stemDown <cis dis eis gis>8 -. ]
    \stemDown <cis dis eis gis>8 -. [ \stemDown <cis dis eis gis>8 -. ]
    \stemDown <b cis dis fis>8 -. [ \stemDown <b cis dis fis>8 -. ] }

PartPFourTwoVoiceTwo =  \relative b' {
    \clef "treble" \time 3/4 \key c \major \stopStaff \override
    Staff.StaffSymbol.line-count = #5 \startStaff | % 1
    \stemDown <b c>8 -. [ \stemDown <b c>8 -. ] \stemDown <b c>8 -. [
    \stemDown <b c>8 -. ] \stemUp <a b>8 -. [ \stemUp <a b>8 -. ] | % 2
    \stemDown <b c>8 -. [ \stemDown <b c>8 -. ] \stemDown <b c>8 -. [
    \stemDown <b c>8 -. ] \stemUp <a b>8 -. [ \stemUp <a b>8 -. ] | % 3
    \stemDown <b c>8 -. [ \stemDown <b c>8 -. ] \stemDown <b c>8 -. [
    \stemDown <b c>8 -. ] \stemUp <a b>8 -. [ \stemUp <a b>8 -. ] | % 4
    \stemDown <b c>8 -. [ \stemDown <b c>8 -. ] \stemDown <b c>8 -. [
    \stemDown <b c>8 -. ] \stemUp <a b>8 -. [ \stemUp <a b>8 -. ] | % 5
    \stemDown <b c>8 -. [ \stemDown <b c>8 -. ] \stemDown <b c>8 -. [
    \stemDown <b c>8 -. ] \stemDown <d e>8 -. [ \stemDown <d e>8 -. ] | % 6
    \stemDown <b c>8 -. [ \stemDown <b c>8 -. ] \stemDown <b c>8 -. [
    \stemDown <b c>8 -. ] \stemUp <a b>8 -. [ \stemUp <a b>8 -. ] | % 7
    \stemUp <gis b>8 -. [ \stemUp <gis b>8 -. ] \stemUp <gis b>8 -. [
    \stemUp <gis b>8 -. ] \stemUp <fis ais>8 -. [ \stemUp <fis ais>8 -.
    ] | % 8
    \stemUp <gis b>8 -. [ \stemUp <gis b>8 -. ] \stemUp <gis b>8 -. [
    \stemUp <gis b>8 -. ] \stemUp <fis ais>8 -. [ \stemUp <fis ais>8 -.
    ] }


% The score definition
\score {
    <<
        
        \new Staff
        <<
            \set Staff.instrumentName = "Piccolo"
            \set Staff.shortInstrumentName = "Picc"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneVoiceOne" {  \PartPOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Flute 1"
            \set Staff.shortInstrumentName = "Fl 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoVoiceOne" {  \PartPTwoVoiceOne }
                \new Lyrics \lyricsto "PartPTwoVoiceOne" { \set stanza = "1." \PartPTwoVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Flute 2"
            \set Staff.shortInstrumentName = "Fl 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeVoiceOne" {  \PartPThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Oboe 1"
            \set Staff.shortInstrumentName = "Ob 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFourVoiceOne" {  \PartPFourVoiceOne }
                \new Lyrics \lyricsto "PartPFourVoiceOne" { \set stanza = "1." \PartPFourVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Oboe 2"
            \set Staff.shortInstrumentName = "Ob 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFiveVoiceOne" {  \PartPFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "English Horn"
            \set Staff.shortInstrumentName = "E Hn"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSixVoiceOne" {  \PartPSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "A Clarinet 1"
            \set Staff.shortInstrumentName = "Cl 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSevenVoiceOne" {  \PartPSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "A Clarinet 2"
            \set Staff.shortInstrumentName = "Cl 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPEightVoiceOne" {  \PartPEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "A Bass Clarinet"
            \set Staff.shortInstrumentName = "B Cl"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPNineVoiceOne" {  \PartPNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bassoon 1"
            \set Staff.shortInstrumentName = "Bsn 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneZeroVoiceOne" {  \PartPOneZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bassoon 2"
            \set Staff.shortInstrumentName = "Bsn 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneOneVoiceOne" {  \PartPOneOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bass Sarrusophone"
            \set Staff.shortInstrumentName = "B Sar"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneTwoVoiceOne" {  \PartPOneTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "F Horn 1"
            \set Staff.shortInstrumentName = "F Hn 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneThreeVoiceOne" {  \PartPOneThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "F Horn 2"
            \set Staff.shortInstrumentName = "F Hn 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFourVoiceOne" {  \PartPOneFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "F Horn 3"
            \set Staff.shortInstrumentName = "F Hn 3"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFiveVoiceOne" {  \PartPOneFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "F Horn 4"
            \set Staff.shortInstrumentName = "F Hn 4"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSixVoiceOne" {  \PartPOneSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Trumpet 1"
            \set Staff.shortInstrumentName = "C Tpt 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSevenVoiceOne" {  \PartPOneSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Trumpet 2"
            \set Staff.shortInstrumentName = "C Tpt 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneEightVoiceOne" {  \PartPOneEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Trombone 1"
            \set Staff.shortInstrumentName = "Tbn 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneNineVoiceOne" {  \PartPOneNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Trombone 2"
            \set Staff.shortInstrumentName = "Tbn 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoZeroVoiceOne" {  \PartPTwoZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Trombone 3"
            \set Staff.shortInstrumentName = "Tbn 3"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoOneVoiceOne" {  \PartPTwoOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Tuba"
            \set Staff.shortInstrumentName = "Tba"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoTwoVoiceOne" {  \PartPTwoTwoVoiceOne }
                >>
            >>
        \new RhythmicStaff
        <<
            \set RhythmicStaff.instrumentName = "Cymbal"
            \set RhythmicStaff.shortInstrumentName = "Cym"
            
            \context RhythmicStaff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoThreeVoiceOne" {  \PartPTwoThreeVoiceOne }
                >>
            >>
        \new RhythmicStaff
        <<
            \set RhythmicStaff.instrumentName = "Tambourine"
            \set RhythmicStaff.shortInstrumentName = "Tamb"
            
            \context RhythmicStaff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoFourVoiceOne" {  \PartPTwoFourVoiceOne }
                >>
            >>
        \new RhythmicStaff
        <<
            \set RhythmicStaff.instrumentName = "Triangle"
            \set RhythmicStaff.shortInstrumentName = "Tri"
            
            \context RhythmicStaff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoFiveVoiceOne" {  \PartPTwoFiveVoiceOne }
                >>
            >>
        \new PianoStaff
        <<
            \set PianoStaff.instrumentName = "Celesta"
            \set PianoStaff.shortInstrumentName = "Cel"
            
            \context Staff = "1" << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoSixVoiceOne" {  \PartPTwoSixVoiceOne }
                >> \context Staff = "2" <<
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoSixVoiceTwo" {  \PartPTwoSixVoiceTwo }
                >>
            >>
        \new PianoStaff
        <<
            \set PianoStaff.instrumentName = "Harp"
            \set PianoStaff.shortInstrumentName = "Hrp"
            
            \context Staff = "1" << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoSevenVoiceOne" {  \PartPTwoSevenVoiceOne }
                >> \context Staff = "2" <<
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoSevenVoiceTwo" {  \PartPTwoSevenVoiceTwo }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin"
            \set Staff.shortInstrumentName = "Vln Solo."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoEightVoiceOne" {  \PartPTwoEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 1"
            \set Staff.shortInstrumentName = "Vln 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoNineVoiceOne" {  \PartPTwoNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 1 div(2)"
            \set Staff.shortInstrumentName = "Vln. 1 div(2)"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeZeroVoiceOne" {  \PartPThreeZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 1 div(3)"
            \set Staff.shortInstrumentName = "Vln. 1 div(3)"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeOneVoiceOne" {  \PartPThreeOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin"
            \set Staff.shortInstrumentName = "Vln. 2 Solo"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeTwoVoiceOne" {  \PartPThreeTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 2"
            \set Staff.shortInstrumentName = "Vln 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeThreeVoiceOne" {  \PartPThreeThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violins"
            \set Staff.shortInstrumentName = "Vln 2 div."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeFourVoiceOne" {  \PartPThreeFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Viola"
            \set Staff.shortInstrumentName = "Vla."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeFiveVoiceOne" {  \PartPThreeFiveVoiceOne }
                >>
            >>
        \new PianoStaff
        <<
            \set PianoStaff.instrumentName = "Viola"
            \set PianoStaff.shortInstrumentName = "Vla"
            
            \context Staff = "1" << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeSixVoiceOne" {  \PartPThreeSixVoiceOne }
                >> \context Staff = "2" <<
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeSixVoiceTwo" {  \PartPThreeSixVoiceTwo }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello"
            \set Staff.shortInstrumentName = "Vc. Solo"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeSevenVoiceOne" {  \PartPThreeSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello"
            \set Staff.shortInstrumentName = "Vc"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeEightVoiceOne" {  \PartPThreeEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello"
            \set Staff.shortInstrumentName = "Vcs div 2."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeNineVoiceOne" {  \PartPThreeNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Contrabass"
            \set Staff.shortInstrumentName = "Cb"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFourZeroVoiceOne" {  \PartPFourZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin"
            \set Staff.shortInstrumentName = "Vln."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFourOneVoiceOne" {  \PartPFourOneVoiceOne }
                >>
            >>
        \new PianoStaff
        <<
            \set PianoStaff.instrumentName = "Piano"
            \set PianoStaff.shortInstrumentName = "Pno."
            
            \context Staff = "1" << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFourTwoVoiceOne" {  \PartPFourTwoVoiceOne }
                >> \context Staff = "2" <<
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFourTwoVoiceTwo" {  \PartPFourTwoVoiceTwo }
                >>
            >>
        
        >>
    \layout {}
    % To create MIDI output, uncomment the following line:
    %  \midi {\tempo 4 = 100 }
    }

