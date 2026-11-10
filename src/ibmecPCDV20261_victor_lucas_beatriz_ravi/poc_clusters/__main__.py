"""Ponto de entrada: python -m ibmecPCDV20261_victor_lucas_beatriz_ravi.poc_clusters"""

from __future__ import annotations

import argparse

from . import pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="POC de clusterização de municípios (fiança).")
    parser.add_argument(
        "--baixar-tudo",
        action="store_true",
        help="refaz o download de todas as fontes em vez de reaproveitar o que está em data/raw",
    )
    parser.add_argument(
        "--k-maximo",
        type=int,
        default=None,
        help="maior número de clusters testado na varredura",
    )
    argumentos = parser.parse_args()

    extras = {} if argumentos.k_maximo is None else {"k_maximo": argumentos.k_maximo}
    pipeline.executar(forcar_download=argumentos.baixar_tudo, **extras)


if __name__ == "__main__":
    main()
