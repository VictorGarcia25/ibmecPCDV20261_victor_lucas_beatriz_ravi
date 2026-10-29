"""Explicar as praças com modelos supervisionados: que regras separam um tipo de praça do outro?

O rótulo da praça vira a resposta e as variáveis do modelo viram as entradas. Uma árvore rasa
traduz o agrupamento em regras com valores reais ("mais de X imobiliárias por 10 mil hab."), que
é o formato que a Loft consegue usar sem rodar o modelo. Um Random Forest mede o quanto essas
regras simples deixam escapar, e a importância por permutação e o SHAP dizem qual variável pesa
em cada praça.

Atenção ao que isto NÃO é: não é previsão de desempenho. O modelo aprende a reproduzir o
agrupamento, não a acertar vendas. Acurácia alta aqui quer dizer "as praças têm regra simples",
não "as praças predizem negócio".
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree

from . import config, descritiva, estilo

PROFUNDIDADE_ARVORE = 3
FOLDS = 5


def _modelos() -> dict:
    return {
        "Baseline: sempre a praça mais comum": DummyClassifier(strategy="most_frequent"),
        f"Árvore de decisão (profundidade {PROFUNDIDADE_ARVORE})": DecisionTreeClassifier(
            max_depth=PROFUNDIDADE_ARVORE, min_samples_leaf=15, random_state=config.SEMENTE
        ),
        "Random Forest (300 árvores)": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=3, random_state=config.SEMENTE, n_jobs=-1
        ),
    }


def _rotulos_curtos(variaveis: list[str]) -> list[str]:
    return [descritiva.rotulo(v) for v in variaveis]


def explicar(base: pd.DataFrame, variaveis: list[str]) -> dict[str, object]:
    """Validação cruzada estratificada, matriz de confusão, regras da árvore, permutação e SHAP.

    As variáveis entram em valor real, sem padronizar: árvore não precisa de escala, e assim os
    cortes das regras saem em unidades que a Loft entende.
    """
    estilo.aplicar()
    x = base[variaveis].astype(float)
    y = base["nome_cluster"].to_numpy()
    divisao = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=config.SEMENTE)

    linhas, previsoes = [], {}
    for nome, modelo in _modelos().items():
        previsto = cross_val_predict(modelo, x, y, cv=divisao)
        previsoes[nome] = previsto
        acertos = [
            accuracy_score(y[teste], previsto[teste]) for _, teste in divisao.split(x, y)
        ]
        linhas.append(
            {
                "modelo": nome,
                "acuracia": round(float(accuracy_score(y, previsto)), 3),
                "acuracia_balanceada": round(float(balanced_accuracy_score(y, previsto)), 3),
                "acuracia_desvio_entre_folds": round(float(np.std(acertos)), 3),
            }
        )
    validacao = pd.DataFrame(linhas)

    nome_floresta = "Random Forest (300 árvores)"
    nome_arvore = f"Árvore de decisão (profundidade {PROFUNDIDADE_ARVORE})"
    _grafico_confusao(y, previsoes[nome_floresta], previsoes[nome_arvore])

    arvore = _modelos()[nome_arvore].fit(x, y)
    regras = export_text(arvore, feature_names=_rotulos_curtos(variaveis), decimals=1, show_weights=False)
    _grafico_arvore(arvore, variaveis)

    importancia = _permutacao_fora_da_amostra(x, y, variaveis, divisao)
    _grafico_permutacao(importancia)

    floresta = _modelos()[nome_floresta].fit(x, y)
    shap_por_praca = _shap(floresta, x, variaveis)
    return {
        "validacao": validacao,
        "regras": regras,
        "importancia": importancia,
        "shap_por_praca": shap_por_praca,
    }


def _permutacao_fora_da_amostra(x, y, variaveis, divisao) -> pd.DataFrame:
    """Permutação medida só nos municípios que o modelo não viu em cada fold."""
    quedas = []
    for treino, teste in divisao.split(x, y):
        modelo = _modelos()["Random Forest (300 árvores)"].fit(x.iloc[treino], y[treino])
        resultado = permutation_importance(
            modelo, x.iloc[teste], y[teste], n_repeats=20, random_state=config.SEMENTE,
            scoring="balanced_accuracy",
        )
        quedas.append(resultado.importances_mean)
    quedas = np.array(quedas)
    return (
        pd.DataFrame(
            {
                "variavel": variaveis,
                "rotulo": _rotulos_curtos(variaveis),
                "queda_media_acuracia": quedas.mean(axis=0).round(4),
                "desvio_entre_folds": quedas.std(axis=0).round(4),
            }
        )
        .sort_values("queda_media_acuracia", ascending=False)
        .reset_index(drop=True)
    )


def _shap(floresta, x, variaveis) -> pd.DataFrame:
    explicador = shap.TreeExplainer(floresta)
    valores = explicador(x)   # municípios x variáveis x praças
    classes = list(floresta.classes_)

    medio = pd.DataFrame(
        np.abs(valores.values).mean(axis=0), index=_rotulos_curtos(variaveis), columns=classes
    )
    figura, eixo = plt.subplots(figsize=(11, 4.8))
    imagem = eixo.imshow(medio.to_numpy(), cmap="Blues", aspect="auto")
    eixo.set_xticks(range(len(classes)), [c.replace("Praça ", "") for c in classes], rotation=20, ha="right")
    eixo.set_yticks(range(len(medio)), medio.index)
    for i in range(medio.shape[0]):
        for j in range(medio.shape[1]):
            valor = medio.iat[i, j]
            eixo.text(j, i, f"{valor:.2f}", ha="center", va="center", fontsize=8,
                      color="white" if valor > medio.to_numpy().max() * 0.6 else "black")
    eixo.set_title("SHAP: quanto cada variável pesa na decisão de cada praça\n(média do |valor SHAP| sobre os municípios)")
    eixo.grid(False)
    figura.colorbar(imagem, ax=eixo, fraction=0.03)
    estilo.salvar(figura, "19_shap_por_praca")

    alvo = classes.index("Praça madura de locação") if "Praça madura de locação" in classes else 0
    explicacao = shap.Explanation(
        values=valores.values[:, :, alvo], base_values=valores.base_values[:, alvo],
        data=x.to_numpy(), feature_names=_rotulos_curtos(variaveis),
    )
    plt.figure()
    shap.plots.beeswarm(explicacao, show=False, max_display=len(variaveis), color_bar_label="valor da variável")
    figura = plt.gcf()
    figura.set_size_inches(10, 4.8)
    plt.gca().set_xlabel("valor SHAP (quanto empurra para esta praça)")
    plt.title(f"SHAP para '{classes[alvo]}': cada ponto é um município\nà direita = empurra para esta praça; cor = valor da variável")
    estilo.salvar(figura, "20_shap_praca_madura")
    return medio.round(3).reset_index(names="variavel")


def _grafico_confusao(y, previsto_floresta, previsto_arvore) -> None:
    rotulos = sorted(set(y))
    curtos = [r.replace("Praça ", "") for r in rotulos]
    figura, eixos = plt.subplots(1, 2, figsize=(15, 6))
    for eixo, previsto, titulo in [
        (eixos[0], previsto_arvore, f"Árvore rasa (profundidade {PROFUNDIDADE_ARVORE})"),
        (eixos[1], previsto_floresta, "Random Forest"),
    ]:
        ConfusionMatrixDisplay.from_predictions(
            y, previsto, labels=rotulos, display_labels=curtos, normalize="true",
            cmap="Blues", values_format=".0%", ax=eixo, colorbar=False,
        )
        eixo.set_title(f"{titulo}\nacerto balanceado = {balanced_accuracy_score(y, previsto):.0%}")
        eixo.set_xlabel("praça prevista (validação cruzada)")
        eixo.set_ylabel("praça do modelo")
        eixo.tick_params(axis="x", rotation=30)
        eixo.grid(False)
    figura.tight_layout()
    estilo.salvar(figura, "17_matriz_confusao_pracas")


def _grafico_arvore(arvore, variaveis) -> None:
    figura, eixo = plt.subplots(figsize=(20, 8))
    plot_tree(
        arvore, feature_names=_rotulos_curtos(variaveis),
        class_names=[c.replace("Praça ", "") for c in arvore.classes_],
        filled=True, rounded=True, impurity=False, proportion=True, fontsize=8, ax=eixo,
        precision=1,
    )
    eixo.set_title("As praças em regras: árvore de decisão rasa treinada para reproduzir o agrupamento")
    estilo.salvar(figura, "18_arvore_regras_pracas")


def _grafico_permutacao(tabela: pd.DataFrame) -> None:
    figura, eixo = plt.subplots(figsize=(9, 4.2))
    ordem = tabela.iloc[::-1]
    eixo.barh(ordem["rotulo"], ordem["queda_media_acuracia"], xerr=ordem["desvio_entre_folds"],
              color=estilo.AZUL, ecolor=estilo.CINZA, capsize=3)
    eixo.set_xlabel("queda no acerto balanceado ao embaralhar a variável")
    eixo.set_title("Importância por permutação, medida fora da amostra (5 folds)")
    estilo.salvar(figura, "21_importancia_permutacao")
