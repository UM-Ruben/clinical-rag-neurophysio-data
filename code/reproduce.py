#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificacion completa del estudio con UN SOLO COMANDO, usando SOLO los datos publicados.

    python code/reproduce.py

No necesita el corpus, ni GPU, ni un servidor Ollama, ni conexion a la red. Regenera desde los
datos crudos publicados todo lo que es regenerable, lo coteja campo a campo con los agregados
publicados, y termina con codigo 0 SOLO si todo coincide.

Lo que hace, en orden:

  1. stats_hallucination.py --selftest
     Autotest de la capa estadistica (Wilson, McNemar, AUROC con empates, kappa, Holm, bootstrap).
     Incluye la reproduccion de los p-valores canonicos del ablativo.

  2. audit_reports.py
     Recomputa desde los 8 reports CRUDOS de P1 las accuracies, los deltas, las celdas b/c de
     McNemar, la p exacta y el IC95 pareado, y los coteja campo a campo con rag_benefit_summary.json.
     Es la pieza que hace verificable ese fichero, que se ensamblo a mano.

  3. resolve_unparsed.py --verificar
     Regenera la resolucion por regla de las 20 respuestas no parseadas y comprueba que reproduce
     exactamente la clasificacion manual de referencia.

  4-11. Regenera cada agregado y lo compara con el publicado (igualdad estructural exacta).

Al final imprime la tabla ARTEFACTO | REGENERADO | PUBLICADO | COINCIDE, y declara explicitamente
lo que NO es reproducible con lo publicado, con su motivo. Nada se omite en silencio.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent          # code/
REPO = HERE.parent                              # raiz del repositorio
ANALYSIS = HERE / "analysis"

OK = "OK"
FALLO = "NO COINCIDE"
DOCUMENTADA = "DIVERGENCIA DOCUMENTADA"


# ── divergencias conocidas ────────────────────────────────────────────────────
# DOS artefactos publicados NO se regeneran bit a bit: detectability_frontera.json (dos covariables
# medidas sobre el texto original, que despues se redacto por derechos de autor) y
# taxonomia_resumen.json (el IC bootstrap de un kappa, que depende del orden de remuestreo).
# Ninguna de las dos divergencias es un error de calculo, y ninguna altera una cifra del articulo.
# Pero tampoco se dan por buenas a ciegas: cada una lleva aqui un validador que comprueba que la
# divergencia es EXACTAMENTE la esperada y nada mas. Si algun dia creciera fuera de ese sobre, el
# validador la devolveria como NO COINCIDE y este script fallaria.
#
# Hubo una TERCERA, ya RESUELTA: detectability_frontera_resumen.json contenia una regresion de
# confusores degenerada (OR=50,498 con se=433,8: separacion completa) y se ha REGENERADO con la
# salvaguarda activa, de modo que ahora reproduce exactamente. Su validador se conserva abajo como
# red de seguridad: si alguien reintrodujera el fichero antiguo, lo detectaria.

def _difs(a: Any, b: Any, ruta: str = "") -> List[str]:
    """Todas las diferencias estructurales entre dos JSON (no solo la primera)."""
    out: List[str] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            out += _difs(a.get(k), b.get(k), f"{ruta}.{k}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += _difs(x, y, f"{ruta}[{i}]")
    elif a != b:
        out.append(ruta)
    return out


def valida_detectability_frontera(regen: Any, pub: Any, root: Path) -> Tuple[bool, str]:
    """Las covariables se midieron sobre el texto ORIGINAL; el publicado esta redactado.

    `len_chars` y `densidad_tecnica` se calcularon cuando el juez vio la justificacion completa.
    Despues, 7 respuestas de los reports de P1 tuvieron que redactarse porque el modelo estaba
    citando >=50 palabras seguidas del corpus con copyright. Al recomputar las covariables sobre
    el texto ya redactado salen valores mas bajos: el texto es literalmente mas corto.

    Es una consecuencia inevitable de la politica de derechos de autor, no un error. Se comprueba
    que la divergencia esta confinada a esos dos campos y SOLO en registros cuya justificacion
    lleva la marca de redaccion; y que ningun campo con valor estadistico (prob_correcta,
    es_correcta, fiable, juez_coincide...) difiere en ningun registro.
    """
    if len(regen) != len(pub):
        return False, f"longitud {len(regen)} vs {len(pub)}"
    permitidos = {"len_chars", "densidad_tecnica"}
    tocados: List[str] = []
    for i, (x, y) in enumerate(zip(regen, pub)):
        for k in sorted(set(x) | set(y)):
            if x.get(k) == y.get(k):
                continue
            if k not in permitidos:
                return False, f"[{i}].{k}: campo no exento ({x.get(k)!r} vs {y.get(k)!r})"
            # la justificacion de ese caso DEBE llevar marca de redaccion
            p = root / "results_ablation_p1" / \
                f"report_{x['tag']}_GPU_Local_Win11_9doc_sysrole_{x['arm']}_RERUN.json"
            q = next(q for q in json.load(open(p, encoding="utf-8"))["questions"] if q["id"] == x["id"])
            if "[CITA REDACTADA" not in q["respuesta_ia"]:
                return False, f"[{i}].{k} difiere pero su justificacion NO esta redactada"
            tocados.append(f"caso {x['caso']} ({x['tag']}/{x['arm']}/id={x['id']}).{k}")
    if not tocados:
        return True, "identico"
    n_reg = len({t.split(')')[0] for t in tocados})
    return True, (f"{len(tocados)} campos en {n_reg} de {len(pub)} registros: "
                  f"{', '.join(sorted(tocados))}. Todos son covariables medidas sobre texto que "
                  f"despues se redacto por derechos de autor. Ningun campo estadistico difiere. "
                  f"No alimentan ninguna cifra publicada: para el juez de frontera la regresion "
                  f"de confusores se omite (clase minoritaria 4 < 5x4 covariables).")


def valida_taxonomia_resumen(regen: Any, pub: Any, root: Path) -> Tuple[bool, str]:
    """El IC bootstrap de un kappa depende del ORDEN de la lista remuestreada.

    `kappa_ci` remuestrea POSICIONES con semilla fija. El kappa puntual es invariante al orden;
    el IC no. El `taxonomia_resumen.json` publicado se calculo con la lista de etiquetas en un
    orden distinto del que produce hoy `taxonomia_frontera.json`, de modo que el bootstrap
    extrajo otras replicas. Se comprueba que el DATO subyacente es identico (mismo kappa a 1e-12,
    misma n, mismo acuerdo bruto) y que el IC coincide con el publicado a los dos decimales con
    los que se reporta.
    """
    difs = _difs(regen, pub)
    esperados = {".acuerdo.juez_local_vs_frontera.ci95[0]",
                 ".acuerdo.juez_local_vs_frontera.ci95[1]"}
    extra = set(difs) - esperados
    if extra:
        return False, f"diferencias fuera del sobre declarado: {sorted(extra)[:4]}"
    if not difs:
        return True, "identico"
    a = regen["acuerdo"]["juez_local_vs_frontera"]
    b = pub["acuerdo"]["juez_local_vs_frontera"]
    if abs(a["kappa"] - b["kappa"]) > 1e-12:
        return False, f"el kappa puntual difiere: {a['kappa']} vs {b['kappa']}"
    if a["n"] != b["n"] or a["acuerdo_bruto"] != b["acuerdo_bruto"]:
        return False, "difieren n o el acuerdo bruto"
    for x, y in zip(a["ci95"], b["ci95"]):
        if abs(x - y) > 0.005:          # los dos decimales con que se reporta
            return False, f"el IC difiere en la cifra reportada: {x:.4f} vs {y:.4f}"
    return True, (f"solo el IC bootstrap de kappa(juez local vs frontera): "
                  f"regenerado [{a['ci95'][0]:.4f}, {a['ci95'][1]:.4f}] vs publicado "
                  f"[{b['ci95'][0]:.4f}, {b['ci95'][1]:.4f}]. El kappa puntual coincide a 1e-12 "
                  f"({a['kappa']:.4f}), igual n ({a['n']}) e igual acuerdo bruto. El IC solo "
                  f"depende del orden de remuestreo y coincide a los dos decimales que se "
                  f"reportan: [0,12; 0,32]. Todo lo demas del fichero es identico.")


def valida_detectability_frontera_resumen(regen: Any, pub: Any, root: Path) -> Tuple[bool, str]:
    """RED DE SEGURIDAD. Esta divergencia YA ESTA RESUELTA: el fichero se ha regenerado.

    `analyze_detectability.py` omite la regresion de confusores cuando la clase minoritaria tiene
    menos de 5 casos por covariable, porque ahi la verosimilitud es casi plana: salen odds ratios
    enormes con errores estandar enormes y p cercanas a 1, que no significan nada. Para el juez de
    frontera hay 4 casos en la clase minoritaria y 4 covariables, asi que la regresion se omite.

    El `detectability_frontera_resumen.json` que se publico en su dia se genero ANTES de que
    existiera esa salvaguarda y arrastraba la regresion degenerada (OR=50,498 con se=433,8:
    separacion completa). Ese fichero SE HA REGENERADO: ahora lleva `regresion_omitida` en lugar de
    `regresion_confusores`, coherente con el articulo, y `compara()` lo da por identico sin llegar a
    llamar a este validador.

    Este validador se conserva como red de seguridad: si alguien reintrodujera la version antigua
    del fichero, aqui se detectaria y se acotaria en lugar de pasar inadvertida.
    """
    difs = _difs(regen, pub)
    esperados = {".jueces.claude-frontera.regresion_omitida",
                 ".jueces.claude-frontera.regresion_confusores"}
    extra = set(difs) - esperados
    if extra:
        return False, f"diferencias fuera del sobre declarado: {sorted(extra)[:4]}"
    if not difs:
        return True, "identico"
    # la version vigente (la de detectability_resumen.json) SI debe omitir la regresion
    vigente = json.load(open(root / "aggregates" / "detectability_resumen.json", encoding="utf-8"))
    cf = vigente["jueces"].get("claude-frontera", {})
    if "regresion_omitida" not in cf:
        return False, ("detectability_resumen.json tampoco omite la regresion: la salvaguarda no "
                       "esta activa donde deberia")
    om = regen["jueces"]["claude-frontera"]["regresion_omitida"]
    return True, (f"el fichero publicado es OBSOLETO: contiene una regresion de confusores que la "
                  f"salvaguarda actual descarta por degenerada (clase minoritaria "
                  f"{om['clase_minoritaria']} < 5 x {om['covariables']} covariables). El resto del "
                  f"fichero (AUROC, IC, sensibilidad, veredicto H2) es identico. Queda SUPERADO por "
                  f"la entrada claude-frontera de detectability_resumen.json, que si reproduce "
                  f"exactamente y es la que alimenta la tabla del articulo.")


# ── lo que NO puede reproducirse con lo publicado, y por que ──────────────────
NO_REPRODUCIBLE: List[Tuple[str, str]] = [
    ("results_ablation_p1/*.json (8 reports)",
     "Son el DATO PRIMARIO, no un derivado: regenerarlos exige reejecutar los 4 modelos sobre "
     "Ollama con los fragmentos recuperados del corpus. Ademas uno de los modelos (neurofisio-qlora) "
     "no se distribuye. Se publican crudos precisamente para que no haya que confiar en nadie: "
     "audit_reports.py recomputa desde ellos todas las cifras del ablativo."),
    ("results_hallucination_p2_sanitized/*.json (24 reports)",
     "Idem: dato primario. Se publican con los fragmentos recuperados sustituidos por su SHA-256 y "
     "su longitud, porque el texto verbatim de esos fragmentos es del corpus con copyright. La "
     "sanitizacion no afecta a ninguna cifra: ningun analisis lee el texto de los fragmentos."),
    ("datasets/dataset_{trap,ood}_validado.json",
     "Los produce inference/build_banks.py a partir de los BORRADORES (trap_raw.json, ood_raw.json), "
     "redactados desde pasajes concretos del corpus y por tanto no distribuibles. El barajado que "
     "elimina el sesgo posicional usa semilla fija (42), de modo que la permutacion aplicada es "
     "auditable leyendo el script contra los bancos publicados."),
    ("datasets/dataset_gold_standard.json",
     "Las 53 preguntas se extrajeron del temario con copyright. El banco se publica; el proceso de "
     "extraccion (inference/create_gold_standard.py) necesita el material fuente."),
    ("aggregates/chunk_provenance.json",
     "Lo produce inference/chunk_provenance.py, que vuelve a trocear los 9 PDF del corpus para "
     "emparejar cada fragmento recuperado con su documento y su pagina. Sin el corpus no hay con que "
     "emparejar. Se publica el resultado, no se puede recomputar."),
    ("aggregates/distractor_efecto.json",
     "NO TIENE SCRIPT PRODUCTOR en el repositorio: se calculo en una sesion de analisis exploratorio "
     "y no llego a consolidarse en un fichero ejecutable. Se declara asi, sin adornos. Sus cifras "
     "(n, k, Fisher, permutacion clusterizada) son verificables a mano desde chunk_provenance.json y "
     "los 8 reports de P1, pero este script NO las recomputa y por tanto NO las avala."),
    ("aggregates/detectability_{qwen,llama}.json",
     "Son los juicios crudos de los dos jueces LLM locales, emitidos por inference/detectability_study.py "
     "contra un servidor Ollama. Dato primario del panel ciego."),
    ("exploratory/embeddings_ranking.csv (barrido de embeddings)",
     "De la fase exploratoria se publican los 4 reports del embedding ganador, en "
     "`results_retrieval_exploratory_sanitized/`, y sobre ellos SI corre analysis/analyze_embeddings.py. "
     "Pero los reports de los otros tres embeddings del barrido no se publican, asi que la COMPARACION "
     "entre embeddings (el ranking) no puede rehacerse: solo se publica su resultado. Queda fuera del "
     "alcance de esta verificacion."),
]


def run(cmd: List[str], titulo: str) -> Tuple[bool, str]:
    print(f"\n{'='*95}\n>>> {titulo}\n{'='*95}")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    salida = (r.stdout or "") + (r.stderr or "")
    print(salida.rstrip())
    return r.returncode == 0, salida


def cargar(p: Path) -> Optional[Any]:
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def primera_diferencia(a: Any, b: Any, ruta: str = "") -> Optional[str]:
    """Devuelve la primera diferencia estructural entre dos JSON, o None si son iguales."""
    if type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return f"{ruta or '<raiz>'}: tipo {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, dict):
        for k in a.keys() | b.keys():
            if k not in a:
                return f"{ruta}.{k}: falta en el REGENERADO"
            if k not in b:
                return f"{ruta}.{k}: falta en el PUBLICADO"
            d = primera_diferencia(a[k], b[k], f"{ruta}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{ruta}: longitud {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = primera_diferencia(x, y, f"{ruta}[{i}]")
            if d:
                return d
        return None
    if isinstance(a, float) or isinstance(b, float):
        if abs(float(a) - float(b)) > 1e-9:
            return f"{ruta}: {a!r} vs {b!r}"
        return None
    if a != b:
        return f"{ruta}: {a!r} vs {b!r}"
    return None


class Tabla:
    def __init__(self, root: Path) -> None:
        self.filas: List[Dict[str, str]] = []
        self.todo_ok = True
        self.root = root

    def compara(self, nombre: str, regenerado: Path, publicado: Path, validador=None) -> None:
        a, b = cargar(regenerado), cargar(publicado)
        if a is None:
            estado, detalle = FALLO, "no se ha regenerado"
        elif b is None:
            estado, detalle = "NO PUBLICADO", "regenerado, pero no hay fichero publicado que cotejar"
        else:
            d = primera_diferencia(a, b)
            if d is None:
                estado, detalle = OK, "identico"
            elif validador is None:
                estado, detalle = FALLO, d
            else:
                # hay divergencia y existe un sobre declarado: se comprueba que no lo desborda
                ok, detalle = validador(a, b, self.root)
                estado = DOCUMENTADA if ok else FALLO
        if estado == FALLO:
            self.todo_ok = False
        self.filas.append({"artefacto": nombre, "regenerado": regenerado.name,
                           "publicado": publicado.name if b is not None else "-",
                           "estado": estado, "detalle": detalle})

    def check(self, nombre: str, ok: bool, detalle: str) -> None:
        if not ok:
            self.todo_ok = False
        self.filas.append({"artefacto": nombre, "regenerado": "(ejecucion)", "publicado": "(autotest)",
                           "estado": OK if ok else FALLO, "detalle": detalle})

    def imprime(self) -> None:
        w = max(len(f["artefacto"]) for f in self.filas) + 2
        MARCA = {OK: "si", DOCUMENTADA: "PARCIAL", "NO PUBLICADO": "--", FALLO: "NO"}
        print("\n\n" + "=" * 110)
        print("TABLA DE VERIFICACION")
        print("=" * 110)
        print(f"{'ARTEFACTO':<{w}}{'REGENERADO':<38}{'PUBLICADO':<38}COINCIDE")
        print("-" * 110)
        for f in self.filas:
            print(f"{f['artefacto']:<{w}}{f['regenerado']:<38}{f['publicado']:<38}{MARCA[f['estado']]}")
        print("-" * 110)

        docs = [f for f in self.filas if f["estado"] == DOCUMENTADA]
        if docs:
            print("\nDIVERGENCIAS DOCUMENTADAS (comprobadas, acotadas, y sin efecto sobre ninguna cifra"
                  " del articulo):")
            for f in docs:
                print(f"\n  * {f['artefacto']}")
                for linea in _envuelve(f["detalle"], 100):
                    print(f"      {linea}")
        for f in self.filas:
            if f["estado"] == FALLO:
                print(f"\n  !! FALLO {f['artefacto']}: {f['detalle']}")
            elif f["estado"] == "NO PUBLICADO":
                print(f"\n  -- {f['artefacto']}: {f['detalle']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", default=str(REPO))
    ap.add_argument("--out-dir", default=None,
                    help="por defecto, un directorio temporal: no se escribe nada en el repositorio")
    ap.add_argument("--keep", action="store_true", help="conserva la salida en code/output/")
    ap.add_argument("--n-boot", type=int, default=10000,
                    help="replicas bootstrap (bajarlo cambia las cifras y hara fallar el cotejo)")
    args = ap.parse_args()

    root = Path(args.data_root).resolve()
    agg = root / "aggregates"

    tmp: Optional[tempfile.TemporaryDirectory] = None
    if args.out_dir:
        out = Path(args.out_dir).resolve()
    elif args.keep:
        out = HERE / "output"
    else:
        tmp = tempfile.TemporaryDirectory(prefix="reproduce_")
        out = Path(tmp.name)
    out.mkdir(parents=True, exist_ok=True)

    py = sys.executable
    base = ["--data-root", str(root), "--out-dir", str(out)]
    t = Tabla(root)

    print("=" * 95)
    print("VERIFICACION DEL ESTUDIO — solo con los datos publicados (sin corpus, sin GPU, sin red)")
    print("=" * 95)
    print(f"  datos:   {root}")
    print(f"  salida:  {out}")

    # ── 1. autotest de la capa estadistica ────────────────────────────────────
    ok, _ = run([py, str(ANALYSIS / "stats_hallucination.py"), "--selftest"],
                "1/8  stats_hallucination.py --selftest")
    t.check("stats (autotest)", ok, "wilson, mcnemar, auroc con empates, kappa, holm, bootstrap")

    # ── 2. auditoria de los 8 reports crudos contra rag_benefit_summary.json ──
    ok, _ = run([py, str(ANALYSIS / "audit_reports.py")] + base,
                "2/8  audit_reports.py  (recomputa P1 desde los reports crudos)")
    t.check("rag_benefit_summary.json", ok,
            "recomputado desde los 8 reports crudos y cotejado campo a campo "
            "(accuracy, delta, b/c, McNemar, IC95)")

    # ── 3. resolucion por regla de las respuestas no parseadas ────────────────
    ok, _ = run([py, str(ANALYSIS / "resolve_unparsed.py")] + base + ["--verificar"],
                "3/8  resolve_unparsed.py --verificar")
    t.check("resolucion_no_parseadas (autotest)", ok,
            "la regla reproduce la clasificacion manual de los 20 casos")
    resol = out / "resolucion_no_parseadas.json"
    t.compara("resolucion_no_parseadas.json", resol, agg / "resolucion_no_parseadas.json")

    # ── 4. agregacion P2, extractor estricto ──────────────────────────────────
    run([py, str(ANALYSIS / "aggregate_hallucination.py")] + base,
        "4/8  aggregate_hallucination.py  (protocolo P2, extractor estricto)")
    t.compara("hallucination_summary.json", out / "hallucination_summary.json",
              agg / "hallucination_summary.json")

    # ── 5. agregacion P2, analisis de sensibilidad ────────────────────────────
    run([py, str(ANALYSIS / "aggregate_hallucination.py")] + base +
        ["--resolucion", str(resol), "--out", str(out / "hallucination_summary_resuelto.json")],
        "5/8  aggregate_hallucination.py --resolucion  (analisis de sensibilidad)")
    t.compara("hallucination_summary_resuelto.json", out / "hallucination_summary_resuelto.json",
              agg / "hallucination_summary_resuelto.json")

    # ── 6. reconstruccion de la adjudicacion externa desde los CSV ────────────
    run([py, str(ANALYSIS / "finalizar_anotacion.py")] + base,
        "6/8  finalizar_anotacion.py  (reconstruye la adjudicacion desde annotation/*.csv)")
    t.compara("taxonomia_frontera.json", out / "taxonomia_frontera.json",
              agg / "taxonomia_frontera.json")
    t.compara("detectability_frontera.json", out / "detectability_frontera.json",
              agg / "detectability_frontera.json", valida_detectability_frontera)

    # ── 7. taxonomia del error (H1) ───────────────────────────────────────────
    run([py, str(ANALYSIS / "analyze_taxonomia.py")] + base,
        "7/8  analyze_taxonomia.py  (H1: como cambia la naturaleza del error con RAG)")
    t.compara("taxonomia_errores.json", out / "taxonomia_errores.json", agg / "taxonomia_errores.json")
    t.compara("taxonomia_resumen.json", out / "taxonomia_resumen.json",
              agg / "taxonomia_resumen.json", valida_taxonomia_resumen)

    # ── 8. detectabilidad del error (H2) ──────────────────────────────────────
    nb = ["--n-boot", str(args.n_boot)]
    run([py, str(ANALYSIS / "analyze_detectability.py")] + base + nb,
        "8/8  analyze_detectability.py  (H2: los tres jueces ciegos)")
    t.compara("detectability_resumen.json", out / "detectability_resumen.json",
              agg / "detectability_resumen.json")

    run([py, str(ANALYSIS / "analyze_detectability.py")] + base + nb +
        ["--juicios", str(agg / "detectability_frontera.json"),
         "--out", str(out / "detectability_frontera_resumen.json")],
        "8/8  analyze_detectability.py  (solo el juez de frontera)")
    t.compara("detectability_frontera_resumen.json", out / "detectability_frontera_resumen.json",
              agg / "detectability_frontera_resumen.json", valida_detectability_frontera_resumen)

    # ── informe ───────────────────────────────────────────────────────────────
    t.imprime()

    print("\n" + "=" * 95)
    print("NO REPRODUCIBLE con lo publicado (declarado, no omitido)")
    print("=" * 95)
    for nombre, motivo in NO_REPRODUCIBLE:
        print(f"\n  {nombre}")
        for linea in _envuelve(motivo, 89):
            print(f"      {linea}")

    n_ok = sum(1 for f in t.filas if f["estado"] == OK)
    n_doc = sum(1 for f in t.filas if f["estado"] == DOCUMENTADA)

    print("\n" + "=" * 95)
    if t.todo_ok:
        print(f"VERIFICACION SUPERADA: {n_ok} artefactos reproducen exactamente lo publicado; "
              f"{n_doc} divergen")
        print(f"dentro del sobre declarado y comprobado que se detalla arriba. Ninguna cifra del "
              f"articulo cambia.")
        print("=" * 95)
        if tmp:
            tmp.cleanup()
        return 0
    print("VERIFICACION FALLIDA: hay artefactos que no reproducen lo publicado (ver arriba).")
    print("=" * 95)
    if tmp:
        tmp.cleanup()
    return 1


def _envuelve(texto: str, ancho: int) -> List[str]:
    palabras, linea, out = texto.split(), "", []
    for p in palabras:
        if len(linea) + len(p) + 1 > ancho:
            out.append(linea)
            linea = p
        else:
            linea = f"{linea} {p}".strip()
    if linea:
        out.append(linea)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
