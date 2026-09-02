#(set-default-paper-size "a4")
#(set-global-staff-size 16)
\version "2.24.4"
% automatically converted by musicxml2ly from benchmarks/omr-corpus-widening-2026-09/fixtures/dvorak-sym9-mvt4.musicxml
\pointAndClickOff

\header {
  tagline = ##f
    title =  "Symphony #9 in E Minor Op 95 part 4"
    subtitle =  "dvorak-sym9-mvt4.mxl"
    composer =  "Antonin Dvorak"
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
    \clef "treble" \time 4/4 \key g \major | % 1
    \tempo 4=152 R1*3 ^\markup{ \bold {Allegro con fuoco. M.M.} } }

PartPTwoVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key g \major | % 1
    R1*3 }

PartPThreeVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key bes \major \transposition a | % 1
    R1*3 }

PartPFourVoiceOne =  \relative c' {
    \clef "bass" \time 4/4 \key g \major | % 1
    R1*3 }

PartPFiveVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key c \major \transposition e | % 1
    R1*3 }

PartPFiveVoiceTwo =  \relative c' {
    \clef "treble" \time 4/4 \key c \major \transposition e | % 1
    R1*3 }

PartPSixVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key c \major \transposition es | % 1
    R1*3 }

PartPSevenVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key c \major \transposition e' | % 1
    R1*3 }

PartPEightVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key c \major \transposition c' | % 1
    R1*3 }

PartPNineVoiceOne =  \relative c' {
    \clef "treble" \time 4/4 \key c \major \transposition es' | % 1
    R1*3 }

PartPOneZeroVoiceOne =  \relative c' {
    \clef "alto" \time 4/4 \key g \major | % 1
    R1*3 }

PartPOneOneVoiceOne =  \relative c' {
    \clef "bass" \time 4/4 \key g \major | % 1
    R1*3 }

PartPOneTwoVoiceOne =  \relative c' {
    \clef "bass" \time 4/4 \key c \major | % 1
    R1*3 }

PartPOneThreeVoiceOne =  \relative c' {
    \clef "percussion" \time 4/4 \key c \major \stopStaff \override
    Staff.StaffSymbol.line-count = #1 \startStaff | % 1
    R1*3 }

PartPOneFourVoiceOne =  \relative b {
    \clef "treble" \time 4/4 \key g \major | % 1
    \stemUp b4. ( _\ff \stemUp c8 ) r2 | % 2
    \stemUp b4. ( \stemUp c8 ) r2 | % 3
    \stemUp b4 ( -> \stemUp c8 ) r8 \stemUp b4 ( -> \stemUp c8 ) r8 }

PartPOneFiveVoiceOne =  \relative b {
    \clef "treble" \time 4/4 \key g \major | % 1
    \stemUp b4. ( _\ff \stemUp c8 ) r2 | % 2
    \stemUp b4. ( \stemUp c8 ) r2 | % 3
    \stemUp b4 ( -> \stemUp c8 ) r8 \stemUp b4 ( -> \stemUp c8 ) r8 }

PartPOneSixVoiceOne =  \relative b {
    \clef "alto" \time 4/4 \key g \major | % 1
    \stemUp b4. ( _\ff \stemDown c8 ) r2 | % 2
    \stemUp b4. ( \stemDown c8 ) r2 | % 3
    \stemUp b4 ( -> \stemDown c8 ) r8 \stemUp b4 ( -> \stemDown c8 ) r8
    }

PartPOneSevenVoiceOne =  \relative b, {
    \clef "bass" \time 4/4 \key g \major | % 1
    \stemUp b4. ( _\ff \stemUp c8 ) r2 | % 2
    \stemUp b4. ( \stemUp c8 ) r2 | % 3
    \stemUp b4 ( -> \stemUp c8 ) r8 \stemUp b4 ( -> \stemUp c8 ) r8 }

PartPOneEightVoiceOne =  \relative b, {
    \clef "bass_8" \time 4/4 \key g \major \transposition c | % 1
    \stemUp b4. ( _\ff \stemUp c8 ) r2 | % 2
    \stemUp b4. ( \stemUp c8 ) r2 | % 3
    \stemUp b4 ( -> \stemUp c8 ) r8 \stemUp b4 ( -> \stemUp c8 ) r8 }


% The score definition
\score {
    <<
        
        \new Staff
        <<
            \set Staff.instrumentName = "Flutes"
            \set Staff.shortInstrumentName = "Fl."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneVoiceOne" {  \PartPOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Oboes"
            \set Staff.shortInstrumentName = "Ob."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoVoiceOne" {  \PartPTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "A Clarinet"
            \set Staff.shortInstrumentName = "A Cl."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPThreeVoiceOne" {  \PartPThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bassoons"
            \set Staff.shortInstrumentName = "Bsn."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFourVoiceOne" {  \PartPFourVoiceOne }
                >>
            >>
        \new PianoStaff
        <<
            \set PianoStaff.instrumentName = "E Horn"
            \set PianoStaff.shortInstrumentName = "E Hn."
            
            \context Staff = "1" << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFiveVoiceOne" {  \PartPFiveVoiceOne }
                >> \context Staff = "2" <<
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFiveVoiceTwo" {  \PartPFiveVoiceTwo }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Horn in E♭"
            \set Staff.shortInstrumentName = "E♭ Hn."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSixVoiceOne" {  \PartPSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "E Trumpet"
            \set Staff.shortInstrumentName = "E Tpt."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPSevenVoiceOne" {  \PartPSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Trumpet"
            \set Staff.shortInstrumentName = "C Tpt."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPEightVoiceOne" {  \PartPEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "E♭ Trumpet"
            \set Staff.shortInstrumentName = "E♭ Tpt."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPNineVoiceOne" {  \PartPNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Trombone"
            \set Staff.shortInstrumentName = "Tbn."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneZeroVoiceOne" {  \PartPOneZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bass Trombone"
            \set Staff.shortInstrumentName = "B. Tbn."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneOneVoiceOne" {  \PartPOneOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Timpani"
            \set Staff.shortInstrumentName = "Timp."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneTwoVoiceOne" {  \PartPOneTwoVoiceOne }
                >>
            >>
        \new RhythmicStaff
        <<
            \set RhythmicStaff.instrumentName = "Crash Cymbal"
            \set RhythmicStaff.shortInstrumentName = "Cr. Cym."
            
            \context RhythmicStaff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneThreeVoiceOne" {  \PartPOneThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violins I"
            \set Staff.shortInstrumentName = "Vln. I"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFourVoiceOne" {  \PartPOneFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violins II"
            \set Staff.shortInstrumentName = "Vln. II"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFiveVoiceOne" {  \PartPOneFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violas"
            \set Staff.shortInstrumentName = "Vlas."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSixVoiceOne" {  \PartPOneSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncellos"
            \set Staff.shortInstrumentName = "Vc."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSevenVoiceOne" {  \PartPOneSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Contrabasses"
            \set Staff.shortInstrumentName = "Cb."
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneEightVoiceOne" {  \PartPOneEightVoiceOne }
                >>
            >>
        
        >>
    \layout {}
    % To create MIDI output, uncomment the following line:
    %  \midi {\tempo 4 = 152 }
    }

