"""Universo de análise: municípios com 50 mil habitantes ou mais (estimativa IBGE)."""

from __future__ import annotations

import requests
import pandas as pd

from .. import config
from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw

API_AGREGADOS = "https://servicodados.ibge.gov.br/api/v3/agregados"
API_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
TABELA_ESTIMATIVAS = 6579
VARIAVEL_POPULACAO = 9324


def _ano_mais_recente() -> int:
    resposta = requests.get(f"{API_AGREGADOS}/{TABELA_ESTIMATIVAS}/periodos", timeout=120)
    resposta.raise_for_status()
    return max(int(p["id"]) for p in resposta.json())


def baixar_populacao(ano: int | None = None, exigir_ano_minimo: bool = True) -> pd.DataFrame:
    """A regra de data mínima vale para a população do universo, não para a série de comparação."""
    if ano is None:
        ano = _ano_mais_recente()
    if exigir_ano_minimo and ano < config.ANO_POPULACAO:
        raise ValueError(
            f"Estimativa populacional mais recente é {ano}; a POC exige {config.ANO_POPULACAO} ou posterior."
        )
    url = (
        f"{API_AGREGADOS}/{TABELA_ESTIMATIVAS}/periodos/{ano}"
        f"/variaveis/{VARIAVEL_POPULACAO}?localidades=N6[all]"
    )
    resposta = requests.get(url, timeout=300)
    resposta.raise_for_status()
    series = resposta.json()[0]["resultados"][0]["series"]
    registros = [
        {
            "id_municipio": s["localidade"]["id"],
            "municipio_uf": s["localidade"]["nome"],
            "populacao": int(list(s["serie"].values())[0]),
        }
        for s in series
    ]
    df = pd.DataFrame(registros)
    df["ano_populacao"] = ano
    return df


def baixar_metadados_municipios() -> pd.DataFrame:
    resposta = requests.get(API_LOCALIDADES, timeout=300)
    resposta.raise_for_status()
    registros = []
    for m in resposta.json():
        micro = m.get("microrregiao")
        if micro:
            uf = micro["mesorregiao"]["UF"]
        else:
            uf = m["regiao-imediata"]["regiao-intermediaria"]["UF"]
        registros.append(
            {
                "id_municipio": str(m["id"]),
                "municipio": m["nome"],
                "sigla_uf": uf["sigla"],
                "uf": uf["nome"],
                "regiao": uf["regiao"]["nome"],
            }
        )
    return pd.DataFrame(registros)


def baixar_populacao_anterior(ano_atual: int) -> pd.DataFrame:
    """População do ano anterior, para medir crescimento, que é o motor da demanda de aluguel."""
    anterior = baixar_populacao(ano_atual - 1, exigir_ano_minimo=False)
    return anterior.rename(columns={"populacao": "populacao_anterior"})[
        ["id_municipio", "populacao_anterior"]
    ]


def carregar_universo(forcar_download: bool = False) -> pd.DataFrame:
    """Municípios com população mínima, com UF e região do IBGE."""
    populacao = None if forcar_download else ler_raw_mais_recente("ibge_populacao")
    metadados = None if forcar_download else ler_raw_mais_recente("ibge_municipios")
    if populacao is None:
        populacao = baixar_populacao()
        salvar_raw(populacao, "ibge_populacao")
    if metadados is None:
        metadados = baixar_metadados_municipios()
        salvar_raw(metadados, "ibge_municipios")

    anterior = None if forcar_download else ler_raw_mais_recente("ibge_populacao_anterior")
    if anterior is None:
        anterior = baixar_populacao_anterior(int(populacao["ano_populacao"].iloc[0]))
        salvar_raw(anterior, "ibge_populacao_anterior")

    df = populacao.merge(metadados, on="id_municipio", how="left", validate="one_to_one")
    df = df.merge(anterior, on="id_municipio", how="left")
    faltando = df["sigla_uf"].isna().sum()
    if faltando:
        raise ValueError(f"{faltando} municípios sem UF depois do merge com localidades do IBGE.")

    ano = int(df["ano_populacao"].iloc[0])
    universo = df[df["populacao"] >= config.POPULACAO_MINIMA].copy()
    universo["porte"] = pd.cut(
        universo["populacao"],
        bins=[f[0] for f in config.FAIXAS_PORTE] + [float("inf")],
        labels=[f[2] for f in config.FAIXAS_PORTE],
        right=False,
    )
    universo = universo.sort_values("id_municipio").reset_index(drop=True)

    registrar_fonte(
        "crescimento_populacional_pct",
        "IBGE - Estimativas da população, dois anos consecutivos (tabela SIDRA 6579)",
        f"{ano}-07-01",
        f"variação da população de {ano - 1} para {ano}: entrada de gente é o que cria demanda "
        f"de locação, e é independente do nível de renda da praça",
    )
    registrar_fonte(
        "populacao",
        "IBGE - Estimativas da população (tabela SIDRA 6579)",
        f"{ano}-07-01",
        f"{len(universo)} municípios com {config.POPULACAO_MINIMA:,} habitantes ou mais".replace(",", "."),
    )
    return universo
