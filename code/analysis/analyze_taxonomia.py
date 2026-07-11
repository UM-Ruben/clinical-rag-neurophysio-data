#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analiza el pre-etiquetado de la taxonomia de errores y contrasta la hipotesis H1.

H1: sin RAG el error es sobre todo FABRICACION PARAMETRICA (T1); con RAG el error se desplaza
    hacia la LECTURA ERRONEA DEL CONTEXTO (T2) y el RAZONAMIENTO INVALIDO (T3).

Cautela metodologica que se declara en el articulo: T2 es estructuralmente imposible sin
contexto. Por eso NO se contrasta la composicion completa con una prueba simetrica, sino:
  (a) la caida de la proporcion de T1 entre brazos (prueba exacta de Fisher sobre T1 vs resto);
  (b) la aparicion de T2 con RAG, que es descriptiva por construccion;
  (c) la composicion del error dentro de cada brazo.

Ademas, si existe un segundo etiquetado (segundo juez o adjudicacion humana), calcula el kappa
de Cohen con IC bootstrap.

Entrada:  <data-root>/aggregates/errores_prelabel.json        (pre-etiquetado del juez local)
          <data-root>/aggregates/errores_prelabel_juez2.json   (segundo juez, submuestra)
          <data-root>/aggregates/taxonomia_frontera.json       (adjudicacion externa)
Salida:   <out-dir>/taxonomia_errores.json  (etiquetas consolidadas)
          <out-dir>/taxonomia_resumen.json  (estadistica)

NOTA SOBRE DERECHOS DE AUTOR. En `errores_prelabel.json`, el campo `cita_soporte` recoge el
pasaje de la evidencia que el juez cito para justificar su etiqueta. Siete de esos pasajes
superaban las 50 palabras consecutivas del corpus fuente y se han sustituido por el marcador
`[CITA REDACTADA: N palabras ...]` seguido del documento y la pagina. La redaccion no afecta a
ninguna cifra: `cita_soporte` no entra en ningun calculo, solo se arrastra al consolidado.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402
from stats_hallucination import cohen_kappa, fisher_2x2, kappa_ci, wilson_ci  # noqa: E402

CATS = ["T1", "T2", "T3", "T4", "T5"]
NOMBRE = {
    "T1": "Fabricacion parametrica",
    "T2": "Lectura erronea del contexto",
    "T3": "Razonamiento invalido",
    "T4": "Premisa correcta, opcion erronea",
    "T5": "Rechazo residual",
}


def clave(r: Dict[str, Any]) -> tuple:
    return (r["tag"], r["arm"], r["id"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _repo.add_data_root(ap)
    _repo.add_out_dir(ap)
    ap.add_argument("--prelabel", default=None)
    ap.add_argument("--juez2", default=None, help="segundo etiquetado (submuestra) para el kappa")
    ap.add_argument("--humano", default=None,
                    help="adjudicacion externa que sustituye al pre-etiquetado (humana o de un "
                         "juez de frontera verificado adversarialmente; el nombre del flag se "
                         "conserva por compatibilidad, pero NO implica que la fuente sea humana)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--resumen", default=None)
    args = ap.parse_args()

    agg = _repo.aggregates(args)
    out = _repo.out_dir(args)
    prelabel = Path(args.prelabel) if args.prelabel else agg / "errores_prelabel.json"
    juez2 = Path(args.juez2) if args.juez2 else agg / "errores_prelabel_juez2.json"
    humano = Path(args.humano) if args.humano else agg / "taxonomia_frontera.json"
    out_errores = Path(args.out) if args.out else out / "taxonomia_errores.json"
    out_resumen = Path(args.resumen) if args.resumen else out / "taxonomia_resumen.json"

    base: List[Dict[str, Any]] = json.load(open(prelabel, encoding="utf-8"))
    print(f"Pre-etiquetado: {len(base)} errores")

    # la adjudicacion externa, si existe, SUSTITUYE a la del juez local de 7B
    externa: Dict[tuple, str] = {}
    if humano and humano.exists():
        for r in json.load(open(humano, encoding="utf-8")):
            externa[clave(r)] = r["categoria"]
        print(f"Adjudicacion externa (juez de frontera, verificada adversarialmente): {len(externa)} etiquetas")

    consolidado = []
    for r in base:
        k = clave(r)
        cat = externa.get(k, r.get("categoria"))
        consolidado.append({**r, "categoria_final": cat,
                            "fuente_etiqueta": "juez_frontera_verificado" if k in externa else r.get("origen", "juez")})
    json.dump(consolidado, open(out_errores, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    validos = [r for r in consolidado if r["categoria_final"] in CATS]
    print(f"Etiquetas validas: {len(validos)}/{len(consolidado)}")

    resumen: Dict[str, Any] = {"n_total": len(consolidado), "n_validos": len(validos)}

    # ── composicion por brazo ────────────────────────────────────────────────
    por_brazo: Dict[str, Dict[str, int]] = {"con": defaultdict(int), "sin": defaultdict(int)}
    for r in validos:
        por_brazo[r["arm"]][r["categoria_final"]] += 1

    resumen["composicion"] = {}
    print(f"\n{'categoria':<36}{'sin RAG':>18}{'con RAG':>18}")
    for c in CATS:
        s, cc = por_brazo["sin"][c], por_brazo["con"][c]
        ns, nc = sum(por_brazo["sin"].values()), sum(por_brazo["con"].values())
        resumen["composicion"][c] = {
            "nombre": NOMBRE[c],
            "sin": {"k": s, "n": ns, "pct": round(s / ns * 100, 1) if ns else None},
            "con": {"k": cc, "n": nc, "pct": round(cc / nc * 100, 1) if nc else None},
        }
        ps = f"{s} ({s/ns*100:.1f}%)" if ns else "-"
        pc = f"{cc} ({cc/nc*100:.1f}%)" if nc else "-"
        print(f"{c} {NOMBRE[c]:<32}{ps:>18}{pc:>18}")

    # ── H1(a): la fabricacion parametrica cae con RAG ────────────────────────
    a = por_brazo["con"]["T1"]
    b = sum(por_brazo["con"].values()) - a
    c_ = por_brazo["sin"]["T1"]
    d = sum(por_brazo["sin"].values()) - c_
    p = fisher_2x2(a, b, c_, d)
    lo_c, hi_c = wilson_ci(a, a + b)
    lo_s, hi_s = wilson_ci(c_, c_ + d)
    resumen["H1a_caida_T1"] = {
        "T1_con": {"k": a, "n": a + b, "pct": round(a / (a + b) * 100, 1) if a + b else None,
                   "ci95_wilson": [round(lo_c * 100, 1), round(hi_c * 100, 1)]},
        "T1_sin": {"k": c_, "n": c_ + d, "pct": round(c_ / (c_ + d) * 100, 1) if c_ + d else None,
                   "ci95_wilson": [round(lo_s * 100, 1), round(hi_s * 100, 1)]},
        "fisher_p": round(p, 5), "significativo": p < 0.05,
    }
    print(f"\nH1(a) fabricacion parametrica (T1) como fraccion del error:")
    print(f"  sin RAG: {c_}/{c_+d} = {c_/(c_+d)*100:.1f}%  IC95 [{lo_s*100:.1f}, {hi_s*100:.1f}]")
    print(f"  con RAG: {a}/{a+b} = {a/(a+b)*100:.1f}%  IC95 [{lo_c*100:.1f}, {hi_c*100:.1f}]")
    print(f"  Fisher exacto p = {p:.5f} -> {'significativo' if p < 0.05 else 'no significativo'}")

    # ── H1(b): aparicion de T2 (descriptivo) ─────────────────────────────────
    t2 = por_brazo["con"]["T2"]
    n_con = sum(por_brazo["con"].values())
    resumen["H1b_aparicion_T2"] = {"k": t2, "n": n_con,
                                   "pct": round(t2 / n_con * 100, 1) if n_con else None,
                                   "nota": "T2 es imposible sin contexto; la comparacion es descriptiva"}
    print(f"\nH1(b) lectura erronea del contexto (T2) con RAG: {t2}/{n_con} "
          f"({t2/n_con*100:.1f}% del error con RAG). Imposible por construccion sin RAG.")

    # ── subtags ──────────────────────────────────────────────────────────────
    subt: Dict[str, int] = defaultdict(int)
    for r in validos:
        for s in r.get("subtags", []):
            subt[s] += 1
    resumen["subtags"] = dict(subt)
    if subt:
        print(f"\nSubtags (solo brazo con RAG): {dict(subt)}")

    # ── por modelo ───────────────────────────────────────────────────────────
    por_modelo: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for r in validos:
        por_modelo[r["modelo"]][r["arm"]][r["categoria_final"]] += 1
    resumen["por_modelo"] = {m: {a: dict(v) for a, v in d.items()} for m, d in por_modelo.items()}

    # ── acuerdo entre anotadores ─────────────────────────────────────────────
    acuerdos = {}
    if juez2 and juez2.exists():
        j2 = {clave(r): r.get("categoria") for r in json.load(open(juez2, encoding="utf-8"))}
        j1 = {clave(r): r.get("categoria") for r in base}
        comunes = [k for k in j2 if k in j1 and j1[k] in CATS and j2[k] in CATS]
        if comunes:
            a1 = [j1[k] for k in comunes]
            a2 = [j2[k] for k in comunes]
            acuerdos["juez1_vs_juez2"] = {**kappa_ci(a1, a2),
                                          "acuerdo_bruto": round(sum(x == y for x, y in zip(a1, a2)) / len(a1), 3)}
            print(f"\nKappa juez1 vs juez2 (n={len(comunes)}): "
                  f"{acuerdos['juez1_vs_juez2']['kappa']:.3f} "
                  f"IC95 {[round(x,3) for x in acuerdos['juez1_vs_juez2']['ci95']]}")
    if externa:
        j1 = {clave(r): r.get("categoria") for r in base}
        comunes = [k for k in externa if k in j1 and j1[k] in CATS and externa[k] in CATS]
        if comunes:
            a1 = [j1[k] for k in comunes]
            a2 = [externa[k] for k in comunes]
            acuerdos["juez_local_vs_frontera"] = {**kappa_ci(a1, a2),
                                          "acuerdo_bruto": round(sum(x == y for x, y in zip(a1, a2)) / len(a1), 3)}
            print(f"Kappa juez local vs juez de frontera (n={len(comunes)}): "
                  f"{acuerdos['juez_local_vs_frontera']['kappa']:.3f}")
    resumen["acuerdo"] = acuerdos

    json.dump(resumen, open(out_resumen, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nEscritos: {out_errores}, {out_resumen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
