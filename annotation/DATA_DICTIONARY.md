# Data dictionary — `annotation/`

The review material behind the two manual studies: the **blind detectability panel** and the **error taxonomy**.

| File | Format | Rows | Content |
|---|---|---|---|
| `detectabilidad_humano.csv` | CSV, **`;`-delimited** | 80 | The frontier judge's 80 ratings, reviewed and endorsed by the author. **Not an independent human panel** — read the warning below. |
| `detectabilidad_humano_CLAVE.json` | JSON list | 80 | The ground-truth key that de-blinds those 80 cases. Contains **no ratings**. |
| `taxonomia_para_anotar.csv` | CSV, **`;`-delimited** | 131 | The annotation template for the error taxonomy, carrying the 131 endorsed category labels. |

> Both CSV files use the **semicolon** as the field separator (the Spanish-locale convention under which they were produced) and are UTF-8 encoded. Parse them with `delimiter=';'`, not with the default comma. Decimal points are written with a dot.

> ## ⚠️ Warning: there is NO independent human rater in this repository
>
> The file name `detectabilidad_humano.csv` is misleading and is kept only because it is the name under which the file was produced. **Its 240 values (80 cases × 3 fields) are byte-for-byte the ratings of the frontier LLM judge** in `aggregates/detectability_frontera.json`, continuous probabilities to three decimals included. The author read the frontier judge's output and **endorsed it in full**, without altering a single value.
>
> The same holds for the taxonomy: `categoria_final` in `aggregates/taxonomia_errores.json` matches the frontier judge's label in `aggregates/taxonomia_frontera.json` on **131 of 131 cases** — the reviewer changed none — and all 42 items of the detectability banks were accepted with none withdrawn.
>
> This is an **expert confirmation of an automatic result, not an independent re-annotation.** The consequences are strict and non-negotiable:
>
> - **Do NOT use this file as a second annotator.** It is not independent of the frontier judge; it *is* the frontier judge.
> - **Do NOT compute inter-annotator agreement** (Cohen's kappa or any other) between this file and `aggregates/detectability_frontera.json` or `aggregates/taxonomia_frontera.json`. The answer is 1.00 by construction and means nothing.
> - **No human–machine agreement figure exists, and none can be computed** from this repository. Any such figure would be an artefact.
> - The blind detectability panel is composed of **three language models** (two weak local models and one frontier model). **It contains no independent human ratings.**
>
> The only inter-rater agreement that exists here is **between the two automatic judges**: Cohen's kappa = **0.223** (local judge vs frontier judge, n = 131) and **0.468** (judge 1 vs judge 2, n = 40), both in `aggregates/taxonomia_resumen.json` → `acuerdo`. Neither is a human–machine kappa.

> ### Warning: these annotations belong to Protocol P1
>
> Every annotated case comes from **Study P1** (`results_ablation_p1/`), where three options are offered (`a`/`b`/`c`) and abstention is forbidden. This is why the rater's option field admits only `a`, `b` or `c`, with no abstention value. Do not compare accuracy figures derived from this folder with anything from Protocol P2, where a fourth option exists and abstention is a legitimate answer.

---

## The blind detectability panel: how the two files fit together

**The question:** are errors made *with* RAG harder for a reviewer to catch than errors made *without* it? An answer wrapped in retrieved evidence may look more convincing, which would make it more dangerous, not less.

**The design.** A balanced subsample of **80 answers** was drawn from Study P1 — **40 from the with-RAG arm and 40 from the without-RAG arm**, half of each being correct answers and half errors. Each was stripped of its identifying metadata and presented to the raters as a numbered **case, 1 to 80**, showing only the question, the options and the model's free-text answer. **The gold answer was withheld**, and so was the arm the answer came from: the rater could not know whether the model had had retrieved context or not.

**Who rated the 80 cases.** They were rated by the **frontier LLM judge** (`aggregates/detectability_frontera.json`). The author then reviewed that output and endorsed it in full: `detectabilidad_humano.csv` reproduces those same 80 ratings, unmodified. **The panel therefore consists of three language-model judges and no independent human rater**, and machine-versus-human detectability cannot be compared on this material.

**The blinding is undone by `caso`.** The number 1–80 is the only join key. `detectabilidad_humano.csv` carries the rating and nothing else; `detectabilidad_humano_CLAVE.json` maps each `caso` back to the answer it came from, and to the truth. Joining the two is what turns a set of blind opinions into a measurable detection performance. The two files are kept separate because that separation is what makes the blinding auditable: the rating file, on its own, provably contains nothing that could have identified the arm.

---

## `detectabilidad_humano.csv` — the frontier judge's ratings, endorsed by the author

80 rows, one per case. **These 240 values are identical to the frontier judge's ratings in `aggregates/detectability_frontera.json`** (see the warning at the top of this file): the author reviewed them and accepted every one. They are *not* an independent second opinion, and must never be used as one.

The header row spells the admissible values out in the column names, exactly as the case was presented to the rater:

```
caso;mi_opcion(a/b/c);fiable(si/no);prob_correcta(0-1)
1;b;si;0.900
```

| Column | Type | Description |
|---|---|---|
| `caso` | integer | The blind case number, **1–80**. The only join key to `detectabilidad_humano_CLAVE.json` and to `aggregates/detectability_frontera.json`. |
| `mi_opcion(a/b/c)` | string | Which option the rater would have chosen, having read the question and the model's answer but **not** the gold answer. Values `a`, `b`, `c`. Equal to `mi_opcion` in `detectability_frontera.json` on all 80 cases. |
| `fiable(si/no)` | string | The binary verdict on whether the model's answer is trustworthy. Values **`si`** / **`no`** (Spanish for yes/no, written without the accent). Equal to `fiable` in `detectability_frontera.json` on all 80 cases. This drives the **sensitivity** metric: of the answers that were in fact wrong, how many were flagged as unreliable? |
| `prob_correcta(0-1)` | float | The stated probability, from 0 to 1, that the model's answer is correct, to three decimals. Equal to `prob_correcta` in `detectability_frontera.json` on all 80 cases. **This is the score whose ability to separate correct answers from errors is measured by AUROC**, computed separately for the with-RAG and without-RAG halves of the sample. A lower AUROC on one arm means that arm's errors are harder to detect. |

The three rating fields mirror the fields `mi_opcion`, `fiable` and `prob_correcta` of the machine judges in `aggregates/detectability_*.json` — not merely in schema but **in value**, because they are the frontier judge's own ratings. Any AUROC or sensitivity computed from this file will therefore reproduce the frontier judge's figures in `aggregates/detectability_frontera_resumen.json` exactly. That is a tautology, not a validation.

## `detectabilidad_humano_CLAVE.json` — the de-blinding key

A JSON **list of 80 objects**, one per case. **It is a ground-truth key, not a set of ratings**: it contains no rater's opinion of any kind. It is purely the map from a blind case number back to the record it was drawn from, plus the truth that the rater was not shown.

| Field | Type | Description |
|---|---|---|
| `caso` | integer | The blind case number, 1–80. Join key. |
| `tag` | string | The model whose answer this was: `llama8b`, `qlora`, `qwen7b`, `med42`. |
| `arm` | string | `con` (with RAG) or `sin` (without RAG) — **the variable that was hidden from the raters** and the one the whole panel exists to test. 40 cases each. |
| `id` | integer | Question id, 1–53. Together with `tag` and `arm`, this locates the original record in `results_ablation_p1/`. |
| `es_correcta` | boolean | Whether the model's answer was in fact correct. **The ground-truth label for the AUROC and for the sensitivity metric.** |
| `opcion_detectada` | string | The option letter the model actually emitted. |
| `respuesta_correcta` | string | The gold answer letter. |

Joining rating to key on `caso` gives, per arm, the AUROC of `prob_correcta` against `es_correcta`, and the proportion of true errors flagged `fiable = no`. The corresponding machine-judge results are in `aggregates/detectability_resumen.json` and `aggregates/detectability_frontera_resumen.json`.

---

## `taxonomia_para_anotar.csv` — the annotation template, with the 131 endorsed labels

The **annotation template** for the error taxonomy. Its `categoria(T1-T5)` column carries the labels the author endorsed after reviewing the frontier judge's output.

> **This sheet is not an independent re-annotation.** Its 131 categories match the frontier judge's labels in `aggregates/taxonomia_frontera.json` on **131 of 131 cases**: the reviewer accepted every one and modified none (raw agreement 1.00). Treat it as an **expert endorsement of an automatic labelling**, not as a second rater.
>
> Consequently **no judge–human kappa exists or can be computed.** The agreement figures that do exist are between the two *automatic* judges (`aggregates/taxonomia_resumen.json` → `acuerdo`): kappa = **0.223** for the local judge vs the frontier judge over all 131 cases (raw agreement 0.405), and kappa = **0.468** between the two local judges over a 40-case subsample. The low first figure is exactly why the frontier judge's labels, and not the local judge's, are the ones carried into `categoria_final`.

131 rows, one per erroneous response of Protocol P1 (52 from the with-RAG arm, 79 from the without-RAG arm). Header:

```
tag;arm;id;correcta;elegida;categoria(T1-T5);subtags(C-DIST,C-DILU);notas
llama8b;con;4;a;b;T1;;
llama8b;con;13;c;desconocida;T5;;
```

Note that the header line itself contains a comma inside the column name `subtags(C-DIST,C-DILU)`. Because the delimiter is the semicolon this is unambiguous, but a parser configured for comma-separated values will split that column in two and misread the file.

| Column | Type | Description |
|---|---|---|
| `tag` | string | The model that made the error: `llama8b`, `qlora`, `qwen7b`, `med42`. |
| `arm` | string | `con` or `sin`. |
| `id` | integer | Question id, 1–53. (`tag`, `arm`, `id`) uniquely locates the erroneous response in `results_ablation_p1/` and joins to `aggregates/taxonomia_errores.json`. |
| `correcta` | string | The gold answer letter. |
| `elegida` | string | The letter the model emitted, or **`desconocida`** when no interpretable letter could be extracted. A `desconocida` value is what forces category **T5**. |
| `categoria(T1-T5)` | string | The endorsed category — one and only one of `T1`–`T5`, mutually exclusive. It is the **frontier judge's label, reviewed and accepted by the author** (131/131 unchanged), and it is the value that appears as `categoria_final` in `aggregates/taxonomia_errores.json`. |
| `subtags(C-DIST,C-DILU)` | string | Optional secondary tags, comma-separated within the cell; **empty in this sheet**. The subtags were **discarded from the article**: the LLM judge assigned them in a free field with no rule tying them to the evidence, and the result contradicted the judge's own other answers. The deterministic replacement is `aggregates/chunk_provenance.json` + `aggregates/distractor_efecto.json`. The column is preserved for transparency, not for use. |
| `notas` | string | Free-text reviewer notes. Optional; may be empty. |

### The five categories

| Category | Name | Meaning |
|---|---|---|
| **T1** | Parametric fabrication | The model asserts as true a clinical fact **absent from the available evidence** and leans on it to justify its choice. |
| **T2** | Misreading of the context | *Only possible in the with-RAG arm.* The needed fact **is** in the retrieved fragments, but the model reads it wrongly. Without context there is nothing to misread, so an error of this shape in the `sin` arm is a distorted recollection, i.e. T1. |
| **T3** | Invalid reasoning | The facts are right; the inference joining them to the chosen option does not hold. |
| **T4** | Right premise, wrong option | The prose explicitly identifies the correct content, but the emitted letter does not match it. A mapping failure, not a knowledge failure. |
| **T5** | Residual refusal | The model refuses, or emits no interpretable letter, **despite the anti-refusal clause of Protocol P1**. A failure of the protocol rather than of knowledge — and one of the reasons Protocol P2 exists. |

**Decision order applied when labelling** (first rule that fires, wins): no interpretable letter or an explicit refusal → **T5**; the model's own summary contradicts the letter it emitted → **T4**; it asserts a substantive fact absent from the evidence and that fact carries its choice → **T1**; the facts come from the context but are misread → **T2**; otherwise → **T3**. The rule was applied by the frontier judge and the resulting labels were reviewed and endorsed by the author.
