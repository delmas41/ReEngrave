# System-grouping sweep summary

Build-agent run, 2026-09-01. Layout-only (no YOLO): `render_page` + `detect_staves`
+ `system_grouping.gap_bridging_counts`/`_x_overlap_frac`, called directly — the
rule itself was not touched. Companion outputs in this directory:
`eval_grouping_reproduction.txt` (harness sanity check), `gt/gt.json` +
`verdicts.jsonl` + `SCORE_ROLLUP.md` (partition-level scoring against every free
GT source), `anomaly_shortlist.json` + `crops/` (adjudication artifacts).

**Harness sanity check.** `eval_grouping.py` run unchanged (output captured
verbatim in `eval_grouping_reproduction.txt`): **connectivity 20/23 (87%), gap
heuristic 7/23 (30%), 0 spurious single-staff systems** — reproduces repo-state.md
exactly. `score.py`'s independent GT import+scoring (41 cases from 3 source files,
see `SCORE_ROLLUP.md`) lands on the identical count (`count_agree=20/23`) and
identifies the same three failing pages (B9 p25, B9 p60, B5 p40) both by count
(`count_differ`) and by partition (`we_merge`, via `probes/fulldist.py`'s
break-index GT) — three independent readings of this codebase agree exactly,
which is the cross-check this build was asked to set up.

**The library corpus was live during this session, not a fixed snapshot.**
Discovered PDF count grew 122 (repo-state.md, research time) -> 175 (sweep start)
-> 235 (sweep end) while another process ingested/renamed editions concurrently.
Two consequences, both handled by the resumable design rather than worked around:
(1) 4 rows show a stale `FileNotFoundError` for
`lalo/symphonie-espagnole-op21/...imslp174510.pdf`, mid-sweep renamed on disk to
`lalo/symphony-espagnole-op21/...` (typo fix) — the corrected path swept
successfully under its new name a few minutes later (4 fresh rows, `staves` 15-18,
both present in `sweep.jsonl`). (2) 8 of the 60 anomaly-shortlist crops failed for
the same reason (`durand`/lalo, plus a `manuscript`-edition Berlioz Symphonie
Fantastique — imslp412097 — that was removed from the corpus entirely, apparently
superseded by a `berliozcomplete-1900` edition already present under a different
imslp id) — **52/60 crops generated**; the 8 failures are listed with their exact
error in the shortlist table below and were not chased further given the corpus
kept moving. None of this affects the 235-PDF sweep's validity as of completion;
it means a re-run today will discover a different (larger) PDF count.

Source: `sweep.jsonl` — 977 page rows (973 ok, 4 error, the stale Lalo path above).
Sum of per-page `runtime_s` (serial, single process): 681s (~11.3 min) for this
file's total accumulated work; the final complete-corpus pass alone (804 fresh
pages after 235 PDFs were discovered) ran in 558s wall clock.

## Publisher histogram (swept pages)

| publisher_token | pages swept | errors |
|---|--:|--:|
| breitkopf-und-hartel | 56 | 0 |
| breitkopf-hartel-mozart-1880 | 54 | 0 |
| henry-litolff-s-verlag-1870 | 40 | 0 |
| eulenburg | 40 | 0 |
| peters | 24 | 0 |
| breitkopf-hartel-brahms | 24 | 0 |
| breitkopf-hartel-mozart-1879 | 24 | 0 |
| barenreiter-neue-mozart-1960 | 19 | 0 |
| breitkopf-und-hartel-1855 | 16 | 0 |
| durand | 16 | 4 |
| breitkopf-hartel-beethov-1862 | 12 | 0 |
| co-issue-with-universal | 12 | 0 |
| wiener-philharmonischer | 12 | 0 |
| jurgenson | 12 | 0 |
| simrock-1881 | 8 | 0 |
| durand-fils | 8 | 0 |
| breitkopf-und-hartel-1857 | 8 | 0 |
| breitkopf-und-hartel-1854 | 8 | 0 |
| goodwin-tabb-1921 | 8 | 0 |
| unknown-edition | 8 | 0 |
| edition-1912 | 8 | 0 |
| edition-1906 | 8 | 0 |
| mendelssohncomplete-1877 | 8 | 0 |
| breitkopf-hartel-mozart-1878 | 8 | 0 |
| breitkopf-hartel-s-parti | 8 | 0 |
| durand-1875 | 8 | 0 |
| schubertcomplete-1884 | 8 | 0 |
| schumanncomplete-1883 | 8 | 0 |
| peters-1887 | 8 | 0 |
| ricordi | 8 | 0 |
| simrock-1878 | 4 | 0 |
| bachcomplete-1871 | 4 | 0 |
| edition-peters-nr-4412 | 4 | 0 |
| peters-1851 | 4 | 0 |
| breitkopf-hartels-partit | 4 | 0 |
| edition-peters-nr-4415 | 4 | 0 |
| snortum-2024 | 4 | 0 |
| breitkopf-und-hartel-1899 | 4 | 0 |
| arthur-p-schmidt-1897 | 4 | 0 |
| simrock-1847 | 4 | 0 |
| schott-1827 | 4 | 0 |
| breitkopf-hartel-beethov | 4 | 0 |
| eulenburg-1899 | 4 | 0 |
| berliozcomplete-1901 | 4 | 0 |
| manuscript | 4 | 0 |
| berliozcomplete-1900 | 4 | 0 |
| rahter | 4 | 0 |
| v-bessel-co-1888 | 4 | 0 |
| simrock-1882 | 4 | 0 |
| simrock-1874 | 4 | 0 |
| simrock-1879 | 4 | 0 |
| bruckneraga-1935 | 4 | 0 |
| eulenburg-1926 | 4 | 0 |
| enoch-1884 | 4 | 0 |
| enoch-cie-1902 | 4 | 0 |
| catalog-part-b-2051-2051 | 4 | 0 |
| novello | 4 | 0 |
| durand-et-cie-1913 | 4 | 0 |
| fromont | 4 | 0 |
| simrock-1896 | 4 | 0 |
| schirmer-s-library-of-mu | 4 | 0 |
| simrock-1888 | 4 | 0 |
| simrock-1885 | 4 | 0 |
| novello-1892 | 4 | 0 |
| simrock-1894 | 4 | 0 |
| novello-co-1921 | 4 | 0 |
| novello-and-co-1905 | 4 | 0 |
| novello-co-1908 | 4 | 0 |
| novello-co-1899 | 4 | 0 |
| peters-1979 | 4 | 0 |
| hamelle-1901 | 4 | 0 |
| hamelle-1890 | 4 | 0 |
| peters-1884 | 4 | 0 |
| peters-1888 | 4 | 0 |
| lead-sheet | 4 | 0 |
| vocal-reduction | 4 | 0 |
| linkwork-1874 | 4 | 0 |
| breitkopf-hartels-orches | 4 | 0 |
| goodwin-tabb-1922 | 4 | 0 |
| weinberger-1897 | 4 | 0 |
| hofmeister-1897 | 4 | 0 |
| edition-1911 | 4 | 0 |
| unidentified-scan-2016 | 4 | 0 |
| c-f-kahnt-nachfolger-1906 | 4 | 0 |
| bote-bock-1909 | 4 | 0 |
| breitkopf-und-hartel-1842 | 4 | 0 |
| breitkopf-hartel-mozart-1881 | 4 | 0 |
| simrock | 4 | 0 |
| breitkopf-und-hartel-1801 | 4 | 0 |
| breitkopf-und-hartel-1812 | 4 | 0 |
| eulenburg-1956 | 4 | 0 |
| v-bessel-co-1886 | 4 | 0 |
| augener-1914 | 4 | 0 |
| hansen-1916 | 4 | 0 |
| editions-russes-de-musiq-1925 | 4 | 0 |
| gutheil-1909 | 4 | 0 |
| gutheil-1908 | 4 | 0 |
| 2016 | 4 | 0 |
| durand-fils-1908 | 4 | 0 |
| g-ricordi-c-1925 | 4 | 0 |
| belaieff | 4 | 0 |
| breitkopf-hartel | 4 | 0 |
| durand-schoenewerk-1886 | 4 | 0 |
| schubertcomplete-1893 | 4 | 0 |
| schubertcomplete-1885 | 4 | 0 |
| breitkopf-und-hartel-1850 | 4 | 0 |
| breitkopf-und-hartel-1891 | 4 | 0 |
| breitkopf-und-hartel-1905 | 4 | 0 |
| breitkopf-und-hartel-1902 | 4 | 0 |
| breitkopf-und-hartel-fro-1905 | 4 | 0 |
| hansen-1921 | 4 | 0 |
| hansen-1925 | 4 | 0 |
| breitkopf-hartel-1901 | 4 | 0 |
| lienau-1905 | 4 | 0 |
| p2 | 4 | 0 |
| snklhu-1953 | 4 | 0 |
| eulenburg-1920 | 4 | 0 |
| jos-aibl-verlag | 4 | 0 |
| jos-aibl-verlag-1898 | 4 | 0 |
| leuckart-1899 | 4 | 0 |
| furstner-1916 | 4 | 0 |
| aibl-1896 | 4 | 0 |
| aibl-1891 | 4 | 0 |
| jurgenson-1911 | 4 | 0 |
| jurgenson-1882 | 4 | 0 |
| ed-bote-g-bock-1881 | 4 | 0 |
| jurgenson-1881 | 4 | 0 |
| jurgenson-1875 | 4 | 0 |
| bessel-1881 | 4 | 0 |
| breitkopf-hartel-1930 | 4 | 0 |
| jurgenson-1892 | 4 | 0 |
| jurgenson-1888 | 4 | 0 |
| oxford-university-press-1925 | 4 | 0 |
| univerzitet-umetnosti-u | 4 | 0 |
| breitkopf-und-hartel-1688 | 4 | 0 |
| edition-1935 | 4 | 0 |
| bote-bock-1879 | 4 | 0 |
| novello-co-1911 | 4 | 0 |
| renioult-2025 | 4 | 0 |
| john-s-shaw-2024 | 4 | 0 |
| belaieff-1896 | 4 | 0 |
| nielsencomplete-1998 | 4 | 0 |
| gutheil-1901 | 4 | 0 |
| durand-cie-1921 | 4 | 0 |
| durand-cie-1918 | 4 | 0 |
| b-schott-s-sohne-1924 | 4 | 0 |
| durand-1874 | 4 | 0 |
| chang-2019 | 4 | 0 |
| leuckart-1915 | 4 | 0 |
| 535915 | 4 | 0 |
| peters-1920 | 4 | 0 |
| breitkopf-und-hartel-1860 | 4 | 0 |

## K.183 cross-publisher pair

Two different ENGRAVINGS (not two scans of the same plate) — page index is NOT content-aligned between columns. Listed side by side by row order only, for a quick visual scan of each publisher's layout tendency.

- A = `mozart/symphony-25-in-g-minor-k183-173db/mozart--symphony-25-in-g-minor-k183-173db--barenreiter-neue-mozart-1960--imslp849180.pdf`
- B = `mozart/symphony-25-in-g-minor-k183/mozart--symphony-25-in-g-minor-k183--breitkopf-hartel-mozart-1880--imslp57.pdf`

| A: page | A: staves | A: systems (sizes) | B: page | B: staves | B: systems (sizes) |
|--:|--:|---|--:|--:|---|
| 1 | 24 | [8, 8, 8] | 1 | 21 | [7, 7, 7] |
| 2 | 24 | [8, 8, 8] | 2 | 21 | [7, 7, 7] |
| 3 | 24 | [8, 8, 8] | 3 | 21 | [7, 7, 7] |
| 4 | 24 | [8, 8, 8] | 4 | 21 | [7, 7, 7] |
| 5 | 23 | [7, 8, 8] | 5 | 21 | [7, 7, 7] |
| 6 | 24 | [8, 8, 8] | 6 | 21 | [7, 7, 7] |
| 7 | 24 | [8, 8, 8] | 7 | 21 | [7, 7, 7] |
| 8 | 24 | [8, 8, 8] | 8 | 21 | [7, 7, 7] |
| 9 | 21 | [7, 7, 7] | 9 | 21 | [7, 7, 7] |
| 10 | 21 | [7, 7, 7] | 10 | 21 | [7, 7, 7] |
| 11 | 21 | [7, 7, 7] | 11 | 22 | [7, 7, 4, 4] |
| 12 | 22 | [7, 7, 4, 4] | 12 | 21 | [7, 7, 7] |
| 13 | 24 | [8, 8, 8] | 13 | 20 | [6, 7, 7] |
| 14 | 24 | [8, 8, 8] | 14 | 21 | [7, 7, 7] |
| 15 | 24 | [8, 8, 8] | 15 | 21 | [7, 7, 7] |
| 16 | 24 | [8, 8, 8] | 16 | 21 | [7, 7, 7] |
| 17 | 24 | [8, 8, 8] | 17 | 21 | [7, 7, 7] |
| 18 | 24 | [8, 8, 8] | 18 | 21 | [7, 7, 7] |
| 19 | 22 | [7, 7, 8] |  |  |  |

## Same-plate scan-variance pairs

### beethoven5-scan-pair

4 shared pages compared, 3 disagreement(s).

| page | kind | sizes (scan A) | sizes (scan B) |
|--:|---|---|---|
| 13 | system count agrees, staff sizes differ | [12, 11] | [11, 11] |
| 35 | system count agrees, staff sizes differ | [11, 9] | [11, 10] |
| 57 | system-count differs | [17] | [9, 15] |

### brahms1-scan-pair

4 shared pages compared, 2 disagreement(s).

| page | kind | sizes (scan A) | sizes (scan B) |
|--:|---|---|---|
| 34 | system count agrees, staff sizes differ | [12, 12] | [13, 13] |
| 56 | system count agrees, staff sizes differ | [9, 14] | [7, 14] |

### mozart41-scan-pair

4 shared pages compared, 0 disagreement(s).


## Anomaly shortlist

68 pages matched at least one flag; 60 selected below (cap 60, round-robin across flags a-f so no single flag crowds out the others). Full row data (for `make_crops.py --input`): `/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/system-break-rule-publishers-62ead4/benchmarks/omr-system-grouping-2026-09/anomaly_shortlist.json`.

Flags: (a) error or zero staves; (b) size-1 system next to a >=5-staff system; (c) max/min system-size ratio >= 3; (d) >=5 systems with median size >= 4; (e) gap-heuristic fallback fired (used_bridging=False); (f) scan-pair disagreement

| # | publisher_token | pdf | page | flags | reason |
|--:|---|---|--:|---|---|
| 1 | eulenburg | ...-concerto-1-in-f-major-bwv1046--eulenburg--imslp47820.pdf | 4 | a | error or zero staves: zero staves detected |
| 2 | edition-peters-nr-4412 | ...-g-major-bwv1048--edition-peters-nr-4412--imslp468678.pdf | 16 | b,c | size-1 system next to a >=5-staff system: sizes=[11, 2, 3, 3, 1, 2] / max/min system-size ratio >= 3: sizes=[11, 2, 3, 3, 1, 2] (ratio 11.0) |
| 3 | simrock-1878 | ...p73/brahms--symphony-2-op73--simrock-1878--imslp23103.pdf | 29 | c | max/min system-size ratio >= 3: sizes=[23, 4] (ratio 5.8) |
| 4 | simrock-1878 | ...p73/brahms--symphony-2-op73--simrock-1878--imslp23103.pdf | 47 | d | >=5 systems with median size >= 4: 6 systems, median 4.0: sizes=[4, 2, 5, 4, 2, 5] |
| 5 | henry-litolff-s-verlag-1870 | ...hony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf | 13 | f | scan-pair disagreement: see scan-pair table |
| 6 | edition-peters-nr-4415 | ...at-major-bwv1051--edition-peters-nr-4415--imslp468681.pdf | 4 | a | error or zero staves: zero staves detected |
| 7 | berliozcomplete-1901 | ...arnaval-romain-h-95--berliozcomplete-1901--imslp11357.pdf | 7 | b,c | size-1 system next to a >=5-staff system: sizes=[10, 7, 1, 2] / max/min system-size ratio >= 3: sizes=[10, 7, 1, 2] (ratio 10.0) |
| 8 | breitkopf-und-hartel | ...hoven--egmont-op84--breitkopf-und-hartel--imslp807970.pdf | 74 | c | max/min system-size ratio >= 3: sizes=[13, 9, 4] (ratio 3.2) |
| 9 | henry-litolff-s-verlag-1870 | ...hony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf | 35 | f | scan-pair disagreement: see scan-pair table |
| 10 | manuscript | ...--symphonie-fantastique-h-48--manuscript--imslp412097.pdf | 247 | a | error or zero staves: zero staves detected |
| 11 | manuscript | ...--symphonie-fantastique-h-48--manuscript--imslp412097.pdf | 57 | b,c | size-1 system next to a >=5-staff system: sizes=[1, 12, 1, 1] / max/min system-size ratio >= 3: sizes=[1, 12, 1, 1] (ratio 12.0) |
| 12 | breitkopf-hartel-beethov-1862 | ...to-5-op73--breitkopf-hartel-beethov-1862--imslp977419.pdf | 13 | c | max/min system-size ratio >= 3: sizes=[2, 6, 9] (ratio 4.5) |
| 13 | henry-litolff-s-verlag-1870 | ...hony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf | 57 | f | scan-pair disagreement: see scan-pair table |
| 14 | manuscript | ...--symphonie-fantastique-h-48--manuscript--imslp412097.pdf | 342 | a | error or zero staves: zero staves detected |
| 15 | manuscript | ...--symphonie-fantastique-h-48--manuscript--imslp412097.pdf | 152 | b,c | size-1 system next to a >=5-staff system: sizes=[1, 16, 1, 1] / max/min system-size ratio >= 3: sizes=[1, 16, 1, 1] (ratio 16.0) |
| 16 | breitkopf-hartel-beethov-1862 | ...to-5-op73--breitkopf-hartel-beethov-1862--imslp977419.pdf | 35 | c | max/min system-size ratio >= 3: sizes=[9, 9, 2] (ratio 4.5) |
| 17 | henry-litolff-s-verlag-1870 | ...hony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf | 13 | f | scan-pair disagreement: see scan-pair table |
| 18 | rahter | ...-in-the-steppes-of-central-asia--rahter--imslp1043848.pdf | 18 | a | error or zero staves: zero staves detected |
| 19 | v-bessel-co-1888 | ...-2/borodin--symphony-2--v-bessel-co-1888--imslp197128.pdf | 62 | b,c | size-1 system next to a >=5-staff system: sizes=[1, 18] / max/min system-size ratio >= 3: sizes=[1, 18] (ratio 18.0) |
| 20 | v-bessel-co-1888 | ...-2/borodin--symphony-2--v-bessel-co-1888--imslp197128.pdf | 23 | c | max/min system-size ratio >= 3: sizes=[12, 4] (ratio 3.0) |
| 21 | henry-litolff-s-verlag-1870 | ...hony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf | 35 | f | scan-pair disagreement: see scan-pair table |
| 22 | durand | ...1/lalo--symphonie-espagnole-op21--durand--imslp174510.pdf | 22 | a | error or zero staves: FileNotFoundError: no such file: '/Users/seanjohnson/Desktop/ReEngrave/library/editions/lalo/symphonie-espagnole-op21/lalo--symphonie-espa |
| 23 | simrock-1882 | ...hms--piano-concerto-2-op83--simrock-1882--imslp145434.pdf | 64 | b,c | size-1 system next to a >=5-staff system: sizes=[14, 1] / max/min system-size ratio >= 3: sizes=[14, 1] (ratio 14.0) |
| 24 | simrock-1882 | ...hms--piano-concerto-2-op83--simrock-1882--imslp145434.pdf | 24 | c | max/min system-size ratio >= 3: sizes=[15, 2] (ratio 7.5) |
| 25 | henry-litolff-s-verlag-1870 | ...hony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf | 57 | f | scan-pair disagreement: see scan-pair table |
| 26 | durand | ...1/lalo--symphonie-espagnole-op21--durand--imslp174510.pdf | 59 | a | error or zero staves: FileNotFoundError: no such file: '/Users/seanjohnson/Desktop/ReEngrave/library/editions/lalo/symphonie-espagnole-op21/lalo--symphonie-espa |
| 27 | eulenburg | ...ab-45/bruckner--te-deum-wab-45--eulenburg--imslp62720.pdf | 5 | b,c | size-1 system next to a >=5-staff system: sizes=[1, 2, 10, 1, 8] / max/min system-size ratio >= 3: sizes=[1, 2, 10, 1, 8] (ratio 10.0) |
| 28 | enoch-1884 | ...rier/espana/chabrier--espana--enoch-1884--imslp112203.pdf | 42 | c | max/min system-size ratio >= 3: sizes=[20, 6] (ratio 3.3) |
| 29 | breitkopf-hartel-brahms | ...symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf | 34 | f | scan-pair disagreement: see scan-pair table |
| 30 | durand | ...1/lalo--symphonie-espagnole-op21--durand--imslp174510.pdf | 96 | a | error or zero staves: FileNotFoundError: no such file: '/Users/seanjohnson/Desktop/ReEngrave/library/editions/lalo/symphonie-espagnole-op21/lalo--symphonie-espa |
| 31 | eulenburg | ...ab-45/bruckner--te-deum-wab-45--eulenburg--imslp62720.pdf | 13 | b,c | size-1 system next to a >=5-staff system: sizes=[1, 1, 1, 5, 1, 7, 1, 1, 1, 2] / max/min system-size ratio >= 3: sizes=[1, 1, 1, 5, 1, 7, 1, 1, 1, 2] (ratio 7.0 |
| 32 | durand-et-cie-1913 | ...ite-a-joujoux-cd-136--durand-et-cie-1913--imslp199718.pdf | 43 | c | max/min system-size ratio >= 3: sizes=[3, 1, 2, 2] (ratio 3.0) |
| 33 | breitkopf-hartel-brahms | ...symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf | 56 | f | scan-pair disagreement: see scan-pair table |
| 34 | durand | ...1/lalo--symphonie-espagnole-op21--durand--imslp174510.pdf | 132 | a | error or zero staves: FileNotFoundError: no such file: '/Users/seanjohnson/Desktop/ReEngrave/library/editions/lalo/symphonie-espagnole-op21/lalo--symphonie-espa |
| 35 | eulenburg | ...ab-45/bruckner--te-deum-wab-45--eulenburg--imslp62720.pdf | 21 | b,c | size-1 system next to a >=5-staff system: sizes=[2, 1, 2, 1, 2, 1, 4, 1, 7, 2] / max/min system-size ratio >= 3: sizes=[2, 1, 2, 1, 2, 1, 4, 1, 7, 2] (ratio 7.0 |
| 36 | schirmer-s-library-of-mu | ...ic-dances-op46--schirmer-s-library-of-mu--imslp147746.pdf | 36 | c | max/min system-size ratio >= 3: sizes=[2, 6, 2, 2] (ratio 3.0) |
| 37 | breitkopf-hartel-brahms | ...symphony-1-op68--breitkopf-hartel-brahms--imslp516790.pdf | 34 | f | scan-pair disagreement: see scan-pair table |
| 38 | breitkopf-und-hartel | ...-die-hebriden-op26--breitkopf-und-hartel--imslp683560.pdf | 8 | a | error or zero staves: zero staves detected |
| 39 | eulenburg | ...ab-45/bruckner--te-deum-wab-45--eulenburg--imslp62720.pdf | 30 | b,c | size-1 system next to a >=5-staff system: sizes=[3, 1, 1, 1, 4, 1, 2, 1, 5, 1] / max/min system-size ratio >= 3: sizes=[3, 1, 1, 1, 4, 1, 2, 1, 5, 1] (ratio 5.0 |
| 40 | breitkopf-und-hartel | ...-music-hwv-348-350--breitkopf-und-hartel--imslp780551.pdf | 26 | c | max/min system-size ratio >= 3: sizes=[10, 2, 4, 2, 2] (ratio 5.0) |
| 41 | breitkopf-hartel-brahms | ...symphony-1-op68--breitkopf-hartel-brahms--imslp516790.pdf | 56 | f | scan-pair disagreement: see scan-pair table |
| 42 | breitkopf-und-hartel | ...-die-hebriden-op26--breitkopf-und-hartel--imslp683560.pdf | 22 | a | error or zero staves: zero staves detected |
| 43 | breitkopf-und-hartel | ...-die-hebriden-op26--breitkopf-und-hartel--imslp683560.pdf | 35 | b,c | size-1 system next to a >=5-staff system: sizes=[5, 7, 1, 1] / max/min system-size ratio >= 3: sizes=[5, 7, 1, 1] (ratio 7.0) |
| 44 | peters | ...ht-s-dream-incidental-music-op61--peters--imslp225827.pdf | 92 | c | max/min system-size ratio >= 3: sizes=[7, 2, 7] (ratio 3.5) |
| 45 | breitkopf-hartel-1901 | ...of-tuonela-op22-2--breitkopf-hartel-1901--imslp255071.pdf | 18 | a | error or zero staves: zero staves detected |
| 46 | simrock | ...20/mozart--die-zauberflote-k620--simrock--imslp923456.pdf | 150 | b,c | size-1 system next to a >=5-staff system: sizes=[9, 7, 1, 1] / max/min system-size ratio >= 3: sizes=[9, 7, 1, 1] (ratio 9.0) |
| 47 | breitkopf-und-hartel-1801 | ...giovanni-k527--breitkopf-und-hartel-1801--imslp433273.pdf | 534 | c | max/min system-size ratio >= 3: sizes=[2, 3, 1, 1, 1, 1, 1] (ratio 3.0) |
| 48 | b-schott-s-sohne-1924 | ...ante-defunte-m-19--b-schott-s-sohne-1924--imslp617507.pdf | 1 | a | error or zero staves: zero staves detected |
| 49 | breitkopf-und-hartel-1801 | ...giovanni-k527--breitkopf-und-hartel-1801--imslp433273.pdf | 385 | b,c | size-1 system next to a >=5-staff system: sizes=[3, 1, 7, 1, 2] / max/min system-size ratio >= 3: sizes=[3, 1, 7, 1, 2] (ratio 7.0) |
| 50 | breitkopf-hartel-mozart-1878 | ...-minor-k466--breitkopf-hartel-mozart-1878--imslp26334.pdf | 36 | c | max/min system-size ratio >= 3: sizes=[10, 2, 12] (ratio 6.0) |
| 51 | breitkopf-hartel-mozart-1879 | ...igaro-k492--breitkopf-hartel-mozart-1879--imslp515701.pdf | 278 | b,c | size-1 system next to a >=5-staff system: sizes=[8, 6, 1, 1] / max/min system-size ratio >= 3: sizes=[8, 6, 1, 1] (ratio 8.0) |
| 52 | breitkopf-hartel-mozart-1878 | ...major-k467--breitkopf-hartel-mozart-1878--imslp516497.pdf | 8 | c | max/min system-size ratio >= 3: sizes=[2, 6, 6, 9] (ratio 4.5) |
| 53 | breitkopf-hartel-mozart-1880 | ...major-k543--breitkopf-hartel-mozart-1880--imslp984554.pdf | 29 | b,c | size-1 system next to a >=5-staff system: sizes=[10, 9, 1] / max/min system-size ratio >= 3: sizes=[10, 9, 1] (ratio 10.0) |
| 54 | breitkopf-hartel-mozart-1880 | ...minor-k550--breitkopf-hartel-mozart-1880--imslp984555.pdf | 32 | c | max/min system-size ratio >= 3: sizes=[2, 8, 11] (ratio 5.5) |
| 55 | eulenburg-1920 | ...so-sprach-zarathustra-op30--eulenburg-1920--imslp8190.pdf | 143 | b,c | size-1 system next to a >=5-staff system: sizes=[12, 1, 11] / max/min system-size ratio >= 3: sizes=[12, 1, 11] (ratio 12.0) |
| 56 | gutheil-1908 | ...hmaninoff--symphony-2-op27--gutheil-1908--imslp105597.pdf | 92 | c | max/min system-size ratio >= 3: sizes=[3, 8, 12] (ratio 4.0) |
| 57 | univerzitet-umetnosti-u | ...dal--178-basses--univerzitet-umetnosti-u--imslp756089.pdf | 55 | b,c,e | size-1 system next to a >=5-staff system: sizes=[1, 3, 5, 1] / max/min system-size ratio >= 3: sizes=[1, 3, 5, 1] (ratio 5.0) / gap-heuristic fallback fired (us |
| 58 | durand-1875 | ...saens--piano-concerto-2-op22--durand-1875--imslp21451.pdf | 72 | c | max/min system-size ratio >= 3: sizes=[7, 2, 4] (ratio 3.5) |
| 59 | jurgenson-1875 | ...ikovsky--symphony-1-op13--jurgenson-1875--imslp369941.pdf | 49 | c | max/min system-size ratio >= 3: sizes=[12, 4, 3, 5] (ratio 4.0) |
| 60 | univerzitet-umetnosti-u | ...dal--178-basses--univerzitet-umetnosti-u--imslp756089.pdf | 21 | c,e | max/min system-size ratio >= 3: sizes=[1, 1, 2, 1, 4, 1] (ratio 4.0) / gap-heuristic fallback fired (used_bridging=False) |

