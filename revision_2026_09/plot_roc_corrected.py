#!/usr/bin/env python3
"""Regenera la figura ROC de P1 a partir de los juicios publicados y corregidos."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

from analyze_detectability import corrected_labels


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT.parent / "aggregates" / "detectability_qwen.json"


def roc_points(rows: list[dict]) -> tuple[list[float], list[float], float]:
    """Calcula la ROC agrupando los empates de puntuacion en un solo umbral."""
    pairs = sorted(((float(r["prob_correcta"]), bool(r["es_correcta"])) for r in rows),
                   reverse=True)
    positives = sum(label for _, label in pairs)
    negatives = len(pairs) - positives
    if not positives or not negatives:
        raise ValueError("Cada brazo debe contener aciertos y errores")
    fpr, tpr = [0.0], [0.0]
    tp = fp = index = 0
    while index < len(pairs):
        threshold = pairs[index][0]
        while index < len(pairs) and pairs[index][0] == threshold:
            tp += int(pairs[index][1])
            fp += int(not pairs[index][1])
            index += 1
        fpr.append(fp / negatives)
        tpr.append(tp / positives)
    area = sum((fpr[i] - fpr[i - 1]) * (tpr[i] + tpr[i - 1]) / 2
               for i in range(1, len(fpr)))
    return fpr, tpr, area


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--juicios", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=ROOT / "fig_roc_detectabilidad.pdf")
    args = parser.parse_args()
    rows = corrected_labels(json.loads(args.juicios.read_text(encoding="utf-8")))
    rows = [r for r in rows if r.get("prob_correcta") is not None and not r.get("autojuicio")]
    if not rows or rows[0].get("juez") != "qwen2.5:7b":
        raise ValueError("Se esperaba el archivo de juicios del juez Qwen")

    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    for arm, color, style, label in (("sin", "#777777", "--", "without RAG"),
                                      ("con", "#2c7bb6", "-", "with RAG")):
        arm_rows = [r for r in rows if r["arm"] == arm]
        fpr, tpr, area = roc_points(arm_rows)
        ax.plot(fpr, tpr, color=color, linestyle=style, linewidth=2.1,
                label=f"{label} (AUROC = {area:.3f}, n={len(arm_rows)})")
        print(f"{arm}: n={len(arm_rows)}, AUROC={area:.4f}")
    ax.plot([0, 1], [0, 1], color="#cccccc", linewidth=1, linestyle=":")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("Detectability by a blind judge (Qwen-2.5-7B)\nSelf-judgments excluded")
    ax.legend(loc="lower right", frameon=True, fontsize=9.5)
    ax.grid(linestyle=":", alpha=0.5)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, bbox_inches="tight")
    plt.close(fig)
    print(args.out)


if __name__ == "__main__":
    main()
