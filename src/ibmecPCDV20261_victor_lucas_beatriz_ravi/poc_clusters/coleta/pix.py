"""Transações Pix por município (Banco Central, API OData de dados abertos do Pix)."""

from __future__ import annotations

import requests
import pandas as pd

from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw

RECURSO = (
    "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata/"
    "TransacoesPixPorMunicipio(DataBase=@DataBase)"
)
MESES_JANELA = 12
# Um mês em andamento aparece na API com volume parcial; abaixo desta fração da
# mediana nacional o mês é tratado como incompleto e descartado.
FRACAO_MINIMA_MES_COMPLETO = 0.85


def _mes_inicial(meses_atras: int) -> str:
    inicio = pd.Timestamp.today().to_period("M") - meses_atras
    return inicio.strftime("%Y%m")


def baixar_bruto(meses_atras: int = MESES_JANELA + 2) -> pd.DataFrame:
    """A API devolve todos os meses a partir da data-base informada."""
    resposta = requests.get(
        RECURSO,
        params={"@DataBase": f"'{_mes_inicial(meses_atras)}'", "$format": "json"},
        timeout=600,
    )
    resposta.raise_for_status()
    return pd.DataFrame(resposta.json()["value"])


def meses_completos(df: pd.DataFrame) -> list[int]:
    """Descarta meses cujo volume nacional indica mês ainda em andamento."""
    total = df.groupby("AnoMes")["VL_PagadorPF"].sum().sort_index()
    mediana = total.median()
    return sorted(total[total >= mediana * FRACAO_MINIMA_MES_COMPLETO].index.tolist())


def carregar(forcar_download: bool = False) -> pd.DataFrame:
    bruto = None if forcar_download else ler_raw_mais_recente("bcb_pix_municipio")
    if bruto is None:
        bruto = baixar_bruto()
        salvar_raw(bruto, "bcb_pix_municipio")

    completos = meses_completos(bruto)
    descartados = sorted(set(bruto["AnoMes"]) - set(completos))
    janela = completos[-MESES_JANELA:]
    if len(janela) < MESES_JANELA:
        raise ValueError(
            f"Só há {len(janela)} meses completos de Pix; a POC exige {MESES_JANELA}."
        )

    recorte = bruto[bruto["AnoMes"].isin(janela)].copy()
    agregado = (
        recorte.groupby("Municipio_Ibge")
        .agg(
            pix_pf_valor_12m=("VL_PagadorPF", "sum"),
            pix_pf_quantidade_12m=("QT_PagadorPF", "sum"),
            pix_pf_recebido_12m=("VL_RecebedorPF", "sum"),
            meses=("AnoMes", "nunique"),
        )
        .reset_index()
    )
    agregado = agregado[agregado["meses"] == MESES_JANELA].drop(columns="meses")
    agregado["id_municipio"] = agregado.pop("Municipio_Ibge").astype("Int64").astype(str)

    registrar_fonte(
        "pix_pf_por_hab",
        "Banco Central - Transações Pix por Município (API OData)",
        f"{str(janela[-1])[:4]}-{str(janela[-1])[4:]}",
        f"soma de {MESES_JANELA} meses completos ({janela[0]} a {janela[-1]}); "
        f"meses incompletos descartados: {descartados or 'nenhum'}",
    )
    return agregado
