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
| `aggregates/taxonomia_errores.json` | 131 cases | 131 |
| `aggregates/taxonomia_frontera.json` | 131 cases | 131 |
| `aggregates/detectability_frontera.json` | 80 (40 con / 40 sin) | 80 (40/40) |
| `aggregates/detectability_llama.json` | 190 records | 190 |
| `aggregates/detectability_qwen.json` | 424 records | 424 |

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

### LLM-judge means and AUROC — recomputed, match

- Mean `prob_correcta` of the qwen2.5:7b judge **on the subset of errors without self-judgement** (`es_correcta == false AND autojuicio == false`): **with RAG 0.457 (n = 36)**, **without RAG 0.624 (n = 62)**. The filter matters: the mean over the full 424 raw records is 0.6755, and over the 318 non-self-judged records 0.6923 — neither is the reported figure. The exact formula is documented in `derived_metrics.json`.
- AUROC per arm, recomputed independently as Mann-Whitney U / (n₊·n₋) in pure Python: **con = 0.7125**, **sin = 0.5772** — identical to the precomputed `aggregates/detectability_resumen.json`.

### Integrity of the sanitisation — verified

The `fragmentos` field of the 24 Protocol-2 reports originally held the verbatim retrieved passages. Each string was replaced by `{sha256, n_chars, documento, pagina}`. Verification: **2 648 / 2 648** hashes recomputed from the source retrieval cache match byte for byte; **0** raw corpus strings remain in the published files. 1 472 of them (bank `original`) carry document + page provenance; 1 176 (banks `trap` / `ood`) carry `"provenance": "no_disponible"` because no provenance mapping exists for those banks.

### Privacy scan — clean

21 patterns (e-mail addresses, Windows/Unix absolute paths, user names, `sk-`/`hf_`/`Bearer` tokens, `api_key`, `password`, private IPs) over every file of the repository (**70 files in total, of which 56 are data files** — 3 question banks, 8 P1 reports, 24 P2 reports, 13 aggregates, 3 annotation files, 4 exploratory files and `derived_metrics.json`): **0 findings in the data files**. The only matches anywhere in the repository are the authors' names and their institutional e-mail addresses, which appear in **`README.md`, `CITATION.cff` and `datapackage.json`** and are published deliberately for attribution and contact. No absolute paths, no credentials, no tokens, no third-party personal data.

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

**Fields audited.** Every free-text field of every published file, not only `respuesta_ia`: `pregunta`, `opciones`, `traza_cita`, `cita_soporte`, `justificacion`, `premisa_falsa`, `motivo`, `terminos_clave_ausentes`, `comentario`, and every other string in the 52 JSON files, plus the CSVs under `annotation/` and `exploratory/` and the Markdown documentation.

**Reference used.** Overlap is measured against the **nine complete source documents** (full text extracted with PyMuPDF), *not* against the retrieved chunks. This is a correction of method: an earlier version of this audit compared only against the chunks in the retrieval cache and was therefore blind to quotations that straddle a chunk boundary. Each document is additionally indexed a second time with running headers and footers removed, so that the token stream is continuous across page breaks (a quotation spanning a page boundary is otherwise not contiguous in the extracted text). Two tokenisations are used (*normalised*: lower-cased, accents and punctuation stripped; and *strict*: whitespace-split, punctuation and case preserved). The **most conservative** outcome is applied: a span is redacted if **any** of the four (document variant × tokenisation) combinations reports ≥ 50 consecutive words.

- **Long quotations (≥ 50 consecutive words): redacted.** **29** spans reach that length, spread over **8 files**, the longest being 101 words, **1 669 words removed in total**. Each was replaced in place by the literal marker `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`, where *N* is the number of words removed. Only the overlapping span is replaced; the surrounding text (the model's own reasoning, or the remainder of the field) is preserved untouched. By field: **18** in `respuesta_ia` (6 of which were found only once the full documents were used as reference), **7** in `cita_soporte` (`aggregates/taxonomia_errores.json`), **4** in `traza_cita` (`datasets/dataset_gold_standard.json`, longest 66 words).
- **Short quotations (12–49 consecutive words): kept.** **1 219** spans of that length remain (median 16 words, maximum 49, across 30 files). They are retained under the academic right of quotation.

**Evidential function of `traza_cita` and `cita_soporte` is preserved.** These fields exist to evidence, respectively, the question and the error label, so they are not simply emptied. In `datasets/dataset_gold_standard.json` the sibling fields `documento_fuente` and `traza_pagina` already carry the provenance. In `aggregates/taxonomia_errores.json`, which has no such sibling fields, the marker is followed by an explicit `Ref.: <document>, p. <page>`. Anyone holding a licensed copy of the corpus can therefore still locate the passage and check the claim.

**Residual exposure.** After redaction, **0** spans of ≥ 50 consecutive words remain anywhere in the repository, verified against the complete source documents under all four combinations above. What remains is the 1 219 short quotations: scattered, non-contiguous fragments amounting to **1.30 %** of the distinct 12-grams of the corpus (2 222 of 170 510). They do not permit reconstruction of any source document. `datasets/dataset_trap_validado.json` was checked and required no redaction (its longest overlap is 49 words); `datasets/dataset_ood_validado.json` contains no corpus-derived text by construction.

Redaction is cosmetic and strictly posterior to the experiments: `es_correcta`, `opcion_detectada`, `abstiene`, `alucina` and every other field were computed on the original, unredacted answers and remain valid. No schema changed and no record count changed (8 × 53 for Protocol 1; 760 inferences for Protocol 2; 131 taxonomy cases; 53 gold-standard questions).

**The complete, unredacted raw data is held by the authors and is available on reasonable request for verification purposes** (e.g. to a reviewer or an editor who needs to audit the full model outputs), subject to the copyright constraints of the underlying teaching corpus.

**(e) The article's `recall@k = 88.7 %` has no direct support in the published data.**
The article reports a retrieval recall@k of **88.7 %** for the ablation experiment. **That figure cannot be verified, or even reconstructed, from the files published here, and we say so rather than manufacture a substitute.** Concretely:

- The **8 Study-P1 reports carry no retrieval-recall field of any kind.** Their `questions[]` records hold `num_fragmentos` (how many chunks were placed in the prompt) but nothing about whether the *relevant* chunk was among them.
- **`aggregates/chunk_provenance.json` does not permit the reconstruction.** It resolves each retrieved chunk to a document and a page, but it carries **no per-chunk relevance judgement**, and recall@k is undefined without one. The only recall-like quantity it does support is **document-level**: of the **30** gold-standard questions that declare a source document, the retriever returned that document in **30 of 30** (`preguntas_sin_recuperar_su_documento_fuente: 0`) — that is **100 %**, at document granularity, over 30 of the 53 questions. It is a different and coarser quantity, and it is not 88.7 %.
- The **only** retrieval-recall figures anywhere in this repository belong to the **deprecated exploratory campaign** (`exploratory/datos_detallados_preguntas.csv`, fields `retrieval_recall_hit` and `summary_recall_at_k`), and they give **252/306 = 82.35 %** over a different 17-question bank, a different `top_k` (8) and different hardware. **They are not the article's 88.7 %** and must not be used as if they were.

We have not altered the article's figure and we have not invented a derivation for it: the number originates in the analysis pipeline, which is not published (caveat: the source code is withheld by the authors' decision). Readers who need to audit recall@k should request the retrieval cache and the harness from the authors. **No claim in this repository depends on this figure**, and the P1/P2 results reported here are unaffected by it.

**(f) There is no independent human validation — the "human" annotation is an endorsement of the frontier judge.**
`annotation/detectabilidad_humano.csv` and `annotation/taxonomia_para_anotar.csv` do **not** contain independent human ratings, despite their names. The frontier LLM judge produced the labels; the author reviewed that output and **endorsed it in full**. Verified in this audit:

- `aggregates/taxonomia_errores.json` → `categoria_final` equals `aggregates/taxonomia_frontera.json` → `categoria` on **131 of 131** cases. Not one category was changed; raw agreement is **1.00** by construction. (For contrast, the *local* judge's `categoria` in the same file agrees with the final label on only **53 of 131**.)
- The **240** values of `annotation/detectabilidad_humano.csv` (80 cases × 3 fields) are **identical, value for value**, to the frontier judge's `mi_opcion`, `fiable` and `prob_correcta` in `aggregates/detectability_frontera.json` — three-decimal probabilities included. The 42 items of the banks were likewise accepted without withdrawal.

This is an **expert confirmation of an automatic result, not an independent re-annotation.** Therefore: **no independent human evaluator exists in this work**; the blind detectability panel is composed of **three language models** (two weak local, one frontier) and no human; and **no human–machine agreement is published, because none can legitimately be computed** — any such kappa would be 1.00 by construction. The only inter-rater agreement that exists is **between the two automatic judges**: kappa = **0.223** (local vs frontier, n = 131, raw agreement 0.405) and **0.468** (judge 1 vs judge 2, n = 40), both in `aggregates/taxonomia_resumen.json` → `acuerdo`. **Neither is a judge–human kappa, and this repository publishes none.**

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
| `aggregates/taxonomia_errores.json` | 131 casos | 131 |
| `aggregates/taxonomia_frontera.json` | 131 casos | 131 |
| `aggregates/detectability_frontera.json` | 80 (40 con / 40 sin) | 80 (40/40) |
| `aggregates/detectability_llama.json` | 190 registros | 190 |
| `aggregates/detectability_qwen.json` | 424 registros | 424 |

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

### Medias del juez LLM y AUROC — recomputadas, cuadran

- Media de `prob_correcta` del juez qwen2.5:7b **sobre el subconjunto de errores sin autojuicios** (`es_correcta == false AND autojuicio == false`): **con RAG 0,457 (n = 36)**, **sin RAG 0,624 (n = 62)**. El filtro es determinante: la media sobre los 424 registros brutos da 0,6755 y sobre los 318 sin autojuicio da 0,6923; ninguna es la cifra publicada. La fórmula exacta está en `derived_metrics.json`.
- AUROC por brazo, recomputado de forma independiente como U de Mann-Whitney / (n₊·n₋) en Python puro: **con = 0,7125**, **sin = 0,5772**, idénticos al precalculado `aggregates/detectability_resumen.json`.

### Integridad del saneado — verificada

El campo `fragmentos` de los 24 reports del Protocolo 2 contenía los pasajes recuperados en verbatim. Cada cadena se ha sustituido por `{sha256, n_chars, documento, pagina}`. Verificación: **2 648 / 2 648** hashes recomputados desde la caché de recuperación original casan byte a byte; quedan **0** cadenas de corpus en los ficheros publicados. 1 472 (banco `original`) llevan procedencia documento + página; 1 176 (bancos `trap` / `ood`) llevan `"provenance": "no_disponible"` porque para esos bancos no existe mapa de procedencia.

### Escaneo de datos sensibles — limpio

21 patrones (correos, rutas absolutas Windows/Unix, nombres de usuario, tokens `sk-`/`hf_`/`Bearer`, `api_key`, `password`, IPs privadas) sobre todos los ficheros del repositorio (**70 ficheros en total, de los cuales 56 son ficheros de datos**: 3 bancos de preguntas, 8 reports de P1, 24 de P2, 13 agregados, 3 de anotación, 4 de la exploratoria y `derived_metrics.json`): **0 hallazgos en los ficheros de datos**. Las únicas coincidencias en todo el repositorio son los nombres de los autores y sus correos institucionales, que aparecen en **`README.md`, `CITATION.cff` y `datapackage.json`** y se publican deliberadamente para atribución y contacto. Ninguna ruta absoluta, ninguna credencial, ningún token, ningún dato personal de terceros.

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

**Campos auditados.** Todos los campos de texto libre de todos los ficheros publicados, no solo `respuesta_ia`: `pregunta`, `opciones`, `traza_cita`, `cita_soporte`, `justificacion`, `premisa_falsa`, `motivo`, `terminos_clave_ausentes`, `comentario` y cualquier otra cadena de los 52 ficheros JSON, además de los CSV de `annotation/` y `exploratory/` y la documentación Markdown.

**Referencia utilizada.** El solapamiento se mide contra los **nueve documentos fuente completos** (texto íntegro extraído con PyMuPDF), *no* contra los *chunks* recuperados. Esto corrige un fallo de método: una versión anterior de esta auditoría comparaba solo contra los *chunks* de la caché de recuperación y era, por tanto, ciega a las citas que cruzan una frontera de *chunk*. Cada documento se indexa además una segunda vez eliminando las cabeceras y pies de página recurrentes, de modo que el flujo de tokens sea continuo entre páginas (si no, una cita que cruza un salto de página no aparece como contigua en el texto extraído). Se emplean dos tokenizaciones (*normalizada*: minúsculas, sin tildes ni puntuación; y *estricta*: separación solo por espacios, conservando puntuación y mayúsculas). Se aplica el criterio **más conservador**: un tramo se redacta si **cualquiera** de las cuatro combinaciones (variante de documento × tokenización) alcanza ≥ 50 palabras consecutivas.

- **Citas largas (≥ 50 palabras consecutivas): redactadas.** **29** tramos alcanzan esa longitud, repartidos en **8 ficheros**, el más largo de 101 palabras, **1 669 palabras retiradas en total**. Cada uno se ha sustituido *in situ* por el marcador literal `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`, donde *N* es el número de palabras retiradas. Solo se sustituye el tramo solapado: el texto circundante (el razonamiento propio del modelo, o el resto del campo) queda intacto. Por campo: **18** en `respuesta_ia` (6 de ellos detectados solo al usar los documentos completos como referencia), **7** en `cita_soporte` (`aggregates/taxonomia_errores.json`) y **4** en `traza_cita` (`datasets/dataset_gold_standard.json`, el mayor de 66 palabras).
- **Citas cortas (12–49 palabras consecutivas): conservadas.** Quedan **1 219** tramos de esa longitud (mediana 16 palabras, máximo 49, en 30 ficheros). Se mantienen al amparo del derecho de cita académico.

**Se preserva la función probatoria de `traza_cita` y `cita_soporte`.** Estos campos existen para evidenciar, respectivamente, la pregunta y la etiqueta de error, así que no se vacían sin más. En `datasets/dataset_gold_standard.json` los campos hermanos `documento_fuente` y `traza_pagina` ya aportan la procedencia. En `aggregates/taxonomia_errores.json`, que carece de esos campos hermanos, el marcador va seguido de una referencia explícita `Ref.: <documento>, p. <página>`. Quien disponga de una copia licenciada del corpus puede así localizar el pasaje y comprobar la afirmación.

**Exposición residual.** Tras la redacción **no queda ningún** tramo de ≥ 50 palabras consecutivas en todo el repositorio, verificado contra los documentos fuente completos bajo las cuatro combinaciones anteriores. Lo que permanece son las 1 219 citas cortas: fragmentos dispersos y no contiguos que suponen el **1,30 %** de los 12-gramas distintos del corpus (2 222 de 170 510). No permiten reconstruir ningún documento fuente. `datasets/dataset_trap_validado.json` se comprobó y no necesitó redacción (su solapamiento máximo es de 49 palabras); `datasets/dataset_ood_validado.json` no contiene texto derivado del corpus por construcción.

La redacción es cosmética y estrictamente posterior a los experimentos: `es_correcta`, `opcion_detectada`, `abstiene`, `alucina` y todos los demás campos se calcularon sobre las respuestas originales sin redactar y siguen siendo válidos. No cambia ningún esquema ni ningún conteo (8 × 53 en el Protocolo 1; 760 inferencias en el Protocolo 2; 131 casos de taxonomía; 53 preguntas del gold standard).

**Los datos crudos completos y sin redactar obran en poder de los autores y están disponibles bajo petición razonada con fines de verificación** (por ejemplo, para una persona revisora o editora que necesite auditar las salidas íntegras de los modelos), sujeto a las restricciones de derechos del corpus docente subyacente.

**(e) El `recall@k = 88,7 %` del artículo no tiene respaldo directo en los datos publicados.**
El artículo reporta un recall@k de recuperación del **88,7 %** para el experimento ablativo. **Esa cifra no puede verificarse, ni siquiera reconstruirse, a partir de los ficheros aquí publicados, y lo decimos en lugar de fabricar un sustituto.** En concreto:

- Los **8 reports del estudio P1 no llevan ningún campo de recall de recuperación.** Sus registros de `questions[]` contienen `num_fragmentos` (cuántos fragmentos se colocaron en el prompt), pero nada sobre si el fragmento *relevante* estaba entre ellos.
- **`aggregates/chunk_provenance.json` no permite reconstruirlo.** Resuelve cada fragmento recuperado a un documento y una página, pero **no contiene ningún juicio de relevancia por fragmento**, y sin él el recall@k no está definido. La única magnitud parecida al recall que sí admite es **de nivel documento**: de las **30** preguntas del gold standard que declaran documento fuente, el recuperador trajo ese documento en **30 de 30** (`preguntas_sin_recuperar_su_documento_fuente: 0`), es decir un **100 %** con granularidad de documento y sobre 30 de las 53 preguntas. Es una magnitud distinta y más gruesa, y no es el 88,7 %.
- Las **únicas** cifras de recall de recuperación de todo el repositorio pertenecen a la **campaña exploratoria deprecada** (`exploratory/datos_detallados_preguntas.csv`, campos `retrieval_recall_hit` y `summary_recall_at_k`), y dan **252/306 = 82,35 %** sobre un banco distinto de 17 preguntas, otro `top_k` (8) y otro hardware. **No son el 88,7 % del artículo** y no deben usarse como si lo fueran.

No hemos alterado la cifra del artículo ni le hemos inventado una derivación: el número procede de la cadena de análisis, que no se publica (salvedad: el código se retiene por decisión de los autores). Quien necesite auditar el recall@k debe solicitar a los autores la caché de recuperación y el arnés. **Ninguna afirmación de este repositorio depende de esa cifra**, y los resultados de P1 y P2 aquí publicados no se ven afectados por ella.

**(f) No hay validación humana independiente: la anotación "humana" es un respaldo del juez de frontera.**
`annotation/detectabilidad_humano.csv` y `annotation/taxonomia_para_anotar.csv` **no** contienen valoraciones humanas independientes, pese a sus nombres. El juez LLM de frontera produjo las etiquetas; el autor revisó esa salida y **la respaldó íntegramente**. Verificado en esta auditoría:

- `aggregates/taxonomia_errores.json` → `categoria_final` coincide con `aggregates/taxonomia_frontera.json` → `categoria` en **131 de 131** casos. No se cambió ni una categoría; el acuerdo bruto es **1,00** por construcción. (Por contraste, el campo `categoria` del *juez local*, en ese mismo fichero, solo coincide con la etiqueta final en **53 de 131**.)
- Los **240** valores de `annotation/detectabilidad_humano.csv` (80 casos × 3 campos) son **idénticos, valor a valor**, a los campos `mi_opcion`, `fiable` y `prob_correcta` del juez de frontera en `aggregates/detectability_frontera.json`, incluidas las probabilidades a tres decimales. Los 42 ítems de los bancos se aceptaron igualmente sin retirar ninguno.

Es una **confirmación experta de un resultado automático, no una reanotación independiente.** Por tanto: **no existe ningún evaluador humano independiente** en este trabajo; el panel ciego de detectabilidad lo componen **tres modelos de lenguaje** (dos locales débiles y uno de frontera) y ningún humano; y **no se publica ningún acuerdo humano-máquina, porque ninguno puede calcularse legítimamente** (cualquier kappa de ese tipo valdría 1,00 por construcción). El único acuerdo entre evaluadores que existe es el que hay **entre los dos jueces automáticos**: kappa = **0,223** (local frente a frontera, n = 131, acuerdo bruto 0,405) y **0,468** (juez 1 frente a juez 2, n = 40), ambos en `aggregates/taxonomia_resumen.json` → `acuerdo`. **Ninguno es un kappa juez-humano, y este repositorio no publica ninguno.**
