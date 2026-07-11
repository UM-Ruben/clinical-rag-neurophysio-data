#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Figuras del estudio de alucinaciones. Salida VECTORIAL (PDF) a <out-dir>/figuras/.

  fig_taxonomia_errores.pdf   barras apiladas: distribucion de categorias T1-T5 por brazo (H1)
  fig_roc_detectabilidad.pdf  curvas ROC del juez ciego, con y sin RAG (H2)
  fig_alucinacion_arms.pdf    tasa de alucinacion por ruta (OOD / TRAP-D) y brazo, con IC95 Wilson
  fig_riesgo_cobertura.pdf    punto operativo de cada modelo/brazo (estilo Khan)

Todas las cifras se leen de los JSON publicados. Ninguna esta escrita a mano.

Entrada:  <data-root>/aggregates/{taxonomia_errores,detectability_qwen,hallucination_summary}.json
Salida:   <out-dir>/figuras/*.pdf

Uso:
    python make_hallucination_figures.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402
from stats_hallucination import auroc, wilson_ci  # noqa: E402

LABELS = {"llama3.1:8b": "Llama-3.1-8B", "neurofisio-qlora": "Llama-3.1-8B\nQLoRA",
          "qwen2.5:7b": "Qwen-2.5-7B", "thewindmom/llama3-med42-8b": "Med42-8B"}
ORDEN = ["llama3.1:8b", "neurofisio-qlora", "qwen2.5:7b", "thewindmom/llama3-med42-8b"]

CAT_COLOR = {
    "T1": "#d7191c",  # fabricacion parametrica
    "T2": "#fdae61",  # lectura erronea del contexto
    "T3": "#4575b4",  # razonamiento invalido
    "T4": "#91bfdb",  # premisa correcta, opcion erronea
    "T5": "#999999",  # rechazo residual
}
CAT_NOMBRE = {
    "T1": "T1 Fabricación paramétrica",
    "T2": "T2 Lectura errónea del contexto",
    "T3": "T3 Razonamiento inválido",
    "T4": "T4 Premisa correcta, opción errónea",
    "T5": "T5 Rechazo residual",
}

plt.rcParams.update({"font.family": "serif", "font.size": 11})


def fig_taxonomia(prelabel: Path, out: Path) -> None:
    # 'prelabel' es en realidad taxonomia_errores.json (salida de analyze_taxonomia.py), que
    # conserva el campo 'categoria' original del juez local junto al 'categoria_final' ya
    # adjudicado. Usar 'categoria' aqui reproduciria el pre-etiquetado local descartado.
    datos = json.load(open(prelabel, encoding="utf-8"))
    conteo = defaultdict(lambda: defaultdict(int))
    for r in datos:
        if r.get("categoria_final"):
            conteo[(r["modelo"], r["arm"])][r["categoria_final"]] += 1

    fig, ax = plt.subplots(figsize=(10.5, 6))
    etiquetas, x = [], []
    pos = 0.0
    for m in ORDEN:
        for arm in ("sin", "con"):
            x.append(pos)
            etiquetas.append(f"{LABELS[m]}\n{arm} RAG")
            pos += 1.0
        pos += 0.55

    fondo = np.zeros(len(x))
    for cat in ("T1", "T2", "T3", "T4", "T5"):
        alturas = []
        for m in ORDEN:
            for arm in ("sin", "con"):
                total = sum(conteo[(m, arm)].values()) or 1
                alturas.append(conteo[(m, arm)][cat] / total * 100)
        alturas = np.array(alturas)
        ax.bar(x, alturas, bottom=fondo, width=0.82, color=CAT_COLOR[cat],
               edgecolor="white", linewidth=0.8, label=CAT_NOMBRE[cat])
        for xi, h, b in zip(x, alturas, fondo):
            if h >= 7:
                ax.text(xi, b + h / 2, f"{h:.0f}", ha="center", va="center",
                        fontsize=8.5, color="white", fontweight="bold")
        fondo += alturas

    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, fontsize=8.5)
    ax.set_ylabel("Composición del error (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Cómo cambia la naturaleza del error al introducir RAG\n"
                 "(distribución de las 131 respuestas erróneas del protocolo P1)",
                 fontsize=12, fontweight="bold")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False, fontsize=9)
    ax.grid(axis="y", linestyle=":", alpha=0.45)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("  ->", out.name)


def _roc(scores, labels):
    pares = sorted(zip(scores, labels), key=lambda t: -t[0])
    P = sum(labels)
    N = len(labels) - P
    tpr, fpr = [0.0], [0.0]
    tp = fp = 0
    for s, y in pares:
        tp += y
        fp += 1 - y
        tpr.append(tp / P)
        fpr.append(fp / N)
    return fpr, tpr


def fig_roc(detect: Path, out: Path) -> None:
    # Mismo universo que analyze_detectability.py: se descartan los autojuicios (un modelo
    # puntuando sus propias respuestas) para no arrastrar sesgo de autopreferencia. Sin este
    # filtro la figura mostraria un AUROC distinto del de la tabla, sobre la misma magnitud.
    datos = [r for r in json.load(open(detect, encoding="utf-8"))
             if r.get("prob_correcta") is not None and not r.get("autojuicio")]
    juez = datos[0]["juez"] if datos else "?"
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    estilos = {"sin": ("#999999", "--", "sin RAG"), "con": ("#2c7bb6", "-", "con RAG")}
    for arm, (col, ls, nombre) in estilos.items():
        sub = [r for r in datos if r["arm"] == arm]
        sc = [r["prob_correcta"] for r in sub]
        lb = [1 if r["es_correcta"] else 0 for r in sub]
        a = auroc(sc, lb)
        fpr, tpr = _roc(sc, lb)
        ax.plot(fpr, tpr, color=col, linestyle=ls, linewidth=2.1,
                label=f"{nombre} (AUROC = {a:.3f}, n={len(sub)})")
    ax.plot([0, 1], [0, 1], color="#cccccc", linewidth=1, linestyle=":")
    ax.set_xlabel("Tasa de falsos positivos")
    ax.set_ylabel("Sensibilidad")
    ax.set_title(f"Detectabilidad por un juez ciego ({juez}, sin autojuicios)\n"
                 "Un AUROC menor significa errores más difíciles de detectar",
                 fontsize=12, fontweight="bold")
    ax.legend(loc="lower right", frameon=True, fontsize=9.5)
    ax.grid(linestyle=":", alpha=0.5)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("  ->", out.name)


def fig_alucinacion(summary: Path, out: Path) -> None:
    s = json.load(open(summary, encoding="utf-8"))
    filas = {f["model"]: f for f in s["modelos"]}
    rutas = [("alucinacion_ood", "OOD (información ausente)"),
             ("alucinacion_trap_d", "TRAP-D (premisa falsa refutada por el corpus)")]

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.4), sharey=True)
    for ax, (clave, titulo) in zip(axes, rutas):
        x = np.arange(len(ORDEN))
        w = 0.36
        for off, arm, col in ((-w / 2, "sin", "#bdbdbd"), (w / 2, "con", "#2c7bb6")):
            vals, errs = [], [[], []]
            for m in ORDEN:
                a = filas[m]["arms"].get(arm, {}).get(clave)
                if not a:
                    vals.append(0); errs[0].append(0); errs[1].append(0); continue
                p = a["pct"]; lo, hi = a["ci95_wilson"]
                vals.append(p); errs[0].append(max(0, p - lo)); errs[1].append(max(0, hi - p))
            ax.bar(x + off, vals, w, color=col, edgecolor="white",
                   label=f"{arm} RAG", yerr=errs, capsize=3,
                   error_kw={"elinewidth": 1, "ecolor": "#444"})
            for xi, v in zip(x + off, vals):
                ax.text(xi, v + 1.5, f"{v:.0f}", ha="center", fontsize=8.5)
        ax.set_xticks(x)
        ax.set_xticklabels([LABELS[m].replace("\n", " ") for m in ORDEN], fontsize=8.5, rotation=12)
        ax.set_title(titulo, fontsize=10.5)
        ax.grid(axis="y", linestyle=":", alpha=0.45)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Tasa de alucinación (%)")
    axes[0].set_ylim(0, 108)
    axes[0].legend(loc="upper right", frameon=True, fontsize=9)
    fig.suptitle("Alucinación bajo protocolo con abstención permitida (P2), con IC95% de Wilson",
                 fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("  ->", out.name)


def fig_riesgo_cobertura(summary: Path, out: Path) -> None:
    s = json.load(open(summary, encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    cols = {"llama3.1:8b": "#74add1", "neurofisio-qlora": "#2c7bb6",
            "qwen2.5:7b": "#1a9850", "thewindmom/llama3-med42-8b": "#d7191c"}
    for f in s["modelos"]:
        for arm, marker, alpha in (("sin", "o", 0.45), ("con", "D", 1.0)):
            a = f["arms"].get(arm)
            if not a:
                continue
            cob = a["cobertura"]["pct"]
            rie = a["riesgo_entre_contestadas"]["pct"]
            ax.scatter(cob, rie, s=180, marker=marker, c=cols[f["model"]],
                       edgecolors="white", linewidths=1.2, alpha=alpha, zorder=5)
        ac = f["arms"].get("con"); as_ = f["arms"].get("sin")
        if ac and as_:
            ax.annotate("", xy=(ac["cobertura"]["pct"], ac["riesgo_entre_contestadas"]["pct"]),
                        xytext=(as_["cobertura"]["pct"], as_["riesgo_entre_contestadas"]["pct"]),
                        arrowprops={"arrowstyle": "-|>", "color": cols[f["model"]],
                                    "alpha": 0.7, "linewidth": 1.5, "mutation_scale": 16,
                                    "shrinkA": 9, "shrinkB": 9})
            ax.annotate(f["label"], (ac["cobertura"]["pct"], ac["riesgo_entre_contestadas"]["pct"]),
                        textcoords="offset points", xytext=(10, 7), fontsize=9)
    ax.set_xlabel("Cobertura: preguntas respondibles que el modelo contesta (%)")
    ax.set_ylabel("Riesgo: error entre las contestadas (%)")
    ax.set_title("Punto operativo riesgo-cobertura\n"
                 "Círculo = sin RAG, rombo = con RAG; la flecha marca el efecto del RAG",
                 fontsize=12, fontweight="bold")
    ax.grid(linestyle=":", alpha=0.5)
    ax.margins(x=0.10, y=0.14)
    ax.text(0.015, 0.975, "abajo y a la derecha es mejor:\nmás respuestas y menos error",
            transform=ax.transAxes, ha="left", va="top", fontsize=8,
            style="italic", color="#555")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("  ->", out.name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _repo.add_data_root(ap)
    _repo.add_out_dir(ap)
    ap.add_argument("--prelabel", default=None, help="taxonomia_errores.json (salida consolidada)")
    ap.add_argument("--detect", default=None, help="fichero de juicios del juez ciego")
    ap.add_argument("--summary", default=None, help="hallucination_summary.json")
    args = ap.parse_args()

    agg = _repo.aggregates(args)
    args.prelabel = args.prelabel or str(agg / "taxonomia_errores.json")
    args.detect = args.detect or str(agg / "detectability_qwen.json")
    args.summary = args.summary or str(agg / "hallucination_summary.json")

    DOC = _repo.out_dir(args) / "figuras"
    DOC.mkdir(parents=True, exist_ok=True)
    print("Generando figuras vectoriales:")
    if Path(args.prelabel).exists():
        fig_taxonomia(Path(args.prelabel), DOC / "fig_taxonomia_errores.pdf")
    else:
        print("  (omitida taxonomia: falta", args.prelabel, ")")
    if Path(args.detect).exists():
        fig_roc(Path(args.detect), DOC / "fig_roc_detectabilidad.pdf")
    else:
        print("  (omitida ROC: falta", args.detect, ")")
    if Path(args.summary).exists():
        fig_alucinacion(Path(args.summary), DOC / "fig_alucinacion_arms.pdf")
        fig_riesgo_cobertura(Path(args.summary), DOC / "fig_riesgo_cobertura.pdf")
    else:
        print("  (omitidas 2x2 y riesgo-cobertura: falta", args.summary, ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
