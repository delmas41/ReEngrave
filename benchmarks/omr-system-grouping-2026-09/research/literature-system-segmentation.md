# OMR literature on system segmentation (Phase 1C, part 1)

2026-09-01. Literature survey (sub-agent of the conventions research agent).
Claims tagged by the surveyor: [STATED] = read in the paper's own text,
[INFERRED] = arithmetic/reasoning over stated facts, [NOT FOUND] = searched,
unverified. Condensed here; full survey in the session transcript.

## The two findings that matter most

**1. No published work reports system-segmentation / staff-grouping accuracy on
orchestral or conductor's scores.** [INFERRED from corpus arithmetic + STATED
author admissions] The layout-analysis benchmark corpora average **1.8–3.1
staves per system** (AudioLabs v2 ≈ 2.07 — grand-staff piano; OSLiC ≈ 3.06 —
voice+piano lieder; MUSCIMA++ ≈ 1.82 — handwritten). A conductor's page runs
15–30. The best published "system detection" numbers describe two- and
three-staff systems and have never been shown a 21-staff page. The only paper
with an orchestral corpus (Egozy & Clester 2022) reports **barline** F-scores,
not grouping accuracy, and says itself the field's datasets "tend to focus on
piano pieces or non-orchestral works". The Sheet Music Benchmark's (ISMIR 2025,
our OMR-NED source) densest texture is a string quartet.

**2. No paper isolates publisher, engraver, or edition as the experimental
variable.** [NOT FOUND after systematic search] Every "domain" split in the
literature is handwritten-vs-typeset, one manuscript collection vs another, or
born-digital-vs-scanned. Nobody has run "trained on Breitkopf, tested on
Eulenburg". Sean's publisher-dependence hypothesis is unmeasured in the
published literature — this benchmark would be the first measurement.

Consequence: there is no drop-in method or baseline to adopt; our repo's 20/23
has no published comparator, and our finding that within-system gaps (17–237 px
on Brahms) exceed between-system gaps on piano pages is a direct, quantified
counterexample to the only published grouping heuristic — unanticipated in the
literature.

## The only published grouping heuristic — and it's the one our repo disproved

**Egozy & Clester, "Computer-Assisted Measure Detection in a Music
Score-Following Application", WoRMS 4 (2022)**, arXiv:2211.13285. Classical CV:
deskew → x-projection → staff-line likelihood → **staves grouped into systems
by white space** → per-system y-projection for barlines. [STATED verbatim]:

> "In a typical multi-system score, the left-most edge of the score has a
> vertical line connecting staves into a single system. Therefore, undisturbed
> white space between staves usually indicates the beginning of a new system."

They acknowledge the over-merge failure mode ("accidentally combining two
separate systems into one") and fix it with a **human drag handle**, not an
algorithm. The left-edge connector (systemic barline) is stated as the *reason*
the gap works — never implemented as a detector.

Their orchestral **barline** results are strong and relevant (14 typeset scores,
1,117 pages, 10,053 barlines, total F 0.976; La Mer 0.987, Scheherazade 0.952,
Prokofiev VC2 0.931 the worst) — evidence that per-system projection barline
finding scales to real orchestral scans.

## The one system-as-object detector, with public code

**Dvořák, Hajič jr. & Mayer, "Staff Layout Analysis Using the YOLO Platform",
WoRMS 6 (2024)**, in arXiv:2411.15741; code+models:
github.com/v-dvorak/omr-layout-analysis. YOLOv8m / Faster R-CNN predicting
boxes for **staff, grand staff, system, staff measure, system measure**,
trained on AudioLabs v2 + MUSCIMA++ + OSLiC + negatives (7,013 images).

- In-domain: systems mAP50 0.990 / mAP50-95 **0.986** (YOLOv8m); 0.83 s/page CPU.
- Out-of-domain across *printed* corpora: systems stay 0.95–0.99 mAP50 —
  the most domain-robust class.
- Out-of-domain on *handwritten* MUSCIMA++: systems collapse to mAP50
  **0.19–0.24**. "Out-of-domain layout analysis still has a long way to go."
- [INFERRED] The appearance model breaks, not the grouping logic. And its
  training corpora max ~3 staves/system — transfer to conductor pages untested.

**Possible use for us:** a second-opinion *miner* on our corpus (the LEGATO
pattern — miner, not oracle), likely useful on piano/chamber pages, informative
even in failure on orchestral. Check license before use. Low priority vs. our
own benchmark.

## Datasets — who annotates systems at all

| Dataset | Staff→system annotation | Notes |
|---|---|---|
| **MUSCIMA++** | **Yes — the only explicit grouping model**: `staff_grouping` symbol (191 instances) built from `multi-staff_bracket`, `multi-staff_brace`, thin/thick barline primitives, recursive, with outlinks to all grouped staves; separate subset with 28,880 system measures | handwritten |
| AudioLabs v2 | system measures + staves; Dvořák et al. added 5,376 `system` boxes | ≈2.07 staves/system |
| OSLiC (OpenScore Lieder) | 17,991 systems from MuseScore SVG (pixel-accurate) | ≈3.06 staves/system |
| DeepScoresV2 (our training set) | **No system regions.** Has `brace` (725 test instances; Faster R-CNN mAP 0.869, watershed 0.000). **No orchestral square-bracket class, no systemic-barline class** | typeset |
| DoReMi | No — "most images one system per page", max 6 staves | |
| SMB (OMR-NED source) | region boxes "staves or systems", ambiguous; no segmentation metric | densest = quartet |
| PrIMuS, CVC-MUSCIMA, Capitan | No | |

**MUSCIMA++'s data model is the right conceptual shape for a fix**: grouping as
a relation *constructed from bracket + brace + systemic-barline evidence*, with
sub-groups. Nobody has implemented it as an algorithm and reported grouping
accuracy. [NOT FOUND: any paper detecting bracket/brace/systemic barline and
reporting resulting grouping accuracy.]

## What the canonical surveys say

Calvo-Zaragoza/Hajič/Pacha (ACM CSur 2020, the field's reference survey)
mentions staff→system grouping **exactly once**, dismissively ("a decision on
how to group them into systems has to be made anyway"); its
complexity taxonomy is staff-count-agnostic — [INFERRED] the field's own
taxonomy defines away what makes conductor's scores hard. Byrd & Simonsen's
testbed names "system segmentation" as a difficulty axis (level 3/3.5) — named,
never measured. Older Bellini/Bruno/Nesi is the clearest early statement that
systems-of-staves are a distinct problem.

## Domain-shift evidence (nearest thing to publisher-dependence)

- Castellanos et al. IJDAR 2022: "each new manuscript requires a preliminary
  manual annotation … one of the main bottlenecks in OMR"; DANN adaptation
  +29% F.
- Castellanos/Gallego/Fujinaga WoRMS 5: heuristics "struggled with
  generalization, as they require an expert to adapt them to each application
  domain (or score type)".
- Moss et al. WoRMS 4 (19MT-OMR): OMR datasets "stem from a single source or
  collection of more or less uniform sources".
- Kletz & Pacha: "our dataset lacks diversity."

All framed as manuscript/typeset/collection shift — never engraver identity.

## Corrections recorded by the surveyor

- Rebelo et al. 2012 is IJMIR 1(3):173–190 (not IJDAR); full text unobtainable.
- WoRMS proceedings live on arXiv; no 7th (2025) edition appears to exist.
