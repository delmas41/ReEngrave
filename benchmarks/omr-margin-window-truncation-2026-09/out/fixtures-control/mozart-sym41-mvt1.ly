#(set-default-paper-size "a4")
#(set-global-staff-size 16)
\version "2.24.4"
% automatically converted by musicxml2ly from benchmarks/omr-margin-window-truncation-2026-09/out/fixtures-control/mozart-sym41-mvt1.musicxml
\pointAndClickOff

\header {
  tagline = ##f
    title =  "Symphony No. 41 in C Major (“Jupiter”)"
    subtitle =  "mozart-sym41-mvt1.mxl"
    composer =  "Wolfgang Amadeus Mozart"
    encodingsoftware =  "music21 v.8.3.0"
    encodingdate =  "2026-09-06"
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
PartPOneVoiceOne =  \relative c''' {
    \clef "treble" \time 4/4 \key c \major | % 1
    \stemDown c4 ^\markup{ \bold {Allegro vivace} } _\f r8 \once \omit
    TupletBracket
    \times 2/3  {
        \stemDown g16 ( [ \stemDown a16 \stemDown b16 ] }
    \stemDown c4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown g16 ( [ \stemDown a16 \stemDown b16 ] }
    | % 2
    \stemDown c4 ) r4 r2 | % 3
    R1*2 | % 5
    \stemDown g4 r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    \stemDown g4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    | % 6
    \stemDown g4 ) r4 r2 }

PartPTwoVoiceOne =  \relative c'' {
    \clef "treble" \time 4/4 \key c \major | % 1
    \stemDown c4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    \stemDown c4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    | % 2
    \stemDown c4 ) r4 r2 | % 3
    R1*2 | % 5
    \stemDown g'4 r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    \stemDown g4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    | % 6
    \stemDown g4 ) r4 r2 }

PartPThreeVoiceOne =  \relative c'' {
    \clef "treble" \time 4/4 \key c \major | % 1
    \stemDown c4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    \stemDown c4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    | % 2
    \stemDown c4 ) r4 r2 | % 3
    R1*2 | % 5
    \stemDown g'4 r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    \stemDown g4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    | % 6
    \stemDown g4 ) r4 r2 }

PartPFourVoiceOne =  \relative c {
    \clef "bass" \time 4/4 \key c \major | % 1
    \stemUp c4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    \stemUp c4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    | % 2
    \stemUp c4 ) r4 r2 | % 3
    R1*2 | % 5
    \stemDown g'4 r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    \stemDown g4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    | % 6
    \stemDown g4 ) r4 r2 }

PartPFiveVoiceOne =  \relative c {
    \clef "bass" \time 4/4 \key c \major | % 1
    \stemUp c4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    \stemUp c4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    | % 2
    \stemUp c4 ) r4 r2 | % 3
    R1*2 | % 5
    \stemDown g'4 r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    \stemDown g4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    | % 6
    \stemDown g4 ) r4 r2 }

PartPSixVoiceOne =  \relative c'' {
    \clef "treble" \time 4/4 \key c \major \transposition c | % 1
    \stemDown c4 _\f r4 \stemDown c4 r4 | % 2
    \stemDown c4 r4 r2 | % 3
    R1*2 | % 5
    \stemUp g4 r4 \stemUp g4 r4 | % 6
    \stemUp g4 r4 r2 }

PartPSevenVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key c \major \transposition c | % 1
    \stemUp c4 _\f r4 \stemUp c4 r4 | % 2
    \stemUp c4 r4 r2 | % 3
    R1*2 | % 5
    \stemUp g'4 r4 \stemUp g4 r4 | % 6
    \stemUp g4 r4 r2 }

PartPEightVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key g \major \transposition f | % 1
    R1*6 }

PartPNineVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key g \major \transposition f | % 1
    R1*6 }

PartPOneZeroVoiceOne =  \relative c'' {
    \clef "treble" \time 4/4 \key c \major \transposition c' | % 1
    \stemDown c4 _\f r4 \stemDown c4 r4 | % 2
    \stemDown c4 r4 r2 | % 3
    R1*2 | % 5
    \stemUp g4 r4 \stemUp g4 r4 | % 6
    \stemUp g4 r4 r2 }

PartPOneOneVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key c \major \transposition c' | % 1
    \stemUp c4 _\f r4 \stemUp c4 r4 | % 2
    \stemUp c4 r4 r2 | % 3
    R1*2 | % 5
    \stemUp g'4 r4 \stemUp g4 r4 | % 6
    \stemUp g4 r4 r2 }

PartPOneTwoVoiceOne =  \relative c {
    \clef "bass" \time 4/4 \key c \major | % 1
    \stemUp c4 _\f r4 \stemUp c4 r4 | % 2
    \stemUp c4 r4 r2 | % 3
    R1*2 | % 5
    \stemUp g4 r4 \stemUp g4 r4 | % 6
    \stemUp g4 r4 r2 }

PartPOneThreeVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key c \major | % 1
    \stemUp c4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    \stemUp c4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    | % 2
    \stemUp c4 ) r4 r4 r8 \stemDown c'8 -. _\p | % 3
    \stemDown c4. ( \stemDown b8 \stemDown d4. \stemDown c8 ) | % 4
    \stemDown g'2 ( \stemDown f4 ) r4 | % 5
    \stemUp <g,, g'>4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp d'16 ( [ \stemUp e16 \stemUp fis16 ] }
    \stemUp g4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp d16 ( [ \stemUp e16 \stemUp fis16 ] }
    | % 6
    \stemUp g4 ) r4 r4 r8 \stemDown d'8 -. _\p }

PartPOneFourVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key c \major | % 1
    \stemUp c4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    \stemUp c4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    | % 2
    \stemUp c4 ) r4 r2 | % 3
    \stemUp f2 ( _\p \stemUp e2 ) | % 4
    \stemUp d2. r4 | % 5
    \stemUp <g, g'>4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp d'16 ( [ \stemUp e16 \stemUp fis16 ] }
    \stemUp g4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp d16 ( [ \stemUp e16 \stemUp fis16 ] }
    | % 6
    \stemUp g4 ) r4 r2 }

PartPOneFiveVoiceOne =  \relative c' {
    \clef "alto" \time 4/4 \key c \major | % 1
    \stemDown c4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    \stemDown c4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    | % 2
    \stemDown c4 ) r4 r2 | % 3
    g'1 ~ _\p | % 4
    \stemDown g2. r4 | % 5
    \stemDown g4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    \stemDown g4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    | % 6
    \stemDown g4 ) r4 r2 }

PartPOneSixVoiceOne =  \relative c {
    \clef "bass" \time 4/4 \key c \major | % 1
    \stemUp c4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    \stemUp c4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    | % 2
    \stemUp c4 ) r4 r2 | % 3
    \stemDown d'2 ( _\p \stemDown c2 ) | % 4
    \stemDown b2. r4 | % 5
    \stemDown g4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    \stemDown g4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    | % 6
    \stemDown g4 ) r4 r2 }

PartPOneSevenVoiceOne =  \relative c {
    \clef "bass" \time 4/4 \key c \major \transposition c | % 1
    \stemUp c4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    \stemUp c4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemUp g16 ( [ \stemUp a16 \stemUp b16 ] }
    | % 2
    \stemUp c4 ) r4 r2 | % 3
    R1*2 | % 5
    \stemDown g'4 _\f r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    \stemDown g4 ) r8 \once \omit TupletBracket
    \times 2/3  {
        \stemDown d16 ( [ \stemDown e16 \stemDown fis16 ] }
    | % 6
    \stemDown g4 ) r4 r2 }


% The score definition
\score {
    <<
        
        \new Staff
        <<
            \set Staff.instrumentName = "Flauto"
            \set Staff.shortInstrumentName = "Fl."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneVoiceOne" {  \PartPOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Oboe I"
            \set Staff.shortInstrumentName = "Ob. I"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoVoiceOne" {  \PartPTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Oboe II"
            \set Staff.shortInstrumentName = "Ob. II"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeVoiceOne" {  \PartPThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Fagotto I"
            \set Staff.shortInstrumentName = "Fgt. I"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFourVoiceOne" {  \PartPFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Fagotto II"
            \set Staff.shortInstrumentName = "Fgt. II"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFiveVoiceOne" {  \PartPFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Corno I in C"
            \set Staff.shortInstrumentName = "Cn. I"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSixVoiceOne" {  \PartPSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Corno II in C"
            \set Staff.shortInstrumentName = "Cn. II"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSevenVoiceOne" {  \PartPSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Corno I in F"
            \set Staff.shortInstrumentName = "Cn. I"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPEightVoiceOne" {  \PartPEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Corno II in F"
            \set Staff.shortInstrumentName = "Cn. II"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPNineVoiceOne" {  \PartPNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Clarino I in C"
            \set Staff.shortInstrumentName = "Cln. I"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneZeroVoiceOne" {  \PartPOneZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Clarino II in C"
            \set Staff.shortInstrumentName = "Cln. II"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneOneVoiceOne" {  \PartPOneOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Timpani in C–G"
            \set Staff.shortInstrumentName = "Timp."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneTwoVoiceOne" {  \PartPOneTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violino I"
            \set Staff.shortInstrumentName = "Vln. I"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneThreeVoiceOne" {  \PartPOneThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violino II"
            \set Staff.shortInstrumentName = "Vln. II"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFourVoiceOne" {  \PartPOneFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Viola"
            \set Staff.shortInstrumentName = "Vla."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFiveVoiceOne" {  \PartPOneFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello"
            \set Staff.shortInstrumentName = "Vc."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSixVoiceOne" {  \PartPOneSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Basso"
            \set Staff.shortInstrumentName = "Bs."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSevenVoiceOne" {  \PartPOneSevenVoiceOne }
                >>
            >>
        
        >>
    \layout {}
    % To create MIDI output, uncomment the following line:
    %  \midi {\tempo 4 = 100 }
    }

