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
    "salario_admissao": "Salário médio de admissão (R$)",
    "cadunico_pct": "Famílias no CadÚnico (%)",
    "credito_per_capita": "Crédito per capita (R$)",
    "veiculos_por_hab": "Veículos por habitante",
    "saldo_emprego_pct": "Saldo de emprego em 12 meses (% do estoque)",
    "internet_movel_100": "Internet móvel 4G/5G / 100 hab.",
    "banda_larga_100": "Banda larga fixa / 100 hab.",
    "trends_fianca": "Busca por fiança no Google (índice)",
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
}

NOMES_GRUPOS = {
    "A": "Mercado imobiliário",
    "B": "Capacidade de pagamento",
    "C": "Mercado + renda",
    "D": "Mercado + renda + marketing",
}

# Variáveis que só descrevem os clusters depois de formados.
DESCRITORAS = [
    "domicilios_alugados_pct_uf",
    "inadimplencia_pf_uf",
    "fipezap_aluguel",
]

COBERTURA_MINIMA_TRENDS = 0.80

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
