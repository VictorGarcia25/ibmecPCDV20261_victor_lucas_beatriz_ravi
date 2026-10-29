"""Gráficos de leitura do modelo: as praças projetadas no plano (PCA) e o parentesco entre variáveis."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform
from sklearn.decomposition import PCA

from . import clustering, config, descritiva, estilo


def pca_das_pracas(base: pd.DataFrame, variaveis: list[str]) -> pd.DataFrame:
    """Projeta os municípios nos dois eixos que mais concentram variação e pinta pela praça.

    É só um retrato: o modelo usa as 6 dimensões, e o plano mostra a parte da variação que os dois
    primeiros eixos carregam. As setas dizem para onde cada variável empurra o município.
    """
    estilo.aplicar()
    matriz, _ = clustering.preparar_matriz(base, variaveis)
    pca = PCA(n_components=2, random_state=config.SEMENTE).fit(matriz)
    pontos = pca.transform(matriz)
    explicada = pca.explained_variance_ratio_ * 100

    figura, eixo = plt.subplots(figsize=(10, 7))
    for nome in sorted(base["nome_cluster"].unique()):
        filtro = (base["nome_cluster"] == nome).to_numpy()
        cor = estilo.cor_da_praca(nome)
        eixo.scatter(pontos[filtro, 0], pontos[filtro, 1], s=22, alpha=0.6, color=cor,
                     edgecolor="k", linewidth=0.2, label=nome)
        centro = pontos[filtro].mean(axis=0)
        eixo.scatter(*centro, s=260, marker="X", color=cor, edgecolor="k", linewidth=1.2)

    escala = 3.2
    curtos = {
        "imobiliarias_loft_10k": "Imobiliárias", "imobiliarias_novas_pct": "Imob. novas",
        "pix_pf_por_hab": "Pix", "cadunico_pct": "CadÚnico",
        "internet_movel_100": "Internet móvel", "banda_larga_100": "Banda larga",
    }
    for i, variavel in enumerate(variaveis):
        dx, dy = pca.components_[0, i] * escala, pca.components_[1, i] * escala
        eixo.arrow(0, 0, dx, dy, color="#333333", width=0.012, head_width=0.1, length_includes_head=True, zorder=5)
        # Setas quase paralelas: o rótulo de uma vai um pouco para cima e o da outra para baixo.
        ajuste = {"pix_pf_por_hab": 0.22, "imobiliarias_loft_10k": -0.22}.get(variavel, 0.0)
        eixo.text(dx * 1.18, dy * 1.18 + ajuste, curtos.get(variavel, variavel), fontsize=9, fontweight="bold",
                  color="#333333", ha="center", va="center", zorder=6,
                  bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none", "pad": 1.5})
    eixo.set_ylim(top=max(eixo.get_ylim()[1], escala * 1.35))

    eixo.set_xlabel(f"PC1 ({explicada[0]:.0f}% da variação)")
    eixo.set_ylabel(f"PC2 ({explicada[1]:.0f}% da variação)")
    eixo.set_title("As 5 praças no plano dos dois componentes principais\nX = centro da praça; setas = direção de cada variável")
    eixo.legend(fontsize=8, loc="best")
    estilo.salvar(figura, "15_pca_pracas")

    cargas = pd.DataFrame(pca.components_.T, index=variaveis, columns=["PC1", "PC2"]).round(3)
    cargas.insert(0, "rotulo", [descritiva.rotulo(v) for v in variaveis])
    cargas.attrs["variacao_explicada_pct"] = [round(float(v), 1) for v in explicada]
    return cargas.reset_index(names="variavel")


def dendrograma_variaveis(base: pd.DataFrame) -> pd.DataFrame:
    """Agrupa as 16 variáveis candidatas pela distância 1 - |correlação de Spearman|.

    Ligação média, para a altura do galho ser a própria distância: duas variáveis que se juntam
    abaixo de 0,20 têm correlação acima de 0,80, o limiar que usamos para cortar redundância.
    """
    estilo.aplicar()
    variaveis = list(config.VARIAVEIS)
    tratada, _ = descritiva.winsorizar(base, variaveis)
    correlacao = tratada[variaveis].corr(method="spearman").to_numpy()
    distancia = 1 - np.abs(correlacao)
    np.fill_diagonal(distancia, 0)
    ligacao = hierarchy.linkage(squareform(distancia, checks=False), method="average")
    limiar = 1 - descritiva.LIMIAR_CORRELACAO

    hierarchy.set_link_color_palette([estilo.VERMELHO, estilo.AZUL_CLARO, estilo.AMARELO])
    figura, eixo = plt.subplots(figsize=(12, 5))
    rotulos = [descritiva.rotulo(v) for v in variaveis]
    hierarchy.dendrogram(ligacao, labels=rotulos, leaf_rotation=80, leaf_font_size=8, ax=eixo,
                         color_threshold=limiar, above_threshold_color=estilo.CINZA)
    eixo.axhline(limiar, color=estilo.VERMELHO, linestyle="--",
                 label=f"corte em {limiar:.2f} = correlação de {descritiva.LIMIAR_CORRELACAO:.2f}")
    eixo.set_ylabel("1 - |correlação de Spearman|")
    eixo.set_title("Parentesco entre as 16 variáveis candidatas: quem se junta abaixo da linha diz a mesma coisa")
    eixo.legend()
    eixo.grid(False)
    estilo.salvar(figura, "16_dendrograma_variaveis")

    grupos = hierarchy.fcluster(ligacao, limiar, criterion="distance")
    tabela = pd.DataFrame({"variavel": variaveis, "rotulo": rotulos, "grupo_redundancia": grupos})
    tamanho = tabela.groupby("grupo_redundancia")["variavel"].transform("size")
    tabela["redundante_com_outra"] = tamanho > 1
    return tabela.sort_values(["grupo_redundancia", "variavel"]).reset_index(drop=True)
