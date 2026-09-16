# The meter template reader, at a bar head

Read **FINDINGS.md**. What is in here, and what each thing can and cannot say:

| file | needs weights? | what it measures |
|---|---|---|
| `probe/candidate_columns.py` | no | **REACH** — how many mid-staff bars carry meter-shaped ink, per document, off committed legacy transcriptions. `--check` fails only when it assessed nothing. |
| `probe/empty_window.py` | no | **THE DECIDING NUMBER** — how often the template reader answers on a crop that prints NO meter, over 1,612 windows on 10 real scanned pages of 2 publishers, with a positive control that stamps a real Bravura meter into the same windows. `--check` fails when it assessed nothing OR when the positive control did not answer. |
| `local_arm.py` | **YES** | **TWO FULL RE-GATHERS**, flag off then on. ⚠️ The only thing that can PRICE a GATHER change, and it cannot run in a cloud container. See FINDINGS section 5 for the exact command. |
| `mutation_battery.py` | no | 15 arms over `gather.py` and `rhythm.py`, with a positive control in the same class. Snapshots BYTES and verifies the restore. |
| `out/` | — | committed output of the two probes. |

⚠️ **The two probes measure the READER. Only `local_arm.py` measures the
PIPELINE**, and it has not been run: `readjudicate.py` rebuilds ADJUDICATE from
a saved record so a new quantity never enters it, and `reexport_arm.py` has the
mirror blind spot. A GATHER change has no cheaper price.

⚠️ **Every window `empty_window.py` reads is EMPTY.** No page in reach prints a
mid-staff meter change, so the FALSE-POSITIVE side is measured and the
TRUE-POSITIVE side is not. Do not read a low false-positive rate as evidence
that this reads a real change.
