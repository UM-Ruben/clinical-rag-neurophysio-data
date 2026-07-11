#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cierra el estudio con la adjudicacion externa (humana o de juez de frontera).

Es el puente que faltaba: los ficheros de adjudicacion son CSV con ';', mientras que
`analyze_taxonomia.py --humano` consume JSON. Este script detecta que hay anotado, convierte,
reejecuta el analisis con la etiqueta de oro, y regenera tablas y figuras.

Es NO DESTRUCTIVO y IDEMPOTENTE. Nunca sobrescribe el pre-etiquetado ni ningun fichero publicado:
escribe en `code/output/` y deja que `analyze_taxonomia.py` haga la sustitucion (la adjudicacion
externa manda sobre el juez local).

Reconstruye, desde los CSV de `annotation/` y los 8 reports crudos de `results_ablation_p1/`:
  - taxonomia_frontera.json      (131 etiquetas adjudicadas)
  - detectability_frontera.json  (80 casos juzgados, con sus covariables)

Ambos estan publicados en `aggregates/`, de modo que `reproduce.py` los coteja.

Uso:
    python finalizar_anotacion.py             # diagnostico: que hay anotado y que falta
    python finalizar_anotacion.py --ejecutar  # ademas, rehace analisis + tablas + figuras
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# `covariables()` vive en el script de inferencia, pero es una funcion pura de texto: no toca
# Ollama ni el corpus. Importarla garantiza que el juez de frontera y los jueces locales comparten
# EXACTAMENTE la misma definicion de las covariables de confusion.
sys.path.insert(0, str(HERE.parent / "inference"))

import _repo  # noqa: E402

CATS = {"T1", "T2", "T3", "T4", "T5"}
TAGS = ("llama8b", "qlora", "qwen7b", "med42")
REPORT_TMPL = "report_{tag}_GPU_Local_Win11_9doc_sysrole_{arm}_RERUN.json"


def leer_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def col(fila: Dict[str, str], prefijo: str) -> str:
    """Los encabezados llevan sufijos explicativos, p.ej. 'categoria(T1-T5)'."""
    for k, v in fila.items():
        if k and k.strip().lower().startswith(prefijo):
            return (v or "").strip()
    return ""


# ───────────────────────── taxonomia (D3) ─────────────────────────
def taxonomia(args, anot: Path, out: Path, ejecutar: bool) -> bool:
    filas = leer_csv(anot / "taxonomia_para_anotar.csv")
    if not filas:
        print("  taxonomia: no se encuentra el CSV de anotacion")
        return False

    anotadas, malas = [], []
    for f in filas:
        cat = col(f, "categoria").upper()
        if not cat:
            continue
        if cat not in CATS:
            malas.append((f.get("tag"), f.get("arm"), f.get("id"), cat))
            continue
        anotadas.append({"tag": f["tag"], "arm": f["arm"], "id": int(f["id"]), "categoria": cat})

    print(f"  taxonomia: {len(anotadas)}/{len(filas)} errores adjudicados")
    if malas:
        print(f"  AVISO: {len(malas)} categorias no reconocidas (deben ser T1..T5): {malas[:5]}")
    if not anotadas:
        print("  -> nada que consolidar; el analisis usaria el pre-etiquetado automatico")
        return False
    if len(anotadas) < len(filas):
        print(f"  -> PARCIAL: faltan {len(filas)-len(anotadas)}. Se consolidara lo anotado y el resto")
        print("     conservara la etiqueta del juez local.")

    destino = out / "taxonomia_frontera.json"
    json.dump(anotadas, open(destino, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  -> escrito {destino.name} ({len(anotadas)} etiquetas adjudicadas)")

    if ejecutar:
        corre([sys.executable, str(HERE / "analyze_taxonomia.py"),
               "--data-root", args.data_root, "--out-dir", str(out),
               "--humano", str(destino)])
    return True


# ─────────────────────── detectabilidad (panel del juez de frontera) ──────────
def detectabilidad(args, anot: Path, reports: Path, agg: Path, out: Path, ejecutar: bool) -> bool:
    filas = leer_csv(anot / "detectabilidad_humano.csv")
    clave_path = anot / "detectabilidad_humano_CLAVE.json"
    if not filas or not clave_path.exists():
        print("  detectabilidad: falta el CSV o la clave")
        return False

    clave = {int(r["caso"]): r for r in json.load(open(clave_path, encoding="utf-8"))}

    # Los confusores se calculan con la MISMA funcion que usaron los jueces locales; ponerlos a
    # cero haria degenerar la regresion logistica (columnas constantes) y produciria un
    # "el efecto no sobrevive al control" sobre datos vacios, que seria una afirmacion falsa.
    from detectability_study import covariables  # noqa: E402

    respuestas = {}
    for tag in TAGS:
        for arm in ("con", "sin"):
            p = reports / REPORT_TMPL.format(tag=tag, arm=arm)
            for q in json.load(open(p, encoding="utf-8"))["questions"]:
                respuestas[(tag, arm, q["id"])] = q["respuesta_ia"]

    juicios = []
    for f in filas:
        fiable, prob = col(f, "fiable").lower(), col(f, "prob_correcta")
        if not fiable and not prob:
            continue
        caso = int(f["caso"])
        k = clave.get(caso)
        if not k:
            continue
        try:
            p = float(prob.replace(",", "."))
        except ValueError:
            print(f"  AVISO: caso {caso} con prob_correcta no numerica: {prob!r}")
            continue
        just = respuestas[(k["tag"], k["arm"], k["id"])]
        juicios.append({
            "juez": "claude-frontera", "caso": caso, "tag": k["tag"], "arm": k["arm"], "id": k["id"],
            "es_correcta": k["es_correcta"], "prob_correcta": p,
            "fiable": fiable in ("si", "sí", "s", "true", "1"),
            "mi_opcion": col(f, "mi_opcion") or None,
            "juez_coincide": (col(f, "mi_opcion") or None) == k["opcion_detectada"],
            "autojuicio": False,
            **covariables(just),
        })

    print(f"  detectabilidad: {len(juicios)}/{len(filas)} casos juzgados por el juez de frontera")
    if not juicios:
        print("  -> nada que puntuar")
        return False
    if len(juicios) < len(filas):
        print(f"  -> PARCIAL: faltan {len(filas)-len(juicios)} de los 80")

    destino = out / "detectability_frontera.json"
    json.dump(juicios, open(destino, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  -> escrito {destino.name}")

    n_con = sum(1 for j in juicios if j["arm"] == "con")
    if n_con < 8 or (len(juicios) - n_con) < 8:
        print(f"  -> AVISO: brazos desequilibrados (con={n_con}, sin={len(juicios)-n_con});")
        print("     el AUROC por brazo sera inestable. Conviene completar el panel.")
        return True

    if ejecutar:
        corre([sys.executable, str(HERE / "analyze_detectability.py"),
               "--data-root", args.data_root, "--out-dir", str(out), "--juicios",
               str(agg / "detectability_qwen.json"), str(agg / "detectability_llama.json"),
               str(destino)])
    return True


def corre(cmd: List[str]) -> None:
    print("\n$ " + " ".join(Path(c).name if c.endswith(".py") else c for c in cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"  !! fallo con codigo {r.returncode}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _repo.add_data_root(ap)
    _repo.add_out_dir(ap)
    ap.add_argument("--ejecutar", action="store_true",
                    help="ademas de convertir, reejecuta analisis, tablas y figuras")
    args = ap.parse_args()

    anot = _repo.annotation(args)
    reports = _repo.reports_p1(args)
    agg = _repo.aggregates(args)
    out = _repo.out_dir(args)

    print("=" * 72)
    print("ESTADO DE LA ADJUDICACION")
    print("=" * 72)
    hay_tax = taxonomia(args, anot, out, args.ejecutar)
    print()
    hay_det = detectabilidad(args, anot, reports, agg, out, args.ejecutar)

    if args.ejecutar and (hay_tax or hay_det):
        corre([sys.executable, str(HERE / "make_hallucination_tables.py"),
               "--data-root", args.data_root, "--out-dir", str(out)])
        corre([sys.executable, str(HERE / "make_hallucination_figures.py"),
               "--data-root", args.data_root, "--out-dir", str(out)])
    elif not (hay_tax or hay_det):
        print("\n" + "=" * 72)
        print("NADA ANOTADO. Se esperan los CSV en annotation/:")
        print("  taxonomia_para_anotar.csv    (columna 'categoria', T1..T5)")
        print("  detectabilidad_humano.csv    (mi_opcion, fiable, prob_correcta)")
        print("Nota: la columna 'subtags' del CSV se ignora; C-DIST/C-DILU se retiraron del estudio.")
        print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
