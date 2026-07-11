#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Construye los bancos definitivos TRAP y OOD a partir de los borradores redactados y auditados.

Aplica, de forma explicita y trazable, tres correcciones detectadas en la revision adversarial,
y un control de sesgo posicional imprescindible:

  (1) SESGO POSICIONAL. En los borradores, la opcion correcta de las `trap_c` caia casi siempre
      en la letra `b`, y la opcion que acepta la premisa falsa casi siempre en la `a`. Un modelo
      con sesgo de posicion habria puntuado bien sin entender nada. Se barajan las opciones
      a/b/c con semilla fija y se remapean `respuesta_correcta` y `opcion_que_acepta_la_premisa`.
      La `d` (abstencion) queda SIEMPRE en su sitio, porque los prompts se refieren a ella.

  (2) ITEM TRAP MAL CLASIFICADO. El item del ritmo escapulo-humeral de Codman preguntaba cuantos
      grados de glenohumeral corresponden a 180 grados de abduccion. El documento SI da la
      respuesta de forma explicita ("tenemos que mover la escapula 60 y la glenohumeral 120"),
      luego la pregunta es respondible y etiquetarla `trap_d` (correcta = "no puede responderse")
      era incorrecto. Se reconvierte a `trap_c` con la cifra correcta, 120 grados, como opcion
      valida: responderla bien exige rechazar la proporcion invertida del enunciado.

  (3) JUSTIFICACIONES OOD CON HECHOS FALSOS. Tres justificaciones afirmaban que las guias de
      ictus citan las escalas ARAT y Berg. Verificado por busqueda directa: `ARAT` no aparece
      (los aparentes aciertos son "aparato") y `Berg` solo aparece dentro de los apellidos
      "Bergman" y "Bergquist" de las bibliografias. Se reescriben citando unicamente escalas
      verificadas como presentes: Rankin, Barthel, Ashworth y Frenchay Activity Index.
      La validez OOD de esas preguntas no cambia: sus terminos diana siguen ausentes.

Ids: TRAP 1001-1024, OOD 2001-2018, para no colisionar con el Gold Standard (1-53).

===============================================================================================
AVISO. Este script NO es ejecutable por terceros y se publica solo para inspeccion.

Necesita los BORRADORES de los bancos (`trap_raw.json`, `ood_raw.json`), que se redactaron a
partir de pasajes concretos del corpus con copyright y por eso NO se distribuyen. Lo que si se
publica es su SALIDA, ya depurada: `datasets/dataset_trap_validado.json` y
`datasets/dataset_ood_validado.json`.

Este fichero se publica porque documenta, de forma auditable, las cuatro correcciones que
convierten un borrador en un instrumento de medida: el barajado que elimina el sesgo posicional
(con semilla fija, de modo que la permutacion es verificable contra los bancos publicados), la
reclasificacion del item de Codman, y la depuracion de las justificaciones y de los terminos
diana OOD.
===============================================================================================

Uso:  python build_banks.py --drafts-dir <carpeta_con_los_borradores> [--seed 42]
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent

OPCION_D = "No puede responderse con la documentacion disponible"

# (2) reemplazo integro del item de Codman
CODMAN_FIX = {
    "tipo": "trap_c",
    "pregunta": ("Según el ritmo escápulo-humeral de Codman, una abducción de 90º del miembro superior "
                 "se compone de 60º de movimiento escapular y 30º de movimiento glenohumeral. "
                 "Partiendo de esta proporción, ¿cuántos grados de movimiento glenohumeral "
                 "corresponderían a una abducción total de 180º?"),
    "opciones": {
        "a": "60º de glenohumeral.",
        "b": "120º de glenohumeral.",
        "c": "90º de glenohumeral.",
        "d": OPCION_D,
    },
    "respuesta_correcta": "b",
    "opcion_que_acepta_la_premisa": "a",
    "premisa_falsa": ("El enunciado invierte la proporción de Codman al afirmar que 90º de abducción se "
                      "reparten en 60º de escápula y 30º de glenohumeral. El documento establece lo "
                      "contrario: 30º de escápula y 60º de glenohumeral, una relación 2:1 a favor de la "
                      "glenohumeral."),
    "justificacion": ("El documento aplica la proporción correcta y resuelve el caso de forma explícita: "
                      "para 180º \"tenemos que mover la escápula 60º y la glenohumeral 120º\". Responder "
                      "bien exige rechazar la proporción invertida del enunciado. La opción a (60º) es la "
                      "que se obtiene precisamente al aceptar la premisa falsa."),
    "traza_cita": "tenemos que mover la escápula 60º y la glenohumeral 120º",
    "traza_pagina": 20,
    "documento_fuente": "01_bobath_concepto",
    "dificultad": "alta",
}

# (3) justificaciones OOD reescritas, sin afirmar hechos falsos sobre el corpus
OOD_JUST_FIX = {
    12: ("Ninguno de los nueve documentos menciona la escala de Fugl-Meyer ni el concepto de diferencia "
         "mínima clínicamente importante (MCID). Las guías de ictus emplean otros instrumentos, como las "
         "escalas de Rankin, Barthel, Ashworth o el Frenchay Activity Index, pero no recogen la subescala "
         "motora de miembro superior de Fugl-Meyer ni ninguna cifra de MCID, de modo que la puntuación "
         "propuesta solo puede proceder del conocimiento paramétrico del modelo."),
    13: ("La escala de Tinetti (Performance-Oriented Mobility Assessment, POMA) y su punto de corte para "
         "riesgo de caídas no aparecen en ninguno de los nueve ficheros. Las guías de ictus abordan la "
         "valoración funcional con las escalas de Rankin y Barthel, pero no incluyen la escala de Tinetti "
         "ni ningún umbral numérico de riesgo de caídas."),
    15: ("El Box and Block Test y su mínimo cambio detectable (MDC) no figuran en ninguno de los nueve "
         "ficheros. El corpus no contiene ninguna propiedad psicométrica de tipo MDC para pruebas de "
         "miembro superior, por lo que la cifra propuesta es necesariamente una invención del modelo."),
}

# (4) TERMINOS DIANA MAL ELEGIDOS. Un `termino_clave_ausente` solo prueba algo si de verdad esta
# ausente. "control de tronco" aparece literalmente en 05_bloques_3_4_tecnicas, luego no sirve
# para demostrar que la pregunta sea irresoluble. La pregunta sigue siendo OOD: lo irrecuperable
# es la escala (Trunk Impairment Scale, Verheyden) y su puntuacion, no el concepto de tronco.
OOD_TERM_FIX = {
    14: ["Trunk Impairment Scale", "Verheyden"],
}


def shuffle_options(q: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """Baraja los contenidos de a/b/c; `d` permanece fija. Remapea las letras clave."""
    letras = ["a", "b", "c"]
    contenidos = [q["opciones"][l] for l in letras]
    perm = letras[:]
    rng.shuffle(perm)
    # perm[i] es la NUEVA letra que recibe el contenido originalmente en letras[i]
    mapa = {vieja: nueva for vieja, nueva in zip(letras, perm)}

    nuevas = {mapa[l]: c for l, c in zip(letras, contenidos)}
    nuevas["d"] = OPCION_D
    q["opciones"] = {k: nuevas[k] for k in ("a", "b", "c", "d")}

    if q["respuesta_correcta"] in mapa:
        q["respuesta_correcta"] = mapa[q["respuesta_correcta"]]
    acepta = q.get("opcion_que_acepta_la_premisa")
    if acepta in mapa:
        q["opcion_que_acepta_la_premisa"] = mapa[acepta]
    q["_permutacion"] = mapa
    return q


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--drafts-dir", default="drafts",
                    help="carpeta con trap_raw.json y ood_raw.json (borradores, no distribuibles)")
    ap.add_argument("--out-dir", default=".", help="carpeta donde escribir los bancos validados")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    drafts = Path(args.drafts_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    trap: List[Dict[str, Any]] = json.load(open(drafts / "trap_raw.json", encoding="utf-8"))
    ood: List[Dict[str, Any]] = json.load(open(drafts / "ood_raw.json", encoding="utf-8"))
    assert len(trap) == 24 and len(ood) == 18, (len(trap), len(ood))

    # (2)
    trap[2] = dict(CODMAN_FIX)
    print("Item TRAP 2 (Codman) reconvertido de trap_d a trap_c, correcta = 120 grados")

    # (3)
    for idx, texto in OOD_JUST_FIX.items():
        ood[idx]["justificacion"] = texto
    print(f"Reescritas {len(OOD_JUST_FIX)} justificaciones OOD que citaban ARAT/Berg como presentes")

    # (4)
    for idx, terms in OOD_TERM_FIX.items():
        ood[idx]["terminos_clave_ausentes"] = terms
    print(f"Depurados los terminos diana de {len(OOD_TERM_FIX)} preguntas OOD")

    # (1) barajado + ids
    antes_c = sum(1 for q in trap if q["respuesta_correcta"] == "b" and q["tipo"] == "trap_c")
    for i, q in enumerate(trap):
        q["opciones"]["d"] = OPCION_D
        if q["tipo"] == "trap_c":
            shuffle_options(q, rng)
        else:
            # en trap_d la correcta es `d`; barajar a/b/c evita que el distractor tentador
            # caiga siempre en la misma letra
            shuffle_options(q, rng)
            assert q["respuesta_correcta"] == "d"
        q["id"] = 1001 + i
        q["banco"] = "trap"

    for i, q in enumerate(ood):
        q["opciones"]["d"] = OPCION_D
        q["id"] = 2001 + i
        q["banco"] = "ood"
        q["tipo"] = "ood"
        assert q["respuesta_correcta"] == "d"

    # informe de balance
    tc = [q for q in trap if q["tipo"] == "trap_c"]
    td = [q for q in trap if q["tipo"] == "trap_d"]
    dist_correcta: Dict[str, int] = {}
    dist_acepta: Dict[str, int] = {}
    for q in tc:
        dist_correcta[q["respuesta_correcta"]] = dist_correcta.get(q["respuesta_correcta"], 0) + 1
    for q in trap:
        a = q.get("opcion_que_acepta_la_premisa")
        if a:
            dist_acepta[a] = dist_acepta.get(a, 0) + 1

    print(f"\nTRAP: {len(tc)} trap_c + {len(td)} trap_d = {len(trap)}")
    print(f"  antes del barajado: {antes_c}/12 trap_c tenian la correcta en 'b'")
    print(f"  despues: correcta de trap_c por letra -> {dict(sorted(dist_correcta.items()))}")
    print(f"  opcion que acepta la premisa por letra -> {dict(sorted(dist_acepta.items()))}")
    print(f"OOD: {len(ood)} preguntas, todas con correcta = d")

    n_total = 53 + len(trap) + len(ood)
    n_d = len(td) + len(ood)
    print(f"\nInstrumento P2: {n_total} items. Responder siempre 'd' acierta {n_d}/{n_total}; "
          f"no abstenerse nunca acierta como mucho {n_total - n_d}/{n_total}.")

    json.dump(trap, open(out_dir / "dataset_trap_validado.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(ood, open(out_dir / "dataset_ood_validado.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nEscritos en {out_dir}: dataset_trap_validado.json, dataset_ood_validado.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
