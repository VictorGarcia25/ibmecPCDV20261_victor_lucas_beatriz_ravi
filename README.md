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
- email_do_ravi

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
- verificação de correlação entre variáveis de volume;
- construção de dois baselines de referência;
- treinamento de modelos de Machine Learning;
- comparação de desempenho entre baselines e modelos;
- geração de tabelas e gráficos para análise.

---

# 2. Problema de Negócio

Em mídia paga, uma campanha que apresenta bom desempenho médio não necessariamente continuará eficiente quando o investimento for aumentado.

Por exemplo, conhecer apenas o custo médio de uma campanha não responde diretamente à pergunta:

> **Quanto resultado adicional será gerado caso o investimento aumente?**

O projeto busca criar uma base analítica para estudar esse problema.

A POC atual ainda não estima causalmente o retorno do próximo real investido. Nesta etapa, o objetivo é verificar se as informações históricas das campanhas contêm sinal suficiente para prever o volume de conversões atribuídas — e se esse sinal vai além do que já seria esperado apenas pelo volume de impressões de cada campanha.

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
Verificação de correlação entre variáveis de volume
  ↓
Divisão temporal treino/teste
  ↓
Baselines (mínimo e de negócio)
  ↓
Modelos de Machine Learning
  ↓
Avaliação das métricas
  ↓
Conclusão automática da POC
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

## 6.3 Verificação de correlação entre variáveis

Antes de definir as features do modelo, foi calculada a correlação entre `impressoes` e `cliques` na base agregada por campanha e hora.

O objetivo dessa checagem é identificar, ainda na fase exploratória, sinais de multicolinearidade entre as variáveis de volume — o que pode dificultar a interpretação dos coeficientes da Regressão Linear, mesmo sem necessariamente prejudicar a capacidade preditiva do modelo.

Nesta POC as duas variáveis foram mantidas como features, já que o foco atual é validar o sinal preditivo do pipeline. A eventual necessidade de tratar a colinearidade (por exemplo, removendo ou combinando variáveis) será reavaliada nas próximas etapas, à medida que o modelo evoluir para uma análise mais explicativa.

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

# 9. Baselines e Modelos

Foram avaliadas quatro abordagens nesta primeira POC: dois baselines de referência e dois modelos treinados.

## 9.1 Baseline mínimo — DummyRegressor

O `DummyRegressor` foi utilizado como **baseline mínimo**.

Ele gera previsões utilizando uma estratégia simples baseada na média da variável alvo observada no conjunto de treinamento.

O objetivo desse baseline é estabelecer uma referência mínima de desempenho: um modelo de Machine Learning só apresenta ganho real se conseguir superá-lo.

## 9.2 Baseline simples — Taxa média × Impressões

Como referência adicional, foi construído um segundo baseline, mais próximo de uma heurística de negócio: a taxa média de conversão observada no treino é multiplicada pelo número de impressões de cada campanha/hora no teste.

Esse baseline responde a uma pergunta mais exigente do que o `DummyRegressor`: os modelos treinados conseguem capturar algo além da relação óbvia "mais impressões geram mais conversões"? Se um modelo não superar esse baseline, é sinal de que seu ganho ainda depende, em grande parte, apenas do volume de impressões.

## 9.3 Regressão Linear

A Regressão Linear foi utilizada como primeiro modelo preditivo.

O objetivo foi verificar se existe relação entre as características agregadas das campanhas e o volume de conversões atribuídas.

## 9.4 Random Forest Regressor

Também foi utilizado o `RandomForestRegressor`.

Esse modelo combina diversas árvores de decisão e é capaz de representar relações não lineares entre as variáveis.

Nesta POC foram utilizadas **100 árvores**, com `random_state=42` para permitir reprodutibilidade.

---

# 10. Métricas de Avaliação

Os modelos foram avaliados utilizando três métricas, calculadas por uma função auxiliar (`avaliar_modelo`) reutilizada para todas as abordagens.

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

> ⚠️ **Atenção:** a tabela abaixo foi atualizada para refletir as quatro abordagens do script atual (incluindo o novo baseline simples), mas os valores da nova linha ainda não foram recalculados com os dados reais. Rodem `python notebooks/01_poc.py` com a versão atual do script e substituam os valores marcados como `A PREENCHER` pelos números gerados em `reports/tables/comparacao_modelos.csv`.

Os resultados obtidos no conjunto de teste foram:

| Modelo | MAE | RMSE | R² |
|---|---:|---:|---:|
| Baseline mínimo - Dummy | 1.2238 | 3.3948 | -0.0296 |
| Baseline simples - Taxa média x Impressões | A PREENCHER | A PREENCHER | A PREENCHER |
| Regressão Linear | **0.9236** | **1.8979** | **0.6782** |
| Random Forest | 0.9954 | 2.1979 | 0.5684 |

Nesta primeira POC, a **Regressão Linear apresentou o melhor desempenho** entre os modelos treinados.

O RMSE foi reduzido de aproximadamente **3,39 no baseline mínimo para 1,90 na Regressão Linear**, uma redução relevante.

O R² da Regressão Linear foi de aproximadamente **0,68 no conjunto de teste desta POC**.

O Random Forest também apresentou desempenho superior ao baseline mínimo, porém ficou abaixo da Regressão Linear nesta primeira análise.

O script também compara automaticamente o melhor modelo treinado (o de menor RMSE entre Regressão Linear e Random Forest) contra os **dois** baselines, separadamente:

- se o melhor modelo superar o baseline mínimo (Dummy), isso indica que existe sinal preditivo nas variáveis das campanhas;
- se o melhor modelo também superar o baseline simples (taxa média × impressões), isso indica que o modelo captura informação além do volume de impressões — um resultado mais forte do que apenas vencer o Dummy.

Caso o melhor modelo não supere o baseline simples, isso é um indício de que boa parte do desempenho atual ainda vem do volume de impressões, e reforça a necessidade das features temporais e defasadas previstas nas próximas etapas.

Como a POC utiliza apenas uma parcela inicial da base (apenas 9 horas de dados, com o conjunto de teste cobrindo somente as duas últimas), os resultados ainda não devem ser generalizados para todo o período disponível.

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

`comparacao_modelos.csv` agora traz as quatro abordagens (os dois baselines e os dois modelos treinados), e `previsoes_teste.csv` traz as previsões de todas elas lado a lado (`Real`, `Baseline_Dummy`, `Baseline_Taxa_Media`, `Regressao_Linear`, `Random_Forest`), o que facilita comparar erro por observação em vez de apenas na média.

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

Se a variável `DATA_DIR` não for encontrada, o script interrompe a execução com uma mensagem clara (`A variável DATA_DIR não foi encontrada. Confira o arquivo .env.`), em vez de um erro genérico — facilitando identificar o problema na primeira execução.

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
- verificação de correlação entre impressões e cliques;
- divisão temporal de treino e teste;
- treinamento do baseline mínimo (Dummy) e do baseline simples (taxa média × impressões);
- treinamento da Regressão Linear;
- treinamento do Random Forest;
- cálculo das métricas;
- conclusão automática comparando o melhor modelo contra os dois baselines;
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
- Como os dados estão ordenados pelo `timestamp`, a amostra representa somente a parcela inicial do período disponível (cerca de 9 horas, com apenas 2 horas no conjunto de teste).
- Os valores de `cost` e `cpo` foram transformados pela Criteo e não representam diretamente valores monetários reais.
- A análise atual identifica relações preditivas, mas não permite afirmar causalidade.
- As features utilizadas ainda representam informações do próprio período analisado.
- `impressoes` e `cliques` apresentam correlação relevante entre si, o que ainda não foi tratado nesta etapa.
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
10. validar os modelos em períodos futuros;
11. avaliar formas de tratar a colinearidade entre impressões e cliques (ex.: seleção ou combinação de variáveis).

---

# 17. Objetivo de Longo Prazo

A visão de longo prazo do projeto é evoluir para uma ferramenta capaz de apoiar decisões como:

> **Onde o próximo investimento tem maior potencial de gerar resultado adicional?**

Nesta primeira entrega, a POC tem como objetivo validar o pipeline inicial de dados, análise estatística e Machine Learning necessário para avançar para as próximas etapas do projeto.
