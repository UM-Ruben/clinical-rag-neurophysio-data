#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contrasta la hipotesis H2: los errores CON RAG son mas dificiles de detectar que los SIN RAG.

Detector: la probabilidad `prob_correcta` que un juez ciego asigna a cada respuesta.
Etiqueta verdadera: `es_correcta`.
Metrica: AUROC por brazo. Un AUROC menor = el juez distingue peor acierto de error = errores
mas dificiles de detectar.

Contrastes:
  1. AUROC(con) vs AUROC(sin), con IC bootstrap de la diferencia remuestreando CLUSTERES de
     pregunta (las 53 preguntas se repiten en los 4 modelos: las observaciones no son independientes).
  2. Sensibilidad del detector binario `fiable=false` sobre los errores de cada brazo (Fisher).
  3. Confusores: se ajusta una regresion logistica
        marcado_no_fiable ~ con_rag + longitud + densidad_tecnica + cita_el_contexto
     sobre el subconjunto de ERRORES, para comprobar si el efecto del brazo sobrevive al control
     por la verbosidad y la especificidad del texto.
  4. Deteccion independiente: fraccion de errores en los que el juez, razonando por su cuenta,
     elige una opcion distinta de la del modelo evaluado.

Se excluyen por defecto los autojuicios (un modelo juzgando sus propias respuestas), que
introducen sesgo de autopreferencia. Con --incluir-autojuicio se conservan.

Entrada:  <data-root>/aggregates/detectability_{qwen,llama,frontera}.json
Salida:   <out-dir>/detectability_resumen.json

Uso:
    python analyze_detectability.py                     # los tres jueces (fichero canonico)
    python analyze_detectability.py --juicios <ruta>/detectability_frontera.json \
                                    --out <ruta>/detectability_frontera_resumen.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402
from stats_hallucination import auroc, bootstrap_auroc_diff, fisher_2x2, wilson_ci  # noqa: E402

# orden canonico de los jueces: los dos locales primero (su interseccion define `entre_jueces`),
# el de frontera despues.
JUECES_POR_DEFECTO = ("detectability_qwen.json", "detectability_llama.json",
                      "detectability_frontera.json")


def logistic(X: np.ndarray, y: np.ndarray, nombres: List[str]) -> Dict[str, Any]:
    """Regresion logistica con errores estandar de Wald (matriz de informacion observada)."""
    from sklearn.linear_model import LogisticRegression

    modelo = LogisticRegression(penalty=None, max_iter=2000)
    modelo.fit(X, y)
    coef = np.concatenate([modelo.intercept_, modelo.coef_[0]])

    Xd = np.hstack([np.ones((X.shape[0], 1)), X])
    p = 1.0 / (1.0 + np.exp(-Xd @ coef))
    W = np.diag(p * (1 - p))
    try:
        cov = np.linalg.inv(Xd.T @ W @ Xd)
        se = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        se = np.full(len(coef), float("nan"))

    out = {}
    for i, nom in enumerate(["intercepto"] + nombres):
        z = coef[i] / se[i] if se[i] and not math.isnan(se[i]) else float("nan")
        p_val = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2)))) if not math.isnan(z) else float("nan")
        out[nom] = {
            "coef": round(float(coef[i]), 4),
            "se": round(float(se[i]), 4) if not math.isnan(se[i]) else None,
            "odds_ratio": round(float(np.exp(coef[i])), 3),
            "p": round(float(p_val), 4) if not math.isnan(p_val) else None,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _repo.add_data_root(ap)
    _repo.add_out_dir(ap)
    ap.add_argument("--juicios", nargs="+", default=None,
                    help="uno o mas ficheros de juez (por defecto, los tres de aggregates/)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--incluir-autojuicio", action="store_true")
    ap.add_argument("--n-boot", type=int, default=10000)
    args = ap.parse_args()

    agg = _repo.aggregates(args)
    juicios = args.juicios or [str(agg / f) for f in JUECES_POR_DEFECTO]
    out_path = Path(args.out) if args.out else _repo.out_dir(args) / "detectability_resumen.json"

    resumen: Dict[str, Any] = {"jueces": {}}

    for path in juicios:
        datos = json.load(open(path, encoding="utf-8"))
        juez = datos[0]["juez"] if datos else "?"
        n_bruto = len(datos)
        if not args.incluir_autojuicio:
            datos = [r for r in datos if not r.get("autojuicio")]
        datos = [r for r in datos if r.get("prob_correcta") is not None]

        print(f"\n{'='*70}\nJUEZ: {juez}  ({len(datos)} juicios utiles de {n_bruto})")

        res: Dict[str, Any] = {"n_utiles": len(datos), "n_bruto": n_bruto}

        # ── 1. AUROC por brazo y diferencia ──────────────────────────────────
        d_con = [(r["prob_correcta"], 1 if r["es_correcta"] else 0, r["id"])
                 for r in datos if r["arm"] == "con"]
        d_sin = [(r["prob_correcta"], 1 if r["es_correcta"] else 0, r["id"])
                 for r in datos if r["arm"] == "sin"]
        boot = bootstrap_auroc_diff(d_con, d_sin, n_boot=args.n_boot, seed=42)
        res["auroc"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in boot.items()}
        res["auroc"]["ci95_diff"] = [round(x, 4) for x in boot["ci95_diff"]]

        print(f"  AUROC sin RAG : {boot['auroc_sin']:.4f}  (n={len(d_sin)})")
        print(f"  AUROC con RAG : {boot['auroc_con']:.4f}  (n={len(d_con)})")
        print(f"  diferencia con-sin: {boot['diff']:+.4f}  IC95 bootstrap "
              f"[{boot['ci95_diff'][0]:+.4f}, {boot['ci95_diff'][1]:+.4f}]  p={boot['p_bootstrap']:.4f}")
        veredicto = ("los errores CON RAG son mas dificiles de detectar"
                     if boot["diff"] < 0 else "los errores SIN RAG son mas dificiles de detectar")
        sig = boot["ci95_diff"][1] < 0 or boot["ci95_diff"][0] > 0
        print(f"  -> {veredicto} ({'significativo' if sig else 'no significativo'})")
        res["H2_veredicto"] = {"direccion": veredicto, "significativo": bool(sig)}

        # ── 2. sensibilidad del detector binario sobre los errores ───────────
        err = {arm: [r for r in datos if r["arm"] == arm and not r["es_correcta"]] for arm in ("con", "sin")}
        det = {arm: sum(1 for r in v if r.get("fiable") is False) for arm, v in err.items()}
        res["sensibilidad"] = {}
        for arm in ("sin", "con"):
            n, k = len(err[arm]), det[arm]
            lo, hi = wilson_ci(k, n) if n else (0, 1)
            res["sensibilidad"][arm] = {"errores": n, "marcados_no_fiables": k,
                                        "pct": round(k / n * 100, 1) if n else None,
                                        "ci95_wilson": [round(lo * 100, 1), round(hi * 100, 1)]}
            print(f"  errores {arm} RAG marcados como NO fiables: {k}/{n} "
                  f"({k/n*100:.1f}% IC95 [{lo*100:.1f}, {hi*100:.1f}])" if n else "")
        if err["con"] and err["sin"]:
            p = fisher_2x2(det["con"], len(err["con"]) - det["con"],
                           det["sin"], len(err["sin"]) - det["sin"])
            res["sensibilidad"]["fisher_p"] = round(p, 5)
            print(f"  Fisher exacto de la diferencia de sensibilidad: p = {p:.5f}")

        # ── 3. deteccion independiente (el juez elige otra opcion) ───────────
        res["desacuerdo_en_errores"] = {}
        for arm in ("sin", "con"):
            sub = [r for r in err[arm] if r.get("juez_coincide") is not None]
            if not sub:
                continue
            k = sum(1 for r in sub if not r["juez_coincide"])
            lo, hi = wilson_ci(k, len(sub))
            res["desacuerdo_en_errores"][arm] = {
                "k": k, "n": len(sub), "pct": round(k / len(sub) * 100, 1),
                "ci95_wilson": [round(lo * 100, 1), round(hi * 100, 1)]}
            print(f"  el juez propone otra opcion en {k}/{len(sub)} de los errores {arm} RAG "
                  f"({k/len(sub)*100:.1f}%)")

        # ── 4. confusores ────────────────────────────────────────────────────
        errores = err["con"] + err["sin"]
        errores = [r for r in errores if r.get("fiable") is not None]
        if len(errores) >= 30 and len({r["arm"] for r in errores}) == 2:
            y = np.array([1 if r["fiable"] is False else 0 for r in errores])
            if 0 < y.sum() < len(y):
                X = np.array([[1.0 if r["arm"] == "con" else 0.0,
                               r["len_chars"] / 1000.0,
                               r["densidad_tecnica"],
                               1.0 if r["cita_el_contexto"] else 0.0] for r in errores])
                nombres = ["con_rag", "longitud_kchars", "densidad_tecnica", "cita_el_contexto"]
                # Una columna constante hace singular la matriz de informacion: los errores estandar
                # salen infinitos, los p a None, y el veredicto "no sobrevive al control" seria una
                # afirmacion sobre datos que no existen. Se descarta la columna y se dice.
                vivas = [i for i in range(X.shape[1]) if X[:, i].std() > 1e-9]
                muertas = [nombres[i] for i in range(X.shape[1]) if i not in vivas]
                if muertas:
                    print(f"  AVISO: covariables constantes, excluidas de la regresion: {muertas}")
                    res["covariables_constantes"] = muertas
                if "con_rag" not in [nombres[i] for i in vivas]:
                    print("  (regresion omitida: el brazo no varia)")
                    resumen["jueces"][juez] = res
                    continue
                X = X[:, vivas]
                nombres = [nombres[i] for i in vivas]
                # Regla de dedo: al menos 5 eventos por covariable en la clase minoritaria. Por debajo,
                # la verosimilitud es casi plana o hay separacion, y salen OR astronomicos con p=1.
                minoritaria = int(min(y.sum(), len(y) - y.sum()))
                if minoritaria < 5 * X.shape[1]:
                    print(f"  (regresion OMITIDA: solo {minoritaria} casos en la clase minoritaria "
                          f"para {X.shape[1]} covariables; habria separacion y los OR no serian "
                          f"interpretables)")
                    res["regresion_omitida"] = {"clase_minoritaria": minoritaria,
                                                "covariables": X.shape[1]}
                    resumen["jueces"][juez] = res
                    continue
                res["regresion_confusores"] = logistic(X, y, nombres)
                print("\n  Regresion logistica: marcado_no_fiable ~ brazo + confusores "
                      f"(n={len(errores)} errores)")
                for nom, v in res["regresion_confusores"].items():
                    if nom == "intercepto":
                        continue
                    print(f"    {nom:<20} OR={v['odds_ratio']:>7.3f}  p={v['p']}")
                orc = res["regresion_confusores"]["con_rag"]
                print(f"    -> el efecto del RAG sobre la deteccion "
                      f"{'sobrevive' if (orc['p'] or 1) < 0.05 else 'NO sobrevive'} al control por "
                      f"longitud, densidad tecnica y cita del contexto")
            else:
                print("  (regresion omitida: la variable respuesta no tiene ambas clases)")
        else:
            print("  (regresion omitida: muestra insuficiente)")

        resumen["jueces"][juez] = res

    # ── acuerdo entre jueces sobre las respuestas comunes ────────────────────
    if len(juicios) >= 2:
        mapas = []
        for path in juicios:
            d = json.load(open(path, encoding="utf-8"))
            mapas.append({(r["tag"], r["arm"], r["id"]): r for r in d if r.get("prob_correcta") is not None})
        comunes = set(mapas[0]) & set(mapas[1])
        if comunes:
            a = [mapas[0][k]["prob_correcta"] for k in comunes]
            b = [mapas[1][k]["prob_correcta"] for k in comunes]
            r = float(np.corrcoef(a, b)[0, 1]) if len(comunes) > 2 else float("nan")
            acuerdo_bin = sum(1 for k in comunes
                              if mapas[0][k].get("fiable") == mapas[1][k].get("fiable")) / len(comunes)
            resumen["entre_jueces"] = {"n_comunes": len(comunes),
                                       "correlacion_prob": round(r, 3),
                                       "acuerdo_binario_fiable": round(acuerdo_bin, 3)}
            print(f"\nEntre jueces (n={len(comunes)}): correlacion de prob_correcta r={r:.3f}, "
                  f"acuerdo binario {acuerdo_bin*100:.1f}%")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(resumen, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nEscrito: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
