#(set-default-paper-size "a4")
#(set-global-staff-size 16)
\version "2.24.4"
% automatically converted by musicxml2ly from benchmarks/omr-corpus-widening-2026-09/fixtures/beethoven-sym3-mvt1.musicxml
\pointAndClickOff

\header {
  tagline = ##f
    title =  "Symphony No.3"
    movementnumber =  "1"
    subtitle =  "Allegro con brio"
    copyright =  "Score: CC0 1.0 Universal; Annotations: CC-By-SA"
    composer =  "Beethoven, Ludwig van"
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
PartPOneVoiceOne =  \relative es''' {
    \clef "treble" \time 3/4 \key es \major | % 1
    \tempo 2.=60 \stemDown es4 -. ^\markup{ \bold {Allegro con brio} }
    _\f r4 r4 | % 2
    \stemDown es4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPTwoVoiceOne =  \relative bes'' {
    \clef "treble" \time 3/4 \key es \major | % 1
    \stemDown bes4 -. _\f r4 r4 | % 2
    \stemDown bes4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPThreeVoiceOne =  \relative g'' {
    \clef "treble" \time 3/4 \key es \major | % 1
    \stemDown g4 -. _\f r4 r4 | % 2
    \stemDown g4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPFourVoiceOne =  \relative es'' {
    \clef "treble" \time 3/4 \key es \major | % 1
    \stemDown es4 -. _\f r4 r4 | % 2
    \stemDown es4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPFiveVoiceOne =  \relative f'' {
    \clef "treble" \time 3/4 \key f \major \transposition bes | % 1
    \stemDown f4 -. _\f r4 r4 | % 2
    \stemDown f4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPSixVoiceOne =  \relative a' {
    \clef "treble" \time 3/4 \key f \major \transposition bes | % 1
    \stemUp a4 -. _\f r4 r4 | % 2
    \stemUp a4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPSevenVoiceOne =  \relative es' {
    \clef "bass" \time 3/4 \key es \major | % 1
    \stemDown es4 -. _\f r4 r4 | % 2
    \stemDown es4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPEightVoiceOne =  \relative es {
    \clef "bass" \time 3/4 \key es \major | % 1
    \stemDown es4 -. _\f r4 r4 | % 2
    \stemDown es4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPNineVoiceOne =  \relative c'' {
    \clef "treble" \time 3/4 \key c \major \transposition es | % 1
    \stemDown c4 -. _\f r4 r4 | % 2
    \stemDown c4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPOneZeroVoiceOne =  \relative e' {
    \clef "treble" \time 3/4 \key c \major \transposition es | % 1
    \stemUp e4 -. _\f r4 r4 | % 2
    \stemUp e4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPOneOneVoiceOne =  \relative c'' {
    \clef "treble" \time 3/4 \key c \major \transposition es | % 1
    \stemDown c4 -. _\f r4 r4 | % 2
    \stemDown c4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPOneTwoVoiceOne =  \relative f'' {
    \clef "treble" \time 3/4 \key f \major \transposition bes | % 1
    \stemDown f4 -. _\f r4 r4 | % 2
    \stemDown f4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPOneThreeVoiceOne =  \relative f' {
    \clef "treble" \time 3/4 \key f \major \transposition bes | % 1
    \stemUp f4 -. _\f r4 r4 | % 2
    \stemUp f4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPOneFourVoiceOne =  \relative es {
    \clef "bass" \time 3/4 \key es \major | % 1
    \stemDown es4 -. _\f r4 r4 | % 2
    \stemDown es4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }

PartPOneFiveVoiceOne =  \relative g {
    \clef "treble" \time 3/4 \key es \major | % 1
    \stemUp <g es' bes' g'>4 -. _\f r4 r4 | % 2
    \stemUp <g es' bes' g'>4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*2 | % 7
        r8 \stemDown g''4 ^ "cresc." _\p \stemDown g4 \stemDown g8 ~ | % 8
        \stemDown g8 \stemDown g4 \stemDown g4 \stemDown g8 ~ }
    }

PartPOneFiveVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata = ##t
    a\skip1 a\skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    }

PartPOneSixVoiceOne =  \relative g {
    \clef "treble" \time 3/4 \key es \major | % 1
    \stemUp <g es' es'>4 -. _\f r4 r4 | % 2
    \stemUp <g es' es'>4 -. r4 r4 | % 3
    \stemUp g'2. :8 _\p | % 4
    \stemUp g2. :8 \repeat volta 2 {
        | % 5
        \stemUp g2. :8 | % 6
        \stemUp g2. :8 | % 7
        \stemUp g2. :8 ^ "cresc." | % 8
        \stemUp g2. :8 }
    }

PartPOneSevenVoiceOne =  \relative g {
    \clef "alto" \time 3/4 \key es \major | % 1
    \stemUp <g es'>4 -. _\f r4 r4 | % 2
    \stemUp <g es'>4 -. r4 r4 | % 3
    \stemUp bes2. :8 _\p | % 4
    \stemUp bes2. :8 \repeat volta 2 {
        | % 5
        \stemUp bes2. :8 | % 6
        \stemUp bes2. :8 | % 7
        \stemUp bes2. :8 ^ "cresc." | % 8
        \stemUp bes2. :8 }
    }

PartPOneEightVoiceOne =  \relative es {
    \clef "bass" \time 3/4 \key es \major | % 1
    \stemDown es4 -. _\f r4 r4 | % 2
    \stemDown es4 -. r4 r4 | % 3
    \stemDown es2 ( _\p \stemDown g4 | % 4
    \stemDown es2 \stemUp bes4 ) \repeat volta 2 {
        | % 5
        \stemDown es4 ( \stemDown g4 \stemDown bes4 ) | % 6
        \stemDown es,2 ( \stemDown d4 | % 7
        \stemUp cis2. ) ~ ^ "cresc." | % 8
        \stemUp cis2. }
    }

PartPOneEightVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata =
    ##t\skip1 \skip1 a\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1
    }

PartPOneNineVoiceOne =  \relative es {
    \clef "bass" \time 3/4 \key es \major \transposition c | % 1
    \stemDown es4 -. _\f r4 r4 | % 2
    \stemDown es4 -. r4 r4 | % 3
    R2.*2 \repeat volta 2 {
        | % 5
        R2.*4 }
    }


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
            \set Staff.instrumentName = "Eb Horn 3"
            \set Staff.shortInstrumentName = "Hn 3"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneOneVoiceOne" {  \PartPOneOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bb Trumpet 1"
            \set Staff.shortInstrumentName = "Tpt 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneTwoVoiceOne" {  \PartPOneTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Bb Trumpet 2"
            \set Staff.shortInstrumentName = "Tpt 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneThreeVoiceOne" {  \PartPOneThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Timpani"
            \set Staff.shortInstrumentName = "Timp"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFourVoiceOne" {  \PartPOneFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 1"
            \set Staff.shortInstrumentName = "Vln 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFiveVoiceOne" {  \PartPOneFiveVoiceOne }
                \new Lyrics \lyricsto "PartPOneFiveVoiceOne" { \set stanza = "1." \PartPOneFiveVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 2"
            \set Staff.shortInstrumentName = "Vln 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSixVoiceOne" {  \PartPOneSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Viola"
            \set Staff.shortInstrumentName = "Vla"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSevenVoiceOne" {  \PartPOneSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello"
            \set Staff.shortInstrumentName = "Vc"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneEightVoiceOne" {  \PartPOneEightVoiceOne }
                \new Lyrics \lyricsto "PartPOneEightVoiceOne" { \set stanza = "1." \PartPOneEightVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Contrabass"
            \set Staff.shortInstrumentName = "Cb"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneNineVoiceOne" {  \PartPOneNineVoiceOne }
                >>
            >>
        
        >>
    \layout {}
    % To create MIDI output, uncomment the following line:
    %  \midi {\tempo 4 = 180 }
    }

