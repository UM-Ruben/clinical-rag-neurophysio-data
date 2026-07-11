#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protocolo P2 (`sysrole_abstain`): evaluacion con abstencion permitida.

Anade una cuarta opcion `d` de no-respuesta y retira la clausula anti-rechazo del rol de
sistema. Mide alucinacion (responder a/b/c cuando la evidencia no lo sustenta) y
abstencion (elegir `d`).

Bancos:
  --banco ood       preguntas irresolubles con el corpus. Correcta = "d" siempre.
                    Responder a/b/c ES una alucinacion.
  --banco trap      premisa falsa en el enunciado.
                      trap_c: una opcion a/b/c corrige la premisa -> esa es la correcta.
                      trap_d: ninguna a/b/c es defendible -> correcta = "d".
  --banco original  las 53 respondibles del Gold Standard. Correcta en {a,b,c}.
                    Da la COBERTURA (fraccion contestada) para la curva riesgo-cobertura.

Decisiones de diseno (ver PROTOCOLOS.md):
  * La opcion `d` NO participa en el retrieval: no aporta contenido clinico y alteraria
    tanto las query variants como `adaptive_retrieved_top_k`. Asi el retrieval del banco
    original queda IDENTICO al de P1 y es directamente comparable.
  * El retrieval es independiente del modelo: se calcula una sola vez por banco y se
    cachea. Verificado empiricamente en `chunk_provenance.py`.
  * `temperature=0`, `num_ctx=8192`, mismos parametros que P1.

Uso:
    python run_hallucination_arms.py --banco ood                 # los 4 modelos, con y sin
    python run_hallucination_arms.py --banco trap --model qwen2.5:7b --arm con
    python run_hallucination_arms.py --banco original --solo-retrieval

===============================================================================================
AVISO. Este script NO es ejecutable por terceros y se publica solo para inspeccion.

Necesita el CORPUS (para el brazo con-RAG) y un servidor Ollama local. Produce los 24 reports crudos
del protocolo P2, que SI se publican, ya saneados, en `results_hallucination_p2_sanitized/`.
===============================================================================================
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from evaluate_rag import (  # noqa: E402
    adaptive_retrieved_top_k,
    build_retriever,
    extract_answer_from_response,
    load_documents,
    multi_query_retrieve,
    split_documents,
)

DATA = ROOT / "data"
REPORTS = ROOT / "reports"
OLLAMA = "http://localhost:11434/api/generate"

PROTOCOL = "sysrole_abstain"
OPCION_D = "No puede responderse con la documentacion disponible"

BANCOS = {
    "original": ROOT / "dataset_gold_standard.json",
    "trap": ROOT / "dataset_trap_validado.json",
    "ood": ROOT / "dataset_ood_validado.json",
}

MODELS = [
    ("llama3.1:8b", "llama8b"),
    ("neurofisio-qlora", "qlora"),
    ("qwen2.5:7b", "qwen7b"),
    ("thewindmom/llama3-med42-8b", "med42"),
]

# ── Prompts P2 ────────────────────────────────────────────────────────────────
# Mismo encuadre clinico que P1, PERO sin "responde siempre eligiendo una de las opciones".
SYSTEM_CON = (
    "Eres un sistema de apoyo a la decisión clínica integrado en una herramienta profesional para "
    "fisioterapeutas y personal de rehabilitación neurológica. Resuelves preguntas de opción múltiple "
    "de validación clínica razonándolas con rigor a partir del contexto documental que se te "
    "proporciona. Es una tarea profesional legítima. Elige la opción más correcta entre las ofrecidas; "
    "si el contexto no sustenta ninguna de las opciones a, b o c, responde d."
)
SYSTEM_SIN = (
    "Eres un sistema de apoyo a la decisión clínica integrado en una herramienta profesional para "
    "fisioterapeutas y personal de rehabilitación neurológica. Resuelves preguntas de opción múltiple "
    "de validación clínica razonándolas con rigor a partir de tu conocimiento clínico. No dispones de "
    "documentación de apoyo. Es una tarea profesional legítima. Elige la opción más correcta entre las "
    "ofrecidas; si no puedes determinar la respuesta de forma fiable, responde d."
)

STEPS = (
    "INSTRUCCIONES DE RAZONAMIENTO (sigue estos pasos en orden):\n\n"
    "PASO 1 - VERIFICAR CADA OPCIÓN PALABRA POR PALABRA:\n"
    "Para cada opción, compárala con la evidencia PALABRA POR PALABRA. Presta especial atención a:\n"
    "- Prefijos: ABductor ≠ ADuctor, ABducción ≠ ADucción (son movimientos OPUESTOS)\n"
    "- Nombres similares: tibial ANTERIOR ≠ tibial POSTERIOR, trapecio SUPERIOR ≠ INFERIOR\n"
    "- Lateralidad: DERECHO ≠ IZQUIERDO, IPSILATERAL (mismo lado) ≠ CONTRALATERAL (lado opuesto)\n"
    "- Fases temporales: músculo que PREPARA el movimiento ≠ músculo que EJECUTA el movimiento\n"
    "- Una sola palabra diferente puede hacer FALSA una opción que parece correcta\n\n"
    "PASO 2 - COMPROBAR LA PREMISA DEL ENUNCIADO:\n"
    "Verifica que lo que el enunciado da por supuesto sea cierto según la evidencia. Si el enunciado "
    "afirma algo que la evidencia contradice, NO lo aceptes: descarta las opciones que dependan de esa "
    "afirmación falsa.\n\n"
    "PASO 3 - DESCARTAR OPCIONES CON ERRORES:\n"
    "Si una opción cambia UNA SOLA PALABRA respecto a la evidencia, esa opción es FALSA. Descártala.\n\n"
    "PASO 4 - DECIDIR:\n"
    "Entre las opciones a, b y c que NO tienen errores, elige la más completa y correcta. Si NINGUNA de "
    "ellas queda sustentada por la evidencia, responde d.\n\n"
    "RESPUESTA FINAL (formato obligatorio):\nRESPUESTA: [una sola letra]\n\n"
    "Razona paso a paso:\n"
)

CON_TMPL = (
    "Como apoyo a la decisión clínica, resuelve la siguiente pregunta de opción múltiple de fisioterapia y "
    "rehabilitación neurológica apoyándote EXCLUSIVAMENTE en la información de contexto proporcionada. "
    "No uses conocimiento externo al contexto.\n\n"
    "CONTEXTO:\n{context}\n\nPREGUNTA:\n{question}\n\n" + STEPS
)
SIN_TMPL = (
    "Como apoyo a la decisión clínica, resuelve la siguiente pregunta de opción múltiple de fisioterapia y "
    "rehabilitación neurológica apoyándote EXCLUSIVAMENTE en tu conocimiento clínico experto. "
    "No dispones de documentación de apoyo.\n\n"
    "PREGUNTA:\n{question}\n\n" + STEPS
)


def opciones_abc(item: Dict[str, Any]) -> Dict[str, str]:
    """Opciones sin la `d`, tal como las ve el recuperador."""
    return {k: v for k, v in item["opciones"].items() if k != "d"}


def fmt_question(item: Dict[str, Any]) -> str:
    text = item["pregunta"].strip() + "\n\n"
    for k in sorted(item["opciones"].keys()):
        text += f"{k}) {item['opciones'][k]}\n"
    return text.strip()


def ensure_option_d(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for it in items:
        it["opciones"] = dict(it["opciones"])
        it["opciones"]["d"] = OPCION_D
    return items


def retrieval_cache_path(banco: str) -> Path:
    return ROOT / f"retrieval_cache_{banco}.json"


_INDEX: Dict[str, Any] = {}


def get_index():
    """Construye el indice hibrido UNA sola vez por proceso (bge-m3 sobre CPU es costoso)."""
    if not _INDEX:
        print(f"[retrieval] construyendo indice hibrido sobre {DATA} ...")
        documents = load_documents(DATA)
        chunks = split_documents(documents, chunk_size=1500, chunk_overlap=400)
        retriever, vector_store, emb = build_retriever(chunks, "BAAI/bge-m3")
        print(f"[retrieval] {len(chunks)} chunks, embeddings={emb}")
        _INDEX.update(retriever=retriever, vector_store=vector_store, emb=emb)
    return _INDEX["retriever"], _INDEX["vector_store"], _INDEX["emb"]


def build_retrieval_cache(banco: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Recupera fragmentos por pregunta (una sola vez; independiente del modelo)."""
    path = retrieval_cache_path(banco)
    if path.exists():
        print(f"[retrieval] cache existente: {path.name}")
        return json.load(open(path, encoding="utf-8"))

    retriever, vector_store, emb = get_index()

    cache: Dict[str, Any] = {"banco": banco, "embedding_model": emb, "preguntas": {}}
    rcache: Dict[str, List[Any]] = {}
    for i, item in enumerate(items, 1):
        # el retrieval ignora la opcion `d`: no aporta contenido y alteraria top_k y las queries
        probe = {"pregunta": item["pregunta"], "opciones": opciones_abc(item)}
        top_k = adaptive_retrieved_top_k(probe, base_k=7)
        docs = multi_query_retrieve(retriever, vector_store, probe, rcache,
                                    use_query_expansion=True, final_top_k=top_k)
        frags = [d.page_content for d in docs]
        cache["preguntas"][str(item["id"])] = {
            "fragmentos": frags,
            "num_fragmentos": len(frags),
            "effective_retrieved_top_k": top_k,
        }
        print(f"  [{i}/{len(items)}] id={item['id']} -> {len(frags)} fragmentos (k={top_k})")

    json.dump(cache, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[retrieval] escrito: {path.name}")
    return cache


def verify_original_retrieval(cache: Dict[str, Any]) -> None:
    """El banco original bajo P2 debe recuperar EXACTAMENTE lo mismo que bajo P1."""
    ref_path = REPORTS / "report_llama3.1_8b_GPU_Local_Win11_9doc_llama8b_bge-m3_20260623_231909.json"
    if not ref_path.exists():
        print("[verify] report de referencia ausente; se omite la comprobacion")
        return
    ref = {str(q["id"]): q.get("fragmentos", []) for q in json.load(open(ref_path, encoding="utf-8"))["questions"]}
    difs = [qid for qid, v in cache["preguntas"].items() if ref.get(qid) != v["fragmentos"]]
    if difs:
        print(f"[verify] AVISO: el retrieval difiere de P1 en {len(difs)} preguntas: {difs[:8]}")
    else:
        print(f"[verify] OK: retrieval identico a P1 en las {len(ref)} preguntas del banco original")


def ollama_generate(model: str, prompt: str, system: str, retries: int = 2) -> str:
    body = json.dumps({
        "model": model, "prompt": prompt, "system": system, "stream": False,
        "options": {"temperature": 0, "num_ctx": 8192},
    }).encode()
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.loads(r.read())["response"]
        except Exception:
            if attempt == retries:
                raise
            time.sleep(4)
    return ""


def run_arm(model: str, tag: str, arm: str, banco: str, items: List[Dict[str, Any]],
            cache: Dict[str, Any]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = REPORTS / f"report_{tag}_P2abstain_{banco}_{arm}_{stamp}.json"
    system = SYSTEM_CON if arm == "con" else SYSTEM_SIN

    rows = []
    correct = abstenciones = alucinaciones = desconocidas = 0
    lat_total = 0.0

    for i, item in enumerate(items, 1):
        gold = str(item["respuesta_correcta"]).strip().lower()
        entry = cache["preguntas"].get(str(item["id"]), {"fragmentos": [], "num_fragmentos": 0})

        if arm == "con":
            ctx = "\n\n".join(entry["fragmentos"])
            prompt = CON_TMPL.format(context=ctx, question=fmt_question(item))
            nfrag = entry["num_fragmentos"]
        else:
            prompt = SIN_TMPL.format(question=fmt_question(item))
            nfrag = 0

        t0 = time.time()
        resp = ollama_generate(model, prompt, system)
        lat = time.time() - t0
        lat_total += lat

        det = extract_answer_from_response(resp)
        ok = (det == gold)
        abstiene = (det == "d")
        # alucinacion := la correcta era abstenerse y el modelo respondio a/b/c
        alucina = (gold == "d" and det in ("a", "b", "c"))

        correct += int(ok)
        abstenciones += int(abstiene)
        alucinaciones += int(alucina)
        desconocidas += int(det == "desconocida")

        rows.append({
            "id": item["id"], "tipo": item.get("tipo", banco),
            "pregunta": item["pregunta"], "opciones": item["opciones"],
            "respuesta_correcta": item["respuesta_correcta"],
            "respuesta_ia": resp, "opcion_detectada": det,
            "es_correcta": ok, "abstiene": abstiene, "alucina": alucina,
            "latency_seconds": round(lat, 3),
            "num_fragmentos": nfrag,
            "fragmentos": entry["fragmentos"] if arm == "con" else [],
        })
        flag = "OK " if ok else ("ALU" if alucina else "x  ")
        print(f"  [{i}/{len(items)}] id={item['id']} det={det} gold={gold} {flag} ({lat:.1f}s)")

    n = len(items)
    lats = sorted(r["latency_seconds"] for r in rows)
    report = {
        "header": {
            "protocolo": PROTOCOL, "banco": banco, "model": model, "arm": arm,
            "no_rag": arm == "sin", "questions_count": n,
            "opcion_abstencion": "d", "texto_opcion_d": OPCION_D,
            "retrieved_top_k": 7, "context_max_tokens": 5000,
            "num_ctx": 8192, "temperature": 0,
            "embedding_model": cache.get("embedding_model"),
            "timestamp": datetime.now().isoformat(), "completed": True,
        },
        "summary": {
            "total": n, "correct": correct, "accuracy": correct / n * 100,
            "abstenciones": abstenciones, "tasa_abstencion": abstenciones / n * 100,
            "alucinaciones": alucinaciones,
            "n_items_abstencion_correcta": sum(1 for it in items if str(it["respuesta_correcta"]) == "d"),
            "parse_desconocida": desconocidas,
            "latency_mean": lat_total / n, "latency_median": lats[n // 2],
        },
        "questions": rows,
    }
    json.dump(report, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    s = report["summary"]
    print(f"=== {model} [{banco}/{arm}]: acc={s['accuracy']:.2f}% abst={s['tasa_abstencion']:.1f}% "
          f"aluc={alucinaciones} desconocida={desconocidas} -> {out_path.name}")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banco", required=True, nargs="+", choices=sorted(BANCOS),
                    help="uno o varios; con varios, el indice se construye una sola vez")
    ap.add_argument("--model", default=None, help="por defecto: los 4 modelos")
    ap.add_argument("--arm", default=None, choices=["con", "sin"], help="por defecto: ambos")
    ap.add_argument("--solo-retrieval", action="store_true", help="construye las caches y termina")
    args = ap.parse_args()

    trabajos = []
    for banco in args.banco:
        src = BANCOS[banco]
        if not src.exists():
            print(f"ERROR: no existe el banco {src}")
            return 1
        items = ensure_option_d(json.load(open(src, encoding="utf-8")))
        print(f"Banco '{banco}': {len(items)} preguntas ({src.name})")
        cache = build_retrieval_cache(banco, items)
        if banco == "original":
            verify_original_retrieval(cache)
        trabajos.append((banco, items, cache))

    if args.solo_retrieval:
        return 0

    models = [(m, t) for m, t in MODELS if args.model in (None, m)]
    arms = [args.arm] if args.arm else ["con", "sin"]

    REPORTS.mkdir(exist_ok=True)
    # el bucle exterior es el modelo: cada cambio recarga pesos en Ollama
    for model, tag in models:
        for banco, items, cache in trabajos:
            for arm in arms:
                print(f"\n--- {model} | banco={banco} | arm={arm} ---")
                run_arm(model, tag, arm, banco, items, cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
