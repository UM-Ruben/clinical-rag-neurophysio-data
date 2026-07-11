#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-etiquetado de la taxonomia de errores sobre las 131 respuestas erroneas de P1.

Combina reglas deterministas (que tienen PRIORIDAD sobre el juez) con un juez LLM local.
El codebook completo esta en `taxonomia_codebook.md` y se considera congelado (D3).

  T5  rechazo residual        -> por REGLA (opcion_detectada desconocida o patron de rechazo)
  T1  fabricacion parametrica
  T2  lectura erronea del contexto   (solo brazo con RAG)
  T3  razonamiento invalido
  T4  premisa correcta, opcion erronea
  subtags con RAG: C-DIST (usa un chunk distractor), C-DILU (fragmento relevante ausente)

El juez NUNCA es autoridad final: la etiqueta de oro es la humana. Este script produce el
pre-etiquetado que el anotador humano adjudica, y permite medir el acuerdo juez-humano.

Uso:
    python classify_errors.py --judge qwen2.5:7b --out errores_prelabel.json
    python classify_errors.py --judge llama3.1:8b --subsample 40 --seed 42 --out errores_prelabel_juez2.json

===============================================================================================
AVISO. Este script NO es ejecutable por terceros y se publica solo para inspeccion.

Necesita un servidor Ollama local (el juez LLM que pre-etiqueta la taxonomia) y los fragmentos
recuperados verbatim del corpus, que no se distribuyen. Produce `errores_prelabel.json`,
publicado en `aggregates/` con sus citas largas redactadas por derechos de autor.
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

# fragmentos que vio el brazo con-RAG (identicos para los 4 modelos, verificado en chunk_provenance.py)
FRAG_SOURCE = REPORTS / "report_llama3.1_8b_GPU_Local_Win11_9doc_llama8b_bge-m3_20260623_231909.json"
PROVENANCE = ROOT / "chunk_provenance.json"

RECHAZO = re.compile(
    r"ninguna\s+(?:de\s+las\s+)?opci|no\s+est[aá]\s+entre\s+las\s+opciones|no\s+se\s+ajusta\s+a\s+ninguna|"
    r"no\s+hay\s+(?:una\s+)?opci[oó]n\s+correcta|none\s+of\s+the|lo siento|no puedo proporcionar|"
    r"no puedo ayudar|no puedo asistir",
    re.IGNORECASE,
)

CATEGORIAS = ("T1", "T2", "T3", "T4", "T5")

ESTADOS = ("presente_bien_usada", "presente_mal_leida", "ausente", "contradicha")

# El juez NO asigna la categoria. Se le pide una descomposicion factual sencilla, que un modelo
# de 7B puede resolver con fiabilidad, y la categoria se deduce por regla en Python. Un intento
# previo que pedia la etiqueta directamente produjo una distribucion degenerada (cero T2, dos T1),
# porque en el brazo sin RAG el juez no recibia evidencia y no podia saber si un hecho estaba o no
# en el temario. Ahora la evidencia se entrega SIEMPRE, como material de referencia del anotador.
CODEBOOK = """Eres un auditor de errores de un sistema de IA clinica. Un modelo ha fallado una pregunta
de opcion multiple de fisioterapia neurologica. Tu tarea NO es clasificarlo, sino responder tres
preguntas concretas sobre su razonamiento.

Se te entrega la EVIDENCIA DOCUMENTAL de referencia: los fragmentos del temario que corresponden a
esa pregunta. Es material de auditoria. {acceso}

1. AFIRMACION CLAVE. Identifica la afirmacion factual concreta sobre la que el modelo apoya su
   eleccion (no su conclusion, sino el hecho en que se basa). Citala brevemente.

2. ESTADO DE ESA AFIRMACION EN LA EVIDENCIA. Elige exactamente uno:
   - "presente_bien_usada": la afirmacion aparece en la evidencia y el modelo la reproduce con
     fidelidad.
   - "presente_mal_leida": el tema aparece en la evidencia, pero el modelo lo distorsiona
     (invierte una lateralidad, atribuye a una estructura lo que el texto dice de otra, cambia
     abduccion por aduccion, saca una frase de su alcance).
   - "ausente": la evidencia no dice nada de eso; el modelo lo ha traido de su propio conocimiento.
   - "contradicha": la evidencia afirma expresamente lo contrario.

3. QUE OPCION DEFIENDE SU PROPIO TEXTO. Lee el cuerpo del razonamiento, IGNORANDO la letra final
   que emite y IGNORANDO cual es la respuesta correcta. Segun lo que el texto argumenta, que
   opcion esta defendiendo? Responde con una letra (a, b, c o d), o "ninguna" si no defiende
   ninguna con claridad.
   ATENCION: esta pregunta NO es "cual es la respuesta correcta". Aunque el modelo se equivoque,
   normalmente su texto defiende de forma coherente la misma opcion que acaba eligiendo, y
   entonces debes devolver esa misma letra. Solo devolveras una letra distinta si el texto
   argumenta a favor de una opcion y luego, por descuido, escribe otra.

4. SUBTAGS (solo si el modelo TUVO acceso a la evidencia). Marca los que apliquen:
   - "C-DIST": el modelo se apoya en contenido sobre ICTUS, codigo ictus, trombolisis, atencion
     primaria o guias de practica clinica del ictus. Son documentos distractores, ajenos al
     temario de neurorrehabilitacion.
   - "C-DILU": la evidencia trata el tema pero NO contiene el dato concreto que la pregunta pide.

Responde UNICAMENTE con un objeto JSON valido, sin texto alrededor:
{{"afirmacion_clave": "<cita breve>", "estado_en_evidencia": "presente_bien_usada|presente_mal_leida|ausente|contradicha", "opcion_que_defiende_el_texto": "a|b|c|d|ninguna", "subtags": [], "motivo": "<una frase>"}}"""

ACCESO_CON = ("El modelo evaluado SI vio exactamente estos fragmentos: se le entregaron como contexto.")
ACCESO_SIN = ("El modelo evaluado NO vio estos fragmentos: respondio unicamente de memoria, sin "
              "documentacion. La evidencia se te muestra a ti para que puedas juzgar si lo que el "
              "modelo afirmo se corresponde con el temario o se lo invento.")


def mapear_categoria(estado: str, opcion_defendida: Optional[str], emitida: str, arm: str) -> str:
    """Deduce la categoria primaria a partir de la descomposicion del juez. Regla, no juicio.

    - T4 se decide por COMPARACION objetiva, no por opinion del juez: si el texto defiende una
      opcion y la letra emitida es otra, el fallo es de mapeo.
    - Si el hecho no esta en la evidencia o la evidencia lo contradice, el modelo lo fabrico: T1.
    - Si el hecho esta pero lo distorsiona: T2 si tuvo el contexto delante; si no lo tuvo, no pudo
      "leer mal" nada, luego reprodujo de memoria una version deformada, que es fabricacion: T1.
    - Si el hecho esta y lo usa bien, lo que falla es la inferencia: T3.
    """
    if opcion_defendida in ("a", "b", "c", "d") and opcion_defendida != emitida:
        return "T4"
    if estado in ("ausente", "contradicha"):
        return "T1"
    if estado == "presente_mal_leida":
        return "T2" if arm == "con" else "T1"
    return "T3"


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
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        # rescate: comillas simples o comas colgantes
        raw = m.group(0).replace("'", '"')
        raw = re.sub(r",\s*}", "}", raw)
        raw = re.sub(r",\s*]", "]", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None


def build_prompt(err: Dict[str, Any], evidencia: str) -> str:
    ops = "\n".join(f"{k}) {v}" for k, v in sorted(err["opciones"].items()))
    acceso = ACCESO_CON if err["arm"] == "con" else ACCESO_SIN
    bloques = [
        CODEBOOK.format(acceso=acceso), "", "=" * 60, "",
        f"PREGUNTA:\n{err['pregunta']}\n\nOPCIONES:\n{ops}",
        f"\nOPCION CORRECTA: {err['respuesta_correcta']}",
        f"OPCION QUE ELIGIO EL MODELO (incorrecta): {err['opcion_detectada']}",
        f"\nEVIDENCIA DOCUMENTAL DE REFERENCIA:\n{evidencia}",
        f"\nRAZONAMIENTO COMPLETO DEL MODELO:\n{err['respuesta_ia']}",
        "\nJSON:",
    ]
    return "\n".join(bloques)


def regla_t5(err: Dict[str, Any]) -> bool:
    if err["opcion_detectada"] == "desconocida":
        return True
    # rechazo explicito en el tramo final de la justificacion
    cola = err["respuesta_ia"][-400:]
    return bool(RECHAZO.search(cola)) and err["opcion_detectada"] not in ("a", "b", "c", "d")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--judge", default="qwen2.5:7b")
    ap.add_argument("--out", default=str(ROOT / "errores_prelabel.json"))
    ap.add_argument("--subsample", type=int, default=0, help="anotar solo N casos (doble anotacion)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-frag-chars", type=int, default=6000)
    args = ap.parse_args()

    frags = {q["id"]: q.get("fragmentos", []) for q in json.load(open(FRAG_SOURCE, encoding="utf-8"))["questions"]}
    prov = json.load(open(PROVENANCE, encoding="utf-8"))["preguntas"] if PROVENANCE.exists() else {}

    errores: List[Dict[str, Any]] = []
    for model, tag in MODELS:
        for arm in ("con", "sin"):
            path = REPORTS / f"report_{tag}_GPU_Local_Win11_9doc_sysrole_{arm}_RERUN.json"
            for q in json.load(open(path, encoding="utf-8"))["questions"]:
                if q["es_correcta"]:
                    continue
                errores.append({**q, "modelo": model, "tag": tag, "arm": arm})

    print(f"Errores a clasificar: {len(errores)} (esperados 131)")

    if args.subsample:
        random.Random(args.seed).shuffle(errores)
        errores = sorted(errores[:args.subsample], key=lambda e: (e["tag"], e["arm"], e["id"]))
        print(f"Submuestra de {len(errores)} (semilla {args.seed})")

    out: List[Dict[str, Any]] = []
    por_regla = 0
    fallos_parseo = 0

    for i, err in enumerate(errores, 1):
        base = {
            "modelo": err["modelo"], "tag": err["tag"], "arm": err["arm"], "id": err["id"],
            "respuesta_correcta": err["respuesta_correcta"], "opcion_detectada": err["opcion_detectada"],
            "len_justificacion": len(err["respuesta_ia"]),
            "juez": args.judge,
        }

        if regla_t5(err):
            por_regla += 1
            out.append({**base, "categoria": "T5", "subtags": [], "cita_soporte": "",
                        "motivo": "regla determinista: rechazo residual / letra no interpretable",
                        "origen": "regla"})
            print(f"  [{i}/{len(errores)}] {err['tag']}/{err['arm']} q{err['id']}: T5 (regla)")
            continue

        # la evidencia se entrega en AMBOS brazos: sin ella el juez no puede distinguir un hecho
        # fabricado de uno correcto pero mal aplicado
        evidencia = "\n\n---\n\n".join(frags.get(err["id"], []))[:args.max_frag_chars]

        t0 = time.time()
        resp = ollama(args.judge, build_prompt(err, evidencia))
        dt = time.time() - t0
        parsed = parse_json(resp)

        estado = (parsed or {}).get("estado_en_evidencia")
        if not parsed or estado not in ESTADOS:
            fallos_parseo += 1
            out.append({**base, "categoria": None, "subtags": [], "estado_en_evidencia": None,
                        "motivo": "el juez no devolvio una descomposicion valida", "origen": "juez",
                        "raw": resp[:600]})
            print(f"  [{i}/{len(errores)}] {err['tag']}/{err['arm']} q{err['id']}: SIN PARSEAR ({dt:.1f}s)")
            continue

        defendida = str(parsed.get("opcion_que_defiende_el_texto", "")).strip().lower()[:1]
        if defendida not in ("a", "b", "c", "d"):
            defendida = None
        cat = mapear_categoria(estado, defendida, err["opcion_detectada"], err["arm"])

        subtags = [s for s in (parsed.get("subtags") or []) if s in ("C-DIST", "C-DILU")]
        if err["arm"] == "sin":
            subtags = []  # sin contexto no hay contaminacion ni dilucion posibles

        rec = {**base, "categoria": cat, "subtags": subtags,
               "estado_en_evidencia": estado, "opcion_que_defiende_el_texto": defendida,
               "cita_soporte": str(parsed.get("afirmacion_clave", ""))[:400],
               "motivo": str(parsed.get("motivo", ""))[:300], "origen": "juez"}
        if err["arm"] == "con" and str(err["id"]) in prov:
            rec["contexto_tenia_distractor"] = prov[str(err["id"])]["contaminado_por_distractor"]
        out.append(rec)
        print(f"  [{i}/{len(errores)}] {err['tag']}/{err['arm']} q{err['id']}: "
              f"{cat} <- {estado} defiende={defendida} emitida={err['opcion_detectada']} {subtags} ({dt:.1f}s)")

    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"\n--- Resumen del pre-etiquetado (juez: {args.judge}) ---")
    print(f"  por regla (T5): {por_regla}")
    print(f"  fallos de parseo: {fallos_parseo}")
    for arm in ("con", "sin"):
        conteo: Dict[str, int] = {}
        for r in out:
            if r["arm"] == arm and r["categoria"]:
                conteo[r["categoria"]] = conteo.get(r["categoria"], 0) + 1
        total = sum(conteo.values())
        detalle = "  ".join(f"{k}={v}" for k, v in sorted(conteo.items()))
        print(f"  {arm}-RAG (n={total}): {detalle}")
    print(f"\nEscrito: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
