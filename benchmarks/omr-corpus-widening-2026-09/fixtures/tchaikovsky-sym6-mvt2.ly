#(set-default-paper-size "a4")
#(set-global-staff-size 16)
\version "2.24.4"
% automatically converted by musicxml2ly from benchmarks/omr-corpus-widening-2026-09/fixtures/tchaikovsky-sym6-mvt2.musicxml
\pointAndClickOff

\header {
  tagline = ##f
    title =  "Symphony No. 6, Pathétique"
    subtitle =  "tchaikovsky-sym6-mvt2.mxl"
    composer =  "Pyotr Ilyich Tchaikovsky(1840–1893)"
    poet =  "Пётр Ильич Чайкoвский"
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
    \clef "treble" \time 5/4 \key d \major | % 1
    R4*20 ^\markup{ \bold {Allegretto con grazia} } }

PartPOneVoiceTwo =  \relative c' {
    \clef "treble" \time 5/4 \key d \major | % 1
    R4*20 }

PartPTwoVoiceOne =  \relative c' {
    \clef "treble" \time 5/4 \key d \major | % 1
    R4*20 }

PartPThreeVoiceOne =  \relative f'' {
    \clef "treble" \time 5/4 \key f \major \transposition a | % 1
    r2 r4 \stemDown <f a>4 ( _\mf \stemDown <a, c>8 ) r8 | % 2
    r2 r4 \stemDown <c g'>4 ( \stemUp <g c>8 ) r8 | % 3
    r2 r4 \stemDown <c f>4 ( \stemUp <e, c'>8 ) r8 | % 4
    r2 r4 \stemDown <c' e>4 ( \stemUp <e, c'>8 ) r8 }

PartPFourVoiceOne =  \relative d' {
    \clef "bass" \time 5/4 \key d \major | % 1
    r2 r4 \clef "tenor" \stemDown <d fis>4 ( _\mf \stemUp <fis, a>8 ) r8
    | % 2
    r2 r4 \stemDown <a e'>4 ( \stemUp <e a>8 ) r8 | % 3
    r2 r4 \stemDown <a d>4 ( \stemUp <cis, a'>8 ) r8 | % 4
    r2 r4 \stemDown <a' cis>4 ( \stemUp <cis, a'>8 ) r8 }

PartPFiveVoiceOne =  \relative a {
    \clef "treble" \time 5/4 \key c \major \transposition f | % 1
    r4 \stemUp <a e'>4 ( _\mf \stemUp <cis a'>8 ) r8 r2 | % 2
    r4 \stemUp <cis a'>8 r8 r4 r2 | % 3
    R4*10 }

PartPFiveVoiceTwo =  \relative g' {
    \clef "treble" \time 5/4 \key c \major \transposition f s4*15 | % 4
    g4 \rest \stemDown cis,8 g'8 \rest g4 \rest g2 \rest }

PartPSixVoiceOne =  \relative e' {
    \clef "treble" \time 5/4 \key c \major \transposition f | % 1
    R4*5 | % 2
    r4 ^\mf \stemUp e8 r8 r4 r2 | % 3
    r4 \stemUp <cis a'>4 ( _\mf \stemUp <e cis'>8 ) r8 r2 | % 4
    r4 \stemUp <a, e'>8 r8 r4 r2 }

PartPSixVoiceTwo =  \relative c' {
    \clef "treble" \time 5/4 \key c \major \transposition f s4*5 | % 2
    R4*5 }

PartPSevenVoiceOne =  \relative c' {
    \clef "treble" \time 5/4 \key c \major \transposition a | % 1
    R4*20 }

PartPEightVoiceOne =  \relative c' {
    \clef "tenor" \time 5/4 \key d \major | % 1
    R4*20 }

PartPNineVoiceOne =  \relative c' {
    \clef "bass" \time 5/4 \key d \major | % 1
    R4*20 }

PartPOneZeroVoiceOne =  \relative c' {
    \clef "bass" \time 5/4 \key d \major | % 1
    R4*20 }

PartPOneOneVoiceOne =  \relative c' {
    \clef "bass" \time 5/4 \key c \major | % 1
    R4*20 }

PartPOneTwoVoiceOne =  \relative d' {
    \clef "treble" \time 5/4 \key d \major | % 1
    R4*15 | % 4
    \stemUp d8 ^\markup{ \italic {pizz.} } _\mf r8 r4 \stemUp cis8 r8 r4
    r4 }

PartPOneThreeVoiceOne =  \relative a {
    \clef "treble" \time 5/4 \key d \major | % 1
    \stemUp a8 ^\markup{ \italic {pizz.} } _\mf r8 r4 r2 r4 | % 2
    \stemUp a8 r8 r4 \stemUp a8 r8 r4 r4 | % 3
    \stemUp a8 r8 r4 r2 r4 | % 4
    \stemUp a8 r8 r4 \stemUp a8 r8 r4 r4 }

PartPOneFourVoiceOne =  \relative d {
    \clef "alto" \time 5/4 \key d \major | % 1
    \stemUp d8 ^\markup{ \italic {pizz.} } _\mf r8 r4 r2 r4 | % 2
    \stemUp d8 r8 r4 \stemUp e8 r8 r4 r4 | % 3
    \stemUp d8 r8 r4 r2 r4 | % 4
    \stemUp d8 r8 r4 \stemUp e8 r8 r4 r4 }

PartPOneFiveVoiceOne =  \relative fis {
    \clef "bass" \time 5/4 \key d \major | % 1
    \stemDown fis4 ( _\mf \stemDown g4 ) \once \omit TupletBracket
    \times 2/3  {
        \stemDown a8 ( [ _\< \stemDown g8 \stemDown a8 ] }
    \stemDown b4 \stemDown cis4 ) | % 2
    \stemDown d4 ( _\! _\f \stemDown b4 ) \stemDown cis2. _\> | % 3
    \stemDown a4 ( _\! _\mf \stemDown b4 ) \once \omit TupletBracket
    \times 2/3  {
        \stemDown cis8 ( [ _\< \stemDown b8 \stemDown cis8 ] }
    \stemDown d4 \stemDown e4 ) | % 4
    \clef "tenor" \stemDown fis4 ( _\! _\f \stemDown d4 ) \stemDown e2.
    }

PartPOneSixVoiceOne =  \relative d {
    \clef "bass" \time 5/4 \key d \major \transposition c | % 1
    \stemDown d8 ^\markup{ \italic {pizz.} } _\mf r8 r4 r2 r4 | % 2
    \stemDown fis8 r8 r4 \stemDown a8 r8 r4 r4 | % 3
    \stemDown fis8 r8 r4 r2 r4 | % 4
    \stemDown d8 r8 r4 \stemDown a'8 r8 r4 r4 }


% The score definition
\score {
    <<
        
        \new PianoStaff
        <<
            \set PianoStaff.instrumentName = "Flauti"
            \set PianoStaff.shortInstrumentName = "Fl."
            
            \context Staff = "1" << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneVoiceOne" {  \PartPOneVoiceOne }
                >> \context Staff = "2" <<
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneVoiceTwo" {  \PartPOneVoiceTwo }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Oboi"
            \set Staff.shortInstrumentName = "Ob."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoVoiceOne" {  \PartPTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Clarinetti in A"
            \set Staff.shortInstrumentName = "Cl."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeVoiceOne" {  \PartPThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Fagotti"
            \set Staff.shortInstrumentName = "Fag."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFourVoiceOne" {  \PartPFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Corni in F I II"
            \set Staff.shortInstrumentName = "Cor. I II"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFiveVoiceOne" {  \voiceOne \PartPFiveVoiceOne }
                \context Voice = "PartPFiveVoiceTwo" {  \voiceTwo \PartPFiveVoiceTwo }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Corni in F III IV"
            \set Staff.shortInstrumentName = "Cor. III IV"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSixVoiceOne" {  \voiceOne \PartPSixVoiceOne }
                \context Voice = "PartPSixVoiceTwo" {  \voiceTwo \PartPSixVoiceTwo }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Trombe in A"
            \set Staff.shortInstrumentName = "Tr."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSevenVoiceOne" {  \PartPSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Tromboni Alto e Tenore"
            \set Staff.shortInstrumentName = "Tbni. A. T."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPEightVoiceOne" {  \PartPEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Trombone Basso"
            \set Staff.shortInstrumentName = "Tbn. B."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPNineVoiceOne" {  \PartPNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Tuba"
            \set Staff.shortInstrumentName = "Tuba"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneZeroVoiceOne" {  \PartPOneZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Timpani in A.D.E."
            \set Staff.shortInstrumentName = "Timp."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneOneVoiceOne" {  \PartPOneOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violino I"
            \set Staff.shortInstrumentName = "Str"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneTwoVoiceOne" {  \PartPOneTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violino II"
            \set Staff.shortInstrumentName = "Str"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneThreeVoiceOne" {  \PartPOneThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Viola"
            \set Staff.shortInstrumentName = "Str"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFourVoiceOne" {  \PartPOneFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello"
            \set Staff.shortInstrumentName = "Str"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFiveVoiceOne" {  \PartPOneFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Basso"
            \set Staff.shortInstrumentName = "Str"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSixVoiceOne" {  \PartPOneSixVoiceOne }
                >>
            >>
        
        >>
    \layout {}
    % To create MIDI output, uncomment the following line:
    %  \midi {\tempo 4 = 100 }
    }

