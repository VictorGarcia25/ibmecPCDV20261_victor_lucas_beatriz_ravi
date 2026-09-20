# Projeto de ML 4

**Repo:** ibmecPCDV20261_victor_lucas_beatriz_ravi

**Disciplina:** Ciencia de Dados 
**Python:** 3.12

## Equipe
**Membros:** Victor Garcia, Lucas Nauer, Beatriz Babinski e Ravi Oberg  
**E-mails:** victorjg252@gmail.com, lucasnauer@gmail.com, bfbabinski@gmail.com


## Estrutura do projeto
- `data/raw` : dados originais (não editar)
- `data/interim` : dados intermediários
- `data/processed` : dataset final para modelagem
- `notebooks/` : exploração/EDA (protótipos)
- `src/` : código reutilizável (pipeline)
- `models/` : artefatos treinados (pkl, joblib, etc.)
- `reports/` : relatório final + figuras/tabelas
- `configs/` : configs de experimentos (yaml/json)

## Como rodar (mínimo)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
