"""Famílias inscritas no Cadastro Único por município (API MISocial do SAGI/MDS).

A API devolve o código IBGE com 6 dígitos (sem dígito verificador), então o cruzamento com
o universo do IBGE é feito pelos 6 primeiros dígitos do código de 7.
"""

from __future__ import annotations

import io

import pandas as pd
import requests

from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw

API = "https://aplicacoes.mds.gov.br/sagi/servicos/misocial"
CAMPOS = [
    "codigo_ibge",
    "municipio",
    "sigla_uf",
    "anomes_s",
    "cadun_qtd_familias_cadastradas_i",
    "cadun_qtd_pessoas_cadastradas_i",
    "cadun_qtde_fam_sit_pobreza_s",
    "cadun_qtde_fam_sit_extrema_pobreza_s",
]
MESES_TENTATIVA = 6


def _consultar(anomes: str) -> pd.DataFrame:
    resposta = requests.get(
        API,
        params={
            "q": f"anomes_s:{anomes}",
            "fl": ",".join(CAMPOS),
            "rows": 6000,
            "wt": "csv",
        },
        timeout=300,
    )
    resposta.raise_for_status()
    if resposta.text.lstrip().startswith("<"):
        raise RuntimeError("A API do SAGI devolveu HTML em vez de dados.")
    return pd.read_csv(io.StringIO(resposta.text), dtype={"codigo_ibge": str})


def baixar() -> pd.DataFrame:
    """Anda para trás mês a mês até achar a competência mais recente já publicada."""
    mes = pd.Timestamp.today().to_period("M")
    for _ in range(MESES_TENTATIVA):
        df = _consultar(mes.strftime("%Y%m"))
        if len(df) > 5_000:
            df["anomes"] = mes.strftime("%Y%m")
            return df
        mes -= 1
    raise RuntimeError(
        f"Não achei competência do CadÚnico com cobertura nacional nos últimos "
        f"{MESES_TENTATIVA} meses."
    )


def carregar(forcar_download: bool = False) -> pd.DataFrame:
    df = None if forcar_download else ler_raw_mais_recente("cadunico_municipio")
    if df is None:
        df = baixar()
        salvar_raw(df, "cadunico_municipio")

    df = df.rename(
        columns={
            "cadun_qtd_familias_cadastradas_i": "familias_cadunico",
            "cadun_qtd_pessoas_cadastradas_i": "pessoas_cadunico",
            "cadun_qtde_fam_sit_pobreza_s": "familias_pobreza",
            "cadun_qtde_fam_sit_extrema_pobreza_s": "familias_extrema_pobreza",
        }
    )
    df["id_municipio_6"] = df["codigo_ibge"].astype(str).str.zfill(6)
    anomes = str(df["anomes"].iloc[0])

    registrar_fonte(
        "cadunico_pct",
        "Ministério do Desenvolvimento e Assistência Social - Cadastro Único (API MISocial/SAGI)",
        f"{anomes[:4]}-{anomes[4:]}",
        "famílias cadastradas divididas pelo número estimado de domicílios do município "
        "(população IBGE dividida pelo tamanho médio do domicílio da PNAD Contínua)",
    )
    colunas = [
        "id_municipio_6",
        "familias_cadunico",
        "pessoas_cadunico",
        "familias_pobreza",
        "familias_extrema_pobreza",
    ]
    return df[[c for c in colunas if c in df.columns]]
