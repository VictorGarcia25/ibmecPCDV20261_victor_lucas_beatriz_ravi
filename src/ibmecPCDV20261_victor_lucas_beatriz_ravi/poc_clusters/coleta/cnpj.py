"""Estabelecimentos imobiliários ativos por município (CNPJ da Receita Federal via Base dos Dados)."""

from __future__ import annotations

import pandas as pd

from .. import config
from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw
from . import bq

TABELA = "basedosdados.br_me_cnpj.estabelecimentos"
SITUACAO_ATIVA = "2"


def baixar() -> pd.DataFrame:
    ano, mes = bq.periodo_mais_recente(TABELA)
    sql = f"""
        WITH snapshot AS (
            SELECT MAX(data) AS data_snapshot
            FROM `{TABELA}`
            WHERE ano = {ano} AND mes = {mes}
        )
        SELECT
            e.id_municipio,
            (SELECT data_snapshot FROM snapshot) AS data_referencia,
            COUNTIF(e.cnae_fiscal_principal = '{config.CNAE_ADMINISTRADORAS}') AS administradoras,
            COUNTIF(e.cnae_fiscal_principal = '{config.CNAE_IMOBILIARIAS}') AS imobiliarias,
            COUNT(*) AS setor_total,
            COUNTIF(
                e.data_inicio_atividade
                >= DATE_SUB((SELECT data_snapshot FROM snapshot), INTERVAL 12 MONTH)
            ) AS setor_novas_12m
        FROM `{TABELA}` AS e
        WHERE e.ano = {ano}
          AND e.mes = {mes}
          AND e.situacao_cadastral = '{SITUACAO_ATIVA}'
          AND e.cnae_fiscal_principal IN (
              '{config.CNAE_ADMINISTRADORAS}', '{config.CNAE_IMOBILIARIAS}'
          )
        GROUP BY e.id_municipio
    """
    return bq.consultar(sql)


def carregar(forcar_download: bool = False) -> pd.DataFrame:
    df = None if forcar_download else ler_raw_mais_recente("cnpj_imobiliario_municipio")
    if df is None:
        df = baixar()
        salvar_raw(df, "cnpj_imobiliario_municipio")

    df["id_municipio"] = df["id_municipio"].astype(str)
    data_referencia = str(df["data_referencia"].iloc[0])[:10]

    registrar_fonte(
        "administradoras_10k",
        f"Receita Federal - CNPJ, CNAE {config.CNAE_ADMINISTRADORAS} (Base dos Dados)",
        data_referencia,
        "estabelecimentos com situação cadastral ativa",
    )
    registrar_fonte(
        "imobiliarias_10k",
        f"Receita Federal - CNPJ, CNAE {config.CNAE_IMOBILIARIAS} (Base dos Dados)",
        data_referencia,
        "estabelecimentos com situação cadastral ativa",
    )
    registrar_fonte(
        "imobiliarias_novas_pct",
        "Receita Federal - CNPJ, CNAE 6821 e 6822 (Base dos Dados)",
        data_referencia,
        "abertas nos 12 meses anteriores ao snapshot, sobre o total ativo do setor",
    )
    return df[
        [
            "id_municipio",
            "administradoras",
            "imobiliarias",
            "setor_total",
            "setor_novas_12m",
        ]
    ]
