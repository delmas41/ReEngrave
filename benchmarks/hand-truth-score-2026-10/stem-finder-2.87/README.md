# 2.87 stem finder: raw scorer output

`python3 -m tools.omr.hand_truth.score` on Sean's Brahms 317803 pdf 0, the source of every number in
`../FINDINGS.md` section 9. The records they score (3.4 GB) are machine-local and not committed.

| file | record | hand truth |
|---|---|---|
| `base-score.*` | base gather, origin/main `40ab373a` | 227 stems |
| `final-base.score.*` | base, clean | 227 stems |
| `final-f0.score.*` | `42b28f31`, `OMR_STEM_FINDER` set empty (control: identical to base) | 227 stems |
| `final-f1.score.*` | `42b28f31`, four GATHER repairs on | 227 stems |
| `truth7-base.score.txt` / `truth7-f1.score.txt` | base / f1 | 234 stems (Sean's 7 added) |
| `dflt.score.txt` | `219301ba`, switch UNSET = the staged default (landed) | 234 stems |
