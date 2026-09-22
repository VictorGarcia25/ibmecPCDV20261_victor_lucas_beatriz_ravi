"""Variáveis descritoras, que não entram no cluster e só ajudam a nomear os grupos.

São de granularidade mais grossa que o município: UF na PNAD Contínua e no SCR, cidade no
FipeZap. Por isso ficam fora do modelo e entram apenas na leitura dos clusters.
"""

from __future__ import annotations

import io
import unicodedata

import pandas as pd
import requests

from ..io_utils import ler_raw_mais_recente, registrar_fonte, salvar_raw

SIDRA_ALUGADOS = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/6821/periodos/{ano}"
    "/variaveis/9784?localidades=N3[all]&classificacao=63[1055]"
)
ANO_PNAD_MINIMO = 2025
SCR = "https://olinda.bcb.gov.br/olinda/servico/scr_sub_regiao/versao/v1/odata/scr_sub_regiao(DataBase=@DataBase)"
FIPEZAP = "https://downloads.fipe.org.br/indices/fipezap/fipezap-serieshistoricas.xlsx"


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


def _ano_pnad_mais_recente() -> int:
    resposta = requests.get(
        "https://servicodados.ibge.gov.br/api/v3/agregados/6821/periodos", timeout=120
    )
    resposta.raise_for_status()
    return max(int(p["id"]) for p in resposta.json())


def domicilios_alugados(forcar_download: bool = False) -> pd.DataFrame:
    """Percentual de domicílios alugados por UF, PNAD Contínua anual (tabela SIDRA 6821)."""
    df = None if forcar_download else ler_raw_mais_recente("pnadc_domicilios_alugados")
    if df is None:
        ano = _ano_pnad_mais_recente()
        if ano < ANO_PNAD_MINIMO:
            raise ValueError(
                f"PNAD Contínua mais recente é {ano}; a POC exige {ANO_PNAD_MINIMO} ou posterior."
            )
        resposta = requests.get(SIDRA_ALUGADOS.format(ano=ano), timeout=300)
        resposta.raise_for_status()
        series = resposta.json()[0]["resultados"][0]["series"]
        df = pd.DataFrame(
            [
                {
                    "uf": s["localidade"]["nome"],
                    "domicilios_alugados_pct_uf": float(list(s["serie"].values())[0]),
                    "ano": ano,
                }
                for s in series
            ]
        )
        salvar_raw(df, "pnadc_domicilios_alugados")

    registrar_fonte(
        "domicilios_alugados_pct_uf",
        "IBGE - PNAD Contínua anual, condição de ocupação do domicílio (tabela SIDRA 6821)",
        str(int(df["ano"].iloc[0])),
        "percentual de domicílios alugados na UF; descritora, não entra no cluster",
    )
    return df[["uf", "domicilios_alugados_pct_uf"]]


def inadimplencia_pf(forcar_download: bool = False) -> pd.DataFrame:
    """Inadimplência de pessoa física por UF, calculada do SCR do Banco Central."""
    bruto = None if forcar_download else ler_raw_mais_recente("bcb_scr_inadimplencia_pf")
    if bruto is None:
        mes = pd.Timestamp.today().to_period("M")
        for _ in range(6):
            # Sem $filter: o Olinda rejeita o espaço codificado como + na expressão de filtro,
            # então o recorte de pessoa física é feito depois, no pandas.
            resposta = requests.get(
                SCR,
                params={"@DataBase": int(mes.strftime("%Y%m")), "$format": "json"},
                timeout=600,
            )
            # Mês ainda não publicado responde 400 nesse serviço, não 200 com lista vazia.
            if resposta.ok:
                valores = resposta.json().get("value", [])
                if valores:
                    bruto = pd.DataFrame(valores)
                    break
            elif resposta.status_code != 400:
                resposta.raise_for_status()
            mes -= 1
        if bruto is None:
            raise RuntimeError("SCR não devolveu nenhum mês com dados nos últimos 6 meses.")
        salvar_raw(bruto, "bcb_scr_inadimplencia_pf")

    # 'NI' é a UF não informada da própria fonte.
    pessoa_fisica = bruto[(bruto["CLIENTE"] == "PF") & (bruto["ESTADO"] != "NI")]
    agregado = (
        pessoa_fisica.groupby("ESTADO", as_index=False)[["CARTEIRA", "VENCIDO_ACIMA_DE_15_DIAS"]]
        .sum()
        .rename(columns={"ESTADO": "sigla_uf"})
    )
    agregado["inadimplencia_pf_uf"] = (
        agregado["VENCIDO_ACIMA_DE_15_DIAS"] / agregado["CARTEIRA"] * 100
    ).round(3)
    referencia = str(int(bruto["DATA_BASE"].iloc[0]))

    registrar_fonte(
        "inadimplencia_pf_uf",
        "Banco Central - SCR por sub-região, cliente pessoa física (API OData)",
        f"{referencia[:4]}-{referencia[4:]}",
        "carteira vencida acima de 15 dias sobre a carteira total da UF; descritora",
    )
    return agregado[["sigla_uf", "inadimplencia_pf_uf"]]


def fipezap_aluguel(forcar_download: bool = False) -> pd.DataFrame:
    """Aluguel médio por m² nas cidades cobertas pelo FipeZap."""
    df = None if forcar_download else ler_raw_mais_recente("fipezap_aluguel")
    if df is None:
        # O servidor da FIPE recusa requisição sem User-Agent de navegador.
        resposta = requests.get(
            FIPEZAP,
            timeout=600,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://fipezap.zapimoveis.com.br/"},
        )
        resposta.raise_for_status()
        planilha = pd.ExcelFile(io.BytesIO(resposta.content))
        df = _extrair_fipezap(planilha)
        salvar_raw(df, "fipezap_aluguel")

    registrar_fonte(
        "fipezap_aluguel",
        "FIPE/ZAP - índice FipeZap, séries históricas de locação residencial",
        str(df["mes_referencia"].iloc[0]),
        f"aluguel médio por m² em {len(df)} cidades; descritora, cruzada por nome de município",
    )
    return df[["cidade", "fipezap_aluguel", "mes_referencia"]]


ABAS_NAO_CIDADE = ("Resumo", "Aux", "Índice FipeZAP")


def _coluna_aluguel(bruto: pd.DataFrame) -> int | None:
    """Acha a coluna 'Locação / Preço médio (R$/m²) / Total' pelo cabeçalho de três níveis."""
    bloco = bruto.iloc[1].ffill()
    medida = bruto.iloc[2].ffill()
    detalhe = bruto.iloc[3]
    for j in range(len(detalhe)):
        if (
            "locac" in _normalizar(bloco.iloc[j])
            and "preco medio" in _normalizar(medida.iloc[j])
            and _normalizar(detalhe.iloc[j]) == "total"
        ):
            return j
    return None


def _extrair_fipezap(planilha: pd.ExcelFile) -> pd.DataFrame:
    """Uma aba por cidade, com cabeçalho de três níveis e a série mensal nas linhas."""
    registros = []
    for aba in planilha.sheet_names:
        if aba in ABAS_NAO_CIDADE:
            continue
        bruto = planilha.parse(aba, header=None)
        coluna = _coluna_aluguel(bruto)
        if coluna is None:
            continue
        datas = pd.to_datetime(bruto[1], errors="coerce")
        valores = pd.to_numeric(bruto[coluna], errors="coerce")
        validos = datas.notna() & valores.notna()
        if not validos.any():
            continue
        ultimo = validos[validos].index[-1]
        registros.append(
            {
                "cidade": aba.strip(),
                "fipezap_aluguel": round(float(valores[ultimo]), 2),
                "mes_referencia": datas[ultimo].strftime("%Y-%m"),
            }
        )
    if not registros:
        raise RuntimeError("Não consegui extrair nenhuma cidade da planilha do FipeZap.")
    return pd.DataFrame(registros)


def juntar(base: pd.DataFrame, forcar_download: bool = False) -> pd.DataFrame:
    """Anexa as descritoras à base municipal, cada uma na sua granularidade."""
    from . import trends

    resultado = base.merge(domicilios_alugados(forcar_download), on="uf", how="left")
    resultado = resultado.merge(inadimplencia_pf(forcar_download), on="sigla_uf", how="left")
    resultado = resultado.merge(
        trends.carregar_por_uf(forcar_download), on="uf", how="left"
    )

    fipezap = fipezap_aluguel(forcar_download)
    fipezap["chave"] = fipezap["cidade"].map(_normalizar)
    resultado["chave"] = resultado["municipio"].map(_normalizar)
    resultado = resultado.merge(
        fipezap[["chave", "fipezap_aluguel"]], on="chave", how="left"
    ).drop(columns="chave")
    return resultado
