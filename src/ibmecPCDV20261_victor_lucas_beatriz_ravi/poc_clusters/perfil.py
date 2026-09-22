"""Perfil, nome e leitura de negócio de cada cluster."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .descritiva import rotulo

# Regras de nome: cada cluster recebe o nome da primeira regra que ele satisfaz, olhando
# o perfil padronizado (z) das variáveis. z > 0 é acima da média nacional.
LIMIAR_ALTO = 0.4
LIMIAR_BAIXO = -0.4


def perfil_padronizado(base: pd.DataFrame, variaveis: list[str]) -> pd.DataFrame:
    """Média de cada cluster em desvios padrão em relação à média de todo o universo."""
    z = (base[variaveis] - base[variaveis].mean()) / base[variaveis].std()
    z["cluster"] = base["cluster"].to_numpy()
    return z.groupby("cluster")[variaveis].mean().round(3)


def tamanho_clusters(base: pd.DataFrame) -> pd.DataFrame:
    tabela = (
        base.groupby("cluster")
        .agg(
            municipios=("id_municipio", "size"),
            populacao=("populacao", "sum"),
            populacao_mediana=("populacao", "median"),
        )
        .reset_index()
    )
    tabela["municipios_pct"] = (tabela["municipios"] / len(base) * 100).round(1)
    tabela["populacao_pct"] = (
        tabela["populacao"] / base["populacao"].sum() * 100
    ).round(1)
    return tabela


VARIAVEIS_MERCADO = ("administradoras_10k", "imobiliarias_10k")
VARIAVEIS_RENDA = ("pix_pf_por_hab", "salario_admissao", "credito_per_capita", "veiculos_por_hab")
VARIAVEIS_DIGITAL = ("internet_movel_100", "banda_larga_100")


def _eixos(linha: pd.Series) -> dict[str, float]:
    def media(nomes):
        valores = [linha[v] for v in nomes if v in linha.index]
        return float(np.mean(valores)) if valores else 0.0

    return {
        "mercado": media(VARIAVEIS_MERCADO),
        "renda": media(VARIAVEIS_RENDA),
        "digital": media(VARIAVEIS_DIGITAL),
        "vulnerabilidade": float(linha.get("cadunico_pct", 0.0)),
        "dinamismo": float(linha.get("imobiliarias_novas_pct", 0.0)),
    }


def nomear(perfil: pd.DataFrame) -> dict[int, str]:
    """Nome curto para cada cluster, derivado do próprio perfil padronizado."""
    nomes: dict[int, str] = {}
    for cluster, linha in perfil.iterrows():
        e = _eixos(linha)
        if e["mercado"] >= 0.5 and e["renda"] >= 0.5:
            nome = "Praça madura de locação"
        elif e["mercado"] >= 0.5 and e["renda"] < 0.5:
            nome = "Praça de temporada e veraneio"
        elif e["dinamismo"] >= 0.8:
            nome = "Praça em formação"
        elif e["vulnerabilidade"] >= 0.8 and e["digital"] <= -0.5:
            nome = "Praça sem mercado formal"
        elif e["vulnerabilidade"] >= 0.3 and e["mercado"] < 0:
            nome = "Praça popular de grande porte"
        elif e["vulnerabilidade"] <= -0.3 and e["digital"] >= 0:
            nome = "Praça intermediária conectada"
        elif e["renda"] >= 0.5:
            nome = "Praça de renda sem oferta"
        else:
            nome = "Praça intermediária"
        contador = sum(1 for n in nomes.values() if n.startswith(nome))
        nomes[cluster] = nome if not contador else f"{nome} {contador + 1}"
    return nomes


def top_municipios(base: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Os maiores municípios de cada cluster, que é como a Loft reconhece a praça."""
    partes = []
    for cluster, recorte in base.groupby("cluster"):
        maiores = recorte.nlargest(n, "populacao")[
            ["cluster", "municipio", "sigla_uf", "populacao", "administradoras_10k", "pix_pf_por_hab"]
        ].copy()
        maiores["posicao"] = range(1, len(maiores) + 1)
        partes.append(maiores)
    return pd.concat(partes, ignore_index=True).round(2)


def media_por_cluster(base: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    presentes = [c for c in colunas if c in base.columns and base[c].notna().any()]
    if not presentes:
        return pd.DataFrame()
    return base.groupby("cluster")[presentes].mean().round(2).reset_index()


def composicao_geografica(base: pd.DataFrame) -> pd.DataFrame:
    tabela = pd.crosstab(base["cluster"], base["regiao"], normalize="index") * 100
    return tabela.round(1).reset_index()


def composicao_porte(base: pd.DataFrame) -> pd.DataFrame:
    tabela = pd.crosstab(base["cluster"], base["porte"], normalize="index") * 100
    return tabela.round(1).reset_index()


def tabela_valor_loft(
    perfil: pd.DataFrame, nomes: dict[int, str], tamanhos: pd.DataFrame
) -> pd.DataFrame:
    """Traduz cada cluster em leitura de fiança e ação de mídia paga."""
    leituras = {
        "Praça madura de locação": (
            "Muitas administradoras e inquilino com capacidade de pagar: o risco da fiança é "
            "baixo e o cliente B2B já existe e já vende locação.",
            "Mídia de conversão para imobiliária (Meta e Google Search em segmentação B2B), "
            "com verba concentrada e meta de custo por lead.",
        ),
        "Praça de temporada e veraneio": (
            "Densidade alta de imobiliária, mas o contrato é de curta duração e temporada, "
            "onde a fiança tradicional quase não é usada.",
            "Não colocar verba de fiança aqui. Se entrar, testar outro produto da Loft, "
            "não a fiança.",
        ),
        "Praça sem mercado formal": (
            "Praticamente não existe administradora formal e a vulnerabilidade é alta: não há "
            "cliente B2B para vender e o risco de inadimplência é o maior.",
            "Zero verba de mídia paga. Praça de exclusão no planejamento.",
        ),
        "Praça de renda sem oferta": (
            "O inquilino tem capacidade de pagar, mas a oferta de administradoras é fraca: "
            "demanda reprimida por locação organizada.",
            "Praça de expansão. Mídia de geração de demanda e prospecção de novas "
            "imobiliárias, com verba de teste antes de escalar.",
        ),
        "Praça em formação": (
            "Muita imobiliária abrindo agora: o mercado está se organizando e as empresas "
            "novas ainda não têm processo de garantia definido.",
            "Momento de entrada. Mídia de educação de produto para imobiliária nova, "
            "custo por lead ainda baixo.",
        ),
        "Praça intermediária conectada": (
            "Mercado e renda medianos, mas alcance digital alto: dá para testar barato com "
            "boa cobertura de audiência.",
            "Praça de teste A/B de criativo. Verba pequena e recorrente em Meta e TikTok "
            "para aprender antes de levar o aprendizado às praças maduras.",
        ),
        "Praça intermediária": (
            "Praça sem traço dominante: mercado, renda e alcance digital todos perto da média "
            "nacional. Não é oportunidade nem exclusão, é o meio da tabela.",
            "Verba de manutenção. Replicar o que já funciona nas praças maduras, sem criativo "
            "próprio e sem teste, até que algum indicador saia da média.",
        ),
        "Praça popular de grande porte": (
            "Cidade grande com muita gente e muito contrato potencial, mas o mercado formal de "
            "locação é raso para o tamanho dela e a vulnerabilidade está acima da média. A fiança "
            "cabe, só que o gargalo não é demanda: é falta de imobiliária organizada para vender.",
            "Praça de volume, mas de captação antes de conversão. Mídia para recrutar imobiliária "
            "nova, com meta de custo por imobiliária cadastrada, não por lead de inquilino. "
            "Verba média e análise de risco mais rígida na esteira.",
        ),
        "Praça intermediária popular": (
            "Mercado e renda abaixo da média, com vulnerabilidade acima: a fiança cabe, mas "
            "com análise de risco mais rígida.",
            "Verba mínima e apenas remarketing. Priorizar canal orgânico e parceria com "
            "imobiliária local em vez de mídia paga.",
        ),
    }
    linhas = []
    for cluster in perfil.index:
        nome = nomes[cluster]
        chave = next((c for c in leituras if nome.startswith(c)), None)
        if chave is None:
            raise KeyError(
                f"O cluster '{nome}' não tem leitura de negócio escrita em tabela_valor_loft. "
                "Toda praça nomeada precisa de significado e ação, senão a tabela entregue à "
                "Loft sai com lacuna."
            )
        significado, acao = leituras[chave]
        tamanho = tamanhos[tamanhos["cluster"] == cluster].iloc[0]
        linhas.append(
            {
                "cluster": cluster,
                "nome": nome,
                "municipios": int(tamanho["municipios"]),
                "populacao_pct": tamanho["populacao_pct"],
                "o_que_significa_para_a_fianca": significado,
                "acao_de_marketing_sugerida": acao,
            }
        )
    return pd.DataFrame(linhas)


def descricao_variaveis_chave(perfil: pd.DataFrame, nomes: dict[int, str]) -> pd.DataFrame:
    """As três variáveis que mais destacam cada cluster, para dar apoio ao nome."""
    linhas = []
    for cluster, linha in perfil.iterrows():
        ordenada = linha.reindex(linha.abs().sort_values(ascending=False).index)[:3]
        linhas.append(
            {
                "cluster": cluster,
                "nome": nomes[cluster],
                "marcas_do_cluster": "; ".join(
                    f"{rotulo(v)}: {valor:+.2f} desvios"
                    for v, valor in ordenada.items()
                ),
            }
        )
    return pd.DataFrame(linhas)
