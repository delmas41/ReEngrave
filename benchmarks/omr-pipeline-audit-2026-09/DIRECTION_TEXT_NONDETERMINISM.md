# `OMR_DIRECTION_TEXT=0` did not stop the OCR rung — and the strings it left behind

**Agent IV, 2026-09-07.** Reproduction of a live defect reported by Fix Agent A,
not a verification of a report. Read-only: no pipeline was run, no server was
touched, nothing was fixed. Everything below is derived from source at `d0de3931`
(`tools/` unchanged since `350f0532`) and from **committed artefacts**.

**One-line answer.** The flag is real and correct. **`argparse` overrides it:
`--direction-text` is declared `default=True` instead of `default=None`, so every
CLI run passes an explicit `True` and the environment variable is never read.**
The backend does not have this bug. The nondeterminism is a *separate* fault in
the same rung, and it is reproducible from committed artefacts.

⚠️ The coordinator's instruction was to stop at the first question that turns out
to be the whole story. **Q1 is the whole story for "why did the reader run" and
for nothing else** — the nondeterminism, the missing output guard and the HTTP
exposure are not consequences of it and would all exist with the flag working
perfectly. So Q1 is answered and closed, and Q2–Q5 continue.

---

## Q1 — The flag is honoured on one path and defeated on the other

**The flag itself is correct.** `transcribe._direction_text_default()`
(`:3688-3699`) reads `OMR_DIRECTION_TEXT` with a default of `"1"` and treats
`0 / "" / false / no / off` as off. Verified against the live function:

```
'0'->False  'off'->False  'false'->False  'no'->False  ''->False  ' 0 '->False   '1'->True  unset->True
```

**The gate is also correct**, and it is the only writer of `out["direction_text"]`
(`transcribe.py:4963-4983`):

```python
if (_direction_text_default() if read_direction_text is None
        else read_direction_text):
```

⚠️ **`_direction_text_default()` is consulted only when the caller passes
`None`.** Any explicit value wins — which is deliberate and right.

**The defect is one keyword, at `transcribe.py:5111-5112`:**

```python
ap.add_argument("--direction-text", action=argparse.BooleanOptionalAction,
                default=True,          # <-- should be None
```

`BooleanOptionalAction` with `default=True` yields `args.direction_text is True`
whenever the user types neither `--direction-text` nor `--no-direction-text`.
That is handed straight to the gate at `:5249` (`read_direction_text=args.direction_text`),
so the `else` branch is taken and **`_direction_text_default()` is never called on
the CLI path.** Confirmed by AST (`{'action': 'argparse.BooleanOptionalAction',
'default': 'True'}`, line 5111) and by `BooleanOptionalAction` semantics
(`default=None` yields `None`; the module asks for `True`).

**Which callers are affected:**

| caller | passes | `OMR_DIRECTION_TEXT` honoured? |
|---|---|---|
| **`python3 -m tools.omr.transcribe`** (CLI) | `args.direction_text` = **`True`** | ❌ **NO — silently ignored** |
| `backend/modules/local_omr.py:250-258` | nothing → `None` | ✅ **yes** |
| `benchmarks/omr-scan-e2e-2026-09/scan_eval.py:259` | `protocol["read_direction_text"]` | by design — an explicit protocol value |
| `tools/omr/training/orchestral_eval.py:441` | `direction_text=` (default `False`) | by design |

⚠️ **The two benchmark harnesses are NOT bugs.** They pin the value explicitly
because their protocol requires it, and an explicit caller opinion beating an env
default is the documented contract. The only broken caller is the CLI, where the
user expressed no opinion and argparse invented one.

⚠️ **The web app is not affected.** `local_omr.py` passes no flag, so a
deployment setting `OMR_DIRECTION_TEXT=0` really does suppress the reader. The
docstring at `:3690-3697` says the env knob exists precisely because *"the backend
passes no flag"* — that reasoning is sound and that path works. The CLI is the
path the docstring did not consider.

### The distinction the coordinator asked for: reader, or label reader?

**It was the direction reader, not the margin-label reader.** `out["direction_text"]`
is written at `transcribe.py:4975` and **nowhere else in the tree** — it exists
only inside the gate. So an artefact carrying `direction_text.pages[].rejected`
is proof the gate evaluated true. The margin-label reader
(`staff_labels_surya`, on by default, which CLAUDE.md notes gets blamed for this
rung's model load) writes no such key and could not have produced those strings.

⚠️ **But both readers share one rung**, and that matters for Q2: `direction_text.default_readers`
(`:719-726`) obtains Surya as `staff_labels_surya.read_crops_text`. So even with
the flag working, `.venv-surya` is loaded on any page without a text layer — by
the *label* reader. **Turning the direction reader off does not remove Surya from
the run**, and any wall-clock claim must say which consumer it is attributing.

---

## Q2 — The cost, MEASURED from committed artefacts

`transcribe.py:4983` records `runtime.direction_text_s` whenever the gate runs, so
the cost is already on disk. Over **23 committed transcriptions** carrying the
field (11 scan rows × 2 arms, plus the Brahms labeling transcription):

| | direction_text share of `runtime.total_s` |
|---|--:|
| median | **0.192** |
| min | 0.112 |
| max | **0.845** |

⚠️ **This corrects a figure in the record.** The memory entry quotes *"direction
text is 75% of whole-work wall clock"*. On these per-page runs the median is
**19.2%**, not 75%. The 75% figure is reachable — `beethoven-984073-p2` spends
150.2 s of 196.2 s (76.5%) in one arm and 284.7 s of 337.1 s (84.5%) in the other
— but it is the **tail, not the typical case**. Both figures should be quoted with
their unit (per page here; per whole work there).

**And the cost is often paid for nothing.** On **13 of the 23** runs `n_placed`
is **0** while `rejected` is non-empty: the reader ran, produced no exported
`<words>` at all, and left only refused strings behind.

⚠️ **UNMEASURED:** what a CLI run with `OMR_DIRECTION_TEXT=0` costs *relative to
one with the flag honoured*. That needs an A/B this agent is embargoed from
running. The figures above are the cost of the pass when it runs, which is what
the flag bug causes a user to pay unknowingly.

---

## Q3 — The nondeterminism, reproduced independently and localised

**I reproduced it without running anything**, by comparing the two committed arms
of the scan gate, and **the weights confound is controlled**: the two arms use
different checkpoints, so different detections give different candidate crops, and
a difference in `rejected` would be expected. So I compared only rows where the
funnel is identical.

| row | graft09 `cand/read/acc/rej` | restamp `cand/read/acc/rej` | funnel identical? | `rejected` symmetric difference |
|---|---|---|---|--:|
| beethoven-984073-**p2** | 26/25/2/**27** | 26/25/2/**28** | **YES** | **1** |
| beethoven-575951-p1/p2, 984073-p1, brahms p1/p2, dvorak p5/p6, mahler p2/p3 | — | — | YES | **0** |
| bach-brandenburg3-p1 | 20/20/0/20 | 25/23/0/23 | no (25≠20) | (confounded, excluded) |

**On `beethoven-984073-p2` the two runs proposed the same 26 candidates, read the
same 25, accepted the same 2 — and one of them emitted an extra refused string:**

```
'- 8 - - 9 - - 10 - - 11 - - 12 - - 13 - - 14 - - 15 - - 16 - - 17 - - 18 - - 19 - - 20 - -'
```

That is a **degenerate repetition** — the same shape as the reported
11,708-character essay *"repeated to item 64"*. **And it is the same page that
shows the wall-clock anomaly**: 150.18 s in one arm against 284.73 s in the other,
a 1.9× difference on one page. Output nondeterminism and runtime nondeterminism
co-locate.

**So: rare, page-specific, and not pervasive** — 10 of 11 comparable rows are
byte-identical in `rejected`.

### The mechanism, as far as the tree can establish it

**The Surya rung is a GENERATIVE decoder, not a classical OCR.**
`staff_labels_surya`'s own docstring (`:41-43`) records the dependency:
`brew install llama.cpp`, and *"Surya auto-spawns the llama.cpp server and pulls a
650M GGUF on first use"*. A generative decode on an ambiguous crop can loop, and
that single hypothesis explains every symptom at once:

- degenerate repetition (`- 8 - - 9 - …`; *"repeated to item 64"*);
- an 11,708-character output — the signature of hitting a max-token cap;
- 150 s → 285 s on the same page (generating thousands of tokens costs time);
- a short spurious completion (`SECRET`);
- run-to-run variation, if sampling is not greedy.

⚠️ **This repository sets no sampling parameters at all.**
`grep -n "temperature\|top_p\|top_k\|seed\|max_tokens\|n_predict\|repeat_penalty"`
over `_surya_worker.py`, `staff_labels_surya.py` and `direction_text.py` returns
**nothing**. Temperature, seed and token cap are whatever Surya and llama.cpp
default to, so the determinism of this rung is **not currently under this
project's control**. CLAUDE.md's existing "Surya temperature nondeterminism lead"
is the right lead and this is a second instance of it.

⚠️ **The resident server was not touched.** PID 2831 was neither restarted,
queried nor killed; the whole of Q3 is committed-artefact archaeology. I therefore
**cannot distinguish** decode sampling from shared-server state — both predict
what I observed. **UNMEASURED, and the run that would settle it:** the same crop
submitted N times to a *private* llama.cpp instance (never the shared one), with
and without a fixed seed.

### ⚠️ The runaway guard exists — and it is not on this path

This is the sharpest structural finding here. `staff_labels_surya._assign` carries
a **runaway-block gate** (`_RUNAWAY_HEIGHT_FRACTION = 0.5`), built and measured
in `benchmarks/omr-margin-labels-blob-2026-09/` on a 22× empty gap, precisely
because Surya sometimes returns one enormous block instead of per-staff labels.

**`direction_text` does not go through `_assign`.** It calls
`staff_labels_surya.read_crops_text` directly (`direction_text.py:724`), and
`read_crops_text` (`staff_labels_surya.py:280-330`) applies **no length cap, no
content check and no sanity guard** — its docstring states the contract plainly:
*"the caller's job is to gate what was read"*. The caller's gate is the lexicon,
which is a gate on *acceptance*, not on *recording*.

> **So the one runaway defence the Surya rung has protects the label path and not
> the direction path, and an 11,708-character string is the predicted result.**

---

## Q4 — Downstream exposure: nothing reads it, and the lexicon gate held

**`rejected` is write-only.** Over all of `tools/` and `backend/`, the token
appears in exactly **two** places, both in `direction_text.py`:

```
direction_text.py:759   "rejected": [],                                     # created
direction_text.py:798   info["rejected"].extend(text for _name, text in texts)   # extended
```

**No consumer anywhere in production code.** It is serialised into the result
JSON and read by nobody — it reaches no exporter, no MusicXML, no decision. The
only readers in the repository are analysis probes (this audit's
`probe_direction_funnel.py`, and mine).

**The lexicon gate did its documented job.** `n_accepted` is 0 in both reported
runs, and in my reproduction the extra degenerate string was refused too — the
essay and `SECRET` never became a `<words>` element. The gate is load-bearing and
nothing here licenses touching it; this investigation is **evidence for** the
standing refusal to loosen it, not against.

⚠️ **Adopting the coordinator's posture, and it is the right one:** `rejected`
holds model-generated text derived from a third-party PDF. It is **untrusted
content, not data we authored**. Today nothing consumes it, so the posture costs
nothing to hold — but it is the thing to state loudly *before* someone gives it a
consumer, because two of this audit's standing conclusions (round 1 item 2's
`contested_with`, round 2's *"record the refusal"*) are proposals to record more
refused strings, and a future reader of them would inherit this.

---

## Q5 — It DOES reach the application, as an unauthenticated static file

`backend/modules/local_omr.py:262-265` writes **the entire result dict**:

```python
json_path = os.path.join(output_dir, f"{pdf_stem}.omr.json")
with open(json_path, "w", encoding="utf-8") as fh:
    json.dump(omr_result, fh)
```

`output_dir` is under `settings.upload_dir`, and `backend/main.py:105` is:

```python
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
```

with `frontend/nginx.conf:14` proxying `^~ /uploads/` to it. **The mount carries
no `Depends(get_current_user)`** — the only middleware on the app is CORS, and
`Depends(get_current_user)` appears on route handlers, which do not cover a
`StaticFiles` mount.

**So `rejected` — including an 11 kB hallucinated essay — is served over HTTP at
`/uploads/{score_id}/{pdf_stem}.omr.json` to anyone who can reach that path, with
no authentication.** ⚠️ I am reporting reachability, not claiming an exploit: the
path needs a `score_id`, the content is not executed, and nothing interprets it.

**Nothing in the app *interprets* it.** `local_omr.py` reads four aggregate fields
from the result — `n_measures_total`, `n_pages_processed`, `n_detections_total`,
`runtime.total_s` (`:280-284`, `:320-324`) — and never touches `direction_text`.

⚠️ **And this exposure is independent of the flag bug.** Direction text is
default-ON, so the strings reach that JSON on the web-app path in the normal
configuration. Fixing `default=True` does not close it.

---

## Summary, and what belongs to a build agent

| # | question | answer |
|--:|---|---|
| 1 | is the flag honoured? | **Not on the CLI.** `transcribe.py:5111` `default=True` should be `default=None`. The flag, the gate and the backend path are all correct. Not the label reader — `direction_text` is written only inside the gate |
| 2 | cost | **median 19.2% of page wall clock** (n=23, min 11.2%, max 84.5%), and `n_placed == 0` on 13 of 23. ⚠️ corrects the "75%" in the record — that is the tail |
| 3 | nondeterminism | reproduced from committed artefacts on `beethoven-984073-p2` at an identical funnel (26/25/2): `rejected` 27 vs 28, the extra string a degenerate repetition, on the page that also runs 150 s vs 285 s. Rare (1 of 11 rows). Mechanism: a generative 650M GGUF via llama.cpp, with **no temperature, seed or token cap set anywhere in this repo**. Server untouched; decode-vs-server-state **UNMEASURED** |
| 4 | downstream | **`rejected` has no consumer** — 2 occurrences, both its own creation and extension. Lexicon gate held (`n_accepted` 0). Treat as untrusted |
| 5 | reaches the app? | **Yes** — written into `uploads/{score_id}/{stem}.omr.json` and served by an **unauthenticated** `StaticFiles` mount. Nothing interprets it. Independent of the flag bug |

**Three separable build tasks, in the order I would rank them:**

1. **`default=True` → `default=None`** at `transcribe.py:5111`. One keyword; makes
   `OMR_DIRECTION_TEXT` work on the CLI. ⚠️ It changes no default behaviour (the
   env default is `"1"`, so an unset environment still runs the reader) — but it
   **is** behaviour-changing for anyone who has been setting the variable and not
   getting it, so it wants the byte-identity check on an unset environment.
2. **A length/degeneracy guard on `read_crops_text`**, the sibling of `_assign`'s
   `_RUNAWAY_HEIGHT_FRACTION`. ⚠️ It belongs in the **reader**, not the lexicon —
   the lexicon gate is documented load-bearing and this needs none of it. A crop
   is a word; a 11,708-character answer to "what does this word say" is a reader
   failure and should be recorded as one rather than passed on as a string.
3. **Decide whether `rejected` should be serialised at all**, or capped. Round 2
   proposes recording *more* refused strings; that proposal and this exposure
   should be decided together, and the `/uploads` mount's lack of authentication
   is a separate question that outlives both.
