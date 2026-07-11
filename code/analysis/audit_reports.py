#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auditoria de integridad de los 8 reports sysrole (protocolo P1) contra rag_benefit_summary.json.

Solo lectura: no reejecuta nada, no toca los reports. Recalcula accuracy, delta_RAG,
McNemar (b/c) e IC95 pareado desde los datos crudos y los compara con el resumen canonico.
Emite ademas el inventario completo de respuestas erroneas (universo de la taxonomia, Fase 4).

Esta es la pieza que hace verificable `rag_benefit_summary.json`: ese fichero se ensamblo a mano
a partir de las recomputaciones del estudio, y aqui se recalcula cada una de sus cifras desde los
8 reports crudos. Si una sola no cuadrase, el script sale con codigo distinto de cero.

Entrada:  <data-root>/results_ablation_p1/*.json  y  <data-root>/aggregates/rag_benefit_summary.json
Salida:   <out-dir>/audit_reports.json

Uso:
    python audit_reports.py [--data-root .] [--out-dir code/output]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

from scipy.stats import binom

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

# (etiqueta, modelo ollama, tag de fichero)
MODELS = [
    ("Llama-3.1-8B", "llama3.1:8b", "llama8b"),
    ("QLoRA neurofisio", "neurofisio-qlora", "qlora"),
    ("Qwen-2.5-7B", "qwen2.5:7b", "qwen7b"),
    ("Med42-8B", "thewindmom/llama3-med42-8b", "med42"),
]

# nombre canonico de los 8 reports crudos publicados en results_ablation_p1/
REPORT_TMPL = "report_{tag}_GPU_Local_Win11_9doc_sysrole_{arm}_RERUN.json"


def report_path(reports: Path, tag: str, arm: str) -> Path:
    return reports / REPORT_TMPL.format(tag=tag, arm=arm)


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    _repo.add_data_root(parser)
    _repo.add_out_dir(parser)
    parser.add_argument("--out", default=None, help="ruta del JSON de auditoria")
    args = parser.parse_args()

    reports = _repo.reports_p1(args)
    summary_path = _repo.aggregates(args) / "rag_benefit_summary.json"
    out_path = Path(args.out) if args.out else _repo.out_dir(args) / "audit_reports.json"

    canon = {r["model"]: r for r in json.load(open(summary_path, encoding="utf-8"))}

    audit: Dict[str, Any] = {"protocolo": "P1_sysrole_anti_rechazo", "modelos": [], "errores": []}
    discrepancias: List[str] = []
    total_errores = 0

    for label, model, tag in MODELS:
        arms = {}
        for arm in ("con", "sin"):
            path = report_path(reports, tag, arm)
            data = json.load(open(path, encoding="utf-8"))
            qs = data["questions"]
            arms[arm] = {q["id"]: q for q in qs}

            # recuento propio, ignorando el summary del fichero
            correct = sum(1 for q in qs if q["es_correcta"])
            acc = correct / len(qs) * 100
            if abs(acc - data["summary"]["accuracy"]) > 1e-6:
                discrepancias.append(
                    f"{tag}/{arm}: accuracy recomputada {acc:.4f} != summary {data['summary']['accuracy']}")

            for q in qs:
                if not q["es_correcta"]:
                    total_errores += 1
                    audit["errores"].append({
                        "modelo": model, "tag": tag, "arm": arm, "id": q["id"],
                        "respuesta_correcta": q["respuesta_correcta"],
                        "opcion_detectada": q["opcion_detectada"],
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

        # cotejo contra el resumen canonico
        ref = canon.get(model)
        if ref is None:
            discrepancias.append(f"{model}: ausente en rag_benefit_summary.json")
            continue
        for field in ("acc_sin_rag", "acc_con_rag", "delta_rag_pp", "b_mejora", "c_empeora", "significativo"):
            if row[field] != ref[field]:
                discrepancias.append(f"{model}.{field}: auditoria={row[field]} canonico={ref[field]}")
        if abs(row["mcnemar_p"] - ref["mcnemar_p"]) > 5e-4:
            discrepancias.append(f"{model}.mcnemar_p: auditoria={row['mcnemar_p']} canonico={ref['mcnemar_p']}")
        if row["paired_ci95"] != ref["paired_ci95"]:
            discrepancias.append(f"{model}.paired_ci95: auditoria={row['paired_ci95']} canonico={ref['paired_ci95']}")

    audit["total_errores"] = total_errores
    audit["discrepancias"] = discrepancias

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)

    print(f"{'modelo':<28}{'sin':>8}{'con':>8}{'delta':>9}{'b':>5}{'c':>5}{'p':>10}  err_con/err_sin")
    for r in audit["modelos"]:
        print(f"{r['label']:<28}{r['acc_sin_rag']:>8.2f}{r['acc_con_rag']:>8.2f}"
              f"{r['delta_rag_pp']:>+9.2f}{r['b_mejora']:>5}{r['c_empeora']:>5}{r['mcnemar_p']:>10.4f}"
              f"  {r['errores_con']}/{r['errores_sin']}")
    print(f"\nTotal respuestas erroneas (universo taxonomia): {total_errores}")
    if discrepancias:
        print(f"\n!! {len(discrepancias)} DISCREPANCIAS vs rag_benefit_summary.json:")
        for d in discrepancias:
            print("  -", d)
        return 1
    print("\nOK: los 8 reports crudos reproducen exactamente rag_benefit_summary.json")
    print(f"Escrito: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
