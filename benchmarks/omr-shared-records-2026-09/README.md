# Shared staged records — the second publisher

`library/_shared-records/` holds staged records that several jobs read instead
of each re-gathering the same pages. The directory is **machine-local**
(`library/` is gitignored); this benchmark holds the RECIPE and the RECEIPT.

| record | document | pdf pages | why it exists |
|---|---|--:|---|
| `beethoven5-p1-p4.record.json` | Litolff Beethoven 5 mvt 1 | 1-3 | the cleanup count's artefact |
| `brahms1-breitkopf-p0-p3.record.json` | **Breitkopf & Härtel Brahms 1 mvt 1** | **0-3** | **the second publisher** |

⚠️ **Everything ReEngrave measured on 2026-09-15 is n = 1 document, 1
publisher, 4 pages, on the low-res bitonal Litolff `984073` — the pessimistic
end of the corpus. A result that holds on BOTH is a result; one that holds only
on Litolff is a property of that scan.**

Build: `make_breitkopf_brahms1.sh`. Receipt, coverage inventory and what the
gather exposed and this job deliberately did NOT fix: `FINDINGS.md`.
