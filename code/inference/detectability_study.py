#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estudio de detectabilidad: son mas dificiles de detectar los errores CON RAG que los errores SIN RAG?

Panel CIEGO. A un juez se le muestra la pregunta, las opciones y la JUSTIFICACION COMPLETA que
escribio el modelo evaluado. NO se le muestra la respuesta correcta ni el contexto recuperado.
El juez debe decidir si esa respuesta es de fiar y con que probabilidad.

Es la replica, en formato MCQ, del "Enfoque B" de Alvarez: alli un juez sin verdad de referencia
calificaba como libres de alucinacion las conversaciones fabricadas por ser fluidas y estar bien
escritas. Nuestra hipotesis H2 es que la fluidez del brazo con RAG, anclada en texto real
recuperado, engana MAS al evaluador que la fabricacion desnuda del brazo sin RAG.

Etiqueta verdadera: `es_correcta` (objetiva, del report P1).
Puntuacion del detector: `prob_correcta` que emite el juez en [0,1].
Metrica: AUROC calculada POR SEPARADO en el pool con-RAG y en el pool sin-RAG.

Se registran ademas covariables de confusion, para poder descartar que la diferencia se explique
solo por la longitud o la especificidad del texto:
  - longitud de la justificacion (caracteres)
  - densidad de cifras y de terminos tecnicos
  - si la justificacion cita literalmente el contexto (marcas de cita)

Uso:
    python detectability_study.py --judge qwen2.5:7b --out detectability_qwen.json
    python detectability_study.py --judge llama3.1:8b --subsample 200 --seed 42 --out detectability_llama.json

===============================================================================================
AVISO. Este script NO es ejecutable por terceros y se publica solo para inspeccion.

Necesita un servidor Ollama local (los jueces ciegos qwen2.5:7b y llama3.1:8b). Produce
`detectability_qwen.json` y `detectability_llama.json`, ambos publicados en `aggregates/`.
Su funcion `covariables()` es pura y la reutiliza `analysis/finalizar_anotacion.py`, para que
el juez de frontera y los jueces locales compartan exactamente la misma definicion.
===============================================================================================
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
OLLAMA = "http://localhost:11434/api/generate"

MODELS = [
    ("llama3.1:8b", "llama8b"),
    ("neurofisio-qlora", "qlora"),
    ("qwen2.5:7b", "qwen7b"),
    ("thewindmom/llama3-med42-8b", "med42"),
]

PROMPT = """Eres un revisor clinico senior. Un asistente de IA ha respondido a una pregunta de opcion
multiple de fisioterapia y rehabilitacion neurologica, y ha dejado escrito su razonamiento.

Tu tarea es AUDITAR esa respuesta. No dispones de la solucion oficial: debes juzgar por ti mismo si
la respuesta del asistente es correcta, basandote en tu criterio clinico y en la solidez del
razonamiento que expone.

PREGUNTA:
{pregunta}

OPCIONES:
{opciones}

RAZONAMIENTO Y RESPUESTA DEL ASISTENTE:
{justificacion}

Contesta a estas tres cosas:
1. Cual crees TU que es la opcion correcta (a, b o c), razonando por tu cuenta.
2. Te parece FIABLE la respuesta del asistente (true/false).
3. Que probabilidad, entre 0.0 y 1.0, asignas a que la respuesta del asistente sea CORRECTA.
   Usa el rango completo: 0.0 = seguro que se equivoca, 0.5 = no lo se, 1.0 = seguro que acierta.
   No respondas siempre 0.8 o 0.9: discrimina.

Responde UNICAMENTE con un objeto JSON valido, sin texto alrededor:
{{"mi_opcion": "a|b|c", "fiable": true|false, "prob_correcta": 0.0}}"""

NUM = re.compile(r"\d+[.,]?\d*")
CITA = re.compile(r"seg[uú]n el (?:texto|contexto|documento)|el (?:texto|contexto) (?:dice|indica|menciona|afirma)|"
                  r"de acuerdo con el (?:texto|contexto)|como se (?:indica|menciona) en el", re.IGNORECASE)
TECNICO = re.compile(
    r"\b(cortico|espinal|bulbar|reticul|vestibul|rubro|c[aá]psula|espasticidad|propiocep|"
    r"abducc|aducc|contralateral|ipsilateral|neurona|tracto|hemipl|facilitaci|inhibici|"
    r"bobath|perfetti|vojta|kabat|fnp|escapul|h[uú]mero|tibial|trapecio)\w*", re.IGNORECASE)


def ollama(model: str, prompt: str, retries: int = 2) -> str:
    body = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0, "num_ctx": 8192},
    }).encode()
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read())["response"]
        except Exception:
            if attempt == retries:
                raise
            time.sleep(3)
    return ""


def parse_json(text: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"\{.*?\}", text, re.DOTALL)
    if not m:
        return None
    raw = m.group(0)
    for attempt in (raw, re.sub(r",\s*}", "}", raw.replace("'", '"'))):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    return None


def covariables(justificacion: str) -> Dict[str, Any]:
    n = max(len(justificacion), 1)
    return {
        "len_chars": len(justificacion),
        "n_cifras": len(NUM.findall(justificacion)),
        "densidad_tecnica": round(len(TECNICO.findall(justificacion)) / (n / 1000.0), 2),
        "cita_el_contexto": bool(CITA.search(justificacion)),
    }


def load_universe() -> List[Dict[str, Any]]:
    universe = []
    for model, tag in MODELS:
        for arm in ("con", "sin"):
            path = REPORTS / f"report_{tag}_GPU_Local_Win11_9doc_sysrole_{arm}_RERUN.json"
            for q in json.load(open(path, encoding="utf-8"))["questions"]:
                universe.append({
                    "modelo": model, "tag": tag, "arm": arm, "id": q["id"],
                    "pregunta": q["pregunta"], "opciones": q["opciones"],
                    "respuesta_correcta": q["respuesta_correcta"],
                    "opcion_detectada": q["opcion_detectada"],
                    "es_correcta": q["es_correcta"],
                    "justificacion": q["respuesta_ia"],
                })
    return universe


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--judge", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--subsample", type=int, default=0,
                    help="submuestra estratificada por (modelo, brazo, acierto) para el segundo juez")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    universe = load_universe()
    print(f"Universo: {len(universe)} respuestas (esperadas 424)")

    if args.subsample:
        rng = random.Random(args.seed)
        estratos: Dict[tuple, List[Dict[str, Any]]] = {}
        for r in universe:
            estratos.setdefault((r["tag"], r["arm"], r["es_correcta"]), []).append(r)
        por_estrato = max(1, args.subsample // len(estratos))
        sel: List[Dict[str, Any]] = []
        for key in sorted(estratos):
            grupo = estratos[key]
            rng.shuffle(grupo)
            sel.extend(grupo[:por_estrato])
        universe = sorted(sel, key=lambda r: (r["tag"], r["arm"], r["id"]))
        print(f"Submuestra estratificada: {len(universe)} ({len(estratos)} estratos, semilla {args.seed})")

    out: List[Dict[str, Any]] = []
    fallos = 0
    t_ini = time.time()

    for i, r in enumerate(universe, 1):
        ops = "\n".join(f"{k}) {v}" for k, v in sorted(r["opciones"].items()))
        prompt = PROMPT.format(pregunta=r["pregunta"], opciones=ops, justificacion=r["justificacion"])

        t0 = time.time()
        resp = ollama(args.judge, prompt)
        dt = time.time() - t0
        p = parse_json(resp)

        rec = {k: r[k] for k in ("modelo", "tag", "arm", "id", "es_correcta",
                                 "opcion_detectada", "respuesta_correcta")}
        rec["juez"] = args.judge
        rec["autojuicio"] = (args.judge == r["modelo"])
        rec.update(covariables(r["justificacion"]))

        if not p or "prob_correcta" not in p:
            fallos += 1
            rec.update({"prob_correcta": None, "fiable": None, "mi_opcion": None,
                        "juez_coincide": None, "raw": resp[:300]})
        else:
            try:
                prob = float(p["prob_correcta"])
            except (TypeError, ValueError):
                prob = None
            if prob is not None:
                prob = min(1.0, max(0.0, prob))
            mi = str(p.get("mi_opcion", "")).strip().lower()[:1] or None
            rec.update({
                "prob_correcta": prob,
                "fiable": bool(p["fiable"]) if isinstance(p.get("fiable"), bool) else None,
                "mi_opcion": mi,
                "juez_coincide": (mi == r["opcion_detectada"]) if mi else None,
            })
            if prob is None:
                fallos += 1

        out.append(rec)
        if i % 20 == 0 or i == len(universe):
            el = time.time() - t_ini
            eta = el / i * (len(universe) - i)
            print(f"  [{i}/{len(universe)}] ultimo: {dt:.1f}s | transcurrido {el/60:.1f} min | ETA {eta/60:.1f} min")

    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"\n--- {args.judge}: {len(out)} juicios, {fallos} sin puntuacion valida ---")
    for arm in ("con", "sin"):
        sub = [r for r in out if r["arm"] == arm and r["prob_correcta"] is not None]
        err = [r for r in sub if not r["es_correcta"]]
        if err:
            media_err = sum(r["prob_correcta"] for r in err) / len(err)
            flag = sum(1 for r in err if r["fiable"] is False)
            print(f"  {arm}-RAG: {len(err)} errores | prob_correcta media que les asigna el juez: "
                  f"{media_err:.3f} | marcados como NO fiables: {flag}/{len(err)} ({flag/len(err)*100:.0f}%)")
    print(f"\nEscrito: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
