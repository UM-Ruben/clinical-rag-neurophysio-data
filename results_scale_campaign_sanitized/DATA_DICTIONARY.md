# Data dictionary — `results_scale_campaign_sanitized/`

The seven raw reports of the **exploratory campaign along the scale axis**, run on the HPC cluster on 25 July 2026. They are published for one reason above all others: **they are the source of Table 3 of the article**, the table that compares seven models from 7B to 72B parameters under identical retrieval and hardware conditions.

The design is what makes the table readable. Every model answered **the same 53 gold-standard questions**, through **the same retrieval pipeline**, on **the same GPU**. Retrieval is therefore constant across rows — `recall_at_k` is `92.45 %` in all seven files, byte for byte — and any difference in accuracy is attributable to the generator alone, not to the evidence it received.

**Design:** 7 models × 1 arm (**with RAG only**) × 53 gold-standard questions = **371 inferences**, in **7 files** of 53 records each.

| | |
|---|---|
| Question bank | `datasets/dataset_gold_standard.json`, n = 53 (all answerable) |
| Index | the 9 corpus documents (6 teaching documents + 3 open-access stroke-guideline distractors) |
| Embeddings | `BAAI/bge-m3` |
| `retrieved_top_k` | 8 |
| Chunking | `chunk_size = 1300`, `chunk_overlap = 300` |
| `context_max_tokens` | 4800 |
| Recall threshold | `recall_overlap_threshold = 0.3` |
| `num_ctx` | 8192 (7–8B models), 16384 (70–72B models) |
| Executed | 25 July 2026, HPC cluster node, NVIDIA RTX 4090 (24 GB VRAM) |
| **Recall@k** | **49 / 53 = 92.453 %** — identical in all seven files |

> ### Warning: these accuracies are NOT the accuracies of Study P1
>
> This campaign and the definitive ablation (`results_ablation_p1/`) share the 53 questions but not the conditions. Three things differ:
>
> 1. **Different retrieval settings.** 1300/300-token chunks, a 4800-token context budget and top-8 injected fragments here; 1500/400, 5000 and top-7 in P1.
> 2. **No anti-refusal system role.** The `sysrole_anti_rechazo` framing that defines Protocol P1 is not applied here.
> 3. **A different corpus condition.** P1 measures on the multi-document corpus with the three stroke guidelines acting as *distractors*, which is why its recall is lower (88.7 % against 92.45 %).
>
> This is why the same `llama3.1:8b` scores **75.47 %** here and **81.13 %** in P1. Both figures are internally consistent within their own campaign, and the article says so explicitly. **Do not read them as repeated measurements of one quantity.**

---

## Files

```
report_{model}_GPU_{node}_{...}_SANITIZED.json
```

| File (abbreviated) | `header.model` | Label in the article | `summary.correct` | Accuracy | Median latency | Unparsable |
|---|---|---|---|---|---|---|
| `report_llama3.3_70b_GPU_4090_20260725` | `llama3.3:70b` | Llama-3.3-70B | 47 / 53 | 88.68 % | 149.6 s | 0 |
| `report_qwen2.5_72b_GPU_4090_20260725` | `qwen2.5:72b` | Qwen-2.5-72B | 47 / 53 | 88.68 % | 150.3 s | 0 |
| `report_llama3.1_8b_..._20260725_090008` | `llama3.1:8b` | Llama-3.1-8B | 40 / 53 | 75.47 % | 3.5 s | 0 |
| `report_qwen2.5_7b_..._20260725_090534` | `qwen2.5:7b` | Qwen-2.5-7B | 39 / 53 | 73.58 % | 3.5 s | 1 |
| `report_deepseek-llm_7b_..._20260725_091111` | `deepseek-llm:7b` | DeepSeek-LLM-7B | 20 / 53 | 37.74 % | 2.2 s | 6 |
| `report_medllama2_7b_..._20260725_091459` | `medllama2:7b` | Medllama2-7B (legacy) | 2 / 53 | 3.77 % | 0.3 s | 46 |
| `report_meditron_7b_..._20260725_091714` | `meditron:7b` | Meditron-7B (legacy) | 0 / 53 | 0.00 % | 0.2 s | 53 |

**Unparsable** is `summary.unknown`: responses from which the deterministic parser could extract no option letter. It is the column that explains the two legacy rows. Their near-zero accuracy is **not** weak clinical judgement but an inability to comply with the answer format: Meditron returned no parsable option in any of the 53 questions, Medllama2 in 46 of them. Both were served the English fall-back prompt (`prompt_language = "en"`, `is_medical_legacy_model = true`) with a reduced context budget, exactly as Table 2 of the article describes.

### A note on the file names

Five files carry `Cluster_Amdahl` in the name and two carry `4090`. **All seven ran on the same node and the same GPU.** `header.device` is `Cluster_Amdahl` and `header.hardware_type` is `Cluster_GPU` in all seven; the naming difference is an artefact of two separate submissions on the same day, not of two machines. The article's claim that the seven models share one GPU is verifiable in the headers, and in `gpu_residency.txt`.

---

## Top-level structure

Identical to `results_retrieval_exploratory_sanitized/`: three keys, `header`, `summary` and `questions`. Only the fields whose meaning is specific to this campaign are documented below; for the rest, see the dictionary of that folder.

### `header`

| Field | Meaning here |
|---|---|
| `device` | `Cluster_Amdahl` in all seven files. |
| `mode` | `GPU` in all seven. GPU-accelerated inference throughout; no CPU-only run is included. |
| `hardware_type` | `Cluster_GPU`. |
| `param_size` | `7b`, `8b`, `70b`, `72b`. The scale axis of the campaign. |
| `num_ctx` | 8192 for the 7–8B models, 16384 for the two massive ones. |
| `is_medical_legacy_model` | `true` only for `medllama2:7b` and `meditron:7b`, which triggers the English fall-back prompt and the reduced context window. |
| `no_rag` | `false` in all seven. There is no without-RAG arm in this campaign; the ablation is in `results_ablation_p1/`. |

### `summary`

| Field | Meaning here |
|---|---|
| `total`, `processed` | 53 in all seven files. |
| `correct`, `incorrect`, `unknown` | `unknown` is the Unparsable column of Table 3. `correct + incorrect + unknown = 53`. |
| `recall_hits`, `recall_at_k` | 49 and 92.4528…, **identical in all seven files**. This is the point of the design. |
| `accuracy` | `correct / total`, in per cent. Unparsable responses count as failures, the same criterion applied in both arms of Study P1. |

### `questions[]`

One object per inference, 53 per file. `latency_seconds` is the per-query wall-clock latency from which the median of Table 3 is taken.

---

## GPU residency

The `ollama ps` lines captured during the run, extracted verbatim from the Slurm job log. Columns are `NAME  ID  SIZE  PROCESSOR  CONTEXT  UNTIL`; the `--> VRAM` line that follows each block is the measured device memory.

```
llama3.1:8b    46e0c10c039e    6.3 GB    100% GPU     8192       4 minutes from now
  --> VRAM: 6216 MiB
qwen2.5:7b    845dbda0ea48    5.3 GB    100% GPU     8192       4 minutes from now
  --> VRAM: 5454 MiB
deepseek-llm:7b    9aab369a853b    6.1 GB    100% GPU     4096       4 minutes from now
qwen2.5:7b         845dbda0ea48    5.3 GB    100% GPU     8192       About a minute from now
  --> VRAM: 11689 MiB
medllama2:7b       a53737ec0c72    6.2 GB    100% GPU     4096       4 minutes from now
deepseek-llm:7b    9aab369a853b    6.1 GB    100% GPU     4096       2 minutes from now
  --> VRAM: 12479 MiB
medllama2:7b       a53737ec0c72    6.2 GB    100% GPU     4096       3 minutes from now
deepseek-llm:7b    9aab369a853b    6.1 GB    100% GPU     4096       48 seconds from now
  --> VRAM: 17700 MiB
llama3.3:70b    a6eb4748fd29    49 GB    52%/48% CPU/GPU    16384      4 minutes from now
  --> VRAM: 22120 MiB
qwen2.5:72b    424bad2cc13f    54 GB    56%/44% CPU/GPU    16384      4 minutes from now
  --> VRAM: 22030 MiB
```

They are the evidence for the article's claim that scale is not merely expensive but structurally unusable within a single-GPU budget:

- the 7–8B models are resident at **100 % GPU**;
- `llama3.3:70b` reports **49 GB** and splits execution **52 %/48 % CPU/GPU**;
- `qwen2.5:72b` reports **54 GB** and splits **56 %/44 %**;
- in both cases VRAM saturates at ~22 GB of the 24 GB available.

**The complete Slurm log is not published.** It interleaves the retrieved context of every query, so it reproduces the source corpus at length; it is held by the authors under the same terms as the rest of the unredacted material. Only the residency lines, which contain no corpus text, are extracted here.

---

## Sanitisation applied

Identical in method to the other report folders, and described in full in `NOTICE.md`.

**`fragmentos`.** The retrieved context passages were replaced with

```json
{ "sha256": "<sha256 of the passage, UTF-8>", "n_chars": 1246,
  "documento": "03_sistemas_motores_descendentes.pdf", "pagina": 9 }
```

**2 947 fragments** were processed (7 files × 53 questions × 8 passages, minus the questions where the retriever returned fewer), and **every one of them resolved to a source document and page**. Anyone holding a licensed copy of the corpus can confirm which passage was retrieved by hashing it; nobody without one can reconstruct the text. `pagina` is **0-indexed** over the PDF, so it is the printed page number minus the document's front matter.

Where the same passage occurs verbatim in more than one document at the same page index — the three stroke guidelines share boilerplate — `documento` is a list rather than a string.

**`respuesta_ia`.** Every free-text field was audited against the nine complete source documents, and passages reproducing **50 or more consecutive words** were replaced with the marker `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`, where *N* counts whitespace-delimited tokens in the removed span. In this folder that affects **21 spans across 3 files, 1 208 words removed**:

| File | Spans | Words |
|---|---|---|
| `report_qwen2.5_7b_...` | 12 | 700 |
| `report_qwen2.5_72b_...` | 7 | 392 |
| `report_llama3.3_70b_...` | 2 | 116 |
| The other four | 0 | 0 |

The distribution is itself informative: the models that quote the context at length are the ones that use it well. The two legacy fine-tunes required no redaction because they never produced a grounded answer at all.

Redaction is **cosmetic and strictly posterior to the experiments**. `es_correcta`, `opcion_detectada`, `retrieval_recall_hit` and every other derived field were computed on the original, unredacted answers and remain valid. No record was dropped and no count changed.

---

## Re-deriving Table 3 from these files

Every cell of Table 3 comes from `summary`, except the latency column, which is the median of `questions[].latency_seconds`:

```python
import json, glob, statistics

for f in sorted(glob.glob("results_scale_campaign_sanitized/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    lat = statistics.median(q["latency_seconds"] for q in d["questions"])
    s = d["summary"]
    print(f"{d['header']['model']:<18} n={s['total']} "
          f"acc={s['accuracy']:.2f}% unparsable={s['unknown']} "
          f"recall@k={s['recall_at_k']:.2f}% lat={lat:.1f}s")
```

The `SE` and `CI95%` columns of the article are the normal approximation, `1.96 · sqrt(s(1-s)/n)`, computed on those accuracies. As the article's own footnote states, that approximation is unreliable at the extremes and therefore should not be trusted for the two legacy rows.
