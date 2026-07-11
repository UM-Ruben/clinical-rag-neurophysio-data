# What is NOT published here, and why · Qué NO se publica aquí, y por qué

*(English first; español a continuación.)*

Publishing a partial codebase and saying nothing about the rest is a way of hiding things. This
file lists every script of the working project that is **not** in `code/`, and the reason. One of
them is excluded because it contains a genuine bug, described below without euphemism.

---

## EN

### 1. `analyze_rag_benefit.py` — excluded: **it has a bug**

This was the original script that computed the RAG benefit table (accuracy with/without RAG,
delta, McNemar). **It groups reports by the `timestamp` field.** The eight canonical reports of
protocol P1 (`results_ablation_p1/*_RERUN.json`) do **not carry a `timestamp` field at all**: they
were written by `final_rerun.py`, whose header omits it.

The consequence is not a crash — it is worse. The script silently falls back to whatever reports
*do* have a timestamp, which are the P2 out-of-distribution and trap runs. It would therefore
compute the "RAG benefit" of the ablation study **from the wrong reports**, and print plausible
looking numbers that are simply not the ones the paper reports.

It is superseded by **`analysis/audit_reports.py`**, which addresses the reports by their canonical
filename, recomputes every figure from the raw per-question data, and cross-checks the result
field by field against `aggregates/rag_benefit_summary.json`. That is the script `reproduce.py`
runs, and it is the reason the ablation numbers can be trusted without trusting us.

### 2. Dataset generation for the QLoRA adapter — excluded: **copyrighted content**

- `blend_datasets_v4.py`
- `generate_mcq_dataset_v4.py`
- `generate_dataset_v3.py`

These embed passages of the source syllabus and generate the QLoRA training data from it. They
cannot be published without publishing the copyrighted material they carry.

### 3. QLoRA fine-tuning pipeline — excluded: **derived from copyrighted data**

- `finetune_neurofisio_v4.py`
- `evaluate_v2.py`
- `evaluate_v4_categorical.py`
- `export_lora_to_ollama.py`

The `neurofisio-qlora` adapter is fine-tuned on data derived from the copyrighted corpus. Neither
the weights nor the training pipeline are distributed.

> **Honest consequence, stated plainly: the QLoRA arm of this study is NOT reproducible by third
> parties.** The other three models are: `llama3.1:8b`, `qwen2.5:7b` and
> `thewindmom/llama3-med42-8b` are all public on Ollama. Everything downstream of inference — every
> statistic, every table, every figure — remains fully verifiable for all four models, because the
> raw per-question outputs of all four are published.

### 4. `export_para_anotacion.py` — excluded: **copyright leak by construction**

It dumps 900 verbatim characters of the retrieved corpus fragment per error into the annotation
`.md` files, so the human adjudicator could read the evidence. That is exactly the kind of bulk
verbatim reproduction the copyright policy forbids. The annotation artefacts it produced are
published in `annotation/` **without** those fragments.

### 5. `RAG_Techniques/` — excluded: **third-party, non-commercial license**

Vendored third-party code under a proprietary non-commercial license. No published script imports
it. Republishing it would violate its license.

### 6. Housekeeping — excluded: noise or broken

- `unsloth_compiled_cache/`, `archive/`, `__pycache__/` — build/scratch artefacts.
- `Dockerfile` — **broken**: it copies a `requirements.txt` that does not exist in the project. It
  never built. Publishing it would be publishing a lie about reproducibility.

---

## ES

### 1. `analyze_rag_benefit.py` — excluido: **tiene un bug**

Era el script original que calculaba la tabla del beneficio del RAG (accuracy con/sin RAG, delta,
McNemar). **Agrupa los reports por el campo `timestamp`.** Los ocho reports canónicos del protocolo
P1 (`results_ablation_p1/*_RERUN.json`) **no tienen campo `timestamp`**: los escribió
`final_rerun.py`, cuya cabecera no lo incluye.

La consecuencia no es que reviente, que sería lo bueno. Es que, en silencio, se queda con los
reports que *sí* llevan timestamp, que son los de P2 (los bancos OOD y TRAP). Calcularía por tanto
el «beneficio del RAG» del estudio ablativo **a partir de los reports equivocados**, e imprimiría
cifras verosímiles que sencillamente no son las que reporta el artículo.

Queda superado por **`analysis/audit_reports.py`**, que direcciona los reports por su nombre
canónico, recomputa cada cifra desde los datos crudos pregunta a pregunta, y coteja el resultado
campo a campo contra `aggregates/rag_benefit_summary.json`. Es el que ejecuta `reproduce.py`, y es
la razón por la que las cifras del ablativo se pueden creer sin tener que creernos a nosotros.

### 2. Generación del dataset del QLoRA — excluido: **contenido con copyright**

- `blend_datasets_v4.py`
- `generate_mcq_dataset_v4.py`
- `generate_dataset_v3.py`

Llevan incrustados pasajes del temario y generan a partir de ellos los datos de entrenamiento del
QLoRA. No se pueden publicar sin publicar el material con copyright que arrastran.

### 3. Pipeline de afinado QLoRA — excluido: **derivado de datos con copyright**

- `finetune_neurofisio_v4.py`
- `evaluate_v2.py`
- `evaluate_v4_categorical.py`
- `export_lora_to_ollama.py`

El adaptador `neurofisio-qlora` está afinado sobre datos derivados del corpus con copyright. Ni los
pesos ni el pipeline de entrenamiento se publican.

> **Consecuencia honesta, dicha sin rodeos: el brazo QLoRA de este estudio NO es reproducible por
> terceros.** Los otros tres sí: `llama3.1:8b`, `qwen2.5:7b` y `thewindmom/llama3-med42-8b` son
> públicos en Ollama. Todo lo que viene después de la inferencia — cada estadístico, cada tabla,
> cada figura — sigue siendo verificable para los cuatro modelos, porque las salidas crudas
> pregunta a pregunta de los cuatro sí están publicadas.

### 4. `export_para_anotacion.py` — excluido: **fuga de copyright por construcción**

Vuelca 900 caracteres verbatim del fragmento recuperado por cada error a los `.md` de anotación,
para que quien adjudicaba pudiera leer la evidencia. Es exactamente la reproducción verbatim masiva
que la política de derechos de autor prohíbe. Los artefactos de anotación que produjo sí se
publican, en `annotation/`, **sin** esos fragmentos.

### 5. `RAG_Techniques/` — excluido: **código de terceros con licencia no comercial**

Código de terceros incorporado al proyecto bajo licencia propietaria no comercial. Ningún script
publicado lo importa. Republicarlo violaría su licencia.

### 6. Intendencia — excluido: ruido o roto

- `unsloth_compiled_cache/`, `archive/`, `__pycache__/` — artefactos de compilación y borradores.
- `Dockerfile` — **roto**: copia un `requirements.txt` que no existe en el proyecto. Nunca llegó a
  construir. Publicarlo sería publicar una mentira sobre la reproducibilidad.
