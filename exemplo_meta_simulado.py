"""
Gera arquivos de EXEMPLO (dados FICTÍCIOS) no formato dos que a Loft não vai enviar:

  1. meta_ads_SIMULADO.csv  -> imita a exportação do Gerenciador de Anúncios da Meta
                               (nomes de coluna em português, uma linha por campanha,
                               conjunto, região, cidade e mês).
  2. crm_loft_SIMULADO.csv  -> imita o que viria do CRM/BigQuery da Loft
                               (mes, uf, cidade, mqls, cadastros), porque a Meta NÃO
                               informa MQL nem cadastro da Loft, só os "resultados" dela.

Os valores vêm da mesma mídia simulada do script 04. Servem só para testar o
fluxo (06_meta_para_midia.py) e ver o formato; NÃO são resultado de negócio.

Uso: LOFT_CSV=caminho/do/painel.csv python notebooks/05_exemplo_meta_simulado.py
"""
import io, os, contextlib
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI.parents[0] / "data" / "external" / "exemplos_simulados"
SAIDA.mkdir(parents=True, exist_ok=True)

os.environ.pop("MIDIA_CSV", None)
cabeca = (AQUI / "04_eficiencia_regional.py").read_text().split("#%% FUNÇÕES")[0]
g = {"__file__": str(AQUI / "04_eficiencia_regional.py"), "__name__": "exemplo"}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(cabeca, g["__file__"], "exec"), g)
base = g["dados"][["mes", "uf", "cidade", "investimento", "mqls", "cadastros"]].copy()

ESTADOS = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
           "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
           "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará",
           "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
           "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
           "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins"}
rng = np.random.default_rng(7)

# CRM da Loft (o que a Meta não tem)
base[["mes", "uf", "cidade", "mqls", "cadastros"]].to_csv(SAIDA / "crm_loft_SIMULADO.csv", index=False)

# Exportação estilo Meta: cada cidade-mês vira 2 campanhas
linhas = []
for r in base.itertuples():
    ini = pd.Timestamp(r.mes)
    fim = ini + pd.offsets.MonthEnd(0)
    parte = np.clip(rng.normal(0.6, 0.08), 0.35, 0.8)
    for camp, conj, p in (("LOFT | Aluguel | Leads", "Aberto 25-54", parte),
                          ("LOFT | Venda | Leads", "Interesse imóveis", 1 - parte)):
        gasto = r.investimento * p
        cpm = rng.lognormal(np.log(28), 0.25)
        impr = int(gasto / cpm * 1000)
        ctr = rng.lognormal(np.log(1.1), 0.25)
        cliques = int(impr * ctr / 100)
        leads_meta = int(max(0, r.mqls * p * rng.lognormal(np.log(1.5), 0.2)))  # a Meta costuma contar mais "leads"
        linhas.append({
            "Início dos relatórios": ini.date(), "Fim dos relatórios": fim.date(),
            "Nome da campanha": camp, "Nome do conjunto de anúncios": conj,
            "Região": ESTADOS[r.uf], "Cidade": r.cidade.title(),
            "Valor usado (BRL)": round(gasto, 2), "Impressões": impr,
            "Alcance": int(impr / rng.uniform(1.3, 2.0)), "Cliques no link": cliques,
            "CTR (taxa de cliques no link)": round(ctr, 2),
            "CPM (custo por 1.000 impressões) (BRL)": round(cpm, 2),
            "Resultados": leads_meta, "Tipo de resultado": "Leads",
            "Custo por resultado": round(gasto / leads_meta, 2) if leads_meta else None,
        })
pd.DataFrame(linhas).to_csv(SAIDA / "meta_ads_SIMULADO.csv", index=False)
print("Gerado em", SAIDA, "| linhas Meta:", len(linhas), "| linhas CRM:", len(base))
