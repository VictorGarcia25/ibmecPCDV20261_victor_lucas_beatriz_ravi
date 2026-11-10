"""Etapa 2 do projeto: aprofundamento do agrupamento escolhido.

Reúne quatro leituras complementares, todas sobre as praças já formadas:
densidade (DBSCAN, HDBSCAN e Isolation Forest), retrato no plano (PCA), parentesco entre as
variáveis (dendrograma) e explicação das praças por modelos supervisionados (árvore, Random
Forest, permutação e SHAP).
"""

from __future__ import annotations

import pandas as pd

from . import config, densidade, explicacao, visao


def _salvar(df: pd.DataFrame, nome: str) -> None:
    df.to_csv(config.DIR_TABELAS / f"{nome}.csv", index=False)


def executar(base: pd.DataFrame, variaveis: list[str]) -> dict[str, object]:
    resultado: dict[str, object] = {}

    dens = densidade.comparar(base, variaveis)
    _salvar(dens["resumo"], "30_densidade_resumo")
    _salvar(dens["sensibilidade"], "31_densidade_sensibilidade_eps")
    _salvar(dens["cruzamento"], "32_densidade_vs_pracas")
    atipicas = densidade.cidades_atipicas(base)
    _salvar(atipicas, "33_cidades_atipicas")
    resultado.update(densidade=dens, atipicas=atipicas)

    cargas = visao.pca_das_pracas(base, variaveis)
    _salvar(cargas, "34_pca_cargas")
    parentesco = visao.dendrograma_variaveis(base)
    _salvar(parentesco, "35_parentesco_variaveis")
    resultado.update(pca=cargas, parentesco=parentesco)

    exp = explicacao.explicar(base, variaveis)
    _salvar(exp["validacao"], "36_explicacao_validacao_cruzada")
    _salvar(exp["importancia"], "37_importancia_permutacao")
    _salvar(exp["shap_por_praca"], "38_shap_por_praca")
    (config.DIR_TABELAS / "39_regras_da_arvore.txt").write_text(exp["regras"], encoding="utf-8")
    resultado.update(explicacao=exp)
    return resultado
