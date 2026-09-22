\version "2.24.4"
% automatically converted by musicxml2ly from src.musicxml
\pointAndClickOff

\header {
    title =  "Symphony No.5"
    movementnumber =  "1"
    subtitle =  "Allegro con brio"
    copyright =  "Score: CC0 1.0 Universal; Annotations: CC-By-SA"
    composer =  "Beethoven, Ludwig van"
    encodingsoftware =  "music21 v.8.3.0"
    encodingdate =  "2026-09-22"
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
PartPOneVoiceOne =  \relative g''' {
    \clef "treble" \time 2/4 \key es \major | % 1
    \tempo "" 2=108 R2*13 \pageBreak ^\markup{ \bold {Allegro con brio}
        } | % 14
    R2*4 | % 18
    r8 \stemDown g8 [ _\markup{ \small\italic {cresc.} } _\p \stemDown g8
    \stemDown f8 ] | % 19
    \stemDown es4 _\f r4 | \barNumberCheck #20
    \stemDown c4 r4 | % 21
    \stemDown g'4 r4 ^\fermata | % 22
    r8 \stemDown as,8 [ _\ff \stemDown as8 \stemDown as8 ] | % 23
    \stemDown f2 ~ | % 24
    \stemDown f2 ^\fermata }

PartPTwoVoiceOne =  \relative d''' {
    \clef "treble" \time 2/4 \key es \major | % 1
    R2*13 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemDown d8 [ _\markup{ \small\italic {cresc.} } _\p \stemDown d8
    \stemDown d8 ] | % 19
    \stemDown c4 _\f r4 | \barNumberCheck #20
    \stemDown c4 r4 | % 21
    \stemDown b4 r4 ^\fermata | % 22
    r8 \stemDown as8 [ _\ff \stemDown as8 \stemDown as8 ] | % 23
    \stemDown f2 ~ | % 24
    \stemDown f2 ^\fermata }

PartPThreeVoiceOne =  \relative g'' {
    \clef "treble" \time 2/4 \key es \major | % 1
    R2*13 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemDown g8 [ _\markup{ \small\italic {cresc.} } _\p \stemDown g8
    \stemDown f8 ] | % 19
    \stemDown es4 r4 | \barNumberCheck #20
    \stemDown fis4 r4 | % 21
    \stemDown g4 r4 ^\fermata | % 22
    r8 \stemDown as8 [ _\ff \stemDown as8 \stemDown as8 ] | % 23
    \stemDown f2 ~ | % 24
    \stemDown f2 ^\fermata }

PartPFourVoiceOne =  \relative d'' {
    \clef "treble" \time 2/4 \key es \major | % 1
    R2*13 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemDown d8 [ _\markup{ \small\italic {cresc.} } _\p \stemDown d8
    \stemDown d8 ] | % 19
    \stemDown c4 r4 | \barNumberCheck #20
    \stemDown c4 r4 | % 21
    \stemDown b4 r4 ^\fermata | % 22
    r8 \stemDown as'8 [ _\ff \stemDown as8 \stemDown as8 ] | % 23
    \stemDown f2 ~ | % 24
    \stemDown f2 ^\fermata }

PartPFiveVoiceOne =  \relative a' {
    \clef "treble" \time 2/4 \key f \major \transposition bes | % 1
    r8 \stemUp a8 [ _\ff \stemUp a8 \stemUp a8 ] | % 2
    \stemUp f2 ^\fermata | % 3
    r8 \stemUp g8 [ \stemUp g8 \stemUp g8 ] | % 4
    \stemUp e2 ~ | % 5
    \stemUp e2 ^\fermata | % 6
    R2*8 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemUp cis8 [ _\markup{ \small\italic {cresc.} } _\p \stemUp e8
    \stemUp a8 ] | % 19
    \stemUp a4 _\f r4 | \barNumberCheck #20
    \stemUp gis4 r4 | % 21
    \stemUp e4 r4 ^\fermata | % 22
    r8 \stemDown bes'8 [ _\ff \stemDown bes8 \stemDown bes8 ] | % 23
    \stemUp g2 ~ | % 24
    \stemUp g2 ^\fermata }

PartPSixVoiceOne =  \relative a' {
    \clef "treble" \time 2/4 \key f \major \transposition bes | % 1
    r8 \stemUp a8 [ _\ff \stemUp a8 \stemUp a8 ] | % 2
    \stemUp f2 ^\fermata | % 3
    r8 \stemUp g8 [ \stemUp g8 \stemUp g8 ] | % 4
    \stemUp e2 ~ | % 5
    \stemUp e2 ^\fermata | % 6
    R2*8 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemUp a,8 [ _\markup{ \small\italic {cresc.} } _\p \stemUp cis8
    \stemUp e8 ] | % 19
    \stemUp f4 _\f r4 | \barNumberCheck #20
    \stemUp d4 r4 | % 21
    \stemUp cis4 r4 ^\fermata | % 22
    r8 \stemDown bes'8 [ _\ff \stemDown bes8 \stemDown bes8 ] | % 23
    \stemUp g2 ~ | % 24
    \stemUp g2 ^\fermata }

PartPSevenVoiceOne =  \relative c' {
    \clef "bass" \time 2/4 \key es \major | % 1
    R2*6 | % 7
    \stemDown c2 ~ _\p | % 8
    \stemDown c2 ~ | % 9
    \stemDown c2 ~ | \barNumberCheck #10
    \stemDown c2 | % 11
    \stemDown b2 ~ | % 12
    \stemDown b2 ~ | % 13
    \stemDown b2 ~ \pageBreak | % 14
    \stemDown b2 | % 15
    \stemDown c2 | % 16
    \stemDown b2 | % 17
    \stemDown c2 | % 18
    \stemDown b8 [ \stemDown b8 _\markup{ \small\italic {cresc.} }
    \stemDown b8 \stemDown b8 ] | % 19
    \stemDown c4 _\f r4 | \barNumberCheck #20
    \stemUp as,4 r4 | % 21
    \stemUp g4 r4 ^\fermata | % 22
    r8 \stemUp as8 [ _\ff \stemUp as8 \stemUp as8 ] | % 23
    \stemUp f2 ~ | % 24
    \stemUp f2 ^\fermata }

PartPEightVoiceOne =  \relative c' {
    \clef "bass" \time 2/4 \key es \major | % 1
    R2*6 | % 7
    \stemDown c2 ~ _\p | % 8
    \stemDown c2 ~ | % 9
    \stemDown c2 ~ | \barNumberCheck #10
    \stemDown c2 | % 11
    \stemDown b2 ~ | % 12
    \stemDown b2 ~ | % 13
    \stemDown b2 ~ \pageBreak | % 14
    \stemDown b2 | % 15
    \stemDown c2 | % 16
    \stemDown b2 | % 17
    \stemDown c2 | % 18
    \stemDown b8 [ \stemDown b8 _\markup{ \small\italic {cresc.} }
    \stemDown b8 \stemDown b8 ] | % 19
    \stemDown c4 _\f r4 | \barNumberCheck #20
    \stemUp as,4 r4 | % 21
    \stemUp g4 r4 | % 22
    r8 \stemUp as8 [ _\ff \stemUp as8 \stemUp as8 ] | % 23
    \stemUp f2 ~ | % 24
    \stemUp f2 ^\fermata }

PartPNineVoiceOne =  \relative e'' {
    \clef "treble" \time 2/4 \key c \major \transposition es | % 1
    R2*13 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemDown e8 [ _\markup{ \small\italic {cresc.} } _\p \stemDown e8
    \stemDown e8 ] | % 19
    \stemDown e4 _\f r4 | \barNumberCheck #20
    \stemDown c4 r4 | % 21
    \stemDown e4 r4 ^\fermata | % 22
    r8 \stemDown f8 [ _\ff \stemDown f8 \stemDown f8 ] | % 23
    \stemDown d2 ~ | % 24
    \stemDown d2 ^\fermata }

PartPOneZeroVoiceOne =  \relative e'' {
    \clef "treble" \time 2/4 \key c \major \transposition es | % 1
    R2*13 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemDown e8 [ _\markup{ \small\italic {cresc.} } _\p \stemDown e8
    \stemDown e8 ] | % 19
    \stemDown e4 _\f r4 | \barNumberCheck #20
    \stemUp c,4 r4 | % 21
    \stemUp e4 r4 ^\fermata | % 22
    r8 \stemDown f'8 [ _\ff \stemDown f8 \stemDown f8 ] | % 23
    \stemDown d2 ~ | % 24
    \stemDown d2 ^\fermata }

PartPOneOneVoiceOne =  \relative g' {
    \clef "treble" \time 2/4 \key es \major \transposition c' | % 1
    R2*13 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemUp g8 [ _\markup{ \small\italic {cresc.} } _\p \stemUp g8
    \stemUp g8 ] | % 19
    \stemDown c4 _\f r4 | \barNumberCheck #20
    \stemDown c4 r4 | % 21
    \stemUp g4 r4 ^\fermata | % 22
    R2*3 }

PartPOneTwoVoiceOne =  \relative g {
    \clef "treble" \time 2/4 \key es \major \transposition c' | % 1
    R2*13 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemUp g8 [ _\markup{ \small\italic {cresc.} } _\p \stemUp g8
    \stemUp g8 ] | % 19
    \stemUp c4 _\f r4 | \barNumberCheck #20
    \stemUp c4 r4 | % 21
    \stemUp g4 r4 ^\fermata | % 22
    R2*3 }

PartPOneThreeVoiceOne =  \relative g, {
    \clef "bass" \time 2/4 \key es \major | % 1
    R2*13 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemUp g8 [ _\markup{ \small\italic {cresc.} } _\p \stemUp g8
    \stemUp g8 ] | % 19
    \stemUp c4 _\f r4 | \barNumberCheck #20
    \stemUp c4 r4 | % 21
    \stemUp g4 r4 ^\fermata | % 22
    R2*3 }

PartPOneFourVoiceOne =  \relative g' {
    \clef "treble" \time 2/4 \key es \major | % 1
    r8 \stemUp g8 [ _\ff \stemUp g8 \stemUp g8 ] | % 2
    \stemUp es2 ^\fermata | % 3
    r8 \stemUp f8 [ \stemUp f8 \stemUp f8 ] | % 4
    \stemUp d2 ~ | % 5
    \stemUp d2 ^\fermata | % 6
    R2*2 | % 8
    r8 \stemDown es'8 [ _\p \stemDown es8 \stemDown es8 ] | % 9
    \stemDown c2 ~ | \barNumberCheck #10
    \stemDown c4 r4 | % 11
    R2 | % 12
    r8 \stemDown f8 [ \stemDown f8 \stemDown f8 ] | % 13
    \stemDown d2 ~ \pageBreak | % 14
    \stemDown d8 [ \stemDown g8 \stemDown g8 \stemDown f8 ] | % 15
    \stemDown es2 ( | % 16
    \stemDown d8 ) [ \stemDown g8 \stemDown g8 \stemDown f8 ] | % 17
    \stemDown es2 ( | % 18
    \stemDown d8 ) [ _\markup{ \small\italic {cresc.} } \stemDown g8
    \stemDown g8 \stemDown f8 ] | % 19
    \stemDown es4 _\f r4 | \barNumberCheck #20
    \stemUp <as,, fis' c'>4 r4 | % 21
    \stemDown g''2 ^\fermata | % 22
    r8 \stemUp as,8 [ _\ff \stemUp as8 \stemUp as8 ] | % 23
    \stemUp f2 ~ | % 24
    \stemUp f2 ^\fermata }

PartPOneFourVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata = ##t
    a\skip1 \skip1 \skip1 a\skip1 \skip1 \skip1 \skip1 a\skip1 \skip1
    \skip1 \skip1 a\skip1 \skip1 \skip1 \skip1 a\skip1 \skip1 \skip1
    \skip1 a\skip1 \skip1 \skip1 \skip1 a\skip1 \skip1 \skip1 \skip1
    \skip1 a\skip1 \skip1 \skip1 \skip1
    }

PartPOneFiveVoiceOne =  \relative g' {
    \clef "treble" \time 2/4 \key es \major | % 1
    r8 \stemUp g8 [ _\ff \stemUp g8 \stemUp g8 ] | % 2
    \stemUp es2 ^\fermata | % 3
    r8 \stemUp f8 [ \stemUp f8 \stemUp f8 ] | % 4
    \stemUp d2 ~ | % 5
    \stemUp d2 ^\fermata | % 6
    r8 \stemUp g8 [ _\p \stemUp g8 \stemUp g8 ] | % 7
    \stemUp es2 ~ | % 8
    \stemUp es2 ~ | % 9
    \stemUp es2 ~ | \barNumberCheck #10
    \stemUp es8 [ \stemUp g8 \stemUp g8 \stemUp g8 ] | % 11
    \stemUp d2 ~ | % 12
    \stemUp d2 | % 13
    \stemUp g2 ~ \pageBreak | % 14
    \stemUp g2 ~ | % 15
    \stemUp g8 [ \stemUp es8 \stemUp es8 \stemUp f8 ] | % 16
    \stemUp g2 ~ | % 17
    \stemUp g8 [ \stemUp es8 \stemUp es8 \stemUp f8 ] | % 18
    \stemDown g8 [ _\markup{ \small\italic {cresc.} } \stemDown d'8
    \stemDown d8 \stemDown g,8 ] | % 19
    \stemUp <c, g' es'>4 _\f r4 | \barNumberCheck #20
    \stemUp <as fis' c'>4 r4 | % 21
    \stemUp <g d' b'>4 r4 ^\fermata | % 22
    r8 \stemUp as'8 [ _\ff \stemUp as8 \stemUp as8 ] | % 23
    \stemUp f2 ~ | % 24
    \stemUp f2 ^\fermata }

PartPOneFiveVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata =
    ##t\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    a\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 a\skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 a\skip1 \skip1 \skip1 \skip1 a\skip1
    \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1
    }

PartPOneSixVoiceOne =  \relative g {
    \clef "alto" \time 2/4 \key es \major | % 1
    r8 \stemUp g8 [ _\ff \stemUp g8 \stemUp g8 ] | % 2
    \stemUp es2 ^\fermata | % 3
    r8 \stemUp f8 \stemUp f8 [ \stemUp f8 ] | % 4
    \stemUp d2 ~ | % 5
    \stemUp d2 ^\fermata | % 6
    R2 | % 7
    r8 \stemDown as''8 [ _\p \stemDown as8 \stemDown as8 ] | % 8
    \stemDown g2 ~ | % 9
    \stemDown g2 ~ | \barNumberCheck #10
    \stemDown g4 r4 | % 11
    r8 \stemDown as8 [ \stemDown as8 \stemDown as8 ] | % 12
    \stemDown g2 | % 13
    \stemDown d2 ~ \pageBreak | % 14
    \stemDown d2 | % 15
    \stemDown es8 [ \stemDown es8 \stemDown es8 \stemDown f8 ] | % 16
    \stemDown g2 ~ | % 17
    \stemDown g8 [ \stemDown es8 \stemDown es8 \stemDown f8 ] | % 18
    \stemDown g4. _\markup{ \small\italic {cresc.} } \stemDown d8 | % 19
    \stemDown es4 _\f r4 | \barNumberCheck #20
    \stemUp as,4 r4 | % 21
    \stemUp g4 r4 ^\fermata | % 22
    r8 \stemUp as8 [ _\ff \stemUp as8 \stemUp as8 ] | % 23
    \stemUp f2 ~ | % 24
    \stemUp f2 ^\fermata }

PartPOneSixVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata =
    ##t\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    a\skip1 \skip1 \skip1 \skip1 \skip1 a\skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1
    }

PartPOneSevenVoiceOne =  \relative g, {
    \clef "bass" \time 2/4 \key es \major | % 1
    r8 \stemUp g8 [ _\ff \stemUp g8 \stemUp g8 ] | % 2
    \stemUp es2 ^\fermata | % 3
    r8 \stemUp f8 \stemUp f8 [ \stemUp f8 ] | % 4
    \stemUp d2 ~ | % 5
    \stemUp d2 ^\fermata | % 6
    R2 | % 7
    \stemDown c''2 ~ _\p | % 8
    \stemDown c2 ~ | % 9
    \stemDown c2 ~ | \barNumberCheck #10
    \stemDown c2 | % 11
    \stemDown b2 ~ | % 12
    \stemDown b2 ~ | % 13
    \stemDown b2 ~ \pageBreak | % 14
    \stemDown b2 | % 15
    \stemDown c2 | % 16
    \stemDown b2 | % 17
    \stemDown c2 | % 18
    \stemDown b8 [ _\markup{ \small\italic {cresc.} } \stemDown b8
    \stemDown b8 \stemDown b8 ] | % 19
    \stemDown c4 r4 | \barNumberCheck #20
    \stemUp as,4 r4 | % 21
    \stemUp g4 r4 ^\fermata | % 22
    r8 \stemUp as8 [ _\ff \stemUp as8 \stemUp as8 ] | % 23
    \stemUp f2 ~ | % 24
    \stemUp f2 ^\fermata }

PartPOneEightVoiceOne =  \relative g {
    \clef "bass" \time 2/4 \key es \major \transposition c | % 1
    r8 \stemDown g8 [ _\ff \stemDown g8 \stemDown g8 ] | % 2
    \stemDown es2 ^\fermata | % 3
    r8 \stemDown f8 \stemDown f8 [ \stemDown f8 ] | % 4
    \stemDown d2 ~ | % 5
    \stemDown d2 ^\fermata | % 6
    R2*8 \pageBreak | % 14
    R2*4 | % 18
    r8 \stemUp b8 [ _\markup{ \small\italic {cresc.} } _\p \stemUp b8
    \stemUp b8 ] | % 19
    \stemUp c4 _\f _\f r4 | \barNumberCheck #20
    \stemUp as4 r4 | % 21
    \stemUp g4 r4 ^\fermata | % 22
    r8 \stemUp as8 [ _\ff \stemUp as8 \stemUp as8 ] | % 23
    \stemUp f2 ~ | % 24
    \stemUp f2 ^\fermata }


% The score definition
\score {
    <<
        
        \new Staff
        <<
            \set Staff.instrumentName = "Flute 1"
            \set Staff.shortInstrumentName = "Fl 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneVoiceOne" {  \PartPOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Flute 2"
            \set Staff.shortInstrumentName = "Fl 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoVoiceOne" {  \PartPTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Oboe 1"
            \set Staff.shortInstrumentName = "Ob 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeVoiceOne" {  \PartPThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Oboe 2"
            \set Staff.shortInstrumentName = "Ob 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFourVoiceOne" {  \PartPFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bb Clarinet"
            \set Staff.shortInstrumentName = "Cl 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFiveVoiceOne" {  \PartPFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bb Clarinet 2"
            \set Staff.shortInstrumentName = "Cl 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSixVoiceOne" {  \PartPSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bassoon 1"
            \set Staff.shortInstrumentName = "Bsn 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSevenVoiceOne" {  \PartPSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bassoon 2"
            \set Staff.shortInstrumentName = "Bsn 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPEightVoiceOne" {  \PartPEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Eb Horn 1"
            \set Staff.shortInstrumentName = "Hn 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPNineVoiceOne" {  \PartPNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Eb Horn 2"
            \set Staff.shortInstrumentName = "Hn 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneZeroVoiceOne" {  \PartPOneZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Trumpet 1"
            \set Staff.shortInstrumentName = "Tpt 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneOneVoiceOne" {  \PartPOneOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Trumpet 2"
            \set Staff.shortInstrumentName = "Tpt 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneTwoVoiceOne" {  \PartPOneTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C, G Timpani"
            \set Staff.shortInstrumentName = "Timp"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneThreeVoiceOne" {  \PartPOneThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 1"
            \set Staff.shortInstrumentName = "Vln 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFourVoiceOne" {  \PartPOneFourVoiceOne }
                \new Lyrics \lyricsto "PartPOneFourVoiceOne" { \set stanza = "1." \PartPOneFourVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 2"
            \set Staff.shortInstrumentName = "Vln 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFiveVoiceOne" {  \PartPOneFiveVoiceOne }
                \new Lyrics \lyricsto "PartPOneFiveVoiceOne" { \set stanza = "1." \PartPOneFiveVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Viola"
            \set Staff.shortInstrumentName = "Vla"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSixVoiceOne" {  \PartPOneSixVoiceOne }
                \new Lyrics \lyricsto "PartPOneSixVoiceOne" { \set stanza = "1." \PartPOneSixVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello"
            \set Staff.shortInstrumentName = "Vc"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSevenVoiceOne" {  \PartPOneSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Contrabass"
            \set Staff.shortInstrumentName = "Cb"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneEightVoiceOne" {  \PartPOneEightVoiceOne }
                >>
            >>
        
        >>
    \layout {}
    % To create MIDI output, uncomment the following line:
    %  \midi {\tempo 4 = 216 }
    }

