"""Monta a tabela municipal de variáveis, todas relativas à população."""

from __future__ import annotations

import pandas as pd

from . import config
from .coleta import anatel, cadunico, caged, cnpj, estban, ibge, senatran
from .io_utils import registrar_fonte

ARQUIVO_BASE = config.DIR_PROCESSED / "base_municipios.csv"


def montar(forcar_download: bool = False) -> pd.DataFrame:
    base = ibge.carregar_universo(forcar_download)

    base = base.merge(cnpj.carregar(forcar_download), on="id_municipio", how="left")
    base = base.merge(caged.carregar(forcar_download), on="id_municipio", how="left")
    base = base.merge(estban.carregar(forcar_download), on="id_municipio", how="left")
    base = base.merge(senatran.carregar(forcar_download), on="id_municipio", how="left")
    base = base.merge(pix_valores(forcar_download), on="id_municipio", how="left")
    base = base.merge(
        anatel.carregar_banda_larga_fixa(forcar_download), on="id_municipio", how="left"
    )
    base = base.merge(anatel.carregar_movel(forcar_download), on="id_municipio", how="left")

    familias = cadunico.carregar(forcar_download)
    base["id_municipio_6"] = base["id_municipio"].str[:6]
    base = base.merge(familias, on="id_municipio_6", how="left").drop(columns="id_municipio_6")

    # Municípios sem nenhuma empresa do setor têm zero de verdade, não dado faltante.
    for coluna in ["administradoras", "imobiliarias", "setor_total", "setor_novas_12m"]:
        base[coluna] = base[coluna].fillna(0)
    # Sem agência bancária no município o saldo de crédito local é zero.
    for coluna in ["credito_total", "financiamento_imobiliario"]:
        base[coluna] = base[coluna].fillna(0)

    base["administradoras_10k"] = base["administradoras"] / base["populacao"] * 10_000
    base["imobiliarias_10k"] = base["imobiliarias"] / base["populacao"] * 10_000
    base["imobiliarias_novas_pct"] = (
        base["setor_novas_12m"] / base["setor_total"].replace(0, float("nan")) * 100
    ).astype(float)
    base["sem_mercado_formal"] = base["setor_total"] == 0
    base.loc[base["sem_mercado_formal"], "imobiliarias_novas_pct"] = 0.0

    base["pix_pf_por_hab"] = base["pix_pf_valor_12m"] / base["populacao"]
    base["salario_admissao"] = base["salario_admissao_mediano"]
    base["domicilios_estimados"] = base["populacao"] / config.MORADORES_POR_DOMICILIO
    base["cadunico_pct"] = base["familias_cadunico"] / base["domicilios_estimados"] * 100
    base["credito_per_capita"] = base["credito_total"] / base["populacao"]
    base["veiculos_por_hab"] = base["automoveis"] / base["populacao"]
    base["motos_por_hab"] = base["motocicletas"] / base["populacao"]
    base["saldo_emprego_pct"] = base["saldo_12m"] / base["admissoes_12m"] * 100
    base["internet_movel_100"] = base["acessos_movel_4g5g_pf"] / base["populacao"] * 100
    base["financiamento_imob_per_capita"] = (
        base["financiamento_imobiliario"] / base["populacao"]
    )

    registrar_fonte(
        "cadunico_pct",
        "Ministério do Desenvolvimento e Assistência Social - Cadastro Único (API MISocial/SAGI)",
        _referencia_cadunico(base),
        f"famílias cadastradas sobre domicílios estimados (população IBGE dividida por "
        f"{config.MORADORES_POR_DOMICILIO} moradores por domicílio, PNAD Contínua); a API não "
        f"preenche a contagem de pessoas nesta competência",
    )
    return base


def pix_valores(forcar_download: bool = False) -> pd.DataFrame:
    from .coleta import pix

    return pix.carregar(forcar_download)


def _referencia_cadunico(base: pd.DataFrame) -> str:
    from .io_utils import tabela_fontes

    fontes = tabela_fontes()
    linha = fontes[fontes["variavel"] == "cadunico_pct"]
    return str(linha["data_referencia"].iloc[0]) if len(linha) else "indefinida"


def relatorio_cobertura(base: pd.DataFrame) -> pd.DataFrame:
    """Faltantes e dispersão de cada variável, para conferir se a base está usável."""
    linhas = []
    for variavel, rotulo in config.VARIAVEIS.items():
        if variavel not in base.columns:
            linhas.append(
                {
                    "variavel": variavel,
                    "rotulo": rotulo,
                    "faltantes": len(base),
                    "faltantes_pct": 100.0,
                }
            )
            continue
        serie = base[variavel]
        linhas.append(
            {
                "variavel": variavel,
                "rotulo": rotulo,
                "faltantes": int(serie.isna().sum()),
                "faltantes_pct": round(serie.isna().mean() * 100, 2),
                "zeros": int((serie == 0).sum()),
                "minimo": round(float(serie.min()), 3),
                "mediana": round(float(serie.median()), 3),
                "maximo": round(float(serie.max()), 3),
                "assimetria": round(float(serie.skew()), 2),
            }
        )
    return pd.DataFrame(linhas)


def salvar(base: pd.DataFrame) -> None:
    base.to_csv(ARQUIVO_BASE, index=False)


def carregar_salva() -> pd.DataFrame:
    return pd.read_csv(ARQUIVO_BASE, dtype={"id_municipio": str})
