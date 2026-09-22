"""Baselines, cotovelo, estabilidade e ablação."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, silhouette_score

from . import clustering, config, descritiva


def cotovelo(varredura: pd.DataFrame, grupo: str) -> int:
    """k do cotovelo pelo ponto mais distante da reta que liga os extremos da inércia."""
    curva = (
        varredura[(varredura["grupo"] == grupo) & (varredura["modelo"] == "kmeans")]
        .sort_values("k")[["k", "inercia"]]
        .dropna()
    )
    k = curva["k"].to_numpy(dtype=float)
    inercia = curva["inercia"].to_numpy(dtype=float)
    k_norm = (k - k.min()) / (k.max() - k.min())
    i_norm = (inercia - inercia.min()) / (inercia.max() - inercia.min())
    # Distância de cada ponto à reta que une o primeiro e o último ponto da curva.
    distancia = np.abs(i_norm + k_norm - 1) / np.sqrt(2)
    return int(k[int(distancia.argmax())])


def rotulos_baseline(base: pd.DataFrame, tipo: str, k: int, semente: int = config.SEMENTE) -> np.ndarray:
    if tipo == "regiao":
        return base["regiao"].astype("category").cat.codes.to_numpy()
    if tipo == "porte":
        return base["porte"].astype("category").cat.codes.to_numpy()
    if tipo == "aleatorio":
        gerador = np.random.default_rng(semente)
        return gerador.integers(0, k, size=len(base))
    raise ValueError(f"Baseline desconhecido: {tipo}")


def comparar_baselines(
    base: pd.DataFrame,
    variaveis: list[str],
    rotulos_cluster: np.ndarray,
    n_repeticoes_aleatorio: int = 30,
) -> pd.DataFrame:
    """Silhueta do nosso agrupamento contra geografia, porte e sorteio, no mesmo espaço."""
    matriz, _ = clustering.preparar_matriz(base, variaveis)
    k = len(set(rotulos_cluster))

    linhas = [
        {
            "agrupamento": "Clusters da POC",
            "n_grupos": k,
            "silhueta": float(silhouette_score(matriz, rotulos_cluster)),
            "rand_ajustado_vs_cluster": 1.0,
        }
    ]
    for tipo, nome in [
        ("regiao", "Baseline: 5 regiões do IBGE"),
        ("porte", "Baseline: faixas de porte populacional"),
    ]:
        rotulos = rotulos_baseline(base, tipo, k)
        linhas.append(
            {
                "agrupamento": nome,
                "n_grupos": len(set(rotulos)),
                "silhueta": float(silhouette_score(matriz, rotulos)),
                "rand_ajustado_vs_cluster": float(adjusted_rand_score(rotulos_cluster, rotulos)),
            }
        )

    silhuetas, randes = [], []
    for repeticao in range(n_repeticoes_aleatorio):
        rotulos = rotulos_baseline(base, "aleatorio", k, semente=config.SEMENTE + repeticao)
        silhuetas.append(silhouette_score(matriz, rotulos))
        randes.append(adjusted_rand_score(rotulos_cluster, rotulos))
    linhas.append(
        {
            "agrupamento": f"Baseline: sorteio aleatório (média de {n_repeticoes_aleatorio})",
            "n_grupos": k,
            "silhueta": float(np.mean(silhuetas)),
            "rand_ajustado_vs_cluster": float(np.mean(randes)),
        }
    )
    return pd.DataFrame(linhas).round(4)


def estabilidade_sementes(
    base: pd.DataFrame,
    variaveis: list[str],
    nome_modelo: str,
    k: int,
    n_sementes: int = config.N_SEMENTES_ROBUSTEZ,
) -> pd.DataFrame:
    """Rand ajustado entre a solução da semente 42 e as demais sementes."""
    matriz, _ = clustering.preparar_matriz(base, variaveis)
    referencia = clustering.rotular(matriz, nome_modelo, k, semente=config.SEMENTE)
    linhas = []
    for i in range(n_sementes):
        semente = config.SEMENTE + i
        rotulos = clustering.rotular(matriz, nome_modelo, k, semente=semente)
        linhas.append(
            {
                "semente": semente,
                "rand_ajustado_vs_referencia": round(
                    float(adjusted_rand_score(referencia, rotulos)), 4
                ),
                "silhueta": round(float(silhouette_score(matriz, rotulos)), 4),
            }
        )
    return pd.DataFrame(linhas)


def estabilidade_bootstrap(
    base: pd.DataFrame,
    variaveis: list[str],
    nome_modelo: str,
    k: int,
    n_bootstrap: int = config.N_BOOTSTRAP,
    fracao: float = 0.8,
) -> pd.DataFrame:
    """Reamostra municípios e mede o Rand ajustado nos municípios em comum entre rodadas.

    Duas escolhas de protocolo importam aqui. A reamostragem é sem reposição, ou seja
    subamostragem de uma fração fixa: com reposição, os municípios duplicados ficam a distância
    zero e inflam a concordância. E a winsorização, o log e a padronização são refeitos dentro
    de cada subamostra, não herdados da base cheia, senão parte da informação do conjunto todo
    vaza para dentro de cada rodada e a estabilidade sai otimista.
    """
    gerador = np.random.default_rng(config.SEMENTE)
    n = len(base)
    tamanho = int(n * fracao)

    resultados = []
    anterior_indices, anterior_rotulos = None, None
    for _ in range(n_bootstrap):
        indices = gerador.choice(n, size=tamanho, replace=False)
        matriz, _ = clustering.preparar_matriz(
            base.iloc[indices].reset_index(drop=True), variaveis
        )
        rotulos = clustering.rotular(matriz, nome_modelo, k)
        if anterior_indices is not None:
            comuns = np.intersect1d(indices, anterior_indices)
            if len(comuns) > k:
                mapa_atual = dict(zip(indices, rotulos))
                mapa_anterior = dict(zip(anterior_indices, anterior_rotulos))
                resultados.append(
                    adjusted_rand_score(
                        [mapa_anterior[i] for i in comuns], [mapa_atual[i] for i in comuns]
                    )
                )
        anterior_indices, anterior_rotulos = indices, rotulos

    serie = pd.Series(resultados)
    return pd.DataFrame(
        [
            {
                "modelo": clustering.NOMES_MODELOS[nome_modelo],
                "k": k,
                "metodo": "subamostragem sem reposição",
                "fracao_reamostrada": fracao,
                "n_comparacoes": len(serie),
                "rand_ajustado_medio": round(float(serie.mean()), 4),
                "rand_ajustado_desvio": round(float(serie.std()), 4),
                "rand_ajustado_p5": round(float(serie.quantile(0.05)), 4),
                "rand_ajustado_p95": round(float(serie.quantile(0.95)), 4),
            }
        ]
    )


def diferenca_silhueta(
    base: pd.DataFrame,
    configuracoes: list[tuple[str, list[str], str, int]],
    n_repeticoes: int = 200,
    fracao: float = 0.8,
) -> pd.DataFrame:
    """Intervalo da diferença de silhueta entre duas configurações, sob reamostragem.

    Serve para não tratar como vantagem uma diferença de terceira casa decimal: se o intervalo
    de 95% cruza o zero, as duas configurações são equivalentes e o desempate tem de ser outro.
    """
    if len(configuracoes) < 2:
        return pd.DataFrame()

    gerador = np.random.default_rng(config.SEMENTE)
    n = len(base)
    tamanho = int(n * fracao)

    amostras: dict[str, list[float]] = {nome: [] for nome, _, _, _ in configuracoes}
    for _ in range(n_repeticoes):
        indices = gerador.choice(n, size=tamanho, replace=False)
        recorte_base = base.iloc[indices].reset_index(drop=True)
        for nome, variaveis, modelo, k in configuracoes:
            # Preparo refeito dentro da subamostra, pelo mesmo motivo da estabilidade.
            recorte, _ = clustering.preparar_matriz(recorte_base, variaveis)
            rotulos = clustering.rotular(recorte, modelo, k)
            if len(set(rotulos)) < 2:
                amostras[nome].append(np.nan)
                continue
            amostras[nome].append(float(silhouette_score(recorte, rotulos)))

    primeiro, segundo = configuracoes[0][0], configuracoes[1][0]
    diferenca = pd.Series(amostras[primeiro]) - pd.Series(amostras[segundo])
    diferenca = diferenca.dropna()
    inferior, superior = diferenca.quantile([0.025, 0.975])
    return pd.DataFrame(
        [
            {
                "configuracao_a": primeiro,
                "configuracao_b": segundo,
                "silhueta_media_a": round(float(pd.Series(amostras[primeiro]).mean()), 4),
                "silhueta_media_b": round(float(pd.Series(amostras[segundo]).mean()), 4),
                "diferenca_media": round(float(diferenca.mean()), 4),
                "intervalo_95_inferior": round(float(inferior), 4),
                "intervalo_95_superior": round(float(superior), 4),
                "vezes_que_a_venceu_pct": round(float((diferenca > 0).mean() * 100), 1),
                "diferenca_significativa": bool(inferior > 0 or superior < 0),
                "n_reamostragens": len(diferenca),
            }
        ]
    )


def ablacao(
    base: pd.DataFrame,
    variaveis: list[str],
    nome_modelo: str,
    k: int,
) -> pd.DataFrame:
    """Silhueta ao remover cada variável, uma por vez."""
    matriz_cheia, _ = clustering.preparar_matriz(base, variaveis)
    rotulos_cheios = clustering.rotular(matriz_cheia, nome_modelo, k)
    referencia = silhouette_score(matriz_cheia, rotulos_cheios)

    linhas = []
    for variavel in variaveis:
        restantes = [v for v in variaveis if v != variavel]
        matriz, _ = clustering.preparar_matriz(base, restantes)
        rotulos = clustering.rotular(matriz, nome_modelo, k)
        silhueta = silhouette_score(matriz, rotulos)
        linhas.append(
            {
                "variavel_removida": variavel,
                "rotulo": descritiva.rotulo(variavel),
                "silhueta_sem_ela": round(float(silhueta), 4),
                "silhueta_completa": round(float(referencia), 4),
                "variacao": round(float(silhueta - referencia), 4),
                "rand_ajustado_vs_completo": round(
                    float(adjusted_rand_score(rotulos_cheios, rotulos)), 4
                ),
            }
        )
    return pd.DataFrame(linhas).sort_values("variacao").reset_index(drop=True)
