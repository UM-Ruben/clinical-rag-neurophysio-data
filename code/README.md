# Code · Código

Source code for the study. Two layers: an **analysis layer** that anyone can run against the
published data, and an **inference layer** that nobody but us can run, published so it can be read.

Código fuente del estudio. Dos capas: una **capa de análisis** que cualquiera puede ejecutar contra
los datos publicados, y una **capa de inferencia** que nadie salvo nosotros puede ejecutar, y que se
publica para que pueda leerse.

---

## EN

### Verify the whole study with one command

```bash
pip install -r code/requirements.txt
python code/reproduce.py
```

No corpus. No GPU. No model server. No network. Python 3.11+.

`reproduce.py` regenerates every regenerable artefact from the **raw published data**, compares it
field by field with the published aggregates, prints an
`ARTEFACT | REGENERATED | PUBLISHED | MATCHES?` table, and **exits non-zero if anything fails to
match**. It ends by listing, explicitly, everything that is *not* reproducible and why — nothing is
omitted in silence.

The load-bearing check is `analysis/audit_reports.py`: it takes the eight raw per-question reports
of protocol P1 and recomputes, from scratch, every accuracy, every delta, the McNemar b/c cells,
the exact p-value and the paired 95% CI — then cross-checks all of it against
`aggregates/rag_benefit_summary.json`. That summary file was assembled by hand from the study's
recomputations, so it is exactly the kind of file you should not take on trust. You don't have to.

### What you can run without the corpus

Everything in `analysis/` — the entire statistical layer:

| Script | What it does |
|---|---|
| `stats_hallucination.py` | Statistical core: Wilson CI, exact McNemar, AUROC with correct tie handling, cluster bootstrap, Cohen's kappa, Holm. `--selftest` reproduces the paper's canonical p-values. |
| `audit_reports.py` | Recomputes protocol P1 from the 8 raw reports and audits `rag_benefit_summary.json`. |
| `aggregate_hallucination.py` | Protocol P2: hallucination, complacency, coverage, risk, Khan 2×2 matrix. |
| `resolve_unparsed.py` | Deterministic rule for the 20 unparsed answers, with a self-test against manual reference labels. |
| `analyze_taxonomia.py` | H1: how the *nature* of the error shifts when RAG is introduced. |
| `analyze_detectability.py` | H2: are RAG errors harder for a blind judge to detect? |
| `finalizar_anotacion.py` | Rebuilds the external adjudication from the `annotation/` CSVs. |
| `make_hallucination_tables.py` | Emits the LaTeX tables. No figure in the paper is typed by hand. |
| `make_hallucination_figures.py` | Emits the vector (PDF) figures. |
| `json_to_csv.py`, `plot_tradeoff.py`, `analyze_embeddings.py` | Exploratory-phase utilities. |

Every script takes `--data-root` (defaults to this repository) and `--out-dir` (defaults to
`code/output/`). **Nothing ever writes inside a published data folder.**

### What you cannot run

Everything in `inference/`. It is published to be *inspected*, not executed: it needs the corpus
(nine copyrighted PDFs, not distributable) and/or a local Ollama server. Each file says so in its
header. It covers the retrieval engine (`evaluate_rag.py`), the two experimental protocols
(`final_rerun.py`, `run_hallucination_arms.py`), the LLM judges (`classify_errors.py`,
`detectability_study.py`), the question banks (`build_banks.py`, `validate_banks.py`,
`create_gold_standard.py`) and chunk provenance (`chunk_provenance.py`).

### The honest declarations

- **The corpus is not distributed.** It is copyrighted teaching material. Any passage of **≥50
  consecutive words** of it that appeared in a published artefact has been replaced by
  `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`. Shorter
  quotations are kept (right of quotation). Across the whole repository this affects **43 spans in
  13 files, 2 468 words**: 24 in the model answers of the three report folders, 14 in `cita_soporte`
  (7 in `aggregates/taxonomia_errores.json` and 7 in `aggregates/errores_prelabel.json`), 4 in
  `traza_cita` (`datasets/dataset_gold_standard.json`) and 1 in `cola`
  (`aggregates/resolucion_no_parseadas.json`). **No script in `code/` carries a redaction.** No
  published statistic reads that text, so no figure changes. Full breakdown: caveat (d) of
  `VERIFICATION.md`.
- **The QLoRA arm is not reproducible by third parties.** Its adapter is fine-tuned on data derived
  from the copyrighted corpus, so neither the weights nor the training pipeline are published. The
  other three models are public on Ollama and fully reproducible. See `EXCLUDED.md`.
- **`distractor_efecto.json` has no producer script.** It was computed in an exploratory session and
  never consolidated into an executable file. `reproduce.py` therefore does **not** vouch for it,
  and says so.
- **`rag_benefit_summary.json` was assembled by hand** from the study's recomputations — which is
  precisely why `audit_reports.py` re-derives it independently from the raw data and checks it field
  by field.
- **Two artefacts diverge from a bit-exact regeneration.** Neither is a computation error, neither
  changes a reported figure, and each is *machine-checked* to stay inside a declared envelope —
  `reproduce.py` fails if either grows beyond it, and prints both on every run. They are
  side-effects of the copyright redaction (`detectability_frontera.json`: two covariates in 2 of 80
  records, measured on the original text, which was longer) and of bootstrap resampling order
  (`taxonomia_resumen.json`: one kappa CI in the fourth decimal; the point kappa agrees to 1e-12).
  Both are set out in full in caveat (g) of `VERIFICATION.md`.
- **A third artefact used to diverge and has been fixed.** `detectability_frontera_resumen.json`
  was generated before `analyze_detectability.py` grew its separation guard, and still carried a
  **degenerate confounder regression** (odds ratio 50.498, standard error 433.8 — complete
  separation, 4 cases in the minority class against 4 covariates). **It has been regenerated**: it
  now reports `regresion_omitida` instead, consistent with the article, which declares that
  regression omitted for separation. `reproduce.py` reproduces it exactly, so it is no longer a
  divergence at all.

### The stack

Python 3.11+ · LangChain ≥0.3 · FAISS-cpu ≥1.8 · rank_bm25 · sentence-transformers 3.3.1 ·
PyTorch 2.6.0+cpu · embeddings `BAAI/bge-m3` · reranker `cross-encoder/ms-marco-MiniLM-L-6-v2` ·
**k=20 per retrieval method** (BM25 + dense), reranked to top-7 · temperature 0 · `num_ctx` 8192.

Models, all on Ollama: `llama3.1:8b`, `qwen2.5:7b`, `thewindmom/llama3-med42-8b` (public) and
`neurofisio-qlora` (not distributed, see above).

### License

Code: MIT (`LICENSE-CODE`). The data files elsewhere in this repository keep their own license.

---

## ES

### Verificar el estudio entero con un solo comando

```bash
pip install -r code/requirements.txt
python code/reproduce.py
```

Sin corpus. Sin GPU. Sin servidor de modelos. Sin red. Python 3.11 o superior.

`reproduce.py` regenera todos los artefactos regenerables a partir de los **datos crudos
publicados**, los coteja campo a campo con los agregados publicados, imprime una tabla
`ARTEFACTO | REGENERADO | PUBLICADO | ¿COINCIDE?` y **termina con código distinto de cero si algo no
cuadra**. Al final enumera, de forma explícita, todo lo que *no* es reproducible y por qué. Nada se
omite en silencio.

La comprobación que sostiene el resto es `analysis/audit_reports.py`: coge los ocho reports crudos
del protocolo P1, pregunta a pregunta, y recomputa desde cero cada accuracy, cada delta, las celdas
b/c de McNemar, la p exacta y el IC95 pareado; después lo coteja todo contra
`aggregates/rag_benefit_summary.json`. Ese resumen se ensambló a mano a partir de las
recomputaciones del estudio, así que es exactamente la clase de fichero que no deberías creerte
porque sí. No hace falta que lo hagas.

### Qué se puede ejecutar sin el corpus

Todo lo de `analysis/`, es decir, toda la capa estadística:

| Script | Qué hace |
|---|---|
| `stats_hallucination.py` | Núcleo estadístico: IC de Wilson, McNemar exacto, AUROC con empates bien tratados, bootstrap por conglomerados, kappa de Cohen, Holm. Su `--selftest` reproduce los p-valores canónicos del artículo. |
| `audit_reports.py` | Recomputa el protocolo P1 desde los 8 reports crudos y audita `rag_benefit_summary.json`. |
| `aggregate_hallucination.py` | Protocolo P2: alucinación, complacencia, cobertura, riesgo, matriz 2×2 de Khan. |
| `resolve_unparsed.py` | Regla determinista para las 20 respuestas no parseadas, con autotest contra la clasificación manual. |
| `analyze_taxonomia.py` | H1: cómo cambia la *naturaleza* del error al introducir RAG. |
| `analyze_detectability.py` | H2: ¿son los errores con RAG más difíciles de detectar para un juez ciego? |
| `finalizar_anotacion.py` | Reconstruye la adjudicación externa desde los CSV de `annotation/`. |
| `make_hallucination_tables.py` | Emite las tablas LaTeX. Ninguna cifra del artículo se teclea a mano. |
| `make_hallucination_figures.py` | Emite las figuras vectoriales (PDF). |
| `json_to_csv.py`, `plot_tradeoff.py`, `analyze_embeddings.py` | Utilidades de la fase exploratoria. |

Todos aceptan `--data-root` (por defecto, este repositorio) y `--out-dir` (por defecto,
`code/output/`). **Ninguno escribe jamás dentro de una carpeta de datos publicada.**

### Qué NO se puede ejecutar

Todo lo de `inference/`. Se publica para *inspeccionarlo*, no para ejecutarlo: necesita el corpus
(nueve PDF con copyright, no distribuibles) y/o un servidor Ollama local. Cada fichero lo dice en su
cabecera. Cubre el motor de recuperación (`evaluate_rag.py`), los dos protocolos experimentales
(`final_rerun.py`, `run_hallucination_arms.py`), los jueces LLM (`classify_errors.py`,
`detectability_study.py`), los bancos de preguntas (`build_banks.py`, `validate_banks.py`,
`create_gold_standard.py`) y la procedencia de los fragmentos (`chunk_provenance.py`).

### Las declaraciones honestas

- **El corpus no se distribuye.** Es material docente con derechos de autor. Cualquier pasaje de
  **≥50 palabras consecutivas** suyo que apareciera en un artefacto publicado se ha sustituido por
  `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`. Las citas más
  cortas se conservan (derecho de cita). En todo el repositorio afecta a **43 tramos en 13 ficheros,
  2 468 palabras**: 24 en las respuestas de los modelos de las tres carpetas de reports, 14 en
  `cita_soporte` (7 en `aggregates/taxonomia_errores.json` y 7 en `aggregates/errores_prelabel.json`),
  4 en `traza_cita` (`datasets/dataset_gold_standard.json`) y 1 en `cola`
  (`aggregates/resolucion_no_parseadas.json`). **Ningún script de `code/` lleva redacción.** Ningún
  estadístico publicado lee ese texto, así que no cambia ninguna cifra. Desglose completo: salvedad
  (d) de `VERIFICATION.md`.
- **El brazo QLoRA no es reproducible por terceros.** Su adaptador está afinado sobre datos
  derivados del corpus con copyright, así que ni los pesos ni el pipeline de entrenamiento se
  publican. Los otros tres modelos son públicos en Ollama y sí son reproducibles. Véase
  `EXCLUDED.md`.
- **`distractor_efecto.json` no tiene script productor.** Se calculó en una sesión de análisis
  exploratorio y nunca llegó a consolidarse en un fichero ejecutable. `reproduce.py` **no** lo avala,
  y lo dice.
- **`rag_benefit_summary.json` se ensambló a mano** a partir de las recomputaciones del estudio, que
  es justamente el motivo por el que `audit_reports.py` lo vuelve a derivar de forma independiente
  desde los datos crudos y lo verifica campo a campo.
- **Dos artefactos divergen de una regeneración bit a bit.** Ninguna divergencia es un error de
  cálculo, ninguna cambia una cifra reportada, y cada una lleva una *comprobación automática* que la
  mantiene dentro de un sobre declarado: `reproduce.py` falla si alguna se sale de él, y las imprime
  las dos en cada ejecución. Son efectos colaterales de la redacción por derechos de autor
  (`detectability_frontera.json`: dos covariables en 2 de 80 registros, medidas sobre el texto
  original, que era más largo) y del orden de remuestreo del bootstrap (`taxonomia_resumen.json`: el
  IC de un kappa en el cuarto decimal; el kappa puntual coincide hasta 1e-12). Ambas se detallan en
  la salvedad (g) de `VERIFICATION.md`.
- **Un tercer artefacto divergía y ya está corregido.** `detectability_frontera_resumen.json` se
  generó antes de que `analyze_detectability.py` incorporase su salvaguarda de separación, y todavía
  arrastraba una **regresión de confusores degenerada** (odds ratio 50,498 con error estándar 433,8:
  separación completa, 4 casos en la clase minoritaria frente a 4 covariables). **Se ha
  regenerado**: ahora reporta `regresion_omitida`, coherente con el artículo, que declara esa
  regresión omitida por separación. `reproduce.py` lo reproduce exactamente, de modo que ya no es
  una divergencia.

### La pila

Python 3.11+ · LangChain ≥0.3 · FAISS-cpu ≥1.8 · rank_bm25 · sentence-transformers 3.3.1 ·
PyTorch 2.6.0+cpu · embeddings `BAAI/bge-m3` · reranker `cross-encoder/ms-marco-MiniLM-L-6-v2` ·
**k=20 por método de recuperación** (BM25 + denso), reranqueado a top-7 · temperatura 0 ·
`num_ctx` 8192.

Modelos, todos en Ollama: `llama3.1:8b`, `qwen2.5:7b`, `thewindmom/llama3-med42-8b` (públicos) y
`neurofisio-qlora` (no distribuido, véase arriba).

### Licencia

Código: MIT (`LICENSE-CODE`). Los ficheros de datos del resto del repositorio conservan su propia
licencia.
