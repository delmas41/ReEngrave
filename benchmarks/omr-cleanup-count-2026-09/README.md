# The first cleanup count — the artefact, and what you are being asked to decide

**Open `out/side-by-side-<tag>.html` in a browser.** It is the print beside our
output, one printed system at a time, ordered by where the machine thinks your
time will go — highest first, so the page that failed structurally is at the
top and not buried at row 14.

**You are being asked for one thing:** for each printed system, how many
FIX-ACTIONS would you perform to make our file match the print, and in which of
four categories — **missing / wrong / spurious / would-not-notice**. Mark them
in `out/counting-sheet-<tag>.csv`; the definitions are in
[CATEGORIES.md](CATEGORIES.md) and were committed before any of this output
existed, which `git log` will confirm.

**The machine has pre-filled only the `proposed_*` columns, and only about
ABSENCE** — bars it read nothing in, and ink it holds that the file does not
carry. It proposes NOTHING in `spurious`, because deciding that needs the
print and the machine has not got one. Never add a `proposed_` column into a
total.

**Read [FINDINGS.md](FINDINGS.md) §1 before the first number**: this document
is the pessimistic end of this repo's corpus (a low-res bitonal scan), the
artefact covers part of the movement and says exactly where it stops, and three
of the columns have limits that will otherwise look like results.

---

## Regenerating it

```bash
bash  benchmarks/omr-cleanup-count-2026-09/run_gather.sh 1-4 p1-p4
python3 benchmarks/omr-cleanup-count-2026-09/export_arm.py --record \
        benchmarks/omr-cleanup-count-2026-09/out/record-p1-p4.json --tag p1-p4
python3 benchmarks/omr-cleanup-count-2026-09/build_sheet.py      --tag p1-p4
python3 benchmarks/omr-cleanup-count-2026-09/build_sidebyside.py --tag p1-p4
```

The gather is the slow half and it is **Surya-bound, not detector-bound** on
this machine. `run_gather.sh` sets `OMR_SURYA_KEEP_ALIVE=0` so the run owns its
own worker; **never `pkill -f` anything while it runs** — one machine has one
shared server and killing it by name has already cost a sibling agent a
multi-hour transcription.

**The HTML is self-contained** — the crops are embedded in it, because the
repo's root `.gitignore` excludes `benchmarks/**/crops/` and a linked crop
would show anyone who had not re-run the gather seven broken images. The
`out/crops/*.png` written beside it are build products.

The only thing NOT committed is the staged **record**, which is 132 MB for four
pages. Everything derived from it is: the file, the system map, the coverage
report, the proposals, the sheet and the HTML — so every figure in FINDINGS.md
can be checked from a checkout, and only re-deriving the proposals needs the
gather re-run.
