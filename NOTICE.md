# NOTICE — Scope of the licence / Alcance de la licencia

## English

This repository is published under **two licences**, one for the data and one for the code.

| What | Licence | Full text |
|---|---|---|
| **The data** — the three question banks (Gold Standard, TRAP, OOD), the model responses and per-question records, the aggregate results, the error taxonomy, the detectability panel, the annotation files and all documentation | **CC BY 4.0** | [`LICENSE`](LICENSE) |
| **The code** — everything under `code/`: the analysis layer, the inference layer and `reproduce.py` | **MIT** | [`code/LICENSE-CODE`](code/LICENSE-CODE) |

The two are deliberately different. CC BY 4.0 is the appropriate licence for a research dataset, whose value lies in being cited; MIT is the customary licence for software, and lets the scripts be reused, modified and embedded in other projects without carrying a data licence's attribution machinery. Both apply only to **material created by the authors**.

Neither licence extends to third-party material. Specifically:

1. **The source corpus is not distributed here.** The retrieval corpus consists of copyrighted teaching material on neurophysiotherapy plus three open-access clinical practice guidelines on stroke. Neither the PDFs nor their extracted text are included in this repository.

2. **Retrieved context is published as hashes, not text.** In the P2 reports, in the four reports of `results_retrieval_exploratory_sanitized/` and in the seven reports of `results_scale_campaign_sanitized/`, the `fragmentos` field (the context passages retrieved by the RAG system) was replaced with SHA-256 hashes together with the character count and, where derivable, the source document and page. This lets anyone who holds a licensed copy of the corpus verify exactly which passage was retrieved, without redistributing the text itself.

3. **Long verbatim quotations were redacted, in every free-text field.** Because the models were instructed to ground their answers in the retrieved evidence, some responses reproduce the corpus literally; the hand-built evidence fields quote it by construction. Every free-text field of every published file was audited against the nine complete source documents, and passages reproducing **50 or more consecutive words** of the source corpus were replaced with the marker `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`. This affects **64 spans in 16 files, 3 676 words removed in total**: 45 in `respuesta_ia` (the four report folders), 14 in `cita_soporte` (7 in `aggregates/taxonomia_errores.json` and 7 in `aggregates/errores_prelabel.json`), 4 in `traza_cita` (`datasets/dataset_gold_standard.json`) and 1 in `cola` (`aggregates/resolucion_no_parseadas.json`). **No file under `code/` carries a redaction**: no published script reproduces 50 or more consecutive words of the corpus. Shorter quotations are retained. Where a redacted field served as evidence, its provenance (document and page) is preserved so the field remains auditable. The full per-folder breakdown is in caveat (d) of `VERIFICATION.md`.

4. **Short quotations retained under the right of quotation.** Some fields deliberately preserve short literal quotations from the source corpus (**fewer than 50 consecutive words**), always attributed with document and page: the `traza_cita` field in the TRAP bank (audited, no redaction required) and in the gold-standard bank, the `cita_soporte` field in `taxonomia_errores.json` and `errores_prelabel.json`, as well as the sub-50-word quotations inside `respuesta_ia`. These are retained under the academic right of quotation (Art. 32 of the Spanish Intellectual Property Act and equivalent provisions elsewhere) for the purposes of research, analysis and verification. **They are not covered by the CC BY 4.0 licence** and remain the property of their respective rights holders. Anyone reusing this dataset should treat those quotations accordingly.

5. **The QLoRA fine-tuning pipeline is not published, and that arm is not reproducible.** The `neurofisio-qlora` adapter was fine-tuned on data derived from the copyrighted corpus, so neither its weights nor its training scripts are released (`code/EXCLUDED.md` lists them). The consequence is stated plainly: **the QLoRA arm of this study cannot be reproduced by a third party.** The other three models (`llama3.1:8b`, `qwen2.5:7b`, `thewindmom/llama3-med42-8b`) are public on Ollama and are reproducible. Everything downstream of inference remains verifiable for all four, because the raw outputs of all four are published and `code/analysis/` recomputes the figures from them.

The complete, unredacted data is held by the authors and is available on reasoned request for verification purposes.

---

## Español

Este repositorio se publica bajo **dos licencias**, una para los datos y otra para el código.

| Qué | Licencia | Texto completo |
|---|---|---|
| **Los datos** — los tres bancos de preguntas (Gold Standard, TRAP, OOD), las respuestas de los modelos y los registros por pregunta, los resultados agregados, la taxonomía de errores, el panel de detectabilidad, los ficheros de anotación y toda la documentación | **CC BY 4.0** | [`LICENSE`](LICENSE) |
| **El código** — todo lo que hay bajo `code/`: la capa de análisis, la de inferencia y `reproduce.py` | **MIT** | [`code/LICENSE-CODE`](code/LICENSE-CODE) |

Son distintas a propósito. La CC BY 4.0 es la licencia adecuada para un conjunto de datos de investigación, cuyo valor está en que se cite; la MIT es la licencia habitual del software y permite reutilizar, modificar e incrustar los scripts en otros proyectos sin arrastrar la maquinaria de atribución propia de una licencia de datos. Ambas se aplican únicamente al **material de creación propia de los autores**.

Ninguna de las dos se extiende al material de terceros. En concreto:

1. **El corpus fuente no se distribuye aquí.** El corpus de recuperación está formado por material docente de neurofisioterapia con derechos de autor y tres guías de práctica clínica del ictus de acceso abierto. Ni los PDF ni su texto extraído se incluyen en este repositorio.

2. **El contexto recuperado se publica como hashes, no como texto.** En los reports de P2, en los cuatro reports de `results_retrieval_exploratory_sanitized/` y en los siete de `results_scale_campaign_sanitized/`, el campo `fragmentos` (los pasajes de contexto recuperados por el sistema RAG) se sustituyó por hashes SHA-256 junto con el número de caracteres y, cuando es derivable, el documento y la página de origen. Esto permite a quien disponga de una copia legítima del corpus verificar exactamente qué pasaje se recuperó, sin redistribuir el texto.

3. **Se redactaron las citas literales largas, en todos los campos de texto libre.** Dado que se instruyó a los modelos para que anclaran su respuesta en la evidencia recuperada, algunas respuestas reproducen el corpus literalmente; los campos de evidencia construidos a mano lo citan por construcción. Se auditaron todos los campos de texto libre de todos los ficheros publicados contra los nueve documentos fuente completos, y los pasajes que reproducían **50 o más palabras consecutivas** del corpus fuente se sustituyeron por el marcador `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`. Afecta a **64 tramos en 16 ficheros, 3 676 palabras retiradas en total**: 45 en `respuesta_ia` (las cuatro carpetas de reports), 14 en `cita_soporte` (7 en `aggregates/taxonomia_errores.json` y 7 en `aggregates/errores_prelabel.json`), 4 en `traza_cita` (`datasets/dataset_gold_standard.json`) y 1 en `cola` (`aggregates/resolucion_no_parseadas.json`). **Ningún fichero de `code/` lleva redacción alguna**: ningún script publicado reproduce 50 o más palabras consecutivas del corpus. Las citas más breves se conservan. Cuando el campo redactado cumplía una función probatoria, se conserva su procedencia (documento y página) para que siga siendo auditable. El desglose completo por carpeta está en la salvedad (d) de `VERIFICATION.md`.

4. **Citas breves conservadas al amparo del derecho de cita.** Algunos campos conservan deliberadamente citas literales breves del corpus fuente (**de menos de 50 palabras consecutivas**), siempre atribuidas con documento y página: el campo `traza_cita` del banco TRAP (auditado, sin necesidad de redacción) y del banco gold standard, el campo `cita_soporte` de `taxonomia_errores.json` y de `errores_prelabel.json`, así como las citas de menos de 50 palabras dentro de `respuesta_ia`. Se conservan al amparo del derecho de cita académico (art. 32 de la Ley de Propiedad Intelectual y disposiciones equivalentes en otros ordenamientos) con fines de investigación, análisis y verificación. **No quedan cubiertas por la licencia CC BY 4.0** y siguen perteneciendo a sus respectivos titulares de derechos. Quien reutilice este conjunto de datos debe tratar esas citas en consecuencia.

5. **El pipeline de ajuste fino QLoRA no se publica, y ese brazo no es reproducible.** El adaptador `neurofisio-qlora` se afinó sobre datos derivados del corpus con derechos de autor, de modo que ni sus pesos ni sus scripts de entrenamiento se liberan (`code/EXCLUDED.md` los enumera). La consecuencia se dice sin rodeos: **el brazo QLoRA de este estudio no puede reproducirlo un tercero.** Los otros tres modelos (`llama3.1:8b`, `qwen2.5:7b`, `thewindmom/llama3-med42-8b`) son públicos en Ollama y sí son reproducibles. Todo lo que viene después de la inferencia sigue siendo verificable para los cuatro, porque las salidas crudas de los cuatro están publicadas y `code/analysis/` recomputa las cifras a partir de ellas.

Los datos originales completos, sin redactar, obran en poder de los autores y están disponibles bajo petición razonada con fines de verificación.
