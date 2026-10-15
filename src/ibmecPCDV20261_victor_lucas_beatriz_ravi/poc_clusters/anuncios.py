"""Validação externa dos tipos de praça com a base de anúncios dos portais enviada pela Loft.

A base é interna da Loft e não entra no repositório: o arquivo bruto fica em data/raw e as
tabelas geradas aqui vão para reports/interno, ambos fora do Git. Os anúncios não entram no
modelo, só conferem o resultado; se entrassem, a validação compararia o modelo com ele mesmo.
"""

from __future__ import annotations

import unicodedata

import pandas as pd
from scipy import stats

from . import avaliacao, config

PADRAO_ARQUIVO = "bq-results-*.csv"
# Janela estável da coleta: antes de nov/2024 a cobertura era outra, fev e mar/2026 têm buraco
# e o último mês da extração está incompleto.
INICIO_JANELA = "2026-04-01"
FIM_JANELA = "2026-08-01"


def _normalizar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    return sem_acento.upper().replace("'", " ").replace("-", " ").strip()


def carregar() -> pd.DataFrame | None:
    """Mediana mensal de anúncios de aluguel e de venda por município, na janela estável."""
    arquivos = sorted(config.DIR_RAW.glob(PADRAO_ARQUIVO))
    if not arquivos:
        return None
    colunas = ["snapshot_month", "normalized_state_seed", "normalized_city_seed", "operation_type", "n_listings"]
    bruto = pd.read_csv(arquivos[-1], usecols=colunas)
    bruto = bruto[bruto["snapshot_month"].between(INICIO_JANELA, FIM_JANELA)]
    bruto["chave"] = bruto["normalized_state_seed"] + "|" + bruto["normalized_city_seed"].map(_normalizar)
    mensal = bruto.groupby(["snapshot_month", "chave", "operation_type"])["n_listings"].sum()
    return mensal.groupby(["chave", "operation_type"]).median().unstack(fill_value=0)


def validar(base: pd.DataFrame, coluna_cluster: str = "cluster") -> dict[str, pd.DataFrame] | None:
    anuncios = carregar()
    if anuncios is None:
        return None

    dados = base.copy()
    dados["chave"] = dados["sigla_uf"] + "|" + dados["municipio"].map(_normalizar)
    dados = dados.join(anuncios, on="chave")
    dados["coberto"] = dados["rent"].notna() | dados["sale"].notna()
    dados[["rent", "sale"]] = dados[["rent", "sale"]].fillna(0)
    dados["aluguel_10k"] = dados["rent"] / dados["populacao"] * 10_000
    # Venda sobre aluguel: quanto o dono tem a alternativa de vender em vez de alugar.
    dados["venda_por_aluguel"] = dados["sale"] / dados["rent"].replace(0, float("nan"))

    por_praca = (
        dados.groupby(["cluster", "nome_cluster"])
        .agg(
            municipios=("chave", "size"),
            com_anuncio_pct=("coberto", lambda s: round(s.mean() * 100, 1)),
            anuncios_aluguel_10k_media=("aluguel_10k", "mean"),
            anuncios_aluguel_10k_mediana=("aluguel_10k", "median"),
            anuncios_aluguel=("rent", "sum"),
            venda_por_aluguel_mediana=("venda_por_aluguel", "median"),
        )
        .reset_index()
        .sort_values("anuncios_aluguel_10k_media", ascending=False)
    )
    por_praca["parcela_dos_anuncios_pct"] = (
        por_praca["anuncios_aluguel"] / por_praca["anuncios_aluguel"].sum() * 100
    )

    teste = stats.kruskal(*[g["aluguel_10k"] for _, g in dados.groupby(coluna_cluster)])
    posto = dados["aluguel_10k"].rank()
    sem = avaliacao._r2_ajustado(posto, dados["regiao"], dados["porte"])
    com = avaliacao._r2_ajustado(posto, dados["regiao"], dados["porte"], dados[coluna_cluster])
    resumo = pd.DataFrame(
        [
            {
                "janela": f"{INICIO_JANELA[:7]} a {FIM_JANELA[:7]}",
                "municipios_com_anuncio": int(dados["coberto"].sum()),
                "municipios_total": len(dados),
                "kruskal_wallis_h": round(float(teste.statistic), 1),
                "kruskal_wallis_p": float(teste.pvalue),
                "r2_regiao_e_porte": round(sem, 4),
                "r2_com_o_cluster": round(com, 4),
                "ganho_do_cluster": round(com - sem, 4),
            }
        ]
    )

    cobertura_uf = (
        dados.groupby("sigla_uf")["coberto"].mean().mul(100).round(1).sort_values().reset_index()
    )
    destino = config.RAIZ / "reports" / "interno"
    destino.mkdir(parents=True, exist_ok=True)
    por_praca.round(2).to_csv(destino / "26_anuncios_por_praca.csv", index=False)
    resumo.to_csv(destino / "27_anuncios_resumo_do_teste.csv", index=False)
    cobertura_uf.to_csv(destino / "28_anuncios_cobertura_por_uf.csv", index=False)
    return {"por_praca": por_praca, "resumo": resumo, "cobertura_uf": cobertura_uf}
