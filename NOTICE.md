# NOTICE — Scope of the licence / Alcance de la licencia

## English

The `LICENSE` file contains the full legal code of the **Creative Commons Attribution 4.0 International (CC BY 4.0)** licence. That licence applies to the **material created by the authors**: the three question banks (Gold Standard, TRAP, OOD), the model responses and per-question records, the aggregate results, the error taxonomy, the detectability panel, the annotation files and all documentation in this repository.

The licence does **not** extend to third-party material. Specifically:

1. **The source corpus is not distributed here.** The retrieval corpus consists of copyrighted teaching material on neurophysiotherapy plus three open-access clinical practice guidelines on stroke. Neither the PDFs nor their extracted text are included in this repository.

2. **Retrieved context is published as hashes, not text.** In the P2 reports, the `fragmentos` field (the context passages retrieved by the RAG system) was replaced with SHA-256 hashes together with the character count and, where derivable, the source document and page. This lets anyone who holds a licensed copy of the corpus verify exactly which passage was retrieved, without redistributing the text itself.

3. **Long verbatim quotations were redacted, in every free-text field.** Because the models were instructed to ground their answers in the retrieved evidence, some responses reproduce the corpus literally; the hand-built evidence fields quote it by construction. Every free-text field of every published file was audited against the nine complete source documents, and passages reproducing **50 or more consecutive words** of the source corpus were replaced with the marker `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`. This affects **29 spans in 8 files**: 18 in `respuesta_ia`, 7 in `cita_soporte` (`aggregates/taxonomia_errores.json`) and 4 in `traza_cita` (`datasets/dataset_gold_standard.json`). Shorter quotations are retained. Where a redacted field served as evidence, its provenance (document and page) is preserved so the field remains auditable.

4. **Short quotations retained under the right of quotation.** Some fields deliberately preserve short literal quotations from the source corpus (**fewer than 50 consecutive words**), always attributed with document and page: the `traza_cita` field in the TRAP bank (audited, no redaction required) and in the gold-standard bank, the `cita_soporte` field in `taxonomia_errores.json`, as well as the sub-50-word quotations inside `respuesta_ia`. These are retained under the academic right of quotation (Art. 32 of the Spanish Intellectual Property Act and equivalent provisions elsewhere) for the purposes of research, analysis and verification. **They are not covered by the CC BY 4.0 licence** and remain the property of their respective rights holders. Anyone reusing this dataset should treat those quotations accordingly.

The complete, unredacted data is held by the authors and is available on reasoned request for verification purposes.

---

## Español

El fichero `LICENSE` contiene el texto legal completo de la licencia **Creative Commons Atribución 4.0 Internacional (CC BY 4.0)**. Esa licencia se aplica al **material de creación propia de los autores**: los tres bancos de preguntas (Gold Standard, TRAP, OOD), las respuestas de los modelos y los registros por pregunta, los resultados agregados, la taxonomía de errores, el panel de detectabilidad, los ficheros de anotación y toda la documentación de este repositorio.

La licencia **no** se extiende al material de terceros. En concreto:

1. **El corpus fuente no se distribuye aquí.** El corpus de recuperación está formado por material docente de neurofisioterapia con derechos de autor y tres guías de práctica clínica del ictus de acceso abierto. Ni los PDF ni su texto extraído se incluyen en este repositorio.

2. **El contexto recuperado se publica como hashes, no como texto.** En los reports de P2, el campo `fragmentos` (los pasajes de contexto recuperados por el sistema RAG) se sustituyó por hashes SHA-256 junto con el número de caracteres y, cuando es derivable, el documento y la página de origen. Esto permite a quien disponga de una copia legítima del corpus verificar exactamente qué pasaje se recuperó, sin redistribuir el texto.

3. **Se redactaron las citas literales largas, en todos los campos de texto libre.** Dado que se instruyó a los modelos para que anclaran su respuesta en la evidencia recuperada, algunas respuestas reproducen el corpus literalmente; los campos de evidencia construidos a mano lo citan por construcción. Se auditaron todos los campos de texto libre de todos los ficheros publicados contra los nueve documentos fuente completos, y los pasajes que reproducían **50 o más palabras consecutivas** del corpus fuente se sustituyeron por el marcador `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`. Afecta a **29 tramos en 8 ficheros**: 18 en `respuesta_ia`, 7 en `cita_soporte` (`aggregates/taxonomia_errores.json`) y 4 en `traza_cita` (`datasets/dataset_gold_standard.json`). Las citas más breves se conservan. Cuando el campo redactado cumplía una función probatoria, se conserva su procedencia (documento y página) para que siga siendo auditable.

4. **Citas breves conservadas al amparo del derecho de cita.** Algunos campos conservan deliberadamente citas literales breves del corpus fuente (**de menos de 50 palabras consecutivas**), siempre atribuidas con documento y página: el campo `traza_cita` del banco TRAP (auditado, sin necesidad de redacción) y del banco gold standard, el campo `cita_soporte` de `taxonomia_errores.json`, así como las citas de menos de 50 palabras dentro de `respuesta_ia`. Se conservan al amparo del derecho de cita académico (art. 32 de la Ley de Propiedad Intelectual y disposiciones equivalentes en otros ordenamientos) con fines de investigación, análisis y verificación. **No quedan cubiertas por la licencia CC BY 4.0** y siguen perteneciendo a sus respectivos titulares de derechos. Quien reutilice este conjunto de datos debe tratar esas citas en consecuencia.

Los datos originales completos, sin redactar, obran en poder de los autores y están disponibles bajo petición razonada con fines de verificación.
