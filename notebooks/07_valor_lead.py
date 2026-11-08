#%% OBJETIVO
#
# Modelo 07 - Aluguel esperado por bairro e "valor do lead" por praça
#
# Pergunta: quanto vale um lead de fiança em cada praça?
#
# A fiança é cobrada como percentual do aluguel. Um MQL em bairro de aluguel alto
# vale mais do que um MQL em bairro de aluguel baixo. Se a Loft otimiza mídia só por
# QUANTIDADE de MQL, ela trata os dois como iguais. Este modelo estima o aluguel
# esperado de cada bairro e transforma isso em um índice de valor do lead por cidade,
# que pode entrar no otimizador (modelo 06) como "receita por conversão".
#
# Abordagem supervisionada (dados reais da Loft):
#   unidade   = bairro x tipo (apartamento ou casa), na janela recente do 03
#   alvo      = log do aluguel mediano anunciado
#   variáveis = área, condomínio, tipo, volume de oferta, peso do aluguel na oferta
#               do bairro, preço de venda por m² do bairro, nível de preço da cidade e
#               da UF (codificação pela média do alvo, feita dentro da validação)
#
# Por que modelar se o aluguel já é observado?
#   1. Bairro com poucos anúncios tem mediana ruidosa: o aluguel de REFERÊNCIA mistura
#      o observado com o previsto, com peso proporcional ao número de anúncios.
#   2. O modelo generaliza para cidades e bairros sem dado suficiente.
#   3. O resíduo mostra bairros mais caros ou mais baratos do que o perfil indica.
#
# Validação:
#   - KFold (bairros novos em cidades conhecidas)
#   - GroupKFold por cidade (cidade que o modelo nunca viu): teste mais duro
#   - baselines: mediana nacional por tipo; mediana da cidade por tipo


#%% IMPORTS

import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, TargetEncoder


#%% PARÂMETROS

ARQUIVO_LOFT = "bq-results-20261005-170605-1791220258075.csv"
SEMENTE = 42
N_PARTES = 5

PRECO_MIN, PRECO_MAX = 300, 30_000
AREA_MIN, AREA_MAX = 15, 1_000
PRECO_M2_VENDA_MIN, PRECO_M2_VENDA_MAX = 500, 50_000
MIN_ANUNCIOS_BAIRRO = 10          # abaixo disso o bairro x tipo não entra no treino

# Peso do observado no aluguel de referência: n / (n + K_SUAVIZACAO)
# Com 20 anúncios, observado e previsto pesam igual.
K_SUAVIZACAO = 20

# Percentual do aluguel cobrado pela fiança. Deixe None até a Loft informar:
# o índice de valor do lead não depende dele; só o ticket em R$ depende.
TAXA_FIANCA = None


#%% CAMINHOS

load_dotenv()

caminho_dados = os.getenv("DATA_DIR")
if caminho_dados is None:
    raise ValueError("A variável DATA_DIR não foi encontrada. Confira o arquivo .env.")

ARQUIVO = Path(caminho_dados) / os.getenv("LOFT_FILE", ARQUIVO_LOFT)

PROJECT_DIR = Path(__file__).resolve().parents[1]
TABLES_DIR = PROJECT_DIR / "reports" / "tables"
FIGURES_DIR = PROJECT_DIR / "reports" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

ARQUIVO_QUALIDADE = TABLES_DIR / "qualidade_meses_aluguel.csv"
ARQUIVO_POTENCIAL = TABLES_DIR / "potencial_cidades.csv"

for arquivo in [ARQUIVO, ARQUIVO_QUALIDADE, ARQUIVO_POTENCIAL]:
    if not arquivo.exists():
        raise FileNotFoundError(
            f"{arquivo.name} não encontrado. Rode antes: python notebooks/03_potencial_mercado.py"
        )


#%% LEITURA

texto = [
    "normalized_state_seed", "normalized_city_seed", "normalized_neighbourhood_seed",
    "operation_type", "property_type_group", "distrito",
]

df = pd.read_csv(
    ARQUIVO,
    usecols=[
        "snapshot_month", *texto, "n_listings", "median_price_mm3",
        "median_price_m2_mm3", "median_condo_fee_mm3", "median_area_mm3",
    ],
    dtype={c: str for c in texto},
    parse_dates=["snapshot_month"],
).rename(columns={
    "snapshot_month": "mes",
    "normalized_state_seed": "uf",
    "normalized_city_seed": "cidade",
    "normalized_neighbourhood_seed": "bairro",
    "operation_type": "operacao",
    "property_type_group": "tipo",
    "n_listings": "anuncios",
    "median_price_mm3": "preco",
    "median_price_m2_mm3": "preco_m2",
    "median_condo_fee_mm3": "condominio",
    "median_area_mm3": "area",
})

qualidade = pd.read_csv(ARQUIVO_QUALIDADE, parse_dates=["mes"])
janela = qualidade.loc[qualidade["na_janela"], "mes"]

# Apartamento e casa separados ('apartment_house' é a soma dos dois)
df = df[df["mes"].isin(janela) & df["tipo"].isin(["apartment", "house"])].copy()

print("Janela:", [m.strftime("%Y-%m") for m in janela])
print("Linhas de apartamento/casa na janela:", len(df))


#%% FUNÇÃO DE AGREGAÇÃO PONDERADA

CHAVE = ["uf", "cidade", "bairro", "tipo"]


def media_ponderada_log(grupo, coluna):
    validos = grupo[coluna].notna() & (grupo[coluna] > 0) & (grupo["anuncios"] > 0)
    if not validos.any():
        return np.nan
    return np.average(np.log(grupo.loc[validos, coluna]), weights=grupo.loc[validos, "anuncios"])


#%% ALUGUEL POR BAIRRO x TIPO (alvo e variáveis do próprio aluguel)

aluguel = df[
    (df["operacao"] == "rent")
    & df["preco"].between(PRECO_MIN, PRECO_MAX)
    & df["area"].between(AREA_MIN, AREA_MAX)
]

bairros = (
    aluguel.groupby(CHAVE)
    .apply(
        lambda g: pd.Series({
            "anuncios_aluguel": g["anuncios"].sum(),
            "log_aluguel": media_ponderada_log(g, "preco"),
            "log_area": media_ponderada_log(g, "area"),
            "log_condominio": media_ponderada_log(g, "condominio"),
            "distrito": g["distrito"].dropna().iloc[0] if g["distrito"].notna().any() else np.nan,
        }),
        include_groups=False,
    )
    .reset_index()
)


#%% VARIÁVEIS DO MERCADO DE VENDA NO MESMO BAIRRO

venda = df[(df["operacao"] == "sale") & df["preco_m2"].between(PRECO_M2_VENDA_MIN, PRECO_M2_VENDA_MAX)]

venda_bairro = (
    venda.groupby(CHAVE)
    .apply(
        lambda g: pd.Series({
            "anuncios_venda": g["anuncios"].sum(),
            "log_preco_m2_venda": media_ponderada_log(g, "preco_m2"),
        }),
        include_groups=False,
    )
    .reset_index()
)

# Bairro sem nenhum anúncio de aluguel na janela não tem preço observado
bairros = bairros[(bairros["anuncios_aluguel"] > 0) & bairros["log_aluguel"].notna()]

bairros = bairros.merge(venda_bairro, on=CHAVE, how="left")
bairros["anuncios_venda"] = bairros["anuncios_venda"].fillna(0)

bairros["log_anuncios_aluguel"] = np.log1p(bairros["anuncios_aluguel"])
bairros["pct_aluguel_na_oferta"] = bairros["anuncios_aluguel"] / (
    bairros["anuncios_aluguel"] + bairros["anuncios_venda"]
)
bairros["tem_condominio"] = bairros["log_condominio"].notna().astype(float)
bairros["tem_preco_venda"] = bairros["log_preco_m2_venda"].notna().astype(float)
bairros["cidade_uf"] = bairros["cidade"] + " - " + bairros["uf"]

print("\nBairros x tipo com aluguel válido:", len(bairros))


#%% BASE DE TREINO

treino = bairros[bairros["anuncios_aluguel"] >= MIN_ANUNCIOS_BAIRRO].reset_index(drop=True)

print(f"Com pelo menos {MIN_ANUNCIOS_BAIRRO} anúncios (treino): {len(treino)}")
print("Cidades no treino:", treino["cidade_uf"].nunique())

NUMERICAS = [
    "log_area", "log_condominio", "tem_condominio", "log_anuncios_aluguel",
    "pct_aluguel_na_oferta", "log_preco_m2_venda", "tem_preco_venda",
]
CATEGORICAS_ALVO = ["cidade_uf", "uf"]       # codificadas pela média do alvo
CATEGORICAS_ONEHOT = ["tipo"]
VARIAVEIS = NUMERICAS + CATEGORICAS_ALVO + CATEGORICAS_ONEHOT

X = treino[VARIAVEIS]
y = treino["log_aluguel"].to_numpy()
grupos = treino["cidade_uf"].to_numpy()


#%% MODELOS

def codificador_alvo():
    """TargetEncoder reprodutível nas versões antigas e novas do scikit-learn."""
    try:
        return TargetEncoder(cv=KFold(5, shuffle=True, random_state=SEMENTE))   # sklearn >= 1.9
    except TypeError:
        return TargetEncoder(random_state=SEMENTE)                              # sklearn 1.3 a 1.8


def preprocessador(escalar):
    numericas = make_pipeline(
        # mediana para faltantes; o indicador tem_* já carrega a informação da ausência
        SimpleImputer(strategy="median"),
        *([StandardScaler()] if escalar else []),
    )
    return ColumnTransformer([
        ("num", numericas, NUMERICAS),
        # TargetEncoder faz validação cruzada interna: não vaza o alvo do próprio bairro
        ("alvo", codificador_alvo(), CATEGORICAS_ALVO),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAS_ONEHOT),
    ])


def modelos():
    return {
        "Regressão Ridge": make_pipeline(preprocessador(True), RidgeCV(alphas=np.logspace(-3, 3, 25))),
        "Random Forest": make_pipeline(
            preprocessador(False),
            RandomForestRegressor(n_estimators=300, min_samples_leaf=5, max_features=0.5,
                                  random_state=SEMENTE, n_jobs=-1),
        ),
        "Gradient Boosting": make_pipeline(
            preprocessador(False),
            HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, min_samples_leaf=20,
                                          l2_regularization=1.0, random_state=SEMENTE),
        ),
    }


def baselines(idx_tr, idx_te):
    tr, te = treino.iloc[idx_tr], treino.iloc[idx_te]
    nacional = tr.groupby("tipo")["log_aluguel"].median()
    cidade = tr.groupby(["cidade_uf", "tipo"])["log_aluguel"].median()
    pred_nacional = te["tipo"].map(nacional).to_numpy()
    chaves = list(zip(te["cidade_uf"], te["tipo"]))
    pred_cidade = np.array([cidade.get(k, np.nan) for k in chaves])
    pred_cidade = np.where(np.isnan(pred_cidade), pred_nacional, pred_cidade)
    return {
        "Baseline mediana nacional do tipo": pred_nacional,
        "Baseline mediana da cidade e tipo": pred_cidade,
    }


def validar(divisor, rotulo, usar_grupos=False):
    previsoes = {}
    for idx_tr, idx_te in divisor.split(X, y, grupos if usar_grupos else None):
        for nome, pred in baselines(idx_tr, idx_te).items():
            # em cidade nunca vista não existe mediana da cidade: esse baseline não se aplica
            if usar_grupos and "cidade" in nome:
                continue
            previsoes.setdefault(nome, np.zeros(len(y)))[idx_te] = pred
        for nome, modelo in modelos().items():
            modelo.fit(X.iloc[idx_tr], y[idx_tr])
            previsoes.setdefault(nome, np.zeros(len(y)))[idx_te] = modelo.predict(X.iloc[idx_te])

    linhas = []
    for nome, pred in previsoes.items():
        erro_reais = np.abs(np.exp(pred) - np.exp(y)) / np.exp(y)
        linhas.append({
            "validacao": rotulo,
            "modelo": nome,
            "RMSE_log": np.sqrt(mean_squared_error(y, pred)),
            "MAE_log": mean_absolute_error(y, pred),
            "R2_log": r2_score(y, pred),
            "erro_mediano_pct_em_reais": np.median(erro_reais) * 100,
        })
    return pd.DataFrame(linhas), previsoes


#%% VALIDAÇÃO

comparacao_kfold, oof_kfold = validar(
    KFold(N_PARTES, shuffle=True, random_state=SEMENTE), f"KFold {N_PARTES} partes"
)
comparacao_cidade, oof_cidade = validar(
    GroupKFold(N_PARTES), "Agrupada por cidade (cidade nunca vista)", usar_grupos=True
)

comparacao = pd.concat([comparacao_kfold, comparacao_cidade], ignore_index=True)

print("\n============================")
print("COMPARAÇÃO DOS MODELOS (fora da amostra)")
print("============================")
print(comparacao.sort_values(["validacao", "RMSE_log"]).round(4).to_string(index=False))

aprendidos = comparacao_kfold[~comparacao_kfold["modelo"].str.startswith("Baseline")]
MELHOR = aprendidos.loc[aprendidos["RMSE_log"].idxmin(), "modelo"]
print(f"\nMelhor modelo: {MELHOR}")


#%% IMPORTÂNCIA DAS VARIÁVEIS (permutação, sobre o melhor modelo)

modelo_final = modelos()[MELHOR]
modelo_final.fit(X, y)

amostra = treino.sample(min(3000, len(treino)), random_state=SEMENTE).index
perm = permutation_importance(
    modelo_final, X.loc[amostra], y[amostra], n_repeats=10,
    random_state=SEMENTE, scoring="neg_root_mean_squared_error",
)
importancia = pd.DataFrame({
    "variavel": VARIAVEIS,
    "aumento_RMSE_ao_embaralhar": perm.importances_mean,
    "desvio": perm.importances_std,
}).sort_values("aumento_RMSE_ao_embaralhar", ascending=False)

print("\nImportância das variáveis:")
print(importancia.round(4).to_string(index=False))


#%% ALUGUEL DE REFERÊNCIA PARA TODOS OS BAIRROS

# Treino: previsão fora da amostra (o modelo não viu o próprio bairro)
treino["log_aluguel_previsto"] = oof_kfold[MELHOR]

# Bairros com poucos anúncios: previsão do modelo treinado com todo o treino
poucos = bairros[bairros["anuncios_aluguel"] < MIN_ANUNCIOS_BAIRRO].copy()
poucos["log_aluguel_previsto"] = modelo_final.predict(poucos[VARIAVEIS])

referencia = pd.concat([treino, poucos], ignore_index=True)

peso_observado = referencia["anuncios_aluguel"] / (referencia["anuncios_aluguel"] + K_SUAVIZACAO)
referencia["aluguel_observado"] = np.exp(referencia["log_aluguel"])
referencia["aluguel_previsto"] = np.exp(referencia["log_aluguel_previsto"])
referencia["aluguel_referencia"] = np.exp(
    peso_observado * referencia["log_aluguel"] + (1 - peso_observado) * referencia["log_aluguel_previsto"]
)
referencia["peso_do_observado"] = peso_observado
referencia["diferenca_vs_perfil_pct"] = (
    referencia["aluguel_observado"] / referencia["aluguel_previsto"] - 1
) * 100

colunas_bairro = [
    "uf", "cidade", "distrito", "bairro", "tipo", "anuncios_aluguel",
    "aluguel_observado", "aluguel_previsto", "aluguel_referencia",
    "peso_do_observado", "diferenca_vs_perfil_pct",
]
referencia = referencia[colunas_bairro].sort_values(["uf", "cidade", "bairro", "tipo"])


#%% VALOR DO LEAD POR CIDADE

# Aluguel de referência da cidade = média ponderada pelos anúncios dos bairros.
# É o valor esperado do aluguel de um contrato que nasce de um lead naquela cidade.
valor_cidade = (
    referencia.groupby(["uf", "cidade"])
    .apply(
        lambda g: pd.Series({
            "anuncios_aluguel": g["anuncios_aluguel"].sum(),
            "bairros": g["bairro"].nunique(),
            "aluguel_referencia_medio": np.average(g["aluguel_referencia"], weights=g["anuncios_aluguel"]),
        }),
        include_groups=False,
    )
    .reset_index()
)

media_nacional = np.average(valor_cidade["aluguel_referencia_medio"], weights=valor_cidade["anuncios_aluguel"])
valor_cidade["indice_valor_lead"] = valor_cidade["aluguel_referencia_medio"] / media_nacional

if TAXA_FIANCA is not None:
    valor_cidade["ticket_fianca_mensal_estimado"] = valor_cidade["aluguel_referencia_medio"] * TAXA_FIANCA

# Cruzar com o potencial do 03: ranking por QUANTIDADE x ranking por VALOR
potencial = pd.read_csv(ARQUIVO_POTENCIAL)[["uf", "cidade", "anuncios_mes", "share_anuncios", "faixa_prioridade"]]
valor_cidade = valor_cidade.merge(potencial, on=["uf", "cidade"], how="left")

valor_cidade["potencial_em_valor"] = valor_cidade["share_anuncios"] * valor_cidade["indice_valor_lead"]
valor_cidade["share_valor"] = valor_cidade["potencial_em_valor"] / valor_cidade["potencial_em_valor"].sum()
valor_cidade["ranking_quantidade"] = valor_cidade["share_anuncios"].rank(ascending=False, method="min")
valor_cidade["ranking_valor"] = valor_cidade["share_valor"].rank(ascending=False, method="min")
valor_cidade["mudanca_ranking"] = valor_cidade["ranking_quantidade"] - valor_cidade["ranking_valor"]

valor_cidade = valor_cidade.sort_values("share_valor", ascending=False)

relevantes = valor_cidade[valor_cidade["anuncios_aluguel"] >= 200]

print("\nÍndice de valor do lead (1,00 = média nacional) - cidades com 200+ anúncios:")
print("Mais valiosas:")
print(relevantes.sort_values("indice_valor_lead", ascending=False).head(10)[
    ["uf", "cidade", "aluguel_referencia_medio", "indice_valor_lead"]
].round(2).to_string(index=False))
print("Menos valiosas:")
print(relevantes.sort_values("indice_valor_lead").head(10)[
    ["uf", "cidade", "aluguel_referencia_medio", "indice_valor_lead"]
].round(2).to_string(index=False))

top30 = valor_cidade[valor_cidade["ranking_valor"] <= 30]
print("\nCidades que mais SOBEM quando o potencial é medido em valor (top 30 por valor):")
print(top30.sort_values("mudanca_ranking", ascending=False).head(8)[
    ["uf", "cidade", "ranking_quantidade", "ranking_valor", "indice_valor_lead"]
].round(2).to_string(index=False))


#%% SALVAR
'''
comparacao.to_csv(TABLES_DIR / "07_comparacao_modelos.csv", index=False)
importancia.to_csv(TABLES_DIR / "07_importancia_variaveis.csv", index=False)
referencia.to_csv(TABLES_DIR / "07_aluguel_referencia_bairros.csv", index=False)
valor_cidade.to_csv(TABLES_DIR / "07_valor_lead_cidades.csv", index=False)
'''

#%% GRÁFICO - REAL x PREVISTO (fora da amostra)

fig, ax = plt.subplots(figsize=(7, 7))
real = np.exp(y)
prev = np.exp(oof_kfold[MELHOR])
ax.scatter(prev, real, s=4, alpha=0.25, color="#1f6f5c")
limites = [PRECO_MIN, PRECO_MAX]
ax.plot(limites, limites, color="#e07a5f", linestyle="--")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Aluguel previsto (R$) - fora da amostra")
ax.set_ylabel("Aluguel mediano anunciado (R$)")
r2 = comparacao_kfold.loc[comparacao_kfold["modelo"] == MELHOR, "R2_log"].iloc[0]
ax.set_title(f"{MELHOR}: aluguel por bairro x tipo (R² log = {r2:.2f})")
plt.tight_layout()
plt.savefig(FIGURES_DIR / "07_real_vs_previsto.png", dpi=200, bbox_inches="tight")
plt.show()
plt.close()


#%% GRÁFICO - POTENCIAL EM QUANTIDADE x EM VALOR

top = valor_cidade.head(20).iloc[::-1]
posicoes = np.arange(len(top))

fig, ax = plt.subplots(figsize=(10, 7))
ax.barh(posicoes - 0.2, top["share_anuncios"] * 100, height=0.4, color="#b8b8b8", label="Por quantidade de anúncios")
ax.barh(posicoes + 0.2, top["share_valor"] * 100, height=0.4, color="#1f6f5c", label="Por valor (quantidade x índice de valor)")
ax.set_yticks(posicoes)
ax.set_yticklabels(top["cidade"] + " (" + top["uf"] + ")")
ax.set_xscale("log")
ax.set_xlabel("% do mercado nacional (escala log)")
ax.set_title("Top 20 cidades: potencial medido em quantidade x em valor do lead")
ax.legend(loc="lower right")
plt.tight_layout()
plt.savefig(FIGURES_DIR / "07_potencial_quantidade_vs_valor.png", dpi=200, bbox_inches="tight")
plt.show()
plt.close()


#%% CONCLUSÃO

melhor = comparacao_kfold[comparacao_kfold["modelo"] == MELHOR].iloc[0]
base_cidade = comparacao_kfold[comparacao_kfold["modelo"] == "Baseline mediana da cidade e tipo"].iloc[0]
melhor_cidade_nova = comparacao_cidade[comparacao_cidade["modelo"] == MELHOR].iloc[0]
base_nacional_nova = comparacao_cidade[comparacao_cidade["modelo"] == "Baseline mediana nacional do tipo"].iloc[0]

print("\n============================")
print("CONCLUSÃO - MODELO 07")
print("============================")
print(
    f"{MELHOR}: R² (log) fora da amostra de {melhor['R2_log']:.3f}, erro mediano de "
    f"{melhor['erro_mediano_pct_em_reais']:.1f}% no aluguel, contra "
    f"{base_cidade['erro_mediano_pct_em_reais']:.1f}% da mediana da cidade."
)
print(
    f"Em cidades que o modelo nunca viu: erro mediano de "
    f"{melhor_cidade_nova['erro_mediano_pct_em_reais']:.1f}%, contra "
    f"{base_nacional_nova['erro_mediano_pct_em_reais']:.1f}% da mediana nacional."
)
p90, p10 = np.percentile(relevantes["indice_valor_lead"], [90, 10])
print(
    f"Entre cidades com 200+ anúncios, o valor do lead varia {p90 / p10:.1f}x entre o "
    "percentil 90 e o 10: otimizar mídia só por quantidade de MQL ignora essa diferença."
)
print(
    "\nUso no modelo 06: o índice de valor do lead entra como 'receita por conversão' de "
    "cada praça, e o otimizador passa a maximizar valor em vez de quantidade."
)
