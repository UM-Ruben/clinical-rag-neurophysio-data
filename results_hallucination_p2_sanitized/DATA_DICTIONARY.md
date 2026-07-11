# Data dictionary — `results_hallucination_p2_sanitized/`

The raw inference records of **Study P2**, the hallucination experiment in which abstention is permitted.

**Design:** 4 models × 2 arms (with RAG / without RAG) × 3 question banks = **24 files**, **760 inferences**:

| Bank | Items | Records per arm | Records total |
|---|---|---|---|
| `original` (gold standard, answerable) | 53 | 212 | **424** |
| `trap` (false premise in the stem) | 24 | 96 | **192** |
| `ood` (unanswerable from the corpus) | 18 | 72 | **144** |
| | | | **760** |

The `_SANITIZED` suffix marks the copyright treatment described below. **No experimental field was altered by it.**

---

## Protocol P2 — `sysrole_abstain`

- **System role:** the same clinical framing as Protocol P1, but **without the anti-refusal clause**. It instructs the model to select the non-answer option when the evidence supports none of the alternatives.
- **Options:** `a`, `b`, `c` **plus a fourth option**:

  ```
  d) No puede responderse con la documentación disponible
  ```

  Abstention is a legitimate, first-class answer. It is the **correct** answer for all 18 OOD items and for 11 of the 24 TRAP items.
- **Retrieval and generation:** identical parameters to Protocol P1 (`top_k = 7`, `context_max_tokens = 5000`, `num_ctx = 8192`, `temperature = 0`, `BAAI/bge-m3` embeddings).

> ### Warning: P2 accuracies are NOT comparable with P1 accuracies
>
> 1. **The number of options changes** (4 here, 3 in P1): the chance baseline moves from 1/4 to 1/3.
> 2. **The success criterion changes.** Here abstention can be correct; in P1 it is impossible. An item on which a model correctly abstains counts as a success here and could not even arise there.
> 3. **The system role differs** in the anti-refusal clause, which is itself under study.
>
> Compare the two protocols on **hallucination and abstention rates** (`alucina`, `abstiene`), never on `es_correcta`.

---

## Files

```
report_{tag}_P2abstain_{banco}_{arm}_{timestamp}_SANITIZED.json
```

- `tag` ∈ `llama8b`, `qlora`, `qwen7b`, `med42`
- `banco` ∈ `original`, `trap`, `ood`
- `arm` ∈ `con` (with RAG), `sin` (without RAG)
- `timestamp` — execution time, `YYYYMMDD_HHMMSS`, preserved from the original filename.

---

## Top-level structure

Each file is a JSON object with three keys: `header`, `summary`, `questions`.

### `header` — run configuration

| Field | Type | Description |
|---|---|---|
| `protocolo` | string | Always `sysrole_abstain`. Identifies the protocol; do not mix with P1 reports. |
| `banco` | string | `original`, `trap` or `ood`. Which question bank this run used. |
| `model` | string | Model identifier as served by the local runtime. |
| `arm` | string | `con` = with RAG, `sin` = without RAG. **The experimental variable.** |
| `no_rag` | boolean | `true` in the `sin` arm. Redundant with `arm`. |
| `questions_count` | integer | 53, 24 or 18 depending on the bank. |
| `opcion_abstencion` | string | Always `d`. Which letter carries the abstention option. |
| `texto_opcion_d` | string | The exact text of option `d` as rendered in the prompt: `No puede responderse con la documentacion disponible` (stored without the accent, as it was presented to the models). |
| `retrieved_top_k` | integer | 7. Inert in the `sin` arm. |
| `context_max_tokens` | integer | 5000. Inert in the `sin` arm. |
| `num_ctx` | integer | 8192. |
| `temperature` | integer | 0. |
| `embedding_model` | string | `BAAI/bge-m3`. The embedding model of the retriever. |
| `timestamp` | string | ISO-8601 timestamp of the run. |
| `completed` | boolean | Always `true`. |

### `summary` — per-run aggregate, as written by the harness

| Field | Type | Description |
|---|---|---|
| `total` | integer | Records in the file. |
| `correct` | integer | Records with `es_correcta == true`. |
| `accuracy` | float | `100 * correct / total`. **Protocol-specific — not comparable with P1.** |
| `abstenciones` | integer | Records with `abstiene == true` (the model answered `d`), regardless of whether abstaining was correct. |
| `tasa_abstencion` | float | `100 * abstenciones / total`. |
| `alucinaciones` | integer | Records with `alucina == true`. See the definition below. In the `original` bank this is 0 by construction: every item there is answerable, so answering it cannot be a hallucination under this definition. |
| `n_items_abstencion_correcta` | integer | Number of items in this run for which abstaining (`d`) is the gold answer. 0 for the `original` bank, 18 for `ood`, 11 for `trap`. |
| `parse_desconocida` | integer | Records whose final answer could not be parsed into a letter (`opcion_detectada == "desconocida"`). Reported so that the reader can gauge how much of the result rests on unparseable output; the sensitivity analysis in `aggregates/hallucination_summary_resuelto.json` re-resolves these cases by hand. |
| `latency_mean` | float | Mean of `latency_seconds`, in seconds. |
| `latency_median` | float | Median of `latency_seconds`, in seconds. |

### `questions[]` — one object per inference

| Field | Type | Description |
|---|---|---|
| `id` | integer | Question identifier. Ranges are disjoint across banks: **1–53** (`original`), **1001–1024** (`trap`), **2001–2018** (`ood`). Joins to the corresponding file in `datasets/`. |
| `tipo` | string | Item type, and the key that makes the metrics computable. Four values: `original` (424 records), `trap_c` (104 records — a TRAP item where a lettered option is still correct), `trap_d` (88 records — a TRAP item whose correct answer is to abstain), `ood` (144 records). Note that `trap_c` + `trap_d` = 192, the TRAP total. |
| `pregunta` | string | The question stem exactly as presented. |
| `opciones` | object | Map from option letter to option text. Four keys: `a`, `b`, `c`, `d`. |
| `respuesta_correcta` | string | The gold answer letter. Always `d` in the `ood` bank. |
| `respuesta_ia` | string | **The model's complete free-text answer**, verbatim, including its final `RESPUESTA: <letter>` line. See the redaction note below. |
| `opcion_detectada` | string | The option letter parsed from `respuesta_ia`: `a`, `b`, `c`, `d`, or **`desconocida`** when no interpretable letter could be extracted. There are **20** such records across the 760. |
| `es_correcta` | boolean | `opcion_detectada == respuesta_correcta`. A `desconocida` record is `false`. **Not comparable with the P1 field of the same name.** |
| `abstiene` | boolean | `opcion_detectada == "d"`. The model declined to answer. This is a *behaviour*, not a *verdict*: abstaining is correct on OOD and `trap_d` items and incorrect on answerable ones. Its complement over the answerable bank is **coverage**. |
| `alucina` | boolean | **The central variable of the study.** `true` when the model answered a lettered option (`a`/`b`/`c`) on an item whose gold answer is `d` — that is, when it produced a confident substantive answer to a question the documentation cannot answer. It is therefore defined only on the **116 items per arm whose gold answer is `d`** (18 OOD × 4 models + 11 `trap_d` × 4 models = 72 + 44 = 116). On items with a lettered gold answer it is `false` by construction; a wrong lettered answer there is an ordinary error, not a hallucination. This is the field behind the pooled 64.7 % → 30.2 % result. |
| `latency_seconds` | float | Wall-clock time of the inference, in seconds. |
| `num_fragmentos` | integer | Number of retrieved chunks placed in the prompt. **Always 0 in the `sin` arm.** In the `con` arm: 7 for all TRAP and OOD records, and 7 for 204 of the 212 `original` records (5 or 6 for the remaining 8, where the token budget truncated the context). |
| `fragmentos` | array | The retrieved chunks. **Empty (`[]`) in the `sin` arm.** In the `con` arm it holds one object per chunk — **sanitised**, see below. |

---

## The `fragmentos` sanitisation

In the original reports, `fragmentos` was an array of **verbatim strings**: the exact text of the chunks retrieved from the teaching corpus. The corpus is third-party copyrighted material that we may not redistribute, and publishing those strings would amount to redistributing it piecemeal.

Each string has therefore been replaced by an **object describing it**, which preserves the field's scientific function — letting a reader establish exactly which chunk was retrieved — while removing the protected text itself. There are **2 648 such objects** across the 24 files (all in the `con` arm).

### Schema of a `fragmentos` element

| Key | Type | Description |
|---|---|---|
| `sha256` | string | Hex SHA-256 digest of the **exact UTF-8 bytes of the original chunk string**, unmodified and untrimmed. This is the verification handle: a reader holding a licensed copy of the corpus can rebuild the chunks with the published retrieval parameters (`chunk_size`, `chunk_overlap`, and the same extraction), hash them, and confirm byte-for-byte which chunk was retrieved for each question — without the text ever being redistributed here. |
| `n_chars` | integer | Character length of the original chunk string. Gives the size of the removed text and provides a cheap first check before hashing. |
| `documento` | string \| array \| null | The source document the chunk came from, e.g. `03_sistemas_motores_descendentes.pdf`. **Resolvable only for the `original` bank** (1 472 fragments). In **8 fragments** the value is an **array of two document names**: the chunk's text was matched in more than one document and the provenance is genuinely ambiguous, so both candidates are reported rather than an arbitrary choice. `null` for the `trap` and `ood` banks. |
| `pagina` | integer \| null | Page of `documento` on which the chunk begins. `null` for the `trap` and `ood` banks. |
| `provenance` | string | **Present only when provenance could not be resolved**, with the single value `"no_disponible"` (1 176 fragments, all from the `trap` and `ood` banks). Its absence means provenance *was* resolved and `documento`/`pagina` are populated. |

### Why provenance is missing for TRAP and OOD

The provenance map (`aggregates/chunk_provenance.json`) was built by reconstructing the 1 584 corpus chunks and matching them by exact text against the fragments retrieved **for the 53 gold-standard questions** — all 368 of which matched. No equivalent mapping was ever built for the TRAP and OOD banks, so for those the hash and the character count are published and the document/page fields are honestly marked `no_disponible` rather than guessed.

Documents `01`–`06` are the teaching corpus proper; `07`–`09` are the open-access stroke clinical-practice guidelines included in the index as **distractors**. Seeing a `07`/`08`/`09` document in `fragmentos` means the retriever pulled a distractor chunk into that question's context.

---

## Copyright treatment applied to `respuesta_ia`

The models were instructed to ground their answers in the retrieved evidence, and they frequently quote it. Passages of `respuesta_ia` reproducing **50 or more consecutive words** of the source corpus were replaced in place by the literal marker

```
[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]
```

where *N* is the number of words removed. In this folder this affects **4 spans in 4 answers across 3 files**, all in the `con` arm:

| File | `id` | Words removed |
|---|---|---|
| `report_med42_P2abstain_original_con_...` | 33 | 51 |
| `report_med42_P2abstain_trap_con_...` | 1010 | 61 |
| `report_qwen7b_P2abstain_original_con_...` | 7 | 63 |
| `report_qwen7b_P2abstain_original_con_...` | 12 | 55 |

Only the overlapping span is replaced; the model's own reasoning around it is preserved untouched. Shorter quotations are retained under the academic right of quotation.

**The redaction is cosmetic and strictly posterior to the experiments.** `es_correcta`, `opcion_detectada`, `abstiene`, `alucina` and every other field were computed on the original, unredacted answers and remain valid; no record was removed and no count changed (760 inferences). The complete unredacted data is held by the authors and is available on reasonable request for verification purposes.

---

## Re-deriving the headline figures

- **Pooled hallucination rate of an arm** = mean of `alucina` over the 116 records of that arm whose gold answer is `d` (the `ood` records plus the `trap_d` records, across the 4 models). Published values: `con` 35/116 = 30.17 %, `sin` 75/116 = 64.66 % (`aggregates/hallucination_summary.json`, key `pool`).
- **Pooled coverage of an arm** = fraction of the 212 `original` records of that arm with `abstiene == false`. Published values: `con` 178/212 = 83.96 %, `sin` 182/212 = 85.85 %. Coverage barely moves while hallucination halves — that is the point of the study.
- **Sycophancy** (whether the model swallows a false premise) is computed on the 13 `trap_c` items per model, using `opcion_que_acepta_la_premisa` from `datasets/dataset_trap_validado.json`; it appears as `complacencia_trap_c` in `aggregates/hallucination_summary.json`.
