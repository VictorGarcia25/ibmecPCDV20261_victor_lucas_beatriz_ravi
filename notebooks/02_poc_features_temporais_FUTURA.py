#%% IMPORTS

import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from dotenv import load_dotenv

from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression, PoissonRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


#%% CAMINHO DOS DADOS

load_dotenv()

caminho_dados = os.getenv("DATA_DIR")

if caminho_dados is None:
    raise ValueError("A variável DATA_DIR não foi encontrada. Confira o arquivo .env.")

DATA_DIR = Path(caminho_dados)

print("\nPasta configurada:")
print(DATA_DIR)

print("\nA pasta existe?")
print(DATA_DIR.exists())


#%% PASTAS DO PROJETO

PROJECT_DIR = Path(__file__).resolve().parents[1]

TABLES_DIR = PROJECT_DIR / "reports" / "tables"
FIGURES_DIR = PROJECT_DIR / "reports" / "figures"

TABLES_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


#%% LEITURA DA BASE

arquivo_attribution = DATA_DIR / "criteo_attribution_5milhoes.csv"

df = pd.read_csv(arquivo_attribution, nrows=100000)

print("\nTamanho da amostra:")
print(df.shape)

print("\nNúmero de campanhas:")
print(df["campaign"].nunique())


#%% CRIAR PERÍODO DE 1 HORA

df["hora"] = df["timestamp"] // 3600

print("\nQuantidade de horas:")
print(df["hora"].nunique())


#%% AGREGAÇÃO POR CAMPANHA E HORA

campanhas = (
    df.groupby(["hora", "campaign"])
    .agg(
        impressoes=("uid", "size"),
        cliques=("click", "sum"),
        conversoes=("conversion", "sum"),
        conversoes_atribuidas=("attribution", "sum"),
        custo_total=("cost", "sum"),
        custo_medio=("cost", "mean")
    )
    .reset_index()
)

campanhas["ctr"] = campanhas["cliques"] / campanhas["impressoes"]
campanhas["taxa_conversao"] = campanhas["conversoes_atribuidas"] / campanhas["impressoes"]

print("\nTamanho da base agregada:")
print(campanhas.shape)


#%% DIAGNÓSTICO DE ZEROS

proporcao_zero = (campanhas["conversoes_atribuidas"] == 0).mean()

print(f"\nJanelas sem conversão: {proporcao_zero * 100:.2f}%")


#%% CORRELAÇÃO ENTRE IMPRESSÕES E CLIQUES

print("\nCorrelação entre impressões e cliques:")
print(campanhas[["impressoes", "cliques"]].corr())


#%% CRIAR FEATURES DA HORA ANTERIOR

# Criamos uma cópia dos dados de cada campanha/hora.
# Somamos 1 à hora para que os valores sejam associados
# exatamente à hora seguinte da mesma campanha.

lag = campanhas[
    [
        "hora",
        "campaign",
        "impressoes",
        "cliques",
        "conversoes_atribuidas",
        "custo_total",
        "custo_medio",
        "ctr"
    ]
].copy()

lag["hora"] = lag["hora"] + 1

lag = lag.rename(
    columns={
        "impressoes": "impressoes_hora_anterior",
        "cliques": "cliques_hora_anterior",
        "conversoes_atribuidas": "conversoes_hora_anterior",
        "custo_total": "custo_total_hora_anterior",
        "custo_medio": "custo_medio_hora_anterior",
        "ctr": "ctr_hora_anterior"
    }
)


#%% JUNTAR HORA ATUAL COM HORA ANTERIOR

campanhas_temporais = campanhas.merge(
    lag,
    on=["hora", "campaign"],
    how="left"
)

print("\nTamanho antes de retirar linhas sem histórico:")
print(campanhas_temporais.shape)


#%% DEFINIR FEATURES TEMPORAIS

features_temporais = [
    "impressoes_hora_anterior",
    "cliques_hora_anterior",
    "conversoes_hora_anterior",
    "custo_total_hora_anterior",
    "custo_medio_hora_anterior",
    "ctr_hora_anterior"
]

campanhas_temporais = campanhas_temporais.dropna(
    subset=features_temporais
).copy()

print("\nTamanho depois de manter apenas campanhas com hora anterior:")
print(campanhas_temporais.shape)


#%% VER EXEMPLO DAS FEATURES TEMPORAIS

print("\nExemplo das features temporais:")

print(
    campanhas_temporais[
        [
            "hora",
            "campaign",
            "conversoes_atribuidas",
            "impressoes_hora_anterior",
            "cliques_hora_anterior",
            "conversoes_hora_anterior",
            "custo_total_hora_anterior",
            "ctr_hora_anterior"
        ]
    ].head(20)
)


#%% DEFINIR X E Y

X = campanhas_temporais[features_temporais]
y = campanhas_temporais["conversoes_atribuidas"]

print("\nFeatures utilizadas:")
print(features_temporais)

print("\nVariável alvo:")
print("conversoes_atribuidas")


#%% DIVISÃO TEMPORAL ENTRE TREINO E TESTE

horas = sorted(campanhas_temporais["hora"].unique())

ponto_corte = int(len(horas) * 0.80)

horas_treino = horas[:ponto_corte]
horas_teste = horas[ponto_corte:]

treino = campanhas_temporais[
    campanhas_temporais["hora"].isin(horas_treino)
].copy()

teste = campanhas_temporais[
    campanhas_temporais["hora"].isin(horas_teste)
].copy()

X_train = treino[features_temporais]
y_train = treino["conversoes_atribuidas"]

X_test = teste[features_temporais]
y_test = teste["conversoes_atribuidas"]

print("\nHoras de treino:")
print(horas_treino)

print("\nHoras de teste:")
print(horas_teste)

print("\nTamanho do treino:")
print(X_train.shape)

print("\nTamanho do teste:")
print(X_test.shape)


#%% FUNÇÃO DE AVALIAÇÃO

def avaliar_modelo(nome, y_real, y_previsto):

    mae = mean_absolute_error(y_real, y_previsto)
    rmse = np.sqrt(mean_squared_error(y_real, y_previsto))
    r2 = r2_score(y_real, y_previsto)

    return {
        "Modelo": nome,
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2
    }


#%% BASELINE MÍNIMO - DUMMY

baseline = DummyRegressor(strategy="mean")

baseline.fit(X_train, y_train)

y_pred_dummy = baseline.predict(X_test)

resultado_dummy = avaliar_modelo(
    "Baseline mínimo - Dummy",
    y_test,
    y_pred_dummy
)

print("\n============================")
print("BASELINE MÍNIMO - DUMMY")
print("============================")

print("MAE:", resultado_dummy["MAE"])
print("RMSE:", resultado_dummy["RMSE"])
print("R²:", resultado_dummy["R2"])


#%% BASELINE TEMPORAL - REPETIR CONVERSÕES DA HORA ANTERIOR

# Regra extremamente simples:
# assumir que a próxima hora terá o mesmo número
# de conversões atribuídas observado na hora anterior.

y_pred_baseline_temporal = X_test["conversoes_hora_anterior"].to_numpy()

resultado_baseline_temporal = avaliar_modelo(
    "Baseline temporal - Conversões hora anterior",
    y_test,
    y_pred_baseline_temporal
)

print("\n==========================================")
print("BASELINE TEMPORAL - CONVERSÕES HORA ANTERIOR")
print("==========================================")

print("MAE:", resultado_baseline_temporal["MAE"])
print("RMSE:", resultado_baseline_temporal["RMSE"])
print("R²:", resultado_baseline_temporal["R2"])


#%% BASELINE SIMPLES - TAXA HISTÓRICA X IMPRESSÕES ANTERIORES

taxa_historica = (
    y_train.sum()
    / X_train["impressoes_hora_anterior"].sum()
)

y_pred_taxa = (
    X_test["impressoes_hora_anterior"].to_numpy()
    * taxa_historica
)

resultado_taxa = avaliar_modelo(
    "Baseline simples - Taxa histórica x Impressões anteriores",
    y_test,
    y_pred_taxa
)

print("\n=====================================================")
print("BASELINE SIMPLES - TAXA X IMPRESSÕES DA HORA ANTERIOR")
print("=====================================================")

print("Taxa histórica:", taxa_historica)
print("MAE:", resultado_taxa["MAE"])
print("RMSE:", resultado_taxa["RMSE"])
print("R²:", resultado_taxa["R2"])


#%% MODELO 1 - REGRESSÃO LINEAR

modelo_lr = LinearRegression()

modelo_lr.fit(X_train, y_train)

y_pred_lr = modelo_lr.predict(X_test)

resultado_lr = avaliar_modelo(
    "Regressão Linear - Features temporais",
    y_test,
    y_pred_lr
)

print("\n============================")
print("REGRESSÃO LINEAR")
print("============================")

print("MAE:", resultado_lr["MAE"])
print("RMSE:", resultado_lr["RMSE"])
print("R²:", resultado_lr["R2"])


#%% MODELO 2 - RANDOM FOREST

modelo_rf = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    n_jobs=-1
)

modelo_rf.fit(X_train, y_train)

y_pred_rf = modelo_rf.predict(X_test)

resultado_rf = avaliar_modelo(
    "Random Forest - Features temporais",
    y_test,
    y_pred_rf
)

print("\n============================")
print("RANDOM FOREST")
print("============================")

print("MAE:", resultado_rf["MAE"])
print("RMSE:", resultado_rf["RMSE"])
print("R²:", resultado_rf["R2"])


#%% MODELO 3 - POISSON REGRESSOR

# Poisson é apropriado para problemas em que o alvo
# representa uma contagem, como número de conversões.

modelo_poisson = Pipeline(
    [
        ("scaler", StandardScaler()),
        ("poisson", PoissonRegressor(alpha=1.0, max_iter=1000))
    ]
)

modelo_poisson.fit(X_train, y_train)

y_pred_poisson = modelo_poisson.predict(X_test)

resultado_poisson = avaliar_modelo(
    "Poisson Regressor - Features temporais",
    y_test,
    y_pred_poisson
)

print("\n============================")
print("POISSON REGRESSOR")
print("============================")

print("MAE:", resultado_poisson["MAE"])
print("RMSE:", resultado_poisson["RMSE"])
print("R²:", resultado_poisson["R2"])


#%% COMPARAÇÃO DOS MODELOS

resultados = pd.DataFrame(
    [
        resultado_dummy,
        resultado_baseline_temporal,
        resultado_taxa,
        resultado_lr,
        resultado_rf,
        resultado_poisson
    ]
)

resultados_ordenados = resultados.sort_values("RMSE")

print("\n============================")
print("COMPARAÇÃO DOS MODELOS")
print("============================")

print(resultados_ordenados.to_string(index=False))


#%% IMPORTÂNCIA DAS VARIÁVEIS - RANDOM FOREST

importancias = pd.DataFrame(
    {
        "Variavel": features_temporais,
        "Importancia": modelo_rf.feature_importances_
    }
)

importancias = importancias.sort_values(
    "Importancia",
    ascending=False
)

print("\n============================")
print("IMPORTÂNCIA DAS VARIÁVEIS")
print("============================")

print(importancias.to_string(index=False))


#%% GRÁFICO - COMPARAÇÃO DO RMSE

plt.figure(figsize=(12, 6))

plt.bar(
    resultados_ordenados["Modelo"],
    resultados_ordenados["RMSE"]
)

plt.title("Comparação do RMSE - Modelos com Features Temporais")
plt.xlabel("Modelo")
plt.ylabel("RMSE")
plt.xticks(rotation=25, ha="right")
plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "comparacao_rmse_temporal.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()


#%% GRÁFICO - IMPORTÂNCIA DAS VARIÁVEIS

plt.figure(figsize=(10, 5))

plt.bar(
    importancias["Variavel"],
    importancias["Importancia"]
)

plt.title("Importância das Features Temporais - Random Forest")
plt.xlabel("Variável")
plt.ylabel("Importância")
plt.xticks(rotation=35, ha="right")
plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "importancia_variaveis_temporais.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()


#%% RESULTADOS REAIS X PREVISTOS

comparacao = pd.DataFrame(
    {
        "Real": y_test.to_numpy(),
        "Dummy": y_pred_dummy,
        "Baseline_Hora_Anterior": y_pred_baseline_temporal,
        "Baseline_Taxa": y_pred_taxa,
        "Regressao_Linear": y_pred_lr,
        "Random_Forest": y_pred_rf,
        "Poisson": y_pred_poisson
    }
)

print("\nPrimeiras previsões:")
print(comparacao.head(20))


#%% CONCLUSÃO AUTOMÁTICA

modelos_aprendidos = resultados[
    resultados["Modelo"].isin(
        [
            "Regressão Linear - Features temporais",
            "Random Forest - Features temporais",
            "Poisson Regressor - Features temporais"
        ]
    )
]

melhor_modelo = modelos_aprendidos.loc[
    modelos_aprendidos["RMSE"].idxmin()
]

nome_melhor = melhor_modelo["Modelo"]
rmse_melhor = melhor_modelo["RMSE"]
mae_melhor = melhor_modelo["MAE"]
r2_melhor = melhor_modelo["R2"]

print("\n============================")
print("CONCLUSÃO DA POC TEMPORAL")
print("============================")

print(f"\nMelhor modelo treinado: {nome_melhor}")
print(f"MAE: {mae_melhor:.4f}")
print(f"RMSE: {rmse_melhor:.4f}")
print(f"R²: {r2_melhor:.4f}")


#%% COMPARAÇÃO COM BASELINE TEMPORAL

rmse_baseline_temporal = resultado_baseline_temporal["RMSE"]

if rmse_melhor < rmse_baseline_temporal:

    reducao = (
        (rmse_baseline_temporal - rmse_melhor)
        / rmse_baseline_temporal
    ) * 100

    print(f"\nO {nome_melhor} superou o baseline temporal.")
    print(f"Redução do RMSE em relação à hora anterior: {reducao:.2f}%")

else:

    print(f"\nO {nome_melhor} não superou o baseline temporal.")


#%% INTERPRETAÇÃO METODOLÓGICA

print("\nNesta versão, nenhuma feature da hora atual é utilizada para prever a conversão da própria hora.")

print(
    "As previsões são construídas exclusivamente a partir de informações da hora anterior da mesma campanha."
)

print(
    "Isso reduz o problema de utilizar informações que ainda não estariam disponíveis no momento da previsão."
)

