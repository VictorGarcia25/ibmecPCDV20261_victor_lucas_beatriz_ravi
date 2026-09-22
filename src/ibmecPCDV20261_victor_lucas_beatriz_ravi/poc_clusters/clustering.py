"""Pipelines de clusterização e escolha de k para cada grupo de variáveis."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from . import config, descritiva

MODELOS = ("kmeans", "ward", "mistura_gaussiana")
NOMES_MODELOS = {
    "kmeans": "KMeans",
    "ward": "Aglomerativo (Ward)",
    "mistura_gaussiana": "Mistura Gaussiana",
}


def construir_preparo(variaveis: list[str], variaveis_log: list[str]) -> ColumnTransformer:
    """log nas variáveis de cauda longa, depois padronização em todas."""
    diretas = [v for v in variaveis if v not in variaveis_log]
    blocos = []
    if variaveis_log:
        blocos.append(
            (
                "log",
                Pipeline(
                    [
                        ("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                        ("escala", StandardScaler()),
                    ]
                ),
                variaveis_log,
            )
        )
    if diretas:
        blocos.append(("direto", StandardScaler(), diretas))
    return ColumnTransformer(blocos)


def construir_modelo(nome: str, k: int, semente: int = config.SEMENTE):
    if nome == "kmeans":
        return KMeans(n_clusters=k, random_state=semente, n_init=20)
    if nome == "ward":
        return AgglomerativeClustering(n_clusters=k, linkage="ward")
    if nome == "mistura_gaussiana":
        return GaussianMixture(n_components=k, random_state=semente, n_init=5)
    raise ValueError(f"Modelo desconhecido: {nome}")


def construir_pipeline(
    variaveis: list[str], variaveis_log: list[str], nome_modelo: str, k: int, semente: int = config.SEMENTE
) -> Pipeline:
    return Pipeline(
        [
            ("preparo", construir_preparo(variaveis, variaveis_log)),
            ("modelo", construir_modelo(nome_modelo, k, semente)),
        ]
    )


def preparar_matriz(base: pd.DataFrame, variaveis: list[str]) -> tuple[np.ndarray, list[str]]:
    """Aplica winsorização, log e padronização e devolve a matriz usada pelos modelos."""
    tratada, _ = descritiva.winsorizar(base, variaveis)
    variaveis_log = descritiva.variaveis_com_log(tratada, variaveis)
    preparo = construir_preparo(variaveis, variaveis_log)
    matriz = preparo.fit_transform(tratada[variaveis])
    return np.asarray(matriz), variaveis_log


def rotular(matriz: np.ndarray, nome_modelo: str, k: int, semente: int = config.SEMENTE) -> np.ndarray:
    modelo = construir_modelo(nome_modelo, k, semente)
    if nome_modelo == "mistura_gaussiana":
        return modelo.fit(matriz).predict(matriz)
    return modelo.fit_predict(matriz)


def metricas(matriz: np.ndarray, rotulos: np.ndarray) -> dict[str, float]:
    if len(set(rotulos)) < 2:
        return {"silhueta": np.nan, "davies_bouldin": np.nan, "calinski_harabasz": np.nan}
    return {
        "silhueta": float(silhouette_score(matriz, rotulos)),
        "davies_bouldin": float(davies_bouldin_score(matriz, rotulos)),
        "calinski_harabasz": float(calinski_harabasz_score(matriz, rotulos)),
    }


def varrer_k(
    base: pd.DataFrame,
    grupos: dict[str, list[str]] | None = None,
    k_minimo: int = config.K_MINIMO,
    k_maximo: int = config.K_MAXIMO,
) -> pd.DataFrame:
    """Roda os três modelos para cada grupo e cada k, com todas as métricas."""
    grupos = grupos or config.GRUPOS
    linhas = []
    for grupo, variaveis in grupos.items():
        matriz, variaveis_log = preparar_matriz(base, variaveis)
        for nome_modelo in MODELOS:
            for k in range(k_minimo, k_maximo + 1):
                rotulos = rotular(matriz, nome_modelo, k)
                linha = {
                    "grupo": grupo,
                    "nome_grupo": config.NOMES_GRUPOS.get(grupo, grupo),
                    "n_variaveis": len(variaveis),
                    "variaveis_com_log": len(variaveis_log),
                    "modelo": nome_modelo,
                    "nome_modelo": NOMES_MODELOS[nome_modelo],
                    "k": k,
                    "menor_cluster": int(pd.Series(rotulos).value_counts().min()),
                }
                linha.update(metricas(matriz, rotulos))
                if nome_modelo == "kmeans":
                    linha["inercia"] = float(
                        KMeans(n_clusters=k, random_state=config.SEMENTE, n_init=20)
                        .fit(matriz)
                        .inertia_
                    )
                linhas.append(linha)
    return pd.DataFrame(linhas)


def melhor_configuracao(varredura: pd.DataFrame, minimo_por_cluster: int = 15) -> pd.DataFrame:
    """Melhor k de cada grupo e modelo, exigindo cluster com tamanho utilizável."""
    validos = varredura[varredura["menor_cluster"] >= minimo_por_cluster]
    if validos.empty:
        validos = varredura
    return (
        validos.sort_values("silhueta", ascending=False)
        .groupby(["grupo", "modelo"], as_index=False)
        .first()
        .sort_values("silhueta", ascending=False)
        .reset_index(drop=True)
    )
