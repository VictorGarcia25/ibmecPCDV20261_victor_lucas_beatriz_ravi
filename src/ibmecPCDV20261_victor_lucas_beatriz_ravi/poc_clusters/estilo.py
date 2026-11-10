"""Estilo dos gráficos da etapa de aprofundamento: o padrão visual das aulas do IBMEC."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from . import config

AZUL = "#002855"
AMARELO = "#F5C400"
CINZA = "#6C757D"
VERMELHO = "#A6192E"
AZUL_CLARO = "#4A90C2"

# Uma cor fixa por tipo de praça, igual em todos os gráficos da etapa.
CORES_PRACA = {
    "Praça madura de locação": AZUL,
    "Praça intermediária conectada": AZUL_CLARO,
    "Praça popular de grande porte": AMARELO,
    "Praça em formação": "#E07B39",
    "Praça sem mercado formal": VERMELHO,
}


def aplicar() -> None:
    sns.set_theme(style="whitegrid", palette=[AZUL, AMARELO, CINZA, VERMELHO])
    plt.rcParams.update({"axes.titleweight": "bold", "axes.titlesize": 13, "figure.dpi": 110})


def cor_da_praca(nome: str) -> str:
    return next((cor for chave, cor in CORES_PRACA.items() if nome.startswith(chave)), CINZA)


def salvar(figura, nome: str) -> None:
    figura.savefig(config.DIR_FIGURAS / f"{nome}.png", dpi=150, bbox_inches="tight")
    plt.close(figura)
