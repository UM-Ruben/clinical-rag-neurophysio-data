#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Localizacion de los datos publicados. Ninguna ruta absoluta, ninguna ruta de maquina.

Todos los scripts de `analysis/` leen de las carpetas del repositorio de datos y escriben en
`code/output/`. Nunca sobrescriben un fichero publicado: la comparacion entre lo regenerado y lo
publicado la hace `reproduce.py`.

Estructura asumida (la del repositorio recien clonado):

    <raiz>/
      aggregates/                        JSON agregados (lo que se regenera y se coteja)
      annotation/                        CSV de adjudicacion y su clave
      datasets/                          bancos de preguntas (gold standard, TRAP, OOD)
      results_ablation_p1/               los 8 reports crudos del protocolo P1
      results_hallucination_p2_sanitized/ los 24 reports crudos del protocolo P2
      code/
        analysis/   <- este fichero
        inference/
        output/     <- todo lo que se regenera
"""
from __future__ import annotations

import argparse
from pathlib import Path

# code/analysis/_repo.py -> parents[0]=analysis, [1]=code, [2]=raiz del repositorio
REPO_ROOT = Path(__file__).resolve().parents[2]

ABLATION_P1 = "results_ablation_p1"
HALLUCINATION_P2 = "results_hallucination_p2_sanitized"
AGGREGATES = "aggregates"
DATASETS = "datasets"
ANNOTATION = "annotation"

DEFAULT_OUTPUT = REPO_ROOT / "code" / "output"


def add_data_root(ap: argparse.ArgumentParser) -> None:
    """Anade --data-root, con la raiz del repositorio como valor por defecto."""
    ap.add_argument(
        "--data-root",
        default=str(REPO_ROOT),
        help="raiz del repositorio de datos publicado (por defecto, la de este clon)",
    )


def add_out_dir(ap: argparse.ArgumentParser) -> None:
    """Anade --out-dir. Nada se escribe jamas dentro de las carpetas de datos publicadas."""
    ap.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUTPUT),
        help="carpeta de salida de lo regenerado (por defecto, code/output/)",
    )


def data_root(args: argparse.Namespace) -> Path:
    return Path(args.data_root).resolve()


def out_dir(args: argparse.Namespace) -> Path:
    p = Path(args.out_dir).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def aggregates(args: argparse.Namespace) -> Path:
    return data_root(args) / AGGREGATES


def reports_p1(args: argparse.Namespace) -> Path:
    return data_root(args) / ABLATION_P1


def reports_p2(args: argparse.Namespace) -> Path:
    return data_root(args) / HALLUCINATION_P2


def datasets(args: argparse.Namespace) -> Path:
    return data_root(args) / DATASETS


def annotation(args: argparse.Namespace) -> Path:
    return data_root(args) / ANNOTATION
