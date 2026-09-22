"""Parâmetros centrais da POC não supervisionada de clusterização de municípios."""

from __future__ import annotations

from pathlib import Path

SEMENTE = 42

RAIZ = Path(__file__).resolve().parents[3]
DIR_DADOS = RAIZ / "data"
DIR_RAW = DIR_DADOS / "raw"
DIR_INTERIM = DIR_DADOS / "interim"
DIR_PROCESSED = DIR_DADOS / "processed"
DIR_TABELAS = RAIZ / "reports" / "tables"
DIR_FIGURAS = RAIZ / "reports" / "figures"

for _d in (DIR_RAW, DIR_INTERIM, DIR_PROCESSED, DIR_TABELAS, DIR_FIGURAS):
    _d.mkdir(parents=True, exist_ok=True)

POPULACAO_MINIMA = 50_000
ANO_POPULACAO = 2026

CNAE_ADMINISTRADORAS = "6822600"
CNAE_IMOBILIARIAS = "6821801"

# Nome da variável -> rótulo em português para gráficos e tabelas.
VARIAVEIS = {
    "administradoras_10k": "Administradoras de imóveis / 10 mil hab.",
    "imobiliarias_10k": "Imobiliárias e corretoras / 10 mil hab.",
    "imobiliarias_novas_pct": "Imobiliárias novas em 12 meses (%)",
    "pix_pf_por_hab": "Pix de pessoa física por habitante",
    "salario_admissao": "Salário mediano de admissão (R$)",
    "cadunico_pct": "Famílias no CadÚnico / 100 domicílios",
    "credito_per_capita": "Crédito per capita (R$)",
    "veiculos_por_hab": "Veículos por habitante",
    "saldo_emprego_pct": "Saldo de emprego / admissões em 12 meses (%)",
    "internet_movel_100": "Internet móvel 4G/5G de pessoa física / 100 hab.",
    "banda_larga_100": "Banda larga fixa / 100 hab.",
    "alavancagem": "Crédito sobre poupança (alavancagem)",
    "reserva_per_capita": "Poupança e depósito a prazo per capita (R$)",
    "corretores_seguros_10k": "Corretores de seguros / 10 mil hab.",
    "crescimento_populacional_pct": "Crescimento da população em 1 ano (%)",
    "jovens_admissoes_pct": "Admissões de 18 a 30 anos (%)",
}

# Grupos de variáveis comparados na POC.
GRUPOS = {
    "A": [
        "administradoras_10k",
        "imobiliarias_10k",
        "imobiliarias_novas_pct",
        "saldo_emprego_pct",
    ],
    "B": [
        "pix_pf_por_hab",
        "salario_admissao",
        "cadunico_pct",
        "credito_per_capita",
        "veiculos_por_hab",
    ],
    "C": [
        "administradoras_10k",
        "imobiliarias_novas_pct",
        "pix_pf_por_hab",
        "salario_admissao",
        "cadunico_pct",
        "credito_per_capita",
    ],
    "D": [
        "administradoras_10k",
        "imobiliarias_novas_pct",
        "pix_pf_por_hab",
        "cadunico_pct",
        "internet_movel_100",
        "banda_larga_100",
    ],
    # Grupo específico da fiança: oferta do mercado, risco, concorrência e demanda.
    # Nasceu de um teste que mostrou que os grupos A a D descrevem nível socioeconômico,
    # que no Brasil é quase geografia, e por isso perdiam de "região" ao explicar
    # variáveis municipais retidas.
    "E": [
        "administradoras_10k",
        "imobiliarias_novas_pct",
        "alavancagem",
        "reserva_per_capita",
        "corretores_seguros_10k",
        "crescimento_populacional_pct",
        "jovens_admissoes_pct",
    ],
}

NOMES_GRUPOS = {
    "A": "Mercado imobiliário",
    "B": "Capacidade de pagamento",
    "C": "Mercado + renda",
    "D": "Mercado + renda + marketing",
    "E": "Mercado + risco + concorrência + demanda",
}

# Variáveis que só descrevem os clusters depois de formados.
DESCRITORAS = [
    "domicilios_alugados_pct_uf",
    "inadimplencia_pf_uf",
    "fipezap_aluguel",
    "trends_fianca_uf",
    "motos_por_hab",
    "financiamento_imob_per_capita",
]

ROTULOS_DESCRITORAS = {
    "domicilios_alugados_pct_uf": "Domicílios alugados na UF (%)",
    "inadimplencia_pf_uf": "Inadimplência de pessoa física na UF (%)",
    "fipezap_aluguel": "Aluguel médio FipeZap (R$/m²)",
    "trends_fianca_uf": "Busca por fiança no Google, por UF (índice)",
    "motos_por_hab": "Motocicletas por habitante",
    "financiamento_imob_per_capita": "Financiamento imobiliário per capita (R$)",
}

COBERTURA_MINIMA_TRENDS = 0.80

# Moradores por domicílio no Brasil, PNAD Contínua 2025. Serve só para converter a
# contagem de famílias do CadÚnico em percentual; é uma constante nacional, então não
# altera a posição relativa dos municípios no cluster.
MORADORES_POR_DOMICILIO = 2.8

FAIXAS_PORTE = [
    (50_000, 100_000, "50 a 100 mil"),
    (100_000, 250_000, "100 a 250 mil"),
    (250_000, 500_000, "250 a 500 mil"),
    (500_000, 1_000_000, "500 mil a 1 milhão"),
    (1_000_000, float("inf"), "1 milhão ou mais"),
]

K_MINIMO = 2
K_MAXIMO = 10
N_SEMENTES_ROBUSTEZ = 10
N_BOOTSTRAP = 100
