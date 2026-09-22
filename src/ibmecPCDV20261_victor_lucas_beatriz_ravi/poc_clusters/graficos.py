"""Gráficos da POC, todos com título e rótulo em português."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import config

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 130
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["axes.titlesize"] = 11
plt.rcParams["font.size"] = 9

CORES_CLUSTER = "tab10"


def _salvar(figura: plt.Figure, nome: str) -> None:
    figura.savefig(config.DIR_FIGURAS / f"{nome}.png")
    plt.close(figura)


def histogramas(base: pd.DataFrame, variaveis: list[str]) -> None:
    linhas = int(np.ceil(len(variaveis) / 3))
    figura, eixos = plt.subplots(linhas, 3, figsize=(13, 3.1 * linhas))
    for eixo, variavel in zip(eixos.ravel(), variaveis):
        sns.histplot(base[variavel].dropna(), bins=40, ax=eixo, color="#4C72B0")
        eixo.set_title(f"{config.VARIAVEIS[variavel]}\nassimetria = {base[variavel].skew():.2f}")
        eixo.set_xlabel("")
        eixo.set_ylabel("Municípios")
    for eixo in eixos.ravel()[len(variaveis) :]:
        eixo.axis("off")
    figura.suptitle("Distribuição das variáveis nos 687 municípios", y=1.01, fontsize=13)
    _salvar(figura, "01_histogramas")


def boxplots(base: pd.DataFrame, variaveis: list[str]) -> None:
    linhas = int(np.ceil(len(variaveis) / 3))
    figura, eixos = plt.subplots(linhas, 3, figsize=(13, 2.7 * linhas))
    for eixo, variavel in zip(eixos.ravel(), variaveis):
        sns.boxplot(x=base[variavel].dropna(), ax=eixo, color="#DD8452", fliersize=2)
        eixo.set_title(config.VARIAVEIS[variavel])
        eixo.set_xlabel("")
    for eixo in eixos.ravel()[len(variaveis) :]:
        eixo.axis("off")
    figura.suptitle("Boxplot das variáveis e seus valores extremos", y=1.01, fontsize=13)
    _salvar(figura, "02_boxplots")


def heatmap_correlacao(correlacao: pd.DataFrame) -> None:
    rotulos = [config.VARIAVEIS.get(c, c) for c in correlacao.columns]
    figura, eixo = plt.subplots(figsize=(9.5, 7.5))
    sns.heatmap(
        correlacao,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        vmin=-1,
        vmax=1,
        xticklabels=rotulos,
        yticklabels=rotulos,
        ax=eixo,
        annot_kws={"size": 7},
    )
    eixo.set_title("Correlação de Spearman entre as variáveis")
    _salvar(figura, "03_correlacao")


def curvas_k(varredura: pd.DataFrame) -> None:
    metricas = [
        ("inercia", "Inércia (cotovelo)", "menor é melhor"),
        ("silhueta", "Silhueta", "maior é melhor"),
        ("davies_bouldin", "Davies-Bouldin", "menor é melhor"),
        ("calinski_harabasz", "Calinski-Harabasz", "maior é melhor"),
    ]
    figura, eixos = plt.subplots(2, 2, figsize=(13, 8))
    for eixo, (coluna, titulo, sentido) in zip(eixos.ravel(), metricas):
        dados = varredura.dropna(subset=[coluna])
        for grupo in sorted(dados["grupo"].unique()):
            recorte = dados[(dados["grupo"] == grupo) & (dados["modelo"] == "kmeans")]
            if recorte.empty:
                continue
            eixo.plot(
                recorte["k"],
                recorte[coluna],
                marker="o",
                label=f"{grupo} - {config.NOMES_GRUPOS[grupo]}",
            )
        eixo.set_title(f"{titulo} ({sentido})")
        eixo.set_xlabel("Número de clusters (k)")
        eixo.set_ylabel(titulo)
        eixo.legend(fontsize=7)
    figura.suptitle("Escolha de k por grupo de variáveis, modelo KMeans", y=1.0, fontsize=13)
    _salvar(figura, "04_escolha_de_k")


def comparacao_modelos(varredura: pd.DataFrame) -> None:
    figura, eixos = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    for eixo, grupo in zip(eixos.ravel(), sorted(varredura["grupo"].unique())):
        recorte = varredura[varredura["grupo"] == grupo]
        sns.lineplot(
            data=recorte, x="k", y="silhueta", hue="nome_modelo", marker="o", ax=eixo
        )
        eixo.set_title(f"Grupo {grupo} - {config.NOMES_GRUPOS[grupo]}")
        eixo.set_xlabel("Número de clusters (k)")
        eixo.set_ylabel("Silhueta")
        eixo.legend(title="Modelo", fontsize=7)
    figura.suptitle("Silhueta por modelo e por grupo de variáveis", y=1.0, fontsize=13)
    _salvar(figura, "05_comparacao_modelos")


def grafico_baselines(comparacao: pd.DataFrame, nome_arquivo: str = "06_baselines") -> None:
    figura, eixo = plt.subplots(figsize=(9, 4.2))
    cores = ["#2A9D8F" if i == 0 else "#B0B0B0" for i in range(len(comparacao))]
    eixo.barh(comparacao["agrupamento"], comparacao["silhueta"], color=cores)
    eixo.axvline(0, color="black", linewidth=0.8)
    eixo.set_xlabel("Silhueta (maior é melhor)")
    eixo.set_title("Os clusters superam geografia, porte populacional e sorteio")
    eixo.invert_yaxis()
    for y, valor in enumerate(comparacao["silhueta"]):
        eixo.text(valor, y, f" {valor:.3f}", va="center", fontsize=8)
    _salvar(figura, nome_arquivo)


def heatmap_perfil(perfil: pd.DataFrame, nomes: dict[int, str] | None = None) -> None:
    rotulos_linha = [
        f"{c} - {nomes[c]}" if nomes else f"Cluster {c}" for c in perfil.index
    ]
    figura, eixo = plt.subplots(figsize=(11, 0.8 + 0.55 * len(perfil)))
    sns.heatmap(
        perfil,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        xticklabels=[config.VARIAVEIS.get(c, c) for c in perfil.columns],
        yticklabels=rotulos_linha,
        ax=eixo,
        annot_kws={"size": 8},
        cbar_kws={"label": "Desvios padrão em relação à média nacional"},
    )
    eixo.set_title("Perfil dos clusters em variáveis padronizadas")
    plt.setp(eixo.get_xticklabels(), rotation=35, ha="right")
    _salvar(figura, "07_perfil_clusters")


def radar(perfil: pd.DataFrame, nomes: dict[int, str] | None = None) -> None:
    variaveis = list(perfil.columns)
    angulos = np.linspace(0, 2 * np.pi, len(variaveis), endpoint=False).tolist()
    angulos += angulos[:1]

    figura, eixo = plt.subplots(figsize=(8.5, 8.5), subplot_kw={"polar": True})
    cores = sns.color_palette(CORES_CLUSTER, len(perfil))
    for cor, (cluster, linha) in zip(cores, perfil.iterrows()):
        valores = linha.tolist() + [linha.iloc[0]]
        etiqueta = f"{cluster} - {nomes[cluster]}" if nomes else f"Cluster {cluster}"
        eixo.plot(angulos, valores, marker="o", markersize=3, label=etiqueta, color=cor)
        eixo.fill(angulos, valores, alpha=0.08, color=cor)
    eixo.set_xticks(angulos[:-1])
    eixo.set_xticklabels(
        [config.VARIAVEIS.get(v, v).replace(" / ", "\n") for v in variaveis], fontsize=7
    )
    eixo.set_title("Assinatura de cada tipo de praça", y=1.10)
    eixo.legend(loc="upper right", bbox_to_anchor=(1.32, 1.12), fontsize=7)
    _salvar(figura, "08_radar_clusters")


def mapa(base: pd.DataFrame, nomes: dict[int, str] | None = None) -> bool:
    """Mapa do Brasil com os municípios coloridos por cluster."""
    try:
        import geobr
    except ImportError:
        return False
    try:
        municipios = geobr.read_municipality(year=2022, simplified=True)
        estados = geobr.read_state(year=2020, simplified=True)
    except Exception:
        return False

    municipios["id_municipio"] = municipios["code_muni"].astype("int64").astype(str)
    dados = municipios.merge(
        base[["id_municipio", "cluster"]], on="id_municipio", how="inner"
    )
    if dados.empty:
        return False

    figura, eixo = plt.subplots(figsize=(9.5, 10))
    estados.boundary.plot(ax=eixo, color="#999999", linewidth=0.4)
    cores = sns.color_palette(CORES_CLUSTER, base["cluster"].nunique())
    for cor, cluster in zip(cores, sorted(dados["cluster"].unique())):
        etiqueta = f"{cluster} - {nomes[cluster]}" if nomes else f"Cluster {cluster}"
        dados[dados["cluster"] == cluster].plot(
            ax=eixo, color=cor, edgecolor="none", label=etiqueta
        )
    eixo.set_axis_off()
    eixo.set_title(
        "Tipos de praça para o produto de fiança\nmunicípios com 50 mil habitantes ou mais",
        fontsize=12,
    )
    eixo.legend(loc="lower left", fontsize=8, frameon=True)
    _salvar(figura, "09_mapa_clusters")
    return True


def dispersao_decisao(base: pd.DataFrame, nomes: dict[int, str] | None = None) -> None:
    figura, eixo = plt.subplots(figsize=(9.5, 6.5))
    cores = sns.color_palette(CORES_CLUSTER, base["cluster"].nunique())
    for cor, cluster in zip(cores, sorted(base["cluster"].unique())):
        recorte = base[base["cluster"] == cluster]
        etiqueta = f"{cluster} - {nomes[cluster]}" if nomes else f"Cluster {cluster}"
        eixo.scatter(
            recorte["administradoras_10k"],
            recorte["pix_pf_por_hab"],
            s=recorte["populacao"] / 12_000,
            alpha=0.65,
            color=cor,
            label=etiqueta,
            edgecolor="white",
            linewidth=0.4,
        )
    eixo.set_xscale("log")
    eixo.set_xlabel(config.VARIAVEIS["administradoras_10k"] + " (escala log)")
    eixo.set_ylabel(config.VARIAVEIS["pix_pf_por_hab"])
    eixo.set_title(
        "Onde colocar o próximo real: densidade de administradoras x capacidade de pagamento\n"
        "tamanho do círculo é a população do município"
    )
    eixo.legend(fontsize=8)
    _salvar(figura, "10_mapa_de_decisao")


def ablacao(tabela: pd.DataFrame) -> None:
    figura, eixo = plt.subplots(figsize=(9, 4.2))
    cores = ["#C44E52" if v < 0 else "#55A868" for v in tabela["variacao"]]
    eixo.barh(tabela["rotulo"], tabela["variacao"], color=cores)
    eixo.axvline(0, color="black", linewidth=0.8)
    eixo.set_xlabel("Variação da silhueta ao remover a variável")
    eixo.set_title("Ablação: quanto cada variável sustenta a separação dos clusters")
    eixo.invert_yaxis()
    _salvar(figura, "11_ablacao")
