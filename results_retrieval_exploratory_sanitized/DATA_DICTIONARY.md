# Data dictionary — `results_retrieval_exploratory_sanitized/`

The four raw reports of the **exploratory retrieval campaign** over the definitive 9-document index. They are published for one reason above all others: **they are the origin of the `recall@k = 88.7 %` reported in the article**, and they are the only files in this repository that carry a retrieval-recall field for the 53-question gold-standard bank.

They matter a second time as well. The retrieved context (`fragmentos`) recorded in these four files is **exactly the context that Study P1 consumed**: the P1 reports were produced by replaying these stored fragments, not by re-running the retriever. Publishing them therefore closes the provenance chain of `results_ablation_p1/`, which carries no `fragmentos` field of its own.

**Design:** 4 models × 1 arm (**with RAG only**) × 53 gold-standard questions = **212 inferences**, in **4 files** of 53 records each.

| | |
|---|---|
| Question bank | `datasets/dataset_gold_standard.json`, n = 53 (all answerable) |
| Index | the 9 corpus documents (6 teaching documents + 3 open-access stroke-guideline distractors) |
| Embeddings | `BAAI/bge-m3` |
| `retrieved_top_k` | 7 |
| Chunking | `chunk_size = 1500`, `chunk_overlap = 400` |
| Recall threshold | `recall_overlap_threshold = 0.35` |
| Generation | `num_ctx = 8192`, `context_max_tokens = 5000` |
| Executed | 23–24 June 2026, local Windows 11 GPU workstation |
| **Recall@k** | **47 / 53 = 88.679 %** — identical in all four files |

> ### Warning: the accuracies in these files are NOT the accuracies of Study P1
>
> These runs predate the definitive ablation. Two things differ, and both move the accuracy number:
>
> 1. **No anti-refusal system role.** The `sysrole_anti_rechazo` framing that defines Protocol P1 was introduced afterwards, precisely because of what was seen here.
> 2. **A weaker answer-extraction routine.** The parser of this harness fails to reduce the model's final line to a letter on **18 of the 212 records**, where it writes the pseudo-label **`"correcta"`** into `opcion_detectada` (plus **1** record labelled `"desconocida"`). Every one of those 19 records is scored `es_correcta = false`, although in several of them the model's final line does state a letter — and sometimes the right one. **`summary.accuracy` in these files is therefore an underestimate contaminated by a parsing artefact.**
>
> **Use these files for retrieval metrics, not for accuracy.** The article's accuracy figures come exclusively from `results_ablation_p1/`. The recall figures are unaffected by either problem: recall is computed on the retrieved chunks **before** the model is called, and does not touch `respuesta_ia` or `opcion_detectada`.

---

## Files

```
report_{model}_GPU_Local_Win11_9doc_{tag}_bge-m3_{timestamp}_SANITIZED.json
```

| File (abbreviated) | `header.model` | Label used in the article | `summary.correct` |
|---|---|---|---|
| `report_llama3.1_8b_..._llama8b_bge-m3_20260623_231909` | `llama3.1:8b` | Llama-3.1-8B | 37 / 53 |
| `report_neurofisio-qlora_..._qlora_bge-m3_20260623_235311` | `neurofisio-qlora` | QLoRA neurofisio (domain fine-tune) | 41 / 53 |
| `report_qwen2.5_7b_..._qwen7b_bge-m3_20260624_003033` | `qwen2.5:7b` | Qwen-2.5-7B | 25 / 53 |
| `report_thewindmom_llama3-med42-8b_..._med42_bge-m3_20260624_010701` | `thewindmom/llama3-med42-8b` | Med42-8B | 35 / 53 |

- `9doc` — the index held the 9 documents of the definitive corpus.
- `bge-m3` — the embedding model. There is no `noRAG` counterpart in this folder: the without-RAG runs of this campaign carry no retrieval and therefore no recall.
- `_SANITIZED` — marks the copyright treatment described at the end. **No experimental field was altered by it.**

---

## Top-level structure

Each file is a JSON object with three keys: `header`, `summary`, `questions`.

### `header` — run configuration, as written by the harness

| Field | Type | Description |
|---|---|---|
| `timestamp` | string | ISO-8601 start time of the run. |
| `benchmark_engine_version` | string | `3.0.0`. Version of the evaluation harness. |
| `model` | string | Model identifier as served by the local runtime. |
| `device` | string | Free-text run label, e.g. `Local_Win11_9doc_llama8b`. Not a hardware identifier. |
| `mode` | string | `GPU`. |
| `param_size` | string | `8b`, or `7b` for Qwen-2.5. |
| `python_version` | string | `3.11.9`. |
| `platform` | string | `Windows-10-10.0.26200-SP0` (Windows 11, build 26200). |
| `hardware_type` | string | `Local_GPU`. Do not pool these latencies with the CPU-cluster latencies of `exploratory/`. |
| `questions_file` | string | `dataset_gold_standard.json`. The bank published in `datasets/`. |
| `questions_count` | integer | 53. |
| `no_rag` | boolean | `false`. **All four files are with-RAG runs.** |
| `embedding_model` | string | `BAAI/bge-m3`. |
| `retrieved_top_k` | integer | 7. Chunks requested from the retriever. |
| `chunk_size` | integer | 1500. Characters per chunk at index time. |
| `chunk_overlap` | integer | 400. Character overlap between consecutive chunks. |
| `context_max_tokens` | integer | 5000. Token budget for the assembled context. |
| `num_ctx` | integer | 8192. Context window of the generation model. |
| `query_expansion` | boolean | `true`. The retriever issued several query variants per item (stem, options, domain synonyms) and merged the results. |
| `redundancy_threshold` | float | 0.88. Jaccard threshold above which a retrieved chunk was discarded as redundant with one already kept. **This is why `num_fragmentos` is sometimes below `retrieved_top_k`.** |
| `recall_overlap_threshold` | float | **0.35.** The threshold of the recall heuristic. See the section below — it is the single most important number in this folder. |
| `oracle_context` | boolean | `false`. The oracle-retrieval mode of the harness (which injects the chunk that best matches the *correct answer*) was **not** used. Had it been, the retrieval would not be an honest one. |
| `oracle_k` | integer | 7. Inert, since `oracle_context` is `false`. |
| `question_timeout` | integer | 720 seconds per question. No question timed out. |
| `context_limit_tokens_for_small_window_models` | integer | 1200. Inert here. |
| `small_window_model_detected` | boolean | `false`. None of the four models has a small context window. |
| `is_vision_language_model` | boolean | `false`. |
| `is_medical_legacy_model` | boolean | `false`. |
| `prompt_language` | string | `es`. |
| `completed` | boolean | `true`. All 53 questions ran. |

### `summary` — per-run aggregate, as written by the harness

| Field | Type | Description |
|---|---|---|
| `total` | integer | 53. |
| `processed` | integer | 53. |
| `correct` | integer | Records with `es_correcta == true`. **Read the warning above before using this.** |
| `incorrect` | integer | Records with `es_correcta == false` and a parsed option letter. |
| `unknown` | integer | Records whose answer could not be parsed at all (`opcion_detectada == "desconocida"`). 1 across the four files. Note that the 18 `"correcta"` pseudo-labels are **not** counted here; they fall into `incorrect`. |
| `timeout` | integer | 0 in all four files. |
| `recall_hits` | integer | **47** in all four files. Number of questions whose `retrieval_recall_hit` is `true`. |
| `recall_at_k` | float | **88.67924528301887** in all four files, i.e. `100 × 47 / 53`. **This is the article's 88.7 %.** |
| `accuracy` | float | `100 × correct / total`. Protocol-specific and parser-contaminated; not comparable with P1. |

### `questions[]` — one object per inference (53 per file)

| Field | Type | Description |
|---|---|---|
| `id` | integer | Question identifier, 1–53. Joins to `datasets/dataset_gold_standard.json`, to `aggregates/chunk_provenance.json` and, record for record, to the `con` reports of `results_ablation_p1/`. |
| `pregunta` | string | The question stem exactly as presented. |
| `opciones` | object | Map from option letter to option text. Three keys: `a`, `b`, `c`. |
| `respuesta_correcta` | string | The gold answer letter. |
| `respuesta_ia` | string | The model's complete free-text answer, verbatim. See the redaction note at the end. |
| `opcion_detectada` | string | The option letter parsed out of `respuesta_ia`. Besides `a`, `b`, `c` it takes two non-letter values produced by the weak parser of this harness: **`"correcta"`** (18 records) and **`"desconocida"`** (1 record). Both score as errors. |
| `es_correcta` | boolean | `opcion_detectada == respuesta_correcta`. |
| `timed_out` | boolean | `false` in all 212 records. |
| `latency_seconds` | float | Wall-clock time of the inference. Medians: 11.3 s (Llama), 13.3 s (QLoRA), 11.7 s (Qwen), 16.1 s (Med42). |
| `fragmentos` | array | The 7 (or 5–6) retrieved chunks placed in the prompt — **sanitised**, see the schema below. |
| `num_fragmentos` | integer | Number of retrieved chunks. 7 for 51 of the 53 questions; 6 for one and 5 for another, where the redundancy filter dropped near-duplicates. |
| `context_truncated_for_small_window` | boolean | `false` in all 212 records. |
| `retrieval_recall_hit` | boolean | **The recall field.** `true` for 47 of the 53 questions. Fully defined in the next section — **it is a lexical heuristic, not a human relevance judgement.** |
| `retrieval_overlap` | float | The overlap ratio behind that boolean, rounded to 4 decimals. Range across the bank: 0.1786 – 0.8333. |
| `retrieval_matched_tokens` | array of strings | The evidence tokens found in the best-matching retrieved chunk, alphabetically sorted and **truncated to the first 20**. Because of that truncation the length of this array is *not* a usable count of matched tokens. |
| `oracle_context_used` | boolean | `false` in all 212 records. |
| `option_evidence_scores` | object | For each option letter, the fraction of that option's content tokens that appear anywhere in the union of the retrieved chunks, 0–1, rounded to 4 decimals. A crude measure of how well the retrieved context lexically covers each alternative — **not** a measure of which alternative is true. Computed with the same tokeniser as the recall heuristic. |
| `answer_confidence` | float | A **derived, heuristic** confidence for the selected option, 0–1: `min(1, 0.65 × s_chosen + 0.25 × max(0, s_chosen − s_second) + 0.1 × format_bonus)`, where `s_chosen` is the chosen option's `option_evidence_scores` value, `s_second` the second-highest such value among the options, and `format_bonus` is 1 when the answer contains a well-formed `RESPUESTA: <letter>` line. It is forced to **0.0** when the parser produced no valid option; it can also legitimately be 0.0 for a parsed option whose evidence score is 0 and whose answer carries no `RESPUESTA:` line, so **a 0.0 must not be read as a parser failure**. **It is not a model log-probability and carries no calibration guarantee**; it is a lexical artefact of the harness, published for completeness. |
| `effective_retrieved_top_k` | integer | 7 for all 53 questions. The harness may raise `top_k` for unusually long items; it never did here. |
| `context_token_count` | integer | Whitespace-token count of the assembled context that was actually sent to the model. Range 789 – 1546, median 1297. |

---

## How `retrieval_recall_hit` and `recall_at_k` are operationalised

**This is the most important section of this dictionary, and it is a caveat as much as a definition.**

`recall_at_k` is **not** computed against per-chunk relevance labels, because none exist: **no human ever judged which chunk of the corpus is the relevant one for a given question.** It is computed by an **automatic lexical-overlap heuristic** between each question's *evidence text* and each retrieved chunk. The procedure, for one question, is exactly this:

1. **Build the evidence text**: concatenate the question stem and the text of the **correct** option.
   `evidence = pregunta + " " + opciones[respuesta_correcta]`
2. **Tokenise** it: lower-case, keep only alphabetic runs of **3 or more** characters (`[a-záéíóúñü]{3,}` — digits and 1–2-character words are dropped), then remove a fixed list of **27 Spanish stopwords** (`de, la, el, los, las, y, o, u, en, con, por, para, del, al, que, se, un, una, unos, unas, es, son, como, su, sus, lo, a`). Take the **set** of the surviving tokens: `E`.
3. **For each retrieved chunk** independently, tokenise it the same way into a set `C`, and compute
   `overlap(C) = |E ∩ C| / |E|`.
4. **Take the best single chunk**: `best_overlap = max overlap(C)` over the `num_fragmentos` retrieved chunks. This value is stored as `retrieval_overlap`, and the intersection of the winning chunk is stored (truncated to 20 items) as `retrieval_matched_tokens`.
5. **Decide the hit**:
   `retrieval_recall_hit = (best_overlap >= 0.35) AND (|E ∩ C_best| >= 2)`
   The 0.35 is `header.recall_overlap_threshold`; the 2-token floor guards against a spurious hit on a question whose evidence reduces to one or two tokens.
6. **Aggregate over the run**:
   `recall_hits = Σ retrieval_recall_hit` and `recall_at_k = 100 × recall_hits / 53`.

In these four files that gives **47 hits out of 53 questions**, i.e. **`recall_at_k = 88.679 %`** — the figure the article rounds to **88.7 %**. Anyone can recompute it from the published records: count the `true` values of `retrieval_recall_hit` in any of the four files and divide by 53.

The six questions that miss are the **same six in all four files** — ids **4, 13, 15, 36, 46 and 47** — with `retrieval_overlap` of 0.3333, 0.3182, 0.2941, 0.2222, 0.2000 and 0.1786 respectively. The lowest overlap among the 47 hits is 0.3548, so the 0.35 threshold does discriminate rather than merely rubber-stamp.

### What this measure is, and what it is not

- **It is an automatic approximation, not a gold standard of relevance.** It asks a purely lexical question: *does at least one retrieved chunk repeat at least 35 % of the distinct content words of the question plus its correct answer?* It never asks whether that chunk actually **supports** the answer.
- **It can be wrong in both directions.** A chunk that shares the question's vocabulary without answering it counts as a **hit** (false positive); a chunk that answers the question in different words — a synonym, a paraphrase, a table, a figure caption — counts as a **miss** (false negative). Both cases certainly occur in a corpus as terminologically repetitive as this one.
- **It is sensitive to the threshold.** 0.35 is the harness default; it was not tuned, but neither was it validated. A different threshold would give a different recall, and the article's figure inherits that arbitrariness. `retrieval_overlap` is published per question precisely so that a reader can re-threshold it and see how fragile — or robust — the 88.7 % is.
- **It uses the correct option, which the retriever never saw.** The evidence text is built *post hoc* from the gold answer. This is legitimate for measuring recall (it is how one defines what "should" have been retrieved) but it means the metric cannot be computed at inference time and is not a signal the system could act on.
- **`recall@k` here is a chunk-level lexical proxy.** It is a different quantity from the coarser, document-level check in `aggregates/chunk_provenance.json`, where the retriever returned the declared source document for **30 of the 30** gold-standard questions that carry one. Neither number should be substituted for the other.

**In short: treat 88.7 % as an automatic, lexical estimate of retrieval quality, and not as a human-adjudicated recall.**

### Why the recall is a property of the retriever, not of the model

The four files report the **same 47 hits, the same 6 misses and the same `retrieval_overlap` value for every question**. That is not a coincidence and it is not a copy: **retrieval is deterministic and was executed identically for the four models**. This is verifiable, not merely asserted:

- The SHA-256 digests in `fragmentos` are **identical, in the same order, in all four files** — the 368 retrieved chunks (1 472 records over the four files) are byte-for-byte the same.
- `aggregates/chunk_provenance.json` records the same fact independently: `retrieval_identico_entre_modelos: true`, `divergencias: []`.

Consequently `recall_at_k = 88.7 %` describes the **retrieval configuration** (`bge-m3`, `top_k = 7`, 9-document index, chunk 1500/400), not any particular generator. It is reported once, not four times, and it does not vary with the model — which is exactly what one should expect, and a useful internal consistency check on the pipeline.

### The link to Study P1

The with-RAG arm of Study P1 (`results_ablation_p1/report_*_sysrole_con_RERUN.json`) did **not** re-run the retriever. It **replayed the `fragmentos` stored in these four files**, concatenating them into the context of the new anti-refusal prompt. The evidence:

- The 1 472 `sha256` values published here are identical, question by question and position by position, to those in the `original`-bank with-RAG reports of `results_hallucination_p2_sanitized/` — all **1 472 / 1 472** match, including the two chunks whose provenance is ambiguous.
- `num_fragmentos` agrees record for record: 7 chunks for 51 questions, 6 for one and 5 for another, in every model — the 8 P1 records with fewer than 7 chunks (four with 6, four with 5) are exactly these two questions across the four models.

So the context that P1 fed to its models is fully specified by this folder, and the recall of that context is the 88.7 % measured here. The 8 P1 reports carry no `fragmentos` and no recall field of their own; this folder is where both live.

---

## The `fragmentos` sanitisation

Identical in form to the treatment applied in `results_hallucination_p2_sanitized/`. In the original reports `fragmentos` was an array of **verbatim strings** — the exact text of the chunks retrieved from the teaching corpus, which is third-party copyrighted material that may not be redistributed. Each string has been replaced by an **object describing it**:

| Key | Type | Description |
|---|---|---|
| `sha256` | string | Hex SHA-256 digest of the **exact UTF-8 bytes of the original chunk string**, unmodified and untrimmed. The verification handle: a reader holding a licensed copy of the corpus can rebuild the chunks with the published parameters (`chunk_size = 1500`, `chunk_overlap = 400`, same extraction), hash them, and confirm byte for byte which chunk was retrieved for each question — without the text ever being redistributed. |
| `n_chars` | integer | Character length of the original chunk string. Range 212 – 1497, median 1306. |
| `documento` | string \| array | Source document of the chunk, e.g. `03_sistemas_motores_descendentes.pdf`. In **8 fragments** (question 4, position 3, and question 13, position 4, in each of the four files) the value is an **array of two document names**: the chunk's text occurs in more than one document and the provenance is genuinely ambiguous, so both candidates are reported rather than an arbitrary one. |
| `pagina` | integer | Page of `documento` on which the chunk begins. |

**All 1 472 fragments carry document and page** — this bank is the one covered by `aggregates/chunk_provenance.json`, from which the mapping is taken (alignment is by position within each question, and all 368 distinct retrieved chunks were matched). There is no `"provenance": "no_disponible"` case in this folder.

Distribution of the 1 472 fragments by source document (368 per model):

| Document | Fragments (× 4 models) |
|---|---|
| `01_bobath_concepto.pdf` | 364 |
| `03_sistemas_motores_descendentes.pdf` | 292 |
| `05_bloques_3_4_tecnicas.pdf` | 200 |
| `06_fnp_facilitacion_neuromuscular.pdf` | 184 |
| `04_perfetti_etc.pdf` | 176 |
| `02_bobath_principios_tratamiento.pdf` | 156 |
| `07_dist_gpc_ictus_ap_2009.pdf` (distractor) | 52 |
| `08_dist_gpc_ictus_ap_2025.pdf` (distractor) | 24 |
| `09_dist_gpc_ictus_euskadi.pdf` (distractor) | 16 |
| ambiguous, `08` or `09` (distractor) | 8 |

Documents `01`–`06` are the teaching corpus proper; `07`–`09` are the open-access stroke clinical-practice guidelines added to the index as **distractors**. A `07`/`08`/`09` document appearing in `fragmentos` means the retriever pulled a distractor chunk into that question's context — **25 of the 368 chunks per model, affecting 12 of the 53 questions**. Their effect on the error rate is analysed in `aggregates/distractor_efecto.json`.

---

## Copyright treatment applied to `respuesta_ia`

The models were instructed to ground their answers in the retrieved evidence, and they frequently quote it. Passages of `respuesta_ia` that reproduced **50 or more consecutive words** of the source corpus were replaced in place by the literal marker

```
[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]
```

where *N* is the number of words removed. In this folder this affects **6 spans in 5 answers across 3 files**, **350 words in total**:

| File | `id` | Words removed | Source |
|---|---|---|---|
| `report_neurofisio-qlora_..._qlora_bge-m3_...` | 39 | 81 | `04_perfetti_etc.pdf`, p. 1 |
| `report_qwen2.5_7b_..._qwen7b_bge-m3_...` | 14 | 52 | `01_bobath_concepto.pdf`, p. 27 |
| `report_qwen2.5_7b_..._qwen7b_bge-m3_...` | 21 | 62 | `01_bobath_concepto.pdf`, p. 11 |
| `report_qwen2.5_7b_..._qwen7b_bge-m3_...` | 38 | 51 + 51 (two spans) | `03_sistemas_motores_descendentes.pdf`, p. 3 |
| `report_thewindmom_llama3-med42-8b_..._med42_bge-m3_...` | 18 | 53 | `05_bloques_3_4_tecnicas.pdf`, p. 50 |

The Llama-3.1-8B file required no redaction. `pregunta` and `opciones` were audited under the same criterion and required none either.

The audit follows the same method as the rest of the release, documented in caveat (d) of `VERIFICATION.md`: overlap is measured against the **nine complete source documents** (full text extracted with PyMuPDF), each indexed twice — once raw and once with running headers and footers removed, so that the token stream is continuous across page breaks — under **two tokenisations** (*normalised*: lower-cased, accents and punctuation stripped; and *strict*: whitespace-split, punctuation and case preserved). The **most conservative** outcome is applied: a span is redacted if **any** of the four combinations reports ≥ 50 consecutive words. After redaction, **0** spans of ≥ 50 consecutive words remain in these four files. Shorter quotations are retained under the academic right of quotation.

Only the overlapping span is replaced; the model's own reasoning around it is preserved untouched.

**The redaction is cosmetic and strictly posterior to the experiments.** `retrieval_recall_hit`, `retrieval_overlap`, `recall_hits`, `recall_at_k`, `es_correcta`, `opcion_detectada` and every other field were computed on the original, unredacted data and remain valid; no record was removed and no count changed (4 files × 53 records = 212 inferences; 1 472 fragments). The recall figures in particular are untouched by the redaction, since they are computed on the retrieved chunks and not on the answers. The complete unredacted data is held by the authors and is available on reasonable request for verification purposes.

---

## Re-deriving the published figure from these files

```
recall@k of a run = 100 × (number of questions[] with retrieval_recall_hit == true) / 53
                  = 100 × 47 / 53
                  = 88.679 %          (article: 88.7 %)
```

The value is the same in the four files, and equals the `summary.recall_at_k` that the harness wrote. It is not listed in `derived_metrics.json`, which collects only the figures that have **no** source file in the repository; since this folder now supplies one, the recall is re-derivable directly from the raw records above. Caveat (e) of `VERIFICATION.md` states the reservation that must accompany the figure.
