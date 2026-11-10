"""Segunda leitura dos dados por densidade: DBSCAN, HDBSCAN e Isolation Forest.

O KMeans parte do princípio de que existem k grupos redondos e obriga toda cidade a entrar em um.
Os métodos de densidade não assumem nada disso: procuram regiões densas e chamam de ruído o que
fica isolado. Servem aqui para duas perguntas. Os dados têm grupos naturais por densidade, ou são
um contínuo (como a silhueta máxima em k = 2 já sugeria)? E quais cidades são atípicas a ponto
de não pertencerem a praça nenhuma?
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, HDBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from . import clustering, config, descritiva, estilo

CONTAMINACAO = 0.05
FATORES_EPS = (0.6, 0.8, 1.0, 1.2, 1.5, 2.0)


def eps_pelo_joelho(distancias: np.ndarray) -> float:
    """Ponto da curva de k-distância ordenada mais distante da reta entre as pontas."""
    y = np.sort(distancias)
    x = np.linspace(0, 1, len(y))
    y_norm = (y - y.min()) / (y.max() - y.min())
    distancia_reta = np.abs(y_norm - x) / np.sqrt(2)
    return float(y[int(distancia_reta.argmax())])


def _resumo(nome: str, parametro: str, rotulos: np.ndarray, matriz: np.ndarray, kmeans: np.ndarray) -> dict:
    validos = rotulos != -1
    n_grupos = len(set(rotulos[validos]))
    silhueta = (
        float(silhouette_score(matriz[validos], rotulos[validos])) if n_grupos >= 2 else np.nan
    )
    return {
        "metodo": nome,
        "parametro": parametro,
        "grupos_encontrados": n_grupos,
        "ruido_municipios": int((~validos).sum()),
        "ruido_pct": round(float((~validos).mean() * 100), 1),
        "maior_grupo_pct": round(float(pd.Series(rotulos[validos]).value_counts(normalize=True).max() * 100), 1)
        if validos.any() else np.nan,
        "silhueta_sem_ruido": round(silhueta, 3) if not np.isnan(silhueta) else np.nan,
        "rand_ajustado_vs_kmeans": round(float(adjusted_rand_score(kmeans[validos], rotulos[validos])), 3)
        if validos.any() else np.nan,
    }


def comparar(base: pd.DataFrame, variaveis: list[str]) -> dict[str, pd.DataFrame]:
    """DBSCAN no eps do joelho, sensibilidade ao eps e HDBSCAN, no mesmo espaço do modelo final."""
    estilo.aplicar()
    matriz, _ = clustering.preparar_matriz(base, variaveis)
    kmeans = base["cluster"].to_numpy()
    min_amostras = 2 * matriz.shape[1]   # regra prática da literatura: o dobro da dimensão

    vizinhos = NearestNeighbors(n_neighbors=min_amostras).fit(matriz)
    distancias = vizinhos.kneighbors(matriz)[0][:, -1]
    eps = eps_pelo_joelho(distancias)

    rotulos_db = DBSCAN(eps=eps, min_samples=min_amostras).fit_predict(matriz)
    rotulos_hdb = HDBSCAN(min_cluster_size=20, min_samples=10, copy=True).fit_predict(matriz)

    linhas = [
        _resumo("DBSCAN", f"eps = {eps:.2f} (joelho), min_samples = {min_amostras}", rotulos_db, matriz, kmeans),
        _resumo("HDBSCAN", "min_cluster_size = 20, min_samples = 10", rotulos_hdb, matriz, kmeans),
    ]
    sensibilidade = [
        _resumo("DBSCAN", f"{fator:.1f} x joelho", DBSCAN(eps=eps * fator, min_samples=min_amostras).fit_predict(matriz), matriz, kmeans)
        | {"eps": round(eps * fator, 3)}
        for fator in FATORES_EPS
    ]

    cruzamento = pd.crosstab(
        base["nome_cluster"],
        pd.Series(np.where(rotulos_hdb == -1, "ruído", "grupo " + rotulos_hdb.astype(str)), name="HDBSCAN"),
    )

    _grafico_k_distancia(distancias, eps, min_amostras)
    _grafico_sensibilidade(pd.DataFrame(sensibilidade))
    return {
        "resumo": pd.DataFrame(linhas),
        "sensibilidade": pd.DataFrame(sensibilidade),
        "cruzamento": cruzamento.reset_index(),
        "rotulos_hdbscan": rotulos_hdb,
    }


def cidades_atipicas(base: pd.DataFrame, n_destaque: int = 15) -> pd.DataFrame:
    """Isolation Forest nas 16 variáveis candidatas, antes de qualquer winsorização.

    Roda antes do corte de extremos de propósito: a pergunta é se as cidades que ele aponta como
    atípicas são as mesmas que a winsorização aparou, ou seja, se o tratamento pegou o problema.
    """
    variaveis = list(config.VARIAVEIS)
    dados = base[variaveis].astype(float).copy()
    for v in descritiva.variaveis_com_log(dados, variaveis):
        dados[v] = np.log1p(dados[v])
    padronizado = StandardScaler().fit_transform(dados)

    floresta = IsolationForest(n_estimators=300, contamination=CONTAMINACAO, random_state=config.SEMENTE)
    rotulo = floresta.fit_predict(padronizado)
    escore = -floresta.score_samples(padronizado)

    _, registro = descritiva.winsorizar(base, variaveis)
    aparada = np.zeros(len(base), dtype=bool)
    for _, linha in registro.iterrows():
        v = linha["variavel"]
        aparada |= (base[v] < linha["limite_inferior"]).to_numpy() | (base[v] > linha["limite_superior"]).to_numpy()

    z = pd.DataFrame(padronizado, columns=variaveis)
    mais_extrema = z.abs().idxmax(axis=1).map(descritiva.rotulo)
    tabela = pd.DataFrame(
        {
            "municipio": base["municipio"],
            "sigla_uf": base["sigla_uf"],
            "populacao": base["populacao"],
            "tipo_de_praca": base["nome_cluster"],
            "escore_anomalia": escore.round(3),
            "atipica": rotulo == -1,
            "variavel_mais_extrema": mais_extrema,
            "aparada_na_winsorizacao": aparada,
        }
    ).sort_values("escore_anomalia", ascending=False).reset_index(drop=True)
    tabela.attrs["concordancia_pct"] = round(
        float(tabela.loc[tabela["atipica"], "aparada_na_winsorizacao"].mean() * 100), 1
    )
    _grafico_atipicas(tabela, n_destaque)
    return tabela


def _grafico_k_distancia(distancias: np.ndarray, eps: float, k: int) -> None:
    figura, eixo = plt.subplots(figsize=(9, 4.2))
    ordenadas = np.sort(distancias)
    eixo.plot(ordenadas, color=estilo.AZUL, linewidth=2)
    eixo.axhline(eps, color=estilo.VERMELHO, linestyle="--", label=f"eps escolhido no joelho = {eps:.2f}")
    eixo.set_xlabel("municípios, ordenados pela distância")
    eixo.set_ylabel(f"distância ao {k}º vizinho mais próximo")
    eixo.set_title("Curva de k-distância: como o DBSCAN escolhe o raio (eps)")
    eixo.legend()
    estilo.salvar(figura, "12_k_distancia")


def _grafico_sensibilidade(tabela: pd.DataFrame) -> None:
    figura, eixo = plt.subplots(figsize=(9, 4.2))
    eixo.bar(tabela["parametro"], tabela["ruido_pct"], color=estilo.AMARELO, label="% de municípios como ruído")
    eixo.set_ylabel("% de municípios como ruído")
    segundo = eixo.twinx()
    segundo.plot(tabela["parametro"], tabela["grupos_encontrados"], color=estilo.AZUL, marker="o", linewidth=2)
    segundo.set_ylabel("grupos encontrados", color=estilo.AZUL)
    segundo.grid(False)
    eixo.set_title("DBSCAN: grupos e ruído conforme o raio muda")
    eixo.set_xlabel("raio (eps) em múltiplos do joelho")
    estilo.salvar(figura, "13_dbscan_sensibilidade")


def _grafico_atipicas(tabela: pd.DataFrame, n: int) -> None:
    figura, eixos = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1, 1.3]})
    corte = tabela.loc[tabela["atipica"], "escore_anomalia"].min()
    eixos[0].hist(tabela["escore_anomalia"], bins=40, color=estilo.AZUL, alpha=0.85)
    eixos[0].axvline(corte, color=estilo.VERMELHO, linestyle="--", label=f"5% mais atípicos (escore ≥ {corte:.2f})")
    eixos[0].set_xlabel("escore de anomalia (maior = mais atípico)")
    eixos[0].set_ylabel("municípios")
    eixos[0].set_title("Isolation Forest: distribuição do escore")
    eixos[0].legend(fontsize=8)

    topo = tabela.head(n).iloc[::-1]
    cores = [estilo.VERMELHO if a else estilo.CINZA for a in topo["aparada_na_winsorizacao"]]
    eixos[1].barh(topo["municipio"] + " - " + topo["sigla_uf"], topo["escore_anomalia"], color=cores)
    eixos[1].set_xlabel("escore de anomalia")
    eixos[1].set_title(f"Os {n} municípios mais atípicos\nvermelho = já aparado pela winsorização")
    xmin = topo["escore_anomalia"].min() * 0.97
    eixos[1].set_xlim(left=xmin)
    figura.tight_layout()
    estilo.salvar(figura, "14_cidades_atipicas")
