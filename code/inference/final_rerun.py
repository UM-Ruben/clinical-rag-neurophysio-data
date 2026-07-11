#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reejecucion ablativa n=53 con SYSTEM ROLE clinico anti-rechazo + prompts reformulados (P1).

Produce los 8 reports crudos de `results_ablation_p1/`, que son la entrada de `audit_reports.py`.

- Reutiliza los fragmentos recuperados guardados (retrieval identico entre brazos y modelos).
- con/sin RAG difieren SOLO en la presencia del contexto.
- T=0, num_ctx 8192, extractor corregido (el mismo que evaluate_rag.py).

===============================================================================================
AVISO. Este script NO es ejecutable por terceros y se publica solo para inspeccion.

Necesita:
  - un servidor Ollama local con los cuatro modelos cargados. Tres son publicos (llama3.1:8b,
    qwen2.5:7b, thewindmom/llama3-med42-8b); el cuarto, `neurofisio-qlora`, es un adaptador
    afinado sobre datos derivados del corpus con copyright y NO se distribuye.
  - los reports exploratorios de partida, que llevan los `fragmentos` recuperados verbatim del
    corpus y que por eso NO se publican.

En consecuencia, el brazo QLoRA no es reproducible fuera del equipo original. Lo que si es
verificable por cualquiera, sin corpus ni GPU, es que los 8 reports resultantes sostienen
exactamente las cifras publicadas: de eso se encarga `analysis/audit_reports.py`.
===============================================================================================
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
import urllib.request
from pathlib import Path

# Los cuatro modelos y el report exploratorio del que se reutilizan los fragmentos recuperados.
MODELS = [
    ("Llama-3.1-8B (general)", "llama3.1:8b",
     "report_llama3.1_8b_GPU_Local_Win11_9doc_llama8b_bge-m3_20260623_231909.json", "llama8b"),
    ("Llama-3.1-8B-QLoRA", "neurofisio-qlora",
     "report_neurofisio-qlora_GPU_Local_Win11_9doc_qlora_bge-m3_20260623_235311.json", "qlora"),
    ("Qwen-2.5-7B", "qwen2.5:7b",
     "report_qwen2.5_7b_GPU_Local_Win11_9doc_qwen7b_bge-m3_20260624_003033.json", "qwen7b"),
    ("Med42-8B", "thewindmom/llama3-med42-8b",
     "report_thewindmom_llama3-med42-8b_GPU_Local_Win11_9doc_med42_bge-m3_20260624_010701.json", "med42"),
]

SYSTEM = ("Eres un sistema de apoyo a la decisión clínica integrado en una herramienta profesional para "
          "fisioterapeutas y personal de rehabilitación neurológica. Resuelves preguntas de opción múltiple "
          "de validación clínica seleccionando la opción más correcta entre las ofrecidas y razonándola con "
          "rigor. Es una tarea profesional legítima; responde siempre eligiendo una de las opciones.")

STEPS = (
    "INSTRUCCIONES DE RAZONAMIENTO (sigue estos pasos en orden):\n\n"
    "PASO 1 - VERIFICAR CADA OPCIÓN PALABRA POR PALABRA:\n"
    "Para cada opción, compárala con la evidencia PALABRA POR PALABRA. Presta especial atención a:\n"
    "- Prefijos: ABductor ≠ ADuctor, ABducción ≠ ADucción (son movimientos OPUESTOS)\n"
    "- Nombres similares: tibial ANTERIOR ≠ tibial POSTERIOR, trapecio SUPERIOR ≠ INFERIOR\n"
    "- Lateralidad: DERECHO ≠ IZQUIERDO, IPSILATERAL (mismo lado) ≠ CONTRALATERAL (lado opuesto)\n"
    "- Fases temporales: músculo que PREPARA el movimiento ≠ músculo que EJECUTA el movimiento\n"
    "- Una sola palabra diferente puede hacer FALSA una opción que parece correcta\n\n"
    "PASO 2 - DESCARTAR OPCIONES CON ERRORES:\n"
    "Si una opción cambia UNA SOLA PALABRA respecto a la evidencia, esa opción es FALSA. Descártala.\n\n"
    "PASO 3 - OPCIONES 'A Y B SON CIERTAS':\n"
    "Si existe una opción tipo 'a y b son ciertas/correctas', verifica que AMBAS (a Y b) sean verdaderas. "
    "Si ambas lo son, la opción combinada es la correcta.\n\n"
    "PASO 4 - ELEGIR LA MÁS COMPLETA:\n"
    "Entre las opciones que NO tienen errores, elige la más completa y correcta.\n\n"
    "RESPUESTA FINAL (formato obligatorio):\nRESPUESTA: [una sola letra]\n\n"
    "Razona paso a paso:\n"
)
CON_TMPL = (
    "Como apoyo a la decisión clínica, resuelve la siguiente pregunta de opción múltiple de fisioterapia y "
    "rehabilitación neurológica apoyándote EXCLUSIVAMENTE en la información de contexto proporcionada. "
    "Debes elegir obligatoriamente una de las opciones ofrecidas.\n\n"
    "CONTEXTO:\n{context}\n\nPREGUNTA:\n{question}\n\n" + STEPS
)
SIN_TMPL = (
    "Como apoyo a la decisión clínica, resuelve la siguiente pregunta de opción múltiple de fisioterapia y "
    "rehabilitación neurológica apoyándote EXCLUSIVAMENTE en tu conocimiento clínico experto. "
    "Debes elegir obligatoriamente una de las opciones ofrecidas.\n\n"
    "PREGUNTA:\n{question}\n\n" + STEPS
)

# ---- extractor corregido (igual que evaluate_rag.py) ----
S = r'[\s:*\[\(\)"“”\'’.\-]{0,6}'; POS = {"primera": "a", "segunda": "b", "tercera": "c", "cuarta": "d"}
LM = [r'respuesta\s+final\s*(?:es)?'+S+r'([a-d])\b', r'respuesta'+S+r'([a-d])\b', r'answer'+S+r'([a-d])\b',
      r'la\s+respuesta\s+(?:final\s+)?es'+S+r'([a-d])\b', r'la\s+opci[oó]n\s+correcta\s+es'+S+r'([a-d])\b',
      r'la\s+respuesta\s+correcta\s+es'+S+r'([a-d])\b', r'(?:m[aá]s\s+)?correcta\s+y\s+completa\s+es'+S+r'([a-d])\b',
      r'opci[oó]n\s+([a-d])\)?[^.\n]{0,70}?\bes\s+la\s+(?:m[aá]s\s+\w+\s+|única\s+|)?(?:correcta|respuesta)',
      r'la\s+opci[oó]n\s+([a-d])\)?\s+es\s+la\s+(?:correcta|respuesta|m[aá]s)',
      r'the\s+(?:correct\s+)?answer\s+is'+S+r'([a-d])\b']
PM = [r'(?:respuesta|opci[oó]n)\s+(?:final\s+|correcta\s+|m[aá]s\s+\w+\s+)*(?:es\s+)?(?:la\s+)?(primera|segunda|tercera|cuarta)\b']
AYB = r'\b[ab]\s+y\s+[ab]\s+son\s+(?:ciertas|correctas|verdaderas)'
SAF = r'lo siento|no puedo proporcionar|no puedo ayudar|no puedo asistir'
REJ = (r'ninguna\s+(?:de\s+las\s+)?opci|no\s+est[aá]\s+entre\s+las\s+opciones|no\s+se\s+ajusta\s+a\s+ninguna|'
       r'no\s+hay\s+(?:una\s+)?opci[oó]n\s+correcta|none\s+of\s+the|respuesta'+S+r'\bn\b|no\s+puedo\s+proporcionar\s+una\s+respuesta')


def extract(resp):
    rl = resp.lower(); c = []
    for p in LM:
        for m in re.finditer(p, rl): c.append((m.start(), m.group(1)))
    for p in PM:
        for m in re.finditer(p, rl): c.append((m.start(), POS[m.group(1)]))
    for m in re.finditer(AYB, rl): c.append((m.start(), "c"))
    for p in (SAF, REJ):
        for m in re.finditer(p, rl): c.append((m.start(), None))
    if c:
        c.sort(key=lambda x: x[0]); return c[-1][1] or "desconocida"
    last = None
    for mm in re.finditer(r'\b([a-d])\)', rl[-160:]): last = mm
    if last: return last.group(1)
    m = re.search(r'^\s*\(?\[?([a-d])\s*[\)\.\]]', rl[:160], re.MULTILINE)
    return m.group(1) if m else "desconocida"


def fmt_q(item):
    s = item['pregunta'] + "\n\n"
    for k in sorted(item['opciones'].keys()):
        s += f"{k}) {item['opciones'][k]}\n"
    return s.strip()


def ollama(base_url, model, prompt):
    body = json.dumps({"model": model, "prompt": prompt, "system": SYSTEM, "stream": False,
                       "options": {"temperature": 0, "num_ctx": 8192}}).encode()
    for attempt in range(2):
        try:
            req = urllib.request.Request(f"{base_url}/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read())["response"]
        except Exception:
            if attempt == 1:
                raise
            time.sleep(3)


def ci(diffs):
    n = len(diffs); mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1) if n > 1 else 0.0
    se = math.sqrt(var / n)
    return f"[{mean*100-1.96*se*100:+.1f}, {mean*100+1.96*se*100:+.1f}]"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reports-dir", default="reports",
                    help="carpeta con los reports exploratorios de partida; alli se escriben los nuevos")
    ap.add_argument("--out-summary", default="rag_benefit_summary_sysrole.json")
    ap.add_argument("--progress", default=None, help="fichero de progreso (opcional)")
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    args = ap.parse_args()

    rd = Path(args.reports_dir)
    prog = Path(args.progress) if args.progress else None
    if prog:
        prog.parent.mkdir(parents=True, exist_ok=True)
        prog.write_text("", encoding="utf-8")

    def log(msg: str) -> None:
        print(msg, flush=True)
        if prog:
            with open(prog, "a", encoding="utf-8") as f:
                f.write(msg + "\n")

    summary = []
    for disp, oname, conrep, mtag in MODELS:
        src = json.load(open(rd / conrep, encoding="utf-8"))
        qs = src["questions"]
        arms = {}
        for arm in ("con", "sin"):
            rows = []; correct = 0; lat_sum = 0.0
            for q in qs:
                gold = q["respuesta_correcta"].strip().lower()
                if arm == "con":
                    ctx = "\n\n".join(q.get("fragmentos", []))
                    prompt = CON_TMPL.format(context=ctx, question=fmt_q(q))
                else:
                    prompt = SIN_TMPL.format(question=fmt_q(q))
                t0 = time.time(); resp = ollama(args.ollama_url, oname, prompt); lat = time.time() - t0
                lat_sum += lat
                det = extract(resp); ok = (det == gold); correct += 1 if ok else 0
                rows.append({"id": q["id"], "pregunta": q["pregunta"], "opciones": q["opciones"],
                             "respuesta_correcta": q["respuesta_correcta"], "respuesta_ia": resp,
                             "opcion_detectada": det, "es_correcta": ok, "latency_seconds": lat,
                             "num_fragmentos": q.get("num_fragmentos", 0) if arm == "con" else 0})
                log(f"{disp} [{arm}] Q{q['id']}: det={det} gold={gold} {'OK' if ok else 'x'} ({lat:.1f}s)")
            acc = correct / len(qs) * 100
            med = sorted(r["latency_seconds"] for r in rows)[len(rows) // 2]
            out = {"header": {"model": oname, "arm": arm, "system_role": True, "no_rag": (arm == "sin"),
                              "questions_count": len(qs), "context_max_tokens": 5000, "retrieved_top_k": 7,
                              "num_ctx": 8192, "temperature": 0, "completed": True,
                              "rerun": "sysrole_anti_refusal"},
                   "summary": {"total": len(qs), "correct": correct, "accuracy": acc,
                               "latency_mean": lat_sum / len(qs), "latency_median": med},
                   "questions": rows}
            fn = f"report_{mtag}_GPU_Local_Win11_9doc_sysrole_{arm}_RERUN.json"
            json.dump(out, open(rd / fn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            arms[arm] = (out, {r["id"]: r["es_correcta"] for r in rows})
            log(f"=== {disp} {arm}: acc={acc:.2f}% ({correct}/{len(qs)}) lat_med={med:.1f}s -> {fn}")

        cper = arms["con"][1]; sper = arms["sin"][1]
        common = sorted(set(cper) & set(sper))
        diffs = [(1 if cper[i] else 0) - (1 if sper[i] else 0) for i in common]
        accc = arms["con"][0]["summary"]["accuracy"]; accs = arms["sin"][0]["summary"]["accuracy"]
        summary.append({"model": oname, "n": len(qs), "acc_sin_rag": round(accs, 2),
                        "acc_con_rag": round(accc, 2), "delta_rag_pp": round(accc - accs, 2),
                        "paired_ci95": ci(diffs),
                        "lat_median_con": round(arms["con"][0]["summary"]["latency_median"], 2)})
        log(f"##### {disp}: sin={accs:.2f} con={accc:.2f} delta={accc-accs:+.1f} #####")

    json.dump(summary, open(args.out_summary, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    log("TODO COMPLETO.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
