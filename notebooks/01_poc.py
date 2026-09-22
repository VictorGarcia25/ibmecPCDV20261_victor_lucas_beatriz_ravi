#%% IMPORTS

import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
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

print("\nPasta das tabelas:")
print(TABLES_DIR)

print("\nPasta dos gráficos:")
print(FIGURES_DIR)


#%% VER ARQUIVOS DISPONÍVEIS

print("\nArquivos encontrados:")

for arquivo in DATA_DIR.iterdir():
    print(arquivo.name)


#%% LEITURA INICIAL DA BASE

arquivo_attribution = DATA_DIR / "criteo_attribution_5milhoes.csv"

df = pd.read_csv(arquivo_attribution, nrows=100000)

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
print(pd.crosstab(df["conversion"], df["attribution"]))


#%% CRIAR PERÍODO DE 1 HORA

df["hora"] = df["timestamp"] // 3600

print("\nExemplo de timestamp e hora:")
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

print("\nPrimeiras linhas da base agregada:")
print(campanhas.head())

print("\nFormato da base agregada:")
print(campanhas.shape)


#%% INDICADORES DAS CAMPANHAS

campanhas["ctr"] = campanhas["cliques"] / campanhas["impressoes"]
campanhas["taxa_conversao"] = campanhas["conversoes_atribuidas"] / campanhas["impressoes"]

print("\nBase com indicadores:")
print(campanhas.head())


#%% CONFERIR BASE AGREGADA

print("\nTamanho da base de campanhas:")
print(campanhas.shape)

print("\nResumo das conversões atribuídas:")
print(campanhas["conversoes_atribuidas"].describe())

proporcao_zero = (campanhas["conversoes_atribuidas"] == 0).mean()

print("\nProporção de janelas sem conversão:")
print(proporcao_zero)

print(f"\nPercentual de janelas sem conversão: {proporcao_zero * 100:.2f}%")


#%% CORRELAÇÃO ENTRE IMPRESSÕES E CLIQUES

correlacao_volume = campanhas[["impressoes", "cliques"]].corr()

print("\nCorrelação entre impressões e cliques:")
print(correlacao_volume)


#%% DEFINIR X E Y

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

horas = sorted(campanhas["hora"].unique())

ponto_corte = int(len(horas) * 0.80)

horas_treino = horas[:ponto_corte]
horas_teste = horas[ponto_corte:]

treino = campanhas[campanhas["hora"].isin(horas_treino)].copy()
teste = campanhas[campanhas["hora"].isin(horas_teste)].copy()

X_train = treino[features]
y_train = treino["conversoes_atribuidas"]

X_test = teste[features]
y_test = teste["conversoes_atribuidas"]

print("\nQuantidade total de horas:")
print(len(horas))

print("\nHoras utilizadas no treino:")
print(horas_treino)

print("\nHoras utilizadas no teste:")
print(horas_teste)

print("\nTamanho do treino:")
print(X_train.shape)

print("\nTamanho do teste:")
print(X_test.shape)


#%% FUNÇÃO PARA AVALIAR MODELOS

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


#%% BASELINE MÍNIMO - DUMMY REGRESSOR

baseline = DummyRegressor(strategy="mean")
baseline.fit(X_train, y_train)

y_pred_baseline = baseline.predict(X_test)

resultado_baseline = avaliar_modelo(
    "Baseline mínimo - Dummy",
    y_test,
    y_pred_baseline
)

print("\n====================================")
print("BASELINE MÍNIMO - DUMMY REGRESSOR")
print("====================================")
print("MAE:", resultado_baseline["MAE"])
print("RMSE:", resultado_baseline["RMSE"])
print("R²:", resultado_baseline["R2"])


#%% BASELINE SIMPLES - TAXA MÉDIA X IMPRESSÕES

taxa_media_conversao_treino = y_train.sum() / X_train["impressoes"].sum()

y_pred_baseline_simples = (
    X_test["impressoes"].to_numpy() * taxa_media_conversao_treino
)

resultado_baseline_simples = avaliar_modelo(
    "Baseline simples - Taxa média x Impressões",
    y_test,
    y_pred_baseline_simples
)

print("\n============================================")
print("BASELINE SIMPLES - TAXA MÉDIA X IMPRESSÕES")
print("============================================")
print("Taxa média de conversão no treino:", taxa_media_conversao_treino)
print("MAE:", resultado_baseline_simples["MAE"])
print("RMSE:", resultado_baseline_simples["RMSE"])
print("R²:", resultado_baseline_simples["R2"])


#%% MODELO 1 - REGRESSÃO LINEAR

modelo_lr = LinearRegression()
modelo_lr.fit(X_train, y_train)

y_pred_lr = modelo_lr.predict(X_test)

resultado_lr = avaliar_modelo(
    "Regressão Linear",
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
    "Random Forest",
    y_test,
    y_pred_rf
)

print("\n============================")
print("RANDOM FOREST")
print("============================")
print("MAE:", resultado_rf["MAE"])
print("RMSE:", resultado_rf["RMSE"])
print("R²:", resultado_rf["R2"])


#%% COMPARAÇÃO DOS MODELOS

resultados = pd.DataFrame([
    resultado_baseline,
    resultado_baseline_simples,
    resultado_lr,
    resultado_rf
])

resultados_ordenados = resultados.sort_values("RMSE")

print("\n============================")
print("COMPARAÇÃO DOS MODELOS")
print("============================")
print(resultados_ordenados.to_string(index=False))


#%% IMPORTÂNCIA DAS VARIÁVEIS - RANDOM FOREST

importancias = pd.DataFrame({
    "Variavel": features,
    "Importancia": modelo_rf.feature_importances_
})

importancias = importancias.sort_values("Importancia", ascending=False)

print("\n============================")
print("IMPORTÂNCIA DAS VARIÁVEIS")
print("============================")
print(importancias.to_string(index=False))


#%% GRÁFICO - COMPARAÇÃO DO RMSE

plt.figure(figsize=(10, 5))

plt.bar(
    resultados_ordenados["Modelo"],
    resultados_ordenados["RMSE"]
)

plt.title("Comparação do RMSE dos Modelos")
plt.xlabel("Modelo")
plt.ylabel("RMSE")
plt.xticks(rotation=20, ha="right")
plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "comparacao_rmse.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()


#%% GRÁFICO - IMPORTÂNCIA DAS VARIÁVEIS

plt.figure(figsize=(8, 5))

plt.bar(
    importancias["Variavel"],
    importancias["Importancia"]
)

plt.title("Importância das Variáveis - Random Forest")
plt.xlabel("Variável")
plt.ylabel("Importância")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "importancia_variaveis.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()


#%% RESULTADO REAL X PREVISTO

comparacao = pd.DataFrame({
    "Real": y_test.to_numpy(),
    "Baseline_Dummy": y_pred_baseline,
    "Baseline_Taxa_Media": y_pred_baseline_simples,
    "Regressao_Linear": y_pred_lr,
    "Random_Forest": y_pred_rf
})

print("\nPrimeiras previsões:")
print(comparacao.head(20))


#%% CONCLUSÃO AUTOMÁTICA DA POC

print("\n============================")
print("CONCLUSÃO DA POC")
print("============================")

modelos_aprendidos = resultados[
    resultados["Modelo"].isin(["Regressão Linear", "Random Forest"])
]

melhor_linha = modelos_aprendidos.loc[modelos_aprendidos["RMSE"].idxmin()]

melhor_modelo = melhor_linha["Modelo"]
melhor_mae = melhor_linha["MAE"]
melhor_rmse = melhor_linha["RMSE"]
melhor_r2 = melhor_linha["R2"]

rmse_baseline = resultado_baseline["RMSE"]
rmse_baseline_simples = resultado_baseline_simples["RMSE"]

print(f"\nMelhor modelo treinado: {melhor_modelo}")
print(f"MAE: {melhor_mae:.4f}")
print(f"RMSE: {melhor_rmse:.4f}")
print(f"R²: {melhor_r2:.4f}")


#%% COMPARAÇÃO COM BASELINE MÍNIMO

print("\n--- Comparação com baseline mínimo ---")
print(f"RMSE Dummy: {rmse_baseline:.4f}")

if melhor_rmse < rmse_baseline:
    reducao_dummy = ((rmse_baseline - melhor_rmse) / rmse_baseline) * 100
    print(f"\nO {melhor_modelo} superou o baseline mínimo.")
    print(f"Redução do RMSE em relação ao Dummy: {reducao_dummy:.2f}%")
else:
    print(f"\nO {melhor_modelo} não superou o baseline mínimo.")


#%% COMPARAÇÃO COM BASELINE SIMPLES

print("\n--- Comparação com baseline simples ---")
print(f"RMSE taxa média x impressões: {rmse_baseline_simples:.4f}")

if melhor_rmse < rmse_baseline_simples:
    reducao_simples = (
        (rmse_baseline_simples - melhor_rmse)
        / rmse_baseline_simples
    ) * 100

    print(f"\nO {melhor_modelo} também superou o baseline simples de negócio.")
    print(f"Redução do RMSE em relação ao baseline simples: {reducao_simples:.2f}%")
    print("\nIsso indica que o modelo capturou informação adicional além de simplesmente associar mais impressões a mais conversões.")

else:
    print(f"\nO {melhor_modelo} NÃO superou o baseline simples de negócio.")
    print("\nIsso sugere que parte importante do desempenho atual pode estar relacionada principalmente ao volume de impressões.")
    print("\nNas próximas etapas deverão ser criadas features temporais e defasadas para estudar tendência e eficiência.")


#%% SALVAR TABELAS DA POC

resultados.to_csv(
    TABLES_DIR / "comparacao_modelos.csv",
    index=False
)

importancias.to_csv(
    TABLES_DIR / "importancia_variaveis.csv",
    index=False
)

comparacao.to_csv(
    TABLES_DIR / "previsoes_teste.csv",
    index=False
)

df.describe().T.to_csv(
    TABLES_DIR / "resumo_estatistico.csv"
)

campanhas.to_csv(
    TABLES_DIR / "campanhas_agregadas_poc.csv",
    index=False
)

print("\nTabelas salvas com sucesso!")
print("Local:", TABLES_DIR)