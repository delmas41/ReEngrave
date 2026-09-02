#(set-default-paper-size "a4")
#(set-global-staff-size 16)
\version "2.24.4"
% automatically converted by musicxml2ly from benchmarks/omr-corpus-widening-2026-09/fixtures/mozart-sym40-mvt1.musicxml
\pointAndClickOff

\header {
  tagline = ##f
    title =  "Symphony No. 40 in G Minor, K. 550"
    subtitle =  "mozart-sym40-mvt1.mxl"
    composer =  "Wolfgang Amadeus Mozart"
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
    R1*6 ^\markup{ \bold {Allegro molto.} } }

PartPTwoVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key bes \major | % 1
    R1*6 }

PartPThreeVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key c \major \transposition bes | % 1
    R1*6 }

PartPFourVoiceOne =  \relative c' {
    \clef "bass" \time 2/2 \key bes \major | % 1
    R1*6 }

PartPFiveVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key c \major \transposition bes | % 1
    R1*6 }

PartPSixVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key es \major \transposition g | % 1
    R1*6 }

PartPSevenVoiceOne =  \relative es'' {
    \clef "treble" \time 2/2 \key bes \major | % 1
    r2 r4 \stemDown es8 ( [ _\p \stemDown d8 ) ] | % 2
    \stemDown d4 -_ \stemDown es8 ( [ \stemDown d8 ) ] \stemDown d4 -_
    \stemDown es8 ( [ \stemDown d8 ) ] | % 3
    \stemDown d4 ( \stemDown bes'4 ) r4 \stemDown bes8 ( [ \stemDown a8
    ) ] | % 4
    \stemDown g4 -_ \stemDown g8 ( [ \stemDown f8 ) ] \stemDown es4 -_
    \stemDown es8 ( [ \stemDown d8 ) ] | % 5
    \stemDown c4 -_ \stemDown c4 r4 \stemDown d8 ( [ \stemDown c8 ) ] | % 6
    \stemDown c4 -_ \stemDown d8 ( [ \stemDown c8 ) ] \stemDown c4 -_
    \stemDown d8 ( [ \stemDown c8 ) ] }

PartPEightVoiceOne =  \relative es' {
    \clef "treble" \time 2/2 \key bes \major | % 1
    r2 r4 \stemUp es8 ( [ _\p \stemUp d8 ) ] | % 2
    \stemUp d4 -_ \stemUp es8 ( [ \stemUp d8 ) ] \stemUp d4 -_ \stemUp
    es8 ( [ \stemUp d8 ) ] | % 3
    \stemUp d4 ( \stemDown bes'4 ) r4 \stemUp bes8 ( [ \stemUp a8 ) ] | % 4
    \stemUp g4 -_ \stemUp g8 ( [ \stemUp f8 ) ] \stemUp es4 -_ \stemUp
    es8 ( [ \stemUp d8 ) ] | % 5
    \stemUp c4 -_ \stemUp c4 r4 \stemUp d8 ( [ \stemUp c8 ) ] | % 6
    \stemUp c4 -_ \stemUp d8 ( [ \stemUp c8 ) ] \stemUp c4 -_ \stemUp d8
    ( [ \stemUp c8 ) ] }

PartPNineVoiceOne =  \relative bes {
    \clef "alto" \time 2/2 \key bes \major | % 1
    \stemUp bes8 -. [ _\p \stemUp bes8 -. \stemUp g'8 -. \stemUp g8 -. ]
    \stemUp bes,8 -. [ \stemUp bes8 -. \stemUp g'8 -. \stemUp g8 -. ] | % 2
    \stemUp bes,8 -. [ \stemUp bes8 -. \stemUp g'8 -. \stemUp g8 -. ]
    \stemUp bes,8 -. [ \stemUp bes8 -. \stemUp g'8 -. \stemUp g8 -. ] | % 3
    \stemUp bes,8 -. [ \stemUp bes8 -. \stemUp g'8 -. \stemUp g8 -. ]
    \stemUp bes,8 -. [ \stemUp bes8 -. \stemUp g'8 -. \stemUp g8 -. ] | % 4
    \stemUp bes,8 -. [ \stemUp bes8 -. \stemUp d8 -. \stemUp d8 -. ]
    \stemUp bes8 -. [ \stemUp bes8 -. \stemUp g'8 -. \stemUp g8 -. ] | % 5
    \stemUp es8 -. [ \stemUp es8 -. \stemUp a8 -. \stemUp a8 -. ]
    \stemUp es8 -. [ \stemUp es8 -. \stemUp a8 -. \stemUp a8 -. ] | % 6
    \stemUp es8 -. [ \stemUp es8 -. \stemUp a8 -. \stemUp a8 -. ]
    \stemUp es8 -. [ \stemUp es8 -. \stemUp a8 -. \stemUp a8 -. ] }

PartPNineVoiceTwo =  \relative g {
    \clef "alto" \time 2/2 \key bes \major | % 1
    \stemDown g8 -. [ \stemDown g8 -. \stemDown bes8 -. \stemDown bes8
    -. ] \stemDown g8 -. [ \stemDown g8 -. \stemDown bes8 -. \stemDown
    bes8 -. ] | % 2
    \stemDown g8 -. [ \stemDown g8 -. \stemDown bes8 -. \stemDown bes8
    -. ] \stemDown g8 -. [ \stemDown g8 -. \stemDown bes8 -. \stemDown
    bes8 -. ] | % 3
    \stemDown g8 -. [ \stemDown g8 -. \stemDown d'8 -. \stemDown d8 -. ]
    \stemDown g,8 -. [ \stemDown g8 -. \stemDown d'8 -. \stemDown d8 -.
    ] | % 4
    \stemDown g,8 -. [ \stemDown g8 -. \stemDown bes8 -. \stemDown bes8
    -. ] \stemDown g8 -. [ \stemDown g8 -. \stemDown bes8 -. \stemDown
    bes8 -. ] | % 5
    \stemDown a8 -. [ \stemDown a8 -. \stemDown es'8 -. \stemDown es8 -.
    ] \stemDown a,8 -. [ \stemDown a8 -. \stemDown es'8 -. \stemDown es8
    -. ] | % 6
    \stemDown a,8 -. [ \stemDown a8 -. \stemDown es'8 -. \stemDown es8
    -. ] \stemDown a,8 -. [ \stemDown a8 -. \stemDown es'8 -. \stemDown
    es8 -. ] }

PartPOneZeroVoiceOne =  \relative g, {
    \clef "bass" \time 2/2 \key bes \major | % 1
    \stemUp g4 _\p r4 r2 | % 2
    \stemDown g'4 r4 r2 | % 3
    \stemUp g,4 r4 r2 | % 4
    \stemDown g'4 r4 r2 | % 5
    \stemUp g,4 r4 r2 | % 6
    \stemDown g'4 r4 r2 }

PartPOneOneVoiceOne =  \relative g, {
    \clef "bass" \time 2/2 \key bes \major \transposition c | % 1
    \stemUp g4 _\p r4 r2 | % 2
    \stemDown g'4 r4 r2 | % 3
    \stemUp g,4 r4 r2 | % 4
    \stemDown g'4 r4 r2 | % 5
    \stemUp g,4 r4 r2 | % 6
    \stemDown g'4 r4 r2 }


% The score definition
\score {
    <<
        
        \new Staff
        <<
            \set Staff.instrumentName = "Flauto."
            \set Staff.shortInstrumentName = "Fl"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneVoiceOne" {  \PartPOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Oboi."
            \set Staff.shortInstrumentName = "Ob"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoVoiceOne" {  \PartPTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Clarinetti in B."
            \set Staff.shortInstrumentName = "Cl"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeVoiceOne" {  \PartPThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Fagotti."
            \set Staff.shortInstrumentName = "Bsn"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFourVoiceOne" {  \PartPFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Corno in B."
            \set Staff.shortInstrumentName = "Hn"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFiveVoiceOne" {  \PartPFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Corno in G."
            \set Staff.shortInstrumentName = "Hn"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSixVoiceOne" {  \PartPSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violino I."
            \set Staff.shortInstrumentName = "Str"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSevenVoiceOne" {  \PartPSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violino II."
            \set Staff.shortInstrumentName = "Str"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPEightVoiceOne" {  \PartPEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Viola."
            \set Staff.shortInstrumentName = "Str"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPNineVoiceOne" {  \voiceOne \PartPNineVoiceOne }
                \context Voice = "PartPNineVoiceTwo" {  \voiceTwo \PartPNineVoiceTwo }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello."
            \set Staff.shortInstrumentName = "Str"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneZeroVoiceOne" {  \PartPOneZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Contrabasso."
            \set Staff.shortInstrumentName = "Str"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneOneVoiceOne" {  \PartPOneOneVoiceOne }
                >>
            >>
        
        >>
    \layout {}
    % To create MIDI output, uncomment the following line:
    %  \midi {\tempo 4 = 100 }
    }

