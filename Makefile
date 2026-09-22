PYTHON_SISTEMA ?= /opt/homebrew/bin/python3.13
VENV = .venv
PY = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
EXPORTA = PYTHONPATH=src

.PHONY: ajuda ambiente poc poc-completa apresentacao notebook testes limpar

ajuda:
	@echo "make ambiente     cria o .venv e instala as dependencias fixadas"
	@echo "make poc          roda a POC de clusterizacao usando os dados ja baixados (~1 min)"
	@echo "make poc-completa baixa tudo de novo das fontes oficiais e roda a POC (~15 min)"
	@echo "make apresentacao  gera o PDF da apresentacao a partir das tabelas"
	@echo "make testes        roda os testes automatizados"
	@echo "make notebook     abre o notebook de resultados"
	@echo ""
	@echo "Exige o arquivo .env com GCP_PROJETO=<id do projeto no Google Cloud>"

$(VENV)/bin/python:
	$(PYTHON_SISTEMA) -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -r requirements.txt

ambiente: $(VENV)/bin/python
	@$(PY) --version

poc: ambiente
	$(EXPORTA) $(PY) -W ignore -m ibmecPCDV20261_victor_lucas_beatriz_ravi.poc_clusters

poc-completa: ambiente
	$(EXPORTA) $(PY) -W ignore -m ibmecPCDV20261_victor_lucas_beatriz_ravi.poc_clusters --baixar-tudo

apresentacao: ambiente
	$(EXPORTA) $(PY) -W ignore -c "from ibmecPCDV20261_victor_lucas_beatriz_ravi.poc_clusters import apresentacao; print(apresentacao.montar())"

testes: ambiente
	$(EXPORTA) $(PY) -m pytest tests/ -q

notebook: ambiente
	$(EXPORTA) $(VENV)/bin/jupyter notebook notebooks/02_poc_clusterizacao.ipynb

limpar:
	rm -rf $(VENV)
