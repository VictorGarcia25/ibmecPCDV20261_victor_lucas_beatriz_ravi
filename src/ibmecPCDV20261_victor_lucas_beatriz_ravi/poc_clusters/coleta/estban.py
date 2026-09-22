"""Saldo de operações de crédito por município (ESTBAN, Banco Central, via Base dos Dados)."""

from __future__ import annotations

import pandas as pd

from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw
from . import bq

TABELA = "basedosdados.br_bcb_estban.municipio"
VERBETE_CREDITO = "160"
VERBETE_FINANCIAMENTO_IMOBILIARIO = "169"


def baixar() -> pd.DataFrame:
    ano, mes = bq.periodo_mais_recente(TABELA)
    sql = f"""
        SELECT
            id_municipio,
            SUM(IF(id_verbete = '{VERBETE_CREDITO}', valor, 0)) AS credito_total,
            SUM(IF(id_verbete = '{VERBETE_FINANCIAMENTO_IMOBILIARIO}', valor, 0))
                AS financiamento_imobiliario,
            COUNT(DISTINCT instituicao) AS instituicoes
        FROM `{TABELA}`
        WHERE ano = {ano}
          AND mes = {mes}
          AND id_verbete IN ('{VERBETE_CREDITO}', '{VERBETE_FINANCIAMENTO_IMOBILIARIO}')
        GROUP BY id_municipio
    """
    df = bq.consultar(sql)
    df["ano_referencia"] = ano
    df["mes_referencia"] = mes
    return df


def carregar(forcar_download: bool = False) -> pd.DataFrame:
    df = None if forcar_download else ler_raw_mais_recente("estban_municipio")
    if df is None:
        df = baixar()
        salvar_raw(df, "estban_municipio")

    df["id_municipio"] = df["id_municipio"].astype(str)
    referencia = f"{int(df['ano_referencia'].iloc[0])}-{int(df['mes_referencia'].iloc[0]):02d}"
    registrar_fonte(
        "credito_per_capita",
        "Banco Central - ESTBAN, verbete 160 operações de crédito (Base dos Dados)",
        referencia,
        "saldo do mês nas agências instaladas no município; municípios sem agência "
        "bancária não aparecem na fonte",
    )
    return df.drop(columns=["ano_referencia", "mes_referencia"])
