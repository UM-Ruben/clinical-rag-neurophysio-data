# Corrección reproducible del manuscrito (septiembre de 2026)

Esta carpeta acompaña la versión revisada de *The Benefits of RAG for Clinical AI Assistants Using Lightweight LLMs: Limitations and Trade-offs*. Conserva los ocho reports originales de P1 y los juicios ciegos publicados en las carpetas superiores; aplica una corrección de puntuación sin alterar esos datos primarios.

## Cambio de puntuación

En `results_ablation_p1/report_llama8b_GPU_Local_Win11_9doc_sysrole_con_RERUN.json`, pregunta 2, el parser guardó la opción `c` y `es_correcta=true` por una mención anterior. La respuesta final literal es «RESPUESTA: Ninguna de las anteriores». Como P1 exige elegir `a`, `b` o `c`, esa respuesta se puntúa como incorrecta. `audit_reports.py` comprueba la frase final antes de aplicar el cambio; si el dato primario cambiara, fallaría.

El resultado corregido para Llama-3.1-8B con RAG es **42/53 = 79,25 %**, diferencia pareada **+22,64 puntos**, IC **[+8,0; +37,2]**, McNemar exacto **p = 0,0075** y ajuste de Holm **p = 0,0302**. Hay **53 errores con RAG y 79 sin RAG** entre los cuatro modelos. El agregado **+12,26 puntos** es descriptivo porque las mismas 53 preguntas se repiten entre modelos.

La etiqueta del mismo caso se corrige al analizar los juicios de Qwen. El AUROC con RAG pasa a **0,7187** frente a **0,5772** sin RAG, diferencia **+0,1415**, IC bootstrap por pregunta **[-0,0142; +0,2876]**. Su sensibilidad binaria sobre errores con RAG es **28/37**. El resultado sigue siendo inconcluso. Los datos de `detectability_llama.json` no contienen ese autojuicio y sus cifras no cambian.

## Reproducción

Desde la raíz del repositorio, con las dependencias de `code/requirements.txt`:

```bash
python revision_2026_09/audit_reports.py
python revision_2026_09/analyze_detectability.py --juicios aggregates/detectability_qwen.json aggregates/detectability_llama.json
python revision_2026_09/plot_roc_corrected.py --out revision_2026_09/fig_roc_detectabilidad.pdf
```

Los comandos regeneran `audit_reports.json`, `detectability_resumen.json` y la figura ROC en esta carpeta. Los reports y juicios publicados no se modifican. `python code/reproduce.py` verifica la **versión histórica** del conjunto de datos y sus agregados originales; las dos auditorías anteriores verifican las cifras del manuscrito revisado.

## Alcance de los datos

- El 88,7 % llamado `recall@k` en archivos históricos es **47/53 aciertos de una heurística de solapamiento léxico** sobre los fragmentos finales. La función `compute_recall_hit` exige al menos dos términos normalizados compartidos y solapamiento ≥ 0,35 entre un fragmento y la pregunta concatenada con su opción correcta. No es recuperación de evidencia correcta verificada por expertos.
- Las 30 preguntas añadidas al banco tienen documento, página y cita literal en `datasets/dataset_gold_standard.json`; las 23 originales carecen de esos metadatos por ítem. Todas proceden del mismo material docente.
- `aggregates/taxonomia_*.json` y sus 131 etiquetas describen la **versión histórica** de P1. La respuesta corregida añade un error que no tiene etiqueta de taxonomía independiente. El manuscrito revisado no publica resultados de esa taxonomía; no se ha inventado una categoría para el caso nuevo.
- Ni esta revisión ni los datos históricos miden latencia completa de pregunta a respuesta, eficiencia energética, concurrencia, evaluación clínica independiente o respuestas libres. Tampoco aíslan la contribución del Cross-Encoder ni prueban la especialización QLoRA en una fuente ajena al entrenamiento.

El código de esta carpeta se distribuye bajo la licencia MIT del código del repositorio; los datos y textos de investigación conservan la licencia indicada en la raíz, con las exclusiones de material de terceros allí descritas.
