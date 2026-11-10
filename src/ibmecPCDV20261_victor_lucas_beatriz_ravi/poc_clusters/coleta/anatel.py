"""Banda larga fixa e telefonia móvel por município (Anatel).

A banda larga fixa vem da Base dos Dados. A telefonia móvel só existe em um ZIP de 3,2 GB
no portal da Anatel, então o arquivo é lido por requisição de faixa (HTTP Range): baixamos
apenas o índice do ZIP e o membro em formato largo, poucos MB no total.
"""

from __future__ import annotations

import io
import zipfile

import pandas as pd
import requests

from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw
from . import bq

TABELA_FIXA = "basedosdados.br_anatel_banda_larga_fixa.densidade_municipio"
ZIP_MOVEL = (
    "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_telefonia_movel.zip"
)
TECNOLOGIAS_MOVEL_RAPIDA = ("4G", "5G")


class _ArquivoRemoto(io.RawIOBase):
    """Arquivo somente-leitura servido por HTTP Range, para abrir um ZIP sem baixá-lo inteiro."""

    def __init__(self, url: str, sessao: requests.Session | None = None):
        self.url = url
        self.sessao = sessao or requests.Session()
        cabecalho = self.sessao.head(url, allow_redirects=True, timeout=120)
        cabecalho.raise_for_status()
        if cabecalho.headers.get("accept-ranges") != "bytes":
            raise RuntimeError(f"{url} não aceita requisição por faixa (HTTP Range).")
        self.tamanho = int(cabecalho.headers["content-length"])
        self.posicao = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.posicao, io.SEEK_END: self.tamanho}[whence]
        self.posicao = max(0, min(self.tamanho, base + offset))
        return self.posicao

    def tell(self) -> int:
        return self.posicao

    def read(self, quantidade: int = -1) -> bytes:
        if quantidade is None or quantidade < 0:
            quantidade = self.tamanho - self.posicao
        if quantidade == 0 or self.posicao >= self.tamanho:
            return b""
        fim = min(self.tamanho, self.posicao + quantidade) - 1
        resposta = self.sessao.get(
            self.url, headers={"Range": f"bytes={self.posicao}-{fim}"}, timeout=600
        )
        resposta.raise_for_status()
        dados = resposta.content
        self.posicao += len(dados)
        return dados

    def readinto(self, buffer) -> int:
        dados = self.read(len(buffer))
        buffer[: len(dados)] = dados
        return len(dados)


def baixar_banda_larga_fixa() -> pd.DataFrame:
    ano, mes = bq.periodo_mais_recente(TABELA_FIXA)
    sql = f"""
        SELECT id_municipio, densidade AS banda_larga_100
        FROM `{TABELA_FIXA}`
        WHERE ano = {ano} AND mes = {mes}
    """
    df = bq.consultar(sql)
    df["ano_referencia"] = ano
    df["mes_referencia"] = mes
    return df


def carregar_banda_larga_fixa(forcar_download: bool = False) -> pd.DataFrame:
    df = None if forcar_download else ler_raw_mais_recente("anatel_banda_larga_fixa")
    if df is None:
        df = baixar_banda_larga_fixa()
        salvar_raw(df, "anatel_banda_larga_fixa")

    df["id_municipio"] = df["id_municipio"].astype(str)
    referencia = f"{int(df['ano_referencia'].iloc[0])}-{int(df['mes_referencia'].iloc[0]):02d}"
    registrar_fonte(
        "banda_larga_100",
        "Anatel - densidade de banda larga fixa por município (Base dos Dados)",
        referencia,
        "acessos por 100 habitantes, já calculado pela Anatel",
    )
    return df.drop(columns=["ano_referencia", "mes_referencia"])


def _membro_mais_recente(indice: zipfile.ZipFile) -> str:
    candidatos = [
        n
        for n in indice.namelist()
        if "Acessos_Telefonia_Movel" in n and n.endswith("_Colunas.csv")
    ]
    if not candidatos:
        raise RuntimeError(
            "O ZIP da Anatel não traz mais o arquivo em formato largo (_Colunas.csv): "
            f"conteúdo encontrado = {indice.namelist()[:10]}"
        )
    return sorted(candidatos)[-1]


def baixar_movel() -> pd.DataFrame:
    with zipfile.ZipFile(io.BufferedReader(_ArquivoRemoto(ZIP_MOVEL), buffer_size=1 << 20)) as z:
        membro = _membro_mais_recente(z)
        with z.open(membro) as f:
            bruto = pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str, low_memory=False)
    bruto.attrs["membro"] = membro
    return bruto


def carregar_movel(forcar_download: bool = False) -> pd.DataFrame:
    bruto = None if forcar_download else ler_raw_mais_recente("anatel_telefonia_movel")
    if bruto is None:
        bruto = baixar_movel()
        salvar_raw(bruto, "anatel_telefonia_movel")

    colunas_mes = sorted(c for c in bruto.columns if c[:4].isdigit() and "-" in c)
    if not colunas_mes:
        raise RuntimeError(f"Não achei colunas de mês em {list(bruto.columns)[:15]}")
    mes_recente = colunas_mes[-1]

    coluna_ibge = next(c for c in bruto.columns if "IBGE" in c.upper())
    coluna_tecnologia = next(c for c in bruto.columns if "Geração" in c or "Geracao" in c)
    coluna_pessoa = next(c for c in bruto.columns if "Pessoa" in c)

    df = bruto[[coluna_ibge, coluna_tecnologia, coluna_pessoa, mes_recente]].copy()
    df.columns = ["id_municipio", "tecnologia", "tipo_pessoa", "acessos"]
    df["acessos"] = pd.to_numeric(df["acessos"], errors="coerce").fillna(0)
    df["id_municipio"] = df["id_municipio"].astype(str).str.zfill(7)
    rapida = df["tecnologia"].str.upper().isin(TECNOLOGIAS_MOVEL_RAPIDA)
    pessoa_fisica = df["tipo_pessoa"].str.startswith("Pessoa F")

    df["acessos_4g5g"] = df["acessos"].where(rapida, 0)
    df["acessos_4g5g_pf"] = df["acessos"].where(rapida & pessoa_fisica, 0)

    agregado = (
        df.groupby("id_municipio", as_index=False)[
            ["acessos", "acessos_4g5g", "acessos_4g5g_pf"]
        ]
        .sum()
        .rename(
            columns={
                "acessos": "acessos_movel_total",
                "acessos_4g5g": "acessos_movel_4g5g",
                "acessos_4g5g_pf": "acessos_movel_4g5g_pf",
            }
        )
    )

    registrar_fonte(
        "internet_movel_100",
        "Anatel - acessos de telefonia móvel por município e tecnologia (dados abertos)",
        mes_recente,
        f"acessos 4G e 5G do mês {mes_recente}, divididos pela população IBGE; "
        "arquivo lido por requisição de faixa para não baixar o ZIP de 3,2 GB",
    )
    return agregado
