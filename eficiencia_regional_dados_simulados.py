"""
POC 4 - Eficiência regional da mídia: onde o investimento rende menos?

Pergunta: em quais cidades o investimento em mídia é pouco eficiente e para
onde vale realocar a verba do mês para gerar mais MQLs e cadastros?

Entradas
  - Painel de anúncios da Loft (mesmo CSV do 03 e do 07): potencial de mercado
    e aluguel mediano por cidade.
  - Mídia da Loft por cidade e mês (ARQUIVO REAL, ainda não recebido):
      colunas: mes (AAAA-MM-01), uf, cidade, investimento, mqls, cadastros
      (cidade e uf no mesmo padrão do painel, ex.: SAO PAULO / SP).
    Enquanto o arquivo não chega, o script SIMULA a mídia. Nesse modo todas as
    saídas levam o sufixo _SIMULADO e NÃO são resultado de negócio: servem para
    validar o pipeline, e o modelo só recupera o que o simulador embutiu.

Modelos (os mesmos já usados no projeto)
  - Baseline mínimo: DummyRegressor.
  - Baselines de negócio: custo médio por MQL (ou cadastro) x investimento e,
    mais exigente, o custo por resultado de CADA cidade x investimento. Um
    modelo só vale se superar este último, que apenas decora o nível da cidade.
  - Regressão Linear em log-log: o coeficiente do log do investimento é a
    elasticidade, ou seja, o quanto o resultado reage a +1% de verba. Com a
    interação log(investimento) x log(potencial), a elasticidade muda conforme
    o tamanho do mercado da cidade (saturação).
  - Random Forest: comparação de desempenho e checagem de consistência.

Validação: temporal (primeiros meses treinam, últimos testam), como na POC 1.

Sem vazamento temporal: potencial e aluguel por cidade são calculados "ponto no
tempo". Para cada mês da mídia usam-se apenas os 6 meses válidos do painel
ANTERIORES a ele (nunca o próprio mês nem o futuro), e o script confere isso
com um assert. A regra de mês válido também usa só meses até ele, e o script traz
travas de sanidade (alvo embaralhado, variáveis sem o alvo). Só a recomendação final de verba usa a janela mais recente do
painel, que é o que se conhece na hora de decidir. O modelo usa a participação
da cidade no volume nacional (e não o volume absoluto), porque a cobertura do
painel oscila de mês para mês, como já tratado na POC 3.

Como ler o ganho da realocação (verba total fixa)
  - O ganho vem como uma FAIXA:
      * conservador: modelo com elasticidade comum a todas as cidades (sem a
        interação), que não inventa diferenças entre cidades;
      * otimista: modelo com a interação verba x potencial. Verba e tamanho da
        cidade andam juntos, então esse modelo tende a exagerar as diferenças entre
        cidades e, com isso, o ganho.
    Na simulação o ganho verdadeiro ficou dentro da faixa nas sementes testadas;
    com dados reais isso precisa ser verificado.
  - Ganho da regra simples: mover verba de quem tem maior custo por resultado
    observado para quem tem menor, sem modelo. O modelo só se justifica se vencê-la.
  - O custo "antes" é o OBSERVADO; os ganhos são aplicados sobre ele.
  - O ganho depende dos limites de variação da verba por cidade, por isso há uma
    tabela de sensibilidade.
  - A ação (Reduzir/Aumentar) compara o retorno marginal de cada cidade com o "preço
    sombra" do plano otimizado (o retorno marginal que sobra quando a verba está bem
    distribuída), e não com um corte fixo por quartil.

Saídas (reports/tables e reports/figures): comparação de modelos, diagnóstico
por cidade (custo médio, retorno marginal, ação sugerida), realocação sugerida,
impacto estimado e sensibilidade aos limites.

Uso: LOFT_CSV=caminho/do/painel.csv [MIDIA_CSV=caminho/da/midia.csv] \
     python notebooks/04_eficiencia_regional.py
"""

#%% IMPORTS

import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scipy.stats import spearmanr
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


#%% PARÂMETROS

SEMENTE = 42

# Regras de limpeza do painel (mesmas do 03)
# A fonte nova começa em nov/2024, mas as colunas *_mm3 são médias de 3 meses (janela para
# trás): nov/2024 a jan/2025 ainda misturam o preço da fonte antiga e só fev/2025 está limpo.
INICIO_SERIE_CONFIAVEL = "2025-02-01"
LIMIAR_MES_ANOMALO = 0.60
JANELA_MESES_POTENCIAL = 6
PRECO_MIN, PRECO_MAX = 300, 30_000
MIN_ANUNCIOS_PRECO = 5

# Mídia
N_MESES = 12
N_MESES_TESTE = 3                 # últimos meses ficam para o teste
N_CIDADES_SIMULADAS = 60
MIN_RESULTADO = 10                # linhas com menos MQLs/cadastros que isso ficam fora do ajuste
ORCAMENTO_MENSAL_SIMULADO = 1_500_000
CPL_ALVO_SIMULADO = 80

# Realocação
PASSO_REALOCACAO = 1 / 2000       # fração do orçamento movida a cada passo
LIMITE_PRINCIPAL = (0.7, 1.5)     # cada cidade fica entre 70% e 150% da verba atual
LIMITES_SENSIBILIDADE = [(0.5, 2.0), (0.7, 1.5), (0.8, 1.25), (0.9, 1.1)]
TOLERANCIA_ACAO = 0.25            # ação: retorno marginal 25% abaixo/acima do preço sombra
MARGEM_VS_REGRA = 0.05            # o modelo precisa vencer a regra simples por mais de 5% do ganho dela
ACRESCIMO_MARGINAL = 0.10         # +10% de verba para medir o retorno marginal

ALVOS = ["mqls", "cadastros"]


#%% CAMINHOS

ARQUIVO_LOFT = os.getenv("LOFT_CSV")
ARQUIVO_MIDIA = os.getenv("MIDIA_CSV")

if not ARQUIVO_LOFT or not Path(ARQUIVO_LOFT).exists():
    raise FileNotFoundError("Defina LOFT_CSV com o caminho do painel de anúncios da Loft.")

PROJECT_DIR = Path(__file__).resolve().parents[1]
TABLES_DIR = PROJECT_DIR / "reports" / "tables"
FIGURES_DIR = PROJECT_DIR / "reports" / "figures"
TABLES_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

SIMULADO = not (ARQUIVO_MIDIA and Path(ARQUIVO_MIDIA).exists())
SUFIXO = "_SIMULADO" if SIMULADO else ""

if SIMULADO:
    print("\n" + "=" * 70)
    print("ATENÇÃO: mídia SIMULADA (arquivo real da Loft ainda não fornecido).")
    print("Os números abaixo validam o pipeline; não são resultado de negócio.")
    print("=" * 70)


#%% POTENCIAL POR CIDADE (painel da Loft)

colunas = [
    "snapshot_month", "normalized_state_seed", "normalized_city_seed",
    "operation_type", "property_type_group", "n_listings", "median_price_mm3",
]
painel = pd.read_csv(ARQUIVO_LOFT, usecols=colunas, low_memory=False)

aluguel = painel[
    (painel["operation_type"] == "rent")
    & (painel["property_type_group"] == "apartment_house")
    & (painel["snapshot_month"] >= INICIO_SERIE_CONFIAVEL)
].copy()

total_mes = aluguel.groupby("snapshot_month")["n_listings"].sum().sort_index()
# Mês válido = cobertura de pelo menos 60% da mediana dos meses ATÉ ELE (nunca usa meses futuros)
meses_validos = [
    m for i, (m, v) in enumerate(total_mes.items())
    if v >= LIMIAR_MES_ANOMALO * np.median(total_mes.iloc[: i + 1])
]

base = aluguel[
    aluguel["snapshot_month"].isin(meses_validos)
    & aluguel["median_price_mm3"].between(PRECO_MIN, PRECO_MAX)
    & (aluguel["n_listings"] >= MIN_ANUNCIOS_PRECO)
].copy()
base["cidade"] = base["normalized_city_seed"].str.upper().str.strip()
base["uf"] = base["normalized_state_seed"].str.upper().str.strip()
base["preco_x_n"] = base["median_price_mm3"] * base["n_listings"]

# totais por mês x cidade: a partir daqui qualquer janela é só somar meses
mensal = base.groupby(["snapshot_month", "uf", "cidade"], as_index=False).agg(
    anuncios=("n_listings", "sum"), preco_x_n=("preco_x_n", "sum")
)


def potencial_ate(janela):
    """Potencial (anúncios/mês) e aluguel médio por cidade usando SÓ os meses da janela."""
    m = mensal[mensal["snapshot_month"].isin(janela)]
    c = m.groupby(["uf", "cidade"], as_index=False)[["anuncios", "preco_x_n"]].sum()
    c["potencial"] = c["anuncios"] / len(janela)             # anúncios/mês
    c["participacao"] = c["anuncios"] / c["anuncios"].sum()  # fatia do volume nacional
    c["aluguel_medio"] = c["preco_x_n"] / c["anuncios"]
    return c[["uf", "cidade", "potencial", "participacao", "aluguel_medio"]]


def potencial_ponto_no_tempo(meses_midia):
    """Para cada mês da mídia, potencial calculado só com meses válidos ANTERIORES a ele."""
    partes = []
    for mes in meses_midia:
        anteriores = [m for m in meses_validos if m < mes][-JANELA_MESES_POTENCIAL:]
        if not anteriores:
            continue
        p = potencial_ate(anteriores)
        p["mes"] = mes
        p["janela_fim"] = anteriores[-1]
        partes.append(p)
    return pd.concat(partes, ignore_index=True)


# Janela mais recente: usada para escolher cidades e para a recomendação final
meses_janela = meses_validos[-JANELA_MESES_POTENCIAL:]
cidades = potencial_ate(meses_janela).sort_values("potencial", ascending=False).reset_index(drop=True)

print(f"\nCidades com potencial calculado: {len(cidades)}")
print(f"Janela mais recente (recomendação final): {meses_janela[0][:7]} a {meses_janela[-1][:7]}")


#%% MÍDIA (real ou simulada)

if SIMULADO:
    rng = np.random.default_rng(SEMENTE)
    top = cidades.head(N_CIDADES_SIMULADAS).copy()
    n = len(top)
    meses = list(meses_validos[-N_MESES:])
    pot = top["potencial"].to_numpy()
    log_rel = np.log(pot / pot.mean())

    # Parâmetros "escondidos" que o modelo precisa descobrir
    eficiencia = rng.lognormal(0, 0.35, n)                  # eficiência regional
    expoente = np.clip(0.55 + 0.08 * log_rel, 0.3, 0.9)     # retorno decrescente
    desalinho = rng.lognormal(0, 0.6, n)                    # verba mal distribuída
    taxa_cadastro = rng.beta(6, 12, n)

    peso = (pot / pot.sum()) ** 0.5 * desalinho
    peso = peso / peso.sum()

    linhas = []
    for i, mes in enumerate(meses):
        sazonal = 1 + 0.15 * np.sin(2 * np.pi * i / 12)
        inv = ORCAMENTO_MENSAL_SIMULADO * sazonal * peso * rng.lognormal(0, 0.15, n)
        bruto = eficiencia * pot ** 0.45 * inv ** expoente
        linhas.append(pd.DataFrame({
            "mes": mes, "uf": top["uf"], "cidade": top["cidade"],
            "investimento": inv, "bruto": bruto,
        }))
    midia = pd.concat(linhas, ignore_index=True)
    escala = (midia["investimento"].sum() / CPL_ALVO_SIMULADO) / midia["bruto"].sum()
    midia["mqls"] = rng.poisson(midia["bruto"] * escala * rng.lognormal(0, 0.2, len(midia)))
    taxa = np.tile(taxa_cadastro, len(meses))
    midia["cadastros"] = rng.binomial(midia["mqls"], taxa)
    midia = midia.drop(columns="bruto")
    VERDADE = pd.DataFrame({"uf": top["uf"].to_numpy(), "cidade": top["cidade"].to_numpy(),
                            "k": eficiencia * escala, "expoente": expoente, "pot": pot,
                            "taxa": taxa_cadastro})
else:
    midia = pd.read_csv(ARQUIVO_MIDIA)
    midia["cidade"] = midia["cidade"].str.upper().str.strip()
    midia["uf"] = midia["uf"].str.upper().str.strip()
    midia = (
        midia.groupby(["mes", "uf", "cidade"], as_index=False)[["investimento", "mqls", "cadastros"]].sum()
    )

# Potencial e aluguel ponto no tempo: cada linha só enxerga meses anteriores ao seu
pit = potencial_ponto_no_tempo(sorted(midia["mes"].unique()))
dados = midia.merge(pit, on=["mes", "uf", "cidade"], how="inner")
dados = dados[dados["investimento"] > 0].copy()
assert (dados["janela_fim"] < dados["mes"]).all(), \
    "Vazamento temporal: o potencial usa mês igual ou posterior ao da linha."
print("Checagem anti-vazamento: janela do potencial sempre termina antes do mês da linha (ok).")
ordem_meses = {m: i for i, m in enumerate(sorted(dados["mes"].unique()))}
dados["mes_idx"] = dados["mes"].map(ordem_meses)

print(f"\nLinhas cidade x mês: {len(dados)} | cidades: {dados[['uf','cidade']].drop_duplicates().shape[0]}")
print(f"Meses: {dados['mes'].min()} a {dados['mes'].max()}")


#%% FEATURES

dados["log_invest"] = np.log(dados["investimento"])
# O modelo usa a PARTICIPAÇÃO no volume nacional, não o volume absoluto: a cobertura
# do painel oscila mês a mês (regra já adotada na POC 3) e deslocaria a variável.
dados["log_potencial"] = np.log(dados["participacao"])
dados["log_aluguel"] = np.log(dados["aluguel_medio"])
dados["inter"] = dados["log_invest"] * dados["log_potencial"]

FEATURES = ["log_invest", "log_potencial", "log_aluguel", "inter"]
assert not {"mqls", "cadastros"} & set(FEATURES), "Vazamento: o alvo (ou o outro resultado) está nas variáveis."
corte = dados["mes_idx"].max() - N_MESES_TESTE + 1


#%% FUNÇÕES

def avaliar(nome, real, previsto):
    return {
        "Modelo": nome,
        "MAE": mean_absolute_error(real, previsto),
        "RMSE": float(np.sqrt(mean_squared_error(real, previsto))),
        "R2": r2_score(real, previsto),
    }


def prever(modelo, invest, log_pot, log_alu, feats=None):
    """Resultado esperado (escala original) para um investimento dado (Regressão Linear log-log)."""
    li = np.log(invest)
    c = dict(zip(feats or FEATURES, modelo.coef_))
    return np.exp(
        modelo.intercept_ + c["log_invest"] * li + c["log_potencial"] * log_pot
        + c["log_aluguel"] * log_alu + c.get("inter", 0.0) * li * log_pot
    )


def otimizar(f, S0, lo, hi):
    """Realocação gulosa com orçamento fixo: tira de quem perde menos e dá a quem ganha mais."""
    passo = S0.sum() * PASSO_REALOCACAO
    S = S0.copy()
    for _ in range(20_000):
        ganho = np.where(S + passo <= hi, f(S + passo) - f(S), -np.inf)
        perda = np.where(S - passo >= lo, f(S) - f(np.maximum(S - passo, 1.0)), np.inf)
        i, j = np.argmax(ganho), np.argmin(perda)
        if i == j or ganho[i] <= perda[j]:
            break
        S[i] += passo
        S[j] -= passo
    return S


def plano_por_custo(cpl, S0, lo, hi, intensidade=0.5):
    """Regra simples, SEM modelo: sobe a verba de quem tem menor custo por resultado
    observado e reduz a de quem tem maior, mantendo o orçamento e os limites."""
    z = np.log(cpl)
    z = (z - z.mean()) / (z.std() if z.std() > 0 else 1.0)
    base = np.exp(-intensidade * z)
    orc = S0.sum()
    t_lo, t_hi = -10.0, 10.0
    for _ in range(80):
        t = (t_lo + t_hi) / 2
        if np.clip(S0 * base * np.exp(t), lo, hi).sum() < orc:
            t_lo = t
        else:
            t_hi = t
    return np.clip(S0 * base * np.exp(t_lo), lo, hi)


def ganho_relativo(f, S, S0):
    return float(f(S).sum() / f(S0).sum() - 1)


def rodar(alvo):
    print("\n" + "#" * 70)
    print(f"ALVO: {alvo}")
    print("#" * 70)

    # Contagens muito baixas distorcem o log (zeros e 1-2 MQLs): o ajuste usa só
    # linhas com resultado mínimo. Cidades abaixo disso seguem no diagnóstico.
    ajuste = dados[dados[alvo] >= MIN_RESULTADO]
    print(f"Linhas usadas no ajuste: {len(ajuste)} de {len(dados)} "
          f"(resultado >= {MIN_RESULTADO})")
    treino = ajuste[ajuste["mes_idx"] < corte]
    teste = ajuste[ajuste["mes_idx"] >= corte]
    y_tr, y_te = np.log(treino[alvo]), teste[alvo]

    # --- baselines
    dummy = DummyRegressor(strategy="mean").fit(treino[FEATURES], treino[alvo])
    cpl_medio = treino["investimento"].sum() / max(treino[alvo].sum(), 1)
    prev_dummy = dummy.predict(teste[FEATURES])
    prev_simples = teste["investimento"] / cpl_medio
    # Baseline forte: o custo por resultado de CADA cidade no treino. Quem só decora o
    # nível da cidade já chega perto; um modelo só vale se superar isto.
    chave = lambda d_: d_["uf"] + "|" + d_["cidade"]
    cpl_cidade = (treino.groupby(chave(treino))["investimento"].sum()
                  / treino.groupby(chave(treino))[alvo].sum())
    prev_forte = teste["investimento"] / chave(teste).map(cpl_cidade).fillna(cpl_medio)

    # --- modelos
    lr = LinearRegression().fit(treino[FEATURES], y_tr)
    rf = RandomForestRegressor(n_estimators=100, random_state=SEMENTE, n_jobs=-1)
    rf.fit(treino[FEATURES], y_tr)
    prev_lr = np.exp(lr.predict(teste[FEATURES]))
    prev_rf = np.exp(rf.predict(teste[FEATURES]))

    comp = pd.DataFrame([
        avaliar("Baseline mínimo - Dummy", y_te, prev_dummy),
        avaliar("Baseline simples - Custo médio x Investimento", y_te, prev_simples),
        avaliar("Baseline forte - Custo da cidade x Investimento", y_te, prev_forte),
        avaliar("Regressão Linear (log-log)", y_te, prev_lr),
        avaliar("Random Forest", y_te, prev_rf),
    ])
    print("\nDesempenho no teste (escala original):")
    print(comp.round(3).to_string(index=False))
    comp.to_csv(TABLES_DIR / f"eficiencia_comparacao_modelos_{alvo}{SUFIXO}.csv", index=False)

    # Teste de sanidade: com o alvo do treino embaralhado o modelo não pode acertar o teste.
    # Se acertar, há vazamento (alguma variável carrega o próprio resultado).
    y_emb = np.random.default_rng(SEMENTE).permutation(y_tr.to_numpy())
    r2_emb = r2_score(y_te, np.exp(LinearRegression().fit(treino[FEATURES], y_emb).predict(teste[FEATURES])))
    print(f"Teste de sanidade (alvo embaralhado no treino): R2 = {r2_emb:.3f} (deve ficar perto de 0 ou negativo)")
    assert r2_emb < 0.2, "Possível vazamento: o modelo acerta mesmo com o alvo embaralhado."

    # --- elasticidade (modelo final treinado em todos os meses)
    lr_final = LinearRegression().fit(ajuste[FEATURES], np.log(ajuste[alvo]))
    rf_final = RandomForestRegressor(n_estimators=100, random_state=SEMENTE, n_jobs=-1)
    rf_final.fit(ajuste[FEATURES], np.log(ajuste[alvo]))
    b = dict(zip(FEATURES, lr_final.coef_))

    # --- diagnóstico por cidade (últimos meses)
    recente = dados[dados["mes_idx"] >= corte]
    cid = (
        recente.groupby(["uf", "cidade"])
        .agg(invest_mensal=("investimento", "mean"), resultado_mensal=(alvo, "mean"))
        .reset_index()
        # recomendação: potencial mais recente (o que se conhece na hora de decidir)
        .merge(cidades, on=["uf", "cidade"], how="inner")
    )
    cid["custo_por_resultado"] = cid["invest_mensal"] / cid["resultado_mensal"].replace(0, np.nan)
    lp = np.log(cid["participacao"].to_numpy())
    la = np.log(cid["aluguel_medio"].to_numpy())
    S0 = cid["invest_mensal"].to_numpy()

    f_full = lambda v: prever(lr_final, v, lp, la)
    base_pred = f_full(S0)
    mais_pred = f_full(S0 * (1 + ACRESCIMO_MARGINAL))
    cid["elasticidade"] = b["log_invest"] + b["inter"] * lp
    cid["marginal_por_mil"] = (mais_pred - base_pred) / (S0 * ACRESCIMO_MARGINAL) * 1000
    cid["custo_marginal"] = 1000 / cid["marginal_por_mil"].clip(lower=1e-9)

    # Checagem de consistência com a Random Forest (ranking do retorno marginal)
    def prever_rf(inv):
        li = np.log(inv)
        X = pd.DataFrame({"log_invest": li, "log_potencial": lp, "log_aluguel": la,
                          "inter": li * lp})[FEATURES]
        return np.exp(rf_final.predict(X))
    marg_rf = (prever_rf(S0 * 1.25) - prever_rf(S0)) / (S0 * 0.25) * 1000
    rho = spearmanr(cid["marginal_por_mil"], marg_rf).statistic
    print(f"\nElasticidade média: {cid['elasticidade'].mean():.2f} "
          f"(min {cid['elasticidade'].min():.2f}, max {cid['elasticidade'].max():.2f})")
    print(f"Concordância de ranking do retorno marginal, Regressão Linear x Random Forest "
          f"(Spearman): {rho:.2f}")

    # --- modelo CONSERVADOR: elasticidade comum a todas as cidades (sem a interação).
    # Verba e tamanho da cidade andam juntos (correlação alta), então o modelo com
    # interação tende a exagerar as diferenças entre cidades e, com elas, o ganho.
    FEATURES_COMUM = [f_ for f_ in FEATURES if f_ != "inter"]
    lr_comum = LinearRegression().fit(ajuste[FEATURES_COMUM], np.log(ajuste[alvo]))
    f_com = lambda v: prever(lr_comum, v, lp, la, FEATURES_COMUM)
    print(f"Elasticidade comum a todas as cidades (modelo conservador): {lr_comum.coef_[0]:.2f}")
    cpl_obs = S0 / (cid["resultado_mensal"].to_numpy() + 1)

    # verdade do simulador (só existe na simulação; nunca entra no modelo)
    ft = None
    if SIMULADO:
        v = cid[["uf", "cidade"]].merge(VERDADE, on=["uf", "cidade"], how="left")
        fator = v["taxa"].to_numpy() if alvo == "cadastros" else 1.0
        ft = lambda x: fator * v["k"].to_numpy() * v["pot"].to_numpy() ** 0.45 * x ** v["expoente"].to_numpy()

    def cenario(lim):
        lo, hi = S0 * lim[0], S0 * lim[1]
        S_int, S_com = otimizar(f_full, S0, lo, hi), otimizar(f_com, S0, lo, hi)
        S_cpl = plano_por_custo(cpl_obs, S0, lo, hi)
        if abs(S_cpl.sum() / S0.sum() - 1) > 1e-3:
            print(f"  aviso: a regra por custo não fecha o orçamento com limites {lim}")
        r = {
            "limite_inferior": lim[0], "limite_superior": lim[1],
            "ganho_conservador": ganho_relativo(f_com, S_com, S0),
            "ganho_otimista": ganho_relativo(f_full, S_int, S0),
            "ganho_regra_custo_conservador": ganho_relativo(f_com, S_cpl, S0),
            "ganho_regra_custo_otimista": ganho_relativo(f_full, S_cpl, S0),
        }
        if ft is not None:
            r["ganho_verdadeiro_plano_interacao"] = ganho_relativo(ft, S_int, S0)
            r["ganho_verdadeiro_plano_comum"] = ganho_relativo(ft, S_com, S0)
            r["ganho_verdadeiro_regra_custo"] = ganho_relativo(ft, S_cpl, S0)
            r["ganho_verdadeiro_otimo"] = ganho_relativo(ft, otimizar(ft, S0, lo, hi), S0)
            faixa = sorted([r["ganho_conservador"], r["ganho_otimista"]])
            r["verdade_na_faixa"] = bool(faixa[0] <= r["ganho_verdadeiro_plano_interacao"] <= faixa[1])
        return r, S_int, S_com, S_cpl

    linhas, planos = [], {}
    for lim in LIMITES_SENSIBILIDADE:
        r, S_int, S_com, S_cpl = cenario(lim)
        linhas.append(r)
        planos[lim] = (S_int, S_com, S_cpl)
    sens = pd.DataFrame(linhas)
    S, S_com_p, S_cpl = planos[LIMITE_PRINCIPAL]
    principal = sens[(sens["limite_inferior"] == LIMITE_PRINCIPAL[0])
                     & (sens["limite_superior"] == LIMITE_PRINCIPAL[1])].iloc[0]
    lo_p, hi_p = S0 * LIMITE_PRINCIPAL[0], S0 * LIMITE_PRINCIPAL[1]

    # Ação por critério ABSOLUTO: compara o retorno marginal de cada cidade com o "preço
    # sombra" do plano otimizado, isto é, o retorno marginal que sobra nas cidades que
    # ficaram livres (fora dos limites) quando a verba está bem distribuída.
    marg_fn = lambda f, x: (f(x * (1 + ACRESCIMO_MARGINAL)) - f(x)) / (x * ACRESCIMO_MARGINAL) * 1000

    def classificar(m_, f, S_ot):
        livres = (S_ot > lo_p * 1.001) & (S_ot < hi_p * 0.999)
        lam = float(np.median(marg_fn(f, S_ot)[livres])) if livres.any() else float(np.median(m_))
        acao_ = np.where(m_ < (1 - TOLERANCIA_ACAO) * lam, "Reduzir",
                         np.where(m_ > (1 + TOLERANCIA_ACAO) * lam, "Aumentar", "Manter"))
        return lam, acao_

    m = cid["marginal_por_mil"].to_numpy()
    lam, acao = classificar(m, f_full, S)
    cid["marginal_relativo"] = m / lam
    cid["acao"] = acao
    if SIMULADO:
        S_t = otimizar(ft, S0, lo_p, hi_p)
        _, acao_t = classificar(marg_fn(ft, S0), ft, S_t)
        acordo = float((acao == acao_t).mean())
        invertidas = int(((acao == "Aumentar") & (acao_t == "Reduzir")).sum()
                         + ((acao == "Reduzir") & (acao_t == "Aumentar")).sum())

    cid["invest_sugerido"] = S
    cid["variacao_pct"] = (S / S0 - 1) * 100
    cid["invest_sugerido_conservador"] = S_com_p
    cid["invest_regra_custo"] = S_cpl
    cid["resultado_previsto_atual"] = base_pred
    cid["resultado_previsto_sugerido"] = f_full(S)

    # --- impacto: sempre sobre o resultado OBSERVADO; o ganho é uma FAIXA
    orcamento = float(S0.sum())
    resultado_obs = float(cid["resultado_mensal"].sum())
    cpl_atual = orcamento / resultado_obs
    g_con, g_otm = principal["ganho_conservador"], principal["ganho_otimista"]
    gc_con, gc_otm = principal["ganho_regra_custo_conservador"], principal["ganho_regra_custo_otimista"]
    res_con, res_otm = resultado_obs * (1 + g_con), resultado_obs * (1 + g_otm)
    cpl_con, cpl_otm = orcamento / res_con, orcamento / res_otm
    modelo_supera = bool((g_otm - gc_otm) > MARGEM_VS_REGRA * abs(gc_otm))

    print(f"\nOrçamento mensal (fixo): R$ {orcamento:,.0f}")
    print(f"Resultado OBSERVADO (média dos últimos {N_MESES_TESTE} meses): {resultado_obs:,.0f} {alvo}/mês "
          f"| custo observado: R$ {cpl_atual:,.2f}")
    print(f"Limites de verba por cidade: {LIMITE_PRINCIPAL[0]:.0%} a {LIMITE_PRINCIPAL[1]:.0%} da verba atual")
    print(f"Ganho estimado com a verba fixa (FAIXA): conservador {g_con:+.1%} | otimista {g_otm:+.1%}")
    print(f"Ganho da regra simples (verba do maior para o menor custo observado): "
          f"{gc_con:+.1%} pelo modelo conservador | {gc_otm:+.1%} pelo otimista")
    print(f"Estimativa: {resultado_obs:,.0f} -> {res_con:,.0f} a {res_otm:,.0f} {alvo}/mês | "
          f"custo R$ {cpl_atual:,.2f} -> R$ {cpl_otm:,.2f} a R$ {cpl_con:,.2f} | "
          f"economia equivalente R$ {orcamento * g_con:,.0f} a R$ {orcamento * g_otm:,.0f}/mês")
    print(f"Ações sugeridas: Reduzir {int((cid['acao'] == 'Reduzir').sum())}, "
          f"Aumentar {int((cid['acao'] == 'Aumentar').sum())}, Manter {int((cid['acao'] == 'Manter').sum())} "
          f"(retorno marginal ±{TOLERANCIA_ACAO:.0%} do preço sombra de {lam:,.1f} {alvo} por R$ 1.000)")
    if not modelo_supera:
        print(f"ATENÇÃO: o modelo com interação não supera a regra simples de custo observado por mais de "
              f"{MARGEM_VS_REGRA:.0%} do ganho dela; use a regra enquanto não houver mais dados.")

    print("\nSensibilidade ao limite de variação da verba por cidade:")
    cols = ["limite_inferior", "limite_superior", "ganho_conservador", "ganho_otimista",
            "ganho_regra_custo_conservador", "ganho_regra_custo_otimista"]
    if SIMULADO:
        cols += ["ganho_verdadeiro_plano_interacao", "ganho_verdadeiro_regra_custo",
                 "ganho_verdadeiro_otimo", "verdade_na_faixa"]
    print(sens[cols].round(3).to_string(index=False))
    if SIMULADO:
        print(f"\n[CHECAGEM COM O SIMULADOR] faixa {g_con:+.1%} a {g_otm:+.1%} | verdadeiro do plano "
              f"{principal['ganho_verdadeiro_plano_interacao']:+.1%} | regra simples {principal['ganho_verdadeiro_regra_custo']:+.1%} "
              f"| ótimo {principal['ganho_verdadeiro_otimo']:+.1%} | verdade dentro da faixa: {principal['verdade_na_faixa']}")
        print(f"[CHECAGEM COM O SIMULADOR] ações: acordo com a verdade {acordo:.0%}; invertidas {invertidas} de {len(cid)}")

    resumo_dict = {
        "alvo": alvo, "orcamento_mensal": orcamento,
        "resultado_observado": resultado_obs, "cpl_observado": cpl_atual,
        "limite_inferior": LIMITE_PRINCIPAL[0], "limite_superior": LIMITE_PRINCIPAL[1],
        "ganho_conservador": g_con, "ganho_otimista": g_otm,
        "ganho_regra_custo_conservador": gc_con, "ganho_regra_custo_otimista": gc_otm,
        "resultado_estimado_depois_conservador": res_con, "resultado_estimado_depois_otimista": res_otm,
        "cpl_estimado_depois_conservador": cpl_con, "cpl_estimado_depois_otimista": cpl_otm,
        "economia_equivalente_mensal_conservador": orcamento * g_con,
        "economia_equivalente_mensal_otimista": orcamento * g_otm,
        "modelo_supera_regra_custo": modelo_supera,
        "cidades_reduzir": int((cid["acao"] == "Reduzir").sum()),
        "cidades_aumentar": int((cid["acao"] == "Aumentar").sum()),
        "simulado": SIMULADO,
    }
    if SIMULADO:
        for c_ in ("ganho_verdadeiro_plano_interacao", "ganho_verdadeiro_regra_custo",
                   "ganho_verdadeiro_otimo", "verdade_na_faixa"):
            resumo_dict[c_] = principal[c_]
        resumo_dict["acoes_acordo_com_verdade"] = acordo
        resumo_dict["acoes_invertidas"] = invertidas
    resumo = pd.DataFrame([resumo_dict])
    resumo.to_csv(TABLES_DIR / f"eficiencia_impacto_realocacao_{alvo}{SUFIXO}.csv", index=False)
    sens.to_csv(TABLES_DIR / f"eficiencia_sensibilidade_limites_{alvo}{SUFIXO}.csv", index=False)
    cid.sort_values("marginal_por_mil").to_csv(
        TABLES_DIR / f"eficiencia_cidades_{alvo}{SUFIXO}.csv", index=False)

    # --- gráficos
    titulo = f" ({alvo}{' - SIMULADO' if SIMULADO else ''})"
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(range(len(comp)), comp["RMSE"], color=["#999", "#bbb", "#6a8f6a", "#2a6fdb", "#e08a1e"])
    ax.set_xticks(range(len(comp)))
    ax.set_xticklabels(["Dummy", "Custo médio\nx investimento", "Custo da cidade\nx investimento",
                        "Regressão\nLinear", "Random\nForest"])
    ax.set_ylabel("RMSE no teste (menor é melhor)")
    ax.set_title("Comparação de modelos" + titulo)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / f"eficiencia_comparacao_rmse_{alvo}{SUFIXO}.png", dpi=150)
    plt.close(fig)

    cores = {"Reduzir": "#d64545", "Manter": "#999999", "Aumentar": "#2e9e5b"}
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for acao, g in cid.groupby("acao"):
        ax.scatter(g["custo_por_resultado"], g["marginal_por_mil"], s=g["potencial"] ** 0.5 * 4,
                   alpha=0.7, color=cores[acao], label=acao)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Custo médio observado por resultado (R$)")
    ax.set_ylabel(f"{alvo} adicionais por R$ 1.000 a mais")
    ax.set_title("Custo médio x retorno marginal por cidade" + titulo)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / f"eficiencia_marginal_{alvo}{SUFIXO}.png", dpi=150)
    plt.close(fig)

    delta = (cid["invest_sugerido"] - cid["invest_mensal"])
    cid = cid.assign(delta=delta)
    destaque = pd.concat([cid.nsmallest(12, "delta"), cid.nlargest(12, "delta")]).sort_values("delta")
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(destaque["cidade"].str.title(), destaque["delta"],
            color=np.where(destaque["delta"] < 0, "#d64545", "#2e9e5b"))
    ax.set_xlabel("Variação sugerida de verba mensal (R$)")
    ax.set_title("Maiores realocações sugeridas" + titulo)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / f"eficiencia_realocacao_{alvo}{SUFIXO}.png", dpi=150)
    plt.close(fig)
    return comp, cid, resumo, sens


#%% EXECUÇÃO

resultados = {alvo: rodar(alvo) for alvo in ALVOS}


#%% CONCLUSÃO

print("\n============================")
print("CONCLUSÃO - EFICIÊNCIA REGIONAL")
print("============================")
for alvo, (comp, cid, resumo, sens) in resultados.items():
    r = resumo.iloc[0]
    treinados = comp[comp["Modelo"].isin(["Regressão Linear (log-log)", "Random Forest"])]
    melhor = treinados.sort_values("RMSE").iloc[0]
    forte = comp[comp["Modelo"].str.startswith("Baseline forte")].iloc[0]
    print(f"\n[{alvo}] melhor modelo no teste: {melhor['Modelo']} (RMSE {melhor['RMSE']:,.1f}) | "
          f"baseline forte (custo da cidade x investimento): RMSE {forte['RMSE']:,.1f}")
    if forte["RMSE"] <= melhor["RMSE"]:
        print("   O baseline forte iguala ou supera os modelos: o desempenho vem de conhecer o nível "
              "de cada cidade, não de aprender o efeito da verba.")
    print(f"   Custo observado R$ {r.cpl_observado:,.2f} por resultado. Ganho estimado com a verba fixa: "
          f"{r.ganho_conservador:+.1%} (conservador) a {r.ganho_otimista:+.1%} (otimista); "
          f"a regra simples de custo daria {r.ganho_regra_custo_conservador:+.1%} a {r.ganho_regra_custo_otimista:+.1%}.")
    if not r.modelo_supera_regra_custo:
        print("   O modelo não supera a regra simples de custo observado: por ora ela é igualmente boa.")
if SIMULADO:
    print("\nLEMBRETE: mídia simulada. O ganho 'verdadeiro' vem do próprio simulador e dos limites e da "
          "má alocação que ele embute; rode de novo com MIDIA_CSV real da Loft antes de usar qualquer "
          "número fora do grupo.")
else:
    print("\nO retorno marginal vem de associação histórica entre verba e resultado, não de "
          "experimento: confirmar com teste controlado de verba antes de cortar investimento.")
