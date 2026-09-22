"""Evidências numéricas do relatório, calculadas a partir dos dados da execução.

Existe para que nenhuma afirmação do relatório seja um número digitado à mão: quando a coleta
for refeita com dados novos, o texto acompanha em vez de mentir.
"""

from __future__ import annotations

import pandas as pd
from scipy import stats

from . import config
from .coleta import pix
from .io_utils import ler_raw_mais_recente

LIMIARES_BASE_MINIMA = (1, 10, 20, 50)


def _milhoes(valor: float) -> str:
    return f"{valor / 1e6:,.1f} milhões".replace(",", ".")


def _bilhoes(valor: float) -> str:
    return f"R$ {valor / 1e9:,.0f} bi".replace(",", ".")


ANO_MINIMO_PERMITIDO = 2025


def verificar_regra_de_datas(fontes: pd.DataFrame) -> pd.DataFrame:
    """Confere a regra inegociável do projeto: nada anterior a 2025 nas variáveis do modelo.

    A regra é conferida em código em vez de afirmada no texto, porque é ela que dá validade à
    análise: se uma fonte regredir numa coleta futura, isto tem de aparecer.
    """
    tabela = fontes.copy()
    tabela["ano_referencia"] = (
        tabela["data_referencia"].astype(str).str.extract(r"(\d{4})")[0].astype("Int64")
    )
    tabela["cumpre_a_regra"] = tabela["ano_referencia"] >= ANO_MINIMO_PERMITIDO
    return tabela[
        ["variavel", "rotulo", "data_referencia", "ano_referencia", "entra_no_cluster", "cumpre_a_regra"]
    ]


def violacoes_da_regra_de_datas(fontes: pd.DataFrame) -> pd.DataFrame:
    """Só as variáveis do modelo que descumprem a regra. Vazio é o resultado esperado."""
    tabela = verificar_regra_de_datas(fontes)
    return tabela[tabela["entra_no_cluster"] & ~tabela["cumpre_a_regra"].fillna(False)]


def populacao_brasil() -> int | None:
    bruto = ler_raw_mais_recente("ibge_populacao")
    return int(bruto["populacao"].sum()) if bruto is not None else None


def evidencia_pix() -> dict:
    """Qual mês foi descartado por estar em andamento, e com que volume."""
    bruto = ler_raw_mais_recente("bcb_pix_municipio")
    if bruto is None:
        return {}
    total = bruto.groupby("AnoMes")["VL_PagadorPF"].sum().sort_index()
    completos = pix.meses_completos(bruto)
    descartados = [m for m in total.index if m not in completos]
    if not descartados:
        return {"houve_descarte": False}
    mes = descartados[-1]
    return {
        "houve_descarte": True,
        "mes_descartado": f"{str(mes)[:4]}-{str(mes)[4:]}",
        "valor_descartado": _bilhoes(float(total.loc[mes])),
        "valor_tipico": _bilhoes(float(total.loc[completos].median())),
    }


def evidencia_salario(base: pd.DataFrame) -> dict:
    """Município onde a média do salário mais se afasta da mediana."""
    recorte = base.dropna(subset=["salario_admissao_medio", "salario_admissao_mediano"]).copy()
    recorte["distancia"] = recorte["salario_admissao_medio"] - recorte["salario_admissao_mediano"]
    pior = recorte.nlargest(1, "distancia").iloc[0]
    return {
        "municipio": pior["municipio_uf"],
        "media": f"R$ {pior['salario_admissao_medio']:,.0f}".replace(",", "."),
        "mediana": f"R$ {pior['salario_admissao_mediano']:,.0f}".replace(",", "."),
    }


def evidencia_movel(base: pd.DataFrame) -> dict:
    """Efeito de tirar as linhas de pessoa jurídica do indicador de internet móvel."""
    com_pj = base["acessos_movel_4g5g"] / base["populacao"] * 100
    so_pf = base["internet_movel_100"]
    pior = base.loc[com_pj.idxmax()]
    return {
        "municipio": pior["municipio_uf"],
        "valor_com_pj": f"{com_pj.max():,.0f}".replace(",", "."),
        "valor_so_pf": f"{so_pf.loc[com_pj.idxmax()]:,.0f}".replace(",", "."),
        "assimetria_com_pj": f"{com_pj.skew():.2f}".replace(".", ","),
        "assimetria_so_pf": f"{so_pf.skew():.2f}".replace(".", ","),
    }


def evidencia_credito(base: pd.DataFrame) -> dict:
    """Município com o maior crédito per capita, que é efeito de sede bancária."""
    pior = base.nlargest(1, "credito_per_capita").iloc[0]
    return {
        "municipio": pior["municipio_uf"],
        "valor": f"R$ {pior['credito_per_capita']:,.0f}".replace(",", "."),
        "mediana": f"R$ {base['credito_per_capita'].median():,.0f}".replace(",", "."),
        "razao": f"{pior['credito_per_capita'] / base['credito_per_capita'].median():,.0f}".replace(",", "."),
    }


def evidencia_trends(base: pd.DataFrame) -> dict:
    fontes = ler_raw_mais_recente("google_trends_fianca")
    if fontes is None:
        return {}
    cobertura = base["trends_fianca_uf"].notna().mean() if "trends_fianca_uf" in base else 0.0
    return {
        "granularidade_devolvida": "unidade da federação",
        "cobertura_uf": f"{cobertura:.0%}",
        "minimo_exigido": f"{config.COBERTURA_MINIMA_TRENDS:.0%}",
    }


def tabela_volumes(base: pd.DataFrame) -> pd.DataFrame:
    """Total nacional de cada fonte contra a ordem de grandeza conhecida do país.

    O total nacional sai do arquivo bruto, com todos os municípios do Brasil, porque é ele que
    permite confronto com a realidade. A coluna do universo mostra quanto disso está nos
    municípios analisados, o que também serve de sanidade: nunca pode passar de 100%.
    """
    from .coleta import anatel, cadunico, caged, cnpj, estban, senatran

    especificacoes = [
        (
            "ESTBAN, operações de crédito",
            lambda: estban.carregar()["credito_total"].sum(),
            base["credito_total"].sum(),
            lambda v: f"R$ {v / 1e12:,.1f} trilhões".replace(",", "."),
            "estoque de crédito do país: casa dos trilhões de reais",
        ),
        (
            "Senatran, automóveis",
            lambda: senatran.carregar()["automoveis"].sum(),
            base["automoveis"].sum(),
            _milhoes,
            "frota de automóveis do país: algumas dezenas de milhões",
        ),
        (
            "Anatel, acessos móveis 4G e 5G",
            lambda: anatel.carregar_movel()["acessos_movel_4g5g"].sum(),
            base["acessos_movel_4g5g"].sum(),
            _milhoes,
            "acessos móveis do país: algumas centenas de milhões",
        ),
        (
            "CNPJ, imobiliárias e administradoras ativas",
            lambda: cnpj.carregar()["setor_total"].sum(),
            base["setor_total"].sum(),
            lambda v: f"{int(v):,} estabelecimentos".replace(",", "."),
            "empresas do setor imobiliário: casa das centenas de milhares",
        ),
        (
            "Novo CAGED, admissões em 12 meses",
            lambda: caged.carregar()["admissoes_12m"].sum(),
            base["admissoes_12m"].sum(),
            _milhoes,
            "contratações formais no país em um ano: dezenas de milhões",
        ),
        (
            "CadÚnico, famílias cadastradas",
            lambda: cadunico.carregar()["familias_cadunico"].sum(),
            base["familias_cadunico"].sum(),
            _milhoes,
            "famílias no Cadastro Único: dezenas de milhões",
        ),
    ]

    linhas = []
    for nome, calcular_nacional, universo, formatar, esperado in especificacoes:
        try:
            nacional = float(calcular_nacional())
        except Exception:
            nacional = float("nan")
        linhas.append(
            {
                "base": nome,
                "total_no_brasil": formatar(nacional) if nacional == nacional else "indisponível",
                "total_nos_municipios_analisados": formatar(universo),
                "parcela_no_universo": (
                    f"{universo / nacional * 100:.0f}%" if nacional == nacional and nacional else "-"
                ),
                "ordem_de_grandeza_esperada": esperado,
            }
        )
    return pd.DataFrame(linhas)


def municipios_sem_mercado(base: pd.DataFrame) -> dict:
    sem = base[base["setor_total"] == 0]
    por_regiao = sem["regiao"].value_counts()
    return {
        "quantidade": len(sem),
        "por_regiao": ", ".join(f"{n} no {r}" for r, n in por_regiao.items()),
        "clusters": sem["cluster"].nunique() if "cluster" in sem else None,
        "nome_cluster": (
            sem["nome_cluster"].mode().iloc[0]
            if "nome_cluster" in sem and not sem.empty
            else None
        ),
    }


def robustez_denominador(base: pd.DataFrame, coluna_cluster: str = "cluster") -> pd.DataFrame:
    """O cluster mais dependente de 'imobiliárias novas' resiste a exigir base maior?

    A taxa de empresas novas é uma proporção com denominador pequeno em município pequeno:
    poucas aberturas viram percentual alto. Este teste repete a comparação exigindo um número
    mínimo de empresas no município.
    """
    if coluna_cluster not in base or "imobiliarias_novas_pct" not in base:
        return pd.DataFrame()

    medias = base.groupby(coluna_cluster)["imobiliarias_novas_pct"].median()
    cluster_alvo = int(medias.idxmax())

    linhas = []
    for limiar in LIMIARES_BASE_MINIMA:
        recorte = base[base["setor_total"] >= limiar]
        alvo = recorte[recorte[coluna_cluster] == cluster_alvo]["imobiliarias_novas_pct"]
        resto = recorte[recorte[coluna_cluster] != cluster_alvo]["imobiliarias_novas_pct"]
        if len(alvo) < 2 or len(resto) < 2:
            continue
        _, p = stats.mannwhitneyu(alvo, resto, alternative="greater")
        linhas.append(
            {
                "base_minima_de_empresas": limiar,
                "municipios_no_cluster": len(alvo),
                "mediana_no_cluster": round(float(alvo.median()), 1),
                "mediana_no_resto": round(float(resto.median()), 1),
                "p_valor": f"{p:.1e}",
                "continua_maior": bool(alvo.median() > resto.median() and p < 0.05),
            }
        )
    tabela = pd.DataFrame(linhas)
    tabela.attrs["cluster_alvo"] = cluster_alvo
    tabela.attrs["nome_alvo"] = (
        base.loc[base[coluna_cluster] == cluster_alvo, "nome_cluster"].iloc[0]
        if "nome_cluster" in base
        else f"cluster {cluster_alvo}"
    )
    tabela.attrs["correlacao_taxa_x_base"] = round(
        float(base["imobiliarias_novas_pct"].corr(base["setor_total"], method="spearman")), 3
    )
    return tabela
