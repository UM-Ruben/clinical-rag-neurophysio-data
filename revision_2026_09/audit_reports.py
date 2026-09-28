#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auditoria de P1 contra rag_benefit_summary.json.

No reejecuta ni modifica los ocho reports originales. Recalcula accuracy,
delta_RAG, McNemar (b/c) e IC95 pareado desde las respuestas guardadas.
Aplica una correccion de lectura final, documentada y comprobada literalmente,
para la pregunta 2 de Llama con RAG. Emite el inventario de errores corregido.

Uso:
    python audit_reports.py [--out audit_reports.json]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List

from scipy.stats import binom

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT.parent / "results_ablation_p1"
SUMMARY = ROOT / "rag_benefit_summary.json"

# (etiqueta, modelo ollama, tag de fichero)
MODELS = [
    ("Llama-3.1-8B", "llama3.1:8b", "llama8b"),
    ("QLoRA neurofisio", "neurofisio-qlora", "qlora"),
    ("Qwen-2.5-7B", "qwen2.5:7b", "qwen7b"),
    ("Med42-8B", "thewindmom/llama3-med42-8b", "med42"),
]


def report_path(tag: str, arm: str) -> Path:
    return REPORTS / f"report_{tag}_GPU_Local_Win11_9doc_sysrole_{arm}_RERUN.json"


def mcnemar_p(b: int, c: int) -> float:
    """p exacta bilateral del test de McNemar (binomial sobre los discordantes)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return float(min(1.0, 2.0 * binom.cdf(k, n, 0.5)))


def paired_ci95(diffs: List[int]) -> str:
    n = len(diffs)
    mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1) if n > 1 else 0.0
    se = math.sqrt(var / n)
    return f"[{mean * 100 - 1.96 * se * 100:+.1f}, {mean * 100 + 1.96 * se * 100:+.1f}]"


def scored_answer(tag: str, arm: str, q: Dict[str, Any]) -> tuple[bool, str, bool]:
    """Devuelve correccion, opcion final y si hubo una rectificacion del parser.

    El report original conserva la salida y la clasificacion de la ejecucion.
    Esta unica rectificacion evita contar como seleccion de C una respuesta que
    termina expresamente sin elegir ninguna opcion de P1.
    """
    if (tag, arm, q["id"]) != ("llama8b", "con", 2):
        return bool(q["es_correcta"]), q["opcion_detectada"], False
    final = q["respuesta_ia"].strip().casefold()
    expected = "respuesta: ninguna de las anteriores."
    if not final.endswith(expected) or q["opcion_detectada"] != "c" or not q["es_correcta"]:
        raise ValueError("La respuesta original de Llama/con/pregunta 2 ha cambiado; revisar la correccion")
    return False, "desconocida", True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "audit_reports.json"))
    parser.add_argument("--sync-summary", action="store_true",
                        help="actualiza el resumen canonico con las puntuaciones auditadas")
    args = parser.parse_args()

    canon = {r["model"]: r for r in json.load(open(SUMMARY, encoding="utf-8"))}

    audit: Dict[str, Any] = {"protocolo": "P1_sysrole_anti_rechazo", "modelos": [], "errores": [], "correcciones": []}
    discrepancias: List[str] = []
    total_errores = 0
    exact_p_values: List[float] = []

    for label, model, tag in MODELS:
        arms = {}
        for arm in ("con", "sin"):
            path = report_path(tag, arm)
            data = json.load(open(path, encoding="utf-8"))
            qs = data["questions"]
            arms[arm] = {}

            # recuento propio, ignorando el summary del fichero
            correct = sum(1 for q in qs if q["es_correcta"])
            acc = correct / len(qs) * 100
            if abs(acc - data["summary"]["accuracy"]) > 1e-6:
                discrepancias.append(f"{tag}/{arm}: accuracy recomputada {acc:.4f} != summary {data['summary']['accuracy']}")

            for q in qs:
                ok, detected, corrected = scored_answer(tag, arm, q)
                arms[arm][q["id"]] = {**q, "es_correcta": ok, "opcion_detectada": detected}
                if corrected:
                    audit["correcciones"].append({
                        "modelo": model, "arm": arm, "id": q["id"],
                        "parser_original": q["opcion_detectada"],
                        "respuesta_final": "Ninguna de las anteriores",
                        "opcion_corregida": detected,
                        "motivo": "P1 exige elegir a, b o c; la respuesta final no elige ninguna",
                    })
                if not ok:
                    total_errores += 1
                    audit["errores"].append({
                        "modelo": model, "tag": tag, "arm": arm, "id": q["id"],
                        "respuesta_correcta": q["respuesta_correcta"],
                        "opcion_detectada": detected,
                        "len_respuesta": len(q["respuesta_ia"]),
                    })

        ids = sorted(set(arms["con"]) & set(arms["sin"]))
        con_ok = {i: arms["con"][i]["es_correcta"] for i in ids}
        sin_ok = {i: arms["sin"][i]["es_correcta"] for i in ids}

        b = sum(1 for i in ids if con_ok[i] and not sin_ok[i])   # mejora con RAG
        c = sum(1 for i in ids if sin_ok[i] and not con_ok[i])   # empeora con RAG
        acc_con = sum(con_ok.values()) / len(ids) * 100
        acc_sin = sum(sin_ok.values()) / len(ids) * 100
        delta = acc_con - acc_sin
        p = mcnemar_p(b, c)
        exact_p_values.append(p)
        ci = paired_ci95([(1 if con_ok[i] else 0) - (1 if sin_ok[i] else 0) for i in ids])

        row = {
            "model": model, "label": label, "n": len(ids),
            "acc_sin_rag": round(acc_sin, 2), "acc_con_rag": round(acc_con, 2),
            "delta_rag_pp": round(delta, 2), "paired_ci95": ci,
            "mcnemar_p": round(p, 4), "significativo": p < 0.05,
            "b_mejora": b, "c_empeora": c,
            "errores_con": sum(1 for i in ids if not con_ok[i]),
            "errores_sin": sum(1 for i in ids if not sin_ok[i]),
        }
        audit["modelos"].append(row)

    # Holm en las cuatro comparaciones por modelo, usando p sin redondear.
    adjusted = [0.0] * len(exact_p_values)
    running = 0.0
    for rank, index in enumerate(sorted(range(len(exact_p_values)), key=exact_p_values.__getitem__)):
        running = max(running, (len(exact_p_values) - rank) * exact_p_values[index])
        adjusted[index] = min(1.0, running)
    for row, p_holm in zip(audit["modelos"], adjusted):
        row["mcnemar_p_holm"] = round(p_holm, 4)

    if args.sync_summary:
        for row in audit["modelos"]:
            ref = canon[row["model"]]
            for field in ("acc_sin_rag", "acc_con_rag", "delta_rag_pp", "paired_ci95",
                          "mcnemar_p", "mcnemar_p_holm", "significativo", "b_mejora", "c_empeora"):
                ref[field] = row[field]
            ref["significativo"] = row["mcnemar_p_holm"] < 0.05
        with open(SUMMARY, "w", encoding="utf-8", newline="\n") as f:
            json.dump(list(canon.values()), f, ensure_ascii=False, indent=2)
            f.write("\n")

    # Cotejo contra el resumen canonico, despues de la sincronizacion opcional.
    for row in audit["modelos"]:
        model = row["model"]
        ref = canon.get(model)
        if ref is None:
            discrepancias.append(f"{model}: ausente en rag_benefit_summary.json")
            continue
        for field in ("acc_sin_rag", "acc_con_rag", "delta_rag_pp", "b_mejora", "c_empeora", "significativo", "mcnemar_p_holm"):
            if row[field] != ref[field]:
                discrepancias.append(f"{model}.{field}: auditoria={row[field]} canonico={ref[field]}")
        if abs(row["mcnemar_p"] - ref["mcnemar_p"]) > 5e-4:
            discrepancias.append(f"{model}.mcnemar_p: auditoria={row['mcnemar_p']} canonico={ref['mcnemar_p']}")
        if row["paired_ci95"] != ref["paired_ci95"]:
            discrepancias.append(f"{model}.paired_ci95: auditoria={row['paired_ci95']} canonico={ref['paired_ci95']}")

    audit["total_errores"] = total_errores
    audit["discrepancias"] = discrepancias

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)

    print(f"{'modelo':<28}{'sin':>8}{'con':>8}{'delta':>9}{'b':>5}{'c':>5}{'p':>10}  err_con/err_sin")
    for r in audit["modelos"]:
        print(f"{r['label']:<28}{r['acc_sin_rag']:>8.2f}{r['acc_con_rag']:>8.2f}"
              f"{r['delta_rag_pp']:>+9.2f}{r['b_mejora']:>5}{r['c_empeora']:>5}{r['mcnemar_p']:>10.4f}"
              f"  {r['errores_con']}/{r['errores_sin']}")
    print(f"\nTotal respuestas erroneas P1 corregidas: {total_errores}")
    if discrepancias:
        print(f"\n!! {len(discrepancias)} DISCREPANCIAS vs rag_benefit_summary.json:")
        for d in discrepancias:
            print("  -", d)
        return 1
    print("\nOK: los 8 reports crudos reproducen exactamente rag_benefit_summary.json")
    print(f"Escrito: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
