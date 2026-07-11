#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilidades estadisticas del estudio de alucinaciones. Semillas fijas, sin dependencias ocultas.

Amplia el marco ya usado en el articulo (Bernoulli, IC95, McNemar) con lo que exige el estudio nuevo:

  wilson_ci          IC95 de proporciones robusto en tasas extremas (0% y 100%), donde el IC
                     normal se sale del [0,1]. Las tasas de alucinacion en OOD son extremas.
  mcnemar_exact      p bilateral exacta sobre los discordantes (identica a la del ablativo).
  auroc              area bajo ROC por rangos, con manejo correcto de empates (los jueces LLM
                     emiten muchas probabilidades repetidas: 0.8, 0.9...).
  bootstrap_auroc_diff  IC de la diferencia AUROC(con) - AUROC(sin), remuestreando POR PREGUNTA
                     (cluster bootstrap): las 53 preguntas se repiten en los 4 modelos y las
                     observaciones no son independientes.
  cohen_kappa        acuerdo entre anotadores, con IC bootstrap.
  holm               correccion de multiplicidad al declarar significancia por modelo.

Autotest:  python stats_hallucination.py --selftest
"""
from __future__ import annotations

import argparse
import math
import random
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

from scipy.stats import binom, fisher_exact

Z95 = 1.959963984540054


# ── proporciones ──────────────────────────────────────────────────────────────

def wilson_ci(k: int, n: int, z: float = Z95) -> Tuple[float, float]:
    """IC de Wilson para una proporcion. Nunca se sale de [0,1], ni con k=0 o k=n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centro - margen), min(1.0, centro + margen))


def wilson_str(k: int, n: int, pct: bool = True) -> str:
    lo, hi = wilson_ci(k, n)
    if pct:
        return "[%.1f, %.1f]" % (lo * 100, hi * 100)
    return "[%.3f, %.3f]" % (lo, hi)


def mcnemar_exact(b: int, c: int) -> float:
    """p exacta bilateral. b = mejora con RAG, c = empeora con RAG."""
    n = b + c
    if n == 0:
        return 1.0
    return float(min(1.0, 2.0 * binom.cdf(min(b, c), n, 0.5)))


def fisher_2x2(a: int, b: int, c: int, d: int) -> float:
    """p bilateral del test exacto de Fisher sobre [[a,b],[c,d]]."""
    return float(fisher_exact([[a, b], [c, d]])[1])


# ── AUROC ─────────────────────────────────────────────────────────────────────

def auroc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """AUROC por el estadistico de Mann-Whitney, con rangos medios en los empates.

    labels: 1 = positivo (respuesta correcta), 0 = negativo (error).
    Devuelve nan si falta alguna de las dos clases.
    """
    pares = [(s, y) for s, y in zip(scores, labels) if s is not None]
    n_pos = sum(y for _, y in pares)
    n_neg = len(pares) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")

    orden = sorted(range(len(pares)), key=lambda i: pares[i][0])
    rangos = [0.0] * len(pares)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and pares[orden[j + 1]][0] == pares[orden[i]][0]:
            j += 1
        rango_medio = (i + j) / 2.0 + 1.0  # rangos 1-based
        for k in range(i, j + 1):
            rangos[orden[k]] = rango_medio
        i = j + 1

    suma_pos = sum(r for r, (_, y) in zip(rangos, pares) if y == 1)
    return (suma_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def bootstrap_auroc_diff(
    datos_con: List[Tuple[float, int, int]],
    datos_sin: List[Tuple[float, int, int]],
    n_boot: int = 10000,
    seed: int = 42,
) -> Dict[str, float]:
    """IC bootstrap de AUROC(con) - AUROC(sin), remuestreando CLUSTERES de pregunta.

    Cada dato es (score, label, id_pregunta). Se remuestrean los ids de pregunta con reemplazo
    y se arrastran todas las observaciones de ese id, en ambos brazos a la vez, porque un mismo
    item aparece en los dos brazos y en los cuatro modelos.
    """
    por_id_con: Dict[int, List[Tuple[float, int]]] = defaultdict(list)
    por_id_sin: Dict[int, List[Tuple[float, int]]] = defaultdict(list)
    for s, y, qid in datos_con:
        por_id_con[qid].append((s, y))
    for s, y, qid in datos_sin:
        por_id_sin[qid].append((s, y))

    ids = sorted(set(por_id_con) | set(por_id_sin))
    a_con = auroc([s for s, _, _ in datos_con], [y for _, y, _ in datos_con])
    a_sin = auroc([s for s, _, _ in datos_sin], [y for _, y, _ in datos_sin])

    rng = random.Random(seed)
    difs: List[float] = []
    for _ in range(n_boot):
        muestra = [ids[rng.randrange(len(ids))] for _ in range(len(ids))]
        sc_c, lb_c, sc_s, lb_s = [], [], [], []
        for qid in muestra:
            for s, y in por_id_con.get(qid, []):
                sc_c.append(s); lb_c.append(y)
            for s, y in por_id_sin.get(qid, []):
                sc_s.append(s); lb_s.append(y)
        ac, as_ = auroc(sc_c, lb_c), auroc(sc_s, lb_s)
        if not (math.isnan(ac) or math.isnan(as_)):
            difs.append(ac - as_)

    difs.sort()
    if not difs:
        return {"auroc_con": a_con, "auroc_sin": a_sin, "diff": float("nan")}
    lo = difs[int(0.025 * len(difs))]
    hi = difs[min(len(difs) - 1, int(0.975 * len(difs)))]
    # p bilateral empirica para H0: diff = 0
    p = 2.0 * min(sum(1 for d in difs if d >= 0), sum(1 for d in difs if d <= 0)) / len(difs)
    return {
        "auroc_con": a_con, "auroc_sin": a_sin, "diff": a_con - a_sin,
        "ci95_diff": [lo, hi], "p_bootstrap": min(1.0, p), "n_boot_validos": len(difs),
    }


# ── acuerdo entre anotadores ──────────────────────────────────────────────────

def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    assert len(a) == len(b) and a, "las dos anotaciones deben tener la misma longitud no nula"
    n = len(a)
    cats = sorted(set(a) | set(b))
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = {c: sum(1 for x in a if x == c) / n for c in cats}
    pb = {c: sum(1 for y in b if y == c) / n for c in cats}
    pe = sum(pa[c] * pb[c] for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def kappa_ci(a: Sequence[str], b: Sequence[str], n_boot: int = 5000, seed: int = 42) -> Dict[str, float]:
    rng = random.Random(seed)
    n = len(a)
    ks: List[float] = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        aa = [a[i] for i in idx]
        bb = [b[i] for i in idx]
        if len(set(aa)) < 2 and len(set(bb)) < 2:
            continue
        ks.append(cohen_kappa(aa, bb))
    ks.sort()
    if not ks:
        return {"kappa": cohen_kappa(a, b)}
    return {
        "kappa": cohen_kappa(a, b),
        "ci95": [ks[int(0.025 * len(ks))], ks[min(len(ks) - 1, int(0.975 * len(ks)))]],
        "n": n,
    }


# ── multiplicidad ─────────────────────────────────────────────────────────────

def holm(pvals: Dict[str, float], alpha: float = 0.05) -> Dict[str, Dict[str, object]]:
    """Correccion de Holm-Bonferroni. Devuelve p ajustada y decision por clave."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out: Dict[str, Dict[str, object]] = {}
    p_prev = 0.0
    for i, (k, p) in enumerate(items):
        p_adj = min(1.0, max(p_prev, (m - i) * p))
        p_prev = p_adj
        out[k] = {"p": p, "p_holm": p_adj, "significativo": p_adj < alpha}
    return out


# ── autotest ──────────────────────────────────────────────────────────────────

def _selftest() -> int:
    fallos = []

    # Wilson: valor de referencia conocido para 0/10 -> [0, 0.2775]
    lo, hi = wilson_ci(0, 10)
    if not (abs(lo) < 1e-9 and abs(hi - 0.27753) < 1e-4):
        fallos.append(f"wilson_ci(0,10) = ({lo:.5f}, {hi:.5f})")
    lo, hi = wilson_ci(10, 10)
    if not (abs(hi - 1.0) < 1e-9 and abs(lo - 0.72247) < 1e-4):
        fallos.append(f"wilson_ci(10,10) = ({lo:.5f}, {hi:.5f})")

    # McNemar: reproduce los valores canonicos del ablativo
    for (b, c), esperado in {(15, 2): 0.0023, (10, 4): 0.1796, (8, 7): 1.0, (13, 6): 0.1671}.items():
        p = mcnemar_exact(b, c)
        if abs(p - esperado) > 5e-4:
            fallos.append(f"mcnemar_exact({b},{c}) = {p:.4f}, esperado {esperado}")

    # AUROC: separacion perfecta = 1.0, inversa = 0.0, todo empatado = 0.5
    if abs(auroc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) - 1.0) > 1e-9:
        fallos.append("auroc separacion perfecta != 1.0")
    if abs(auroc([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1]) - 0.0) > 1e-9:
        fallos.append("auroc separacion inversa != 0.0")
    if abs(auroc([0.5, 0.5, 0.5, 0.5], [0, 0, 1, 1]) - 0.5) > 1e-9:
        fallos.append("auroc con todo empatado != 0.5")
    # empates parciales: scores [1,2,2,3] labels [0,0,1,1] -> AUC = 0.875
    if abs(auroc([1, 2, 2, 3], [0, 0, 1, 1]) - 0.875) > 1e-9:
        fallos.append(f"auroc con empates = {auroc([1,2,2,3],[0,0,1,1])}, esperado 0.875")

    # kappa: acuerdo perfecto = 1, acuerdo al azar ~ 0
    if abs(cohen_kappa(["a", "b", "c"], ["a", "b", "c"]) - 1.0) > 1e-9:
        fallos.append("kappa acuerdo perfecto != 1")
    k = cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"])
    if abs(k) > 1e-9:
        fallos.append(f"kappa azar = {k}, esperado 0")

    # Holm: con 3 p-valores
    h = holm({"x": 0.01, "y": 0.04, "z": 0.03})
    if not (abs(h["x"]["p_holm"] - 0.03) < 1e-9 and h["x"]["significativo"]):
        fallos.append(f"holm x -> {h['x']}")
    if h["y"]["significativo"]:
        fallos.append(f"holm y no deberia ser significativo -> {h['y']}")

    # bootstrap: si los dos brazos son identicos, la diferencia debe rondar 0
    datos = [(0.9, 1, i) for i in range(20)] + [(0.2, 0, i) for i in range(20, 40)]
    r = bootstrap_auroc_diff(datos, list(datos), n_boot=300, seed=1)
    if abs(r["diff"]) > 1e-9:
        fallos.append(f"bootstrap diff con brazos identicos = {r['diff']}")

    if fallos:
        print("AUTOTEST FALLIDO:")
        for f in fallos:
            print("  !", f)
        return 1
    print("AUTOTEST OK: wilson, mcnemar (reproduce el ablativo), auroc (con empates), kappa, holm, bootstrap")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    raise SystemExit(_selftest() if a.selftest else (print(__doc__) or 0))
