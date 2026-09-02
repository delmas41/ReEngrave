#(set-default-paper-size "a4")
#(set-global-staff-size 16)
\version "2.24.4"
% automatically converted by musicxml2ly from benchmarks/omr-orchestral-e2e/fixtures-dirtext/beethoven-sym5-mvt1.musicxml
\pointAndClickOff

\header {
  tagline = ##f
    title =  "Symphony No.5"
    movementnumber =  "1"
    subtitle =  "Allegro con brio"
    copyright =  "Score: CC0 1.0 Universal; Annotations: CC-By-SA"
    composer =  "Beethoven, Ludwig van"
    encodingsoftware =  "music21 v.8.3.0"
    encodingdate =  "2026-09-02"
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
    \clef "treble" \time 2/4 \key es \major | % 1
    \tempo "" 2=108 R2 ^\markup{ \bold {Allegro con brio} } R2\fermata R2*2 R2\fermata R2*3 }

PartPTwoVoiceOne =  \relative c' {
    \clef "treble" \time 2/4 \key es \major | % 1
    R2 R2\fermata R2*2 R2\fermata R2*3 }

PartPThreeVoiceOne =  \relative c' {
    \clef "treble" \time 2/4 \key es \major | % 1
    R2 R2\fermata R2*2 R2\fermata R2*3 }

PartPFourVoiceOne =  \relative c' {
    \clef "treble" \time 2/4 \key es \major | % 1
    R2 R2\fermata R2*2 R2\fermata R2*3 }

PartPFiveVoiceOne =  \relative a' {
    \clef "treble" \time 2/4 \key f \major \transposition bes | % 1
    r8 \stemUp a8 [ _\ff \stemUp a8 \stemUp a8 ] | % 2
    \stemUp f2 ^\fermata | % 3
    r8 \stemUp g8 [ \stemUp g8 \stemUp g8 ] | % 4
    \stemUp e2 ~ | % 5
    \stemUp e2 ^\fermata | % 6
    R2*3 }

PartPSixVoiceOne =  \relative a' {
    \clef "treble" \time 2/4 \key f \major \transposition bes | % 1
    r8 \stemUp a8 [ _\ff \stemUp a8 \stemUp a8 ] | % 2
    \stemUp f2 ^\fermata | % 3
    r8 \stemUp g8 [ \stemUp g8 \stemUp g8 ] | % 4
    \stemUp e2 ~ | % 5
    \stemUp e2 ^\fermata | % 6
    R2*3 }

PartPSevenVoiceOne =  \relative c' {
    \clef "bass" \time 2/4 \key es \major | % 1
    R2 R2\fermata R2*2 R2\fermata R2 | % 7
    \stemDown c2 ~ _\p | % 8
    \stemDown c2 ~ }

PartPEightVoiceOne =  \relative c' {
    \clef "bass" \time 2/4 \key es \major | % 1
    R2 R2\fermata R2*2 R2\fermata R2 | % 7
    \stemDown c2 ~ _\p | % 8
    \stemDown c2 ~ }

PartPNineVoiceOne =  \relative c' {
    \clef "treble" \time 2/4 \key c \major \transposition es | % 1
    R2 R2\fermata R2*2 R2\fermata R2*3 }

PartPOneZeroVoiceOne =  \relative c' {
    \clef "treble" \time 2/4 \key c \major \transposition es | % 1
    R2 R2\fermata R2*2 R2\fermata R2*3 }

PartPOneOneVoiceOne =  \relative c' {
    \clef "treble" \time 2/4 \key es \major \transposition c' | % 1
    R2 R2\fermata R2*2 R2\fermata R2*3 }

PartPOneTwoVoiceOne =  \relative c' {
    \clef "treble" \time 2/4 \key es \major \transposition c' | % 1
    R2 R2\fermata R2*2 R2\fermata R2*3 }

PartPOneThreeVoiceOne =  \relative c' {
    \clef "bass" \time 2/4 \key es \major | % 1
    R2 R2\fermata R2*2 R2\fermata R2*3 }

PartPOneFourVoiceOne =  \relative g' {
    \clef "treble" \time 2/4 \key es \major | % 1
    r8 \stemUp g8 [ _\ff \stemUp g8 \stemUp g8 ] | % 2
    \stemUp es2 ^\fermata | % 3
    r8 \stemUp f8 [ \stemUp f8 \stemUp f8 ] | % 4
    \stemUp d2 ~ | % 5
    \stemUp d2 ^\fermata | % 6
    R2*2 | % 8
    r8 \stemDown es'8 [ _\p \stemDown es8 \stemDown es8 ] }

PartPOneFourVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata = ##t
    a\skip1 \skip1 \skip1 a\skip1 \skip1 \skip1 \skip1 a\skip1 \skip1
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
    \stemUp es2 ~ }

PartPOneFiveVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata =
    ##t\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    a\skip1 \skip1 \skip1 \skip1
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
    \stemDown g2 ~ }

PartPOneSixVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata =
    ##t\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    a\skip1 \skip1 \skip1
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
    \stemDown c2 ~ }

PartPOneEightVoiceOne =  \relative g {
    \clef "bass" \time 2/4 \key es \major \transposition c | % 1
    r8 \stemDown g8 [ _\ff \stemDown g8 \stemDown g8 ] | % 2
    \stemDown es2 ^\fermata | % 3
    r8 \stemDown f8 \stemDown f8 [ \stemDown f8 ] | % 4
    \stemDown d2 ~ | % 5
    \stemDown d2 ^\fermata | % 6
    R2*3 }


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

