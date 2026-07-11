#!/usr/bin/env python3
"""
Análisis de rendimiento de embeddings (Fase R).

Aísla la métrica `retrieval_recall_hit` y compara embeddings
independientemente del LLM generador.

Embeddings evaluados:
  - BAAI/bge-m3
  - intfloat/multilingual-e5-large
  - sentence-transformers/all-MiniLM-L6-v2
  - sentence-transformers/paraphrase-multilingual-mpnet-base-v2

Requiere reports que lleven el campo `retrieval_recall_hit`, que solo emitieron las corridas de la
fase R. Los 8 reports de `results_ablation_p1/` NO lo llevan.

Los que si lo llevan son los de `results_retrieval_exploratory_sanitized/`, y sobre ellos el script
se ejecuta tal cual. Pero ojo con lo que se puede concluir: esos cuatro reports usan todos el mismo
embedding (`BAAI/bge-m3`, el ganador), de modo que el script producira una unica fila y NO permite
rehacer la comparacion entre embeddings. Los reports de los otros tres embeddings del barrido no se
publican; su ranking derivado si, en `exploratory/embeddings_ranking.csv`.

Uso:
  python3 analyze_embeddings.py ../../results_retrieval_exploratory_sanitized/ -o ../output/embedding_analysis.csv
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Tuple


# ── Constantes ────────────────────────────────────────────────────────────────
CANONICAL_EMBEDDINGS = [
    "BAAI/bge-m3",
    "intfloat/multilingual-e5-large",
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
]


# ── Utilidades ────────────────────────────────────────────────────────────────
def resolve_inputs(inputs: List[str]) -> List[str]:
    """Resuelve rutas, carpetas y globs a una lista ordenada de archivos JSON."""
    resolved: List[str] = []
    for item in inputs:
        if any(tok in item for tok in ["*", "?", "["]):
            resolved.extend(glob.glob(item))
        elif os.path.isdir(item):
            resolved.extend(glob.glob(os.path.join(item, "**", "*.json"), recursive=True))
        elif os.path.isfile(item):
            resolved.append(item)
    return sorted(set(resolved))


def load_report(path: str) -> Dict[str, Any] | None:
    """Carga un JSON de reporte y valida campos mínimos."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if "header" not in data or "questions" not in data:
            return None
        return data
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] {path}: {exc}", file=sys.stderr)
        return None


# ── Extracción de métricas por embedding ──────────────────────────────────────
EmbeddingKey = str  # e.g. "BAAI/bge-m3"


def extract_embedding_stats(
    json_files: List[str],
) -> Tuple[
    Dict[EmbeddingKey, List[bool]],          # recall hits per embedding
    Dict[EmbeddingKey, List[float]],         # overlap per embedding
    Dict[EmbeddingKey, Dict[str, int]],      # per-model breakdown
    Dict[EmbeddingKey, int],                 # report count
]:
    """Recorre todos los reportes y agrupa retrieval_recall_hit por embedding."""
    hits_by_emb: Dict[str, List[bool]] = defaultdict(list)
    overlap_by_emb: Dict[str, List[float]] = defaultdict(list)
    model_breakdown: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    report_count: Dict[str, int] = defaultdict(int)

    for fp in json_files:
        data = load_report(fp)
        if data is None:
            continue

        header = data["header"]
        emb = header.get("embedding_model", "unknown")
        model = header.get("model", "unknown")
        report_count[emb] += 1

        for q in data["questions"]:
            hit = q.get("retrieval_recall_hit", False)
            overlap = q.get("retrieval_overlap", 0.0)
            hits_by_emb[emb].append(bool(hit))
            overlap_by_emb[emb].append(float(overlap))
            if hit:
                model_breakdown[emb][model] = model_breakdown[emb].get(model, 0) + 1

    return hits_by_emb, overlap_by_emb, model_breakdown, report_count


# ── Resumen ──────────────────────────────────────────────────────────────────
def build_summary(
    hits_by_emb: Dict[str, List[bool]],
    overlap_by_emb: Dict[str, List[float]],
    model_breakdown: Dict[str, Dict[str, int]],
    report_count: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Construye una tabla resumen ordenada por recall_hit_rate desc."""
    rows: List[Dict[str, Any]] = []
    for emb in sorted(hits_by_emb.keys()):
        hits = hits_by_emb[emb]
        overlaps = overlap_by_emb[emb]
        n = len(hits)
        n_hits = sum(hits)
        hit_rate = n_hits / n * 100 if n else 0.0
        avg_overlap = sum(overlaps) / n if n else 0.0
        top_model = max(model_breakdown[emb].items(), key=lambda x: x[1])[0] if model_breakdown[emb] else "-"
        rows.append({
            "embedding_model": emb,
            "reports": report_count.get(emb, 0),
            "total_questions": n,
            "recall_hits": n_hits,
            "recall_hit_rate_pct": round(hit_rate, 2),
            "avg_overlap": round(avg_overlap, 4),
            "models_tested": ", ".join(sorted(model_breakdown[emb].keys())),
            "top_contributing_model": top_model,
        })
    rows.sort(key=lambda r: r["recall_hit_rate_pct"], reverse=True)
    return rows


# ── Salida ───────────────────────────────────────────────────────────────────
def write_csv(rows: List[Dict[str, Any]], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"CSV guardado: {path}  ({len(rows)} filas)")


def print_table(rows: List[Dict[str, Any]]) -> None:
    """Imprime una tabla legible en consola."""
    if not rows:
        print("Sin datos.")
        return

    print()
    print("=" * 100)
    print("ANÁLISIS DE RENDIMIENTO DE EMBEDDINGS  —  Fase R (Retrieval)")
    print("=" * 100)
    print(f"{'Embedding Model':<55} {'Reports':>7} {'Questions':>9} "
          f"{'Hits':>5} {'Hit Rate%':>9} {'Avg Overlap':>11}")
    print("-" * 100)
    for r in rows:
        print(f"{r['embedding_model']:<55} {r['reports']:>7} {r['total_questions']:>9} "
              f"{r['recall_hits']:>5} {r['recall_hit_rate_pct']:>8.2f}% {r['avg_overlap']:>11.4f}")
    print("-" * 100)

    if rows:
        best = rows[0]
        print(f"\n>> MEJOR EMBEDDING: {best['embedding_model']}")
        print(f"  Recall Hit Rate: {best['recall_hit_rate_pct']:.2f}%")
        print(f"  Overlap medio:   {best['avg_overlap']:.4f}")
        print(f"  Modelos usados:  {best['models_tested']}")
    print()

    # Desglose por modelo
    print("DESGLOSE POR MODELO (recall hits contribuidos a cada embedding):")
    print("-" * 100)
    for r in rows:
        print(f"  {r['embedding_model']}")
        print(f"    Top modelo contribuyente: {r['top_contributing_model']}")
        print(f"    Modelos: {r['models_tested']}")
    print("=" * 100)
    print()


# ── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fase R — Análisis de rendimiento de embeddings aislando retrieval_recall_hit."
    )
    parser.add_argument(
        "inputs", nargs="+",
        help="Rutas a JSON, carpetas o globs (ej: reports/ resultados_cluster/*.json)",
    )
    parser.add_argument("-o", "--output", default="csv_exports/embedding_analysis.csv",
                        help="Ruta CSV de salida (default: csv_exports/embedding_analysis.csv)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="No imprimir tabla en consola")
    args = parser.parse_args()

    json_files = resolve_inputs(args.inputs)
    if not json_files:
        raise SystemExit("No se encontraron archivos JSON.")

    print(f"Archivos JSON encontrados: {len(json_files)}")

    hits, overlaps, breakdown, rcount = extract_embedding_stats(json_files)
    summary = build_summary(hits, overlaps, breakdown, rcount)

    if not summary:
        raise SystemExit("Sin datos de embedding en los reportes.")

    if not args.quiet:
        print_table(summary)

    write_csv(summary, args.output)


if __name__ == "__main__":
    main()
