#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplana uno o varios reports JSON a un CSV con una fila por pregunta.

Herramienta generica: acepta rutas, carpetas o globs. Funciona con cualquiera de los dos
conjuntos de reports publicados.

Los nombres `amdahl` e `ibsen` que aparecen en la inferencia de `hardware_type` son las etiquetas
de las dos maquinas del clúster usadas en la fase exploratoria, tal como se citan en el articulo.
Son etiquetas de dispositivo escritas en la cabecera de los reports, no nombres de red: no hay
hostname, ni IP, ni credencial alguna.

Uso:
    python json_to_csv.py ../../results_ablation_p1/ -o ../output/p1_flat.csv
    python json_to_csv.py "../../results_hallucination_p2_sanitized/*.json" -o ../output/p2_flat.csv
"""
import argparse
import csv
import glob
import json
import os
from typing import Dict, List, Any


def safe_get(dictionary: Dict[str, Any], key: str, default: Any = "") -> Any:
    return dictionary.get(key, default) if isinstance(dictionary, dict) else default


def collect_rows(json_path: str) -> List[Dict[str, Any]]:
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    header = data.get("header", {})
    summary = data.get("summary", {})
    questions = data.get("questions", [])

    # ── Inferir hardware_type si no está presente en el header ────────────
    hardware_type = safe_get(header, "hardware_type")
    if not hardware_type:
        device_lower = str(safe_get(header, "device")).lower()
        mode = str(safe_get(header, "mode"))
        if any(kw in device_lower for kw in ("cluster", "amdahl", "ibsen")):
            hardware_type = f"Cluster_{mode}"
        else:
            hardware_type = f"Local_{mode}"

    # ── Clasificar tamaño del modelo ─────────────────────────────────────
    param_size = str(safe_get(header, "param_size")).lower()
    model_name  = str(safe_get(header, "model")).lower()
    model_size_class = "70B+ (Masivo)" if any(
        t in param_size or t in model_name for t in ("70b", "72b", "110b", "180b")
    ) else "7B/8B (Ligero)"

    rows: List[Dict[str, Any]] = []
    for question in questions:
        latency = float(safe_get(question, "latency_seconds") or 0)
        timed_out = bool(safe_get(question, "timed_out"))

        # ── Lógica SLA ───────────────────────────────────────────────────
        SLA_THRESHOLD = 15.0      # segundos
        TIMEOUT_SENTINEL = 700.0  # ≈ 720s default timeout
        if timed_out or latency >= TIMEOUT_SENTINEL:
            use_case_classification = "Segunda Opinión Asíncrona"
        elif latency <= SLA_THRESHOLD:
            use_case_classification = "Chatbot en Tiempo Real / Triaje"
        else:
            use_case_classification = "Segunda Opinión Asíncrona"

        row = {
            "source_file": os.path.basename(json_path),
            "timestamp": safe_get(header, "timestamp"),
            "model": safe_get(header, "model"),
            "device": safe_get(header, "device"),
            "mode": safe_get(header, "mode"),
            "param_size": safe_get(header, "param_size"),
            "hardware_type": hardware_type,
            "model_size_class": model_size_class,
            "embedding_model": safe_get(header, "embedding_model"),
            "chunk_size": safe_get(header, "chunk_size"),
            "chunk_overlap": safe_get(header, "chunk_overlap"),
            "context_max_tokens": safe_get(header, "context_max_tokens"),
            "retrieved_top_k": safe_get(header, "retrieved_top_k"),
            "question_id": safe_get(question, "id"),
            "question_text": safe_get(question, "pregunta"),
            "correct_option": safe_get(question, "respuesta_correcta"),
            "detected_option": safe_get(question, "opcion_detectada"),
            "is_correct": safe_get(question, "es_correcta"),
            "latency_seconds": latency,
            "timed_out": timed_out,
            "use_case_classification": use_case_classification,
            "answer_confidence": safe_get(question, "answer_confidence"),
            "num_fragmentos": safe_get(question, "num_fragmentos"),
            "retrieval_recall_hit": safe_get(question, "retrieval_recall_hit"),
            "retrieval_overlap": safe_get(question, "retrieval_overlap"),
            "summary_total": safe_get(summary, "total"),
            "summary_processed": safe_get(summary, "processed"),
            "summary_correct": safe_get(summary, "correct"),
            "summary_incorrect": safe_get(summary, "incorrect"),
            "summary_unknown": safe_get(summary, "unknown"),
            "summary_recall_at_k": safe_get(summary, "recall_at_k"),
            "summary_accuracy": safe_get(summary, "accuracy"),
        }
        rows.append(row)

    return rows


def resolve_inputs(inputs: List[str]) -> List[str]:
    resolved: List[str] = []
    for item in inputs:
        if any(token in item for token in ["*", "?", "["]):
            resolved.extend(glob.glob(item))
        elif os.path.isdir(item):
            resolved.extend(glob.glob(os.path.join(item, "*.json")))
        elif os.path.isfile(item):
            resolved.append(item)

    return sorted(set(resolved))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convierte uno o varios reportes JSON de benchmark a un CSV plano por pregunta."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Rutas a JSON, carpetas o patrones glob (ej: reports/*.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="json_reports_flat.csv",
        help="Ruta de salida del CSV",
    )
    args = parser.parse_args()

    json_files = resolve_inputs(args.inputs)
    if not json_files:
        raise SystemExit("No se encontraron archivos JSON de entrada.")

    all_rows: List[Dict[str, Any]] = []
    for json_file in json_files:
        try:
            all_rows.extend(collect_rows(json_file))
        except Exception as error:
            print(f"[WARN] No se pudo procesar {json_file}: {error}")

    if not all_rows:
        raise SystemExit("No se generaron filas; revisa el formato de tus JSON.")

    fieldnames = list(all_rows[0].keys())
    with open(args.output, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"CSV generado: {args.output}")
    print(f"Archivos JSON procesados: {len(json_files)}")
    print(f"Filas escritas: {len(all_rows)}")


if __name__ == "__main__":
    main()
