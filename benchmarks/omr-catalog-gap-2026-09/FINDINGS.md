# The catalog was under-reporting the store by 54 editions — and they are the publisher diversity

**2026-09-20.** Opened to check one line of
[`docs/handoff-2026-09-18-three-lanes-and-the-print.md`](../../docs/handoff-2026-09-18-three-lanes-and-the-print.md)
§5.4, which ranks *"a third publisher, for the DENOMINATOR rather than the
tie"* and says in passing:

> ⚠️ The catalog does **not** answer this — it names only second *scans* of the
> same two publishers, while **Breitkopf 1862 Beethoven 5, Eulenburg 1938
> Beethoven 5 and Simrock 1877 Brahms 1 are on disk and in the catalog
> NOWHERE.**

**Both halves are true, and the gap is 18× larger than the three plates it
names.**

## 1. WHAT WAS MEASURED

| | before | after |
|---|--:|--:|
| catalog entries | 1,980 | **2,034** |
| of which editions | 235 | **289** |
| store files present, per `verify` | 1,980 present / 0 missing / 0 changed | — |
| **editions on disk and NOT in the catalog** | **54** | 0 |
| of those 54, how many had a provenance sidecar | **54 of 54** | — |

**So nothing was un-ingested.** Every one of the 54 had been downloaded, had
its IMSLP provenance fetched and written, and had a sidecar sitting beside it
carrying publisher, plate, page count, `image_type` and `work_id`. What never
happened is the **catalog rebuild** that turns sidecars into the tracked index.

## 2. ⚠️⚠️ THEY ARE THE PUBLISHER DIVERSITY, WHICH IS WHAT MAKES THIS MORE THAN A COUNT

The 54 span **29 distinct publishers** — Breitkopf & Härtel (Beethoven's Werke
*and* Brahms Sämtliche Werke), Ernst Eulenburg, Cianchettini & Sperati, N.
Simrock, Bärenreiter (Neue Mozart-Ausgabe), Edition Peters, C.F. Peters,
Durand, Ricordi, Novello, Schott, Bote & Bock, Belaieff, Jurgenson, NBA,
Haslinger, Steiner…

For the two documents every OMR lane in this repo measures on:

| work | publishers the catalog reported | publishers it reports now |
|---|---|---|
| Beethoven 5 op.67 | Litolff (2 scans) | **Litolff, Breitkopf & Härtel 1862, Ernst Eulenburg 1938** |
| Brahms 1 op.68 | Breitkopf (2 scans) | **Breitkopf & Härtel, N. Simrock 1877** |

⚠️⚠️ **So `n = 2 publishers` — the limit stated at the foot of a dozen results
in `CLAUDE.md` — is, for these works, a property of the CATALOG and not of what
is held.** A third Beethoven 5 plate and a second Brahms 1 plate have been on
this machine the whole time, and every lane that asked *"is a third publisher
available?"* was answered by an index that did not know about them.

⚠️ It does not retroactively change any measurement: those results are correct
about the plates they ran on, and their `n` was honestly reported. What changes
is what the NEXT lane can reach.

## 3. THE REPAIR, AND WHY IT IS SAFE

`python3 -m tools.library.ingest catalog` — the documented command whose whole
purpose is this. It is **sidecar-driven**, so a file with no sidecar is
REPORTED as unregistered rather than invented into the index, and it carries
the `works` and `editions` maps forward untouched because those are
network-fetched and page-read rather than derivable.

Checked before running, because it writes a **committed** file:

* `verify` first: **1,980 present, 0 missing, 0 changed** — so the rebuild
  could only add, never drop. A rebuild against a store with missing files
  would silently delete their entries.
* all 54 have a sidecar, so all 54 would be added rather than reported.

Checked after, entry by entry against a copy of the previous file:
**54 added, 0 removed, `works` 223 → 223 identical, `editions` 234 → 234
identical, schema 3 → 3.**

⚠️ **THREE EXISTING ENTRIES CHANGED, AND THEY ARE NAMED RATHER THAN NETTED
AWAY.** All three are one field on three Rimsky-Korsakov files: `composer`
`'Rimsky-Korsakov, Nikolai'` → `'Rimsky-Korsakov, Nikolay'`. The sidecars
carry `Nikolay` (IMSLP's own spelling), so the rebuild is restoring the
sidecar's authority, which is the design. **`composer_slug` is unchanged**
(`rimsky-korsakov`), so nothing joins differently.

327 catalog/library/roster/instrument tests pass.

## 4. ⚠️ WHAT THIS DOES *NOT* ESTABLISH

* **Nothing about legibility.** `image_type: "Normal Scan"` is IMSLP's own
  label, not a measurement, and this thread's own history is 4-found/0-false
  engraved against 1-found/9-false scanned on the SAME 22 bars. A third
  publisher being *held* is not a third publisher being *readable*.
* **Nothing has been gathered or measured on any of the 54.** No staged
  record, no page, no figure.
* **No hand-verified window row exists for any of them**, so going from "bar
  N" to "page N" on these plates is still the manual step every meter and
  crop lane has paid for.
* **Why the rebuild was not run** is not established. The sidecars are dated
  across the ingest campaign; the likeliest reading is simply that `catalog`
  was run once and later downloads never re-ran it. **This is a process gap
  with no guard** — nothing fails when the store and the index disagree, which
  is why it survived for 54 files.

## 5. THE CHEAP GUARD THAT WOULD HAVE CAUGHT IT

`verify` already answers *"is every catalogued file present"* and exits
non-zero on a checksum mismatch. It does **not** answer the mirror question,
*"is every present file catalogued"* — which is exactly the direction this
gap ran in. The symmetry is the same one `no_producer.py` needed (a target-only
test reports every chain without the layer the repair lives in), and it is one
line of the same enumeration this findings file used.

✅ **BUILT, the same day** — `score_library.unindexed()`, reported by
`ingest verify`, which now **exits non-zero** on it. Two answers kept apart
because the repairs differ: `with_sidecar` (the catalog is simply behind —
`ingest catalog` fixes it) and `without_sidecar` (no provenance at all — a
rebuild will REPORT it, and the repair is to fetch the provenance, never to
index it anyway).

⚠️ **ITS EMPTY STATE IS THE OPPOSITE OF `verify`'S, which is why they are two
functions.** On a fresh clone `library/` does not exist: `verify` correctly
reports every entry missing, and `unindexed` must report NOTHING — reporting
the whole catalog as unindexed would be exactly backwards. Pinned by a test.

⚠️ **THE CONTROL IS THE HISTORICAL CASE, and the delta IS the repair** — the
same standard `no_producer.py` was held to. Replayed against a copy of the
pre-rebuild catalog it reports **54 with_sidecar / 0 without**; against the
rebuilt one, **0 and 0**. 7 unit tests including a negative control (without
it, a guard that always fires passes every other assertion), and 129
library/catalog/ingest tests pass.
