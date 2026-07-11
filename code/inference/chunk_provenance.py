#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Traza cada fragmento recuperado (brazo con-RAG) hasta su PDF de origen.

Reconstruye los chunks con EXACTAMENTE los mismos parametros que uso el motor
(chunk_size=1500, chunk_overlap=400, trim_to_sentence_boundary) reutilizando las
funciones de evaluate_rag.py, y empareja por texto literal los `fragmentos`
guardados en los reports exploratorios (que son `doc.page_content` verbatim).

Sirve para dos cosas en el estudio de alucinaciones:
  - Subtag C-DIST: la respuesta con-RAG vio chunks de los distractores de ictus (07-09).
  - Subtag C-DILU: el documento fuente esperado de la pregunta no aparece entre los
    chunks recuperados (el fragmento relevante se diluyo y se recupero el vecino).

No usa GPU ni embeddings: solo carga, trocea y empareja texto.

Salida: chunk_provenance.json

===============================================================================================
AVISO. Este script NO es ejecutable por terceros y se publica solo para inspeccion.

Necesita el CORPUS de 9 PDF, que vuelve a trocear con los mismos parametros que el motor para emparejar
cada fragmento recuperado con su documento y pagina de origen. Produce `chunk_provenance.json`,
publicado en `aggregates/`. Sin el corpus no puede recomputarse.
===============================================================================================
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from evaluate_rag import load_documents, split_documents  # noqa: E402

DATA = ROOT / "data"
REPORTS = ROOT / "reports"
GOLD = ROOT / "dataset_gold_standard.json"
OUT = ROOT / "chunk_provenance.json"

# reports exploratorios con-RAG (los que llevan `fragmentos`), uno por modelo
EXPLORATORY_CON = {
    "llama3.1:8b": "report_llama3.1_8b_GPU_Local_Win11_9doc_llama8b_bge-m3_20260623_231909.json",
    "neurofisio-qlora": "report_neurofisio-qlora_GPU_Local_Win11_9doc_qlora_bge-m3_20260623_235311.json",
    "qwen2.5:7b": "report_qwen2.5_7b_GPU_Local_Win11_9doc_qwen7b_bge-m3_20260624_003033.json",
    "thewindmom/llama3-med42-8b": "report_thewindmom_llama3-med42-8b_GPU_Local_Win11_9doc_med42_bge-m3_20260624_010701.json",
}

DISTRACTORES = ("07_dist", "08_dist", "09_dist")


def main() -> int:
    print("Cargando y troceando los 9 PDFs (mismos parametros que el motor)...")
    documents = load_documents(DATA)
    chunks = split_documents(documents, chunk_size=1500, chunk_overlap=400)
    print(f"  {len(documents)} paginas -> {len(chunks)} chunks")

    # texto literal -> lista de (documento, pagina)
    index: dict[str, list[dict]] = defaultdict(list)
    for ch in chunks:
        src = Path(ch.metadata.get("source", "?")).name
        index[ch.page_content].append({"documento": src, "pagina": ch.metadata.get("page")})

    # 1) verificar que el retrieval fue identico entre modelos (no depende del LLM)
    frags_por_modelo = {}
    for model, fname in EXPLORATORY_CON.items():
        rep = json.load(open(REPORTS / fname, encoding="utf-8"))
        frags_por_modelo[model] = {q["id"]: q.get("fragmentos", []) for q in rep["questions"]}

    ref_model = "llama3.1:8b"
    ref = frags_por_modelo[ref_model]
    divergencias = []
    for model, frags in frags_por_modelo.items():
        if model == ref_model:
            continue
        for qid, fl in frags.items():
            if fl != ref.get(qid):
                divergencias.append((model, qid))
    if divergencias:
        print(f"  AVISO: retrieval NO identico en {len(divergencias)} casos: {divergencias[:5]}")
    else:
        print(f"  OK: los 4 modelos recuperaron exactamente los mismos fragmentos en las {len(ref)} preguntas")

    # 2) documento fuente esperado por pregunta (solo las 30 con metadatos)
    gold = {q["id"]: q for q in json.load(open(GOLD, encoding="utf-8"))}

    out = {
        "n_chunks_corpus": len(chunks),
        "retrieval_identico_entre_modelos": not divergencias,
        "divergencias": divergencias,
        "preguntas": {},
    }

    sin_emparejar = 0
    total_frag = 0
    for qid, frags in sorted(ref.items()):
        procedencias = []
        for fr in frags:
            total_frag += 1
            cands = index.get(fr)
            if not cands:
                sin_emparejar += 1
                procedencias.append({"documento": None, "pagina": None, "nota": "sin emparejar"})
            else:
                # si el texto aparece en varios chunks, se registran todos los origenes distintos
                docs = sorted({c["documento"] for c in cands})
                procedencias.append({
                    "documento": docs[0] if len(docs) == 1 else docs,
                    "pagina": cands[0]["pagina"],
                    "ambiguo": len(docs) > 1,
                })

        docs_vistos = []
        for p in procedencias:
            d = p["documento"]
            docs_vistos.extend(d if isinstance(d, list) else [d])
        docs_vistos = [d for d in docs_vistos if d]

        n_dist = sum(1 for d in docs_vistos if d.startswith(DISTRACTORES))
        esperado = (gold.get(qid) or {}).get("documento_fuente")
        # documento_fuente en el gold es un slug tipo "01_bobath_concepto"
        esperado_visto = None
        if esperado:
            esperado_visto = any(d.startswith(str(esperado)[:2]) for d in docs_vistos)

        out["preguntas"][str(qid)] = {
            "n_fragmentos": len(frags),
            "procedencias": procedencias,
            "documentos": sorted(set(docs_vistos)),
            "n_chunks_distractores": n_dist,
            "contaminado_por_distractor": n_dist > 0,
            "documento_fuente_esperado": esperado,
            "documento_fuente_recuperado": esperado_visto,
        }

    con_dist = sum(1 for v in out["preguntas"].values() if v["contaminado_por_distractor"])
    con_meta = [v for v in out["preguntas"].values() if v["documento_fuente_esperado"]]
    fallo_fuente = sum(1 for v in con_meta if v["documento_fuente_recuperado"] is False)

    out["resumen"] = {
        "fragmentos_totales": total_frag,
        "fragmentos_sin_emparejar": sin_emparejar,
        "preguntas_con_chunk_distractor": con_dist,
        "preguntas_totales": len(out["preguntas"]),
        "preguntas_con_metadato_fuente": len(con_meta),
        "preguntas_sin_recuperar_su_documento_fuente": fallo_fuente,
    }

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\n--- RESUMEN ---")
    for k, v in out["resumen"].items():
        print(f"  {k}: {v}")
    print(f"\nEscrito: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
