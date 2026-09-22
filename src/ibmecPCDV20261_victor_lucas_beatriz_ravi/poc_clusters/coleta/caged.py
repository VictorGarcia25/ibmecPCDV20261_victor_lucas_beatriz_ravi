"""Salário de admissão e saldo de emprego por município (Novo CAGED via Base dos Dados)."""

from __future__ import annotations

import pandas as pd

from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw
from . import bq

TABELA = "basedosdados.br_me_caged.microdados_movimentacao"
MESES_JANELA = 12
# Faixa de sanidade do salário mensal declarado, para tirar erro de digitação do microdado.
SALARIO_MINIMO_VALIDO = 100
SALARIO_MAXIMO_VALIDO = 200_000


def baixar() -> pd.DataFrame:
    ano, mes = bq.periodo_mais_recente(TABELA)
    fim = pd.Timestamp(year=ano, month=mes, day=1)
    inicio = fim - pd.DateOffset(months=MESES_JANELA - 1)
    sql = f"""
        WITH janela AS (
            SELECT *
            FROM `{TABELA}`
            WHERE ano BETWEEN {inicio.year} AND {fim.year}
              AND DATE(ano, mes, 1) BETWEEN DATE '{inicio.date()}' AND DATE '{fim.date()}'
        )
        SELECT
            id_municipio,
            COUNTIF(saldo_movimentacao = 1) AS admissoes_12m,
            COUNTIF(saldo_movimentacao = -1) AS desligamentos_12m,
            SUM(saldo_movimentacao) AS saldo_12m,
            AVG(
                CASE
                    WHEN saldo_movimentacao = 1
                     AND salario_mensal BETWEEN {SALARIO_MINIMO_VALIDO} AND {SALARIO_MAXIMO_VALIDO}
                    THEN salario_mensal
                END
            ) AS salario_admissao_medio,
            APPROX_QUANTILES(
                CASE
                    WHEN saldo_movimentacao = 1
                     AND salario_mensal BETWEEN {SALARIO_MINIMO_VALIDO} AND {SALARIO_MAXIMO_VALIDO}
                    THEN salario_mensal
                END, 100
            )[OFFSET(50)] AS salario_admissao_mediano,
            COUNT(DISTINCT FORMAT('%d-%d', ano, mes)) AS meses
        FROM janela
        GROUP BY id_municipio
    """
    df = bq.consultar(sql)
    df["ano_referencia"] = ano
    df["mes_referencia"] = mes
    return df


def carregar(forcar_download: bool = False) -> pd.DataFrame:
    df = None if forcar_download else ler_raw_mais_recente("caged_municipio")
    if df is None:
        df = baixar()
        salvar_raw(df, "caged_municipio")

    df["id_municipio"] = df["id_municipio"].astype(str)
    ano = int(df["ano_referencia"].iloc[0])
    mes = int(df["mes_referencia"].iloc[0])
    referencia = f"{ano}-{mes:02d}"

    registrar_fonte(
        "salario_admissao",
        "Novo CAGED - microdados de movimentação (Base dos Dados)",
        referencia,
        f"média e mediana do salário de admissão nos {MESES_JANELA} meses até {referencia}; "
        f"salários fora de R$ {SALARIO_MINIMO_VALIDO} a R$ {SALARIO_MAXIMO_VALIDO} descartados",
    )
    registrar_fonte(
        "saldo_emprego_pct",
        "Novo CAGED - microdados de movimentação (Base dos Dados)",
        referencia,
        "saldo de 12 meses dividido pelas admissões do período; a RAIS não foi usada como "
        "estoque porque seu dado mais recente é anterior a 2025",
    )
    return df.drop(columns=["ano_referencia", "mes_referencia"])
