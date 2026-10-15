"""Imobiliárias potenciais ativas por município (CNPJ da Receita Federal via Base dos Dados).

Segue a regra que a Loft usa para identificar imobiliárias: situação cadastral ativa e CNAE
principal em compra e venda (6821801), corretagem no aluguel (6821802) ou gestão e
administração (6822600). O CNAE secundário não filtra, só descreve o perfil: a Loft o usa para
saber se a imobiliária também trabalha com aluguel.
"""

from __future__ import annotations

import pandas as pd

from .. import config
from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw
from . import bq

TABELA = "basedosdados.br_me_cnpj.estabelecimentos"
SITUACAO_ATIVA = "2"
# Corretores de seguros vendem seguro-fiança, o produto que compete com a fiança da Loft.
CNAE_CORRETORES_SEGUROS = "6622300"


def baixar() -> pd.DataFrame:
    ano, mes = bq.periodo_mais_recente(TABELA)
    universo = ", ".join(f"'{c}'" for c in config.CNAES_LOFT.values())
    sql = f"""
        WITH snapshot AS (
            SELECT MAX(data) AS data_snapshot
            FROM `{TABELA}`
            WHERE ano = {ano} AND mes = {mes}
        )
        SELECT
            e.id_municipio,
            (SELECT data_snapshot FROM snapshot) AS data_referencia,
            COUNTIF(e.cnae_fiscal_principal = '{config.CNAES_LOFT["compra_venda"]}') AS imobiliarias,
            COUNTIF(e.cnae_fiscal_principal = '{config.CNAES_LOFT["aluguel"]}') AS corretoras_aluguel,
            COUNTIF(e.cnae_fiscal_principal = '{config.CNAES_LOFT["gestao"]}') AS administradoras,
            COUNTIF(e.cnae_fiscal_principal = '{CNAE_CORRETORES_SEGUROS}') AS corretores_seguros,
            COUNTIF(e.cnae_fiscal_principal IN ({universo})) AS setor_total,
            COUNTIF(
                e.cnae_fiscal_principal IN ({universo})
                AND e.data_inicio_atividade
                >= DATE_SUB((SELECT data_snapshot FROM snapshot), INTERVAL 12 MONTH)
            ) AS setor_novas_12m,
            COUNTIF(
                e.cnae_fiscal_principal IN ({universo})
                AND (
                    e.cnae_fiscal_principal = '{config.CNAES_LOFT["aluguel"]}'
                    OR e.cnae_fiscal_secundaria LIKE '%{config.CNAES_LOFT["aluguel"]}%'
                )
            ) AS setor_faz_aluguel
        FROM `{TABELA}` AS e
        WHERE e.ano = {ano}
          AND e.mes = {mes}
          AND e.situacao_cadastral = '{SITUACAO_ATIVA}'
          AND e.cnae_fiscal_principal IN ({universo}, '{CNAE_CORRETORES_SEGUROS}')
        GROUP BY e.id_municipio
    """
    return bq.consultar(sql)


def carregar(forcar_download: bool = False) -> pd.DataFrame:
    df = None if forcar_download else ler_raw_mais_recente("cnpj_imobiliario_loft_municipio")
    if df is None:
        df = baixar()
        salvar_raw(df, "cnpj_imobiliario_loft_municipio")

    df["id_municipio"] = df["id_municipio"].astype(str)
    data_referencia = str(df["data_referencia"].iloc[0])[:10]
    cnaes = ", ".join(config.CNAES_LOFT.values())

    registrar_fonte(
        "imobiliarias_loft_10k",
        f"Receita Federal - CNPJ, CNAE principal {cnaes} (Base dos Dados)",
        data_referencia,
        "estabelecimentos ativos com o filtro de imobiliária potencial usado pela Loft",
    )
    registrar_fonte(
        "locacao_pct",
        f"Receita Federal - CNPJ, CNAE principal {cnaes} (Base dos Dados)",
        data_referencia,
        "parcela das imobiliárias potenciais com CNAE principal de aluguel (6821802) ou "
        "gestão (6822600)",
    )
    registrar_fonte(
        "imobiliarias_novas_pct",
        f"Receita Federal - CNPJ, CNAE principal {cnaes} (Base dos Dados)",
        data_referencia,
        "abertas nos 12 meses anteriores ao snapshot, sobre o total ativo do setor",
    )
    registrar_fonte(
        "faz_aluguel_pct",
        f"Receita Federal - CNPJ, CNAE principal {cnaes} (Base dos Dados)",
        data_referencia,
        "parcela das imobiliárias potenciais com aluguel (6821802) no CNAE principal ou "
        "secundário; só descreve o perfil, como a Loft faz",
    )
    registrar_fonte(
        "corretores_seguros_10k",
        f"Receita Federal - CNPJ, CNAE {CNAE_CORRETORES_SEGUROS} (Base dos Dados)",
        data_referencia,
        "corretores de seguros ativos: oferta local do seguro-fiança, que é o produto "
        "concorrente direto da fiança",
    )
    return df[
        [
            "id_municipio",
            "imobiliarias",
            "corretoras_aluguel",
            "administradoras",
            "corretores_seguros",
            "setor_total",
            "setor_novas_12m",
            "setor_faz_aluguel",
        ]
    ]
