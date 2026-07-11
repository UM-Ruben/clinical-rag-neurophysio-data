# Data dictionary — `aggregates/`

The 13 pre-computed analysis files. Every figure reported in the article is either in one of these files or, when no pre-computed file existed, recomputed from the raw records in the repository's `derived_metrics.json`.

| File | Content |
|---|---|
| `rag_benefit_summary.json` | Study P1: per-model accuracy, delta, paired CI, McNemar |
| `hallucination_summary.json` | Study P2: per-model and pooled hallucination, coverage, accuracy |
| `hallucination_summary_resuelto.json` | Study P2: same, as a sensitivity analysis with unparseable answers resolved |
| `taxonomia_resumen.json` | Error taxonomy: composition per arm and model, inter-rater agreement |
| `taxonomia_errores.json` | Error taxonomy: the 131 adjudicated errors, one record each |
| `taxonomia_frontera.json` | Error taxonomy: the frontier judge's verified label for the same 131 errors (equal to `categoria_final` on 131/131) |
| `detectability_resumen.json` | Detectability panel: AUROC, sensitivity and regression, for the 3 LLM judges |
| `detectability_frontera_resumen.json` | Detectability panel: the same summary, frontier judge only |
| `detectability_qwen.json` | Detectability panel: 424 per-answer judgements (qwen2.5:7b judge) |
| `detectability_llama.json` | Detectability panel: 190 per-answer judgements (llama3.1:8b judge) |
| `detectability_frontera.json` | Detectability panel: 80 per-answer judgements (frontier judge) |
| `chunk_provenance.json` | Retrieval provenance: source document and page of the 368 chunks retrieved for the 53 `original`-bank questions. **Covers the `original` bank only** — there is no provenance for TRAP or OOD. |
| `distractor_efecto.json` | Effect of distractor chunks on the error rate |

> ### Warning: P1 and P2 metrics are NOT comparable
>
> `rag_benefit_summary.json` (Protocol P1) and `hallucination_summary.json` (Protocol P2) both contain a field called *accuracy*, and **they do not mean the same thing**. P1 offers three options and forbids abstention; P2 offers four and treats abstention as a legitimate — often correct — answer. The chance baseline differs (1/3 vs 1/4) and so does the success criterion. Compare the protocols on **hallucination and abstention rates**, never on accuracy.

## Conventions used throughout

Most quantities are reported as a **proportion object** with this shape:

```json
{"k": 35, "n": 116, "pct": 30.17, "ci95_wilson": [22.57, 39.05]}
```

| Key | Meaning |
|---|---|
| `k` | numerator: number of events |
| `n` | denominator: sample size |
| `pct` | `100 * k / n`, rounded to 2 decimals |
| `ci95_wilson` | 95 % confidence interval for the proportion, **Wilson score interval**, as `[lower, upper]` in percentage points. Wilson is used rather than the normal approximation because several cells are small or near 0/1. |

Model labels are stable across files: `Llama-3.1-8B`, `QLoRA neurofisio`, `Qwen-2.5-7B`, `Med42-8B`. Short tags used in the per-item files are `llama8b`, `qlora`, `qwen7b`, `med42`. The `arm` field is always `con` (with RAG) or `sin` (without RAG).

---

## `rag_benefit_summary.json` — Study P1, per model

A **list of 4 objects**, one per model. This is the canonical source for the per-model P1 figures in the article.

| Field | Type | Description |
|---|---|---|
| `model` | string | Runtime model identifier (e.g. `llama3.1:8b`). |
| `model_label` | string | Display label used in the article. |
| `n` | integer | 53 — the paired questions for this model. |
| `acc_sin_rag` | float | Accuracy (%) in the without-RAG arm. |
| `acc_con_rag` | float | Accuracy (%) in the with-RAG arm. |
| `delta_rag_pp` | float | `acc_con_rag − acc_sin_rag`, in **percentage points**. Positive for all four models: RAG improves 4/4. |
| `paired_ci95` | string | 95 % confidence interval of the paired difference, in percentage points, pre-formatted as a string (e.g. `"[+10.7, +38.4]"`). Only Llama-3.1-8B has an interval excluding zero at this sample size. |
| `mcnemar_p` | float | *p*-value of McNemar's test on the 53 paired outcomes. |
| `significativo` | boolean | Whether the paired CI excludes zero. `true` only for Llama-3.1-8B. |
| `lat_median_con` | float | Median inference latency (seconds) in the with-RAG arm. The median, not the mean, is the reported statistic. |
| `b_mejora` | integer | McNemar's *b*: questions this model got **right with RAG and wrong without** it. |
| `c_empeora` | integer | McNemar's *c*: questions it got **right without RAG and wrong with** it. `b` and `c` are the discordant pairs; the concordant ones carry no information for the test. |
| `protocolo` | string | `sysrole_clinico_anti_rechazo` — tags these figures as Protocol P1. |
| `ci95_estimador` | string | Which variance estimator produced `paired_ci95`: **sample variance (ddof = 1)**, the correct estimator for a CI on a mean of paired differences. Recorded explicitly because an earlier version of this file used the population variance (ddof = 0), which underestimates the standard error; the difference is 0.1–0.2 pp and changes no conclusion. |

The **pooled** result over the 212 pairs (all four models together) is not in this file; it is recomputed from the raw reports in `derived_metrics.json`.

---

## `hallucination_summary.json` — Study P2

A JSON object with four keys.

**`protocolo`** — `P2_sysrole_abstain`.

**`modelos`** — a list of 4 objects, one per model: `model`, `label`, and `arms`, which maps `con` and `sin` each to a block of metrics:

| Metric | Definition |
|---|---|
| `alucinacion` | **The headline metric.** Proportion object over the **29 items per model whose gold answer is `d`** (18 OOD + 11 `trap_d`). Numerator: items answered with a lettered option `a`/`b`/`c` — a confident substantive answer to a question the documentation cannot answer. |
| `alucinacion_ood` | The same, restricted to the 18 OOD items. |
| `alucinacion_trap_d` | The same, restricted to the 11 TRAP items whose gold answer is `d`. |
| `complacencia_trap_c` | **Sycophancy.** Over the 13 TRAP items that remain answerable (`tipo = trap_c`), the proportion on which the model chose `opcion_que_acepta_la_premisa` — the option that is only correct if one swallows the stem's false premise. |
| `cobertura` | **Coverage.** Over the 53 answerable (`original`) items, the proportion the model answered with a **usable** option: `abstiene == false` **and** `opcion_detectada ∈ {a, b, c}`. This is the quantity that must *not* collapse when hallucination falls; it barely moves. **It is not the complement of the abstention rate** — see the box below. |
| `riesgo_entre_contestadas` | **Risk among answered.** Of the questions the model chose to answer, the proportion answered wrongly. The *y*-axis of the risk-coverage curve. |
| `accuracy_original` | Accuracy over the 53 `original` items, under Protocol P2. **Not comparable with the P1 accuracy of the same bank.** |
| `accuracy_trap` | Accuracy over the 24 TRAP items. |
| `accuracy_ood` | Accuracy over the 18 OOD items — equivalently, the rate of correct abstention. |
| `matriz_2x2` | The 2×2 decision matrix, as four integer counts: `respondible_contestada` (answerable and answered — the useful cell), `respondible_abstenida` (answerable but declined — lost utility), `irresoluble_contestada` (**unanswerable but answered — the dangerous cell: these are the hallucinations**), `irresoluble_abstenida` (unanswerable and correctly declined). |
| `parse_desconocida` | Count of records in this arm whose answer could not be parsed into a letter. Disclosed so the reader can weigh how much rests on unparseable output. |

**`faltan`** — a list of runs missing from the design. It is **empty**: the 4 × 2 × 3 grid is complete.

**`pruebas_pareadas`** — paired tests, keyed by model label, plus two Holm-correction blocks:

- For each model, `alucinacion_con_vs_sin` gives `b_rag_evita` (items hallucinated **without** RAG but not **with** it — RAG prevented the hallucination), `c_rag_induce` (the converse — RAG induced one), and the exact McNemar `p`. `cobertura_con_vs_sin` gives the analogous `b_rag_contesta` / `c_rag_calla` and its `p`.
- `_holm_alucinacion` and `_holm_cobertura` map each model label to `{p, p_holm, significativo}`, where `p_holm` is the *p*-value after **Holm–Bonferroni correction** for the four simultaneous model comparisons. The correction is applied because four models are tested at once; `significativo` refers to the corrected value.

**`pool`** — the pooled result across the four models, for `con` and `sin`, with two proportion objects: `alucinacion` (over 116 items = 29 × 4) and `cobertura` (over 212 items = 53 × 4). These are the headline numbers of Study P2:

| | with RAG | without RAG |
|---|---|---|
| `alucinacion` | 35/116 = **30.17 %** | 75/116 = **64.66 %** |
| `cobertura` | 178/212 = **83.96 %** | 182/212 = **85.85 %** |

> ### How `cobertura` is computed — and how it is *not*
>
> Coverage is the fraction of the 212 records of the `original` bank in that arm (53 questions × 4 models) that were answered with a **parseable substantive option**:
>
> ```
> cobertura = |{ r ∈ original_bank(arm) : r.abstiene == false AND r.opcion_detectada ∈ {a,b,c} }| / 212
> ```
>
> Applied to the raw reports in `results_hallucination_p2_sanitized/`, this reproduces the published figures exactly: **178/212 = 83.96 %** with RAG and **182/212 = 85.85 %** without.
>
> **Coverage is not the complement of the abstention rate**, and computing it that way is wrong. A record can fail to count towards coverage in two distinct ways: the model **abstained** (`abstiene == true`, i.e. it chose option `d`), or the model answered but its output **could not be parsed into a letter** (`opcion_detectada == "desconocida"`). Only the first is an abstention. In both arms there are exactly **28 abstentions**, so the complement of the abstention rate is 184/212 = 86.79 % *in both arms alike* — which is neither published figure, and which would erase the whole with-vs-without difference. What separates the two arms is entirely the unparseable residue: **6** `desconocida` records with RAG (212 − 28 − 6 = 178) against **2** without (212 − 28 − 2 = 182). These are the same records counted by the `parse_desconocida` field above, and they are what `hallucination_summary_resuelto.json` resolves.

## `hallucination_summary_resuelto.json` — sensitivity analysis

**Identical schema** to `hallucination_summary.json`. It is the same analysis recomputed after **manually resolving the answers that the automatic parser could not read** (`opcion_detectada == "desconocida"`): where a human could tell what the model had actually chosen, that reading was used instead of discarding the record.

It exists to show that the conclusions do not depend on the parser. The pooled hallucination figures are **unchanged** (35/116 and 75/116); coverage moves only marginally (with RAG 178/212 = 83.96 % → 180/212 = 84.91 %; without RAG unchanged). Use `hallucination_summary.json` for the headline numbers and this file to check their robustness.

---

## The error taxonomy — three files

The unit of analysis is **one erroneous response** (`es_correcta == false`) of **Protocol P1**. The universe is **131 errors** = 52 with RAG + 79 without RAG. Exactly one primary category is assigned to each.

| Category | Name | Meaning |
|---|---|---|
| **T1** | Parametric fabrication | The model asserts as true a clinical fact **absent from the available evidence** and uses it to justify its choice: an invented definition, relation, author or figure. |
| **T2** | Misreading of the context | *Only possible in the with-RAG arm.* The needed fact **is** in the retrieved fragments, but the model reads it wrongly — inverts a laterality, attributes to one structure what the text says of another. The content does come from the context; the reading fails. |
| **T3** | Invalid reasoning | The facts it handles are correct, but the **inference** connecting them to the chosen option does not hold. |
| **T4** | Right premise, wrong option | The reasoning explicitly identifies the correct content, but the emitted letter does not match it. A mapping or formatting failure, not a knowledge failure. |
| **T5** | Residual refusal | The model refuses, declares no option correct, or emits no interpretable letter (`opcion_detectada == "desconocida"`) **despite the anti-refusal clause of P1**. It is a failure of the protocol, not of knowledge — and one of the motivations for Protocol P2. |

**T2 is structurally impossible without RAG.** The between-arm comparison of the category distribution is therefore not a symmetric test over a shared sample space; it is read as a *displacement* of the error, not as a test of composition.

### `taxonomia_errores.json` — the 131 adjudicated errors

A **list of 131 objects**, one per erroneous response.

| Field | Type | Description |
|---|---|---|
| `modelo` | string | Runtime identifier of the model that made the error. |
| `tag` | string | Short model tag (`llama8b`, `qlora`, `qwen7b`, `med42`). |
| `arm` | string | `con` (52 errors) or `sin` (79 errors). |
| `id` | integer | Question id, 1–53. Together with `tag` and `arm` this uniquely locates the record in `results_ablation_p1/`. |
| `respuesta_correcta` | string | The gold answer letter. |
| `opcion_detectada` | string | The letter the model actually emitted, or `desconocida`. |
| `len_justificacion` | integer | Character length of the model's free-text answer. A covariate: length is a plausible confounder of detectability. |
| `juez` | string | The LLM judge that produced the decomposition for this record. |
| `categoria` | string | The category **derived from the judge's decomposition** by a deterministic rule (see below). `T1`–`T5`. |
| `subtags` | array of strings | Zero or more of `C-DIST`, `C-DILU`. **Not reported in the article** — see the note below. |
| `estado_en_evidencia` | string | *Present in 115 of 131 records.* The judge's verdict on the status, within the retrieved evidence, of the key claim the model leant on: `presente_bien_usada`, `presente_mal_leida`, `ausente`, or `contradicha`. This is the field the category rule keys on. Absent where the record was categorised by a prior rule (T5 is assigned without consulting the judge). |
| `opcion_que_defiende_el_texto` | string | *Present in 115 of 131 records.* Which option the model's **own prose** argues for, judged while ignoring the letter it finally emitted and ignoring the gold answer. When this differs from `opcion_detectada`, the error is **T4** — an objective comparison, not a judgement call. |
| `cita_soporte` | string | **Verbatim quotation from the third-party corpus or from the model's answer**, or a redaction marker: the excerpt on which the adjudicated category rests. It is the evidence that makes the label auditable. Short quotations (< 50 consecutive words) are retained under the academic right of quotation. **7 of the 131 cases** (array indices 12, 18, 50, 83, 85, 90, 123) reproduced **≥ 50 consecutive words** of the corpus and their `cita_soporte` has therefore been replaced in full by the literal marker `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`, where *N* is the number of words removed (53 to 63). Because this file has no `documento_fuente` / `traza_pagina` fields, the marker is followed in the same field by an explicit provenance reference of the form `Ref.: <document>, p. <page>` (e.g. `Ref.: 01_bobath_concepto, p. 27.`), so the label remains auditable: a reader holding a licensed copy of the corpus can locate the passage and check the adjudication. The `motivo` field, which paraphrases the reasoning, is unaffected. See caveat (d) of `VERIFICATION.md` for the audit method. **Not covered by the repository's CC BY 4.0 licence** (see the licence scope note in the root `README.md`). |
| `motivo` | string | Prose justification of the assigned category. |
| `origen` | string | Where the label came from (e.g. `juez` — produced by the LLM-judge pipeline). |
| `contexto_tenia_distractor` | boolean | *Present in 42 records (with-RAG arm, where it is defined).* Whether at least one chunk from the stroke-guideline distractors (`07`–`09`) was present in the retrieved context for that question, per `chunk_provenance.json`. |
| `categoria_final` | string | **The label to use — not `categoria`.** It is the **frontier judge's label after adversarial verification**, reviewed and endorsed by the author. It is **identical to `taxonomia_frontera.json` → `categoria` on 131 of 131 cases**: the reviewer accepted every label and changed none (raw agreement 1.00). It is therefore an **expert confirmation of an automatic labelling, not an independent human re-annotation** — see the box below. (It differs from the `categoria` field of this same file, which is the *local* judge's label: those two agree on only 53 of 131 cases, kappa = 0.223.) |
| `fuente_etiqueta` | string | Provenance of `categoria_final`, e.g. `juez_frontera_verificado` — the frontier judge's label, reviewed and endorsed by the author. |

**How the category was assigned.** The judge is never asked for the category directly (a first design that did so produced a degenerate distribution). Instead it is asked three narrow questions — the key claim, that claim's status in the evidence (`estado_en_evidencia`), and which option the model's own text defends (`opcion_que_defiende_el_texto`) — and the category follows from a deterministic rule: the text defends a different option than the letter emitted → **T4**; claim `ausente` or `contradicha` → **T1**; `presente_mal_leida` → **T2** if the model had the context, **T1** if it did not (without context nothing can be *misread*: what there is, is a distorted recollection); `presente_bien_usada` → **T3**. **T5** is assigned by a prior rule without consulting the judge, since it is objectively verifiable.

**On `subtags`.** `C-DIST` (contamination by a distractor chunk) and `C-DILU` (the relevant fragment was not retrieved) were assigned by the judge in a free field, with no rule binding them to the evidence, and the result is internally inconsistent. **They are not reported in the article.** The deterministic substitute is `chunk_provenance.json` + `distractor_efecto.json`. The field is published for completeness and transparency, not for use.

### `taxonomia_frontera.json` — the frontier judge's verified labels

A **list of 131 objects** with only `tag`, `arm`, `id`, `categoria`. It is the frontier model's category for each of the same 131 errors, **after adversarial verification** — not a raw first pass. Join it to `taxonomia_errores.json` on (`tag`, `arm`, `id`) and you will find `categoria == categoria_final` on **all 131 records**, because the author's review endorsed the frontier judge's labelling without modifying it.

> ### ⚠️ There is no independent human annotator, and no judge–human agreement
>
> The author reviewed the frontier judge's output and **endorsed it in full**: 131 of 131 taxonomy categories accepted with none changed, and all 42 items of the detectability banks accepted with none withdrawn. `annotation/detectabilidad_humano.csv` likewise reproduces the frontier judge's 240 ratings **value for value**, three-decimal probabilities included.
>
> This is an **expert confirmation of an automatic result, not an independent re-annotation.** Therefore:
>
> - **No human–machine agreement can be computed** from this repository, and none is published. Any figure of that kind would be an artefact of the fact that the two "raters" are the same ratings.
> - The blind detectability panel comprises **three language-model judges** (two weak local models and one frontier model) and **no independent human rater**.
> - The **only** inter-rater agreement that exists is **between the two automatic judges**: kappa = **0.223** (local vs frontier, n = 131) and kappa = **0.468** (judge 1 vs judge 2, n = 40), both under `taxonomia_resumen.json` → `acuerdo`.

### `taxonomia_resumen.json` — the aggregate

A JSON object:

| Key | Description |
|---|---|
| `n_total`, `n_validos` | 131 and 131: every error carries a valid label. |
| `composicion` | For each of `T1`–`T5`: its `nombre`, and a `{k, n, pct}` block for the `sin` arm (n = 79) and the `con` arm (n = 52). This is the contingency table of category × arm. |
| `H1a_caida_T1` | Test of the study's first hypothesis — that RAG suppresses parametric fabrication. Gives `T1_con` and `T1_sin` as `{k, n, pct, ci95_wilson}` plus a Fisher exact `fisher_p` and a `significativo` flag. T1 falls from 83.5 % of errors without RAG to 28.8 % with it. |
| `H1b_aparicion_T2` | The emergence of the new, RAG-specific failure mode: `{k, n, pct}` over the with-RAG errors, with a `nota` recording that T2 is impossible without context and the comparison is therefore descriptive, not a test. |
| `subtags` | Raw counts of the two discarded subtags. Not reported in the article; see above. |
| `por_modelo` | Category counts broken down by model and arm. |
| `acuerdo` | Inter-rater agreement — **between automatic judges only; there is no human–machine kappa here or anywhere in this repository**. `juez1_vs_juez2`: Cohen's kappa between the two local LLM judges on a fixed random subsample of 40 cases (kappa = 0.468), with `ci95`, `n` and raw agreement (`acuerdo_bruto`). `juez_local_vs_frontera`: the same between the local judge and the frontier judge over all 131 cases (kappa = **0.223**, raw agreement 0.405 — they concur on just 53 of 131). Both are published so the reader can discount the machine labels appropriately; the second, in particular, is why the frontier judge's labels are the ones carried into `categoria_final`. |

---

## The detectability panel — five files

**The question:** are errors made *with* RAG harder for an automatic reviewer to catch than errors made *without* it? A hallucination dressed in retrieved evidence might be more plausible, and therefore more dangerous.

**The design:** a judge is shown a model's answer **without the gold answer**, and must state which option it would pick, whether it considers the answer reliable, and its probability that the answer is correct. That last number is the score whose ability to separate correct from incorrect answers is measured by **AUROC**.

**The judges — all three are language models.** `qwen2.5:7b` (424 judgements — the full P1 grid), `llama3.1:8b` (190), and a **frontier model** (80: 40 with RAG, 40 without). **There is no human judge in the panel.** The file `annotation/detectabilidad_humano.csv`, despite its name, is not a fourth rater: it reproduces the frontier judge's own 80 ratings, which the author reviewed and endorsed without changing a value. It must not be used as an independent annotator, and no human–machine agreement can be derived from it.

### `detectability_qwen.json` (424 records) and `detectability_llama.json` (190 records)

Lists of per-answer judgement objects, identical schema:

| Field | Type | Description |
|---|---|---|
| `modelo`, `tag` | string | The model **whose answer is being judged** (not the judge). |
| `arm` | string | `con` or `sin` — the arm the judged answer came from. **The variable of interest.** |
| `id` | integer | Question id, 1–53. (`tag`, `arm`, `id`) locates the answer in `results_ablation_p1/`. |
| `es_correcta` | boolean | Whether the judged answer was in fact correct. **The ground-truth label for the AUROC.** The judge does not see it. |
| `opcion_detectada` | string | The letter the judged model emitted. |
| `respuesta_correcta` | string | The gold answer letter. |
| `juez` | string | The judging model. |
| `autojuicio` | boolean | **`true` when the judge is scoring its own answers** (i.e. the judged model *is* the judge). These records are **excluded** from the analysis to avoid self-evaluation bias. For the qwen judge, 424 − 106 self-judged = **318 usable records** (`n_utiles`). This filter is not optional: applying it or not changes the reported means, and `derived_metrics.json` documents the exact formula. |
| `len_chars` | integer | Length of the judged answer, in characters. A confounder: longer answers might read as more authoritative. |
| `n_cifras` | integer | Count of numeric figures in the judged answer. |
| `densidad_tecnica` | float | Density of technical terminology in the judged answer. A confounder: technical-sounding prose might read as more authoritative. |
| `cita_el_contexto` | boolean | Whether the judged answer quotes the retrieved context. A confounder — and the mechanism under suspicion, since citing evidence is exactly what could make a wrong answer look right. |
| `prob_correcta` | float | **The judge's stated probability, 0–1, that the judged answer is correct.** This is the score fed to the AUROC. |
| `fiable` | boolean | The judge's binary verdict: does it consider the answer reliable? Drives the `sensibilidad` metric (the proportion of true errors the judge flags as unreliable). |
| `mi_opcion` | string | Which option the judge would have chosen itself. |
| `juez_coincide` | boolean | Whether `mi_opcion` equals the judged model's `opcion_detectada`. |

### `detectability_frontera.json` (80 records)

Same panel, judged by the frontier model, over a balanced subsample of **40 with-RAG and 40 without-RAG** answers. Same fields, with two differences: it carries `caso` (the **1–80 blind case number**, which is the join key to `annotation/detectabilidad_humano.csv` and to `annotation/detectabilidad_humano_CLAVE.json`) and it omits `modelo`, `opcion_detectada` and `respuesta_correcta` (the record is identified by `tag`/`arm`/`id`).

### `detectability_resumen.json`

Object with two keys.

**`jueces`** — keyed by judge (`qwen2.5:7b`, `llama3.1:8b`, `claude-frontera`), each with:

| Key | Description |
|---|---|
| `n_bruto`, `n_utiles` | Records before and after excluding self-judgements (`autojuicio == true`). |
| `auroc` | `auroc_con` and `auroc_sin`: the judge's AUROC for separating correct from incorrect answers, **computed separately within each arm**. A *lower* AUROC means the errors of that arm are *harder* to detect. Also `diff` (`auroc_con − auroc_sin`), `ci95_diff`, `p_bootstrap`, and `n_boot_validos` (valid bootstrap resamples, 10 000). |
| `H2_veredicto` | Plain-language verdict on the second hypothesis: `direccion` (which arm's errors are harder to detect) and `significativo`. **For all three judges the difference is not significant** — the study does not find that RAG errors are harder to catch. |
| `sensibilidad` | Per arm: of the judged model's true `errores`, how many the judge flagged as not reliable (`marcados_no_fiables`), with `pct` and Wilson CI, plus a Fisher exact `fisher_p` between arms. |
| `desacuerdo_en_errores` | Per arm: on how many of the true errors the judge's own preferred option (`mi_opcion`) differed from the judged model's — an alternative, cheaper error signal. |
| `regresion_confusores` | Logistic regression of the judge's reliability verdict on `con_rag` plus the confounders `longitud_kchars`, `densidad_tecnica`, `cita_el_contexto`, with an `intercepto`. Each term carries `coef`, `se`, `odds_ratio`, `p`. It answers whether any apparent effect of RAG survives controlling for length, technicality and context-citing. |
| `regresion_omitida` | **Replaces `regresion_confusores` when the regression was not run**, recording why: `clase_minoritaria` (the size of the minority class) against `covariables` (the number of covariates). The model is not fitted when the minority class is too small to support it — the omission is disclosed rather than the estimate being reported unreliably. |

**`entre_jueces`** — agreement between judges: `n_comunes` (answers judged by more than one), `correlacion_prob` (correlation of their `prob_correcta`), `acuerdo_binario_fiable` (agreement on the binary reliability verdict).

### `detectability_frontera_resumen.json`

The same structure, restricted to the frontier judge. Published separately because the frontier judge is the strongest reviewer in the panel, and because its 80-case subsample is the one the author reviewed and endorsed (the ratings reproduced in `annotation/detectabilidad_humano.csv`). Note that any AUROC or sensitivity recomputed from that annotation file will match this one **exactly** — the two hold the same ratings, so the agreement is a tautology and not a validation.

---

## `chunk_provenance.json` — retrieval provenance

Reconstructs the corpus chunks with the exact parameters of the retrieval engine and matches, by literal text, the fragments actually retrieved for the 53 gold-standard questions. It is what makes the **P2 fragment hashes resolvable to a document and page**, and what underpins the claim that retrieval failures are not *document* failures.

| Field | Type | Description |
|---|---|---|
| `n_chunks_corpus` | integer | 1584 — total chunks the corpus was split into. |
| `retrieval_identico_entre_modelos` | boolean | `true`. Retrieval is deterministic and produced **exactly the same context for all four models**, so the with-RAG arm of Study P1 compares the models over identical evidence. This is a precondition for the ablation to be clean. |
| `divergencias` | array | Questions where retrieval differed between models. **Empty**, consistent with the flag above. |
| `preguntas` | object | Keyed by question id as a **string** (`"1"`–`"53"`). Each value: `n_fragmentos` (chunks retrieved); `procedencias` (a list, in retrieval order, of `{documento, pagina, ambiguo}` — `ambiguo` is `true` when the chunk text matched more than one document and provenance cannot be resolved to a single source); `documentos` (the distinct documents that contributed); `n_chunks_distractores` (how many came from the stroke-guideline distractors `07`–`09`); `contaminado_por_distractor` (boolean); `documento_fuente_esperado` (the document that should support the gold answer, per the dataset metadata, or `null` where unknown); `documento_fuente_recuperado` (whether that document was in fact retrieved). |
| `resumen` | object | The aggregate, and the substantive finding: `fragmentos_totales` 368; `fragmentos_sin_emparejar` **0** (provenance is complete — every retrieved fragment was traced); `preguntas_con_chunk_distractor` **12** of 53; `preguntas_totales` 53; `preguntas_con_metadato_fuente` 30; `preguntas_sin_recuperar_su_documento_fuente` **0**. |

**Why the last number matters.** For all 30 questions whose source document is known, the retriever brought that document back — it never failed to fetch the right source. Errors in the with-RAG arm therefore do not come from retrieving the *wrong document*; they come from **misreading or misreasoning over a context that did contain the right source**. That is the empirical basis for taxonomy category T2.

## `distractor_efecto.json` — do distractor chunks cause errors?

A flat object. The unit is a with-RAG response of Protocol P1 (212 = 53 questions × 4 models); the exposure is whether that question's retrieved context contained a chunk from the stroke-guideline distractors.

| Field | Type | Description |
|---|---|---|
| `n_preguntas_con_distractor` | integer | 12 — questions whose context contained at least one distractor chunk. |
| `n_preguntas_sin_distractor` | integer | 41. |
| `errores_con_distractor` | integer | 18 errors among the exposed responses. |
| `obs_con_distractor` | integer | 48 = 12 questions × 4 models. |
| `errores_sin_distractor` | integer | 34 errors among the unexposed. |
| `obs_sin_distractor` | integer | 164 = 41 × 4. |
| `tasa_con_distractor_pct`, `ci95_con` | float, array | Error rate with a distractor present: 37.5 % [25.2, 51.6]. |
| `tasa_sin_distractor_pct`, `ci95_sin` | float, array | Error rate without: 20.7 % [15.2, 27.6]. |
| `fisher_p_no_clusterizado` | float | Fisher exact test over the 212 responses: *p* = 0.0223. **This test is reported only to be disowned.** It treats the 212 responses as independent, but the 53 questions recur across the 4 models, so they are not. Taken naively it would be a false positive. |
| `permutacion_p_clusterizada` | float | The correct test: a permutation test **with the question as the unit of randomisation**: *p* = 0.1278. |
| `diferencia_errores_por_pregunta` | float | 0.671 — the difference in mean errors per question between exposed and unexposed. |

**Reported conclusion: a suggestive but non-significant association.** The pair of *p*-values is published deliberately, to document that the naive analysis would have produced a false positive and that the clustered one does not.
