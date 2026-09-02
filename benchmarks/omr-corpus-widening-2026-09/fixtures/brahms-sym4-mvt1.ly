#(set-default-paper-size "a4")
#(set-global-staff-size 16)
\version "2.24.4"
% automatically converted by musicxml2ly from benchmarks/omr-corpus-widening-2026-09/fixtures/brahms-sym4-mvt1.musicxml
\pointAndClickOff

\header {
  tagline = ##f
    title =  "Symphony No.4"
    movementnumber =  "1"
    subtitle =  "Allegro non troppo"
    copyright =  "Score: CC0 1.0 Universal; Annotations: CC-By-SA"
    composer =  "Brahms, Johannes"
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
PartPOneVoiceOne =  \relative b'' {
    \clef "treble" \time 2/2 \key g \major | % 1
    r4 ^\markup{ \bold {Allegro non troppo} } s2. | % 2
    r4 \stemDown b4 ( -. -\markup{ \italic {dolce} } _\pp r4 \stemDown g4
    ) -. | % 3
    r4 \stemDown e4 ( -. r4 \stemDown c'4 ) -. | % 4
    r4 \stemDown a4 ( -. r4 \stemDown fis4 ) -. | % 5
    r4 \stemDown dis4 ( -. r4 \stemDown b'4 ) -. | % 6
    r4 \stemDown e4 ( -. r4 \stemDown e,4 ) -. }

PartPTwoVoiceOne =  \relative g'' {
    \clef "treble" \time 2/2 \key g \major | % 1
    r4 s2. | % 2
    r4 \stemDown g4 ( -. -\markup{ \italic {dolce} } _\pp r4 \stemDown e4
    ) -. | % 3
    r4 \stemDown c4 ( -. r4 \stemDown a'4 ) -. | % 4
    r4 \stemDown fis4 ( -. r4 \stemDown dis4 ) -. | % 5
    r4 \stemDown b4 ( -. r4 \stemDown g'4 ) -. | % 6
    r4 \stemDown c4 ( -. r4 \stemDown c,4 ) -. }

PartPThreeVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key g \major | % 1
    r4 s2. | % 2
    R1*5 }

PartPFourVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key g \major | % 1
    r4 s2. | % 2
    R1*5 }

PartPFiveVoiceOne =  \relative d'' {
    \clef "treble" \time 2/2 \key bes \major \transposition a | % 1
    r4 s2. | % 2
    r4 \stemDown d4 ( -. -\markup{ \italic {dolce} } _\pp r4 \stemDown
    bes4 ) -. | % 3
    r4 \stemUp g4 ( -. r4 \stemDown es'4 ) -. | % 4
    r4 \stemDown c4 ( -. r4 \stemUp a4 ) -. | % 5
    r4 \stemUp fis4 ( -. r4 \stemDown d'4 ) -. | % 6
    r4 \stemDown g4 ( -. r4 \stemUp g,4 ) -. }

PartPSixVoiceOne =  \relative bes' {
    \clef "treble" \time 2/2 \key bes \major \transposition a | % 1
    r4 s2. | % 2
    r4 \stemDown bes4 ( -. -\markup{ \italic {dolce} } _\pp r4 \stemUp g4
    ) -. | % 3
    r4 \stemUp es4 ( -. r4 \stemDown c'4 ) -. | % 4
    r4 \stemUp a4 ( -. r4 \stemUp fis4 ) -. | % 5
    r4 \stemUp d4 ( -. r4 \stemDown bes'4 ) -. | % 6
    r4 \stemDown es4 ( -. r4 \stemUp es,4 ) -. }

PartPSevenVoiceOne =  \relative b {
    \clef "bass" \time 2/2 \key g \major | % 1
    r4 s2. | % 2
    r4 \stemDown b4 ( -. -\markup{ \italic {dolce} } _\pp r4 \stemDown g4
    ) -. | % 3
    r4 \stemDown e4 ( -. r4 \stemDown c'4 ) -. | % 4
    r4 \stemDown a4 ( -. r4 \stemDown fis4 ) -. | % 5
    r4 \stemDown dis4 ( -. r4 \stemDown b'4 ) -. | % 6
    r4 \stemDown e4 ( -. r4 \stemDown e,4 ) -. }

PartPEightVoiceOne =  \relative g {
    \clef "bass" \time 2/2 \key g \major | % 1
    r4 s2. | % 2
    r4 \stemDown g4 ( -. -\markup{ \italic {dolce} } _\pp r4 \stemDown e4
    ) -. | % 3
    r4 \stemUp c4 ( -. r4 \stemDown a'4 ) -. | % 4
    r4 \stemDown fis4 ( -. r4 \stemDown dis4 ) -. | % 5
    r4 \stemUp b4 ( -. r4 \stemDown g'4 ) -. | % 6
    r4 \stemDown c4 ( -. r4 \stemUp c,4 ) -. }

PartPNineVoiceOne =  \relative c'' {
    \clef "treble" \time 2/2 \key c \major \transposition e | % 1
    r4 s2. | % 2
    c1 ~ _\p | % 3
    c1 ( | % 4
    g1 | % 5
    es1 ) ~ | % 6
    \stemUp es4 r4 r2 }

PartPOneZeroVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key c \major \transposition e | % 1
    r4 s2. | % 2
    c1 ~ _\p | % 3
    c1 ~ | % 4
    c1 ~ | % 5
    c1 ~ | % 6
    \stemUp c4 r4 r2 }

PartPOneOneVoiceOne =  \relative e'' {
    \clef "treble" \time 2/2 \key c \major \transposition c | % 1
    r4 s2. | % 2
    R1*4 | % 6
    e1 ( _\p }

PartPOneTwoVoiceOne =  \relative c'' {
    \clef "treble" \time 2/2 \key c \major \transposition c | % 1
    r4 s2. | % 2
    R1*4 | % 6
    c1 ( _\p }

PartPOneThreeVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key as \major \transposition e' | % 1
    r4 s2. | % 2
    R1*5 }

PartPOneFourVoiceOne =  \relative c' {
    \clef "treble" \time 2/2 \key as \major \transposition e' | % 1
    r4 s2. | % 2
    R1*5 }

PartPOneFiveVoiceOne =  \relative c' {
    \clef "bass" \time 2/2 \key c \major | % 1
    r4 s2. | % 2
    R1*5 }

PartPOneSixVoiceOne =  \relative b'' {
    \clef "treble" \time 2/2 \key g \major | % 1
    \stemDown b4 ( _\p s2. | % 2
    \stemDown g2 ) r4 \stemDown e4 ( | % 3
    \stemDown c'2 ) r4 \stemDown a4 ( | % 4
    \stemDown fis2 ) r4 \stemDown dis4 ( | % 5
    \stemDown b'2 ) r4 \stemDown e4 ( _\> | % 6
    \stemDown e,2 ) _\! r4 \stemDown g4 ( }

PartPOneSixVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata = ##t
    a\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 a\skip1 \skip1
    }

PartPOneSevenVoiceOne =  \relative b' {
    \clef "treble" \time 2/2 \key g \major | % 1
    \stemDown b4 ( _\p s2. | % 2
    \stemUp g2 ) r4 \stemUp e4 ( | % 3
    \stemDown c'2 ) r4 \stemUp a4 ( | % 4
    \stemUp fis2 ) r4 \stemUp dis4 ( | % 5
    \stemDown b'2 ) r4 \stemDown e4 ( _\> | % 6
    \stemUp e,2 ) _\! _\! r4 \stemUp g4 ( }

PartPOneEightVoiceOne =  \relative g {
    \clef "alto" \time 2/2 \key g \major | % 1
    r4 s2. | % 2
    r2 \stemDown <g b>8 ( [ _\p \stemDown <b e>8 \stemDown <e g>8
    \stemDown <g b>8 ) ] | % 3
    \stemDown <a, e'>4 r4 \stemDown <a c>8 ( [ \stemDown <c e>8
    \stemDown <e a>8 \stemDown <a c>8 ) ] | % 4
    \stemUp <a, dis>4 r4 \stemDown <fis a>8 ( [ \stemDown <a dis>8
    \stemDown <dis fis>8 \stemDown <fis a>8 ) ] | % 5
    \stemUp <g, b>4 r4 \stemUp <e g>8 ( [ \stemUp <g b>8 \stemUp <b e>8
    \stemUp <e g>8 ) ] | % 6
    \stemDown <e c'>4 r4 \stemDown <e, c'>8 ( [ \stemDown <g e'>8
    \stemDown <c g'>8 \stemDown <e c'>8 ) ] }

PartPOneNineVoiceOne =  \relative e, {
    \clef "bass" \time 2/2 \key g \major | % 1
    r4 s2. | % 2
    \stemUp e8 ( [ _\p \stemUp b'8 \stemUp g'8 \stemUp b8 ) ] \stemDown
    e,4 r4 | % 3
    \stemDown e,8 ( [ \stemDown c'8 \stemDown a'8 \stemDown c8 ) ]
    \stemDown e,4 r4 | % 4
    \stemUp e,8 [ \stemUp b'8 \stemUp fis'8 \stemUp a8 ] \stemUp b,4 r4
    | % 5
    \stemUp e,8 ( [ \stemUp b'8 \stemUp g'8 \stemUp b8 ) ] \stemDown e,4
    r4 | % 6
    \stemUp c,8 ( [ \stemUp g'8 \stemUp e'8 \stemUp g8 ) ] \stemUp c,4 r4
    }

PartPTwoZeroVoiceOne =  \relative e {
    \clef "bass_8" \time 2/2 \key g \major \transposition c | % 1
    r4 s2. | % 2
    \stemDown e2 _\p r2 | % 3
    \stemDown e2 r2 | % 4
    \stemDown e2 r2 | % 5
    \stemDown e2 r2 | % 6
    \stemDown e2 r2 }


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
            \set Staff.instrumentName = "A Clarinet 1"
            \set Staff.shortInstrumentName = "Cl 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPFiveVoiceOne" {  \PartPFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "A Clarinet 2"
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
            \set Staff.instrumentName = "E Horn 1"
            \set Staff.shortInstrumentName = "Hn 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPNineVoiceOne" {  \PartPNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "E Horn 2"
            \set Staff.shortInstrumentName = "Hn 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneZeroVoiceOne" {  \PartPOneZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Horn 3"
            \set Staff.shortInstrumentName = "Hn 3"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneOneVoiceOne" {  \PartPOneOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Horn 4"
            \set Staff.shortInstrumentName = "Hn 4"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneTwoVoiceOne" {  \PartPOneTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "E Trumpet 1"
            \set Staff.shortInstrumentName = "Tpt 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneThreeVoiceOne" {  \PartPOneThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "E Trumpet 2"
            \set Staff.shortInstrumentName = "Tpt 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFourVoiceOne" {  \PartPOneFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Timpani"
            \set Staff.shortInstrumentName = "Timp"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFiveVoiceOne" {  \PartPOneFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 1"
            \set Staff.shortInstrumentName = "Vln 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSixVoiceOne" {  \PartPOneSixVoiceOne }
                \new Lyrics \lyricsto "PartPOneSixVoiceOne" { \set stanza = "1." \PartPOneSixVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 2"
            \set Staff.shortInstrumentName = "Vln 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSevenVoiceOne" {  \PartPOneSevenVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Viola"
            \set Staff.shortInstrumentName = "Vla"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneEightVoiceOne" {  \PartPOneEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello"
            \set Staff.shortInstrumentName = "Vc"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneNineVoiceOne" {  \PartPOneNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Contrabass"
            \set Staff.shortInstrumentName = "Cb"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoZeroVoiceOne" {  \PartPTwoZeroVoiceOne }
                >>
            >>
        
        >>
    \layout {}
    % To create MIDI output, uncomment the following line:
    %  \midi {\tempo 4 = 100 }
    }

