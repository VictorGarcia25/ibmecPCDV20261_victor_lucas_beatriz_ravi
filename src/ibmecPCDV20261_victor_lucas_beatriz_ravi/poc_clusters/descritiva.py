"""Estatística descritiva, decisão de log, correlação e VIF."""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.stats.outliers_influence import variance_inflation_factor

from . import config

LIMIAR_ASSIMETRIA_LOG = 1.0
LIMIAR_CORRELACAO = 0.8
LIMIAR_VIF = 10.0
QUANTIL_WINSOR = 0.01


def tabela_descritiva(base: pd.DataFrame, variaveis: list[str] | None = None) -> pd.DataFrame:
    variaveis = variaveis or list(config.VARIAVEIS)
    linhas = []
    for v in variaveis:
        s = base[v].astype(float)
        linhas.append(
            {
                "variavel": v,
                "rotulo": config.VARIAVEIS[v],
                "faltantes": int(s.isna().sum()),
                "media": s.mean(),
                "desvio_padrao": s.std(),
                "coef_variacao": s.std() / s.mean() if s.mean() else np.nan,
                "minimo": s.min(),
                "p1": s.quantile(0.01),
                "q1": s.quantile(0.25),
                "mediana": s.median(),
                "q3": s.quantile(0.75),
                "p99": s.quantile(0.99),
                "maximo": s.max(),
                "assimetria": s.skew(),
                "curtose": s.kurtosis(),
                "aplicar_log": bool(precisa_log(s)),
            }
        )
    return pd.DataFrame(linhas).round(4)


def precisa_log(serie: pd.Series) -> bool:
    """Log só entra em variável não negativa e com cauda longa à direita."""
    s = serie.dropna().astype(float)
    return bool(s.min() >= 0 and s.skew() > LIMIAR_ASSIMETRIA_LOG)


def variaveis_com_log(base: pd.DataFrame, variaveis: list[str]) -> list[str]:
    return [v for v in variaveis if precisa_log(base[v])]


def winsorizar(base: pd.DataFrame, variaveis: list[str], quantil: float = QUANTIL_WINSOR):
    """Corta as duas caudas nos quantis informados e devolve o que foi tocado.

    Necessário porque algumas fontes registram a operação onde a empresa está sediada, não
    onde o cliente mora: o crédito do ESTBAN em Osasco é a carteira nacional de um banco.
    """
    tratada = base.copy()
    registro = []
    for v in variaveis:
        inferior = base[v].quantile(quantil)
        superior = base[v].quantile(1 - quantil)
        n_baixo = int((base[v] < inferior).sum())
        n_alto = int((base[v] > superior).sum())
        tratada[v] = base[v].clip(inferior, superior)
        registro.append(
            {
                "variavel": v,
                "rotulo": config.VARIAVEIS[v],
                "limite_inferior": round(float(inferior), 3),
                "limite_superior": round(float(superior), 3),
                "municipios_cortados_abaixo": n_baixo,
                "municipios_cortados_acima": n_alto,
                "assimetria_antes": round(float(base[v].skew()), 2),
                "assimetria_depois": round(float(tratada[v].skew()), 2),
            }
        )
    return tratada, pd.DataFrame(registro)


def matriz_correlacao(base: pd.DataFrame, variaveis: list[str], metodo: str = "spearman"):
    return base[variaveis].corr(method=metodo)


def tabela_vif(base: pd.DataFrame, variaveis: list[str]) -> pd.DataFrame:
    dados = base[variaveis].dropna().astype(float)
    dados = (dados - dados.mean()) / dados.std()
    dados = dados.assign(constante=1.0)
    linhas = [
        {
            "variavel": v,
            "rotulo": config.VARIAVEIS[v],
            "vif": round(float(variance_inflation_factor(dados.values, i)), 2),
        }
        for i, v in enumerate(variaveis)
    ]
    return pd.DataFrame(linhas).sort_values("vif", ascending=False).reset_index(drop=True)


def decidir_cortes(
    base: pd.DataFrame,
    variaveis: list[str],
    limiar: float = LIMIAR_CORRELACAO,
) -> tuple[list[str], pd.DataFrame]:
    """Em cada par acima do limiar descarta uma das duas variáveis.

    Critério de desempate: fica a que o desenho da POC usa em mais grupos, porque é a que
    carrega o sentido de negócio (administradoras de imóveis é proxy de locação, que é o
    mercado da fiança; imobiliárias inclui venda). Empatado nisso, fica a de menor VIF.
    """
    correlacao = matriz_correlacao(base, variaveis).abs()
    vif = tabela_vif(base, variaveis).set_index("variavel")["vif"].to_dict()
    presenca = {
        v: sum(v in grupo for grupo in config.GRUPOS.values()) for v in variaveis
    }

    descartadas: set[str] = set()
    decisoes = []
    pares = [
        (a, b, correlacao.loc[a, b])
        for i, a in enumerate(variaveis)
        for b in variaveis[i + 1 :]
    ]
    for a, b, valor in sorted(pares, key=lambda p: -p[2]):
        if valor < limiar or a in descartadas or b in descartadas:
            continue
        if presenca[a] != presenca[b]:
            vencedora = a if presenca[a] > presenca[b] else b
            criterio = f"usada em {presenca[vencedora]} dos 4 grupos, contra {min(presenca[a], presenca[b])}"
        else:
            vencedora = a if vif.get(a, 0) <= vif.get(b, 0) else b
            criterio = "mesmo peso no desenho, ficou a de menor VIF"
        perdedora = b if vencedora == a else a
        descartadas.add(perdedora)
        decisoes.append(
            {
                "variavel_descartada": perdedora,
                "rotulo_descartada": config.VARIAVEIS[perdedora],
                "variavel_mantida": vencedora,
                "rotulo_mantida": config.VARIAVEIS[vencedora],
                "correlacao_spearman": round(float(valor), 3),
                "vif_descartada": vif.get(perdedora),
                "vif_mantida": vif.get(vencedora),
                "motivo": f"correlação de {valor:.2f} acima do limiar de {limiar:.2f}; {criterio}",
            }
        )

    mantidas = [v for v in variaveis if v not in descartadas]
    if not decisoes:
        decisoes = [
            {
                "variavel_descartada": "nenhuma",
                "rotulo_descartada": "-",
                "variavel_mantida": "-",
                "rotulo_mantida": "-",
                "correlacao_spearman": round(float(correlacao.values[~np.eye(len(variaveis), dtype=bool)].max()), 3),
                "vif_descartada": None,
                "vif_mantida": None,
                "motivo": f"nenhum par passou de {limiar:.2f}",
            }
        ]
    return mantidas, pd.DataFrame(decisoes)
