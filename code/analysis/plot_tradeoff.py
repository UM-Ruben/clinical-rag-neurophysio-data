#!/usr/bin/env python3
"""
Visualización Trade-Off: Precisión (%) vs. Latencia (s).

Genera un scatter plot agrupado / coloreado por:
  • Tamaño del modelo  (7B/8B  vs  70B+)
  • Tipo de hardware    (Local_GPU, Local_CPU, Cluster_CPU, Cluster_GPU)

Los nombres `amdahl` e `ibsen` son las etiquetas de las dos maquinas del clúster de la fase
exploratoria, tal como se citan en el articulo. Aparecen escritas en el campo `device` de la
cabecera de los reports: son etiquetas de dispositivo, no hostnames ni direcciones de red.

Uso:
  python3 plot_tradeoff.py ../../results_ablation_p1/ -o ../output/tradeoff.png
  python3 plot_tradeoff.py ../output/p1_flat.csv -o ../output/tradeoff.png
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List

try:
    import matplotlib
    matplotlib.use("Agg")  # backend no-interactivo para cluster / headless
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError:
    sys.exit("matplotlib es requerido.  Instálalo con:  pip install matplotlib")

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False


# ── Resolución de entradas ────────────────────────────────────────────────────
def resolve_inputs(inputs: List[str]) -> List[str]:
    resolved: List[str] = []
    for item in inputs:
        if any(tok in item for tok in ["*", "?", "["]):
            resolved.extend(glob.glob(item))
        elif os.path.isdir(item):
            resolved.extend(glob.glob(os.path.join(item, "**", "*.json"), recursive=True))
            resolved.extend(glob.glob(os.path.join(item, "**", "*.csv"), recursive=True))
        elif os.path.isfile(item):
            resolved.append(item)
    return sorted(set(resolved))


# ── Clasificadores ────────────────────────────────────────────────────────────
def classify_model_size(param_size: str, model_name: str) -> str:
    """Clasifica el modelo como '7B/8B (Ligero)' o '70B+ (Masivo)'."""
    ps = param_size.lower().strip() if param_size else ""
    mn = model_name.lower()
    for tag in ["70b", "72b", "110b", "180b"]:
        if tag in ps or tag in mn:
            return "70B+ (Masivo)"
    return "7B/8B (Ligero)"


def infer_hardware_type(device: str, mode: str) -> str:
    """Infiere hardware_type a partir de device y mode para reportes legacy."""
    dl = device.lower() if device else ""
    if "cluster" in dl or "amdahl" in dl or "ibsen" in dl:
        return f"Cluster_{mode}"
    return f"Local_{mode}"


# ── Carga de datos ────────────────────────────────────────────────────────────
def _rows_from_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    h = data.get("header", {})
    hw = h.get("hardware_type") or infer_hardware_type(h.get("device", ""), h.get("mode", ""))
    rows: List[Dict[str, Any]] = []
    for q in data.get("questions", []):
        rows.append({
            "model": h.get("model", "?"),
            "param_size": h.get("param_size", ""),
            "hardware_type": hw,
            "latency_seconds": float(q.get("latency_seconds", 0)),
            "is_correct": bool(q.get("es_correcta", False)),
            "timed_out": bool(q.get("timed_out", False)),
        })
    return rows


def _rows_from_csv(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            hw = r.get("hardware_type") or infer_hardware_type(r.get("device", ""), r.get("mode", ""))
            rows.append({
                "model": r.get("model", "?"),
                "param_size": r.get("param_size", ""),
                "hardware_type": hw,
                "latency_seconds": float(r.get("latency_seconds", 0) or 0),
                "is_correct": str(r.get("is_correct", "")).lower() in ("true", "1", "yes"),
                "timed_out": float(r.get("latency_seconds", 0) or 0) >= 700,
            })
    return rows


def load_all_rows(files: List[str]) -> List[Dict[str, Any]]:
    all_rows: List[Dict[str, Any]] = []
    for f in files:
        try:
            if f.endswith(".json"):
                all_rows.extend(_rows_from_json(f))
            elif f.endswith(".csv"):
                all_rows.extend(_rows_from_csv(f))
        except Exception as exc:
            print(f"[WARN] {f}: {exc}", file=sys.stderr)
    return all_rows


# ── Agregación ────────────────────────────────────────────────────────────────
GroupKey = tuple  # (model, hardware_type)


def aggregate_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agrupa por (model, hardware_type) → accuracy media, latency media."""
    buckets: Dict[GroupKey, Dict[str, Any]] = defaultdict(
        lambda: {"correct": 0, "total": 0, "latency_sum": 0.0, "param_size": ""}
    )
    for r in rows:
        key = (r["model"], r["hardware_type"])
        b = buckets[key]
        b["total"] += 1
        b["correct"] += int(r["is_correct"])
        b["latency_sum"] += r["latency_seconds"]
        b["param_size"] = r["param_size"]

    agg: List[Dict[str, Any]] = []
    for (model, hw), b in buckets.items():
        agg.append({
            "model": model,
            "hardware_type": hw,
            "param_size": b["param_size"],
            "latency_seconds": b["latency_sum"] / b["total"] if b["total"] else 0,
            "accuracy_pct": b["correct"] / b["total"] * 100 if b["total"] else 0,
            "n_questions": b["total"],
        })
    return agg


# ── Paleta y marcadores ──────────────────────────────────────────────────────
# Color = tipo de hardware (Local GPU/CPU vs Clúster CPU/GPU)
# Paleta apta para daltonismo, estilo IEEE/Nature
HW_COLORS = {
    "Local_GPU":   "#2c7bb6",   # Azul académico  → máquina local con GPU
    "Local_CPU":   "#74add1",   # Azul claro      → máquina local solo CPU
    "Cluster_CPU": "#d7191c",   # Rojo intenso    → clúster CPU (HPC)
    "Cluster_GPU": "#762a83",   # Púrpura         → clúster con GPU
}
# Marcador = tamaño del modelo
SIZE_MARKERS = {
    "7B/8B (Ligero)": "o",
    "70B+ (Masivo)":  "^",
}


# ── Plot ──────────────────────────────────────────────────────────────────────
def _compute_jitter(agg: List[Dict[str, Any]], tol_x_pct: float = 0.03,
                     tol_y: float = 2.0) -> Dict[int, tuple]:
    """Devuelve offsets (dx, dy) para cada punto que solapa con otro.

    Agrupa puntos cuya latencia difiere < tol_x_pct (relativo al rango X)
    y cuya accuracy difiere < tol_y (puntos porcentuales).
    Dentro de cada grupo se distribuyen en abanico alrededor del centroide
    para que todos sean visibles.
    """
    import math
    if not agg:
        return {}
    x_range = max(r["latency_seconds"] for r in agg) - min(r["latency_seconds"] for r in agg)
    tol_x = max(x_range * tol_x_pct, 0.5)  # mínimo 0.5 s

    # Union-Find ligero para agrupar puntos próximos
    parent = list(range(len(agg)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        parent[find(i)] = find(j)

    for i in range(len(agg)):
        for j in range(i + 1, len(agg)):
            if (abs(agg[i]["latency_seconds"] - agg[j]["latency_seconds"]) < tol_x
                    and abs(agg[i]["accuracy_pct"] - agg[j]["accuracy_pct"]) < tol_y):
                union(i, j)

    groups: Dict[int, list] = defaultdict(list)
    for i in range(len(agg)):
        groups[find(i)].append(i)

    offsets: Dict[int, tuple] = {i: (0.0, 0.0) for i in range(len(agg))}
    spread_x = tol_x * 0.8
    spread_y = tol_y * 1.2
    for members in groups.values():
        if len(members) <= 1:
            continue
        n = len(members)
        for k, idx in enumerate(members):
            angle = 2 * math.pi * k / n
            offsets[idx] = (spread_x * math.cos(angle), spread_y * math.sin(angle))
    return offsets


def plot_scatter(
    agg: List[Dict[str, Any]],
    output_path: str,
    title: str = "Trade-Off: Precisión vs. Latencia",
    sla_line: float | None = 15.0,
) -> None:
    # ── Estilo académico ─────────────────────────────────────────────────────
    if HAS_SEABORN:
        sns.set_theme(style="whitegrid", font_scale=1.1)
    else:
        plt.style.use("seaborn-v0_8-whitegrid")

    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 14,
    })

    fig, ax = plt.subplots(figsize=(14, 8))

    # Calcular offsets para puntos solapados
    jitter = _compute_jitter(agg)

    for i, row in enumerate(agg):
        size_cat = classify_model_size(row["param_size"], row["model"])
        hw = row["hardware_type"]
        color = HW_COLORS.get(hw, "#607D8B")
        marker = SIZE_MARKERS.get(size_cat, "s")
        dx, dy = jitter.get(i, (0.0, 0.0))
        px = row["latency_seconds"] + dx
        py = row["accuracy_pct"] + dy
        ax.scatter(
            px, py,
            c=color,
            marker=marker,
            s=200,
            edgecolors="white",
            linewidths=0.9,
            zorder=5,
        )
        label_text = row["model"].split(":")[0]
        ax.annotate(
            label_text,
            (px, py),
            textcoords="offset points",
            xytext=(8, 6),
            fontsize=9,
            alpha=0.9,
        )

    # Línea SLA
    if sla_line is not None:
        ax.axvline(x=sla_line, color="red", linestyle="--", linewidth=1.2, alpha=0.7)
        ax.text(
            sla_line + 1, ax.get_ylim()[1] * 0.97,
            f"SLA {sla_line:.0f}s",
            color="red", fontsize=9, alpha=0.8, va="top",
        )

    # Leyenda 1: color → hardware
    hw_patches = [
        mpatches.Patch(color=c, label=l)
        for l, c in HW_COLORS.items()
    ]
    # Leyenda 2: marcador → tamaño
    size_handles = [
        plt.Line2D(
            [0], [0],
            marker=m,
            color="#555555",
            linestyle="",
            markersize=11,
            markeredgecolor="white",
            markeredgewidth=0.8,
            label=l,
        )
        for l, m in SIZE_MARKERS.items()
    ]
    legend1 = ax.legend(handles=hw_patches, title="Hardware", loc="upper right", fontsize=10, title_fontsize=10)
    ax.add_artist(legend1)
    ax.legend(handles=size_handles, title="Tamaño de modelo", loc="lower right", fontsize=10, title_fontsize=10)

    ax.set_xlabel("Latencia media (segundos)", fontsize=12)
    ax.set_ylabel("Precisión / Accuracy (%)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylim(-5, 105)

    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    print(f"Gráfico guardado: {output_path}")
    plt.close(fig)


# ── Plot por pregunta individual (no agregado) ───────────────────────────────
def plot_scatter_individual(
    rows: List[Dict[str, Any]],
    output_path: str,
    title: str = "Trade-Off por Pregunta: Correcta vs. Latencia",
    sla_line: float | None = 15.0,
) -> None:
    if HAS_SEABORN:
        sns.set_theme(style="whitegrid", font_scale=1.1)
    else:
        plt.style.use("seaborn-v0_8-whitegrid")

    fig, ax = plt.subplots(figsize=(14, 8))

    for r in rows:
        size_cat = classify_model_size(r["param_size"], r["model"])
        hw = r["hardware_type"]
        color = HW_COLORS.get(hw, "#607D8B")
        marker = SIZE_MARKERS.get(size_cat, "s")
        y_val = 100 if r["is_correct"] else 0
        ax.scatter(
            r["latency_seconds"], y_val,
            c=color, marker=marker, s=50, alpha=0.45, edgecolors="none",
        )

    if sla_line is not None:
        ax.axvline(x=sla_line, color="red", linestyle="--", linewidth=1.2, alpha=0.7)
        ax.text(sla_line + 1, 97, f"SLA {sla_line:.0f}s", color="red", fontsize=9, alpha=0.8, va="top")

    hw_patches = [mpatches.Patch(color=c, label=l) for l, c in HW_COLORS.items()]
    size_handles = [
        plt.Line2D([0], [0], marker=m, color="grey", linestyle="", markersize=10, label=l)
        for l, m in SIZE_MARKERS.items()
    ]
    legend1 = ax.legend(handles=hw_patches, title="Hardware", loc="upper right", fontsize=9)
    ax.add_artist(legend1)
    ax.legend(handles=size_handles, title="Tamaño modelo", loc="center right", fontsize=9)

    ax.set_xlabel("Latencia (segundos)", fontsize=12)
    ax.set_ylabel("Resultado (100 = Correcto, 0 = Incorrecto)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_yticks([0, 100])
    ax.set_yticklabels(["Incorrecto", "Correcto"])

    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    print(f"Gráfico guardado: {output_path}")
    plt.close(fig)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scatter Plot — Trade-off Precisión vs. Latencia agrupado por modelo y hardware."
    )
    parser.add_argument(
        "inputs", nargs="+",
        help="JSON de reportes, CSV flat, carpetas o globs.",
    )
    parser.add_argument("-o", "--output", default="output/plots/tradeoff_precision_vs_latencia.png",
                        help="Ruta del gráfico de salida (default: output/plots/tradeoff_precision_vs_latencia.png)")
    parser.add_argument("--individual", action="store_true",
                        help="Genera además un gráfico por pregunta individual (no agregado)")
    parser.add_argument("--sla", type=float, default=15.0,
                        help="Línea vertical SLA en segundos (default: 15). 0 para desactivar.")
    parser.add_argument("--no-aggregate", action="store_true",
                        help="Solo generar el gráfico individual, sin el agregado")
    args = parser.parse_args()

    files = resolve_inputs(args.inputs)
    if not files:
        raise SystemExit("No se encontraron archivos de entrada.")

    print(f"Archivos encontrados: {len(files)}")
    rows = load_all_rows(files)
    if not rows:
        raise SystemExit("No se pudieron extraer datos de los archivos.")

    print(f"Filas totales: {len(rows)}")
    sla = args.sla if args.sla > 0 else None

    if not args.no_aggregate:
        agg = aggregate_rows(rows)
        print(f"Grupos (modelo × hardware): {len(agg)}")

        # Imprimir tabla resumen en consola
        print(f"\n{'Model':<25} {'Hardware':<15} {'Accuracy%':>9} {'Latency(s)':>10} {'N':>5}")
        print("-" * 68)
        for a in sorted(agg, key=lambda x: x["accuracy_pct"], reverse=True):
            print(f"{a['model']:<25} {a['hardware_type']:<15} "
                  f"{a['accuracy_pct']:>8.1f}% {a['latency_seconds']:>10.1f} {a['n_questions']:>5}")
        print()

        plot_scatter(agg, args.output, sla_line=sla)

    if args.individual or args.no_aggregate:
        ind_path = args.output.replace(".png", "_individual.png")
        plot_scatter_individual(rows, ind_path, sla_line=sla)

    # Sin emoji: en una consola Windows (cp1252) un caracter fuera del mapa hace reventar el
    # print con UnicodeEncodeError y el script termina con codigo != 0 aunque el grafico ya este
    # escrito en disco.
    print("\nVisualizacion completada.")


if __name__ == "__main__":
    main()
