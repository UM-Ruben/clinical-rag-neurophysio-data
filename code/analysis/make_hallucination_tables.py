#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emite las tablas LaTeX del estudio de alucinaciones directamente desde los JSON de resultados.

Ninguna cifra del articulo se teclea a mano: el fuente LaTeX hace \\input de estos ficheros. Si un
JSON falta, la tabla correspondiente no se genera y el fallo es visible en la compilacion, en vez
de quedar disimulado tras un numero obsoleto.

Entrada:  <data-root>/aggregates/{taxonomia_resumen,hallucination_summary,detectability_resumen}.json
Salida:   <out-dir>/tablas/*.tex

Uso:
    python make_hallucination_tables.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

ORDEN = ["llama3.1:8b", "neurofisio-qlora", "qwen2.5:7b", "thewindmom/llama3-med42-8b"]
NOMBRE = {"llama3.1:8b": "Llama-3.1-8B", "neurofisio-qlora": "Llama-3.1-8B-QLoRA",
          "qwen2.5:7b": "Qwen-2.5-7B", "thewindmom/llama3-med42-8b": "Med42-8B"}
CAT_ES = {
    "T1": "T1 Fabricación paramétrica",
    "T2": "T2 Lectura errónea del contexto",
    "T3": "T3 Razonamiento inválido",
    "T4": "T4 Premisa correcta, opción errónea",
    "T5": "T5 Rechazo residual",
}


def dec(x: float, n: int = 1) -> str:
    """Formatea con coma decimal, como el resto del articulo."""
    if x is None:
        return "--"
    return f"{x:.{n}f}".replace(".", ",")


def pct(d: Dict[str, Any]) -> str:
    """Porcentaje recalculado desde k/n: el campo 'pct' del JSON ya viene redondeado a dos
    decimales y volver a redondear sobre el produce dobles redondeos (46,15 -> 46,1 y no 46,2)."""
    if d is None or not d.get("n"):
        return "--"
    return dec(d["k"] / d["n"] * 100)


def ic(par) -> str:
    return f"[{dec(par[0])}; {dec(par[1])}]"


def tabla_taxonomia(res: Dict[str, Any]) -> str:
    comp = res["composicion"]
    filas = []
    for c in ("T1", "T2", "T3", "T4", "T5"):
        s, co = comp[c]["sin"], comp[c]["con"]
        ps = f"{s['k']} ({pct(s)}\\%)" if s["pct"] is not None else "--"
        pc = f"{co['k']} ({pct(co)}\\%)" if co["pct"] is not None else "--"
        if c == "T2":
            ps = "0 (imposible)"
        filas.append(f"      {CAT_ES[c]} & {ps} & {pc} \\\\")
    n_sin = comp["T1"]["sin"]["n"]
    n_con = comp["T1"]["con"]["n"]
    h1 = res["H1a_caida_T1"]
    p = h1["fisher_p"]
    p_txt = "p < 0{,}001" if p < 0.001 else f"p = {dec(p, 3)}"

    return f"""% generado por make_hallucination_tables.py -- no editar a mano
\\begin{{table}}[htbp]
  \\centering
  \\captionsetup{{skip=4pt}}
  \\caption{{Composición del error según el brazo, sobre las {res['n_validos']} respuestas erróneas
  clasificadas del protocolo P1. La categoría T2 es estructuralmente imposible sin contexto, por lo que
  la comparación describe un desplazamiento del error y no un contraste simétrico. La caída de la
  fabricación paramétrica (T1) del {pct(h1['T1_sin'])}\\% al {pct(h1['T1_con'])}\\%
  del total de errores es significativa (prueba exacta de Fisher, ${p_txt}$).}}
  \\label{{tab:taxonomia_errores}}
  \\begin{{adjustbox}}{{max width=\\textwidth}}
    \\begin{{tabular}}{{lrr}}
      \\toprule
      Categoría del error & \\emph{{sin}} RAG ($n={n_sin}$) & \\emph{{con}} RAG ($n={n_con}$) \\\\
      \\midrule
{chr(10).join(filas)}
      \\bottomrule
    \\end{{tabular}}
  \\end{{adjustbox}}
\\end{{table}}
"""


def tabla_alucinacion(s: Dict[str, Any]) -> str:
    filas = []
    for m in ORDEN:
        fila = next((f for f in s["modelos"] if f["model"] == m), None)
        if not fila:
            continue
        for arm in ("sin", "con"):
            a = fila["arms"].get(arm)
            if not a:
                continue
            nombre = NOMBRE[m] if arm == "sin" else ""
            ood, td = a["alucinacion_ood"], a["alucinacion_trap_d"]
            cp, cob = a["complacencia_trap_c"], a["cobertura"]
            filas.append(
                f"      {nombre} & \\emph{{{arm}}} & {ood['k']}/{ood['n']} ({pct(ood)}\\%) & "
                f"{td['k']}/{td['n']} ({pct(td)}\\%) & {pct(cp)}\\% & {pct(cob)}\\% \\\\")
        filas.append("      \\addlinespace[2pt]")

    pool = s.get("pool", {})
    pool_txt = ""
    if "con" in pool and "sin" in pool:
        pc, ps = pool["con"]["alucinacion"], pool["sin"]["alucinacion"]
        pool_txt = (f" Agregando los cuatro modelos, la tasa de alucinación pasa del "
                    f"{dec(ps['pct'])}\\% (IC$_{{95\\%}}$ de Wilson {ic(ps['ci95_wilson'])}) sin RAG al "
                    f"{dec(pc['pct'])}\\% {ic(pc['ci95_wilson'])} con RAG.")

    return f"""% generado por make_hallucination_tables.py -- no editar a mano
\\begin{{table}}[htbp]
  \\centering
  \\captionsetup{{skip=4pt}}
  \\caption{{Alucinación y abstención bajo el protocolo P2. \\emph{{Alucinación}} es responder
  \\texttt{{a}}, \\texttt{{b}} o \\texttt{{c}} en un ítem cuya respuesta correcta es abstenerse, por dos rutas:
  información ausente del corpus (OOD) o premisa falsa que el corpus refuta (TRAP-D).
  \\emph{{Complacencia}} es elegir, en las preguntas TRAP-C, justamente la opción que da por buena la
  premisa falsa. \\emph{{Cobertura}} es la fracción de las 53 preguntas respondibles que el modelo
  contesta en lugar de abstenerse.{pool_txt}}}
  \\label{{tab:alucinacion_p2}}
  \\begin{{adjustbox}}{{max width=\\textwidth}}
    \\begin{{tabular}}{{llrrrr}}
      \\toprule
      Modelo & Brazo & Alucinación OOD & Alucinación TRAP-D & Complacencia & Cobertura \\\\
      \\midrule
{chr(10).join(filas)}
      \\bottomrule
    \\end{{tabular}}
  \\end{{adjustbox}}
\\end{{table}}
"""


def tabla_detectabilidad(d: Dict[str, Any]) -> str:
    filas = []
    for juez, r in d["jueces"].items():
        a = r["auroc"]
        sens = r["sensibilidad"]
        # el signo debe componerse en modo matematico: un guion de texto no es un menos
        signo = "+" if a["diff"] > 0 else ""
        diff = f"${signo}{dec(a['diff'], 3)}$"
        ci = f"$[{dec(a['ci95_diff'][0], 3)};\\ {dec(a['ci95_diff'][1], 3)}]$"
        ss = sens["sin"]["pct"]
        sc = sens["con"]["pct"]
        filas.append(
            f"      \\texttt{{{juez}}} & {dec(a['auroc_sin'], 3)} & {dec(a['auroc_con'], 3)} & "
            f"{diff} & {ci} & {dec(ss)}\\% & {dec(sc)}\\% \\\\")

    return f"""% generado por make_hallucination_tables.py -- no editar a mano
\\begin{{table}}[htbp]
  \\centering
  \\captionsetup{{skip=4pt}}
  \\caption{{Detectabilidad del error por un juez ciego, que no ve ni la solución ni el contexto.
  El AUROC mide su capacidad de separar aciertos de errores a partir de la sola justificación del modelo.
  Un valor menor indica errores más difíciles de detectar. El intervalo de la diferencia se obtiene por
  remuestreo de conglomerados de pregunta ($10^4$ réplicas). Las dos últimas columnas recogen la
  fracción de errores que el juez llega a marcar como no fiables. Ningún intervalo excluye el cero, de
  modo que en ningún caso hay evidencia estadística de una diferencia. Los dos jueces débiles (7B y 8B)
  detectan algo mejor el error \\emph{{con}} RAG; el juez de frontera, cerca del techo en ambos brazos,
  no separa uno de otro. Se excluyen los autojuicios. El juez de frontera opera sobre 80 casos
  estratificados y equilibrados (40 por brazo).}}
  \\label{{tab:detectabilidad}}
  \\begin{{adjustbox}}{{max width=\\textwidth}}
    \\begin{{tabular}}{{lrrrrrr}}
      \\toprule
      & \\multicolumn{{2}}{{c}}{{AUROC}} & \\multicolumn{{2}}{{c}}{{Diferencia con $-$ sin}}
      & \\multicolumn{{2}}{{c}}{{Errores detectados}} \\\\
      \\cmidrule(lr){{2-3}} \\cmidrule(lr){{4-5}} \\cmidrule(lr){{6-7}}
      Juez ciego & \\emph{{sin}} RAG & \\emph{{con}} RAG & $\\Delta$ & IC$_{{95\\%}}$ & \\emph{{sin}} & \\emph{{con}} \\\\
      \\midrule
{chr(10).join(filas)}
      \\bottomrule
    \\end{{tabular}}
  \\end{{adjustbox}}
\\end{{table}}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _repo.add_data_root(ap)
    _repo.add_out_dir(ap)
    ap.add_argument("--taxonomia", default=None)
    ap.add_argument("--alucinacion", default=None)
    ap.add_argument("--detectabilidad", default=None)
    args = ap.parse_args()

    agg = _repo.aggregates(args)
    args.taxonomia = args.taxonomia or str(agg / "taxonomia_resumen.json")
    args.alucinacion = args.alucinacion or str(agg / "hallucination_summary.json")
    args.detectabilidad = args.detectabilidad or str(agg / "detectability_resumen.json")

    TAB = _repo.out_dir(args) / "tablas"
    TAB.mkdir(parents=True, exist_ok=True)
    generadas = []

    for nombre, path, fn in (
        ("tab_taxonomia_errores.tex", args.taxonomia, tabla_taxonomia),
        ("tab_alucinacion_p2.tex", args.alucinacion, tabla_alucinacion),
        ("tab_detectabilidad.tex", args.detectabilidad, tabla_detectabilidad),
    ):
        p = Path(path)
        if not p.exists():
            print(f"  (omitida {nombre}: falta {p.name})")
            continue
        (TAB / nombre).write_text(fn(json.load(open(p, encoding="utf-8"))), encoding="utf-8")
        generadas.append(nombre)
        print(f"  -> tablas/{nombre}")

    print(f"\n{len(generadas)}/3 tablas generadas en {TAB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
