# VERIFICATION / VERIFICACIÓN

**Audit date / Fecha de la auditoría:** 2026-07-11
**Scope / Alcance:** every file published in this repository, checked against the figures reported in the article.

---

## EN — What was verified

All numbers below were **recomputed from the raw records in this repository** with a throwaway Python script (standard library only: no scipy, no numpy), and compared against (a) the precomputed aggregate files and (b) the figures printed in the article. **No figure was silently corrected.** Anything that did not match is listed under *Caveats*.

### Counts — all match

| Check | Expected | Obtained |
|---|---|---|
| `datasets/dataset_gold_standard.json` | 53 questions | 53 |
| `datasets/dataset_trap_validado.json` | 24 questions | 24 |
| `datasets/dataset_ood_validado.json` | 18 questions | 18 |
| `results_ablation_p1/` reports | 8 files × 53 records | 8 × 53 |
| `results_hallucination_p2_sanitized/` reports | 24 files, 760 inferences | 24, 760 |
| P2 breakdown by bank | 424 original + 192 trap + 144 ood | 424 + 192 + 144 |
| `results_retrieval_exploratory_sanitized/` reports | 4 files × 53 records = 212 inferences | 4 × 53 |
| `results_retrieval_exploratory_sanitized/` recall | 47/53 hits in each of the 4 | 47/53 in 4/4 |
| `aggregates/taxonomia_errores.json` | 131 cases | 131 |
| `aggregates/taxonomia_frontera.json` | 131 cases | 131 |
| `aggregates/errores_prelabel.json` | 131 cases (judge 1, qwen2.5:7b) | 131 (52 con / 79 sin) |
| `aggregates/errores_prelabel_juez2.json` | 40 cases (judge 2, llama3.1:8b) | 40 |
| `aggregates/resolucion_no_parseadas.json` | 20 unparseable answers | 20 |
| `aggregates/detectability_frontera.json` | 80 (40 con / 40 sin) | 80 (40/40) |
| `aggregates/detectability_llama.json` | 190 records | 190 |
| `aggregates/detectability_qwen.json` | 424 records | 424 |
| `aggregates/` total files | — | 16 |

### Protocol 1 accuracies — recomputed from the 8 raw reports, all match

Counting `es_correcta` over `questions[]`, per model and per arm. Each value reproduces both `aggregates/rag_benefit_summary.json` and the article, to the second decimal.

| Model | without RAG | with RAG |
|---|---|---|
| Llama-3.1-8B | 30/53 = 56.60 % | 43/53 = 81.13 % |
| QLoRA neurophysio | 34/53 = 64.15 % | 40/53 = 75.47 % |
| Qwen-2.5-7B | 36/53 = 67.92 % | 37/53 = 69.81 % |
| Med42-8B | 33/53 = 62.26 % | 40/53 = 75.47 % |

The per-model McNemar b/c counts (15/2, 10/4, 8/7, 13/6) also reproduce `rag_benefit_summary.json` exactly.

### Pooled result over the 212 pairs — recomputed, matches

- with RAG **160/212 = 75.47 %**; without RAG **133/212 = 62.74 %**; **Δ = +12.74 pp**
- McNemar: **b = 46**, **c = 19**; χ² with continuity correction **p = 0.00126**; exact binomial **p = 0.00109** (article: *p ≈ 0.001*)
- Paired 95 % CI (normal approximation, **sample** variance, ddof = 1): **[+5.46, +20.01] pp** → rounds to the reported *[+5.5, +20.0]*. Bootstrap cross-check (10 000 resamples): [+5.66, +19.81].

Full formulas and source files: `derived_metrics.json`.

### Retrieval recall@k — recomputed from the raw records, matches the article

Counting `retrieval_recall_hit` over the `questions[]` of the four reports now published in `results_retrieval_exploratory_sanitized/`: **47 hits out of 53 questions in each of the four files**, i.e. `recall@k = 47/53 = 88.679 %`, which is the article's **88.7 %**. The per-question booleans and the `summary.recall_hits` / `summary.recall_at_k` written by the harness agree in all four. The six misses are the same six questions (ids 4, 13, 15, 36, 46, 47) in all four files, as they must be: retrieval is deterministic and was executed identically for the four models. **What this figure is — and the reservation it carries — is set out in caveat (e) below. It is a lexical heuristic, not a human relevance judgement.**

### LLM-judge means and AUROC — recomputed, match

- Mean `prob_correcta` of the qwen2.5:7b judge **on the subset of errors without self-judgement** (`es_correcta == false AND autojuicio == false`): **with RAG 0.457 (n = 36)**, **without RAG 0.624 (n = 62)**. The filter matters: the mean over the full 424 raw records is 0.6755, and over the 318 non-self-judged records 0.6923 — neither is the reported figure. The exact formula is documented in `derived_metrics.json`.
- AUROC per arm, recomputed independently as Mann-Whitney U / (n₊·n₋) in pure Python: **con = 0.7125**, **sin = 0.5772** — identical to the precomputed `aggregates/detectability_resumen.json`.

### Integrity of the sanitisation — verified

The `fragmentos` field of the 24 Protocol-2 reports originally held the verbatim retrieved passages. Each string was replaced by `{sha256, n_chars, documento, pagina}`. Verification: **2 648 / 2 648** hashes recomputed from the source retrieval cache match byte for byte; **0** raw corpus strings remain in the published files. 1 472 of them (bank `original`) carry document + page provenance; 1 176 (banks `trap` / `ood`) carry `"provenance": "no_disponible"` because no provenance mapping exists for those banks.

The four reports of `results_retrieval_exploratory_sanitized/` received the same treatment: **1 472 / 1 472** fragments replaced by the same object schema, all of them carrying document + page (this is the `original` bank, the one `aggregates/chunk_provenance.json` covers), **0** raw corpus strings remaining. Cross-check: the 1 472 `sha256` values are **identical, question by question and position by position, to those already published in the P2 `original` with-RAG reports** — 1 472 / 1 472 — which independently confirms both the hashing and the deterministic, model-independent retrieval.

### The analysis code regenerates the aggregates — `python code/reproduce.py`, exit 0

This release publishes the source code (`code/`, MIT licence). The verification above no longer rests on a throwaway script: it is now an executable artefact of the repository. `python code/reproduce.py` runs the statistical self-test, re-derives Protocol P1 from the eight raw reports, and regenerates each regenerable aggregate from the raw published records, comparing it field by field with the published file.

**Result of the run for this release: exit 0.** Ten artefacts regenerate *exactly*; **two diverge inside a declared and machine-checked envelope**, described in caveat (g) below. `reproduce.py` fails (non-zero) if either divergence grows beyond its envelope, so the exemptions cannot silently widen.

| Artefact | Regenerates exactly? |
|---|---|
| statistical layer (`--selftest`: Wilson, McNemar, AUROC with ties, kappa, Holm, bootstrap) | yes |
| `rag_benefit_summary.json` (recomputed from the 8 raw P1 reports) | yes |
| `resolucion_no_parseadas.json` (+ its self-test against the manual reference) | yes |
| `hallucination_summary.json` | yes |
| `hallucination_summary_resuelto.json` | yes |
| `taxonomia_frontera.json` | yes |
| `taxonomia_errores.json` | yes |
| `detectability_resumen.json` | yes |
| `detectability_frontera_resumen.json` | yes — **this file was regenerated for this release**; see caveat (g) |
| `detectability_frontera.json` | **no** — 2 of 80 records, covariates only; caveat (g) |
| `taxonomia_resumen.json` | **no** — one bootstrap CI, 4th decimal; caveat (g) |

What `reproduce.py` **cannot** regenerate it declares explicitly on every run, with the reason: the raw reports of P1 and P2 (primary data, not derivatives), the three question banks (produced from the copyrighted corpus), `chunk_provenance.json` (needs the corpus to re-chunk), the two local judges' raw verdicts (need an Ollama server), the exploratory embeddings ranking (the other embeddings' reports are not published), and `distractor_efecto.json` — which has **no producer script at all**, and is declared as such in caveat (h) below.

### Privacy scan — clean

Nine pattern families (e-mail addresses, Windows/Unix absolute paths, user home directories, `sk-`/`hf_`/`Bearer` tokens, `api_key`, `password`, private IPs) over the parsed string values of every data file of the repository (**63 data files** — 3 question banks, 8 P1 reports, 24 P2 reports, 4 exploratory-retrieval reports, **16 aggregates**, 3 annotation files, 4 files of the deprecated exploratory campaign and `derived_metrics.json`), covering **97 374 string values**: **0 findings**. The **25 files of `code/`** (22 Python scripts and the requirement files) were scanned under the same patterns: **0 findings** — no absolute path of the author's machine, no credential, no token survives in the published code. The only matches anywhere in the repository are the authors' names and their institutional e-mail addresses, which appear in **`README.md`, `CITATION.cff` and `datapackage.json`** and are published deliberately for attribution and contact. No third-party personal data.

---

## EN — Caveats (please read)

**(a) The exploratory CSV is partial: 306 of 493 evaluations.**
`exploratory/datos_detallados_preguntas.csv` contains **306 rows**, whereas the preliminary exploration reported in the article comprises **493 evaluations**. The remaining 187 were run on the original Fedora workstation and their per-question raw records were not preserved through the migration to Windows. The aggregate rankings that the article actually cites (`modelos_ranking.csv`, `embeddings_ranking.csv`) are complete and were computed at the time from the full 493; only the per-question detail is partial. This is why item 4 of the reproducibility checklist is declared **[partially]**.

**(b) Seven old cluster raw files are NOT published.**
Seven raw result files from the early cluster runs (deprecated protocol, partial coverage) still embed verbatim passages of the teaching corpus. They are excluded on three independent grounds: they are deprecated, they are incomplete, and they carry third-party copyright. None of the article's reported figures depends on them.

**(c) Retrieved passages are published as SHA-256 hashes, not as text.**
The teaching corpus is third-party copyrighted material and is not redistributable. In the Protocol-2 reports the retrieved `fragmentos` are therefore given as SHA-256 digests of the exact UTF-8 string, plus its character count and (for the `original` bank) its source document and page. Anyone holding a licensed copy of the corpus can hash their own chunks and verify that the retrieval was exactly the one reported — without the corpus ever being redistributed here.

**(d) Verbatim corpus text in free-text fields: long quotations redacted, short ones kept.**
The models were prompted to ground their answers in the retrieved evidence and they quote it frequently; the hand-built evidence fields (`traza_cita`, `cita_soporte`) were, by construction, copied from the corpus.

**Fields audited.** Every free-text field of every published file, not only `respuesta_ia`: `pregunta`, `opciones`, `traza_cita`, `cita_soporte`, `justificacion`, `premisa_falsa`, `motivo`, `terminos_clave_ausentes`, `comentario`, and every other string in the 56 JSON files, plus the CSVs under `annotation/` and `exploratory/` and the Markdown documentation.

**Reference used.** Overlap is measured against the **nine complete source documents** (full text extracted with PyMuPDF), *not* against the retrieved chunks. This is a correction of method: an earlier version of this audit compared only against the chunks in the retrieval cache and was therefore blind to quotations that straddle a chunk boundary. Each document is additionally indexed a second time with running headers and footers removed, so that the token stream is continuous across page breaks (a quotation spanning a page boundary is otherwise not contiguous in the extracted text). Two tokenisations are used (*normalised*: lower-cased, accents and punctuation stripped; and *strict*: whitespace-split, punctuation and case preserved). The **most conservative** outcome is applied: a span is redacted if **any** of the four (document variant × tokenisation) combinations reports ≥ 50 consecutive words.

- **Long quotations (≥ 50 consecutive words): redacted.** **43** spans reach that length, spread over **13 files**, the longest being 101 words and the shortest 50, **2 468 words removed in total**. Each was replaced in place by the literal marker `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`, where *N* is the number of words removed. Only the overlapping span is replaced; the surrounding text (the model's own reasoning, or the remainder of the field) is preserved untouched.

  **By folder** (every figure below was obtained by counting the markers in the published files):

  | Folder | Spans | Files | Words |
  |---|---|---|---|
  | `results_ablation_p1/` | 9 (over 7 answers) | 2 | 550 |
  | `results_hallucination_p2_sanitized/` | 9 (over 7 answers) | 4 | 490 |
  | `results_retrieval_exploratory_sanitized/` | 6 (over 5 answers) | 3 | 350 |
  | `datasets/` | 4 | 1 (`dataset_gold_standard.json`) | 231 |
  | `aggregates/` | 15 | 3 | 847 |
  | `code/` | **0** | 0 | 0 |
  | **Total** | **43** | **13** | **2 468** |

  **By field:** **24** in `respuesta_ia` (1 390 words — the three report folders, all in the with-RAG arm); **14** in `cita_soporte` (796 words — 7 in `aggregates/taxonomia_errores.json` and 7 in `aggregates/errores_prelabel.json`, which carries the same judge citations, at the same array indices 12, 18, 50, 83, 85, 90, 123); **4** in `traza_cita` (231 words — `datasets/dataset_gold_standard.json`, longest 66 words); **1** in `cola` (51 words — `aggregates/resolucion_no_parseadas.json`).

  The three files of `aggregates/` that carry redactions are `taxonomia_errores.json` (7 spans, 398 words), `errores_prelabel.json` (7 spans, 398 words) and `resolucion_no_parseadas.json` (1 span, 51 words). `errores_prelabel_juez2.json` carries **none**.

  **No script in `code/` contains a redacted span.** The published code was audited under the same criterion and no script reproduces 50 or more consecutive words of the corpus, so the code layer required no redaction at all.
- **Short quotations (12–49 consecutive words): kept**, under the academic right of quotation. **No count of them is asserted in this release.** A census of the short quotations can only be produced by matching every published free-text field against the source corpus, and the corpus is not published here; an earlier census predates the files added since, so it no longer describes this release and has been withdrawn rather than restated approximately. What can be asserted, and is, is the redaction itself: every span of ≥ 50 consecutive words was removed (next paragraph).

**Evidential function of `traza_cita` and `cita_soporte` is preserved.** These fields exist to evidence, respectively, the question and the error label, so they are not simply emptied. In `datasets/dataset_gold_standard.json` the sibling fields `documento_fuente` and `traza_pagina` already carry the provenance. In `aggregates/taxonomia_errores.json`, which has no such sibling fields, the marker is followed by an explicit `Ref.: <document>, p. <page>`. Anyone holding a licensed copy of the corpus can therefore still locate the passage and check the claim.

**Residual exposure.** After redaction, **0** spans of ≥ 50 consecutive words remain anywhere in the repository, verified against the complete source documents under all four combinations above — the four retrieval reports and the code included. What remains is short quotations of 12–49 consecutive words: scattered, non-contiguous fragments that do not permit the reconstruction of any source document. **The size of that residue is not quantified in this release**: measuring it requires the source corpus, which is not published, and the figure previously given (a percentage of the corpus's distinct 12-grams) was computed before the files added in this release existed. Rather than restate a stale number or approximate a new one, it is withdrawn. `datasets/dataset_trap_validado.json` was checked and required no redaction (its longest overlap is 49 words); `datasets/dataset_ood_validado.json` contains no corpus-derived text by construction.

Redaction is cosmetic and strictly posterior to the experiments: `es_correcta`, `opcion_detectada`, `abstiene`, `alucina`, `retrieval_recall_hit` and every other field were computed on the original, unredacted answers and remain valid. No schema changed and no record count changed (8 × 53 for Protocol 1; 760 inferences for Protocol 2; 4 × 53 for the exploratory retrieval reports; 131 taxonomy cases; 53 gold-standard questions).

**The complete, unredacted raw data is held by the authors and is available on reasonable request for verification purposes** (e.g. to a reviewer or an editor who needs to audit the full model outputs), subject to the copyright constraints of the underlying teaching corpus.

**(e) The article's `recall@k = 88.7 %` is now supported — but it is a lexical heuristic, not human-judged relevance.**
An earlier version of this audit stated that the 88.7 % had no support in the published data. **It now has.** The figure was traced to four raw reports of the exploratory retrieval campaign that had not been published, and those four reports are now released, sanitised, in **`results_retrieval_exploratory_sanitized/`**. This caveat records where the number lives, how it is computed, and the reservation that must travel with it.

**Where it comes from.** The four files (one per model: `llama3.1:8b`, `neurofisio-qlora`, `qwen2.5:7b`, `thewindmom/llama3-med42-8b`) are the with-RAG runs over the 53-question gold-standard bank, the 9-document index and the `BAAI/bge-m3` retriever, executed on 23–24 June 2026. Each carries a per-question `retrieval_recall_hit` and a run-level `summary.recall_at_k`. Recomputed for this audit: **47 hits / 53 questions = 88.679 %** in **each of the four files** — the article's 88.7 %. Anyone can repeat the count in one line.

**How it is computed — and why that matters.** `retrieval_recall_hit` is produced by an **automatic token-overlap heuristic**, not by a relevance judgement. For each question the harness builds an *evidence text* from the question stem plus the text of the **correct option**, tokenises it (lower-case, alphabetic runs of ≥ 3 characters, 27 Spanish stopwords removed) into a set *E*, and for each retrieved chunk *C* computes `|E ∩ C| / |E|`. The question counts as a hit when the **best single retrieved chunk** reaches an overlap of **≥ 0.35** (the harness default `recall_overlap_threshold`, recorded in every header) **and** matches at least 2 tokens. `recall@k` is then simply the proportion of questions that hit.

**The reservation, stated plainly.** This is an **automatic lexical approximation of retrieval quality, not a gold standard of relevance**:

- **No human ever judged which chunk is the relevant one for a question.** No per-chunk relevance labels exist in this work.
- The heuristic asks only whether a retrieved chunk **repeats the vocabulary** of the question and its correct answer. It never asks whether that chunk **supports** the answer. It therefore admits **false positives** (a chunk that shares terminology without answering) and **false negatives** (a chunk that answers in different words — a synonym, a paraphrase, a table).
- The **0.35 threshold is the harness default**. It was not tuned, but neither was it validated against human judgement. A different threshold would give a different recall. `retrieval_overlap` is published per question so that a reader can re-threshold it: the lowest overlap among the 47 hits is 0.3548 and the highest among the 6 misses is 0.3333, so the cut is not arbitrary at the margin, but it is a cut.
- The evidence text is built *post hoc* from the gold answer, which the retriever never saw. That is legitimate for measuring recall, but it means the metric cannot be computed at inference time.

**Read 88.7 % as an automatic, lexical estimate of retrieval quality, not as a human-adjudicated recall.** We publish the raw per-question booleans and overlaps precisely so that the reader can judge the metric, and not only the number it produces.

**The recall is a property of the retriever, not of the generator.** The four files report the same 47 hits, the same 6 misses (question ids 4, 13, 15, 36, 46, 47) and the same `retrieval_overlap` per question. Retrieval is deterministic and was executed identically for the four models: the 1 472 SHA-256 chunk digests published in the four files are byte-identical, in the same order, and `aggregates/chunk_provenance.json` records the same fact independently (`retrieval_identico_entre_modelos: true`, `divergencias: []`). The figure therefore describes the retrieval configuration (`bge-m3`, `top_k = 7`, 9 documents, chunk 1500/400), and is reported once rather than four times.

**It also completes the provenance of Study P1.** The with-RAG arm of P1 did not re-run the retriever: it **replayed the `fragmentos` stored in these four reports**. That is why the 8 P1 reports carry no `fragmentos` field of their own, and it is verifiable here — the 1 472 chunk digests match, position for position, those in the P2 `original` with-RAG reports, and `num_fragmentos` agrees record for record (7 chunks for 51 questions, 6 for one, 5 for another, in every model). Publishing these four files therefore closes the provenance chain of `results_ablation_p1/`, not merely the recall gap.

**Two things this figure is still not.**

- It is **not** the document-level check in `aggregates/chunk_provenance.json`, where the retriever returned the declared source document for **30 of the 30** gold-standard questions that carry one (100 %, at document granularity, over 30 of the 53 questions). That is a coarser, different quantity.
- It is **not** the recall of the deprecated exploratory campaign in `exploratory/datos_detallados_preguntas.csv` (**252/306 = 82.35 %**, a 17-question bank, `top_k = 8`, CPU cluster). That number remains what it always was, and must not be substituted for this one.

**Caveats that remain about the four new files.** They predate Protocol P1 and were run **without the anti-refusal system role**, and their answer-extraction routine is the weaker one of the older harness: it leaves **18 of the 212 records** labelled with the pseudo-option `"correcta"` and **1** as `"desconocida"`, all scored as errors. **Their `accuracy` is therefore contaminated and is not the P1 accuracy — do not use these files for accuracy.** The recall is untouched by this: it is computed on the retrieved chunks, before the model is called, and does not read `respuesta_ia` or `opcion_detectada`. The full field-by-field documentation is in `results_retrieval_exploratory_sanitized/DATA_DICTIONARY.md`.

**(f) There is no independent human validation — the "human" annotation is an endorsement of the frontier judge.**
`annotation/detectabilidad_humano.csv` and `annotation/taxonomia_para_anotar.csv` do **not** contain independent human ratings, despite their names. The frontier LLM judge produced the labels; the author reviewed that output and **endorsed it in full**. Verified in this audit:

- `aggregates/taxonomia_errores.json` → `categoria_final` equals `aggregates/taxonomia_frontera.json` → `categoria` on **131 of 131** cases. Not one category was changed; raw agreement is **1.00** by construction. (For contrast, the *local* judge's `categoria` in the same file agrees with the final label on only **53 of 131**.)
- The **240** values of `annotation/detectabilidad_humano.csv` (80 cases × 3 fields) are **identical, value for value**, to the frontier judge's `mi_opcion`, `fiable` and `prob_correcta` in `aggregates/detectability_frontera.json` — three-decimal probabilities included. The 42 items of the banks were likewise accepted without withdrawal.

This is an **expert confirmation of an automatic result, not an independent re-annotation.** Therefore: **no independent human evaluator exists in this work**; the blind detectability panel is composed of **three language models** (two weak local, one frontier) and no human; and **no human–machine agreement is published, because none can legitimately be computed** — any such kappa would be 1.00 by construction. The only inter-rater agreement that exists is **between the two automatic judges**: kappa = **0.223** (local vs frontier, n = 131, raw agreement 0.405) and **0.468** (judge 1 vs judge 2, n = 40), both in `aggregates/taxonomia_resumen.json` → `acuerdo`. **Neither is a judge–human kappa, and this repository publishes none.**

**(g) `reproduce.py` exits 0, but two artefacts do not regenerate bit-for-bit. Here is exactly why.**
Neither divergence is a computation error and neither changes a figure of the article. Both are bounded by a validator inside `reproduce.py` that checks the divergence is *exactly* the expected one and nothing more: if it ever grew, the script would fail. A third artefact used to diverge and **has been corrected for this release**.

**1. `detectability_frontera.json` — 2 of the 80 records differ, in two covariates only.**
Recomputing the file from `annotation/` reproduces 78 of the 80 records exactly. In the two others — case 63 (`qwen7b`/`con`/id 1) and case 72 (`qwen7b`/`con`/id 38) — the fields `len_chars` and `densidad_tecnica` come out **lower** than published (4 differing values in total).

The reason is the copyright redaction, and the direction of the discrepancy is the proof of it. Those two covariates were measured **on the original text of the answers**, at the time the blind judge actually read them. Afterwards, seven answers of the P1 reports had to be redacted because the model was reproducing ≥ 50 consecutive words of the copyrighted corpus, and two of those seven answers are exactly these two cases. The published text is therefore **shorter than the text the judge saw**, and recomputing a character count over it necessarily gives a smaller number.

**This is methodologically correct, not a defect: the analysis used the original text, which is what the judge was shown.** The validator confirms that (i) the divergence is confined to those two fields, (ii) it occurs only in records whose `respuesta_ia` actually carries a redaction marker, and (iii) **no field of statistical value differs in any record** — `prob_correcta`, `es_correcta`, `fiable`, `juez_coincide` and the rest are identical in all 80. **No published figure depends on these two covariates**: they would only enter the confounder regression, and for the frontier judge that regression **is omitted** for separation (minority class of 4 against 4 covariates — see below). The AUROC, the sensitivity and the H2 verdict do not read them.

**2. `taxonomia_resumen.json` — one bootstrap confidence interval differs in the fourth decimal.**
Everything in the file regenerates exactly except the 95 % CI of a single kappa (local judge vs frontier judge): **regenerated [0.1208, 0.3218]** against **published [0.1210, 0.3223]**.

The point estimate is *not* in dispute: the kappa agrees to **1e-12** (0.2231), over the same **n = 131** and with the same raw agreement. What differs is only the interval, because `kappa_ci` bootstraps by resampling **positions** of the label list, so the replicates it draws depend on the **order** of that list. The published file was computed with the labels in an order that the current `taxonomia_frontera.json` no longer reproduces, and **that original order could not be reconstructed**. We say so plainly rather than reshuffle until the numbers match.

The consequence is nil at the precision the article reports: both intervals round to **[0.12, 0.32]**, which is what is printed. The validator enforces this — it fails if the point kappa, the *n*, the raw agreement or the two reported decimals ever move.

**3. `detectability_frontera_resumen.json` — this one was a real defect, and it has been fixed.**
The previously published version of this file contained a **degenerate confounder regression**: an odds ratio of **50.498** with a standard error of **433.8**. Those numbers are the signature of **complete separation** — the minority class holds 4 cases against 4 covariates, so the likelihood is essentially flat and the estimates mean nothing.

`analyze_detectability.py` now carries a guard that refuses to fit the regression when the minority class is smaller than five cases per covariate, and **the file has been regenerated**. It no longer reports `regresion_confusores`; it reports **`regresion_omitida`**, recording the reason (`clase_minoritaria: 4`, `covariables: 4`). This is consistent with the article, which states that the frontier judge's confounder regression is omitted for separation. `reproduce.py` now regenerates this file **exactly**, so it is no longer a divergence at all — it is listed here because it was one, and because a reader comparing releases deserves to know that a published number was withdrawn and why.

**(h) `aggregates/distractor_efecto.json` is NOT reproducible: it has no producer script.**
Every other aggregate in this repository is regenerated and cross-checked by `code/reproduce.py`. **This one is not, because no script in the repository computes it.** Its figures were derived in an exploratory analysis session that was never consolidated into an executable file, and we did not reconstruct one after the fact.

The numbers themselves are not unverifiable — they are **checkable by hand** from `aggregates/chunk_provenance.json` (which questions had a distractor chunk in their context) and the eight P1 reports (which of those responses were errors), and the file documents its own *n*, *k*, Fisher and clustered-permutation values so that the arithmetic can be followed. But **no script recomputes them, and `reproduce.py` therefore does not vouch for them**: it lists the file under "NOT reproducible" on every run. The distinction matters, so it is stated rather than blurred: every other figure in this release is machine-verified; this one rests on a manual derivation. Its conclusion is in any case a **non-significant** association (clustered permutation *p* = 0.1278), and no claim of the article depends on it.

---

## ES — Qué se ha verificado

Todas las cifras siguientes se han **recomputado desde los crudos de este repositorio** con un script Python de usar y tirar (solo biblioteca estándar: sin scipy ni numpy) y se han comparado con (a) los ficheros agregados precalculados y (b) las cifras impresas en el artículo. **Ninguna cifra se ha corregido en silencio.** Todo lo que no cuadra está en *Salvedades*.

### Conteos — cuadran todos

| Comprobación | Esperado | Obtenido |
|---|---|---|
| `datasets/dataset_gold_standard.json` | 53 preguntas | 53 |
| `datasets/dataset_trap_validado.json` | 24 preguntas | 24 |
| `datasets/dataset_ood_validado.json` | 18 preguntas | 18 |
| Reports de `results_ablation_p1/` | 8 ficheros × 53 registros | 8 × 53 |
| Reports de `results_hallucination_p2_sanitized/` | 24 ficheros, 760 inferencias | 24, 760 |
| Desglose P2 por banco | 424 original + 192 trap + 144 ood | 424 + 192 + 144 |
| Reports de `results_retrieval_exploratory_sanitized/` | 4 ficheros × 53 registros = 212 inferencias | 4 × 53 |
| Recall de `results_retrieval_exploratory_sanitized/` | 47/53 aciertos en cada uno de los 4 | 47/53 en 4/4 |
| `aggregates/taxonomia_errores.json` | 131 casos | 131 |
| `aggregates/taxonomia_frontera.json` | 131 casos | 131 |
| `aggregates/errores_prelabel.json` | 131 casos (juez 1, qwen2.5:7b) | 131 (52 con / 79 sin) |
| `aggregates/errores_prelabel_juez2.json` | 40 casos (juez 2, llama3.1:8b) | 40 |
| `aggregates/resolucion_no_parseadas.json` | 20 respuestas no parseables | 20 |
| `aggregates/detectability_frontera.json` | 80 (40 con / 40 sin) | 80 (40/40) |
| `aggregates/detectability_llama.json` | 190 registros | 190 |
| `aggregates/detectability_qwen.json` | 424 registros | 424 |
| Ficheros totales de `aggregates/` | — | 16 |

### Accuracies del Protocolo 1 — recomputadas desde los 8 crudos, cuadran

Contando `es_correcta` sobre `questions[]`, por modelo y por brazo. Cada valor reproduce a la segunda decimal tanto `aggregates/rag_benefit_summary.json` como el artículo.

| Modelo | sin RAG | con RAG |
|---|---|---|
| Llama-3.1-8B | 30/53 = 56,60 % | 43/53 = 81,13 % |
| QLoRA neurofisio | 34/53 = 64,15 % | 40/53 = 75,47 % |
| Qwen-2.5-7B | 36/53 = 67,92 % | 37/53 = 69,81 % |
| Med42-8B | 33/53 = 62,26 % | 40/53 = 75,47 % |

Los b/c de McNemar por modelo (15/2, 10/4, 8/7, 13/6) también reproducen exactamente `rag_benefit_summary.json`.

### Agregado sobre los 212 pares — recomputado, cuadra

- con RAG **160/212 = 75,47 %**; sin RAG **133/212 = 62,74 %**; **Δ = +12,74 pp**
- McNemar: **b = 46**, **c = 19**; χ² con corrección de continuidad **p = 0,00126**; binomial exacta **p = 0,00109** (artículo: *p ≈ 0,001*)
- IC 95 % pareado (aproximación normal, varianza **muestral**, ddof = 1): **[+5,46, +20,01] pp** → redondea al *[+5,5, +20,0]* publicado. Verificación cruzada por bootstrap (10 000 remuestreos): [+5,66, +19,81].

Fórmulas completas y ficheros fuente: `derived_metrics.json`.

### Recall@k de recuperación — recomputado desde los crudos, cuadra con el artículo

Contando `retrieval_recall_hit` sobre `questions[]` en los cuatro reports que ahora se publican en `results_retrieval_exploratory_sanitized/`: **47 aciertos de 53 preguntas en cada uno de los cuatro ficheros**, es decir `recall@k = 47/53 = 88,679 %`, que es el **88,7 %** del artículo. Los booleanos por pregunta y los `summary.recall_hits` / `summary.recall_at_k` que escribió el arnés coinciden en los cuatro. Los seis fallos son las mismas seis preguntas (ids 4, 13, 15, 36, 46, 47) en los cuatro ficheros, como no puede ser de otro modo: la recuperación es determinista y se ejecutó idéntica para los cuatro modelos. **Qué es exactamente esta cifra —y con qué reserva debe leerse— se detalla en la salvedad (e). Es un heurístico léxico, no un juicio humano de relevancia.**

### Medias del juez LLM y AUROC — recomputadas, cuadran

- Media de `prob_correcta` del juez qwen2.5:7b **sobre el subconjunto de errores sin autojuicios** (`es_correcta == false AND autojuicio == false`): **con RAG 0,457 (n = 36)**, **sin RAG 0,624 (n = 62)**. El filtro es determinante: la media sobre los 424 registros brutos da 0,6755 y sobre los 318 sin autojuicio da 0,6923; ninguna es la cifra publicada. La fórmula exacta está en `derived_metrics.json`.
- AUROC por brazo, recomputado de forma independiente como U de Mann-Whitney / (n₊·n₋) en Python puro: **con = 0,7125**, **sin = 0,5772**, idénticos al precalculado `aggregates/detectability_resumen.json`.

### Integridad del saneado — verificada

El campo `fragmentos` de los 24 reports del Protocolo 2 contenía los pasajes recuperados en verbatim. Cada cadena se ha sustituido por `{sha256, n_chars, documento, pagina}`. Verificación: **2 648 / 2 648** hashes recomputados desde la caché de recuperación original casan byte a byte; quedan **0** cadenas de corpus en los ficheros publicados. 1 472 (banco `original`) llevan procedencia documento + página; 1 176 (bancos `trap` / `ood`) llevan `"provenance": "no_disponible"` porque para esos bancos no existe mapa de procedencia.

Los cuatro reports de `results_retrieval_exploratory_sanitized/` han recibido el mismo tratamiento: **1 472 / 1 472** fragmentos sustituidos por el mismo esquema de objeto, todos ellos con documento + página (es el banco `original`, el que cubre `aggregates/chunk_provenance.json`), y **0** cadenas de corpus restantes. Comprobación cruzada: los 1 472 `sha256` son **idénticos, pregunta a pregunta y posición a posición, a los ya publicados en los reports con RAG del banco `original` de P2** —1 472 / 1 472—, lo que confirma de forma independiente tanto el hasheado como que la recuperación es determinista e independiente del modelo.

### El código de análisis regenera los agregados — `python code/reproduce.py`, exit 0

Esta publicación incluye el código fuente (`code/`, licencia MIT). La verificación anterior ya no descansa en un script de usar y tirar: es ahora un artefacto ejecutable del repositorio. `python code/reproduce.py` ejecuta el autotest estadístico, rederiva el Protocolo P1 desde los ocho reports crudos y regenera cada agregado regenerable a partir de los registros crudos publicados, cotejándolo campo a campo con el fichero publicado.

**Resultado de la ejecución para esta publicación: exit 0.** Diez artefactos se regeneran *exactamente*; **dos divergen dentro de un sobre declarado y comprobado por máquina**, descrito en la salvedad (g). `reproduce.py` falla (código distinto de cero) si alguna de las dos divergencias se sale de su sobre, de modo que las exenciones no pueden ensancharse en silencio.

| Artefacto | ¿Se regenera exactamente? |
|---|---|
| capa estadística (`--selftest`: Wilson, McNemar, AUROC con empates, kappa, Holm, bootstrap) | sí |
| `rag_benefit_summary.json` (recomputado desde los 8 reports crudos de P1) | sí |
| `resolucion_no_parseadas.json` (y su autotest contra la referencia manual) | sí |
| `hallucination_summary.json` | sí |
| `hallucination_summary_resuelto.json` | sí |
| `taxonomia_frontera.json` | sí |
| `taxonomia_errores.json` | sí |
| `detectability_resumen.json` | sí |
| `detectability_frontera_resumen.json` | sí — **este fichero se ha regenerado para esta publicación**; véase la salvedad (g) |
| `detectability_frontera.json` | **no** — 2 de 80 registros, solo covariables; salvedad (g) |
| `taxonomia_resumen.json` | **no** — un IC bootstrap, cuarto decimal; salvedad (g) |

Lo que `reproduce.py` **no** puede regenerar lo declara explícitamente en cada ejecución, con su motivo: los reports crudos de P1 y P2 (dato primario, no derivado), los tres bancos de preguntas (producidos desde el corpus con derechos de autor), `chunk_provenance.json` (necesita el corpus para volver a trocearlo), los veredictos crudos de los dos jueces locales (necesitan un servidor Ollama), el ranking de embeddings de la exploratoria (los reports de los otros embeddings no se publican) y `distractor_efecto.json`, que **no tiene script productor alguno** y se declara como tal en la salvedad (h).

### Escaneo de datos sensibles — limpio

Nueve familias de patrones (correos, rutas absolutas Windows/Unix, directorios de usuario, tokens `sk-`/`hf_`/`Bearer`, `api_key`, `password`, IPs privadas) sobre los valores de cadena ya decodificados de todos los ficheros de datos del repositorio (**63 ficheros de datos**: 3 bancos de preguntas, 8 reports de P1, 24 de P2, 4 reports de recuperación exploratoria, **16 agregados**, 3 de anotación, 4 de la campaña exploratoria deprecada y `derived_metrics.json`), que suman **97 374 valores de cadena**: **0 hallazgos**. Los **25 ficheros de `code/`** (22 scripts de Python y los ficheros de requisitos) se han escaneado con los mismos patrones: **0 hallazgos**; en el código publicado no sobrevive ninguna ruta absoluta de la máquina del autor, ninguna credencial ni ningún token. Las únicas coincidencias en todo el repositorio son los nombres de los autores y sus correos institucionales, que aparecen en **`README.md`, `CITATION.cff` y `datapackage.json`** y se publican deliberadamente para atribución y contacto. Ningún dato personal de terceros.

---

## ES — Salvedades (léanse, por favor)

**(a) El CSV exploratorio es parcial: 306 de 493 evaluaciones.**
`exploratory/datos_detallados_preguntas.csv` contiene **306 filas**, mientras que la exploración preliminar que recoge el artículo suma **493 evaluaciones**. Las 187 restantes se ejecutaron en la estación Fedora original y su detalle por pregunta no sobrevivió a la migración a Windows. Los rankings agregados que el artículo sí cita (`modelos_ranking.csv`, `embeddings_ranking.csv`) están completos y se calcularon en su día sobre las 493; lo parcial es únicamente el detalle por pregunta. Por eso el ítem 4 de la checklist de reproducibilidad se declara **[partially]**.

**(b) Siete crudos antiguos del clúster NO se publican.**
Siete ficheros de resultados de las primeras ejecuciones en clúster (protocolo deprecado, cobertura parcial) siguen incrustando pasajes verbatim del corpus docente. Se excluyen por tres motivos independientes: están deprecados, están incompletos y contienen material con derechos de terceros. Ninguna cifra publicada en el artículo depende de ellos.

**(c) Los pasajes recuperados se publican como hashes SHA-256, no como texto.**
El corpus docente es material con derechos de terceros y no es redistribuible. Por eso, en los reports del Protocolo 2 los `fragmentos` recuperados se entregan como resúmenes SHA-256 de la cadena UTF-8 exacta, junto con su número de caracteres y (para el banco `original`) su documento y página de origen. Quien disponga de una copia licenciada del corpus puede hashear sus propios *chunks* y verificar que la recuperación fue exactamente la reportada, sin que aquí se redistribuya el corpus.

**(d) Texto verbatim del corpus en los campos de texto libre: citas largas redactadas, cortas conservadas.**
A los modelos se les pidió fundamentar la respuesta en la evidencia recuperada y con frecuencia la citan; los campos de evidencia construidos a mano (`traza_cita`, `cita_soporte`) son, por construcción, copia del corpus.

**Campos auditados.** Todos los campos de texto libre de todos los ficheros publicados, no solo `respuesta_ia`: `pregunta`, `opciones`, `traza_cita`, `cita_soporte`, `justificacion`, `premisa_falsa`, `motivo`, `terminos_clave_ausentes`, `comentario` y cualquier otra cadena de los 56 ficheros JSON, además de los CSV de `annotation/` y `exploratory/` y la documentación Markdown.

**Referencia utilizada.** El solapamiento se mide contra los **nueve documentos fuente completos** (texto íntegro extraído con PyMuPDF), *no* contra los *chunks* recuperados. Esto corrige un fallo de método: una versión anterior de esta auditoría comparaba solo contra los *chunks* de la caché de recuperación y era, por tanto, ciega a las citas que cruzan una frontera de *chunk*. Cada documento se indexa además una segunda vez eliminando las cabeceras y pies de página recurrentes, de modo que el flujo de tokens sea continuo entre páginas (si no, una cita que cruza un salto de página no aparece como contigua en el texto extraído). Se emplean dos tokenizaciones (*normalizada*: minúsculas, sin tildes ni puntuación; y *estricta*: separación solo por espacios, conservando puntuación y mayúsculas). Se aplica el criterio **más conservador**: un tramo se redacta si **cualquiera** de las cuatro combinaciones (variante de documento × tokenización) alcanza ≥ 50 palabras consecutivas.

- **Citas largas (≥ 50 palabras consecutivas): redactadas.** **43** tramos alcanzan esa longitud, repartidos en **13 ficheros**, el más largo de 101 palabras y el más corto de 50, **2 468 palabras retiradas en total**. Cada uno se ha sustituido *in situ* por el marcador literal `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`, donde *N* es el número de palabras retiradas. Solo se sustituye el tramo solapado: el texto circundante (el razonamiento propio del modelo, o el resto del campo) queda intacto.

  **Por carpeta** (todas las cifras que siguen se han obtenido contando los marcadores en los ficheros publicados):

  | Carpeta | Tramos | Ficheros | Palabras |
  |---|---|---|---|
  | `results_ablation_p1/` | 9 (en 7 respuestas) | 2 | 550 |
  | `results_hallucination_p2_sanitized/` | 9 (en 7 respuestas) | 4 | 490 |
  | `results_retrieval_exploratory_sanitized/` | 6 (en 5 respuestas) | 3 | 350 |
  | `datasets/` | 4 | 1 (`dataset_gold_standard.json`) | 231 |
  | `aggregates/` | 15 | 3 | 847 |
  | `code/` | **0** | 0 | 0 |
  | **Total** | **43** | **13** | **2 468** |

  **Por campo:** **24** en `respuesta_ia` (1 390 palabras — las tres carpetas de reports, todos en el brazo con RAG); **14** en `cita_soporte` (796 palabras — 7 en `aggregates/taxonomia_errores.json` y 7 en `aggregates/errores_prelabel.json`, que arrastra las mismas citas del juez, en los mismos índices de array 12, 18, 50, 83, 85, 90 y 123); **4** en `traza_cita` (231 palabras — `datasets/dataset_gold_standard.json`, el mayor de 66 palabras); **1** en `cola` (51 palabras — `aggregates/resolucion_no_parseadas.json`).

  Los tres ficheros de `aggregates/` con redacciones son `taxonomia_errores.json` (7 tramos, 398 palabras), `errores_prelabel.json` (7 tramos, 398 palabras) y `resolucion_no_parseadas.json` (1 tramo, 51 palabras). `errores_prelabel_juez2.json` **no lleva ninguna**.

  **Ningún script de `code/` contiene tramos redactados.** El código publicado se auditó con el mismo criterio y ningún script reproduce 50 o más palabras consecutivas del corpus, de modo que la capa de código no necesitó redacción alguna.
- **Citas cortas (12–49 palabras consecutivas): conservadas**, al amparo del derecho de cita académico. **Esta publicación no afirma ninguna cifra sobre ellas.** Un censo de las citas cortas solo puede producirse cotejando cada campo de texto libre publicado contra el corpus fuente, y el corpus no se publica aquí; el censo anterior es previo a los ficheros incorporados desde entonces, de modo que ya no describe esta publicación y se retira en lugar de reformularlo de forma aproximada. Lo que sí puede afirmarse, y se afirma, es la redacción en sí: todo tramo de ≥ 50 palabras consecutivas se retiró (párrafo siguiente).

**Se preserva la función probatoria de `traza_cita` y `cita_soporte`.** Estos campos existen para evidenciar, respectivamente, la pregunta y la etiqueta de error, así que no se vacían sin más. En `datasets/dataset_gold_standard.json` los campos hermanos `documento_fuente` y `traza_pagina` ya aportan la procedencia. En `aggregates/taxonomia_errores.json`, que carece de esos campos hermanos, el marcador va seguido de una referencia explícita `Ref.: <documento>, p. <página>`. Quien disponga de una copia licenciada del corpus puede así localizar el pasaje y comprobar la afirmación.

**Exposición residual.** Tras la redacción **no queda ningún** tramo de ≥ 50 palabras consecutivas en todo el repositorio, verificado contra los documentos fuente completos bajo las cuatro combinaciones anteriores, incluidos los cuatro reports de recuperación y el código. Lo que permanece son citas cortas de 12 a 49 palabras consecutivas: fragmentos dispersos y no contiguos que no permiten reconstruir ningún documento fuente. **El tamaño de ese residuo no se cuantifica en esta publicación**: medirlo exige el corpus fuente, que no se publica, y la cifra que se daba antes (un porcentaje de los 12-gramas distintos del corpus) se calculó antes de que existieran los ficheros incorporados en esta publicación. Antes que repetir un número obsoleto o aproximar uno nuevo, se retira. `datasets/dataset_trap_validado.json` se comprobó y no necesitó redacción (su solapamiento máximo es de 49 palabras); `datasets/dataset_ood_validado.json` no contiene texto derivado del corpus por construcción.

La redacción es cosmética y estrictamente posterior a los experimentos: `es_correcta`, `opcion_detectada`, `abstiene`, `alucina`, `retrieval_recall_hit` y todos los demás campos se calcularon sobre las respuestas originales sin redactar y siguen siendo válidos. No cambia ningún esquema ni ningún conteo (8 × 53 en el Protocolo 1; 760 inferencias en el Protocolo 2; 4 × 53 en los reports de recuperación exploratoria; 131 casos de taxonomía; 53 preguntas del gold standard).

**Los datos crudos completos y sin redactar obran en poder de los autores y están disponibles bajo petición razonada con fines de verificación** (por ejemplo, para una persona revisora o editora que necesite auditar las salidas íntegras de los modelos), sujeto a las restricciones de derechos del corpus docente subyacente.

**(e) El `recall@k = 88,7 %` del artículo ya tiene respaldo — pero es un heurístico léxico, no relevancia juzgada por humanos.**
Una versión anterior de esta auditoría afirmaba que el 88,7 % no tenía respaldo en los datos publicados. **Ahora sí lo tiene.** La cifra se ha rastreado hasta cuatro reports crudos de la campaña exploratoria de recuperación que no se habían publicado, y esos cuatro reports se publican ahora, saneados, en **`results_retrieval_exploratory_sanitized/`**. Esta salvedad deja constancia de dónde vive el número, cómo se calcula y con qué reserva debe leerse.

**De dónde sale.** Los cuatro ficheros (uno por modelo: `llama3.1:8b`, `neurofisio-qlora`, `qwen2.5:7b`, `thewindmom/llama3-med42-8b`) son las ejecuciones con RAG sobre el banco gold standard de 53 preguntas, el índice de 9 documentos y el recuperador `BAAI/bge-m3`, ejecutadas el 23 y 24 de junio de 2026. Cada uno lleva un `retrieval_recall_hit` por pregunta y un `summary.recall_at_k` por ejecución. Recomputado para esta auditoría: **47 aciertos / 53 preguntas = 88,679 %** en **cada uno de los cuatro ficheros**, que es el 88,7 % del artículo. Cualquiera puede repetir el conteo en una línea.

**Cómo se calcula, y por qué eso importa.** `retrieval_recall_hit` lo produce un **heurístico automático de solapamiento de tokens**, no un juicio de relevancia. Para cada pregunta el arnés construye un *texto de evidencia* con el enunciado más el texto de la **opción correcta**, lo tokeniza (minúsculas, secuencias alfabéticas de ≥ 3 caracteres, 27 palabras vacías del español eliminadas) en un conjunto *E* y, para cada fragmento recuperado *C*, calcula `|E ∩ C| / |E|`. La pregunta cuenta como acierto cuando el **mejor fragmento recuperado por sí solo** alcanza un solapamiento **≥ 0,35** (el valor por defecto del arnés, `recall_overlap_threshold`, que consta en todas las cabeceras) **y** coincide en al menos 2 tokens. El `recall@k` es entonces, sencillamente, la proporción de preguntas que aciertan.

**La reserva, dicha sin rodeos.** Es una **aproximación léxica automática a la calidad de la recuperación, no un patrón de oro de relevancia**:

- **Ningún humano juzgó nunca qué fragmento es el relevante para una pregunta.** En este trabajo no existen etiquetas de relevancia por fragmento.
- El heurístico solo pregunta si un fragmento recuperado **repite el vocabulario** de la pregunta y de su respuesta correcta. Nunca pregunta si ese fragmento **la sustenta**. Admite, por tanto, **falsos positivos** (un fragmento que comparte terminología sin responder) y **falsos negativos** (un fragmento que responde con otras palabras: un sinónimo, una paráfrasis, una tabla).
- El **umbral de 0,35 es el valor por defecto del arnés**. No se ajustó, pero tampoco se validó contra criterio humano. Otro umbral daría otro recall. `retrieval_overlap` se publica por pregunta para que el lector pueda reumbralizarlo: el solapamiento más bajo entre los 47 aciertos es 0,3548 y el más alto entre los 6 fallos es 0,3333, de modo que el corte no es arbitrario en el margen, pero es un corte.
- El texto de evidencia se construye *a posteriori* a partir de la respuesta correcta, que el recuperador nunca vio. Es legítimo para medir recall, pero implica que la métrica no puede calcularse en tiempo de inferencia.

**Léase el 88,7 % como una estimación léxica y automática de la calidad de la recuperación, no como un recall adjudicado por humanos.** Publicamos los booleanos y los solapamientos crudos por pregunta precisamente para que el lector pueda juzgar la métrica, y no solo la cifra que produce.

**El recall es una propiedad del recuperador, no del generador.** Los cuatro ficheros reportan los mismos 47 aciertos, los mismos 6 fallos (preguntas 4, 13, 15, 36, 46 y 47) y el mismo `retrieval_overlap` por pregunta. La recuperación es determinista y se ejecutó idéntica para los cuatro modelos: los 1 472 digests SHA-256 de fragmentos publicados en los cuatro ficheros son idénticos byte a byte y en el mismo orden, y `aggregates/chunk_provenance.json` recoge el mismo hecho de forma independiente (`retrieval_identico_entre_modelos: true`, `divergencias: []`). La cifra describe, por tanto, la configuración de recuperación (`bge-m3`, `top_k = 7`, 9 documentos, chunk 1500/400), y se reporta una vez y no cuatro.

**Además, completa la procedencia del estudio P1.** El brazo con RAG de P1 no volvió a ejecutar el recuperador: **reutilizó los `fragmentos` almacenados en estos cuatro reports**. Por eso los 8 reports de P1 no llevan campo `fragmentos` propio, y aquí puede comprobarse: los 1 472 digests coinciden, posición a posición, con los de los reports con RAG del banco `original` de P2, y `num_fragmentos` concuerda registro a registro (7 fragmentos en 51 preguntas, 6 en una y 5 en otra, en los cuatro modelos). Publicar estos cuatro ficheros cierra, pues, la cadena de procedencia de `results_ablation_p1/`, y no solo el hueco del recall.

**Dos cosas que esta cifra sigue sin ser.**

- **No** es la comprobación de nivel documento de `aggregates/chunk_provenance.json`, donde el recuperador trajo el documento fuente declarado en **30 de las 30** preguntas del gold standard que lo declaran (100 %, con granularidad de documento, sobre 30 de las 53). Es una magnitud más gruesa y distinta.
- **No** es el recall de la campaña exploratoria deprecada de `exploratory/datos_detallados_preguntas.csv` (**252/306 = 82,35 %**, banco de 17 preguntas, `top_k = 8`, clúster de CPU). Esa cifra sigue siendo lo que siempre fue, y no debe sustituirse por esta.

**Salvedades que siguen afectando a los cuatro ficheros nuevos.** Son anteriores al Protocolo P1 y se ejecutaron **sin el rol de sistema anti-rechazo**, y su rutina de extracción de respuesta es la más débil del arnés antiguo: deja **18 de los 212 registros** etiquetados con la pseudo-opción `"correcta"` y **1** como `"desconocida"`, todos contabilizados como errores. **Su `accuracy` está, por tanto, contaminada y no es la accuracy de P1: no usen estos ficheros para la precisión.** El recall no se ve afectado por ello: se calcula sobre los fragmentos recuperados, antes de llamar al modelo, y no lee `respuesta_ia` ni `opcion_detectada`. La documentación campo a campo está en `results_retrieval_exploratory_sanitized/DATA_DICTIONARY.md`.

**(f) No hay validación humana independiente: la anotación "humana" es un respaldo del juez de frontera.**
`annotation/detectabilidad_humano.csv` y `annotation/taxonomia_para_anotar.csv` **no** contienen valoraciones humanas independientes, pese a sus nombres. El juez LLM de frontera produjo las etiquetas; el autor revisó esa salida y **la respaldó íntegramente**. Verificado en esta auditoría:

- `aggregates/taxonomia_errores.json` → `categoria_final` coincide con `aggregates/taxonomia_frontera.json` → `categoria` en **131 de 131** casos. No se cambió ni una categoría; el acuerdo bruto es **1,00** por construcción. (Por contraste, el campo `categoria` del *juez local*, en ese mismo fichero, solo coincide con la etiqueta final en **53 de 131**.)
- Los **240** valores de `annotation/detectabilidad_humano.csv` (80 casos × 3 campos) son **idénticos, valor a valor**, a los campos `mi_opcion`, `fiable` y `prob_correcta` del juez de frontera en `aggregates/detectability_frontera.json`, incluidas las probabilidades a tres decimales. Los 42 ítems de los bancos se aceptaron igualmente sin retirar ninguno.

Es una **confirmación experta de un resultado automático, no una reanotación independiente.** Por tanto: **no existe ningún evaluador humano independiente** en este trabajo; el panel ciego de detectabilidad lo componen **tres modelos de lenguaje** (dos locales débiles y uno de frontera) y ningún humano; y **no se publica ningún acuerdo humano-máquina, porque ninguno puede calcularse legítimamente** (cualquier kappa de ese tipo valdría 1,00 por construcción). El único acuerdo entre evaluadores que existe es el que hay **entre los dos jueces automáticos**: kappa = **0,223** (local frente a frontera, n = 131, acuerdo bruto 0,405) y **0,468** (juez 1 frente a juez 2, n = 40), ambos en `aggregates/taxonomia_resumen.json` → `acuerdo`. **Ninguno es un kappa juez-humano, y este repositorio no publica ninguno.**

**(g) `reproduce.py` termina en exit 0, pero dos artefactos no se regeneran bit a bit. Este es el motivo exacto.**
Ninguna de las dos divergencias es un error de cálculo y ninguna cambia una cifra del artículo. Ambas están acotadas por un validador dentro de `reproduce.py` que comprueba que la divergencia es *exactamente* la esperada y nada más: si alguna creciera, el script fallaría. Un tercer artefacto divergía antes y **se ha corregido para esta publicación**.

**1. `detectability_frontera.json` — 2 de los 80 registros difieren, y solo en dos covariables.**
Al recomputar el fichero desde `annotation/` se reproducen exactamente 78 de los 80 registros. En los otros dos —el caso 63 (`qwen7b`/`con`/id 1) y el caso 72 (`qwen7b`/`con`/id 38)— los campos `len_chars` y `densidad_tecnica` salen **más bajos** que los publicados (4 valores discrepantes en total).

El motivo es la redacción por derechos de autor, y el sentido de la discrepancia es la prueba de ello. Esas dos covariables se midieron **sobre el texto ORIGINAL de las respuestas**, cuando el juez ciego las leyó de verdad. Después, siete respuestas de los reports de P1 hubo que redactarlas porque el modelo estaba reproduciendo ≥ 50 palabras consecutivas del corpus con derechos de autor, y dos de esas siete respuestas son justamente estos dos casos. El texto publicado es, por tanto, **más corto que el texto que vio el juez**, y recomputar sobre él un recuento de caracteres da necesariamente un número menor.

**Es metodológicamente correcto, no un defecto: el análisis usó el texto original, que es el que se le mostró al juez.** El validador comprueba que (i) la divergencia se confina a esos dos campos, (ii) solo ocurre en registros cuya `respuesta_ia` lleva efectivamente marca de redacción, y (iii) **ningún campo con valor estadístico difiere en ningún registro**: `prob_correcta`, `es_correcta`, `fiable`, `juez_coincide` y los demás son idénticos en los 80. **Ninguna cifra publicada depende de esas dos covariables**: solo entrarían en la regresión de confusores, y para el juez de frontera esa regresión **se omite** por separación (clase minoritaria de 4 frente a 4 covariables — véase más abajo). El AUROC, la sensibilidad y el veredicto H2 no las leen.

**2. `taxonomia_resumen.json` — un intervalo de confianza bootstrap difiere en el cuarto decimal.**
Todo el fichero se regenera exactamente salvo el IC 95 % de un único kappa (juez local frente a juez de frontera): **regenerado [0,1208; 0,3218]** frente a **publicado [0,1210; 0,3223]**.

La estimación puntual no está en discusión: el kappa coincide hasta **1e-12** (0,2231), sobre la misma **n = 131** y con el mismo acuerdo bruto. Lo único que difiere es el intervalo, porque `kappa_ci` hace bootstrap remuestreando **posiciones** de la lista de etiquetas, de modo que las réplicas que extrae dependen del **ORDEN** de esa lista. El fichero publicado se calculó con las etiquetas en un orden que el `taxonomia_frontera.json` actual ya no reproduce, y **ese orden original no se ha podido reconstruir**. Se dice sin rodeos, en lugar de rebarajar hasta que las cifras casen.

La consecuencia es nula a la precisión que reporta el artículo: ambos intervalos redondean a **[0,12; 0,32]**, que es lo que se imprime. El validador lo impone: falla si el kappa puntual, la *n*, el acuerdo bruto o los dos decimales reportados llegaran a moverse.

**3. `detectability_frontera_resumen.json` — este sí era un defecto real, y está corregido.**
La versión publicada anteriormente de este fichero contenía una **regresión de confusores degenerada**: un *odds ratio* de **50,498** con un error estándar de **433,8**. Esas cifras son la firma de una **separación completa**: la clase minoritaria tiene 4 casos frente a 4 covariables, así que la verosimilitud es prácticamente plana y las estimaciones no significan nada.

`analyze_detectability.py` incorpora ahora una salvaguarda que se niega a ajustar la regresión cuando la clase minoritaria tiene menos de cinco casos por covariable, y **el fichero se ha regenerado**. Ya no reporta `regresion_confusores`: reporta **`regresion_omitida`**, dejando constancia del motivo (`clase_minoritaria: 4`, `covariables: 4`). Es coherente con el artículo, que declara que la regresión de confusores del juez de frontera se omite por separación. `reproduce.py` regenera ahora este fichero **exactamente**, de modo que ya no es una divergencia en absoluto: figura aquí porque lo fue, y porque quien compare publicaciones merece saber que una cifra publicada se ha retirado, y por qué.

**(h) `aggregates/distractor_efecto.json` NO es reproducible: no tiene script productor.**
Todos los demás agregados de este repositorio los regenera y coteja `code/reproduce.py`. **Este no, porque ningún script del repositorio lo calcula.** Sus cifras se derivaron en una sesión de análisis exploratorio que nunca llegó a consolidarse en un fichero ejecutable, y no se ha reconstruido uno a posteriori.

Las cifras en sí no son inverificables: son **comprobables a mano** desde `aggregates/chunk_provenance.json` (qué preguntas tenían un fragmento distractor en su contexto) y los ocho reports de P1 (cuáles de esas respuestas fueron errores), y el fichero documenta sus propias *n*, *k*, Fisher y permutación clusterizada para que pueda seguirse la aritmética. Pero **ningún script las recomputa, y `reproduce.py` por tanto NO las avala**: enumera el fichero bajo «NO REPRODUCIBLE» en cada ejecución. La distinción importa, así que se dice en lugar de difuminarse: todas las demás cifras de esta publicación están verificadas por máquina; esta descansa en una derivación manual. Su conclusión es, en cualquier caso, una asociación **no significativa** (permutación clusterizada *p* = 0,1278), y ninguna afirmación del artículo depende de ella.
