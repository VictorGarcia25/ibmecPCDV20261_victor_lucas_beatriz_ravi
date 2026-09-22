"""Frota de veículos por município (Senatran, via Base dos Dados)."""

from __future__ import annotations

import pandas as pd

from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw
from . import bq

TABELA = "basedosdados.br_senatran_estatisticas.municipio_tipo"


def baixar() -> pd.DataFrame:
    ano, mes = bq.periodo_mais_recente(TABELA)
    sql = f"""
        SELECT
            id_municipio,
            SUM(IF(tipo_veiculo = 'automovel', quantidade, 0)) AS automoveis,
            SUM(IF(tipo_veiculo = 'motocicleta', quantidade, 0)) AS motocicletas,
            SUM(quantidade) AS frota_total
        FROM `{TABELA}`
        WHERE ano = {ano} AND mes = {mes}
        GROUP BY id_municipio
    """
    df = bq.consultar(sql)
    df["ano_referencia"] = ano
    df["mes_referencia"] = mes
    return df


def carregar(forcar_download: bool = False) -> pd.DataFrame:
    df = None if forcar_download else ler_raw_mais_recente("senatran_frota")
    if df is None:
        df = baixar()
        salvar_raw(df, "senatran_frota")

    df["id_municipio"] = df["id_municipio"].astype(str)
    referencia = f"{int(df['ano_referencia'].iloc[0])}-{int(df['mes_referencia'].iloc[0]):02d}"
    registrar_fonte(
        "veiculos_por_hab",
        "Senatran - frota de veículos por município e tipo (Base dos Dados)",
        referencia,
        "usa automóveis como proxy de patrimônio; motocicletas ficam como descritora "
        "porque no Brasil a moto cresce onde a renda cai",
    )
    return df.drop(columns=["ano_referencia", "mes_referencia"])
