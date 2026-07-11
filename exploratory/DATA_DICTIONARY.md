# Data dictionary — `exploratory/`

Data from the **preliminary scale-oriented campaign**: the opening exploration that motivated the study, in which 7 models of 7B to 72B parameters and 4 embedding models were screened on dual hardware.

> # DEPRECATED PHASE — READ BEFORE USING
>
> **This folder is not evidence for any claim of the article.** It is the exploration that *motivated* the research question, and it is published for completeness and honesty, not for reuse as a result. Two warnings apply, and both are serious.
>
> ### 1. Coverage is partial: 306 of 493 evaluations
>
> The campaign comprised **493 automated evaluations**. Only **306** per-item records survive, in `datos_detallados_preguntas.csv`. The remaining 187 were measured on the original **Fedora** workstation and were **not preserved** through the project's migration to Windows. Every surviving row belongs to the HPC-cluster half of the campaign: `device` is `Cluster_Amdahl` and `mode` is `CPU` in all 306 rows. **The local-GPU rows are precisely the ones that were lost.**
>
> Consequence: the three aggregate files in this folder (`modelos_ranking.csv`, `embeddings_ranking.csv`, `resumen_ejecutivo.json`) were computed **at the time, over the complete 493 evaluations**, and are preserved exactly as they were produced. **They cannot be recomputed from the 306 surviving rows, and any attempt to do so will disagree with them.** The disagreement is expected and is not an error in the files. This gap is why the article's reproducibility checklist answers `[partially]` on the public availability of all data sets.
>
> ### 2. Not comparable with the definitive results
>
> These numbers were produced under a **different configuration** from Studies P1 and P2, and must never be pooled with them or plotted on the same axis:
>
> - **Different retrieval parameters** — `chunk_size = 1300`, `chunk_overlap = 300`, `retrieved_top_k = 8`, `context_max_tokens = 4800`, against 1500 / 400 / 7 / 5000 in the definitive experiments.
> - **Different embedding models** — four were screened here; the definitive studies settled on `BAAI/bge-m3` alone.
> - **Different hardware** — an HPC CPU cluster (surviving rows) and a Fedora GPU workstation (lost rows), against the Windows 11 local GPU workstation of the definitive runs. **Latencies from this folder must never be pooled with those of `results_ablation_p1/` or `results_hallucination_p2_sanitized/`**: they measure different machines. The four-figure CPU latencies here are a property of the cluster, not of the models.
> - **A simpler answer-extraction routine** than the one used later, which alone accounts for part of the very low accuracies recorded here.
>
> The definitive experiments (P1, 424 inferences; P2, 760 inferences) are preserved **in full** elsewhere in this repository, and every claim of the article rests on those.

> ### Warning: P1 and P2 accuracies are NOT comparable with each other either
>
> This warning is repeated in every `DATA_DICTIONARY.md` of the repository, including this one, because it applies to any reuse of the definitive data. Protocol P2 (`results_hallucination_p2_sanitized/`) offers **four** options instead of the three of Protocol P1 (`results_ablation_p1/`) — moving the chance baseline from 1/3 to 1/4 — and **permits abstention**, which changes the success criterion itself: in P2 abstaining is the *correct* answer on every OOD item and on 11 of the 24 TRAP items, whereas in P1 it is forbidden by the anti-refusal clause of the system role, which is itself one of the variables under study.
>
> Compare the two protocols on **hallucination and abstention rates**, never on raw accuracy. And note that the accuracies in *this* folder are comparable with neither of them, for the reasons given above.

---

## `datos_detallados_preguntas.csv` — the surviving per-question records

**306 rows** (of 493), one per model-question evaluation. Comma-delimited, UTF-8, header row. The 32 columns fall into four groups: run identification, retrieval configuration, the per-question result, and the parent report's summary (denormalised onto every row).

### Run identification

| Column | Type | Description |
|---|---|---|
| `source_file` | string | Filename of the original raw report this row was extracted from, e.g. `report_deepseek-llm_7b_CPU_Cluster_Amdahl_bge-m3_20260222_085540.json`. **Those raw reports are not published**: they embed verbatim passages of the copyrighted teaching corpus. The name is retained so that rows can be grouped by run. |
| `timestamp` | string | ISO-8601 timestamp of the evaluation. |
| `model` | string | The evaluated model, e.g. `llama3.3:70b`, `qwen2.5:7b`, `meditron:7b`. Seven distinct values across the campaign. |
| `device` | string | Machine the run executed on. **`Cluster_Amdahl` in all 306 surviving rows** — the HPC cluster. Rows with the local GPU device are the ones that did not survive. |
| `mode` | string | **`CPU` in all 306 surviving rows.** |
| `param_size` | string | Parameter count of the model, e.g. `7b`, `70b`. |
| `hardware_type` | string | Hardware class, e.g. `Cluster_CPU`. |
| `model_size_class` | string | Size bucket used for the analysis, e.g. `7B/8B (Ligero)` — "lightweight". |

### Retrieval configuration

| Column | Type | Description |
|---|---|---|
| `embedding_model` | string | The embedding model used for retrieval in this run. Four values across the surviving rows: `BAAI/bge-m3` (255 rows), and `sentence-transformers/all-MiniLM-L6-v2`, `intfloat/multilingual-e5-large`, `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (17 rows each). |
| `chunk_size` | integer | Chunk size, in characters. `1300` — **not** the 1500 of the definitive experiments. |
| `chunk_overlap` | integer | Chunk overlap. `300` — not the 400 used later. |
| `context_max_tokens` | integer | Context budget. `4800` — not the 5000 used later. |
| `retrieved_top_k` | integer | Chunks requested from the retriever. `8` — not the 7 used later. |

### Per-question result

| Column | Type | Description |
|---|---|---|
| `question_id` | integer | Question identifier **within the preliminary bank**. This bank is **not** the 53-item gold standard of the definitive studies: every surviving run here evaluates a **17-question** set (`summary_total = 17` in all 306 rows), and a model's total in `modelos_ranking.csv` is the sum over its reports, e.g. 3 × 17 = 51. Do **not** join these ids to `datasets/dataset_gold_standard.json`. |
| `question_text` | string | The question stem. |
| `correct_option` | string | The gold answer letter. |
| `detected_option` | string | The letter parsed from the model's answer. |
| `is_correct` | boolean | Written as the strings `True` / `False`. Whether `detected_option` matched `correct_option`. |
| `latency_seconds` | float | Wall-clock time of the inference, in seconds. **CPU-cluster latencies: not comparable with the GPU latencies of the definitive experiments.** |
| `timed_out` | boolean | `True` / `False`. Whether the inference exceeded the time limit. |
| `use_case_classification` | string | The deployment scenario the measured latency would permit, e.g. `Segunda Opinión Asíncrona` ("asynchronous second opinion") — a slow-but-tolerable use, as opposed to interactive use. This is the field behind the article's argument that heavyweight models, while more accurate, are latency-barred from interactive clinical use. |
| `answer_confidence` | float | Confidence value emitted by the model for its answer, 0–1. |
| `num_fragmentos` | integer | Number of retrieved chunks placed in the prompt. |
| `retrieval_recall_hit` | boolean | `True` / `False`. Whether the retriever brought back the chunk that actually contains the answer — a retrieval-quality measure, independent of whether the model then got the question right. |
| `retrieval_overlap` | float | Lexical overlap between the retrieved context and the reference passage, 0–1. A graded companion to `retrieval_recall_hit`. |

### Parent-report summary (denormalised: identical across all rows of the same `source_file`)

These columns describe the **whole run**, not the row. Aggregating them naively across rows will double-count.

| Column | Type | Description |
|---|---|---|
| `summary_total` | integer | Questions in the run. |
| `summary_processed` | integer | Questions actually processed. |
| `summary_correct` | integer | Correct answers in the run. |
| `summary_incorrect` | integer | Incorrect answers in the run. |
| `summary_unknown` | integer | Answers with no parseable option. |
| `summary_recall_at_k` | float | Retrieval recall@k over the run, in per cent. **`82.35` (= 14/17) in all 306 surviving rows.** |
| `summary_accuracy` | float | Accuracy of the run, in per cent. |

> ### These recall figures are NOT the article's 88.7 % — do not confuse the two
>
> `retrieval_recall_hit` and `summary_recall_at_k` here describe **this deprecated campaign only**: a 17-question preliminary bank, `retrieved_top_k = 8`, four embedding models, CPU cluster. Over the 306 surviving rows the recall@k is **252/306 = 82.35 %**.
>
> **The article's `recall@k = 88.7 %` is a different measurement and lives elsewhere**, in `results_retrieval_exploratory_sanitized/`: 47 of 53 gold-standard questions, `retrieved_top_k = 7`, `BAAI/bge-m3`, the definitive 9-document index, local GPU. The two numbers share a field name and a heuristic — the same token-overlap rule, defined in full in that folder's dictionary — and nothing else. Neither is a human relevance judgement.
>
> The 8 Study-P1 reports carry **no retrieval-recall field at all**; the recall of the context they used is the 88.7 % measured in `results_retrieval_exploratory_sanitized/`, whose fragments they replayed. `aggregates/chunk_provenance.json` supports only a coarser, **document-level** check — for the 30 gold-standard questions whose source document is known, the retriever returned that document in **30 of 30 cases** — which is again a different quantity. See caveat (e) of `VERIFICATION.md`.

---

## `modelos_ranking.csv` — model ranking (computed over the complete 493)

7 rows, one per screened model, ordered by accuracy. Comma-delimited.

| Column | Type | Description |
|---|---|---|
| `model` | string | The model. |
| `accuracy` | float | Accuracy in per cent, over all of that model's evaluations in the campaign. |
| `total_questions` | integer | Evaluations contributing to the figure. **These sum to 493 across the seven rows** — the complete campaign, including the 187 evaluations whose per-question detail was lost. |
| `correct_answers` | integer | Correct answers. |
| `reports` | integer | Number of raw reports aggregated. |
| `embeddings` | string | Comma-separated list of the embedding models the figure aggregates over. Note that most models were screened with `BAAI/bge-m3` only, while `qwen2.5:7b` was the model used to screen all four embedding models — so its row aggregates over a heterogeneous set of runs, and its accuracy is not on equal footing with the others'. |

The headline of this file, and the one the article cites, is that the largest model (`llama3.3:70b`) leads on accuracy — while, per `use_case_classification` above, being far too slow on CPU for interactive use. That tension is what motivated the turn to lightweight models and to isolating the contribution of retrieval.

## `embeddings_ranking.csv` — embedding-model ranking (computed over the complete 493)

4 rows, one per screened embedding model. Same shape:

| Column | Type | Description |
|---|---|---|
| `embedding` | string | The embedding model. |
| `accuracy` | float | Accuracy in per cent of the runs that used it. |
| `total_questions` | integer | Evaluations contributing. |
| `correct_answers` | integer | Correct answers. |
| `reports` | integer | Raw reports aggregated. |
| `models` | string | Comma-separated list of the generation models the figure aggregates over. |

**Read this ranking with care, and do not read a winner out of it.** The comparison is badly unbalanced: `BAAI/bge-m3` was screened across all seven generation models and 391 evaluations, whereas each of the other three was screened only with `qwen2.5:7b`, over 34 evaluations. The accuracies therefore aggregate over different generation models and different sample sizes, and are not a controlled comparison of the embedding models. `BAAI/bge-m3` was adopted for the definitive experiments.

## `resumen_ejecutivo.json` — executive summary (computed over the complete 493)

A small JSON object with two blocks.

| Field | Type | Description |
|---|---|---|
| `metadata.total_reports` | integer | 29 — raw reports in the complete campaign. |
| `metadata.total_questions_evaluated` | integer | **493** — the complete campaign. Contrast with the **306** rows preserved in `datos_detallados_preguntas.csv`: the gap is the 187 lost Fedora evaluations. |
| `metadata.total_correct` | integer | 161. |
| `metadata.overall_accuracy` | float | 32.66 — per cent, over the whole campaign. Low by design: it pools every model screened, including the legacy medical models that failed almost completely, and it uses the simpler answer-extraction routine of this phase. **It is not a baseline for anything in the definitive studies.** |
| `metadata.models_tested` | integer | 7. |
| `metadata.embeddings_tested` | integer | 4. |
| `top_performers.best_model` | string | The most accurate model of the campaign. |
| `top_performers.best_model_accuracy` | float | Its accuracy, in per cent. |
| `top_performers.best_embedding` | string | The embedding model with the highest accuracy — subject to the unbalanced-comparison caveat above, which is why it is *not* the one adopted for the definitive experiments. |
| `top_performers.best_embedding_accuracy` | float | Its accuracy, in per cent. |
