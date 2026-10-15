# POC não supervisionada: tipos de praça para o produto de fiança da Loft

Autoria: Beatriz Babinski · Projeto em Ciência de Dados V, IBMEC · gerado em 15/10/2026

## 1. Problema

A pergunta do projeto é **onde colocar o próximo R$ 1 em mídia paga**. A auditoria pública dos
anúncios da Loft mostrou que cerca de 74% das peças são do produto de **fiança**, com a
**imobiliária** como cliente principal. A tese é que a resposta depende de produto × público ×
praça, e é a praça que esta POC ataca.

Não temos dados internos da Loft, então o objeto de agrupamento **não é cliente: é mercado**.
A pergunta que esta análise responde é: *quais tipos de praça existem no Brasil para vender
fiança, e o que isso muda na decisão de mídia?*

A abordagem é **não supervisionada**: não existe rótulo de "praça boa" para aprender. Por isso
a validação não é acurácia, e sim (a) separação interna medida por silhueta, Davies-Bouldin e
Calinski-Harabasz, (b) superioridade sobre baselines que a Loft já teria de graça (geografia e
tamanho de cidade) e (c) estabilidade sob reamostragem.

## 2. Unidade de análise e dados

Unidade: município brasileiro com **50 mil habitantes ou mais** pela estimativa do IBGE de
2026. São **687 municípios**, que concentram
70% da população do país.

Todas as variáveis são relativas à população (por habitante, por 10 mil habitantes ou por 100
domicílios), justamente para o agrupamento **não separar apenas por tamanho de cidade**.

### 2.1 Fontes e data de referência

| rotulo                                                       | fonte                                                                                   | data_referencia   | data_coleta   | entra_no_cluster   |
|:-------------------------------------------------------------|:----------------------------------------------------------------------------------------|:------------------|:--------------|:-------------------|
| Crédito sobre poupança (alavancagem)                         | Banco Central - ESTBAN, crédito sobre poupança e depósito a prazo (Base dos Dados)      | 2025-09           | 2026-10-15    | True               |
| Banda larga fixa / 100 hab.                                  | Anatel - densidade de banda larga fixa por município (Base dos Dados)                   | 2025-09           | 2026-10-15    | True               |
| Famílias no CadÚnico / 100 domicílios                        | Ministério do Desenvolvimento e Assistência Social - Cadastro Único (API MISocial/SAGI) | 2026-09           | 2026-10-15    | True               |
| Corretores de seguros / 10 mil hab.                          | Receita Federal - CNPJ, CNAE 6622300 (Base dos Dados)                                   | 2026-01-11        | 2026-10-15    | True               |
| Crédito per capita (R$)                                      | Banco Central - ESTBAN, verbete 160 operações de crédito (Base dos Dados)               | 2025-09           | 2026-10-15    | True               |
| Crescimento da população em 1 ano (%)                        | IBGE - Estimativas da população, dois anos consecutivos (tabela SIDRA 6579)             | 2026-07-01        | 2026-10-15    | True               |
| Imobiliárias potenciais (CNAE Loft) / 10 mil hab.            | Receita Federal - CNPJ, CNAE principal 6821801, 6821802, 6822600 (Base dos Dados)       | 2026-01-11        | 2026-10-15    | True               |
| Imobiliárias novas em 12 meses (%)                           | Receita Federal - CNPJ, CNAE principal 6821801, 6821802, 6822600 (Base dos Dados)       | 2026-01-11        | 2026-10-15    | True               |
| Internet móvel 4G/5G de pessoa física / 100 hab.             | Anatel - acessos de telefonia móvel por município e tecnologia (dados abertos)          | 2026-07           | 2026-10-15    | True               |
| Admissões de 18 a 30 anos (%)                                | Novo CAGED - microdados de movimentação (Base dos Dados)                                | 2026-01           | 2026-10-15    | True               |
| Imobiliárias de aluguel ou gestão (%)                        | Receita Federal - CNPJ, CNAE principal 6821801, 6821802, 6822600 (Base dos Dados)       | 2026-01-11        | 2026-10-15    | True               |
| Pix de pessoa física por habitante                           | Banco Central - Transações Pix por Município (API OData)                                | 2026-08           | 2026-10-15    | True               |
| Poupança e depósito a prazo per capita (R$)                  | Banco Central - ESTBAN, verbetes 420 e 432 poupança e depósito a prazo (Base dos Dados) | 2025-09           | 2026-10-15    | True               |
| Salário mediano de admissão (R$)                             | Novo CAGED - microdados de movimentação (Base dos Dados)                                | 2026-01           | 2026-10-15    | True               |
| Saldo de emprego / admissões em 12 meses (%)                 | Novo CAGED - microdados de movimentação (Base dos Dados)                                | 2026-01           | 2026-10-15    | True               |
| Veículos por habitante                                       | Senatran - frota de veículos por município e tipo (Base dos Dados)                      | 2026-07           | 2026-10-15    | True               |
| Domicílios alugados na UF (%)                                | IBGE - PNAD Contínua anual, condição de ocupação do domicílio (tabela SIDRA 6821)       | 2025              | 2026-10-15    | False              |
| Imobiliárias com aluguel no CNAE principal ou secundário (%) | Receita Federal - CNPJ, CNAE principal 6821801, 6821802, 6822600 (Base dos Dados)       | 2026-01-11        | 2026-10-15    | False              |
| Aluguel médio FipeZap (R$/m²)                                | FIPE/ZAP - índice FipeZap, séries históricas de locação residencial                     | 2026-08           | 2026-10-15    | False              |
| Inadimplência de pessoa física na UF (%)                     | Banco Central - SCR por sub-região, cliente pessoa física (API OData)                   | 2026-08           | 2026-10-15    | False              |
| População estimada (universo da análise)                     | IBGE - Estimativas da população (tabela SIDRA 6579)                                     | 2026-07-01        | 2026-10-15    | False              |
| poupanca_per_capita                                          | Banco Central - ESTBAN, verbete 420 depósitos de poupança (Base dos Dados)              | 2025-09           | 2026-09-21    | False              |
| Busca por fiança no Google, por UF (índice)                  | Google Trends - termos ['aluguel sem fiador', 'fiança aluguel'] (pytrends)              | 2026-10           | 2026-10-15    | False              |

Regra do projeto **conferida em código** nas 16 variáveis do modelo: a mais antiga é Crédito sobre poupança (alavancagem), com referência de 2025-09. A execução aborta se alguma fonte regredir para antes de 2025, e a conferência completa está em `02b_checagem_regra_de_datas.csv`. Não há uso do Censo 2022. O Índice Brasileiro de Conectividade da Anatel
foi **descartado** por ter 2024 como ano mais recente; no lugar dele entraram os acessos de
telefonia móvel dos dados abertos da Anatel.

### 2.2 Decisões de tratamento que mudaram o resultado

Cada número desta tabela é recalculado a cada execução, a partir dos dados coletados.

| Decisão | Motivo, com a evidência desta execução |
| --- | --- |
| Pix: descartar o mês em andamento | o mês de 2026-09 aparecia com R$ 784 bi contra R$ 1.058 bi do mês típico fechado, porque ainda estava em andamento na data da coleta. Usamos os 12 meses completos. |
| Salário de admissão: usar a mediana, não a média | Em Belo Jardim - PE a média era R$ 3.634 e a mediana R$ 1.612: poucos salários altos distorciam a comparação entre praças. |
| Internet móvel: usar só linhas de pessoa física | Com pessoa jurídica incluída, Jaboticabal - SP marcava 881 acessos por 100 habitantes, que são linhas de máquina e corporativas; só com pessoa física cai para 93. A assimetria da variável saiu de 8,13 para -0,58. |
| Veículos: usar automóveis, não a frota toda | No Brasil a moto cresce onde a renda cai, então a frota total misturaria dois sinais opostos de patrimônio. |
| Crédito: winsorizar as caudas em 1% | O ESTBAN registra a carteira onde a agência está instalada, não onde o tomador mora: Osasco - SP aparece com R$ 1.007.843 de crédito por habitante, 104 vezes a mediana de R$ 9.696, porque ali está sediado um banco de atuação nacional. |
| Google Trends: virou descritora | Mesmo pedindo resolução de cidade, a API devolve unidade da federação. Sem cobertura municipal não há como atingir o mínimo de 80% combinado. |
| CadÚnico: denominador estimado | A competência disponível não preenche a contagem de pessoas, então usamos famílias sobre domicílios estimados (2.8 moradores por domicílio, PNAD Contínua). Sendo constante nacional, não altera a posição relativa dos municípios. |

### 2.3 Qualidade da base

Cobertura final: **zero valores faltantes** nas 16 variáveis candidatas,
nos 687 municípios. Conferência de volume contra a realidade, que é o teste que pega
erro de extração:

| base                                                          | total_no_brasil          | ordem_de_grandeza_esperada                                   | total_nos_municipios_analisados   | parcela_no_universo   |
|:--------------------------------------------------------------|:-------------------------|:-------------------------------------------------------------|:----------------------------------|:----------------------|
| ESTBAN, operações de crédito                                  | R$ 6.6 trilhões          | estoque de crédito do país: casa dos trilhões de reais       | R$ 6.1 trilhões                   | 93%                   |
| Senatran, automóveis                                          | 65.6 milhões             | frota de automóveis do país: algumas dezenas de milhões      | 51.1 milhões                      | 78%                   |
| Anatel, acessos móveis 4G e 5G                                | 246.2 milhões            | acessos móveis do país: algumas centenas de milhões          | 193.4 milhões                     | 79%                   |
| CNPJ, imobiliárias potenciais ativas (filtro de CNAE da Loft) | 162.766 estabelecimentos | empresas do setor imobiliário: casa das centenas de milhares | 147.456 estabelecimentos          | 91%                   |
| Novo CAGED, admissões em 12 meses                             | 26.3 milhões             | contratações formais no país em um ano: dezenas de milhões   | 21.8 milhões                      | 83%                   |
| CadÚnico, famílias cadastradas                                | 43.4 milhões             | famílias no Cadastro Único: dezenas de milhões               | 26.9 milhões                      | 62%                   |

O total no Brasil vem do arquivo bruto, com todos os municípios, e é ele que se confronta com a
realidade conhecida. A última coluna mostra quanto disso está nos municípios analisados: se
passasse de 100% haveria linha duplicada em algum merge. É o teste que pega erro de extração
calado, do tipo unidade trocada ou junção que multiplica registros.

17 municípios do universo têm **zero** estabelecimento imobiliário
formal ativo (11 no Norte, 6 no Nordeste). Não é dado faltante: é a ausência real de mercado
formal de locação, e o modelo trata isso como informação. Todos eles caíram no mesmo cluster,
o de Praça sem mercado formal, o que é um sinal de que o agrupamento leu esse fato.

## 3. Método

Pipeline por grupo de variáveis: **log nas variáveis de cauda longa → padronização →
modelo**, com winsorização de 1% nas duas caudas antes do log. Semente fixa em
42.

Variáveis com log nesta execução: Imobiliárias potenciais (CNAE Loft) / 10 mil hab., Imobiliárias novas em 12 meses (%).

### 3.1 Corte por correlação

Limiar de 0.80 em módulo na correlação de Spearman. Em cada par acima do
limiar fica a variável que o desenho da POC usa em mais grupos, porque é a que carrega o
sentido de negócio; empatado nisso, fica a de menor VIF.

| rotulo_descartada                   | rotulo_mantida                                    |   correlacao_spearman | motivo                                                                        |
|:------------------------------------|:--------------------------------------------------|----------------------:|:------------------------------------------------------------------------------|
| Corretores de seguros / 10 mil hab. | Imobiliárias potenciais (CNAE Loft) / 10 mil hab. |                 0.839 | correlação de 0.84 acima do limiar de 0.80; usada em 4 dos 4 grupos, contra 1 |
| Veículos por habitante              | Famílias no CadÚnico / 100 domicílios             |                 0.81  | correlação de 0.81 acima do limiar de 0.80; usada em 3 dos 4 grupos, contra 1 |

O maior VIF é de 6.55, em Veículos por habitante, bem abaixo do limiar usual de 10. Não há multicolinearidade grave entre as variáveis que sobraram.

### 3.2 Grupos comparados

| grupo   | nome                                     |   n_variaveis | variaveis                                                                                                                                                                                                                                       |   k_do_cotovelo |
|:--------|:-----------------------------------------|--------------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------:|
| A       | Mercado imobiliário                      |             4 | Imobiliárias potenciais (CNAE Loft) / 10 mil hab., Imobiliárias de aluguel ou gestão (%), Imobiliárias novas em 12 meses (%), Saldo de emprego / admissões em 12 meses (%)                                                                      |               5 |
| B       | Capacidade de pagamento                  |             4 | Pix de pessoa física por habitante, Salário mediano de admissão (R$), Famílias no CadÚnico / 100 domicílios, Crédito per capita (R$)                                                                                                            |               4 |
| C       | Mercado + renda                          |             6 | Imobiliárias potenciais (CNAE Loft) / 10 mil hab., Imobiliárias novas em 12 meses (%), Pix de pessoa física por habitante, Salário mediano de admissão (R$), Famílias no CadÚnico / 100 domicílios, Crédito per capita (R$)                     |               5 |
| D       | Mercado + renda + marketing              |             6 | Imobiliárias potenciais (CNAE Loft) / 10 mil hab., Imobiliárias novas em 12 meses (%), Pix de pessoa física por habitante, Famílias no CadÚnico / 100 domicílios, Internet móvel 4G/5G de pessoa física / 100 hab., Banda larga fixa / 100 hab. |               5 |
| E       | Mercado + risco + concorrência + demanda |             6 | Imobiliárias potenciais (CNAE Loft) / 10 mil hab., Imobiliárias novas em 12 meses (%), Crédito sobre poupança (alavancagem), Poupança e depósito a prazo per capita (R$), Crescimento da população em 1 ano (%), Admissões de 18 a 30 anos (%)  |               4 |

Três modelos por grupo: KMeans, Aglomerativo com ligação de Ward e Mistura Gaussiana, com k de
2 a 10.

## 4. Escolha de k, e um achado desconfortável

A silhueta é máxima em **k = 2** em praticamente todas as combinações, e cai de forma
monotônica a partir daí. Isso não é defeito de implementação: significa que o Brasil municipal,
nessas variáveis, é um **contínuo socioeconômico**, não um conjunto de grupos bem separados.

Aceitar k = 2 seria entregar à Loft uma divisão entre praça rica e praça pobre, que não orienta
decisão de mídia. Por isso o k foi escolhido pelo **cotovelo da inércia**, e a qualidade do
resultado foi julgada pela comparação com os baselines, que é o teste que importa.

k do cotovelo por grupo: A = 5, B = 4, C = 5, D = 5, E = 4.

Configuração escolhida: **grupo D (Mercado + renda + marketing), modelo
KMeans, k = 5**. O critério está detalhado
logo abaixo: entre os grupos que respondem à pergunta de negócio (mercado imobiliário,
capacidade de pagamento **e** alcance digital, porque a pergunta é sobre mídia paga), com todos
os clusters acima de 20 municípios e nenhum acima de 40% deles, vale a maior silhueta; quando
a diferença de silhueta é menor que 0,02, o desempate é a estabilidade na reamostragem.

| grupo   | nome_grupo                  | nome_modelo         |   k |   silhueta |   davies_bouldin |   calinski_harabasz |   menor_cluster |
|:--------|:----------------------------|:--------------------|----:|-----------:|-----------------:|--------------------:|----------------:|
| B       | Capacidade de pagamento     | KMeans              |   4 |   0.325403 |          1.04193 |             474.709 |              79 |
| B       | Capacidade de pagamento     | Aglomerativo (Ward) |   4 |   0.318937 |          1.0902  |             423.148 |              49 |
| C       | Mercado + renda             | KMeans              |   5 |   0.303255 |          1.1407  |             375.082 |              62 |
| C       | Mercado + renda             | Aglomerativo (Ward) |   5 |   0.269247 |          1.17123 |             335.183 |              64 |
| D       | Mercado + renda + marketing | KMeans              |   5 |   0.266406 |          1.21379 |             373.832 |              84 |
| B       | Capacidade de pagamento     | Mistura Gaussiana   |   4 |   0.25638  |          1.27456 |             296.232 |              49 |
| A       | Mercado imobiliário         | KMeans              |   5 |   0.249928 |          1.19043 |             266.445 |              38 |
| C       | Mercado + renda             | Mistura Gaussiana   |   5 |   0.236327 |          1.32677 |             298.102 |              86 |
| D       | Mercado + renda + marketing | Mistura Gaussiana   |   5 |   0.225645 |          1.44028 |             287.349 |              86 |

Sobre a hipótese inicial de que o grupo D separaria melhor: na silhueta pura, quem ganha é o grupo B (Capacidade de pagamento), com 0.325. Isso **não** faz dele o melhor modelo: a silhueta premia espaços com menos variáveis e mais redundantes, e um grupo só de renda ou só de mercado não diz onde vender fiança.

Depois da reunião com a Loft o critério ficou explícito em três regras de negócio, decididas antes de olhar qual grupo venceria: (1) o grupo precisa ter mercado, capacidade de pagamento **e** alcance digital, porque a pergunta é onde pôr mídia paga e sem alcance não se sabe se o real investido chega a alguém; (2) nenhuma praça pode ter mais de 40% dos municípios, senão ela vira "o resto do Brasil" e não orienta verba; (3) todo cluster precisa de pelo menos 20 municípios.

| grupo   | nome_grupo                  | nome_modelo   |   k |   silhueta |   estabilidade_bootstrap | escolhido   |
|:--------|:----------------------------|:--------------|----:|-----------:|-------------------------:|:------------|
| D       | Mercado + renda + marketing | KMeans        |   5 |   0.266406 |                   0.794  | True        |
| C       | Mercado + renda             | KMeans        |   5 |   0.303255 |                   0.7748 | False       |

O concorrente mais forte fora do critério é o grupo C, sem variável de alcance digital. Ele separa um pouco mais (0.303 contra 0.266). Reamostrando os municípios 200 vezes e refazendo o preparo dentro de cada subamostra:

| configuracao_a   | configuracao_b   |   silhueta_media_a |   silhueta_media_b |   diferenca_media |   intervalo_95_inferior |   intervalo_95_superior |   vezes_que_a_venceu_pct | diferenca_significativa   |   n_reamostragens |
|:-----------------|:-----------------|-------------------:|-------------------:|------------------:|------------------------:|------------------------:|-------------------------:|:--------------------------|------------------:|
| D                | C                |             0.2585 |             0.2855 |            -0.027 |                 -0.0423 |                 -0.0114 |                        0 | True                      |               200 |

Na estabilidade, D fica com 0.794 contra 0.775 de C (maior). A vantagem de C em separação é pequena perto da vantagem do próprio agrupamento sobre a geografia (cerca de 0.262).

**Veredito: mantemos o grupo D.** Não porque ele vence todas as métricas, e sim porque é o único que tem as três dimensões que a decisão de mídia paga exige, continua muito acima dos baselines e se reproduz bem em amostras novas. O alcance digital quase não separa praças (a variável de menor dispersão entre as do grupo escolhido é **Internet móvel 4G/5G de pessoa física / 100 hab.**, com coeficiente de variação de 0,17.), mas traz para o modelo a dimensão em que a verba é executada.

## 5. Baselines: o cluster ganha de geografia e de porte?

Este é o critério de aceite do projeto. Todos os agrupamentos são avaliados **no mesmo espaço
de variáveis**, então a silhueta é comparável.

| agrupamento                               |   n_grupos |   silhueta |   rand_ajustado_vs_cluster |
|:------------------------------------------|-----------:|-----------:|---------------------------:|
| Clusters da POC                           |          5 |     0.2664 |                     1      |
| Baseline: 5 regiões do IBGE               |          5 |     0.0049 |                     0.1878 |
| Baseline: faixas de porte populacional    |          5 |    -0.1083 |                     0.0347 |
| Baseline: sorteio aleatório (média de 30) |          5 |    -0.0339 |                    -0.0002 |

Leitura:

- O agrupamento da POC tem silhueta de **0.266**, contra
  **0.005** das 5 regiões do IBGE e
  **-0.108** das faixas de porte populacional. O baseline aleatório
  fica em -0.034. **O cluster bate a geografia e o porte.**
- O Rand ajustado contra o porte é de apenas **0.035**:
  o modelo **não redescobriu o tamanho da cidade**, que era o risco principal desta análise.
- Contra a região o Rand ajustado é **0.188**: existe
  alguma relação com geografia, o que é esperado num país desigual, mas longe de ser a mesma
  coisa. Se fosse, bastaria comprar mídia por região.

Comparação dos quatro grupos contra os baselines: tabela `10_baselines_por_grupo.csv`.

## 6. Robustez

- **Reamostragem** (99 comparações, subamostras sem reposição de
  80% dos municípios): Rand ajustado médio de
  **0.802** (desvio 0.091,
  faixa de 0.642 a 0.942).
  A reamostragem é sem reposição de propósito: com reposição, os municípios duplicados ficam a
  distância zero um do outro e inflam a concordância entre rodadas.
- **Metade treino, metade teste** (100 comparações): os municípios são
  sorteados em duas metades; o modelo aprende cortes, log, padronização e centros só numa
  metade e classifica a outra, que nunca viu. Comparado com o agrupamento que a metade de
  teste forma sozinha, o Rand ajustado médio é **0.659** (faixa de
  0.493 a 0.812). Os tipos de praça se
  repetem em municípios que o modelo não conhecia.
- **Sementes**: 10 sementes diferentes, Rand ajustado médio contra a solução de
  referência de **0.980** (mínimo
  0.951).
- **Ablação**: remoção de uma variável por vez.

| rotulo                                            |   silhueta_sem_ela |   silhueta_completa |   variacao |   rand_ajustado_vs_completo |
|:--------------------------------------------------|-------------------:|--------------------:|-----------:|----------------------------:|
| Imobiliárias novas em 12 meses (%)                |             0.2482 |              0.2664 |    -0.0182 |                      0.6042 |
| Famílias no CadÚnico / 100 domicílios             |             0.2736 |              0.2664 |     0.0071 |                      0.5736 |
| Pix de pessoa física por habitante                |             0.2831 |              0.2664 |     0.0167 |                      0.759  |
| Imobiliárias potenciais (CNAE Loft) / 10 mil hab. |             0.2878 |              0.2664 |     0.0214 |                      0.7167 |
| Banda larga fixa / 100 hab.                       |             0.2927 |              0.2664 |     0.0262 |                      0.6995 |
| Internet móvel 4G/5G de pessoa física / 100 hab.  |             0.2957 |              0.2664 |     0.0293 |                      0.5325 |

A variável mais crítica é **Imobiliárias novas em 12 meses (%)**: sem ela a silhueta varia -0.018. A menos crítica é **Internet móvel 4G/5G de pessoa física / 100 hab.** (+0.029). O Rand ajustado contra a solução completa mostra quanto a composição dos grupos muda ao remover cada variável.

- **Validação externa com os anúncios dos portais (base da Loft, 2026-04 a 2026-08)**: o volume de anúncios de aluguel por habitante segue a ordem Praça madura de locação > Praça intermediária conectada > Praça popular de grande porte > Praça em formação > Praça sem mercado formal (Kruskal-Wallis H = 145.1, p < 0,001). A base cobre 361 dos 687 municípios. Controlando por região e porte, o cluster acrescenta pouco ao volume de anúncios (R² ajustado de 0.500 para 0.501): ele ordena o mercado, mas o tamanho do mercado anunciado é explicado sobretudo por porte e região. Os anúncios ficaram fora do modelo de propósito, só como prova. Os volumes ficam em reports/interno, fora do repositório.

### 6.1 A taxa de empresas novas não é artefato de base pequena

A variável de imobiliárias abertas em 12 meses é uma proporção, e proporção com denominador
pequeno engana: num município com 9 imobiliárias, três aberturas já viram 33%. Como é essa a
variável que mais define o cluster de **Praça em formação**, ela foi testada exigindo um número
mínimo de empresas no município.

|   base_minima_de_empresas |   municipios_no_cluster |   mediana_no_cluster |   mediana_no_resto |   p_valor | continua_maior   |
|--------------------------:|------------------------:|---------------------:|-------------------:|----------:|:-----------------|
|                         1 |                     113 |                 20   |               12   |   3.5e-27 | True             |
|                        10 |                      71 |                 18.8 |               12.5 |   8.1e-12 | True             |
|                        20 |                      30 |                 19.7 |               12.8 |   1.6e-07 | True             |
|                        50 |                       4 |                 17.8 |               12.9 |   0.016   | True             |

O cluster continua com taxa de abertura muito acima do resto mesmo quando se exige base maior,
e a correlação de Spearman entre a taxa e o número de empresas do município é de apenas
0,162, ou seja **a taxa alta não vem de denominador pequeno**. O achado
sobrevive ao teste. Ainda assim a variável é ruidosa em município de base curta, e é por isso
que ela entra winsorizada.

### 6.2 O cluster serve como variável de um modelo futuro?

Separação interna e estabilidade dizem que o agrupamento é consistente, mas não dizem se ele é
**útil como entrada de modelo**. O teste para isso é outro, e a pergunta certa não é se o
cluster substitui a geografia: é se ele **acrescenta** algo a ela.

Comparamos, em variáveis municipais que ficaram **fora** do modelo, o R² ajustado de
`região + porte` contra `região + porte + cluster`. O R² é ajustado para não premiar o simples
aumento de parâmetros.

| rotulo                                                       |   r2_regiao_e_porte |   r2_com_o_cluster |   ganho | o_cluster_acrescenta   |
|:-------------------------------------------------------------|--------------------:|-------------------:|--------:|:-----------------------|
| Corretores de seguros / 10 mil hab.                          |              0.404  |             0.5548 |  0.1509 | True                   |
| Imobiliárias com aluguel no CNAE principal ou secundário (%) |              0.1194 |             0.2209 |  0.1015 | True                   |
| Veículos por habitante                                       |              0.7353 |             0.8181 |  0.0828 | True                   |
| Motocicletas por habitante                                   |              0.159  |             0.2288 |  0.0697 | True                   |
| Salário mediano de admissão (R$)                             |              0.5579 |             0.6096 |  0.0517 | True                   |
| Crescimento da população em 1 ano (%)                        |              0.2272 |             0.2779 |  0.0507 | True                   |
| Poupança e depósito a prazo per capita (R$)                  |              0.2926 |             0.3247 |  0.0321 | True                   |
| Financiamento imobiliário per capita (R$)                    |              0.1375 |             0.1684 |  0.0309 | True                   |
| Imobiliárias de aluguel ou gestão (%)                        |              0.0478 |             0.0727 |  0.0249 | True                   |
| Admissões de 18 a 30 anos (%)                                |              0.39   |             0.4133 |  0.0233 | True                   |
| Domicílios alugados na UF (%)                                |              0.5466 |             0.5659 |  0.0193 | True                   |
| Saldo de emprego / admissões em 12 meses (%)                 |              0.1509 |             0.1699 |  0.019  | True                   |
| Crédito per capita (R$)                                      |              0.0756 |             0.0866 |  0.011  | True                   |
| Inadimplência de pessoa física na UF (%)                     |              0.5167 |             0.5246 |  0.0079 | True                   |
| Busca por fiança no Google, por UF (índice)                  |              0.8189 |             0.8231 |  0.0042 | True                   |
| Crédito sobre poupança (alavancagem)                         |              0.1422 |             0.1436 |  0.0015 | True                   |

O cluster acrescenta informação em **16 de 16** variáveis retidas, com ganho médio de **+0.0426** no R² ajustado. Em nenhuma ele piora. **O rótulo do cluster é, portanto, uma variável válida para alimentar um modelo futuro**: ele carrega algo que região e porte, juntos, não carregam. O maior ganho está em Corretores de seguros / 10 mil hab., de 0.404 para 0.555.

Vale registrar o caminho até aqui, porque ele muda a interpretação. O primeiro teste feito foi
outro: pedir que o cluster **vencesse** a região ao explicar as mesmas variáveis retidas. Nesse
formato o cluster perdia, e a conclusão parecia ser que o agrupamento não servia. O teste estava
mal formulado. No Brasil, quase toda variável socioeconômica municipal é fortemente explicada
pela região, então exigir que um agrupamento derrote a geografia é exigir que ele seja um proxy
melhor de desigualdade regional, que não é a função dele. A função é separar praças que devem
receber o mesmo tratamento de mídia, e para isso o que importa é informação incremental.

## 7. Os tipos de praça encontrados

|   cluster | nome                          |   municipios |   municipios_pct |   populacao_pct |   populacao_mediana |
|----------:|:------------------------------|-------------:|-----------------:|----------------:|--------------------:|
|         0 | Praça madura de locação       |          119 |             17.3 |            41.3 |            231452   |
|         1 | Praça popular de grande porte |          157 |             22.9 |            28   |            124040   |
|         2 | Praça sem mercado formal      |           84 |             12.2 |             4   |             62895.5 |
|         3 | Praça intermediária conectada |          214 |             31.1 |            18.7 |             98962.5 |
|         4 | Praça em formação             |          113 |             16.4 |             8.1 |             79611   |

Assinatura de cada cluster, em desvios padrão em relação à média dos 687 municípios:

|   cluster | nome                          | marcas_do_cluster                                                                                                                                                        |
|----------:|:------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|         0 | Praça madura de locação       | Imobiliárias potenciais (CNAE Loft) / 10 mil hab.: +1.17 desvios; Pix de pessoa física por habitante: +1.16 desvios; Banda larga fixa / 100 hab.: +1.14 desvios          |
|         1 | Praça popular de grande porte | Internet móvel 4G/5G de pessoa física / 100 hab.: +0.48 desvios; Famílias no CadÚnico / 100 domicílios: +0.44 desvios; Banda larga fixa / 100 hab.: -0.39 desvios        |
|         2 | Praça sem mercado formal      | Internet móvel 4G/5G de pessoa física / 100 hab.: -1.37 desvios; Imobiliárias novas em 12 meses (%): -1.36 desvios; Banda larga fixa / 100 hab.: -1.18 desvios           |
|         3 | Praça intermediária conectada | Famílias no CadÚnico / 100 domicílios: -0.82 desvios; Banda larga fixa / 100 hab.: +0.58 desvios; Imobiliárias novas em 12 meses (%): -0.08 desvios                      |
|         4 | Praça em formação             | Imobiliárias novas em 12 meses (%): +1.12 desvios; Famílias no CadÚnico / 100 domicílios: +0.98 desvios; Internet móvel 4G/5G de pessoa física / 100 hab.: -0.92 desvios |

Figuras: `07_perfil_clusters.png` (heatmap), `08_radar_clusters.png` (radar),
`09_mapa_clusters.png` (mapa do Brasil), `10_mapa_de_decisao.png`.

Os dez maiores municípios de cada cluster estão em `18_top_municipios.csv`.

## 8. Valor para a Loft

|   cluster | nome                          |   municipios |   populacao_pct | o_que_significa_para_a_fianca                                                                                                                                                                                                                               | acao_de_marketing_sugerida                                                                                                                                                                                                 |
|----------:|:------------------------------|-------------:|----------------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|         0 | Praça madura de locação       |          119 |            41.3 | Muitas imobiliárias e inquilino com capacidade de pagar: o risco da fiança é baixo e o cliente B2B já existe e já vende locação.                                                                                                                            | Mídia de conversão para imobiliária (Meta e Google Search em segmentação B2B), com verba concentrada e meta de custo por lead.                                                                                             |
|         1 | Praça popular de grande porte |          157 |            28   | Cidade grande com muita gente e muito contrato potencial, mas o mercado formal de locação é raso para o tamanho dela e a vulnerabilidade está acima da média. A fiança cabe, só que o gargalo não é demanda: é falta de imobiliária organizada para vender. | Praça de volume, mas de captação antes de conversão. Mídia para recrutar imobiliária nova, com meta de custo por imobiliária cadastrada, não por lead de inquilino. Verba média e análise de risco mais rígida na esteira. |
|         2 | Praça sem mercado formal      |           84 |             4   | Praticamente não existe imobiliária formal e a vulnerabilidade é alta: não há cliente B2B para vender e o risco de inadimplência é o maior.                                                                                                                 | Zero verba de mídia paga. Praça de exclusão no planejamento.                                                                                                                                                               |
|         3 | Praça intermediária conectada |          214 |            18.7 | Mercado e renda medianos, mas alcance digital alto: dá para testar barato com boa cobertura de audiência.                                                                                                                                                   | Praça de teste A/B de criativo. Verba pequena e recorrente em Meta e TikTok para aprender antes de levar o aprendizado às praças maduras.                                                                                  |
|         4 | Praça em formação             |          113 |             8.1 | Muita imobiliária abrindo agora: o mercado está se organizando e as empresas novas ainda não têm processo de garantia definido.                                                                                                                             | Momento de entrada. Mídia de educação de produto para imobiliária nova, custo por lead ainda baixo.                                                                                                                        |

## 9. Limitações

1. **Ainda sem dado de mídia da Loft.** Já usamos a regra de CNAE e a base de anúncios da Loft,
   mas não há investimento, MQL, cadastro nem sinistro por praça. O agrupamento descreve o
   mercado, não o desempenho da Loft nele.
2. **Os grupos não são naturais.** A silhueta cai com k e o melhor valor puro é k = 2. Os
   clusters são um **corte útil de um contínuo**, não fronteiras que existem na natureza. A
   defesa deles é a comparação com os baselines, não a separação absoluta.
3. **Efeito de sede na fonte.** ESTBAN e telefonia móvel registram a operação onde a empresa
   está sediada. Tratamos com winsorização e com o filtro de pessoa física, mas o viés não
   desaparece: praças que sediam banco ou operadora continuam distorcidas.
4. **CNAE não é produto.** Usamos o filtro da Loft (CNAE principal 6821801, 6821802 e 6822600,
   empresa ativa), mas o CNAE não distingue contrato residencial de temporada nem diz se a
   imobiliária usa garantia locatícia.
5. **Base dos Dados tem defasagem no acesso gratuito.** CNPJ e CAGED só liberam até 2026-01 sem
   assinatura, embora a fonte original esteja mais adiantada.
6. **Google Trends não desce a município**, então a intenção de busca por fiança só existe como
   descritora por UF.
7. **CadÚnico com denominador estimado**, pelo motivo já descrito.
8. **A taxa de empresas novas é ruidosa em praça pequena.** É uma proporção sobre base curta:
   num município com poucas imobiliárias, duas ou três aberturas já produzem percentual alto.
   O teste da seção 6.1 mostra que o achado sobrevive a exigir base maior, e a winsorização
   corta os casos extremos, mas a variável continua sendo a menos precisa do conjunto.
9. **O FipeZap cobre poucas cidades.** Como descritora, ele fica vazio nos clusters formados por
   municípios pequenos, então não serve para comparar todos os grupos entre si.
10. **A escolha do grupo D é um julgamento de negócio, não um resultado automático.** C separa
    um pouco melhor, mas não tem alcance digital, que a decisão de mídia paga exige. O
    critério está registrado na seção 4 para quem quiser decidir diferente.
11. **A base de anúncios é incompleta.** Cobre só parte dos municípios, quase nada do Norte e do
    Nordeste, e mudou de coleta em 2024. Serve como validação, não como variável.

## 10. Próximos passos

1. **Cruzar com os dados de mídia da Loft** (investimento, MQL e cadastro, agregados por data,
   canal e campanha) e calcular o **custo do próximo MQL por tipo de praça**.
2. **Quantificar a realocação**: quanto investimento sai de praças de baixa propensão e quantos
   MQLs a mais essa verba gera nas outras.
3. **Otimização de orçamento**: dado um orçamento mensal, recomendar a divisão entre canais,
   campanhas e praças. A metodologia vale para outros produtos da Loft além da fiança.
4. **Testar de verdade**: escolher dois municípios por cluster, rodar a mesma campanha e medir
   custo por lead qualificado. É o que valida se o cluster prediz desempenho de mídia.
5. **Cobrir a intenção de busca** por município via Google Ads Keyword Planner, que tem
   granularidade melhor que o Trends.
6. **Repetir de forma mensal** com os mesmos scripts, acompanhando a migração de municípios
   entre clusters como sinal antecedente de mercado em formação.

## 11. Como reproduzir

```bash
make poc
```

Roda tudo do zero: cria o ambiente, coleta as fontes, gera as 34 tabelas em
`reports/tables`, as figuras em `reports/figures` e este relatório. Exige um projeto do Google
Cloud configurado em `.env` para as consultas ao BigQuery da Base dos Dados.
