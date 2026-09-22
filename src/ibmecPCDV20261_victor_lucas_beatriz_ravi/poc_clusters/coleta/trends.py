"""Interesse de busca por fiança de aluguel no Google Trends.

Ao pedir resolução de cidade a API devolve unidades da federação, não municípios. A cobertura
municipal medida foi de 0,3% do universo, muito abaixo do mínimo exigido, então a variável
não entra no cluster: fica como descritora por UF, conforme previsto no desenho da POC.
"""

from __future__ import annotations

import time

import pandas as pd

from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw

TERMOS = ["aluguel sem fiador", "fiança aluguel"]
JANELA = "today 12-m"
PAUSA_ENTRE_TERMOS = 5


def baixar() -> pd.DataFrame:
    from pytrends.request import TrendReq

    # Sem retries: o pytrends 4.9 monta o Retry com um argumento que o urllib3 2.x removeu.
    sessao = TrendReq(hl="pt-BR", tz=180)
    partes = []
    for termo in TERMOS:
        sessao.build_payload([termo], timeframe=JANELA, geo="BR")
        regioes = sessao.interest_by_region(resolution="CITY", inc_low_vol=True)
        regioes = regioes.reset_index().rename(columns={"geoName": "regiao", termo: "indice"})
        regioes["termo"] = termo
        partes.append(regioes[["regiao", "indice", "termo"]])
        time.sleep(PAUSA_ENTRE_TERMOS)
    return pd.concat(partes, ignore_index=True)


def carregar_por_uf(forcar_download: bool = False) -> pd.DataFrame:
    bruto = None if forcar_download else ler_raw_mais_recente("google_trends_fianca")
    if bruto is None:
        bruto = baixar()
        salvar_raw(bruto, "google_trends_fianca")

    medio = (
        bruto.groupby("regiao", as_index=False)["indice"]
        .mean()
        .rename(columns={"regiao": "uf", "indice": "trends_fianca_uf"})
    )
    registrar_fonte(
        "trends_fianca",
        f"Google Trends - termos {TERMOS} (pytrends)",
        pd.Timestamp.today().strftime("%Y-%m"),
        "a API devolve unidade da federação mesmo quando se pede cidade; cobertura municipal "
        "de 0,3% do universo, abaixo do mínimo de 80%, então entra apenas como descritora por UF",
    )
    return medio
