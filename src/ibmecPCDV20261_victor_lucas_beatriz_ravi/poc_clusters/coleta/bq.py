"""Acesso ao datalake público Base dos Dados no BigQuery.

O projeto de faturamento sai da variável GCP_PROJETO (arquivo .env, fora do repositório).
O acesso gratuito à Base dos Dados tem defasagem: as partições mais recentes existem na
tabela mas retornam vazias, então toda consulta parte do período mais recente LEGÍVEL.
"""

from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

_cliente: bigquery.Client | None = None


def cliente() -> bigquery.Client:
    global _cliente
    if _cliente is None:
        projeto = os.getenv("GCP_PROJETO")
        if not projeto:
            raise RuntimeError(
                "Defina GCP_PROJETO no arquivo .env com o ID do projeto do Google Cloud."
            )
        _cliente = bigquery.Client(project=projeto)
    return _cliente


def consultar(sql: str) -> pd.DataFrame:
    job = cliente().query(sql)
    df = job.result().to_dataframe()
    gb = (job.total_bytes_billed or 0) / 1e9
    if gb > 50:
        raise RuntimeError(f"Consulta cobrou {gb:.1f} GB; revise o filtro de partição.")
    return df


def periodo_mais_recente(tabela: str, ano_minimo: int = 2025) -> tuple[int, int]:
    """Último (ano, mes) com dados legíveis na tabela."""
    sql = f"""
        SELECT ano, mes
        FROM `{tabela}`
        WHERE ano >= {ano_minimo}
        GROUP BY ano, mes
        ORDER BY ano DESC, mes DESC
        LIMIT 1
    """
    df = consultar(sql)
    if df.empty:
        raise ValueError(f"{tabela} não tem dados legíveis a partir de {ano_minimo}.")
    return int(df.loc[0, "ano"]), int(df.loc[0, "mes"])
