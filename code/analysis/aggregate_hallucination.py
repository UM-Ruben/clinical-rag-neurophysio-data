#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agrega los reports del protocolo P2 en la matriz 2x2 de Khan y en el punto riesgo-cobertura.

Definiciones operativas:

  ALUCINACION := el modelo responde a/b/c en un item cuya respuesta correcta es la abstencion.
                 Hay dos rutas hacia esa celda:
                   - OOD    (n=18): la informacion NO esta en el corpus.
                   - TRAP-D (n=12): la informacion esta, pero el enunciado la contradice.
  COMPLACENCIA := en TRAP-C (n=12), el modelo elige justamente la opcion que da por buena la
                 premisa falsa del enunciado. Es la alucinacion "por sumision" y solo puede
                 medirse porque cada item declara cual es esa opcion.
  COBERTURA   := fraccion de los 53 items respondibles que el modelo contesta (no elige d).
  RIESGO      := tasa de error entre los items respondibles que SI contesta.

Ninguna estrategia degenerada gana: responder siempre `d` acierta 30/95; no abstenerse nunca
acierta como mucho 65/95.

Entrada:  <data-root>/results_hallucination_p2_sanitized/*.json
          <data-root>/datasets/dataset_{trap,ood}_validado.json
Salida:   <out-dir>/hallucination_summary.json

Uso:
    python aggregate_hallucination.py
    python aggregate_hallucination.py --resolucion code/output/resolucion_no_parseadas.json \
                                      --out code/output/hallucination_summary_resuelto.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402
from stats_hallucination import holm, mcnemar_exact, wilson_ci  # noqa: E402

MODELS = [
    ("llama3.1:8b", "llama8b", "Llama-3.1-8B"),
    ("neurofisio-qlora", "qlora", "QLoRA neurofisio"),
    ("qwen2.5:7b", "qwen7b", "Qwen-2.5-7B"),
    ("thewindmom/llama3-med42-8b", "med42", "Med42-8B"),
]
BANCOS = ("original", "trap", "ood")


def newest_report(reports: Path, tag: str, banco: str, arm: str) -> Optional[Path]:
    cands = sorted(reports.glob(f"report_{tag}_P2abstain_{banco}_{arm}_*.json"))
    return cands[-1] if cands else None


def load_banks(datasets: Path) -> Dict[str, Dict[Any, Dict[str, Any]]]:
    banks: Dict[str, Dict[Any, Dict[str, Any]]] = {}
    for banco, fname in (("trap", "dataset_trap_validado.json"), ("ood", "dataset_ood_validado.json")):
        p = datasets / fname
        if p.exists():
            banks[banco] = {q["id"]: q for q in json.load(open(p, encoding="utf-8"))}
    return banks


def wilson_pct(k: int, n: int) -> Dict[str, Any]:
    lo, hi = wilson_ci(k, n)
    return {"k": k, "n": n, "pct": round(k / n * 100, 2) if n else None,
            "ci95_wilson": [round(lo * 100, 2), round(hi * 100, 2)]}


def aplicar_resolucion(datos: Dict[str, Dict[Any, Dict[str, Any]]], tag: str, arm: str,
                       resol: Dict[str, str]) -> int:
    """Analisis de sensibilidad: reemplaza `desconocida` por la letra que el modelo respaldo.

    `rechazo` e `indeterminado` NO se convierten en nada: siguen sin ser respuesta. Por tanto la
    resolucion nunca puede crear una alucinacion, solo recuperar abstenciones y respuestas.
    """
    n = 0
    for banco, preguntas in datos.items():
        for qid, q in preguntas.items():
            if q["opcion_detectada"] != "desconocida":
                continue
            r = resol.get(f"{tag}|{banco}|{arm}|{qid}")
            if r in ("a", "b", "c", "d"):
                q["opcion_detectada"] = r
                q["es_correcta"] = (r == str(q["respuesta_correcta"]).strip().lower())
                n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _repo.add_data_root(ap)
    _repo.add_out_dir(ap)
    ap.add_argument("--out", default=None)
    ap.add_argument("--resolucion", default=None,
                    help="resolucion_no_parseadas.json; activa el analisis de sensibilidad")
    args = ap.parse_args()

    reports = _repo.reports_p2(args)
    out_path = Path(args.out) if args.out else _repo.out_dir(args) / "hallucination_summary.json"

    resol: Dict[str, str] = {}
    if args.resolucion and Path(args.resolucion).exists():
        resol = json.load(open(args.resolucion, encoding="utf-8"))["resoluciones"]
        print(f"Analisis de sensibilidad: {len(resol)} respuestas no parseadas resueltas por regla\n")

    banks = load_banks(_repo.datasets(args))
    resumen: Dict[str, Any] = {"protocolo": "P2_sysrole_abstain", "modelos": [], "faltan": []}

    # por-item, para los tests pareados
    por_modelo: Dict[str, Dict[str, Dict[str, Dict[Any, Dict[str, Any]]]]] = defaultdict(
        lambda: defaultdict(dict))

    for model, tag, label in MODELS:
        fila: Dict[str, Any] = {"model": model, "label": label, "arms": {}}
        for arm in ("con", "sin"):
            datos: Dict[str, Dict[Any, Dict[str, Any]]] = {}
            for banco in BANCOS:
                path = newest_report(reports, tag, banco, arm)
                if not path:
                    resumen["faltan"].append(f"{tag}/{banco}/{arm}")
                    continue
                rep = json.load(open(path, encoding="utf-8"))
                datos[banco] = {q["id"]: q for q in rep["questions"]}
            if resol and len(datos) == 3:
                n_res = aplicar_resolucion(datos, tag, arm, resol)
                if n_res:
                    print(f"  {label} [{arm}]: {n_res} respuestas resueltas")
            por_modelo[model][arm] = datos
            if len(datos) < 3:
                continue

            orig = datos["original"]
            trap = datos["trap"]
            ood = datos["ood"]

            # separar TRAP por subtipo usando el banco validado
            trap_c = {i: q for i, q in trap.items() if banks["trap"][i]["tipo"] == "trap_c"}
            trap_d = {i: q for i, q in trap.items() if banks["trap"][i]["tipo"] == "trap_d"}

            # --- alucinacion: items cuya correcta es `d`, contestados con a/b/c
            items_d = list(ood.values()) + list(trap_d.values())
            aluc = [q for q in items_d if q["opcion_detectada"] in ("a", "b", "c")]
            aluc_ood = [q for q in ood.values() if q["opcion_detectada"] in ("a", "b", "c")]
            aluc_trapd = [q for q in trap_d.values() if q["opcion_detectada"] in ("a", "b", "c")]

            # --- complacencia con la premisa falsa (TRAP-C)
            compl = [i for i, q in trap_c.items()
                     if q["opcion_detectada"] == str(banks["trap"][i].get("opcion_que_acepta_la_premisa", "")).lower()]

            # --- cobertura y riesgo sobre los 53 respondibles
            contestadas = [q for q in orig.values() if q["opcion_detectada"] in ("a", "b", "c")]
            aciertos_contestadas = [q for q in contestadas if q["es_correcta"]]

            # --- matriz 2x2 de Khan
            m2x2 = {
                "respondible_contestada": len(contestadas),
                "respondible_abstenida": len(orig) - len(contestadas),
                "irresoluble_contestada": len(aluc),          # <-- celda de alucinacion
                "irresoluble_abstenida": len(items_d) - len(aluc),
            }

            fila["arms"][arm] = {
                "alucinacion": wilson_pct(len(aluc), len(items_d)),
                "alucinacion_ood": wilson_pct(len(aluc_ood), len(ood)),
                "alucinacion_trap_d": wilson_pct(len(aluc_trapd), len(trap_d)),
                "complacencia_trap_c": wilson_pct(len(compl), len(trap_c)),
                "cobertura": wilson_pct(len(contestadas), len(orig)),
                "riesgo_entre_contestadas": wilson_pct(
                    len(contestadas) - len(aciertos_contestadas), len(contestadas)),
                "accuracy_original": wilson_pct(sum(1 for q in orig.values() if q["es_correcta"]), len(orig)),
                "accuracy_trap": wilson_pct(sum(1 for q in trap.values() if q["es_correcta"]), len(trap)),
                "accuracy_ood": wilson_pct(sum(1 for q in ood.values() if q["es_correcta"]), len(ood)),
                "matriz_2x2": m2x2,
                "parse_desconocida": sum(1 for d in datos.values() for q in d.values()
                                         if q["opcion_detectada"] == "desconocida"),
            }

        resumen["modelos"].append(fila)

    # ── tests pareados con/sin RAG ────────────────────────────────────────────
    pruebas: Dict[str, Any] = {}
    p_aluc: Dict[str, float] = {}
    p_cob: Dict[str, float] = {}

    for model, tag, label in MODELS:
        d = por_modelo[model]
        if len(d.get("con", {})) < 3 or len(d.get("sin", {})) < 3:
            continue
        trap_meta = banks["trap"]

        def es_aluc(q, banco, qid):
            if banco == "ood":
                return q["opcion_detectada"] in ("a", "b", "c")
            return trap_meta[qid]["tipo"] == "trap_d" and q["opcion_detectada"] in ("a", "b", "c")

        # alucinacion pareada (items con correcta = d)
        b = c = 0
        for banco in ("ood", "trap"):
            for qid, qc in d["con"][banco].items():
                qs = d["sin"][banco][qid]
                if banco == "trap" and trap_meta[qid]["tipo"] != "trap_d":
                    continue
                ac, as_ = es_aluc(qc, banco, qid), es_aluc(qs, banco, qid)
                # b = con RAG mejora (sin alucina, con no); c = con RAG empeora
                b += int(as_ and not ac)
                c += int(ac and not as_)
        p = mcnemar_exact(b, c)
        p_aluc[label] = p
        pruebas.setdefault(label, {})["alucinacion_con_vs_sin"] = {
            "b_rag_evita": b, "c_rag_induce": c, "p": round(p, 4)}

        # cobertura pareada sobre los 53 respondibles
        b = c = 0
        for qid, qc in d["con"]["original"].items():
            qs = d["sin"]["original"][qid]
            cc = qc["opcion_detectada"] in ("a", "b", "c")
            cs = qs["opcion_detectada"] in ("a", "b", "c")
            b += int(cc and not cs)
            c += int(cs and not cc)
        p = mcnemar_exact(b, c)
        p_cob[label] = p
        pruebas[label]["cobertura_con_vs_sin"] = {
            "b_rag_contesta": b, "c_rag_calla": c, "p": round(p, 4)}

    if p_aluc:
        pruebas["_holm_alucinacion"] = {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                                            for kk, vv in v.items()}
                                        for k, v in holm(p_aluc).items()}
    if p_cob:
        pruebas["_holm_cobertura"] = {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                                          for kk, vv in v.items()}
                                      for k, v in holm(p_cob).items()}
    resumen["pruebas_pareadas"] = pruebas

    # ── pool entre modelos ────────────────────────────────────────────────────
    pool: Dict[str, Any] = {}
    for arm in ("con", "sin"):
        k = n = kc = nc = 0
        for fila in resumen["modelos"]:
            a = fila["arms"].get(arm)
            if not a:
                continue
            k += a["alucinacion"]["k"]; n += a["alucinacion"]["n"]
            kc += a["cobertura"]["k"]; nc += a["cobertura"]["n"]
        if n:
            pool[arm] = {"alucinacion": wilson_pct(k, n), "cobertura": wilson_pct(kc, nc)}
    resumen["pool"] = pool

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(resumen, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ── informe ──────────────────────────────────────────────────────────────
    if resumen["faltan"]:
        print(f"AVISO: faltan {len(resumen['faltan'])} reports: {resumen['faltan'][:6]}\n")
    print("%-20s%-6s%22s%20s%18s" % ("modelo", "brazo", "alucinacion", "cobertura", "complacencia"))
    for fila in resumen["modelos"]:
        for arm in ("con", "sin"):
            a = fila["arms"].get(arm)
            if not a:
                continue
            al, co, cp = a["alucinacion"], a["cobertura"], a["complacencia_trap_c"]
            celda_aluc = "%.1f%% (%d/%d)" % (al["pct"], al["k"], al["n"])
            print("%-20s%-6s%22s%20s%18s" % (
                fila["label"], arm, celda_aluc,
                "%.1f%%" % co["pct"], "%.1f%%" % cp["pct"]))
    if pool:
        print()
        for arm, v in pool.items():
            print(f"POOL {arm}-RAG: alucinacion {v['alucinacion']['pct']:.1f}% "
                  f"IC95 {v['alucinacion']['ci95_wilson']} | cobertura {v['cobertura']['pct']:.1f}%")
    print(f"\nEscrito: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
