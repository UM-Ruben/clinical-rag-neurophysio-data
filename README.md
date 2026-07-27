# clinical-rag-neurophysio-data

Research data accompanying the article **"Las Bondades del RAG"** (*The Benefits of RAG*) — an empirical quantification of the benefit of context retrieval in a lightweight, private, on-premise clinical assistant for neurophysiotherapy in Spanish.

**Authors:** Rubén Fernández García (<ruben.fernandezg@um.es>), José Manuel García Carrasco (<jmgarcia@um.es>) — Universidad de Murcia, Spain.
**Article status:** submitted to the *Journal of Artificial Intelligence Research* (JAIR), **under review**.
**Data license:** [CC BY 4.0](LICENSE) — see the [scope note](#license): short third-party quotations are excluded.
**Code license:** [MIT](code/LICENSE-CODE) — the code in `code/` is licensed separately from the data.

> This repository contains **the data and the code**. The **teaching corpus is not** published (third-party copyright), and neither is the **QLoRA fine-tuning pipeline**, whose training data derives from that corpus. See [What is NOT included and why](#what-is-not-included-and-why).
>
> `python code/reproduce.py` regenerates every regenerable aggregate **from the published data alone** — no corpus, no GPU, no network — and cross-checks it against the published files. **Exit 0 means everything matches.**

---

**Language / Idioma** — [English](#english) · [Español](#español)

---

<a id="english"></a>

# English

## Contents

- [Relation to the article](#relation-to-the-article)
- [What this repository contains](#what-this-repository-contains)
- [The code](#the-code)
- [What is NOT included and why](#what-is-not-included-and-why)
- [Repository structure](#repository-structure)
- [How to verify the data](#how-to-verify-the-data)
- [License](#license)
- [How to cite](#how-to-cite)
- [Contact](#contact)

## Relation to the article

The article evaluates a Retrieval-Augmented Generation (RAG) assistant built on lightweight, locally deployable language models (7B–8B class), over a Spanish-language corpus of neurophysiotherapy teaching material to which open-access stroke clinical-practice guidelines were added as distractors. Retrieval is hybrid (BM25 + FAISS with `BAAI/bge-m3` embeddings and a cross-encoder re-ranker, `top_k = 7`); generation is deterministic (`temperature = 0`, `num_ctx = 8192`).

Two experiments underpin the paper, and both are published here in full:

| | **Study P1 — ablation** | **Study P2 — hallucination** |
|---|---|---|
| Question | Does retrieval improve accuracy? | Does retrieval stop the model from answering the unanswerable? |
| Design | 4 models × {with RAG, without RAG} × 53 questions | 4 models × {with RAG, without RAG} × 3 banks (53 answerable + 24 false-premise TRAP + 18 out-of-distribution OOD) |
| Inferences | **424** | **760** |
| Options offered | `a` / `b` / `c` — abstention is forbidden by design (anti-refusal clinical framing) | `a` / `b` / `c` / **`d) No puede responderse con la documentación disponible`** — abstention is a legitimate answer |
| Headline result | RAG improves **4/4** models; pooled **+12.7 pp** over 212 paired evaluations (McNemar *p* ≈ 0.001) | Pooled hallucination falls from **64.7 %** to **30.2 %**, with coverage essentially unchanged (85.9 % → 84.0 %) |

Preceding both, and also published here in full, is the **exploratory campaign along the scale axis**: 7 models from 7B to 72B parameters × with-RAG × the same 53 questions = **371 inferences**, all seven under identical retrieval (`recall@k = 92.45 %`) and on the same cluster RTX 4090. It is the source of **Table 3** and of the accuracy-latency contrast the paper draws between scale and interactivity (88.68 % at 149.6 s against 75.47 % at 3.5 s). It lives in `results_scale_campaign_sanitized/`.

Two further analyses are also published: an adjudicated **taxonomy of the 131 erroneous P1 responses** (five mutually exclusive categories, T1–T5) and a **blind detectability panel** in which **three LLM judges** (two weak local models and one frontier model) rate how detectable each error is without access to the ground truth. The panel contains **no independent human rater**: see [point 6 below](#6-there-is-no-independent-human-validation).

> ### Warning: P1 and P2 accuracies are NOT comparable with each other
>
> The two protocols differ in three ways that all move the accuracy number:
>
> 1. P2 adds a fourth option, so the chance baseline moves from 1/3 to 1/4.
> 2. In P1 abstention is impossible; in P2 abstention is the *correct* answer for every OOD item and for 11 of the 24 TRAP items.
> 3. The system role differs precisely in the anti-refusal clause — which is itself part of what is under study.
>
> Any cross-protocol comparison must be made on **hallucination and abstention rates**, never on raw accuracy. Each `DATA_DICTIONARY.md` repeats this warning.

## What this repository contains

| Folder | Contents |
|---|---|
| `datasets/` | The three question banks: the 53-item Gold Standard, the 24-item TRAP bank (false premise embedded in the stem) and the 18-item OOD bank (unanswerable from the corpus). |
| `results_ablation_p1/` | The 8 raw reports of Study P1 (4 models × 2 arms), 53 records each = **424 inferences**, including each model's full free-text reasoning. These reports carry **no corpus fragments**. |
| `results_hallucination_p2_sanitized/` | The 24 raw reports of Study P2 (4 models × 2 arms × 3 banks) = **760 inferences**. The retrieved context (`fragmentos`) has been **replaced by SHA-256 hashes** — see below. |
| `results_retrieval_exploratory_sanitized/` | The 4 raw reports of the exploratory retrieval campaign over the definitive 9-document index (4 models × with-RAG × 53 questions) = **212 inferences**. They are the **source of the article's `recall@k = 88.7 %`** (47/53 in each of the four) and they hold the **retrieved context that Study P1 replayed**, so they close the provenance chain of `results_ablation_p1/`. `fragmentos` is hashed here too. **Their accuracy figures are not P1's** — see the dictionary in the folder. |
| `results_scale_campaign_sanitized/` | The 7 raw reports of the **exploratory campaign along the scale axis** (7 models from 7B to 72B × with-RAG × 53 questions) = **371 inferences**, run on the cluster RTX 4090 on 25 July 2026. They are the **source of Table 3 of the article**. Retrieval is identical across all seven (`recall@k = 92.45 %`, 49/53 in every file), so any difference in accuracy belongs to the generator alone. `fragmentos` is hashed here too. **Their accuracy figures are not P1's** — see the dictionary in the folder. |
| `aggregates/` | 16 pre-computed summary and per-item analysis files: RAG benefit, hallucination, error taxonomy (including the two LLM judges' pre-labelling), detectability panel, retrieval provenance, resolution of the unparsed answers and distractor effect. |
| `annotation/` | The review material and the answer keys for the detectability panel and the error taxonomy. **Despite the file names, it holds no independent human ratings** — see [point 6](#6-there-is-no-independent-human-validation). |
| `exploratory/` | Partial raw data and rankings from an **earlier, superseded** preliminary campaign: 493 evaluations over a 17-question bank on the CPU cluster. **Deprecated, and not the campaign the article reports** — the article's scale campaign is `results_scale_campaign_sanitized/`. See the caveats below and in `exploratory/DATA_DICTIONARY.md`. |
| `code/` | The study's source code: an **analysis layer** (13 files) runnable against the published data alone, an **inference layer** (9 scripts) published for inspection, and `reproduce.py`, which verifies the whole study with one command. **MIT licence**, separate from the data. See [The code](#the-code). |

Field names inside the data files are in **Spanish** (`pregunta`, `respuesta_ia`, `es_correcta`, `abstiene`, `alucina`, …). Every field is documented **in English** in the `DATA_DICTIONARY.md` of its folder.

## The code

The code is published in [`code/`](code/), under the **MIT licence** ([`code/LICENSE-CODE`](code/LICENSE-CODE)) — deliberately **different from the CC BY 4.0 of the data**, so that the scripts can be reused without the attribution conditions attaching to the dataset. `code/README.md` documents it in full, and `code/EXCLUDED.md` lists every script of the working project that is *not* published, with its reason.

**Verify the whole study with one command:**

```bash
pip install -r code/requirements.txt
python code/reproduce.py          # exit 0 = every regenerable figure matches the published one
```

`reproduce.py` needs **no corpus, no GPU, no model server and no network**. It regenerates each regenerable aggregate from the raw published records, compares it field by field with the published file, prints an `ARTEFACT | REGENERATED | PUBLISHED | MATCHES?` table, and exits non-zero if anything fails to match. It ends by listing, explicitly, everything that is *not* reproducible and why. It currently reports **two controlled divergences**, both documented in `VERIFICATION.md`; neither changes a figure of the article.

**Two layers, and an honest line between them:**

- **`code/analysis/` — runs on the published data alone.** The entire statistical layer: the ablation audit, the hallucination aggregation, the error taxonomy, the detectability panel, the LaTeX tables and the figures. This layer is fully reproducible by anyone.
- **`code/inference/` — published to be *read*, not run.** The retrieval engine, the two experimental protocols, the LLM judges and the question-bank builders. Running them requires the **teaching corpus** (nine copyrighted PDFs, not distributable) and/or a local **Ollama** server. Each file states this in its header.
- **The QLoRA fine-tuning pipeline is not published at all.** Its training data is derived from the copyrighted corpus, so neither the adapter weights nor the training scripts can be released. **The consequence, stated plainly: the QLoRA arm of this study is not reproducible by third parties.** The other three models — `llama3.1:8b`, `qwen2.5:7b` and `thewindmom/llama3-med42-8b` — are public on Ollama and **are** reproducible. Everything downstream of inference remains verifiable for all four models, because the raw per-question outputs of all four are published.

No script under `code/` contains a redacted corpus quotation: the copyright redaction described below touches the data files only.

## What is NOT included and why

We prefer to be explicit about what a reader will look for and not find.

### 1. The teaching corpus is not published (third-party copyright)

The thematic documents that constitute the knowledge base are teaching material authored by third parties. **We do not hold redistribution rights over them**, so neither the PDFs, nor their extracted text, nor the chunked index are included here. The three distractor documents are open-access stroke clinical-practice guidelines and can be obtained from their publishers.

Consequence: the retrieval pipeline **cannot be re-run end to end** from this repository alone. What *can* be done is to re-derive every reported number from the raw inference records, which are complete.

### 2. The QLoRA fine-tuning pipeline is not published — so the QLoRA arm is not reproducible

**The source code *is* published** (in `code/` — see [The code](#the-code)); this section records the one part of it that is not, and the consequence.

The `neurofisio-qlora` adapter was fine-tuned on data **derived from the copyrighted teaching corpus**. Publishing the training scripts would mean publishing the corpus passages they embed, and publishing the adapter weights would mean distributing a model trained on material we may not redistribute. Neither the weights nor the dataset-generation and fine-tuning scripts are therefore released; `code/EXCLUDED.md` names each excluded file.

**The honest consequence: the QLoRA arm of this study cannot be reproduced by a third party.** The other three models — `llama3.1:8b`, `qwen2.5:7b` and `thewindmom/llama3-med42-8b` — are all public on Ollama, and their arms *are* reproducible end to end by anyone who also holds a licensed copy of the corpus. Everything **downstream of inference** — every statistic, table and figure — remains verifiable for all four models, because the raw per-question outputs of all four are published and `code/analysis/` recomputes the numbers from them.

The operative parameters are additionally repeated in the `header` block of every raw report published here (`retrieved_top_k`, `context_max_tokens`, `num_ctx`, `temperature`, …). Note that `embedding_model` (`BAAI/bge-m3`) is recorded in the header of the **24 Study-P2 reports only**; the 8 Study-P1 reports do not carry that field, and for them the embedding model is documented in the article, in this README and in `code/inference/evaluate_rag.py` rather than in the file itself.

### 3. In the P2 reports, the retrieved passages were replaced by SHA-256 hashes

The 24 raw reports of Study P2 originally carried, for every question in the with-RAG arm, the verbatim passages retrieved from the corpus. Publishing them would amount to redistributing the copyrighted corpus piecemeal. In the `_SANITIZED` files each passage string has therefore been replaced by an object of this form:

```json
{"sha256": "12036c6aeff1e6872ec1896465278d484102baa0331d5c56d74ba13b89ccc9c8",
 "n_chars": 606,
 "documento": "03_sistemas_motores_descendentes.pdf",
 "pagina": 14}
```

This preserves the scientific function of the field while removing only the protected text itself. A reader who holds a licensed copy of the corpus can rebuild the chunks with the published parameters, hash them, and **verify exactly which passage was retrieved for every question** — without a single line of protected text being redistributed here. Document and page are resolvable only for the `original` bank (via `aggregates/chunk_provenance.json`); for the TRAP and OOD banks no provenance mapping exists, and those fragments carry `"documento": null, "pagina": null, "provenance": "no_disponible"`. The full schema is documented in `results_hallucination_p2_sanitized/DATA_DICTIONARY.md`.

The same treatment is applied to the four reports of `results_retrieval_exploratory_sanitized/` (1 472 fragments, **all** of them carrying document and page, since they belong to the `original` bank) and to the seven reports of `results_scale_campaign_sanitized/` (2 947 fragments, likewise **all** carrying document and page). The P1 reports never contained the retrieved passages, so they required no such treatment — and the context they consumed is not lost: they **replayed** the fragments of those four exploratory reports, whose 1 472 hashes match, position for position, the ones published for P2.

### 4. Long verbatim quotations of the corpus were redacted, in every free-text field

The models were instructed to ground their answers in the retrieved evidence, and they frequently quote it; the hand-built evidence fields (`traza_cita`, `cita_soporte`) were, by construction, copied from the corpus. **Every free-text field of every published file** was audited against the **nine complete source documents** (not against the retrieved chunks, which would be blind to quotations crossing a chunk boundary). Passages reproducing **50 or more consecutive words** of the corpus were replaced in place by the literal marker:

```
[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]
```

where *N* is the number of words removed. Only the overlapping span is replaced; the surrounding text (the model's own reasoning, or the rest of the field) is preserved untouched.

This affects **64 spans across 16 files, 3 676 words removed in total**, the longest span being 101 words and the shortest 50. By folder:

| Folder | Spans | Files | Words removed |
|---|---|---|---|
| `results_ablation_p1/` | 9 | 2 | 550 |
| `results_hallucination_p2_sanitized/` | 9 | 4 | 490 |
| `results_retrieval_exploratory_sanitized/` | 6 | 3 | 350 |
| `results_scale_campaign_sanitized/` | 21 | 3 | 1 208 |
| `datasets/` | 4 | 1 | 231 |
| `aggregates/` | 15 | 3 | 847 |
| `code/` | **0** | 0 | 0 |
| **Total** | **64** | **16** | **3 676** |

By field: **45** in `respuesta_ia` (2 598 words — the four report folders, all in the with-RAG arm), **14** in `cita_soporte` (796 words — 7 in `aggregates/taxonomia_errores.json` and 7 in `aggregates/errores_prelabel.json`, which carries the same judge citations), **4** in `traza_cita` (231 words — `datasets/dataset_gold_standard.json`) and **1** in `cola` (51 words — `aggregates/resolucion_no_parseadas.json`). **No script under `code/` contains a redacted span**: no published script reproduces 50 or more consecutive words of the corpus.

For the two evidence fields the provenance is retained so the field still does its job: `dataset_gold_standard.json` keeps its `documento_fuente` and `traza_pagina` siblings, and in `taxonomia_errores.json` the marker is followed by an explicit `Ref.: <document>, p. <page>`. `dataset_trap_validado.json` was audited and required no redaction (longest overlap: 49 words).

**Shorter quotations are preserved** under the academic right of quotation: spans of 12 to 49 consecutive words remain in the free-text fields, scattered and non-contiguous, and they do not permit the reconstruction of any source document. A census of those short quotations can only be produced against the source corpus, which is not published here, so no count of them is asserted in this release. Redaction is cosmetic and strictly posterior to the experiments: `es_correcta`, `opcion_detectada`, `abstiene`, `alucina`, `retrieval_recall_hit` and every other derived field were computed on the original, unredacted answers and remain valid; no record was dropped and no count changed. Caveat (d) of `VERIFICATION.md` documents the audit method and the full per-file breakdown.

**The complete, unredacted raw data is held by the authors and is available on reasonable request for verification purposes** — for instance, to a reviewer or editor who needs to audit the full model outputs — subject to the copyright constraints of the underlying teaching corpus.

### 5. An earlier preliminary campaign is superseded, and only partially preserved

**The scale campaign the article reports is published in full.** It is `results_scale_campaign_sanitized/`: **371 evaluations**, 7 models × 53 questions, all seven under identical retrieval and on the same cluster GPU. Every cell of Table 3 is re-derivable from those files, and `recall@k = 92.45 %` is byte-identical in all seven. Nothing about that campaign is missing.

What is only partially preserved is an **earlier campaign that the published one superseded**, kept in `exploratory/` for the historical record. It comprised **493 automated evaluations** across 7 models and 4 embedding models on dual hardware, over a **17-question** preliminary bank that is not the 53-item gold standard. Only **306 of those 493** per-item records survive, in `exploratory/datos_detallados_preguntas.csv`; the remainder was measured under Fedora and was not preserved through the project's migration to Windows. Every surviving row belongs to the HPC-cluster half (`device = Cluster_Amdahl`, `mode = CPU`).

The three aggregate files in `exploratory/` (`modelos_ranking.csv`, `embeddings_ranking.csv`, `resumen_ejecutivo.json`) were computed at the time over the **complete 493 evaluations** and are preserved exactly as they were produced; they therefore **cannot be recomputed from the 306 surviving rows**.

> **Do not read the numbers in `exploratory/` against the article.** They belong to the superseded campaign: a different question bank, a different retrieval configuration and a simpler answer-extraction routine. The `58.82 %` best-model accuracy recorded in `exploratory/resumen_ejecutivo.json` is **not** a figure of the article, and no claim in the paper rests on it. The article's opening campaign is the 371-evaluation one, and the two definitive experiments (P1, 424 inferences; P2, 760 inferences) are preserved in full.

### 6. There is no independent human validation

The folder is called `annotation/` and one of its files is called `detectabilidad_humano.csv`. **Neither name should be read as a claim of independent human annotation, because there is none.** This is the single most important caveat in this repository, and we state it plainly.

What actually happened: the **frontier LLM judge** produced the labels, and the **author reviewed its output and endorsed it in full**.

- **Error taxonomy.** `categoria_final` in `aggregates/taxonomia_errores.json` equals the frontier judge's label in `aggregates/taxonomia_frontera.json` on **131 of 131 cases**. The reviewer accepted every category and modified none: raw agreement is **1.00** by construction.
- **Detectability panel.** The 240 values of `annotation/detectabilidad_humano.csv` (80 cases × 3 fields) are **identical, value for value, to the frontier judge's ratings** in `aggregates/detectability_frontera.json` — continuous probabilities to three decimals included. The reviewer likewise accepted the 42 items of the banks without withdrawing any.

This is an **expert confirmation of an automatic result, not an independent re-annotation.** It follows that:

- **There is no independent human evaluator in this work**, and the blind detectability panel is composed of **three language models** (two weak local models and one frontier model) and nobody else.
- **No human–machine agreement can be computed, and none is published.** Any kappa obtained by comparing `annotation/` against `aggregates/` would be 1.00 by construction and would be an artefact, not a result. Do not use these files as a second annotator.
- The **only** inter-rater agreement in this repository is **between the two automatic judges**: Cohen's kappa = **0.223** (local judge vs frontier judge, n = 131, raw agreement 0.405) and **0.468** (judge 1 vs judge 2, n = 40), both in `aggregates/taxonomia_resumen.json` → `acuerdo`. That low first figure is precisely why the frontier judge's labels, and not the local judge's, were the ones carried forward.

The article states the same thing. We would rather publish a weak claim honestly than a strong one we cannot support.

## Repository structure

```
clinical-rag-neurophysio-data/
├── README.md                  this file
├── LICENSE                    CC BY 4.0 full legal code (the DATA)
├── NOTICE.md                  scope of the licences: what is ours and what is third-party (EN/ES)
├── CITATION.cff               machine-readable citation metadata
├── datapackage.json           Frictionless Data descriptor
├── MANIFEST.sha256            SHA-256 digest of every published file
├── VERIFICATION.md            release audit: what was re-derived, what matched, what did not
├── derived_metrics.json       figures recomputed from the raw records for this release
├── code/                      the study's source code — MIT licence (NOT CC BY 4.0)
│   ├── README.md              what runs without the corpus, what does not, and why
│   ├── EXCLUDED.md            every script NOT published, and the reason for each
│   ├── LICENSE-CODE           MIT
│   ├── requirements.txt       analysis layer — all that `reproduce.py` needs
│   ├── requirements-inference.txt   inference layer — documented, not sufficient to re-run
│   ├── reproduce.py           ONE COMMAND: regenerates the aggregates and cross-checks them
│   ├── analysis/              13 files, runnable against the published data alone
│   └── inference/             9 scripts, published for inspection (need the corpus and/or Ollama)
├── datasets/
│   ├── dataset_gold_standard.json      53 answerable questions (a/b/c)
│   ├── dataset_trap_validado.json      24 false-premise questions (a/b/c/d)
│   ├── dataset_ood_validado.json       18 unanswerable questions (a/b/c/d; gold is always d)
│   └── DATA_DICTIONARY.md
├── results_ablation_p1/                Study P1 — 8 reports × 53 records = 424 inferences
│   ├── report_{llama8b,qlora,qwen7b,med42}_GPU_Local_Win11_9doc_sysrole_{con,sin}_RERUN.json
│   └── DATA_DICTIONARY.md
├── results_hallucination_p2_sanitized/ Study P2 — 24 reports = 760 inferences
│   ├── report_{tag}_P2abstain_{original,trap,ood}_{con,sin}_{timestamp}_SANITIZED.json
│   └── DATA_DICTIONARY.md
├── results_retrieval_exploratory_sanitized/  Exploratory retrieval campaign — 4 reports × 53
│   │                                         = 212 inferences. Source of recall@k = 88.7 %
│   │                                         (47/53) and of the fragments P1 replayed.
│   ├── report_{model}_GPU_Local_Win11_9doc_{tag}_bge-m3_{timestamp}_SANITIZED.json
│   └── DATA_DICTIONARY.md
├── results_scale_campaign_sanitized/  Scale campaign — 7 reports × 53 = 371 inferences.
│   │                                  Source of Table 3. recall@k = 92.45 % (49/53),
│   │                                  identical in all seven. Cluster RTX 4090.
│   ├── report_{model}_GPU_{node}_{...}_SANITIZED.json
│   └── DATA_DICTIONARY.md            includes the ollama ps residency lines: 100 % GPU
│                                     for the 7-8B models; 49/54 GB and 52/48 and 56/44
│                                     CPU/GPU splits for the 70-72B ones
├── aggregates/                            16 files
│   ├── rag_benefit_summary.json                     P1 per-model accuracy, delta, CI, McNemar
│   ├── hallucination_summary.json                   P2 per-model and pooled rates
│   ├── hallucination_summary_resuelto.json          P2 sensitivity analysis (unparsed answers resolved)
│   ├── resolucion_no_parseadas.json                 the 20 unparseable answers, resolved by rule;
│   │                                                input to the sensitivity analysis above
│   ├── taxonomia_{resumen,errores,frontera}.json    error taxonomy over the 131 P1 errors
│   ├── errores_prelabel.json                        judge 1's (qwen2.5:7b) pre-labelling of the 131
│   │                                                errors — the INPUT of analyze_taxonomia.py
│   ├── errores_prelabel_juez2.json                  judge 2's (llama3.1:8b) pre-labelling, 40-case
│   │                                                subsample — the other half of the judge-judge kappa
│   ├── detectability_{resumen,frontera_resumen,frontera,qwen,llama}.json   blind detectability panel
│   ├── chunk_provenance.json                        document + page of the 368 chunks retrieved for the
│   │                                                53 `original`-bank questions (no TRAP/OOD provenance)
│   ├── distractor_efecto.json                       effect of distractor chunks on the error rate
│   │                                                (NO producer script — see VERIFICATION.md)
│   └── DATA_DICTIONARY.md
├── annotation/                            NOT an independent human panel — see point 6 above
│   ├── detectabilidad_humano.csv          the frontier judge's 80 ratings, endorsed unchanged by the author
│   ├── detectabilidad_humano_CLAVE.json   the ground-truth key that de-blinds those 80 cases (no ratings)
│   ├── taxonomia_para_anotar.csv          annotation template: the 131 endorsed error labels
│   └── DATA_DICTIONARY.md
└── exploratory/                           SUPERSEDED earlier campaign (306 of 493 rows,
    │                                       17-question bank) — NOT the article's Table 3
    ├── datos_detallados_preguntas.csv
    ├── modelos_ranking.csv
    ├── embeddings_ranking.csv
    ├── resumen_ejecutivo.json
    └── DATA_DICTIONARY.md
```

## How to verify the data

Four artefacts let you check this release without having to trust us.

**0. Re-run the analysis — `code/reproduce.py`.** The strongest check, and the one that needs nothing but this repository and Python:

```bash
pip install -r code/requirements.txt
python code/reproduce.py          # exit 0 = everything matches
```

It regenerates every regenerable aggregate from the raw published records and compares it, field by field, with the published file. It also declares what it *cannot* regenerate, and why. Two controlled divergences are reported and explained in `VERIFICATION.md`; neither alters a figure of the article.

**1. File integrity — `MANIFEST.sha256`.** Lists the SHA-256 digest of every published file:

```bash
sha256sum -c MANIFEST.sha256          # Linux / macOS / Git Bash
```

The repository ships a `.gitattributes` containing `* -text`, which disables end-of-line normalisation. Without it Git would rewrite line endings on checkout and every digest would fail on Windows.

**2. Numerical integrity — `VERIFICATION.md`.** The report of the release audit: which of the article's figures were re-derived from the raw records, which matched, and which discrepancies were found. Discrepancies are reported, never silently corrected. The known limitations of the release — the 306/493 exploratory gap, the withheld raw files, the redactions — are restated there.

**3. Reproducible derivations — `derived_metrics.json`.** The figures that the article reports but that no pre-computed file contained, recomputed from the raw records, each stored with its exact formula, its source files and the date of computation. This matters because some quantities are defined over a **subset** of a file and would give a different answer if computed over the whole of it; the formula is published precisely so that the subset is unambiguous.

**Re-deriving a headline number yourself.** The raw records are self-contained. For example, the accuracy of any P1 arm is the mean of `es_correcta` over the 53 records of the corresponding report; and the pooled P2 hallucination rate is the mean of `alucina` over the 116 items per arm whose gold answer is `d` (the 18 OOD items plus the 11 TRAP items with gold `d`, times 4 models). The definitions of `alucina`, `abstiene` and every other field are given in the data dictionaries.

## License

This repository carries **two licences**, one for the data and one for the code:

| What | Licence | Text |
|---|---|---|
| **The data** — question banks, inference records, annotations, aggregates, documentation | **CC BY 4.0** | [`LICENSE`](LICENSE) |
| **The code** — everything under `code/` | **MIT** | [`code/LICENSE-CODE`](code/LICENSE-CODE) |

The code is MIT rather than CC BY on purpose: MIT is the customary licence for software and lets the scripts be reused, modified and embedded without the attribution machinery of a data licence. The **scope of both is set out in [`NOTICE.md`](NOTICE.md)** (bilingual EN/ES), which is the authoritative statement of what is ours and what belongs to third parties. In short: you may share and adapt the material for any purpose, including commercially, provided you give appropriate credit.

**Scope note — the licences cover our own material only.** CC BY 4.0 applies to everything in this repository that we created and that is data: the question banks, the inference records, the annotations, the aggregate analyses and the documentation. MIT applies to the code. The summary below reproduces the essentials of [`NOTICE.md`](NOTICE.md); if the two ever diverge, `NOTICE.md` governs.

It does **not** — and cannot — apply to the short verbatim quotations from the third-party teaching corpus that a few fields still carry, because those are not ours to license. They are retained under the **academic right of quotation**: they are short, they are strictly necessary for the record to be auditable (they are the evidence on which a label or a validation rests), and they are always attributed to their source document and page. They are:

- `traza_cita` in `datasets/dataset_trap_validado.json` (all 24 items) — the corpus sentence that the item's false premise contradicts, attributed via `documento_fuente` and `traza_pagina`;
- `traza_cita` in `datasets/dataset_gold_standard.json` (the 30 items that carry source metadata, of which 4 are redacted) — the sentence supporting the gold answer, likewise attributed;
- `cita_soporte` in `aggregates/taxonomia_errores.json` (131 records, of which 7 are redacted) and in `aggregates/errores_prelabel.json` (the same 131 judge citations, likewise 7 redacted) — the excerpt on which the adjudicated error category rests;
- `cola` in `aggregates/resolucion_no_parseadas.json` (20 records, of which 1 is redacted) — the tail of the unparseable answer, kept so the resolution rule can be checked;
- the short quotations that models made of the retrieved evidence inside `respuesta_ia`, which are preserved.

In all of the above, only quotations **shorter than 50 consecutive words** remain; every span of 50 words or more was redacted (see [point 4 above](#4-long-verbatim-quotations-of-the-corpus-were-redacted-in-every-free-text-field)).

Anyone reusing this dataset should treat those fields as third-party quotations governed by the copyright law of their own jurisdiction, not as CC BY-licensed material.

## How to cite

Please cite **the article** as the primary reference and **this dataset** as the data source. Machine-readable metadata for both is in [`CITATION.cff`](CITATION.cff), which GitHub renders through the *Cite this repository* button. The article is currently under review at JAIR; the citation will be updated when it is published.

## Contact

Rubén Fernández García — <ruben.fernandezg@um.es> — Universidad de Murcia.
Questions about the data, requests for clarification, and reports of errors are welcome. Please open an issue or write directly.

---
---

<a id="español"></a>

# Español

## Contenido

- [Relación con el artículo](#relación-con-el-artículo)
- [Qué contiene este repositorio](#qué-contiene-este-repositorio)
- [El código](#el-código)
- [Qué NO se incluye y por qué](#qué-no-se-incluye-y-por-qué)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Cómo verificar los datos](#cómo-verificar-los-datos)
- [Licencia](#licencia)
- [Cómo citar](#cómo-citar)
- [Contacto](#contacto)

## Relación con el artículo

El artículo evalúa un asistente con Generación Aumentada por Recuperación (RAG) construido sobre modelos de lenguaje ligeros y desplegables en local (clase 7B–8B), sobre un corpus en español de material docente de neurofisioterapia al que se añadieron, como distractores, guías de práctica clínica del ictus de acceso abierto. La recuperación es híbrida (BM25 + FAISS con *embeddings* `BAAI/bge-m3` y un re-ranker de tipo cross-encoder, `top_k = 7`); la generación es determinista (`temperature = 0`, `num_ctx = 8192`).

El trabajo se sostiene sobre dos experimentos, publicados aquí íntegramente:

| | **Estudio P1 — ablativo** | **Estudio P2 — alucinaciones** |
|---|---|---|
| Pregunta | ¿Mejora la recuperación la precisión? | ¿Impide la recuperación que el modelo responda a lo que no admite respuesta? |
| Diseño | 4 modelos × {con RAG, sin RAG} × 53 preguntas | 4 modelos × {con RAG, sin RAG} × 3 bancos (53 respondibles + 24 TRAP de premisa falsa + 18 OOD irresolubles) |
| Inferencias | **424** | **760** |
| Opciones ofrecidas | `a` / `b` / `c` — la abstención está prohibida por diseño (encuadre clínico anti-rechazo) | `a` / `b` / `c` / **`d) No puede responderse con la documentación disponible`** — la abstención es una respuesta legítima |
| Resultado principal | El RAG mejora a **4/4** modelos; agregado de **+12,7 pp** sobre 212 pares (McNemar *p* ≈ 0,001) | La alucinación agregada cae del **64,7 %** al **30,2 %**, con la cobertura prácticamente intacta (85,9 % → 84,0 %) |

Por delante de ambos, y publicada aquí también íntegramente, está la **campaña exploratoria del eje de escala**: 7 modelos de 7B a 72B parámetros × con RAG × las mismas 53 preguntas = **371 inferencias**, los siete con la misma recuperación (`recall@k = 92,45 %`) y en la misma RTX 4090 del clúster. Es el origen de la **Tabla 3** y del contraste precisión-latencia que el artículo traza entre escala e interactividad (88,68 % a 149,6 s frente a 75,47 % a 3,5 s). Está en `results_scale_campaign_sanitized/`.

Se publican además dos análisis complementarios: una **taxonomía adjudicada de las 131 respuestas erróneas de P1** (cinco categorías mutuamente excluyentes, T1–T5) y un **panel ciego de detectabilidad** en el que **tres jueces LLM** (dos modelos locales débiles y uno de frontera) valoran hasta qué punto cada error es detectable sin acceso a la solución. El panel **no incluye ningún evaluador humano independiente**: véase el [punto 6](#6-no-hay-validación-humana-independiente).

> ### Advertencia: las precisiones de P1 y P2 NO son comparables entre sí
>
> Los dos protocolos difieren en tres aspectos que mueven la cifra de precisión:
>
> 1. P2 añade una cuarta opción, con lo que el azar base pasa de 1/3 a 1/4.
> 2. En P1 abstenerse es imposible; en P2 abstenerse es la respuesta *correcta* en todos los ítems OOD y en 11 de los 24 TRAP.
> 3. El rol de sistema difiere justamente en la cláusula anti-rechazo, que es parte de lo que se está estudiando.
>
> Toda comparación entre protocolos debe hacerse sobre **tasas de alucinación y de abstención**, nunca sobre precisión bruta. Cada `DATA_DICTIONARY.md` repite esta advertencia.

## Qué contiene este repositorio

| Carpeta | Contenido |
|---|---|
| `datasets/` | Los tres bancos de preguntas: el Gold Standard de 53 ítems, el banco TRAP de 24 (premisa falsa en el enunciado) y el banco OOD de 18 (irresolubles con el corpus). |
| `results_ablation_p1/` | Los 8 reports crudos del estudio P1 (4 modelos × 2 brazos), 53 registros cada uno = **424 inferencias**, con el razonamiento libre completo de cada modelo. Estos reports **no contienen fragmentos del corpus**. |
| `results_hallucination_p2_sanitized/` | Los 24 reports crudos del estudio P2 (4 modelos × 2 brazos × 3 bancos) = **760 inferencias**. El contexto recuperado (`fragmentos`) se ha **sustituido por hashes SHA-256** (véase más abajo). |
| `results_retrieval_exploratory_sanitized/` | Los 4 reports crudos de la campaña exploratoria de recuperación sobre el índice definitivo de 9 documentos (4 modelos × con RAG × 53 preguntas) = **212 inferencias**. Son el **origen del `recall@k = 88,7 %` del artículo** (47/53 en cada uno de los cuatro) y contienen el **contexto recuperado que el estudio P1 reutilizó**, con lo que cierran la cadena de procedencia de `results_ablation_p1/`. Aquí `fragmentos` también va hasheado. **Sus cifras de precisión no son las de P1**: véase el diccionario de la carpeta. |
| `results_scale_campaign_sanitized/` | Los 7 reports crudos de la **campaña exploratoria del eje de escala** (7 modelos de 7B a 72B × con RAG × 53 preguntas) = **371 inferencias**, ejecutadas en la RTX 4090 del clúster el 25 de julio de 2026. Son el **origen de la Tabla 3 del artículo**. La recuperación es idéntica en los siete (`recall@k = 92,45 %`, 49/53 en cada fichero), de modo que cualquier diferencia de precisión pertenece solo al generador. Aquí `fragmentos` también va hasheado. **Sus cifras de precisión no son las de P1**: véase el diccionario de la carpeta. |
| `aggregates/` | 16 ficheros de resumen precalculado y de análisis por ítem: beneficio del RAG, alucinación, taxonomía de errores (incluido el pre-etiquetado de los dos jueces LLM), panel de detectabilidad, procedencia del *retrieval*, resolución de las respuestas no parseables y efecto de los distractores. |
| `annotation/` | El material de revisión y las claves del panel de detectabilidad y de la taxonomía de errores. **Pese a los nombres de los ficheros, no contiene valoraciones humanas independientes** — véase el [punto 6](#6-no-hay-validación-humana-independiente). |
| `exploratory/` | Crudos parciales y rankings de una campaña preliminar **anterior y superada**: 493 evaluaciones sobre un banco de 17 preguntas en el clúster de CPU. **Deprecada, y no es la campaña que reporta el artículo** — la campaña de escala del artículo es `results_scale_campaign_sanitized/`. Véanse las salvedades más abajo y en `exploratory/DATA_DICTIONARY.md`. |
| `code/` | El código fuente del estudio: una **capa de análisis** (13 ficheros) ejecutable solo con los datos publicados, una **capa de inferencia** (9 scripts) publicada para inspección, y `reproduce.py`, que verifica el estudio entero con un solo comando. **Licencia MIT**, distinta de la de los datos. Véase [El código](#el-código). |

Los nombres de campo de los ficheros están en **español** (`pregunta`, `respuesta_ia`, `es_correcta`, `abstiene`, `alucina`…). Todos ellos se documentan **en inglés** en el `DATA_DICTIONARY.md` de su carpeta.

## El código

El código se publica en [`code/`](code/), bajo **licencia MIT** ([`code/LICENSE-CODE`](code/LICENSE-CODE)), deliberadamente **distinta de la CC BY 4.0 de los datos**, para que los scripts puedan reutilizarse sin arrastrar las condiciones de atribución propias de un conjunto de datos. `code/README.md` lo documenta por extenso y `code/EXCLUDED.md` enumera todos los scripts del proyecto de trabajo que *no* se publican, con su motivo.

**Verificar el estudio entero con un solo comando:**

```bash
pip install -r code/requirements.txt
python code/reproduce.py          # exit 0 = todas las cifras regenerables cuadran con las publicadas
```

`reproduce.py` no necesita **corpus, ni GPU, ni servidor de modelos, ni red**. Regenera cada agregado regenerable a partir de los registros crudos publicados, lo coteja campo a campo con el fichero publicado, imprime una tabla `ARTEFACTO | REGENERADO | PUBLICADO | ¿COINCIDE?` y termina con código distinto de cero si algo no cuadra. Al final enumera, de forma explícita, todo lo que *no* es reproducible y por qué. Actualmente declara **dos divergencias controladas**, documentadas ambas en `VERIFICATION.md`; ninguna cambia una cifra del artículo.

**Dos capas, y una raya honesta entre ellas:**

- **`code/analysis/` — se ejecuta solo con los datos publicados.** Toda la capa estadística: la auditoría del ablativo, la agregación de alucinaciones, la taxonomía de errores, el panel de detectabilidad, las tablas LaTeX y las figuras. Esta capa es reproducible por cualquiera.
- **`code/inference/` — se publica para *leerlo*, no para ejecutarlo.** El motor de recuperación, los dos protocolos experimentales, los jueces LLM y los constructores de los bancos de preguntas. Ejecutarlos exige el **corpus docente** (nueve PDF con derechos de autor, no distribuibles) y/o un servidor **Ollama** local. Cada fichero lo advierte en su cabecera.
- **El pipeline de ajuste fino QLoRA no se publica en absoluto.** Sus datos de entrenamiento derivan del corpus con derechos de autor, de modo que ni los pesos del adaptador ni los scripts de entrenamiento pueden liberarse. **La consecuencia, dicha sin rodeos: el brazo QLoRA de este estudio no es reproducible por terceros.** Los otros tres modelos —`llama3.1:8b`, `qwen2.5:7b` y `thewindmom/llama3-med42-8b`— son públicos en Ollama y **sí** lo son. Todo lo que viene después de la inferencia sigue siendo verificable para los cuatro modelos, porque las salidas crudas pregunta a pregunta de los cuatro están publicadas.

Ningún script de `code/` contiene una cita redactada del corpus: la redacción por derechos de autor que se describe más abajo afecta solo a los ficheros de datos.

## Qué NO se incluye y por qué

Preferimos ser explícitos sobre lo que un lector buscará y no encontrará.

### 1. El corpus docente no se publica (derechos de terceros)

Los documentos temáticos que constituyen la base de conocimiento son material docente redactado por terceros. **No tenemos derechos de redistribución sobre ellos**, de modo que ni los PDF, ni su texto extraído, ni el índice troceado se incluyen aquí. Los tres documentos distractores son guías de práctica clínica del ictus de acceso abierto y pueden obtenerse de sus editores.

Consecuencia: la cadena de recuperación **no puede reejecutarse de principio a fin** solo con este repositorio. Lo que sí puede hacerse es volver a derivar cualquier cifra publicada a partir de los registros crudos de inferencia, que están completos.

### 2. El pipeline de ajuste fino QLoRA no se publica: el brazo QLoRA no es reproducible

**El código fuente sí se publica** (en `code/` — véase [El código](#el-código)); esta sección deja constancia de la única parte que no, y de su consecuencia.

El adaptador `neurofisio-qlora` se afinó sobre datos **derivados del corpus docente con derechos de autor**. Publicar los scripts de entrenamiento implicaría publicar los pasajes del corpus que llevan incrustados, y publicar los pesos del adaptador implicaría distribuir un modelo entrenado sobre material que no podemos redistribuir. Ni los pesos ni los scripts de generación del dataset y de afinado se liberan, por tanto; `code/EXCLUDED.md` nombra cada fichero excluido.

**La consecuencia honesta: el brazo QLoRA de este estudio no puede reproducirlo un tercero.** Los otros tres modelos —`llama3.1:8b`, `qwen2.5:7b` y `thewindmom/llama3-med42-8b`— son públicos en Ollama, y sus brazos *sí* son reproducibles de principio a fin por quien disponga además de una copia lícita del corpus. Todo lo que viene **después de la inferencia** —cada estadístico, cada tabla y cada figura— sigue siendo verificable para los cuatro modelos, porque las salidas crudas pregunta a pregunta de los cuatro están publicadas y `code/analysis/` recomputa las cifras a partir de ellas.

Los parámetros operativos se repiten además en el bloque `header` de cada report crudo aquí publicado (`retrieved_top_k`, `context_max_tokens`, `num_ctx`, `temperature`…). Conviene precisar que `embedding_model` (`BAAI/bge-m3`) consta en la cabecera de **los 24 reports del estudio P2 únicamente**; los 8 reports del estudio P1 no llevan ese campo, y para ellos el modelo de *embeddings* está documentado en el artículo, en este README y en `code/inference/evaluate_rag.py`, no en el propio fichero.

### 3. En los reports de P2, los fragmentos recuperados se sustituyeron por hashes SHA-256

Los 24 reports crudos de P2 llevaban originalmente, para cada pregunta del brazo con RAG, los fragmentos literales recuperados del corpus. Publicarlos equivaldría a redistribuir el corpus protegido a trozos. En los ficheros `_SANITIZED`, por tanto, cada cadena de texto se ha sustituido por un objeto de esta forma:

```json
{"sha256": "12036c6aeff1e6872ec1896465278d484102baa0331d5c56d74ba13b89ccc9c8",
 "n_chars": 606,
 "documento": "03_sistemas_motores_descendentes.pdf",
 "pagina": 14}
```

Esto preserva la función científica del campo y elimina únicamente el texto protegido. Quien disponga de una copia lícita del corpus puede reconstruir los *chunks* con los parámetros publicados, hashearlos y **verificar exactamente qué fragmento se recuperó para cada pregunta**, sin que aquí se redistribuya una sola línea de material protegido. Documento y página solo son resolubles para el banco `original` (vía `aggregates/chunk_provenance.json`); para los bancos TRAP y OOD no existe mapa de procedencia, y esos fragmentos llevan `"documento": null, "pagina": null, "provenance": "no_disponible"`. El esquema completo se documenta en `results_hallucination_p2_sanitized/DATA_DICTIONARY.md`.

El mismo tratamiento se aplica a los cuatro reports de `results_retrieval_exploratory_sanitized/` (1 472 fragmentos, **todos** con documento y página, por pertenecer al banco `original`) y a los siete de `results_scale_campaign_sanitized/` (2 947 fragmentos, igualmente **todos** con documento y página). Los reports de P1 nunca contuvieron los fragmentos recuperados, de modo que no necesitaron este tratamiento, y el contexto que consumieron no se ha perdido: **reutilizaron** los fragmentos de esos cuatro reports exploratorios, cuyos 1 472 hashes coinciden, posición a posición, con los publicados para P2.

### 4. Las citas literales largas del corpus se redactaron, en todos los campos de texto libre

A los modelos se les pidió fundamentar su respuesta en la evidencia recuperada y con frecuencia la citan; los campos de evidencia construidos a mano (`traza_cita`, `cita_soporte`) son, por construcción, copia del corpus. Se auditaron **todos los campos de texto libre de todos los ficheros publicados** contra los **nueve documentos fuente completos** (no contra los *chunks* recuperados, que serían ciegos a las citas que cruzan una frontera de *chunk*). Los pasajes que reproducían **50 o más palabras consecutivas** del corpus se sustituyeron *in situ* por el marcador literal:

```
[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]
```

donde *N* es el número de palabras retiradas. Solo se sustituye el tramo solapado; el texto circundante (el razonamiento propio del modelo, o el resto del campo) queda intacto.

Afecta a **64 tramos repartidos en 16 ficheros, 3 676 palabras retiradas en total**, el tramo más largo de 101 palabras y el más corto de 50. Por carpeta:

| Carpeta | Tramos | Ficheros | Palabras retiradas |
|---|---|---|---|
| `results_ablation_p1/` | 9 | 2 | 550 |
| `results_hallucination_p2_sanitized/` | 9 | 4 | 490 |
| `results_retrieval_exploratory_sanitized/` | 6 | 3 | 350 |
| `results_scale_campaign_sanitized/` | 21 | 3 | 1 208 |
| `datasets/` | 4 | 1 | 231 |
| `aggregates/` | 15 | 3 | 847 |
| `code/` | **0** | 0 | 0 |
| **Total** | **64** | **16** | **3 676** |

Por campo: **45** en `respuesta_ia` (2 598 palabras — las cuatro carpetas de reports, todos en el brazo con RAG), **14** en `cita_soporte` (796 palabras — 7 en `aggregates/taxonomia_errores.json` y 7 en `aggregates/errores_prelabel.json`, que arrastra las mismas citas del juez), **4** en `traza_cita` (231 palabras — `datasets/dataset_gold_standard.json`) y **1** en `cola` (51 palabras — `aggregates/resolucion_no_parseadas.json`). **Ningún script de `code/` contiene tramos redactados**: ningún script publicado reproduce 50 o más palabras consecutivas del corpus.

En los dos campos de evidencia se conserva la procedencia para que el campo siga cumpliendo su función: `dataset_gold_standard.json` mantiene sus campos hermanos `documento_fuente` y `traza_pagina`, y en `taxonomia_errores.json` el marcador va seguido de una referencia explícita `Ref.: <documento>, p. <página>`. `dataset_trap_validado.json` se auditó y no necesitó redacción (solapamiento máximo: 49 palabras).

**Las citas más cortas se conservan** al amparo del derecho de cita académico: quedan tramos de 12 a 49 palabras consecutivas en los campos de texto libre, dispersos y no contiguos, que no permiten reconstruir ningún documento fuente. Un censo de esas citas cortas solo puede producirse contra el corpus fuente, que aquí no se publica, de modo que esta publicación no afirma ninguna cifra sobre ellas. La redacción es cosmética y estrictamente posterior a los experimentos: `es_correcta`, `opcion_detectada`, `abstiene`, `alucina`, `retrieval_recall_hit` y todos los demás campos derivados se calcularon sobre las respuestas originales sin redactar y siguen siendo válidos; no se eliminó ningún registro ni varió ningún conteo. La salvedad (d) de `VERIFICATION.md` documenta el método de auditoría y el desglose completo por fichero.

**Los datos crudos completos y sin redactar obran en poder de los autores y están disponibles bajo petición razonada con fines de verificación** —por ejemplo, para una persona revisora o editora que necesite auditar las salidas íntegras de los modelos—, sujeto a las restricciones de derechos del corpus docente subyacente.

### 5. Una campaña preliminar anterior quedó superada, y solo se conserva parcialmente

**La campaña de escala que reporta el artículo se publica íntegra.** Es `results_scale_campaign_sanitized/`: **371 evaluaciones**, 7 modelos × 53 preguntas, los siete con la misma recuperación y en la misma GPU del clúster. Toda celda de la Tabla 3 puede volver a derivarse desde esos ficheros, y el `recall@k = 92,45 %` es idéntico en los siete. De esa campaña no falta nada.

Lo que solo se conserva parcialmente es una **campaña anterior, que la publicada dejó superada**, guardada en `exploratory/` como registro histórico. Constó de **493 evaluaciones automatizadas** sobre 7 modelos y 4 modelos de *embeddings* en hardware dual, sobre un banco preliminar de **17 preguntas** que no es el gold standard de 53 ítems. Solo sobreviven **306 de esas 493** filas por ítem, en `exploratory/datos_detallados_preguntas.csv`; el resto se midió bajo Fedora y no se conservó en la migración del proyecto a Windows. Todas las filas supervivientes pertenecen a la mitad ejecutada en el clúster HPC (`device = Cluster_Amdahl`, `mode = CPU`).

Los tres ficheros agregados de `exploratory/` (`modelos_ranking.csv`, `embeddings_ranking.csv`, `resumen_ejecutivo.json`) se calcularon en su día sobre las **493 evaluaciones completas** y se conservan tal y como se produjeron; por tanto **no pueden recomputarse a partir de las 306 filas supervivientes**.

> **No contrastes las cifras de `exploratory/` con el artículo.** Pertenecen a la campaña superada: otro banco de preguntas, otra configuración de recuperación y una extracción de respuesta más simple. El `58,82 %` de mejor modelo que recoge `exploratory/resumen_ejecutivo.json` **no** es una cifra del artículo, y ninguna afirmación del texto descansa sobre ella. La campaña inicial del artículo es la de 371 evaluaciones, y los dos experimentos definitivos (P1, 424 inferencias; P2, 760 inferencias) se conservan íntegros.

### 6. No hay validación humana independiente

La carpeta se llama `annotation/` y uno de sus ficheros se llama `detectabilidad_humano.csv`. **Ninguno de los dos nombres debe leerse como una afirmación de anotación humana independiente, porque no la hay.** Esta es la salvedad más importante de todo el repositorio, y la decimos sin rodeos.

Lo que ocurrió en realidad: el **juez LLM de frontera** produjo las etiquetas y el **autor revisó su salida y la respaldó íntegramente**.

- **Taxonomía de errores.** El campo `categoria_final` de `aggregates/taxonomia_errores.json` coincide con la etiqueta del juez de frontera de `aggregates/taxonomia_frontera.json` en **131 de 131 casos**. El revisor aceptó todas las categorías y no modificó ninguna: el acuerdo bruto es **1,00** por construcción.
- **Panel de detectabilidad.** Los 240 valores de `annotation/detectabilidad_humano.csv` (80 casos × 3 campos) son **idénticos, valor a valor, a las valoraciones del juez de frontera** de `aggregates/detectability_frontera.json`, incluidas las probabilidades continuas a tres decimales. El revisor aceptó igualmente los 42 ítems de los bancos sin retirar ninguno.

Es una **confirmación experta de un resultado automático, no una reanotación independiente.** De ahí se sigue que:

- **No existe ningún evaluador humano independiente** en este trabajo, y el panel ciego de detectabilidad lo componen **tres modelos de lenguaje** (dos locales débiles y uno de frontera) y nadie más.
- **No cabe calcular ningún acuerdo humano-máquina, y no se publica ninguno.** Cualquier kappa que se obtuviera comparando `annotation/` con `aggregates/` valdría 1,00 por construcción y sería un artefacto, no un resultado. No use estos ficheros como segundo anotador.
- El **único** acuerdo entre evaluadores que existe en este repositorio es el que hay **entre los dos jueces automáticos**: kappa de Cohen = **0,223** (juez local frente a juez de frontera, n = 131, acuerdo bruto 0,405) y **0,468** (juez 1 frente a juez 2, n = 40), ambos en `aggregates/taxonomia_resumen.json` → `acuerdo`. Esa primera cifra, tan baja, es justamente la razón de que las etiquetas que se arrastran al análisis sean las del juez de frontera y no las del local.

El artículo dice exactamente lo mismo. Preferimos publicar honestamente una afirmación débil que sostener una fuerte que no podemos respaldar.

## Estructura del repositorio

```
clinical-rag-neurophysio-data/
├── README.md                  este fichero
├── LICENSE                    texto legal completo de la CC BY 4.0 (los DATOS)
├── NOTICE.md                  alcance de las licencias: qué es nuestro y qué de terceros (EN/ES)
├── CITATION.cff               metadatos de cita legibles por máquina
├── datapackage.json           descriptor Frictionless Data
├── MANIFEST.sha256            digest SHA-256 de cada fichero publicado
├── VERIFICATION.md            auditoría de publicación: qué se rederivó, qué cuadró y qué no
├── derived_metrics.json       cifras recomputadas desde los crudos para esta publicación
├── code/                      el código fuente del estudio — licencia MIT (NO CC BY 4.0)
│   ├── README.md              qué se ejecuta sin el corpus, qué no, y por qué
│   ├── EXCLUDED.md            todos los scripts que NO se publican, y el motivo de cada uno
│   ├── LICENSE-CODE           MIT
│   ├── requirements.txt       capa de análisis — todo lo que necesita `reproduce.py`
│   ├── requirements-inference.txt   capa de inferencia — documentada, no basta para reejecutar
│   ├── reproduce.py           UN SOLO COMANDO: regenera los agregados y los coteja
│   ├── analysis/              13 ficheros, ejecutables solo con los datos publicados
│   └── inference/             9 scripts, publicados para inspección (exigen corpus y/o Ollama)
├── datasets/
│   ├── dataset_gold_standard.json      53 preguntas respondibles (a/b/c)
│   ├── dataset_trap_validado.json      24 preguntas de premisa falsa (a/b/c/d)
│   ├── dataset_ood_validado.json       18 preguntas irresolubles (a/b/c/d; la correcta es siempre d)
│   └── DATA_DICTIONARY.md
├── results_ablation_p1/                Estudio P1 — 8 reports × 53 registros = 424 inferencias
│   ├── report_{llama8b,qlora,qwen7b,med42}_GPU_Local_Win11_9doc_sysrole_{con,sin}_RERUN.json
│   └── DATA_DICTIONARY.md
├── results_hallucination_p2_sanitized/ Estudio P2 — 24 reports = 760 inferencias
│   ├── report_{tag}_P2abstain_{original,trap,ood}_{con,sin}_{timestamp}_SANITIZED.json
│   └── DATA_DICTIONARY.md
├── results_retrieval_exploratory_sanitized/  Campaña exploratoria de recuperación — 4 reports × 53
│   │                                         = 212 inferencias. Origen del recall@k = 88,7 %
│   │                                         (47/53) y de los fragmentos que reutilizó P1.
│   ├── report_{modelo}_GPU_Local_Win11_9doc_{tag}_bge-m3_{timestamp}_SANITIZED.json
│   └── DATA_DICTIONARY.md
├── results_scale_campaign_sanitized/  Campaña de escala — 7 reports × 53 = 371 inferencias.
│   │                                  Origen de la Tabla 3. recall@k = 92,45 % (49/53),
│   │                                  idéntico en los siete. RTX 4090 del clúster.
│   ├── report_{model}_GPU_{node}_{...}_SANITIZED.json
│   └── DATA_DICTIONARY.md            incluye las líneas de residencia de ollama ps: 100 %
│                                     GPU en los 7-8B; 49/54 GB y repartos 52/48 y 56/44
│                                     CPU/GPU en los 70-72B
├── aggregates/                            16 ficheros
│   ├── rag_benefit_summary.json                     precisión, delta, IC y McNemar por modelo (P1)
│   ├── hallucination_summary.json                   tasas por modelo y agregadas (P2)
│   ├── hallucination_summary_resuelto.json          análisis de sensibilidad de P2 (respuestas no interpretables resueltas)
│   ├── resolucion_no_parseadas.json                 las 20 respuestas no parseables, resueltas por regla;
│   │                                                entrada del análisis de sensibilidad anterior
│   ├── taxonomia_{resumen,errores,frontera}.json    taxonomía sobre los 131 errores de P1
│   ├── errores_prelabel.json                        pre-etiquetado del juez 1 (qwen2.5:7b) de los 131
│   │                                                errores — la ENTRADA de analyze_taxonomia.py
│   ├── errores_prelabel_juez2.json                  pre-etiquetado del juez 2 (llama3.1:8b), submuestra de
│   │                                                40 casos — la otra mitad del kappa entre jueces
│   ├── detectability_{resumen,frontera_resumen,frontera,qwen,llama}.json   panel ciego de detectabilidad
│   ├── chunk_provenance.json                        documento y página de los 368 fragmentos recuperados para
│   │                                                las 53 preguntas del banco `original` (no hay TRAP/OOD)
│   ├── distractor_efecto.json                       efecto de los chunks distractores sobre la tasa de error
│   │                                                (SIN script productor — véase VERIFICATION.md)
│   └── DATA_DICTIONARY.md
├── annotation/                            NO es un panel humano independiente — véase el punto 6
│   ├── detectabilidad_humano.csv          las 80 valoraciones del juez de frontera, respaldadas sin cambios
│   ├── detectabilidad_humano_CLAVE.json   la clave de verdad-terreno que desciega esos 80 casos (sin valoraciones)
│   ├── taxonomia_para_anotar.csv          plantilla de anotación: las 131 etiquetas de error respaldadas
│   └── DATA_DICTIONARY.md
└── exploratory/                           campaña anterior SUPERADA (306 de 493 filas,
    │                                       banco de 17 preguntas) — NO es la Tabla 3
    ├── datos_detallados_preguntas.csv
    ├── modelos_ranking.csv
    ├── embeddings_ranking.csv
    ├── resumen_ejecutivo.json
    └── DATA_DICTIONARY.md
```

## Cómo verificar los datos

Cuatro artefactos permiten comprobar esta publicación sin tener que fiarse de nosotros.

**0. Reejecutar el análisis — `code/reproduce.py`.** La comprobación más fuerte, y la que no necesita nada más que este repositorio y Python:

```bash
pip install -r code/requirements.txt
python code/reproduce.py          # exit 0 = todo cuadra
```

Regenera cada agregado regenerable desde los registros crudos publicados y lo coteja, campo a campo, con el fichero publicado. Declara además lo que *no* puede regenerar, y por qué. Reporta dos divergencias controladas, explicadas en `VERIFICATION.md`; ninguna altera una cifra del artículo.

**1. Integridad de los ficheros — `MANIFEST.sha256`.** Contiene el digest SHA-256 de cada fichero publicado:

```bash
sha256sum -c MANIFEST.sha256          # Linux / macOS / Git Bash
```

El repositorio incluye un `.gitattributes` con `* -text`, que desactiva la normalización de fin de línea. Sin él, Git reescribiría los saltos de línea al hacer *checkout* y todos los digests fallarían en Windows.

**2. Integridad numérica — `VERIFICATION.md`.** El informe de la auditoría de publicación: qué cifras del artículo se volvieron a derivar desde los crudos, cuáles cuadraron y qué discrepancias se encontraron. Las discrepancias se reportan, nunca se corrigen en silencio. Las limitaciones conocidas de la publicación —el hueco 306/493 de la exploratoria, los crudos retenidos, las redacciones— se reiteran allí.

**3. Derivaciones reproducibles — `derived_metrics.json`.** Las cifras que el artículo reporta pero que ningún fichero precalculado contenía, recomputadas desde los crudos, cada una con su fórmula exacta, sus ficheros fuente y la fecha de cálculo. Esto importa porque algunas magnitudes se definen sobre un **subconjunto** de un fichero y darían otro valor si se calcularan sobre el fichero entero; la fórmula se publica precisamente para que el subconjunto no admita ambigüedad.

**Volver a derivar una cifra principal por su cuenta.** Los registros crudos son autocontenidos. Por ejemplo, la precisión de cualquier brazo de P1 es la media de `es_correcta` sobre los 53 registros del report correspondiente; y la tasa agregada de alucinación de P2 es la media de `alucina` sobre los 116 ítems por brazo cuya respuesta correcta es `d` (los 18 OOD más los 11 TRAP con solución `d`, por 4 modelos). Las definiciones de `alucina`, `abstiene` y del resto de campos están en los diccionarios de datos.

## Licencia

Este repositorio lleva **dos licencias**, una para los datos y otra para el código:

| Qué | Licencia | Texto |
|---|---|---|
| **Los datos** — bancos de preguntas, registros de inferencia, anotaciones, agregados, documentación | **CC BY 4.0** | [`LICENSE`](LICENSE) |
| **El código** — todo lo que hay bajo `code/` | **MIT** | [`code/LICENSE-CODE`](code/LICENSE-CODE) |

El código va bajo MIT y no bajo CC BY a propósito: MIT es la licencia habitual del software y permite reutilizar, modificar e incrustar los scripts sin arrastrar la maquinaria de atribución propia de una licencia de datos. El **alcance de ambas se detalla en [`NOTICE.md`](NOTICE.md)** (bilingüe EN/ES), que es la declaración autorizada de qué es nuestro y qué pertenece a terceros. En resumen: puede compartir y adaptar el material con cualquier finalidad, incluso comercial, siempre que dé el crédito adecuado.

**Nota de alcance — las licencias cubren solo el material de creación propia.** La CC BY 4.0 se aplica a todo lo que hemos creado nosotros y es dato: los bancos de preguntas, los registros de inferencia, las anotaciones, los análisis agregados y la documentación. La MIT se aplica al código. El resumen que sigue reproduce lo esencial de [`NOTICE.md`](NOTICE.md); si ambos textos divergieran, prevalece `NOTICE.md`.

**No** se aplica —ni puede aplicarse— a las citas literales cortas del corpus docente de terceros que aún conservan unos pocos campos, porque no son nuestras para licenciarlas. Se retienen al amparo del **derecho de cita académico**: son breves, son estrictamente necesarias para que el registro sea auditable (son la evidencia en la que se apoya una etiqueta o una validación) y van siempre atribuidas a su documento y página de origen. Son:

- `traza_cita` en `datasets/dataset_trap_validado.json` (los 24 ítems) — la frase del corpus que la premisa falsa del ítem contradice, atribuida mediante `documento_fuente` y `traza_pagina`;
- `traza_cita` en `datasets/dataset_gold_standard.json` (los 30 ítems que llevan metadatos de fuente, de los cuales 4 están redactados) — la frase que respalda la respuesta correcta, igualmente atribuida;
- `cita_soporte` en `aggregates/taxonomia_errores.json` (131 registros, de los cuales 7 están redactados) y en `aggregates/errores_prelabel.json` (las mismas 131 citas del juez, igualmente 7 redactadas) — el fragmento en el que se apoya la categoría de error adjudicada;
- `cola` en `aggregates/resolucion_no_parseadas.json` (20 registros, de los cuales 1 está redactado) — la cola de la respuesta no parseable, conservada para poder comprobar la regla de resolución;
- las citas cortas que los modelos hicieron de la evidencia recuperada dentro de `respuesta_ia`, que se conservan.

En todos los casos anteriores solo permanecen las citas de **menos de 50 palabras consecutivas**; todo tramo de 50 palabras o más se redactó (véase el [punto 4](#4-las-citas-literales-largas-del-corpus-se-redactaron-en-todos-los-campos-de-texto-libre)).

Quien reutilice este conjunto de datos debe tratar esos campos como citas de terceros sujetas a la legislación de propiedad intelectual de su jurisdicción, y no como material licenciado bajo CC BY.

## Cómo citar

Cite **el artículo** como referencia principal y **este conjunto de datos** como fuente de los datos. Los metadatos legibles por máquina de ambos están en [`CITATION.cff`](CITATION.cff), que GitHub convierte en una cita lista para usar mediante el botón *Cite this repository*. El artículo está actualmente en revisión en JAIR; la cita se actualizará cuando se publique.

## Contacto

Rubén Fernández García — <ruben.fernandezg@um.es> — Universidad de Murcia.
Se agradecen preguntas sobre los datos, peticiones de aclaración y avisos de errores. Puede abrir una *issue* o escribir directamente.
