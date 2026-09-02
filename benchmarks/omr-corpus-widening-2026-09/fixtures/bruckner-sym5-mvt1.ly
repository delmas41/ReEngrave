#(set-default-paper-size "a3")
#(set-global-staff-size 16)
\version "2.24.4"
% automatically converted by musicxml2ly from benchmarks/omr-corpus-widening-2026-09/fixtures/bruckner-sym5-mvt1.musicxml
\pointAndClickOff

\header {
  tagline = ##f
    title =  "Symphony No. 5 in B-flat major"
    movementnumber =  "4"
    subtitle =  "Adagio - Allegro moderato"
    copyright =  "Score: CC0 1.0 Universal; Annotations: CC-By-SA"
    composer =  "Bruckner, Anton"
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
    \clef "treble" \time 2/2 \key bes \major | % 1
    R1*8 ^\markup{ \bold {Adagio} } }

PartPTwoVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key bes \major | % 1
    R1*8 }

PartPThreeVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key bes \major | % 1
    R1*8 }

PartPFourVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key bes \major | % 1
    R1*8 }

PartPFiveVoiceOne =  \relative c'' {
    \clef "treble" \time 2/2 \key c \major \transposition bes | % 1
    R1*2 | % 3
    \stemDown c4 -> _\pp \stemUp c,4 r2 | % 4
    R1 | % 5
    \stemDown e'4 -> _\p \stemUp e,4 r2 | % 6
    R1*3 }

PartPSixVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key c \major \transposition bes | % 1
    R1*8 }

PartPSevenVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key bes \major | % 1
    R1*8 }

PartPEightVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key bes \major | % 1
    R1*8 }

PartPNineVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key f \major \transposition f | % 1
    R1*8 }

PartPOneZeroVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key f \major \transposition f | % 1
    R1*8 }

PartPOneOneVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key f \major \transposition f | % 1
    R1*8 }

PartPOneTwoVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key f \major \transposition f | % 1
    R1*8 }

PartPOneThreeVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key f \major \transposition f' | % 1
    R1*8 }

PartPOneFourVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key f \major \transposition f' | % 1
    R1*8 }

PartPOneFiveVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key f \major \transposition f' | % 1
    R1*8 }

PartPOneSixVoiceOne =  \relative c' {
    \clef "tenor" \time 2/2 \key bes \major | % 1
    R1*8 }

PartPOneSevenVoiceOne =  \relative c' {
    \clef "tenor" \time 2/2 \key bes \major | % 1
    R1*8 }

PartPOneEightVoiceOne =  \relative c' {
    \clef "bass" \time 2/2 \key bes \major | % 1
    R1*8 }

PartPOneNineVoiceOne =  \relative c' {
    \clef "bass" \time 2/2 \key bes \major | % 1
    R1*8 }

PartPTwoZeroVoiceOne =  \relative c' {
    \clef "bass" \time 2/2 \key c \major | % 1
    R1*8 }

PartPTwoOneVoiceOne =  \relative f' {
    \clef "treble" \time 2/2 \key bes \major | % 1
    R1*4 | % 5
    f1 ~ _ "II." _\pp | % 6
    g1 ^ "I." ^\p | % 7
    \stemUp f2 _\pp _\sf \stemUp es2 ~ -> | % 8
    \stemUp es2 _\sf \stemUp d2 -> }

PartPTwoOneVoiceTwo =  \relative f' {
    \clef "treble" \time 2/2 \key bes \major s1*5 | % 6
    \stemDown f2 \stemDown e2 | % 7
    \stemDown d2 \stemDown g,2 -> | % 8
    \stemDown c4 \stemDown bes8 ( [ \stemDown a8 ) ] \stemDown a4 ->
    \stemDown g4 }

PartPTwoTwoVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key bes \major | % 1
    R1*3 | % 4
    c1 _\pp | % 5
    d1 ~ | % 6
    \stemUp d2 \stemUp cis2 | % 7
    \stemUp d2 _\pp \stemUp d2 ^> _\sf | % 8
    \stemUp c2. \stemUp bes4 }

PartPTwoTwoVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata = ##t
    a\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    }

PartPTwoThreeVoiceOne =  \relative bes {
    \clef "alto" \time 2/2 \key bes \major | % 1
    R1*2 | % 3
    bes1 ~ _\pp | % 4
    \stemUp bes2 \stemUp a2 ~ | % 5
    \stemUp a4 \stemUp c4 _\markup{ \small\italic {cresc.} } \stemUp bes4
    \stemUp a4 | % 6
    \stemUp bes2. \stemUp a8 ( [ \stemUp g8 ) ] | % 7
    \stemUp f2 _\pp \stemUp es2 ~ ^> _\sf | % 8
    \stemUp es2 \stemUp d2 ^> _\sf }

PartPTwoThreeVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata = ##t
    a\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1
    }

PartPTwoFourVoiceOne =  \relative bes, {
    \clef "bass" \time 2/2 \key bes \major | % 1
    \stemUp bes8 ^ "pizz." _\pp r8 \stemUp a8 r8 \stemUp g8 r8 \stemUp f8
    r8 | % 2
    \stemUp e8 r8 \stemUp f8 r8 \stemUp g8 r8 \stemUp a8 r8 | % 3
    \stemUp bes8 r8 \stemUp a8 r8 \stemUp g8 r8 \stemUp f8 r8 | % 4
    \stemUp e8 r8 \stemUp f8 r8 \stemUp g8 r8 \stemUp a8 r8 | % 5
    \stemUp bes8 r8 \stemUp a8 r8 \stemUp g8 r8 \stemUp f8 r8 | % 6
    \stemUp e8 r8 \stemUp f8 r8 \stemUp g8 r8 \stemUp a8 r8 | % 7
    \stemUp bes8 r8 \stemUp b8 _\markup{ \small\italic {cresc.} } r8
    \stemUp c8 r8 \stemUp bes8 r8 | % 8
    \stemUp a8 r8 \stemUp fis8 _\markup{ \small\italic {dim.} } r8
    \stemUp g8 r8 \stemDown g'8 r8 }

PartPTwoFourVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata = ##t
    x\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1
    }

PartPTwoFiveVoiceOne =  \relative bes, {
    \clef "bass" \time 2/2 \key bes \major \transposition c | % 1
    \stemUp bes8 ^ "pizz." _\pp r8 \stemUp a8 r8 \stemUp g8 r8 \stemUp f8
    r8 | % 2
    \stemUp e8 r8 \stemUp f8 r8 \stemUp g8 r8 \stemUp a8 r8 | % 3
    \stemUp bes8 r8 \stemUp a8 r8 \stemUp g8 r8 \stemUp f8 r8 | % 4
    \stemUp e8 r8 \stemUp f8 r8 \stemUp g8 r8 \stemUp a8 r8 | % 5
    \stemUp bes8 r8 \stemUp a8 r8 \stemUp g8 r8 \stemUp f8 r8 | % 6
    \stemUp e8 r8 \stemUp f8 r8 \stemUp g8 r8 \stemUp a8 r8 | % 7
    \stemUp bes8 r8 \stemUp b8 _\markup{ \small\italic {cresc.} } r8
    \stemUp c8 r8 \stemUp bes8 r8 | % 8
    \stemUp a8 r8 \stemUp fis8 _\markup{ \small\italic {dim.} } r8
    \stemUp g8 r8 \stemDown g'8 r8 }


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
            \set Staff.instrumentName = "Bb Clarinet 1"
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
            \set Staff.instrumentName = "F Horn 1"
            \set Staff.shortInstrumentName = "Hn 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPNineVoiceOne" {  \PartPNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "F Horn 2"
            \set Staff.shortInstrumentName = "Hn 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneZeroVoiceOne" {  \PartPOneZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "F Horn 3"
            \set Staff.shortInstrumentName = "Hn 3"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneOneVoiceOne" {  \PartPOneOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "F Horn 4"
            \set Staff.shortInstrumentName = "Hn 4"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneTwoVoiceOne" {  \PartPOneTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "F Trumpet 1"
            \set Staff.shortInstrumentName = "Tpt 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneThreeVoiceOne" {  \PartPOneThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "F Trumpet 2"
            \set Staff.shortInstrumentName = "Tpt 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFourVoiceOne" {  \PartPOneFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "F Trumpet 3"
            \set Staff.shortInstrumentName = "Tpt 3"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFiveVoiceOne" {  \PartPOneFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Alto Trombone"
            \set Staff.shortInstrumentName = "A Trb"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSixVoiceOne" {  \PartPOneSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Tenor Trombone"
            \set Staff.shortInstrumentName = "T Trb"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSevenVoiceOne" {  \PartPOneSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bass Trombone"
            \set Staff.shortInstrumentName = "B Trb"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneEightVoiceOne" {  \PartPOneEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bass Tuba"
            \set Staff.shortInstrumentName = "B Tba"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneNineVoiceOne" {  \PartPOneNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Timpani"
            \set Staff.shortInstrumentName = "Timp"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoZeroVoiceOne" {  \PartPTwoZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 1"
            \set Staff.shortInstrumentName = "Vln 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoOneVoiceOne" {  \voiceOne \PartPTwoOneVoiceOne }
                \context Voice = "PartPTwoOneVoiceTwo" {  \voiceTwo \PartPTwoOneVoiceTwo }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 2"
            \set Staff.shortInstrumentName = "Vln 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoTwoVoiceOne" {  \PartPTwoTwoVoiceOne }
                \new Lyrics \lyricsto "PartPTwoTwoVoiceOne" { \set stanza = "1." \PartPTwoTwoVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Viola"
            \set Staff.shortInstrumentName = "Vla"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoThreeVoiceOne" {  \PartPTwoThreeVoiceOne }
                \new Lyrics \lyricsto "PartPTwoThreeVoiceOne" { \set stanza = "1." \PartPTwoThreeVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello"
            \set Staff.shortInstrumentName = "Vc"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoFourVoiceOne" {  \PartPTwoFourVoiceOne }
                \new Lyrics \lyricsto "PartPTwoFourVoiceOne" { \set stanza = "1." \PartPTwoFourVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Contrabass"
            \set Staff.shortInstrumentName = "Cb"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoFiveVoiceOne" {  \PartPTwoFiveVoiceOne }
                >>
            >>
        
        >>
    \layout {}
    % To create MIDI output, uncomment the following line:
    %  \midi {\tempo 4 = 100 }
    }

