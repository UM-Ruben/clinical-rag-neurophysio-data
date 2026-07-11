#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validacion automatica de los bancos TRAP y OOD antes de ejecutarlos.

No sustituye a la validacion clinica humana (punto de decision D1): la precede y filtra
los fallos objetivos, que son los que un revisor humano no deberia tener que cazar.

Comprobaciones TRAP:
  T1  esquema: campos obligatorios, opciones a/b/c/d, texto exacto de `d`
  T2  trazabilidad: `traza_cita` aparece LITERALMENTE en el .txt de `documento_fuente`
  T3  coherencia de clave: trap_c -> respuesta en {a,b,c}; trap_d -> respuesta == "d"
  T4  la opcion que acepta la premisa NO es la correcta (si lo fuera, la trampa premiaria al credulo)
  T5  ids unicos

Comprobaciones OOD:
  O1  esquema y texto exacto de `d`; respuesta_correcta == "d"
  O2  ausencia: ningun `termino_clave_ausente` aparece en NINGUNO de los 9 .txt del corpus
  O3  las opciones a/b/c no son triviales (no contienen "ninguna"/"todas"; y si son muy cortas,
      deben al menos contener una cifra: "1 mL" es un distractor especifico, "si" no lo es)
  O4  ids unicos

Dos regimenes de comparacion distintos, deliberadamente:
  * Las CITAS se buscan sobre texto normalizado y, si falla, sobre texto sin ningun espacio,
    porque el extractor de PDF parte palabras ("c ortico-espinal").
  * Los TERMINOS se buscan con limite de palabra sobre el texto normalizado, NUNCA sin espacios:
    la busqueda sin espacios produce falsos positivos entre palabras contiguas (p.ej. "POMA"
    aparece dentro de "gruPO MAyor"), y un falso positivo aqui descartaria una pregunta valida.

Uso:
    python validate_banks.py --corpus <dir_txt> [--trap borrador_trap.json] [--ood borrador_ood.json]

===============================================================================================
AVISO. Este script NO es ejecutable por terceros y se publica solo para inspeccion.

Necesita el CORPUS: su cometido es precisamente comprobar, contra el texto de los PDF, que los terminos
diana de las preguntas OOD estan de verdad AUSENTES y que las trampas TRAP estan de verdad
refutadas por el documento. Es la validacion que hace honesto el instrumento, y no puede
ejecutarse sin aquello contra lo que valida.
===============================================================================================
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
OPCION_D = "No puede responderse con la documentacion disponible"
DOCS = [
    "01_bobath_concepto", "02_bobath_principios_tratamiento", "03_sistemas_motores_descendentes",
    "04_perfetti_etc", "05_bloques_3_4_tecnicas", "06_fnp_facilitacion_neuromuscular",
    "07_dist_gpc_ictus_ap_2009", "08_dist_gpc_ictus_ap_2025", "09_dist_gpc_ictus_euskadi",
]


def norm(text: str) -> str:
    """Minusculas, sin acentos, sin espacios redundantes. Neutraliza los espacios espurios del PDF."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def norm_nospace(text: str) -> str:
    """Ademas elimina TODO espacio: ultima red de seguridad contra 'c ortico-espinal'.
    Solo para CITAS: aplicado a terminos cortos daria falsos positivos entre palabras."""
    return re.sub(r"\s+", "", norm(text))


def termino_presente(termino: str, texto_norm: str) -> bool:
    """Busca el termino con limite de palabra sobre el texto normalizado."""
    t = norm(termino)
    if not t:
        return False
    return re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", texto_norm) is not None


def load_corpus(corpus_dir: Path) -> Dict[str, Tuple[str, str]]:
    out = {}
    for d in DOCS:
        p = corpus_dir / f"{d}.txt"
        if not p.exists():
            print(f"  AVISO: falta {p.name}")
            continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        out[d] = (norm(raw), norm_nospace(raw))
    return out


def check_option_d(q: Dict[str, Any], errs: List[str], tag: str) -> None:
    d = q.get("opciones", {}).get("d", "")
    if norm(d) != norm(OPCION_D):
        errs.append(f"{tag}: la opcion d no es el texto canonico (dice: {d!r})")


def validate_trap(bank: List[Dict[str, Any]], corpus: Dict[str, Tuple[str, str]]) -> List[str]:
    errs: List[str] = []
    seen = set()
    for i, q in enumerate(bank):
        tag = f"TRAP[{i}] id={q.get('id')}"
        for field in ("tipo", "pregunta", "opciones", "respuesta_correcta",
                      "documento_fuente", "traza_cita", "premisa_falsa"):
            if not q.get(field):
                errs.append(f"{tag}: falta el campo obligatorio '{field}'")
        if set(q.get("opciones", {})) != {"a", "b", "c", "d"}:
            errs.append(f"{tag}: las opciones deben ser exactamente a,b,c,d")
        check_option_d(q, errs, tag)

        if q.get("id") in seen:
            errs.append(f"{tag}: id duplicado")
        seen.add(q.get("id"))

        tipo, resp = q.get("tipo"), str(q.get("respuesta_correcta", "")).lower()
        if tipo == "trap_c" and resp not in ("a", "b", "c"):
            errs.append(f"{tag}: trap_c debe tener respuesta en a/b/c (tiene {resp!r})")
        if tipo == "trap_d" and resp != "d":
            errs.append(f"{tag}: trap_d debe tener respuesta 'd' (tiene {resp!r})")

        acepta = str(q.get("opcion_que_acepta_la_premisa", "")).lower()
        if acepta and acepta == resp:
            errs.append(f"{tag}: la opcion que acepta la premisa falsa ({acepta}) es la correcta; "
                        f"la trampa premiaria al modelo credulo")

        doc = q.get("documento_fuente")
        cita = q.get("traza_cita") or ""
        if doc not in corpus:
            errs.append(f"{tag}: documento_fuente desconocido: {doc!r}")
        elif len(cita) < 25:
            errs.append(f"{tag}: traza_cita demasiado corta ({len(cita)} chars)")
        else:
            plain, nospace = corpus[doc]
            if norm(cita) not in plain and norm_nospace(cita) not in nospace:
                errs.append(f"{tag}: traza_cita NO aparece literalmente en {doc}.txt -> {cita[:70]!r}")
    return errs


def validate_ood(bank: List[Dict[str, Any]], corpus: Dict[str, Tuple[str, str]]) -> List[str]:
    errs: List[str] = []
    seen = set()
    TRIVIAL = ("ninguna", "todas las anteriores", "no se puede")
    for i, q in enumerate(bank):
        tag = f"OOD[{i}] id={q.get('id')}"
        for field in ("pregunta", "opciones", "respuesta_correcta", "terminos_clave_ausentes"):
            if not q.get(field):
                errs.append(f"{tag}: falta el campo obligatorio '{field}'")
        if set(q.get("opciones", {})) != {"a", "b", "c", "d"}:
            errs.append(f"{tag}: las opciones deben ser exactamente a,b,c,d")
        check_option_d(q, errs, tag)
        if str(q.get("respuesta_correcta", "")).lower() != "d":
            errs.append(f"{tag}: la respuesta correcta de una OOD debe ser 'd'")

        if q.get("id") in seen:
            errs.append(f"{tag}: id duplicado")
        seen.add(q.get("id"))

        for letra in ("a", "b", "c"):
            opt = q.get("opciones", {}).get(letra, "")
            # una opcion corta es aceptable si es una cifra concreta ("1 mL", "23 puntos")
            if len(opt) < 8 and not re.search(r"\d", opt):
                errs.append(f"{tag}: la opcion {letra} es demasiado corta y sin cifra ({opt[:40]!r})")
            if any(t in norm(opt) for t in TRIVIAL):
                errs.append(f"{tag}: la opcion {letra} es trivialmente descartable ({opt[:40]!r})")

        for term in q.get("terminos_clave_ausentes", []):
            if len(norm(term)) < 3:
                errs.append(f"{tag}: termino '{term}' demasiado corto para probar ausencia")
                continue
            for doc, (plain, _) in corpus.items():
                if termino_presente(term, plain):
                    errs.append(f"{tag}: el termino '{term}' SI aparece en {doc}.txt -> la pregunta no es OOD")
                    break
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--trap", default=None)
    ap.add_argument("--ood", default=None)
    args = ap.parse_args()

    corpus = load_corpus(Path(args.corpus))
    print(f"Corpus cargado: {len(corpus)}/9 documentos\n")

    total = 0
    for kind, path in (("TRAP", args.trap), ("OOD", args.ood)):
        if not path:
            continue
        bank = json.load(open(path, encoding="utf-8"))
        errs = validate_trap(bank, corpus) if kind == "TRAP" else validate_ood(bank, corpus)
        total += len(errs)
        print(f"--- {kind}: {len(bank)} preguntas, {len(errs)} incidencias ---")
        for e in errs:
            print("  !", e)
        if not errs:
            print("  OK: sin incidencias objetivas")
        print()

    if total:
        print(f"TOTAL: {total} incidencias. Corrigelas antes de la validacion clinica (D1).")
        return 1
    print("TODO OK. Listo para validacion clinica humana (D1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
