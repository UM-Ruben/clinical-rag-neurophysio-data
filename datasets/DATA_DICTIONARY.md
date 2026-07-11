# Data dictionary — `datasets/`

The three question banks used in the study. All are UTF-8 JSON files containing a **flat list of question objects**. Field names are in Spanish; they are documented here in English.

| File | Items | Options | Gold answer |
|---|---|---|---|
| `dataset_gold_standard.json` | 53 | `a`, `b`, `c` | one of `a`/`b`/`c` (distribution: 22 `a`, 20 `b`, 11 `c`) |
| `dataset_trap_validado.json` | 24 | `a`, `b`, `c`, `d` | 11 items `d`, 13 items one of `a`/`b`/`c` |
| `dataset_ood_validado.json` | 18 | `a`, `b`, `c`, `d` | always `d` |

---

## The two protocols, and why their accuracies must not be compared

The same gold-standard bank is used under two different evaluation protocols. **This changes what an "accuracy" means, and the two are not comparable with each other.**

**Protocol P1 — `sysrole_anti_rechazo` (ablation study).**
The system role frames the task as a legitimate professional clinical exercise and ends with an **anti-refusal clause**: the model must always choose one of the options. Three options are offered (`a`, `b`, `c`) and **abstention is forbidden by design**. Only the gold-standard bank is used. This is the protocol of `results_ablation_p1/`.

**Protocol P2 — `sysrole_abstain` (hallucination study).**
The system role keeps the same clinical framing but **drops the anti-refusal clause**, and instructs the model to select the non-answer option when the evidence supports none of the alternatives. A **fourth option is added**:

```
d) No puede responderse con la documentación disponible
```

Abstention is therefore a legitimate, first-class answer. All three banks are used. This is the protocol of `results_hallucination_p2_sanitized/`.

> ### Warning: accuracies from P1 and P2 are NOT comparable
>
> 1. **The number of options changes** (3 vs 4), so the chance baseline moves from 1/3 to 1/4.
> 2. **The success criterion changes.** In P1 abstention is impossible. In P2 abstention is the *correct* answer for all 18 OOD items and for 11 of the 24 TRAP items; conversely, answering `a`/`b`/`c` on an OOD item is by definition a hallucination.
> 3. **The system role differs** precisely in the anti-refusal clause, which is itself one of the variables under study.
>
> Any comparison across protocols must be made on **hallucination and abstention rates**, never on raw accuracy.

---

## `dataset_gold_standard.json` — 53 answerable questions

The reference bank of answerable multiple-choice questions on neurophysiotherapy. Every item is answerable from the teaching corpus.

**Fields present in all 53 items:**

| Field | Type | Description |
|---|---|---|
| `id` | integer | Item identifier, 1–53. This is the key that joins the item to `questions[].id` in the raw reports and to `id` in the aggregate files. |
| `pregunta` | string | The question stem, in Spanish. |
| `opciones` | object | The answer options, as a map from the option letter to its text. Exactly three keys: `a`, `b`, `c`. |
| `respuesta_correcta` | string | The gold answer: the letter (`a`, `b` or `c`) of the correct option. |
| `gold_standard_id` | integer | Item index within this bank (1–53); coincides with `id`. |
| `original_id` | integer | Item index in the original question pool from which the bank was drawn (1–53). |

**Fields present in 30 of the 53 items** (those for which the source passage in the corpus was traced; the remaining 23 items carry no source metadata):

| Field | Type | Description |
|---|---|---|
| `fuente` | string | Provenance tag of the item, e.g. `generada_v2_2026-06-23`. Records how and when the item was generated. |
| `documento_fuente` | string | Identifier of the corpus document that supports the gold answer, e.g. `01_bobath_concepto`. The six source documents are `01`–`06`; documents `07`–`09` are the open-access stroke guidelines used as distractors and are never the source of a gold answer. |
| `traza_pagina` | integer | Page of `documento_fuente` on which the supporting passage appears. |
| `traza_cita` | string | **Verbatim quotation from the third-party corpus**, or a redaction marker. The sentence that supports the gold answer, always attributed via `documento_fuente` + `traza_pagina`. Short quotations (< 50 consecutive words) are retained under the academic right of quotation. **4 of the 30 items that carry a quotation** (ids 35, 38, 46, 50; array indices 34, 37, 45, 49) reproduced **≥ 50 consecutive words** of the corpus and their `traza_cita` has therefore been replaced in full by the literal marker `[CITA REDACTADA: N palabras del corpus fuente, retiradas por derechos de autor]`, where *N* is the number of words removed (56, 52, 66 and 57 respectively). The evidential function is preserved by the sibling fields `documento_fuente` and `traza_pagina`, which still point to the exact document and page: a reader holding a licensed copy of the corpus can locate the passage and verify the item. See caveat (d) of `VERIFICATION.md` for the audit method. **Not covered by the repository's CC BY 4.0 licence** — see the licence scope note in the root `README.md`. |
| `dificultad` | string | Difficulty label assigned at validation: `media` or `alta`. |

---

## `dataset_trap_validado.json` — 24 false-premise questions

The TRAP bank. Each stem **embeds a false premise**: it asserts, as if it were established, something that the corpus contradicts. The purpose is to test whether the model accepts a premise handed to it by the user. Only used under Protocol P2.

Of the 24 items, **13 remain answerable despite the false premise** (`tipo = trap_c`: the corpus does support one of `a`/`b`/`c`, and accepting the false premise leads elsewhere), and **11 are not answerable at all** (`tipo = trap_d`: the gold answer is `d`).

| Field | Type | Description |
|---|---|---|
| `id` | integer | Item identifier, 1001–1024. Kept in a distinct numeric range so that TRAP items never collide with gold-standard (`1`–`53`) or OOD (`2001`–`2018`) identifiers. |
| `banco` | string | Always `trap`. Bank tag. |
| `tipo` | string | `trap_c` (13 items — a lettered option is correct) or `trap_d` (11 items — the correct answer is to abstain). This is the value that appears in the `tipo` field of the P2 raw records. |
| `pregunta` | string | The question stem, **containing the false premise**. |
| `opciones` | object | Map from option letter to option text. Four keys: `a`, `b`, `c`, `d`, where `d` is the abstention option. |
| `respuesta_correcta` | string | The gold answer. Distribution across the bank: `d` 11, `b` 6, `c` 4, `a` 3. |
| `opcion_que_acepta_la_premisa` | string | The letter of the **trap option**: the option that is only correct if one accepts the false premise. A model choosing this letter has been captured by the premise. This field is what makes the *sycophancy* metric (`complacencia_trap_c` in `aggregates/hallucination_summary.json`) computable. |
| `premisa_falsa` | string | Prose statement of exactly which assertion in the stem is false, and what the corpus says instead. |
| `justificacion` | string | Prose justification of why `respuesta_correcta` is the gold answer, written at item-validation time. |
| `traza_cita` | string | **Short verbatim quotation from the third-party corpus**: the sentence that the false premise contradicts. Present in all 24 items. Retained under the academic right of quotation, always attributed via `documento_fuente` + `traza_pagina`. This field was audited against the nine complete source documents and **no redaction was required**: the longest verbatim overlap in this file is 49 consecutive words, below the 50-word redaction threshold, so **no `[CITA REDACTADA: ...]` marker appears in this file**. See caveat (d) of `VERIFICATION.md`. **Not covered by the repository's CC BY 4.0 licence.** |
| `traza_pagina` | integer | Page of `documento_fuente` on which that sentence appears. |
| `documento_fuente` | string | Corpus document that the false premise contradicts. The bank is balanced: 4 items per source document across the six documents `01`–`06`. |
| `dificultad` | string | `media` (10 items) or `alta` (14 items). |
| `_permutacion` | object | Bookkeeping of the option shuffle applied at construction: a map from the **final** letter to the letter the option had before shuffling. Recorded so that the shuffle is auditable. Leading underscore marks it as internal metadata, not experimental data. |

---

## `dataset_ood_validado.json` — 18 unanswerable questions

The out-of-distribution bank. Every item asks for a fact that **is not in the corpus at all** (a drug dose, a trial figure, a scale cut-off). The corpus may discuss the topic, but never supplies the specific quantity asked for. **The gold answer is `d` for all 18 items**: answering `a`, `b` or `c` is by definition a hallucination — it is the dangerous cell of the risk matrix. Only used under Protocol P2.

| Field | Type | Description |
|---|---|---|
| `id` | integer | Item identifier, 2001–2018. |
| `banco` | string | Always `ood`. |
| `tipo` | string | Always `ood`. This is the value that appears in the `tipo` field of the P2 raw records. |
| `tematica` | string | The kind of absent fact the item asks for. Three balanced themes, 6 items each: `posologia_farmacologia` (drug dosing), `epidemiologia_cifras_ensayos` (epidemiological and trial figures), `escalas_puntos_de_corte` (clinical-scale cut-off points). |
| `pregunta` | string | The question stem. Clinically plausible, and unanswerable from the corpus. |
| `opciones` | object | Map from option letter to option text. Four keys: `a`, `b`, `c`, `d`. Options `a`–`c` are plausible-looking values; `d` is the abstention option. |
| `respuesta_correcta` | string | Always `d`. |
| `terminos_clave_ausentes` | array of strings | The key terms whose **absence from the corpus** was verified at validation time, and which make the item unanswerable (e.g. `["onabotulinumtoxinA", "gastrocnemio medial", "unidades por músculo"]`). This is the evidence for the item's unanswerability. |
| `justificacion` | string | Prose justification of the unanswerability, stating what the corpus does say about the topic and what it does not. |
| `dificultad` | string | Difficulty label assigned at validation. |

Note that the OOD bank carries **no `traza_cita`**: there is no supporting passage to quote, because the point of the bank is that no such passage exists.

---

## Text of the abstention option

Across the TRAP and OOD banks the text of option `d` is stored without the accent, as it was presented to the models:

```
No puede responderse con la documentacion disponible
```

The same string appears in the `texto_opcion_d` field of the header of every P2 raw report. It is reproduced here as it was actually rendered in the prompt, so that the exact input to the models can be reconstructed.
