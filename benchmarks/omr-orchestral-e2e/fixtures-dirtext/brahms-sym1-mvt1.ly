#(set-default-paper-size "a3")
#(set-global-staff-size 16)
\version "2.24.4"
% automatically converted by musicxml2ly from benchmarks/omr-orchestral-e2e/fixtures-dirtext/brahms-sym1-mvt1.musicxml
\pointAndClickOff

\header {
  tagline = ##f
    title =  "Symphony No.1"
    movementnumber =  "1"
    subtitle =  "Un poco sostenuto - Allegro"
    copyright =  "Score: CC0 1.0 Universal; Annotations: CC-By-SA"
    composer =  "Brahms, Johannes"
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
PartPOneVoiceOne =  \relative c''' {
    \clef "treble" \time 6/8 \key es \major | % 1
    \tempo 8=96 \stemDown c4. ( ^\markup{ \bold {Un poco sostenuto} } ^
    "[" ^\markup{ \bold {]} } _\f \stemDown bes4. -\markup{ \italic
        {legato} } | % 2
    \stemDown a4. \stemDown as4 \stemDown as8 ) | % 3
    \stemDown f4. ( \stemDown es'4. ) | % 4
    \stemDown d4. ( \stemDown d8 [ \stemDown es8 \stemDown f8 ) ] | % 5
    \stemDown d4. ( \stemDown d8 [ \stemDown es8 \stemDown f8 ) ] | % 6
    \stemDown g4. ( \stemDown g,8 [ \stemDown as8 \stemDown bes8 ) ] | % 7
    \stemDown c4 ( \stemDown d8 \stemDown es4 \stemDown f8 ) \bar "||"
    }

PartPTwoVoiceOne =  \relative c'' {
    \clef "treble" \time 6/8 \key es \major | % 1
    \stemDown c4. ( _\f \stemDown g'4. -\markup{ \italic {legato} } | % 2
    \stemDown fis4. \stemDown f4 \stemDown f8 ) | % 3
    \stemDown d4. ( \stemDown c'4. ) | % 4
    \stemDown bes4. ( \stemDown bes8 [ \stemDown c8 \stemDown d8 ) ] | % 5
    \stemDown b4. ( \stemDown b8 [ \stemDown c8 \stemDown d8 ) ] | % 6
    \stemDown es4. ( \stemDown es,8 [ \stemDown f8 \stemDown g8 ) ] | % 7
    \stemDown as4 ( \stemDown bes8 \stemDown c4 \stemDown d8 ) \bar "||"
    }

PartPThreeVoiceOne =  \relative c''' {
    \clef "treble" \time 6/8 \key es \major | % 1
    \stemDown c4. ( _\f \stemDown bes4. -\markup{ \italic {legato} } | % 2
    \stemDown a4. \stemDown as4 \stemDown as8 ) | % 3
    \stemDown f4. ( \stemDown es4. ) | % 4
    \stemDown d4. ( \stemDown d8 [ \stemDown es8 \stemDown f8 ) ] | % 5
    \stemDown d4. ( \stemDown d8 [ \stemDown es8 \stemDown f8 ) ] | % 6
    \stemDown g4. ( \stemDown g8 [ \stemDown as8 \stemDown bes8 ) ] | % 7
    \stemDown c4 ( \stemDown c8 \stemDown e,4 \stemDown f8 ) \bar "||"
    }

PartPFourVoiceOne =  \relative c'' {
    \clef "treble" \time 6/8 \key es \major | % 1
    \stemDown c4. ( _\f \stemDown g'4. -\markup{ \italic {legato} } | % 2
    \stemDown fis4. \stemDown f4 \stemDown f8 ) | % 3
    \stemDown d4. ( \stemDown c4. ) | % 4
    \stemDown bes4. ( \stemDown bes8 [ \stemDown c8 \stemDown d8 ) ] | % 5
    \stemDown b4. ( \stemDown b8 [ \stemDown c8 \stemDown d8 ) ] | % 6
    \stemDown es4. ( \stemDown es8 [ \stemDown f8 \stemDown g8 ) ] | % 7
    \stemDown as4 ( \stemDown d,8 \stemDown c4 \stemDown d8 ) \bar "||"
    }

PartPFiveVoiceOne =  \relative d''' {
    \clef "treble" \time 6/8 \key es \major \transposition bes | % 1
    \stemDown d4. ( _\f \stemDown c4. -\markup{ \italic {legato} } | % 2
    \stemDown b4. \stemDown bes4 \stemDown bes8 ) | % 3
    \stemDown g4. ( \stemDown f4. ) | % 4
    \stemDown e4. ( \stemUp e,8 [ \stemUp f8 \stemUp g8 ) ] | % 5
    \stemUp e4. ( \stemUp e8 [ \stemUp f8 \stemUp g8 ) ] | % 6
    \stemUp a4. ( \stemDown a8 [ \stemDown bes8 \stemDown c8 ) ] | % 7
    \stemDown d4 ( \stemDown e8 \stemDown fis4 \stemDown g8 ) \bar "||"
    }

PartPSixVoiceOne =  \relative d'' {
    \clef "treble" \time 6/8 \key es \major \transposition bes | % 1
    \stemDown d4. ( _\f \stemDown a'4. -\markup{ \italic {legato} } | % 2
    \stemDown gis4. \stemDown g4 \stemDown g8 ) | % 3
    \stemDown e4. ( \stemDown d4. ) | % 4
    \stemDown c4. ( \stemUp c,8 [ \stemUp d8 \stemUp e8 ) ] | % 5
    \stemUp cis4. ( \stemUp cis8 [ \stemUp d8 \stemUp e8 ) ] | % 6
    \stemUp f4. ( \stemUp f8 [ \stemUp g8 \stemUp a8 ) ] | % 7
    \stemDown bes4 ( \stemDown c8 \stemDown d4 \stemDown e8 ) \bar "||"
    }

PartPSevenVoiceOne =  \relative c' {
    \clef "bass" \time 6/8 \key es \major | % 1
    \stemDown c4. ( \stemDown bes4. -\markup{ \italic {legato} } | % 2
    \stemDown a4. \stemDown as4 \stemDown as8 ) | % 3
    \stemDown f4. ( \stemDown es4. ) | % 4
    \stemDown d4. ( \stemDown d8 [ \stemDown es8 \stemDown f8 ) ] | % 5
    \stemDown d4. ( \stemDown d8 [ \stemDown es8 \stemDown f8 ) ] | % 6
    \stemDown g4. ( \stemDown g8 [ \stemDown as8 \stemDown bes8 ) ] | % 7
    \stemDown c4 ( \stemDown d8 \stemDown e4 \stemDown f8 ) \bar "||"
    }

PartPEightVoiceOne =  \relative c {
    \clef "bass" \time 6/8 \key es \major | % 1
    \stemUp c4. ( \stemDown g'4. -\markup{ \italic {legato} } | % 2
    \stemDown fis4. \stemDown f4 \stemDown f8 ) | % 3
    \stemDown d4. ( \stemUp c4. ) | % 4
    \stemUp bes4. ( \stemUp bes8 [ \stemUp c8 \stemUp d8 ) ] | % 5
    \stemUp b4. ( \stemUp b8 [ \stemUp c8 \stemUp d8 ) ] | % 6
    \stemDown es4. ( \stemDown es8 [ \stemDown f8 \stemDown g8 ) ] | % 7
    \stemDown as4 ( \stemDown bes8 \stemDown c4 \stemDown d8 ) \bar "||"
    }

PartPNineVoiceOne =  \relative c, {
    \clef "bass" \time 6/8 \key es \major \transposition c | % 1
    \stemUp c8 ( [ _\f \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 2
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 3
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 4
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 5
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 6
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 7
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] \bar "||"
    }

PartPOneZeroVoiceOne =  \relative c' {
    \clef "treble" \time 6/8 \key c \major \transposition f | % 1
    \stemUp c2. ~ _\f | % 2
    \stemUp c2. ~ | % 3
    \stemUp c2. ~ | % 4
    \stemUp c2. ~ | % 5
    \stemUp c2. ~ | % 6
    \stemUp c2. ~ | % 7
    \stemUp c2. ~ \bar "||"
    }

PartPOneOneVoiceOne =  \relative c {
    \clef "treble" \time 6/8 \key c \major \transposition f | % 1
    \stemUp c2. ~ _\f | % 2
    \stemUp c2. ~ | % 3
    \stemUp c2. ~ | % 4
    \stemUp c2. ~ | % 5
    \stemUp c2. ~ | % 6
    \stemUp c2. ~ | % 7
    \stemUp c2. ~ \bar "||"
    }

PartPOneTwoVoiceOne =  \relative g'' {
    \clef "treble" \time 6/8 \key f \major \transposition f | % 1
    r4 r8 \stemDown g4. _\f | % 2
    \stemDown ges4. \stemDown f4 \stemDown es8 | % 3
    \stemDown d4. \stemDown c4. | % 4
    \stemDown ces4 r8 r4 r8 | % 5
    R2.*3 \bar "||"
    }

PartPOneThreeVoiceOne =  \relative e'' {
    \clef "treble" \time 6/8 \key f \major \transposition f | % 1
    r4 r8 \stemDown e4. _\f | % 2
    \stemDown es4. \stemDown d4 \stemDown c8 | % 3
    \stemDown ces4. \stemUp c,4. | % 4
    \stemUp g'4 r8 r4 r8 | % 5
    R2.*3 \bar "||"
    }

PartPOneFourVoiceOne =  \relative d'' {
    \clef "treble" \time 6/8 \key d \major \transposition bes | % 1
    \stemDown d4. ~ _\f \stemDown d8 r4 | % 2
    R2.*6 \bar "||"
    }

PartPOneFiveVoiceOne =  \relative d' {
    \clef "treble" \time 6/8 \key d \major \transposition bes | % 1
    \stemUp d4. ~ _\f \stemUp d8 r4 | % 2
    R2.*6 \bar "||"
    }

PartPOneSixVoiceOne =  \relative c {
    \clef "bass" \time 6/8 \key es \major | % 1
    \stemUp c8 [ _\f \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ] | % 2
    \stemUp c8 [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8 \stemUp
    c8 ] | % 3
    \stemUp c8 [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8 \stemUp
    c8 ] | % 4
    \stemUp c8 [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8 \stemUp
    c8 ] | % 5
    \stemUp c8 [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8 \stemUp
    c8 ] | % 6
    \stemUp c8 [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8 \stemUp
    c8 ] | % 7
    \stemUp c8 [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8 \stemUp
    c8 ] \bar "||"
    }

PartPOneSevenVoiceOne =  \relative c''' {
    \clef "treble" \time 6/8 \key es \major | % 1
    \stemDown c4. ( ~ _\f \stemDown c4 -\markup{ \italic {espr. e
            legato} } \stemDown cis8 ~ | % 2
    \stemDown cis4 \stemDown d8 ~ \stemDown d8. [ \stemDown es16
    \stemDown f16 ) \stemDown g16 ~ ] | % 3
    \stemDown g4 ( \stemDown as8 ~ \stemDown as4 \stemDown a8 ~ | % 4
    \stemDown a4 \stemDown bes8 ~ \stemDown bes4 \stemDown as8 ) ~ | % 5
    \stemDown as8. ( [ \stemDown g16 \stemDown g,16 \stemDown d'16 ]
    \stemDown g4 \stemDown f8 ) ~ | % 6
    \stemDown f8. ( [ \stemDown es16 \stemDown es,16 \stemDown c'16 ]
    \stemDown es4 \stemDown d8 ) ~ | % 7
    \stemDown d16 ( [ \stemDown c16 \stemDown d,16 \stemDown as'16
    \stemDown c8 ~ ] \stemDown c16 [ \stemDown bes16 \stemDown d,16
    \stemDown g16 \stemDown bes8 ) ~ ] \bar "||"
    }

PartPOneSevenVoiceOneLyricsOne =  \lyricmode {\set ignoreMelismata = ##t
    a\skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 a\skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1 \skip1
    \skip1
    }

PartPOneEightVoiceOne =  \relative c'' {
    \clef "treble" \time 6/8 \key es \major | % 1
    \stemDown c4. ( ~ _\f \stemDown c4 -\markup{ \italic {espr. e
            legato} } \stemDown cis8 ~ | % 2
    \stemDown cis4 \stemDown d8 ~ \stemDown d8. [ \stemDown es16
    \stemDown f16 ) \stemDown g16 ~ ] | % 3
    \stemDown g4 ( \stemDown as8 ~ \stemDown as4 \stemDown a8 ~ | % 4
    \stemDown a4 \stemDown bes8 ~ \stemDown bes4 \stemDown as8 ) ~ | % 5
    \stemDown as8. ( [ \stemDown g16 \stemDown g,16 \stemDown d'16 ]
    \stemDown g4 \stemDown f8 ) ~ | % 6
    \stemDown f8. ( [ \stemDown es16 \stemDown es,16 \stemDown c'16 ]
    \stemDown es4 \stemDown d8 ) ~ | % 7
    \stemUp d16 ( [ \stemUp c16 \stemUp d,16 \stemUp as'16 \stemUp c8 ~
    ] \stemUp c16 [ \stemUp bes16 \stemUp d,16 \stemUp g16 \stemUp bes8
    ) ~ ] \bar "||"
    }

PartPOneNineVoiceOne =  \relative c' {
    \clef "alto" \time 6/8 \key es \major | % 1
    \stemDown <c c'>4. ( _\f \stemDown <g' bes>4. -\markup{ \italic
        {espr. e legato} } | % 2
    \stemDown <fis a>4. \stemDown <f as>4 \stemDown <f as>8 ) | % 3
    \stemDown <d f>4. ( \stemDown <c es>4. | % 4
    \stemDown <bes d>4. \stemDown <bes d>8 [ \stemDown <c es>8 \stemDown
    <d f>8 ) ] | % 5
    \stemDown <b d>4. ( \stemDown <b d>8 [ \stemDown <c es>8 \stemDown
    <d f>8 ) ] | % 6
    \stemDown <es g>4. ( \stemDown <es g>8 [ \stemDown <f as>8 \stemDown
    <g bes>8 ) ] | % 7
    \stemDown <as, c'>4 ( \stemDown <bes d'>8 \stemDown <c e'>4
    \stemDown <d f'>8 ) \bar "||"
    }

PartPTwoZeroVoiceOne =  \relative c' {
    \clef "tenor" \time 6/8 \key es \major | % 1
    \stemDown c4. ( ~ _\f \stemDown c4 -\markup{ \italic {espr. e
            legato} } \stemDown cis8 ~ | % 2
    \stemDown cis4 \stemDown d8 ~ \stemDown d8. [ \stemDown es16
    \stemDown f16 ) \stemDown g16 ~ ] | % 3
    \stemDown g4 ( \stemDown as8 ~ \stemDown as4 \stemDown a8 ~ | % 4
    \stemDown a4 \stemDown bes8 ~ \stemDown bes4 \stemDown as8 ) ~ | % 5
    \stemDown as8. ( [ \stemDown g16 \stemDown g,16 \stemDown d'16 ]
    \stemDown g4 \stemDown f8 ) ~ | % 6
    \stemDown f8. ( [ \clef "bass" \stemDown es16 \stemDown es,16
    \stemDown c'16 ] \stemDown es4 \stemDown d8 ) ~ | % 7
    \stemDown d16 ( [ \stemDown c16 \stemDown c,16 \stemDown as'16
    \stemDown c8 ~ ] \stemDown c16 [ \stemDown bes16 \stemDown c,16
    \stemDown g'16 \stemDown bes8 ) ~ ] \bar "||"
    }

PartPTwoOneVoiceOne =  \relative c {
    \clef "bass" \time 6/8 \key es \major \transposition c | % 1
    \stemUp c8 ( [ _\f \stemUp c8 \stemUp c8 ] -\markup{ \italic
        {pesante} } \stemUp c8 [ \stemUp c8 \stemUp c8 ) ] | % 2
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 3
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 4
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 5
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 6
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] | % 7
    \stemUp c8 ( [ \stemUp c8 \stemUp c8 ] \stemUp c8 [ \stemUp c8
    \stemUp c8 ) ] \bar "||"
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
            \set Staff.instrumentName = "Contrabassoon"
            \set Staff.shortInstrumentName = "C Bsn"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPNineVoiceOne" {  \PartPNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Horn 1"
            \set Staff.shortInstrumentName = "Hn 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneZeroVoiceOne" {  \PartPOneZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Horn 2"
            \set Staff.shortInstrumentName = "Hn 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneOneVoiceOne" {  \PartPOneOneVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Eb Horn 3"
            \set Staff.shortInstrumentName = "Hn 3"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneTwoVoiceOne" {  \PartPOneTwoVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Eb Horn 4"
            \set Staff.shortInstrumentName = "Hn 4"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneThreeVoiceOne" {  \PartPOneThreeVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Trumpet 1"
            \set Staff.shortInstrumentName = "Tpt 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFourVoiceOne" {  \PartPOneFourVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "C Trumpet 2"
            \set Staff.shortInstrumentName = "Tpt 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneFiveVoiceOne" {  \PartPOneFiveVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Timpani"
            \set Staff.shortInstrumentName = "Timp"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSixVoiceOne" {  \PartPOneSixVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 1"
            \set Staff.shortInstrumentName = "Vln 1"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneSevenVoiceOne" {  \PartPOneSevenVoiceOne }
                \new Lyrics \lyricsto "PartPOneSevenVoiceOne" { \set stanza = "1." \PartPOneSevenVoiceOneLyricsOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violin 2"
            \set Staff.shortInstrumentName = "Vln 2"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneEightVoiceOne" {  \PartPOneEightVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Viola"
            \set Staff.shortInstrumentName = "Vla"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPOneNineVoiceOne" {  \PartPOneNineVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Violoncello"
            \set Staff.shortInstrumentName = "Vc"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoZeroVoiceOne" {  \PartPTwoZeroVoiceOne }
                >>
            >>
        \new Staff
        <<
            \set Staff.instrumentName = "Contrabass"
            \set Staff.shortInstrumentName = "Cb"
            
            \context Staff << 
                \mergeDifferentlyDottedOn\mergeDifferentlyHeadedOn
                \context Voice = "PartPTwoOneVoiceOne" {  \PartPTwoOneVoiceOne }
                >>
            >>
        
        >>
    \layout {}
    % To create MIDI output, uncomment the following line:
    %  \midi {\tempo 4 = 48 }
    }

