# Projeto de ML 4

## Incrementalidade e Tendência de Campanhas

**Repo:** `ibmecPCDV20261_victor_lucas_beatriz_ravi`  
**Disciplina:** Ciência de Dados  
**Instituição:** IBMEC  
**Python:** 3.13  

## Equipe

**Membros:**

- Victor Garcia
- Lucas Nauer
- Beatriz Babinski
- Ravi Oberg

**E-mails:**

- victorjg252@gmail.com
- lucasnauer@gmail.com
- bfbabinski@gmail.com
- adicionar_email_do_ravi

---

# 1. Visão Geral

Este projeto tem como objetivo analisar dados de campanhas de mídia digital para investigar a relação entre investimento, comportamento dos usuários e geração de conversões.

A proposta geral do projeto é evoluir para uma ferramenta capaz de apoiar decisões como:

> **Onde ainda existe espaço eficiente para aumentar o investimento em uma campanha?**

Em vez de analisar somente indicadores médios, como custo por conversão, pretende-se estudar o comportamento das campanhas ao longo do tempo e avaliar como alterações no nível de atividade e investimento se relacionam com novas conversões.

Nesta primeira entrega foi desenvolvida uma **Prova de Conceito (POC)** com foco em:

- carregamento e validação dos dados;
- análise estatística inicial;
- agregação dos dados por campanha e período;
- criação de indicadores;
- construção de um baseline;
- treinamento de modelos de Machine Learning;
- comparação de desempenho;
- geração de tabelas e gráficos para análise.

---

# 2. Problema de Negócio

Em mídia paga, uma campanha que apresenta bom desempenho médio não necessariamente continuará eficiente quando o investimento for aumentado.

Por exemplo, conhecer apenas o custo médio de uma campanha não responde diretamente à pergunta:

> **Quanto resultado adicional será gerado caso o investimento aumente?**

O projeto busca criar uma base analítica para estudar esse problema.

A POC atual ainda não estima causalmente o retorno do próximo real investido. Nesta etapa, o objetivo é verificar se as informações históricas das campanhas contêm sinal suficiente para prever o volume de conversões atribuídas.

A análise de eficiência marginal e as recomendações de aumento, manutenção ou redução de investimento serão desenvolvidas nas próximas etapas do projeto.

---

# 3. Base de Dados

O projeto utiliza dados públicos da **Criteo**, empresa especializada em publicidade digital.

A base utilizada na POC é derivada do **Criteo Attribution Modeling Dataset**, que representa dados de tráfego de campanhas de publicidade digital.

Cada linha da base original corresponde a uma impressão de anúncio exibida para um usuário.

Entre as principais variáveis estão:

| Variável | Descrição |
|---|---|
| `timestamp` | Momento da impressão |
| `uid` | Identificador anonimizado do usuário |
| `campaign` | Identificador da campanha |
| `conversion` | Indica se ocorreu conversão |
| `attribution` | Indica se a conversão foi atribuída à Criteo |
| `click` | Indica se houve clique |
| `cost` | Custo transformado da impressão |
| `cpo` | Custo por pedido transformado |
| `time_since_last_click` | Tempo desde o último clique |
| `cat1` a `cat9` | Variáveis categóricas anonimizadas |

Os valores de `cost` e `cpo` são valores transformados disponibilizados pela Criteo e não devem ser interpretados diretamente como valores monetários reais.

## Acesso aos dados

Devido ao tamanho dos arquivos, as bases de dados não são armazenadas diretamente no GitHub.

Os arquivos utilizados pelo grupo são mantidos externamente. Cada integrante deve baixar os dados para seu computador e configurar o caminho local por meio de um arquivo `.env`.

O arquivo utilizado nesta POC é:

`criteo_attribution_5milhoes.csv`

---

# 4. Amostra utilizada na POC

A base de trabalho possui aproximadamente **5 milhões de registros**.

Para esta primeira Prova de Conceito foram utilizados:

**100.000 registros**

A amostra reduzida foi utilizada para validar o pipeline de análise e modelagem com menor custo computacional.

Como a base está ordenada cronologicamente pelo `timestamp`, os primeiros 100 mil registros correspondem apenas a uma parcela inicial do período disponível.

Portanto, os resultados desta POC devem ser interpretados como uma **validação inicial do pipeline**, e não como resultados definitivos ou representativos de todo o conjunto de dados.

---

# 5. Estrutura do Projeto

A organização do projeto segue a estrutura definida pelo template Cookiecutter utilizado na disciplina.

```text
ibmecPCDV20261_victor_lucas_beatriz_ravi/
│
├── configs/
│
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
│
├── models/
│
├── notebooks/
│   └── 01_poc.py
│
├── reports/
│   ├── figures/
│   │   ├── comparacao_rmse.png
│   │   └── importancia_variaveis.png
│   │
│   └── tables/
│       ├── campanhas_agregadas_poc.csv
│       ├── comparacao_modelos.csv
│       ├── importancia_variaveis.csv
│       ├── previsoes_teste.csv
│       └── resumo_estatistico.csv
│
├── src/
│
├── .env
├── .gitignore
├── README.md
└── requirements.txt

```
## Estrutura do projeto

- `data/raw/`: dados originais, sem alterações.
- `data/interim/`: dados intermediários.
- `data/processed/`: dataset final para modelagem.
- `notebooks/`: exploração, EDA e protótipos.
- `src/`: código reutilizável e pipeline.
- `models/`: artefatos treinados (`pkl`, `joblib` etc.).
- `reports/`: relatório final, figuras e tabelas.
- `configs/`: configurações de experimentos (`yaml`, `json` etc.).

Nesta primeira entrega, o principal arquivo de execução é:

`notebooks/01_poc.py`

Os resultados gerados por esse arquivo são armazenados automaticamente nas pastas:

`reports/figures/`

e

`reports/tables/`

---

# 6. Metodologia da POC

O fluxo utilizado nesta primeira versão é:

```text
Dados
  ↓
Validação e estatística descritiva
  ↓
Agregação por campanha e hora
  ↓
Criação de indicadores
  ↓
Divisão temporal treino/teste
  ↓
Baseline
  ↓
Modelos de Machine Learning
  ↓
Avaliação das métricas
```

## 6.1 Análise inicial dos dados

Inicialmente foram realizadas verificações para entender a estrutura e a qualidade da base.

Entre as análises realizadas estão:

- dimensão da base;
- nomes e tipos das variáveis;
- valores ausentes;
- registros duplicados;
- estatísticas descritivas;
- distribuição de conversões;
- distribuição de cliques;
- quantidade de campanhas;
- análise das conversões atribuídas.

Na amostra de 100 mil registros foram identificadas **647 campanhas**.

A taxa observada de conversão foi de aproximadamente **5,15%**, enquanto cerca de **35,41% das impressões apresentaram clique**.

## 6.2 Agregação por campanha e hora

Como o objetivo do projeto é estudar o comportamento das campanhas ao longo do tempo, as impressões individuais foram agregadas por:

`campaign + hora`

A variável `hora` foi criada a partir do `timestamp`.

Para cada campanha e período foram calculados:

- número de impressões;
- número de cliques;
- número de conversões;
- número de conversões atribuídas;
- custo total;
- custo médio.

Também foram criados indicadores como:

### CTR

`CTR = cliques / impressões`

### Taxa de conversão atribuída

`taxa de conversão = conversões atribuídas / impressões`

---

# 7. Variável Alvo e Features

A variável alvo utilizada nesta POC é:

`conversoes_atribuidas`

As variáveis utilizadas como features foram:

- `impressoes`
- `cliques`
- `custo_total`
- `custo_medio`
- `ctr`

A variável `taxa_conversao` não foi utilizada como feature porque seu cálculo utiliza a própria variável alvo.

Sua inclusão poderia causar **data leakage**, fornecendo ao modelo uma informação diretamente derivada daquilo que ele deveria prever.

---

# 8. Divisão de Treino e Teste

Como a base possui componente temporal, a divisão entre treino e teste não foi realizada aleatoriamente.

Os períodos foram ordenados cronologicamente e divididos da seguinte maneira:

- **80% das primeiras horas:** conjunto de treino;
- **20% das últimas horas:** conjunto de teste.

Essa estratégia busca representar melhor uma situação real, na qual informações observadas anteriormente são utilizadas para estimar resultados de períodos posteriores.

Como a POC utiliza apenas os primeiros 100 mil registros da base, essa validação temporal ainda representa uma janela limitada do período total disponível.

---

# 9. Baseline e Modelos

Foram avaliadas três abordagens nesta primeira POC.

## 9.1 DummyRegressor

O `DummyRegressor` foi utilizado como **baseline**.

Ele gera previsões utilizando uma estratégia simples baseada na média da variável alvo observada no conjunto de treinamento.

O objetivo do baseline é estabelecer uma referência mínima de desempenho.

Um modelo de Machine Learning só apresenta ganho real se conseguir superar essa referência.

## 9.2 Regressão Linear

A Regressão Linear foi utilizada como primeiro modelo preditivo.

O objetivo foi verificar se existe relação entre as características agregadas das campanhas e o volume de conversões atribuídas.

## 9.3 Random Forest Regressor

Também foi utilizado o `RandomForestRegressor`.

Esse modelo combina diversas árvores de decisão e é capaz de representar relações não lineares entre as variáveis.

Nesta POC foram utilizadas **100 árvores**, com `random_state=42` para permitir reprodutibilidade.

---

# 10. Métricas de Avaliação

Os modelos foram avaliados utilizando três métricas.

## MAE — Mean Absolute Error

Representa o erro absoluto médio das previsões.

Quanto menor o MAE, melhor o desempenho.

## RMSE — Root Mean Squared Error

Penaliza de forma mais intensa erros maiores.

Quanto menor o RMSE, melhor o desempenho.

## R² — Coeficiente de Determinação

Indica quanto da variação da variável alvo é representada pelo modelo dentro do conjunto avaliado.

Valores maiores indicam melhor ajuste.

---

# 11. Resultados da POC

Os resultados obtidos no conjunto de teste foram:

| Modelo | MAE | RMSE | R² |
|---|---:|---:|---:|
| DummyRegressor | 1.2238 | 3.3948 | -0.0296 |
| Regressão Linear | **0.9236** | **1.8979** | **0.6782** |
| Random Forest | 0.9954 | 2.1979 | 0.5684 |

Nesta primeira POC, a **Regressão Linear apresentou o melhor desempenho** entre os modelos avaliados.

O RMSE foi reduzido de aproximadamente **3,39 no baseline para 1,90 na Regressão Linear**.

O R² da Regressão Linear foi de aproximadamente **0,68 no conjunto de teste desta POC**.

O Random Forest também apresentou desempenho superior ao baseline, porém ficou abaixo da Regressão Linear nesta primeira análise.

Esses resultados mostram que as variáveis utilizadas apresentam sinal preditivo para estimar as conversões atribuídas dentro da amostra analisada.

Como a POC utiliza apenas uma parcela inicial da base, os resultados ainda não devem ser generalizados para todo o período disponível.

---

# 12. Resultados Gerados

O script salva automaticamente tabelas e gráficos para permitir a análise e a reprodução dos resultados.

## Tabelas

Os arquivos são armazenados em:

`reports/tables/`

São gerados:

- `campanhas_agregadas_poc.csv`
- `comparacao_modelos.csv`
- `importancia_variaveis.csv`
- `previsoes_teste.csv`
- `resumo_estatistico.csv`

## Gráficos

Os gráficos são armazenados em:

`reports/figures/`

São gerados:

- `comparacao_rmse.png`
- `importancia_variaveis.png`

---

# 13. Como Rodar o Projeto

## 13.1 Clonar o repositório

Clone o repositório e entre na pasta do projeto.

```bash
git clone URL_DO_REPOSITORIO
cd ibmecPCDV20261_victor_lucas_beatriz_ravi
```

## 13.2 Criar o ambiente virtual

O projeto foi desenvolvido utilizando **Python 3.13**.

No Windows:

```bash
py -3.13 -m venv .venv
```

## 13.3 Ativar o ambiente virtual

No Command Prompt do Windows:

```bash
.venv\Scripts\activate.bat
```

Após a ativação, o terminal deverá apresentar o nome do ambiente, por exemplo:

```text
(.venv) C:\caminho\do\projeto>
```

## 13.4 Instalar as dependências

Com o ambiente virtual ativado:

```bash
python -m pip install -r requirements.txt
```

## 13.5 Configurar o caminho dos dados

As bases de dados não são versionadas no GitHub devido ao tamanho dos arquivos.

Cada integrante deve manter a base em seu próprio computador e configurar o caminho por meio de um arquivo `.env`.

Na raiz do projeto, crie o arquivo:

```text
.env
```

Dentro dele, informe:

```env
DATA_DIR=C:/caminho/para/a/pasta/dos/dados
```

Exemplo de configuração utilizada durante o desenvolvimento:

```env
DATA_DIR=C:/Users/vjuli/OneDrive/Documentos/ProjetoML_Loft
```

A pasta indicada deve conter:

```text
criteo_attribution_5milhoes.csv
```

O arquivo `.env` é específico de cada computador e não deve ser enviado para o GitHub.

Por esse motivo, ele está incluído no `.gitignore`.

## 13.6 Executar a POC

Com o ambiente virtual ativado e o `.env` configurado:

```bash
python notebooks/01_poc.py
```

O script executa automaticamente:

- carregamento dos 100 mil registros utilizados na POC;
- validação da base;
- análise estatística inicial;
- verificação de valores ausentes e duplicados;
- análise de cliques e conversões;
- agregação por campanha e hora;
- criação dos indicadores;
- divisão temporal de treino e teste;
- treinamento do baseline;
- treinamento da Regressão Linear;
- treinamento do Random Forest;
- cálculo das métricas;
- geração das tabelas;
- geração dos gráficos.

---

# 14. Dependências Principais

O projeto utiliza principalmente:

- pandas
- numpy
- scikit-learn
- matplotlib
- python-dotenv

A lista completa das dependências utilizadas está disponível em:

`requirements.txt`

---

# 15. Limitações da POC

Esta primeira versão possui algumas limitações importantes.

- Foram utilizados apenas 100 mil registros dos aproximadamente 5 milhões disponíveis na base de trabalho.
- Como os dados estão ordenados pelo `timestamp`, a amostra representa somente a parcela inicial do período disponível.
- Os valores de `cost` e `cpo` foram transformados pela Criteo e não representam diretamente valores monetários reais.
- A análise atual identifica relações preditivas, mas não permite afirmar causalidade.
- As features utilizadas ainda representam informações do próprio período analisado.
- A análise de eficiência marginal ainda não foi desenvolvida.
- Os resultados desta POC não devem ser interpretados como recomendações finais de investimento.

---

# 16. Próximas Etapas

As próximas etapas previstas para o projeto são:

1. ampliar o volume de dados utilizado;
2. analisar uma janela temporal maior;
3. desenvolver features históricas e defasadas das campanhas;
4. avaliar comportamento de investimento e conversões ao longo do tempo;
5. analisar curvas de resposta das campanhas;
6. estudar eficiência marginal;
7. estimar o custo incremental associado a novas conversões;
8. desenvolver critérios para apoiar decisões de investimento;
9. avaliar outros modelos de Machine Learning;
10. validar os modelos em períodos futuros.

---

# 17. Objetivo de Longo Prazo

A visão de longo prazo do projeto é evoluir para uma ferramenta capaz de apoiar decisões como:

> **Onde o próximo investimento tem maior potencial de gerar resultado adicional?**

Nesta primeira entrega, a POC tem como objetivo validar o pipeline inicial de dados, análise estatística e Machine Learning necessário para avançar para as próximas etapas do projeto.
---

# POC não supervisionada: tipos de praça para o produto de fiança

Responsável: Beatriz Babinski.

Complementa a POC supervisionada (`notebooks/01_poc.py`) atacando o outro lado da pergunta
"onde colocar o próximo R$ 1 em mídia paga": **em que tipo de praça**. A auditoria pública dos
anúncios da Loft mostrou que cerca de 74% das peças são de **fiança**, com a imobiliária como
cliente. Como não temos dado interno da Loft, o que se agrupa aqui é **mercado, não cliente**.

- Unidade: os **687 municípios** com 50 mil habitantes ou mais (estimativa IBGE 2026).
- 16 variáveis de mercado imobiliário, renda, risco, concorrência, demanda e alcance digital,
  todas relativas à população.
- Nenhuma variável do modelo usa dado anterior a 2025, e não há uso do Censo 2022. A regra é
  **conferida em código**: a execução aborta se alguma fonte regredir.
- Resultado: **5 tipos de praça** que superam os baselines de geografia e de porte populacional.
- Validação como variável de modelo: adicionar o rótulo do cluster a `região + porte` melhora o
  R² ajustado em **15 de 15** variáveis municipais retidas, ganho médio de **+0,044**.

Relatório completo: [`reports/poc_clusterizacao.md`](reports/poc_clusterizacao.md).
Notebook de resultados: [`notebooks/02_poc_clusterizacao.ipynb`](notebooks/02_poc_clusterizacao.ipynb).

## Como rodar

```bash
make poc
```

Cria o ambiente, reaproveita o que já está em `data/raw` e gera tabelas, figuras e relatório
em cerca de 1 minuto. Para refazer a coleta de todas as fontes oficiais:

```bash
make poc-completa
```

Exige um arquivo `.env` na raiz, fora do controle de versão, com o projeto do Google Cloud
usado nas consultas ao BigQuery da Base dos Dados:

```
GCP_PROJETO=seu-projeto-no-google-cloud
```

Testes: `PYTHONPATH=src .venv/bin/python -m pytest tests/`

## Fontes

| Variável | Fonte | Referência |
| --- | --- | --- |
| Administradoras e imobiliárias por 10 mil hab. | Receita Federal, CNPJ, CNAE 6821 e 6822 (Base dos Dados) | 2026-01 |
| Imobiliárias abertas em 12 meses | Receita Federal, CNPJ | 2026-01 |
| Pix de pessoa física por habitante | Banco Central, Transações Pix por Município (OData) | 2026-08 |
| Salário mediano de admissão | Novo CAGED, microdados (Base dos Dados) | 2026-01 |
| Saldo de emprego em 12 meses | Novo CAGED, microdados | 2026-01 |
| Famílias no CadÚnico | MDS, API MISocial do SAGI | 2026-09 |
| Crédito per capita | Banco Central, ESTBAN verbete 160 | 2025-09 |
| Automóveis por habitante | Senatran, frota por município | 2026-07 |
| Internet móvel 4G/5G de pessoa física | Anatel, acessos de telefonia móvel | 2026-07 |
| Banda larga fixa por 100 hab. | Anatel, densidade municipal (Base dos Dados) | 2025-09 |
| Alavancagem: crédito sobre poupança | Banco Central, ESTBAN verbetes 160, 420 e 432 | 2025-09 |
| Poupança e depósito a prazo per capita | Banco Central, ESTBAN verbetes 420 e 432 | 2025-09 |
| Corretores de seguros por 10 mil hab. | Receita Federal, CNPJ, CNAE 6622300 | 2026-01 |
| Crescimento da população em 1 ano | IBGE, estimativas de 2025 e 2026 | 2026 |
| Admissões de 18 a 30 anos | Novo CAGED, microdados | 2026-01 |

Descritoras, que não entram no cluster: domicílios alugados por UF (PNAD Contínua 2025),
inadimplência de pessoa física por UF (SCR do Banco Central, 2026-08), aluguel médio FipeZap
(2026-08) e busca por fiança no Google Trends por UF.
