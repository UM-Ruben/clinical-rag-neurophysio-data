# Data dictionary — `results_ablation_p1/`

The raw inference records of **Study P1**, the ablation experiment that isolates the contribution of retrieval.

**Design:** 4 models × 2 arms (with RAG / without RAG) × 53 gold-standard questions = **424 inferences**, in **8 files** of 53 records each.

**These reports contain no corpus fragments.** The retrieved context was not dumped into them, so — unlike the Protocol-2 reports — they needed no hash sanitisation. See the note on `respuesta_ia` at the end for the one copyright treatment that *was* applied.

---

## Protocol P1 — `sysrole_anti_rechazo`

- **System role:** clinical framing designed to prevent refusal. It presents the task as a legitimate professional exercise and closes with an explicit **anti-refusal clause** instructing the model to always choose one of the options.
- **Options:** `a`, `b`, `c`. **Abstention is forbidden by design.**
- **Question bank:** `datasets/dataset_gold_standard.json`, n = 53. All items are answerable.
- **Retrieval (with-RAG arm only):** hybrid BM25 + FAISS with `BAAI/bge-m3` embeddings and a cross-encoder re-ranker, `top_k = 7`, `context_max_tokens = 5000`. Retrieval is deterministic and was verified to be **identical across the four models** (see `aggregates/chunk_provenance.json`), so the with-RAG arm compares the four models over exactly the same context.
- **Generation:** `temperature = 0`, `num_ctx = 8192`.

> ### Warning: P1 accuracies are NOT comparable with P2 accuracies
>
> Protocol P2 (`results_hallucination_p2_sanitized/`) offers **four** options instead of three — moving the chance baseline from 1/3 to 1/4 — and **permits abstention**, which changes the success criterion itself (in P2, abstaining is the correct answer on some items; in P1 it is impossible). The system role also differs in the anti-refusal clause, which is one of the variables under study. Compare the two protocols on **hallucination and abstention rates**, never on raw accuracy.

---

## Files

```
report_{tag}_GPU_Local_Win11_9doc_sysrole_{arm}_RERUN.json
```

- `tag` ∈ `llama8b`, `qlora`, `qwen7b`, `med42` — the four evaluated models.
- `arm` ∈ `con` (with RAG), `sin` (without RAG).
- `GPU_Local_Win11` — the runs were executed on the local Windows 11 GPU workstation.
- `9doc` — the index held the 9 corpus documents (6 source + 3 stroke-guideline distractors).
- `RERUN` — these 8 files are the frozen, canonical execution of Protocol P1 and are the single source of truth for every P1 figure in the article.

| `tag` | `header.model` | Label used in the article |
|---|---|---|
| `llama8b` | `llama3.1:8b` | Llama-3.1-8B |
| `qlora` | `neurofisio-qlora` | QLoRA neurofisio (domain fine-tune) |
| `qwen7b` | `qwen2.5:7b` | Qwen-2.5-7B |
| `med42` | `thewindmom/llama3-med42-8b` | Med42-8B |

---

## Top-level structure

Each file is a JSON object with three keys: `header`, `summary`, `questions`.

### `header` — run configuration

| Field | Type | Description |
|---|---|---|
| `model` | string | Model identifier as served by the local runtime (e.g. `llama3.1:8b`). |
| `arm` | string | `con` = with RAG, `sin` = without RAG. **This is the experimental variable.** |
| `system_role` | boolean | Always `true`: the anti-refusal clinical system role was applied. It is applied **identically in both arms**, so that the only difference between arms is the presence of retrieved context. |
| `no_rag` | boolean | `true` in the `sin` arm, `false` in the `con` arm. Redundant with `arm`, kept as it was written by the harness. |
| `questions_count` | integer | Always 53. |
| `context_max_tokens` | integer | 5000. Token budget for the retrieved context. Inert in the `sin` arm. |
| `retrieved_top_k` | integer | 7. Number of chunks requested from the retriever. Inert in the `sin` arm. |
| `num_ctx` | integer | 8192. Context window of the generation model. |
| `temperature` | integer | 0. Deterministic decoding. |
| `completed` | boolean | Always `true`: the run finished all 53 questions. |
| `rerun` | string | Always `sysrole_anti_refusal`. Tags the protocol under which these files were produced. |

### `summary` — per-run aggregate, as written by the harness

| Field | Type | Description |
|---|---|---|
| `total` | integer | Number of questions processed (53). |
| `correct` | integer | Number of records with `es_correcta == true`. |
| `accuracy` | float | `100 * correct / total`, unrounded. This is the number reported per model and arm in the article and reproduced in `aggregates/rag_benefit_summary.json`. |
| `latency_mean` | float | Mean of `latency_seconds` over the 53 records, in seconds. |
| `latency_median` | float | Median of `latency_seconds`, in seconds. The **median** is the statistic reported in the article (`lat_median_con`), being robust to the occasional slow inference. |

### `questions[]` — one object per inference (53 per file)

| Field | Type | Description |
|---|---|---|
| `id` | integer | Question identifier, 1–53. Joins to `datasets/dataset_gold_standard.json` (`id`) and, across arms and models, to itself: **the record with the same `id` in the `con` and `sin` reports of the same model is the paired observation** used for McNemar and for the paired confidence interval. |
| `pregunta` | string | The question stem exactly as presented to the model. |
| `opciones` | object | Map from option letter to option text, exactly as presented. Three keys: `a`, `b`, `c`. |
| `respuesta_correcta` | string | The gold answer letter. |
| `respuesta_ia` | string | **The model's complete free-text answer**, verbatim: its step-by-step reasoning and its final `RESPUESTA: <letter>` line. This is the field the error taxonomy and the detectability panel are computed over. See the redaction note below. |
| `opcion_detectada` | string | The option letter parsed out of `respuesta_ia`: `a`, `b`, `c`, or **`desconocida`** when no interpretable letter could be extracted (the model refused, hedged, or emitted no parseable final answer). There are **16** such records across the 424. `desconocida` counts as an error for accuracy, and is precisely what the taxonomy category **T5 (residual refusal)** captures — its existence under an anti-refusal protocol is one of the motivations for Protocol P2. |
| `es_correcta` | boolean | `opcion_detectada == respuesta_correcta`. **This is the accuracy field.** A `desconocida` record is always `false`. |
| `latency_seconds` | float | Wall-clock time of the single inference, in seconds. Measured on the local Windows 11 GPU workstation. Do not pool these with the latencies in `exploratory/`, which were measured on different hardware under Fedora. |
| `num_fragmentos` | integer | Number of retrieved chunks placed in the prompt. In the `sin` arm it is **always 0** (212 records). In the `con` arm it is 7 for 204 of the 212 records, and 5 or 6 for the remaining 8 (four each), where the token budget truncated the context. |

Note that there is **no `fragmentos` field**: the text of the retrieved chunks was never written to these reports. Their provenance (which document and page each retrieved chunk came from) is nevertheless recoverable from `aggregates/chunk_provenance.json`, which covers all 368 chunks retrieved for the 53 questions.

---

## Copyright treatment applied to `respuesta_ia`

The models were instructed to ground their answers in the retrieved evidence, and they frequently quote it. Passages of `respuesta_ia` that reproduced **50 or more consecutive words** of the source corpus were replaced in place by the literal marker

```
[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]
```

where *N* is the number of words removed. In this folder this affects **9 spans across 7 answers in 2 files, 550 words in total** — all in the `con` arm, where the model had the evidence in front of it:

| File | `id` | Spans | Words removed |
|---|---|---|---|
| `report_med42_..._sysrole_con_RERUN.json` | 1 | 2 | 101, 60 |
| `report_qwen7b_..._sysrole_con_RERUN.json` | 1 | 1 | 56 |
| `report_qwen7b_..._sysrole_con_RERUN.json` | 7 | 1 | 63 |
| `report_qwen7b_..._sysrole_con_RERUN.json` | 12 | 1 | 55 |
| `report_qwen7b_..._sysrole_con_RERUN.json` | 31 | 2 | 50, 50 |
| `report_qwen7b_..._sysrole_con_RERUN.json` | 38 | 1 | 51 |
| `report_qwen7b_..._sysrole_con_RERUN.json` | 40 | 1 | 64 |

By file: `report_med42_..._sysrole_con_RERUN.json` carries 2 spans (161 words) in 1 answer; `report_qwen7b_..._sysrole_con_RERUN.json` carries 7 spans (389 words) across 6 answers. The two `sin`-arm reports and the `llama8b` and `qlora` reports carry no redaction at all.

Only the overlapping span is replaced; the model's own reasoning around it is preserved untouched. Shorter quotations are retained under the academic right of quotation.

Two of these answers (`qwen7b`/`con`, ids 1 and 38) are also the two records where `aggregates/detectability_frontera.json` does not regenerate bit-for-bit: the covariates `len_chars` and `densidad_tecnica` were measured on the **original** text, which was longer. See caveat (g) of `VERIFICATION.md`.

**The redaction is cosmetic and strictly posterior to the experiments.** `es_correcta`, `opcion_detectada`, `latency_seconds` and every other field were computed on the original, unredacted answers and remain valid; no record was removed and no count changed (8 files × 53 records = 424). The complete unredacted data is held by the authors and is available on reasonable request for verification purposes.

---

## Re-deriving the published figures from these files

- **Accuracy of one model in one arm** = mean of `es_correcta` over the 53 records of that file (equivalently, `summary.accuracy`).
- **Pooled accuracy of one arm** = mean of `es_correcta` over the 4 files of that arm (212 records).
- **Paired analysis** = join the `con` and `sin` report of the same model on `id`. Over the 4 models this gives **212 paired observations**. McNemar's *b* = number of pairs where the with-RAG record is correct and the without-RAG record is not; *c* = the converse.
- The exact formulas, the resulting values and the source files are recorded in the repository's `derived_metrics.json`, and the audit that reproduces them is reported in `VERIFICATION.md`.
