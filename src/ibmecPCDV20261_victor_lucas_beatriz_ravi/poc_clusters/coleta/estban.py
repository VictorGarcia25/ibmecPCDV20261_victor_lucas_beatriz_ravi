"""Saldo de operações de crédito por município (ESTBAN, Banco Central, via Base dos Dados)."""

from __future__ import annotations

import pandas as pd

from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw
from . import bq

TABELA = "basedosdados.br_bcb_estban.municipio"
VERBETE_CREDITO = "160"
VERBETE_FINANCIAMENTO_IMOBILIARIO = "169"
VERBETE_POUPANCA = "420"
VERBETE_DEPOSITO_PRAZO = "432"


def baixar() -> pd.DataFrame:
    ano, mes = bq.periodo_mais_recente(TABELA)
    sql = f"""
        SELECT
            id_municipio,
            SUM(IF(id_verbete = '{VERBETE_CREDITO}', valor, 0)) AS credito_total,
            SUM(IF(id_verbete = '{VERBETE_FINANCIAMENTO_IMOBILIARIO}', valor, 0))
                AS financiamento_imobiliario,
            SUM(IF(id_verbete = '{VERBETE_POUPANCA}', valor, 0)) AS poupanca,
            SUM(IF(id_verbete = '{VERBETE_DEPOSITO_PRAZO}', valor, 0)) AS deposito_prazo,
            COUNT(DISTINCT instituicao) AS instituicoes
        FROM `{TABELA}`
        WHERE ano = {ano}
          AND mes = {mes}
          AND id_verbete IN (
              '{VERBETE_CREDITO}', '{VERBETE_FINANCIAMENTO_IMOBILIARIO}',
              '{VERBETE_POUPANCA}', '{VERBETE_DEPOSITO_PRAZO}'
          )
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
        "alavancagem",
        "Banco Central - ESTBAN, crédito sobre poupança e depósito a prazo (Base dos Dados)",
        referencia,
        "quanto o município toma emprestado em relação ao que poupa; proxy de risco de "
        "inadimplência, que no SCR só existe por UF",
    )
    registrar_fonte(
        "reserva_per_capita",
        "Banco Central - ESTBAN, verbetes 420 e 432 poupança e depósito a prazo (Base dos Dados)",
        referencia,
        "colchão de reserva local, que é o que sustenta o aluguel quando a renda cai",
    )
    registrar_fonte(
        "credito_per_capita",
        "Banco Central - ESTBAN, verbete 160 operações de crédito (Base dos Dados)",
        referencia,
        "saldo do mês nas agências instaladas no município; municípios sem agência "
        "bancária não aparecem na fonte",
    )
    return df.drop(columns=["ano_referencia", "mes_referencia"])
