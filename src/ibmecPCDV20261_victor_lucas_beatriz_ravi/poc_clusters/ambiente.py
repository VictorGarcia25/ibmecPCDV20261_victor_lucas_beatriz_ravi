"""Carimbo do ambiente: o resultado é o mesmo fora e dentro do contêiner?

O modelo depende dos dados, dos parâmetros, da semente e também do ambiente: versões, biblioteca
de álgebra linear, threads e arquitetura. Cada execução grava um carimbo com esse ambiente e com
os tipos de praça obtidos. Com os carimbos de dois ambientes, a discordância é a parcela de
municípios que mudou de praça entre eles; zero quer dizer reprodução exata.

    python -m ibmecPCDV20261_victor_lucas_beatriz_ravi.poc_clusters.ambiente
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys

import numpy
import pandas as pd
import sklearn

from . import config

ARQUIVO_COMPARACAO = "42_comparacao_ambientes"


def nome_ambiente() -> str:
    return os.getenv("AMBIENTE", "local")


def hash_das_pracas(rotulos: pd.DataFrame) -> str:
    """Hash dos pares município e praça, independente da ordem das linhas."""
    ordenado = rotulos.sort_values("id_municipio")
    texto = "\n".join(f"{m}|{p}" for m, p in zip(ordenado["id_municipio"], ordenado["nome_cluster"]))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


def carimbar(base: pd.DataFrame, silhueta: float, acerto_arvore: float, acerto_baseline: float) -> dict:
    """Grava o carimbo e as praças deste ambiente em reports/tables."""
    ambiente = nome_ambiente()
    rotulos = base[["id_municipio", "nome_cluster"]].copy()
    carimbo = {
        "ambiente": ambiente,
        "python": sys.version.split()[0],
        "scikit_learn": sklearn.__version__,
        "numpy": numpy.__version__,
        "sistema": platform.system(),
        "arquitetura": platform.machine(),
        "threads_omp": os.getenv("OMP_NUM_THREADS", "padrão"),
        "silhueta": round(float(silhueta), 6),
        "acerto_arvore": round(float(acerto_arvore), 4),
        "acerto_baseline": round(float(acerto_baseline), 4),
        "hash_pracas": hash_das_pracas(rotulos),
    }
    (config.DIR_TABELAS / f"40_carimbo_{ambiente}.json").write_text(
        json.dumps(carimbo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    rotulos.to_csv(config.DIR_TABELAS / f"41_pracas_{ambiente}.csv", index=False)
    return carimbo


def discordancia(referencia: pd.DataFrame, outro: pd.DataFrame) -> float:
    """Parcela dos municípios em praças diferentes; compara pelo nome, que não depende da ordem."""
    juntos = referencia.merge(outro, on="id_municipio", suffixes=("_a", "_b"), validate="one_to_one")
    if len(juntos) != len(referencia):
        raise ValueError("Os dois ambientes não têm os mesmos municípios.")
    return float((juntos["nome_cluster_a"] != juntos["nome_cluster_b"]).mean())


def comparar(referencia: str = "local") -> pd.DataFrame:
    """Tabela com todos os ambientes já carimbados, contra o ambiente de referência."""
    linhas = [
        json.loads(arquivo.read_text(encoding="utf-8"))
        for arquivo in sorted(config.DIR_TABELAS.glob("40_carimbo_*.json"))
    ]
    if not linhas:
        raise FileNotFoundError("Nenhum carimbo encontrado: rode o pipeline antes de comparar.")
    tabela = pd.DataFrame(linhas)
    pracas = {
        ambiente: pd.read_csv(
            config.DIR_TABELAS / f"41_pracas_{ambiente}.csv", dtype={"id_municipio": str}
        )
        for ambiente in tabela["ambiente"]
    }
    if referencia not in pracas:
        referencia = str(tabela["ambiente"].iloc[0])
    tabela["discordancia_vs_" + referencia] = [
        round(discordancia(pracas[referencia], pracas[a]), 6) for a in tabela["ambiente"]
    ]
    silhueta = tabela.set_index("ambiente")["silhueta"]
    tabela["diferenca_silhueta"] = [round(abs(s - silhueta[referencia]), 6) for s in tabela["silhueta"]]
    tabela.to_csv(config.DIR_TABELAS / f"{ARQUIVO_COMPARACAO}.csv", index=False)
    return tabela


if __name__ == "__main__":
    print(comparar().to_string(index=False))
