#%% IMPORTS

import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv


#%% CAMINHO DOS DADOS

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR"))

print("Pasta configurada:")
print(DATA_DIR)

print("\nA pasta existe?")
print(DATA_DIR.exists())


#%% VER ARQUIVOS DISPONÍVEIS

print("\nArquivos encontrados:")

for arquivo in DATA_DIR.iterdir():
    print(arquivo.name)

#%% LEITURA INICIAL DA BASE

arquivo_attribution = DATA_DIR / "criteo_attribution_5milhoes.csv"

df = pd.read_csv(
    arquivo_attribution,
    nrows=100000
)

print("\nTamanho da amostra:")
print(df.shape)

print("\nColunas:")
print(df.columns.tolist())

print("\nPrimeiras linhas:")
print(df.head())

print("\nTipos das variáveis:")
print(df.dtypes)

#%% INFORMAÇÕES GERAIS

print("\nInformações da base:")
df.info()

print("\nValores ausentes:")
print(df.isnull().sum())

print("\nQuantidade de duplicados:")
print(df.duplicated().sum())

print("\nEstatística descritiva:")
print(df.describe())

#%% VARIÁVEIS PRINCIPAIS DO NEGÓCIO

print("\nDistribuição de conversão:")
print(df["conversion"].value_counts())
print(df["conversion"].value_counts(normalize=True))

print("\nDistribuição de clique:")
print(df["click"].value_counts())
print(df["click"].value_counts(normalize=True))

print("\nNúmero de campanhas:")
print(df["campaign"].nunique())

print("\nCusto médio:")
print(df["cost"].mean())

#%% ENTENDER CONVERSÕES E ATRIBUIÇÕES

df_convertidos = df[df["conversion"] == 1]

print("\nLinhas com conversão:")
print(len(df_convertidos))

print("\nConversões únicas:")
print(df_convertidos["conversion_id"].nunique())

print("\nConversões atribuídas à Criteo:")
print(df["attribution"].sum())

print("\nDistribuição de attribution:")
print(df["attribution"].value_counts())

print("\nConversões por attribution:")
print(
    pd.crosstab(
        df["conversion"],
        df["attribution"]
    )
)

#%% CRIAR PERÍODO DE 1 HORA

df["hora"] = df["timestamp"] // 3600

print(df[["timestamp", "hora"]].head())
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

print(campanhas.head())
print(campanhas.shape)

#%% INDICADORES DAS CAMPANHAS

campanhas["ctr"] = (
    campanhas["cliques"] /
    campanhas["impressoes"]
)

campanhas["taxa_conversao"] = (
    campanhas["conversoes_atribuidas"] /
    campanhas["impressoes"]
)

print(campanhas.head())

#%% CONFERIR A BASE AGREGADA

print("\nTamanho da base de campanhas:")
print(campanhas.shape)

print("\nResumo das conversões atribuídas:")
print(campanhas["conversoes_atribuidas"].describe())

print("\nJanelas sem conversão:")
print((campanhas["conversoes_atribuidas"] == 0).mean())

#%% DEFINIR X E Y

# Variáveis que serão usadas para prever
# o número de conversões atribuídas por campanha/hora
features = [
    "impressoes",
    "cliques",
    "custo_total",
    "custo_medio",
    "ctr"
]

X = campanhas[features]
y = campanhas["conversoes_atribuidas"]

print("\nTamanho de X:")
print(X.shape)

print("\nTamanho de y:")
print(y.shape)


#%% DIVISÃO TEMPORAL ENTRE TREINO E TESTE

# Como os dados têm uma sequência temporal,
# usamos as primeiras horas para treino
# e as últimas horas para teste.

horas = sorted(campanhas["hora"].unique())

ponto_corte = int(len(horas) * 0.80)

horas_treino = horas[:ponto_corte]
horas_teste = horas[ponto_corte:]

treino = campanhas[
    campanhas["hora"].isin(horas_treino)
].copy()

teste = campanhas[
    campanhas["hora"].isin(horas_teste)
].copy()

X_train = treino[features]
y_train = treino["conversoes_atribuidas"]

X_test = teste[features]
y_test = teste["conversoes_atribuidas"]

print("\nQuantidade de horas:")
print(len(horas))

print("\nHoras utilizadas no treino:")
print(horas_treino)

print("\nHoras utilizadas no teste:")
print(horas_teste)

print("\nTamanho do treino:")
print(X_train.shape)

print("\nTamanho do teste:")
print(X_test.shape)


#%% IMPORTAR MODELOS E MÉTRICAS

from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

import numpy as np


#%% BASELINE - DUMMY REGRESSOR

# O DummyRegressor será nosso baseline.
# Ele faz uma previsão simples baseada na média
# das conversões observadas no conjunto de treino.

baseline = DummyRegressor(
    strategy="mean"
)

baseline.fit(
    X_train,
    y_train
)

y_pred_baseline = baseline.predict(
    X_test
)

mae_baseline = mean_absolute_error(
    y_test,
    y_pred_baseline
)

rmse_baseline = np.sqrt(
    mean_squared_error(
        y_test,
        y_pred_baseline
    )
)

r2_baseline = r2_score(
    y_test,
    y_pred_baseline
)

print("\n============================")
print("BASELINE - DUMMY REGRESSOR")
print("============================")

print("MAE:", mae_baseline)
print("RMSE:", rmse_baseline)
print("R²:", r2_baseline)


#%% MODELO 1 - REGRESSÃO LINEAR

modelo_lr = LinearRegression()

modelo_lr.fit(
    X_train,
    y_train
)

y_pred_lr = modelo_lr.predict(
    X_test
)

mae_lr = mean_absolute_error(
    y_test,
    y_pred_lr
)

rmse_lr = np.sqrt(
    mean_squared_error(
        y_test,
        y_pred_lr
    )
)

r2_lr = r2_score(
    y_test,
    y_pred_lr
)

print("\n============================")
print("REGRESSÃO LINEAR")
print("============================")

print("MAE:", mae_lr)
print("RMSE:", rmse_lr)
print("R²:", r2_lr)


#%% MODELO 2 - RANDOM FOREST

modelo_rf = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    n_jobs=-1
)

modelo_rf.fit(
    X_train,
    y_train
)

y_pred_rf = modelo_rf.predict(
    X_test
)

mae_rf = mean_absolute_error(
    y_test,
    y_pred_rf
)

rmse_rf = np.sqrt(
    mean_squared_error(
        y_test,
        y_pred_rf
    )
)

r2_rf = r2_score(
    y_test,
    y_pred_rf
)

print("\n============================")
print("RANDOM FOREST")
print("============================")

print("MAE:", mae_rf)
print("RMSE:", rmse_rf)
print("R²:", r2_rf)


#%% COMPARAÇÃO DOS MODELOS

resultados = pd.DataFrame({
    "Modelo": [
        "DummyRegressor",
        "Regressão Linear",
        "Random Forest"
    ],

    "MAE": [
        mae_baseline,
        mae_lr,
        mae_rf
    ],

    "RMSE": [
        rmse_baseline,
        rmse_lr,
        rmse_rf
    ],

    "R2": [
        r2_baseline,
        r2_lr,
        r2_rf
    ]
})

print("\n============================")
print("COMPARAÇÃO DOS MODELOS")
print("============================")

print(
    resultados.sort_values("RMSE")
)


#%% IMPORTÂNCIA DAS VARIÁVEIS - RANDOM FOREST

importancias = pd.DataFrame({
    "Variavel": features,
    "Importancia": modelo_rf.feature_importances_
})

importancias = importancias.sort_values(
    "Importancia",
    ascending=False
)

print("\n============================")
print("IMPORTÂNCIA DAS VARIÁVEIS")
print("============================")

print(importancias)

#%% PASTAS PARA SALVAR RESULTADOS

PROJECT_DIR = Path(__file__).resolve().parents[1]

TABLES_DIR = PROJECT_DIR / "reports" / "tables"
FIGURES_DIR = PROJECT_DIR / "reports" / "figures"

TABLES_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

print("\nPasta das tabelas:")
print(TABLES_DIR)

print("\nPasta dos gráficos:")
print(FIGURES_DIR)

#%% GRÁFICO - COMPARAÇÃO DO RMSE

#%% GRÁFICO - COMPARAÇÃO DO RMSE

import matplotlib.pyplot as plt

plt.figure(figsize=(8, 5))

plt.bar(
    resultados["Modelo"],
    resultados["RMSE"]
)

plt.title("Comparação do RMSE dos Modelos")
plt.xlabel("Modelo")
plt.ylabel("RMSE")
plt.xticks(rotation=15)

plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "comparacao_rmse.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()


#%% GRÁFICO - IMPORTÂNCIA DAS VARIÁVEIS

plt.figure(figsize=(8, 5))

plt.bar(
    importancias["Variavel"],
    importancias["Importancia"]
)

plt.title("Importância das Variáveis - Random Forest")
plt.xlabel("Variável")
plt.ylabel("Importância")
plt.xticks(rotation=45)

plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "importancia_variaveis.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()


#%% RESULTADO REAL X PREVISTO

comparacao = pd.DataFrame({
    "Real": y_test.values,
    "Previsto_RF": y_pred_rf
})

print("\nPrimeiras previsões:")

print(
    comparacao.head(20)
)


#%% CONCLUSÃO AUTOMÁTICA DA POC

print("\n============================")
print("CONCLUSÃO DA POC")
print("============================")

melhor_modelo = resultados.loc[
    resultados["RMSE"].idxmin(),
    "Modelo"
]

print(
    "Modelo com menor RMSE:",
    melhor_modelo
)

if rmse_rf < rmse_baseline:

    print(
        "\nO Random Forest apresentou desempenho "
        "melhor que o baseline."
    )

    print(
        "Isso indica que as variáveis das campanhas "
        "contêm informação útil para prever "
        "conversões atribuídas."
    )

else:

    print(
        "\nO Random Forest não superou o baseline "
        "nesta amostra inicial."
    )

    print(
        "Será necessário avaliar mais dados, "
        "novas variáveis e outras estratégias "
        "de modelagem."
    )

#%% RESULTADO REAL X PREVISTO

comparacao = pd.DataFrame({
    "Real": y_test.values,
    "Previsto_RF": y_pred_rf
})

print("\nPrimeiras previsões:")

print(
    comparacao.head(20)
)

#%% SALVAR TABELAS DA POC

# Comparação dos modelos
resultados.to_csv(
    TABLES_DIR / "comparacao_modelos.csv",
    index=False
)

# Importância das variáveis
importancias.to_csv(
    TABLES_DIR / "importancia_variaveis.csv",
    index=False
)

# Valores reais x previstos
comparacao.to_csv(
    TABLES_DIR / "previsoes_teste.csv",
    index=False
)

# Estatísticas descritivas da amostra
df.describe().T.to_csv(
    TABLES_DIR / "resumo_estatistico.csv"
)

# Base agregada por campanha e hora
campanhas.to_csv(
    TABLES_DIR / "campanhas_agregadas_poc.csv",
    index=False
)

print("\nTabelas salvas com sucesso!")
print("Local:", TABLES_DIR)