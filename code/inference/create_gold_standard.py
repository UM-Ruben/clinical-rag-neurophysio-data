#!/usr/bin/env python3
"""
Genera el Gold Standard Dataset para el benchmark v2 del TFG.

Lee el banco de preguntas original (test_questions.json) y extrae un
subconjunto aleatorio reproducible de N preguntas (por defecto 50).

Requisitos:
  • Semilla fija (seed=42) → reproducibilidad garantizada.
  • Estructura de salida idéntica al fichero original → compatible
    directamente con evaluate_rag.py --questions_file.

Uso:
  python3 create_gold_standard.py                               # 50 preguntas
  python3 create_gold_standard.py -n 30                         # 30 preguntas
  python3 create_gold_standard.py -i banco_completo.json -n 80  # otra fuente

===============================================================================================
AVISO. Este script NO es ejecutable por terceros y se publica solo para inspeccion.

Necesita el CORPUS y el temario del que se extrajeron las 53 preguntas del Gold Standard. El banco
resultante SI se publica, en `datasets/dataset_gold_standard.json`.
===============================================================================================
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List


SEED = 42
DEFAULT_N = 50
DEFAULT_INPUT = "test_questions.json"
DEFAULT_OUTPUT = "dataset_gold_standard.json"


def validate_question(q: Dict[str, Any], idx: int) -> bool:
    """Valida que una pregunta tenga los campos obligatorios."""
    required = {"id", "pregunta", "respuesta_correcta", "opciones"}
    missing = required - set(q.keys())
    if missing:
        print(f"[WARN] Pregunta índice {idx}: faltan campos {missing}. Se excluye.", file=sys.stderr)
        return False
    opts = q["opciones"]
    if not isinstance(opts, dict) or len(opts) < 2:
        print(f"[WARN] Pregunta id={q.get('id','?')}: menos de 2 opciones. Se excluye.", file=sys.stderr)
        return False
    if q["respuesta_correcta"] not in opts:
        print(f"[WARN] Pregunta id={q.get('id','?')}: respuesta_correcta "
              f"'{q['respuesta_correcta']}' no está en opciones {list(opts.keys())}. Se excluye.",
              file=sys.stderr)
        return False
    return True


def load_questions(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise SystemExit(f"Formato inesperado en {path}: se esperaba una lista JSON.")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un Gold Standard Dataset reproducible para el benchmark RAG."
    )
    parser.add_argument("-i", "--input", default=DEFAULT_INPUT,
                        help=f"Ruta al banco de preguntas original (default: {DEFAULT_INPUT})")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help=f"Ruta del gold standard de salida (default: {DEFAULT_OUTPUT})")
    parser.add_argument("-n", "--num_questions", type=int, default=DEFAULT_N,
                        help=f"Número de preguntas a extraer (default: {DEFAULT_N})")
    parser.add_argument("--seed", type=int, default=SEED,
                        help=f"Semilla aleatoria para reproducibilidad (default: {SEED})")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"No se encontró el fichero de entrada: {input_path}")

    # ── Cargar y validar ──────────────────────────────────────────────────
    raw = load_questions(input_path)
    print(f"Preguntas cargadas de {input_path}: {len(raw)}")

    valid = [q for i, q in enumerate(raw) if validate_question(q, i)]
    print(f"Preguntas válidas tras filtro: {len(valid)}")

    if len(valid) == 0:
        raise SystemExit("No hay preguntas válidas. Revisa tu banco de preguntas.")

    # ── Selección reproducible ────────────────────────────────────────────
    n = args.num_questions
    random.seed(args.seed)

    if len(valid) < n:
        print(
            f"\n⚠ AVISO: El banco solo tiene {len(valid)} preguntas válidas, "
            f"pero se solicitaron {n}.\n"
            f"  → Se incluirán TODAS las {len(valid)} preguntas disponibles.\n"
            f"  → Para alcanzar {n} preguntas, amplía test_questions.json "
            f"y vuelve a ejecutar este script.\n"
        )
        selected = valid[:]
        random.shuffle(selected)
    else:
        selected = random.sample(valid, n)

    # Reasignar IDs secuenciales para el gold standard
    for new_id, q in enumerate(selected, 1):
        q["gold_standard_id"] = new_id
        # Mantener el id original para trazabilidad
        q["original_id"] = q["id"]
        q["id"] = new_id

    # ── Guardar ──────────────────────────────────────────────────────────
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(selected, fh, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"GOLD STANDARD GENERADO")
    print(f"{'='*60}")
    print(f"  Fichero:      {output_path}")
    print(f"  Preguntas:    {len(selected)}")
    print(f"  Seed:         {args.seed}")
    print(f"  Fuente:       {input_path} ({len(raw)} originales)")
    print(f"{'='*60}")
    print(f"\nPara usar en benchmark:")
    print(f"  python3 evaluate_rag.py --questions_file {output_path.name} ...")
    print()


if __name__ == "__main__":
    main()
