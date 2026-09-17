# Shared staged records — the second publisher

`library/_shared-records/` holds staged records that several jobs read instead
of each re-gathering the same pages. The directory is **machine-local**
(`library/` is gitignored); this benchmark holds the RECIPE and the RECEIPT.

| record | document | pdf pages | why it exists |
|---|---|--:|---|
| `beethoven5-p1-p4.record.json` | Litolff Beethoven 5 mvt 1 | 1-3 | the cleanup count's artefact |
| `brahms1-breitkopf-p0-p3.record.json` | **Breitkopf & Härtel Brahms 1 mvt 1** | **0-3** | **the second publisher** |
| `beethoven5-p1-p4-ink-identity.record.json` | Litolff Beethoven 5 mvt 1 | 1-4 | **the only record carrying `Q.INK` AND its own `Q.DOCUMENT_IDENTITY`** |

⚠️⚠️ **THE THIRD RECORD IS THE FIRST THAT NAMES ITS OWN PLATE, and that is
what retires a hand-list.** The two above it predate `gather_document_identity`
and are the ENTIRE contents of `positional_store.LEGACY_RECORD_EDITIONS` — the
table whose own comment calls itself *"the honest patch … every line is a
hand-made assertion"*. Accumulated together the store distinguishes them out
loud: `litolff … (identity from record)` against `breitkopf … (identity from
legacy-table)`. Recipe, receipt and numbers:
[../omr-positional-store-2026-09/out/IDENTITY_RUN_2026-09-17.md](../omr-positional-store-2026-09/out/IDENTITY_RUN_2026-09-17.md).

⚠️ **It supersedes NOTHING.** `beethoven5-p1-p4.record.json` is a different
tree and is what four committed benchmarks read BY EXPLICIT PATH; no consumer
globs this directory (checked), so a third record is additive. Do not retire
the older one — the artefacts that cite it would go unreproducible.

⚠️ **The gap it leaves, and the one command that closes it: the Breitkopf
record has ZERO `ink` rows** (12,932 `glyph_box`, verified), so
**conditioning UNNAMED ink on the plate is still n = 1 publisher** — precisely
where the ink work expects trouble, since that document's composition inverts
(56% specks against Litolff's 1%). Re-gathering it with
`OMR_INK=1 OMR_DOCUMENT_IDENTITY=1` would make it a two-publisher fact and
retire its legacy-table line; the command is in §4 of that findings file.

⚠️ **Everything ReEngrave measured on 2026-09-15 is n = 1 document, 1
publisher, 4 pages, on the low-res bitonal Litolff `984073` — the pessimistic
end of the corpus. A result that holds on BOTH is a result; one that holds only
on Litolff is a property of that scan.**

Build: `make_breitkopf_brahms1.sh`. Receipt, coverage inventory and what the
gather exposed and this job deliberately did NOT fix: `FINDINGS.md`.
