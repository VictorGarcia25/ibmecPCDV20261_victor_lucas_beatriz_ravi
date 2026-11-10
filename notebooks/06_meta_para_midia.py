"""
Converte a exportação da Meta + o arquivo de MQLs/cadastros da Loft no CSV que o
script 04 espera em MIDIA_CSV: mes, uf, cidade, investimento, mqls, cadastros.

Uso: python notebooks/06_meta_para_midia.py META.csv CRM.csv SAIDA.csv
  META.csv: exportação do Gerenciador de Anúncios (Início dos relatórios, Região,
            Cidade, Valor usado (BRL)); soma campanhas e conjuntos de cada cidade-mês.
  CRM.csv : mes, uf, cidade, mqls, cadastros (vem da Loft; a Meta não tem isso).
"""
import sys
import unicodedata

import pandas as pd

UF = {"ACRE": "AC", "ALAGOAS": "AL", "AMAPA": "AP", "AMAZONAS": "AM", "BAHIA": "BA", "CEARA": "CE",
      "DISTRITO FEDERAL": "DF", "ESPIRITO SANTO": "ES", "GOIAS": "GO", "MARANHAO": "MA",
      "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS", "MINAS GERAIS": "MG", "PARA": "PA",
      "PARAIBA": "PB", "PARANA": "PR", "PERNAMBUCO": "PE", "PIAUI": "PI", "RIO DE JANEIRO": "RJ",
      "RIO GRANDE DO NORTE": "RN", "RIO GRANDE DO SUL": "RS", "RONDONIA": "RO", "RORAIMA": "RR",
      "SANTA CATARINA": "SC", "SAO PAULO": "SP", "SERGIPE": "SE", "TOCANTINS": "TO"}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.upper().strip()

meta_csv, crm_csv, saida = sys.argv[1:4]
m = pd.read_csv(meta_csv)
m["mes"] = pd.to_datetime(m["Início dos relatórios"]).dt.strftime("%Y-%m-01")
m["uf"] = m["Região"].map(lambda x: UF.get(norm(x)))
m["cidade"] = m["Cidade"].map(norm)
sem_uf = m[m["uf"].isna()]["Região"].unique()
if len(sem_uf):
    print("ATENÇÃO: regiões sem UF reconhecida (linhas ignoradas):", list(sem_uf))
m = m.dropna(subset=["uf"])
inv = m.groupby(["mes", "uf", "cidade"], as_index=False)["Valor usado (BRL)"].sum().rename(
    columns={"Valor usado (BRL)": "investimento"})

c = pd.read_csv(crm_csv)
c["mes"] = pd.to_datetime(c["mes"]).dt.strftime("%Y-%m-01")
c["uf"] = c["uf"].map(norm); c["cidade"] = c["cidade"].map(norm)

out = inv.merge(c, on=["mes", "uf", "cidade"], how="inner")
print(f"Meta: {len(inv)} cidade-mês | CRM: {len(c)} | casaram: {len(out)}")
if len(out) < 0.9 * min(len(inv), len(c)):
    print("ATENÇÃO: menos de 90% casaram; confira grafia de cidade/UF e os meses.")
out.sort_values(["mes", "uf", "cidade"]).to_csv(saida, index=False)
print("Salvo em", saida)
