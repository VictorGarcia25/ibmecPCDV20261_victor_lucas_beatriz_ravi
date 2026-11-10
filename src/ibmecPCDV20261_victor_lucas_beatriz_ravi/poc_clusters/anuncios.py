"""Validação externa dos tipos de praça com a base de anúncios dos portais enviada pela Loft.

A base é interna da Loft e não entra no repositório: o arquivo bruto fica em data/raw e as
tabelas com volumes vão para reports/interno, ambos fora do Git. Os anúncios não entram no
modelo, só conferem o resultado; se entrassem, a validação compararia o modelo com ele mesmo.

Tratamentos, cada um por um problema encontrado na base:

1. Só a categoria residencial ``apartment_house``. Ela já é a soma de apartamento com casa, então
   somar as categorias contaria o residencial em dobro; ``other`` (terreno, sala, galpão) não é
   mercado de fiança residencial.
2. Janela escolhida por regra, não no olho: a coleta mudou em nov/2024 e tem meses com buraco.
   Um mês é estável quando o volume de aluguel fica a até 25% da mediana dos últimos 12 meses e o
   número de cidades fica perto do máximo; a janela é a sequência mais recente de meses estáveis.
3. Cidade só conta se aparece em quase todos os meses da janela, senão a mediana dela é de um
   ou dois meses soltos.
4. Preço da cidade é a mediana dos bairros ponderada pelo número de anúncios, porque a base traz
   a mediana por bairro e não o anúncio; só vale com pelo menos 20 anúncios de aluguel e de venda.
"""

from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
from scipy import stats

from . import avaliacao, config

PADRAO_ARQUIVO = "bq-results-*.csv"
CATEGORIA_RESIDENCIAL = "apartment_house"
INICIO_COLETA_ATUAL = "2024-11-01"
TOLERANCIA_VOLUME = 0.25
FRACAO_MINIMA_CIDADES = 0.90
MAXIMO_MESES_JANELA = 6
FRACAO_MINIMA_MESES_CIDADE = 0.8
# Preço mediano de cidade com poucos anúncios é ruído (um imóvel comercial já distorce).
MINIMO_ANUNCIOS_PRECO = 20
DESTINO_INTERNO = config.RAIZ / "reports" / "interno"


def _normalizar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    return sem_acento.upper().replace("'", " ").replace("-", " ").strip()


def _ler_bruto() -> pd.DataFrame | None:
    arquivos = sorted(config.DIR_RAW.glob(PADRAO_ARQUIVO))
    if not arquivos:
        return None
    colunas = [
        "snapshot_month", "normalized_state_seed", "normalized_city_seed", "operation_type",
        "property_type_group", "n_listings", "median_price_mm3",
    ]
    bruto = pd.read_csv(arquivos[-1], usecols=colunas)
    bruto = bruto[bruto["property_type_group"] == CATEGORIA_RESIDENCIAL].copy()
    bruto["chave"] = bruto["normalized_state_seed"] + "|" + bruto["normalized_city_seed"].map(_normalizar)
    return bruto


def escolher_janela(bruto: pd.DataFrame) -> tuple[list[str], pd.DataFrame]:
    """Meses estáveis da coleta e a janela usada, com o diagnóstico de cada mês."""
    aluguel = bruto[(bruto["operation_type"] == "rent") & (bruto["snapshot_month"] >= INICIO_COLETA_ATUAL)]
    mensal = aluguel.groupby("snapshot_month").agg(
        anuncios=("n_listings", "sum"), cidades=("chave", "nunique")
    )
    referencia = mensal["anuncios"].rolling(12, min_periods=3).median()
    mensal["indice_volume"] = (mensal["anuncios"] / referencia * 100).round(1)
    mensal["cidades_pct_do_maximo"] = (mensal["cidades"] / mensal["cidades"].max() * 100).round(1)
    mensal["estavel"] = (
        ((mensal["anuncios"] / referencia - 1).abs() <= TOLERANCIA_VOLUME)
        & (mensal["cidades"] >= FRACAO_MINIMA_CIDADES * mensal["cidades"].max())
    )

    janela: list[str] = []
    for mes in reversed(mensal.index):
        if mensal.loc[mes, "estavel"]:
            janela.insert(0, mes)
            if len(janela) == MAXIMO_MESES_JANELA:
                break
        elif janela:
            break
    mensal["na_janela"] = mensal.index.isin(janela)
    return janela, mensal.drop(columns=["anuncios", "cidades"]).reset_index()


def _mediana_ponderada(valores: pd.Series, pesos: pd.Series) -> float:
    ordem = np.argsort(valores.to_numpy())
    v, p = valores.to_numpy()[ordem], pesos.to_numpy()[ordem]
    acumulado = np.cumsum(p)
    return float(v[np.searchsorted(acumulado, acumulado[-1] / 2)])


def carregar() -> pd.DataFrame | None:
    """Por cidade, na janela estável: mediana mensal de anúncios e preço mediano, aluguel e venda."""
    bruto = _ler_bruto()
    if bruto is None:
        return None
    janela, diagnostico = escolher_janela(bruto)
    recorte = bruto[bruto["snapshot_month"].isin(janela)]

    contagem = recorte.groupby(["chave", "operation_type", "snapshot_month"])["n_listings"].sum()
    meses = contagem.groupby(["chave", "operation_type"]).size().unstack(fill_value=0)
    volume = contagem.groupby(["chave", "operation_type"]).median().unstack(fill_value=0)

    precos = recorte.dropna(subset=["median_price_mm3"])
    preco = (
        precos.groupby(["chave", "operation_type", "snapshot_month"])
        .apply(lambda g: _mediana_ponderada(g["median_price_mm3"], g["n_listings"]), include_groups=False)
        .groupby(["chave", "operation_type"]).median().unstack()
    )

    tabela = pd.DataFrame(index=volume.index)
    tabela["aluguel"] = volume.get("rent", 0)
    tabela["venda"] = volume.get("sale", 0)
    tabela["meses_com_aluguel"] = meses.get("rent", 0)
    tabela["preco_aluguel"] = preco.get("rent")
    tabela["preco_venda"] = preco.get("sale")
    minimo = int(np.ceil(FRACAO_MINIMA_MESES_CIDADE * len(janela)))
    tabela["cidade_consistente"] = tabela["meses_com_aluguel"] >= minimo
    poucos = (tabela["aluguel"] < MINIMO_ANUNCIOS_PRECO) | (tabela["venda"] < MINIMO_ANUNCIOS_PRECO)
    tabela.loc[poucos, ["preco_aluguel", "preco_venda"]] = np.nan
    tabela.attrs.update(janela=janela, diagnostico=diagnostico, minimo_meses=minimo)
    return tabela


def validar(base: pd.DataFrame, coluna_cluster: str = "cluster") -> dict[str, pd.DataFrame] | None:
    anuncios = carregar()
    if anuncios is None:
        return None
    janela = anuncios.attrs["janela"]

    dados = base.copy()
    dados["chave"] = dados["sigla_uf"] + "|" + dados["municipio"].map(_normalizar)
    dados = dados.join(anuncios, on="chave")
    dados["coberto"] = dados["cidade_consistente"].fillna(False).astype(bool)
    # Cidade fora da base ou instável conta como sem anúncio: é a leitura conservadora.
    dados.loc[~dados["coberto"], ["aluguel", "venda"]] = 0
    dados["aluguel_10k"] = dados["aluguel"] / dados["populacao"] * 10_000
    # Venda sobre aluguel: quanto o dono tem a alternativa de vender em vez de alugar.
    dados["venda_por_aluguel"] = dados["venda"] / dados["aluguel"].replace(0, np.nan)
    # Rendimento bruto do aluguel em um ano sobre o preço de venda.
    dados["rendimento_aluguel_pct"] = dados["preco_aluguel"] * 12 / dados["preco_venda"] * 100
    dados.loc[~dados["coberto"], ["venda_por_aluguel", "rendimento_aluguel_pct"]] = np.nan

    por_praca = (
        dados.groupby(["cluster", "nome_cluster"])
        .agg(
            municipios=("chave", "size"),
            com_anuncio_pct=("coberto", lambda s: round(s.mean() * 100, 1)),
            anuncios_aluguel_10k_media=("aluguel_10k", "mean"),
            anuncios_aluguel_10k_mediana=("aluguel_10k", "median"),
            anuncios_aluguel=("aluguel", "sum"),
            venda_por_aluguel_mediana=("venda_por_aluguel", "median"),
            rendimento_aluguel_pct_mediana=("rendimento_aluguel_pct", "median"),
        )
        .reset_index()
        .sort_values("anuncios_aluguel_10k_media", ascending=False)
    )
    por_praca["parcela_dos_anuncios_pct"] = (
        por_praca["anuncios_aluguel"] / por_praca["anuncios_aluguel"].sum() * 100
    )

    teste = stats.kruskal(*[g["aluguel_10k"] for _, g in dados.groupby(coluna_cluster)])
    rend = dados.dropna(subset=["rendimento_aluguel_pct"])
    teste_rend = stats.kruskal(*[g["rendimento_aluguel_pct"] for _, g in rend.groupby(coluna_cluster)])
    posto = dados["aluguel_10k"].rank()
    sem = avaliacao._r2_ajustado(posto, dados["regiao"], dados["porte"])
    com = avaliacao._r2_ajustado(posto, dados["regiao"], dados["porte"], dados[coluna_cluster])
    resumo = pd.DataFrame(
        [
            {
                "janela": f"{janela[0][:7]} a {janela[-1][:7]}",
                "meses_na_janela": len(janela),
                "categoria": "residencial (apartamento + casa)",
                "municipios_com_anuncio": int(dados["coberto"].sum()),
                "municipios_total": len(dados),
                "kruskal_wallis_h": round(float(teste.statistic), 1),
                "kruskal_wallis_p": float(teste.pvalue),
                "r2_regiao_e_porte": round(sem, 4),
                "r2_com_o_cluster": round(com, 4),
                "ganho_do_cluster": round(com - sem, 4),
                "rendimento_kruskal_p": float(teste_rend.pvalue),
                "municipios_com_rendimento": len(rend),
            }
        ]
    )

    cobertura_uf = (
        dados.groupby("sigla_uf")["coberto"].mean().mul(100).round(1).sort_values().reset_index()
    )
    rendimento = por_praca[["cluster", "nome_cluster", "rendimento_aluguel_pct_mediana"]].copy()
    diagnostico = anuncios.attrs["diagnostico"]

    DESTINO_INTERNO.mkdir(parents=True, exist_ok=True)
    por_praca.round(2).to_csv(DESTINO_INTERNO / "26_anuncios_por_praca.csv", index=False)
    resumo.to_csv(DESTINO_INTERNO / "27_anuncios_resumo_do_teste.csv", index=False)
    cobertura_uf.to_csv(DESTINO_INTERNO / "28_anuncios_cobertura_por_uf.csv", index=False)
    diagnostico.to_csv(DESTINO_INTERNO / "29_anuncios_meses_estaveis.csv", index=False)
    return {
        "por_praca": por_praca,
        "resumo": resumo,
        "cobertura_uf": cobertura_uf,
        "diagnostico_meses": diagnostico,
        "rendimento": rendimento,
        "por_municipio": dados,
    }
