"""Leitura e escrita de dados brutos e registro da data de referência de cada fonte."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from . import config

ARQUIVO_FONTES = config.DIR_INTERIM / "fontes_data_referencia.json"


def caminho_raw(nome: str, extensao: str = "csv") -> Path:
    """Caminho em data/raw com a data da coleta no nome do arquivo."""
    return config.DIR_RAW / f"{nome}_coletado_{date.today().isoformat()}.{extensao}"


def salvar_raw(df: pd.DataFrame, nome: str) -> Path:
    caminho = caminho_raw(nome)
    df.to_csv(caminho, index=False)
    return caminho


def ler_raw_mais_recente(nome: str, extensao: str = "csv") -> pd.DataFrame | None:
    """Reaproveita a coleta mais recente já salva, para não rebaixar a mesma fonte duas vezes."""
    candidatos = sorted(config.DIR_RAW.glob(f"{nome}_coletado_*.{extensao}"))
    if not candidatos:
        return None
    return pd.read_csv(candidatos[-1], dtype={"id_municipio": str})


def registrar_fonte(
    variavel: str,
    fonte: str,
    data_referencia: str,
    observacao: str = "",
) -> None:
    registro = {}
    if ARQUIVO_FONTES.exists():
        registro = json.loads(ARQUIVO_FONTES.read_text(encoding="utf-8"))
    registro[variavel] = {
        "fonte": fonte,
        "data_referencia": data_referencia,
        "data_coleta": date.today().isoformat(),
        "observacao": observacao,
    }
    ARQUIVO_FONTES.write_text(
        json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def tabela_fontes() -> pd.DataFrame:
    if not ARQUIVO_FONTES.exists():
        return pd.DataFrame(
            columns=["variavel", "fonte", "data_referencia", "data_coleta", "observacao"]
        )
    registro = json.loads(ARQUIVO_FONTES.read_text(encoding="utf-8"))
    df = pd.DataFrame.from_dict(registro, orient="index").reset_index(names="variavel")
    df["rotulo"] = df["variavel"].map(config.VARIAVEIS)
    return df.sort_values("variavel").reset_index(drop=True)
