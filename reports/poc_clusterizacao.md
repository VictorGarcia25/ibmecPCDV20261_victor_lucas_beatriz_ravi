# POC não supervisionada: tipos de praça para o produto de fiança da Loft

Autoria: Beatriz Babinski · Projeto em Ciência de Dados V, IBMEC · gerado em 21/09/2026

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

| rotulo                                           | fonte                                                                                   | data_referencia   | data_coleta   | entra_no_cluster   |
|:-------------------------------------------------|:----------------------------------------------------------------------------------------|:------------------|:--------------|:-------------------|
| Administradoras de imóveis / 10 mil hab.         | Receita Federal - CNPJ, CNAE 6822600 (Base dos Dados)                                   | 2026-01-11        | 2026-09-21    | True               |
| Crédito sobre poupança (alavancagem)             | Banco Central - ESTBAN, crédito sobre poupança e depósito a prazo (Base dos Dados)      | 2025-09           | 2026-09-21    | True               |
| Banda larga fixa / 100 hab.                      | Anatel - densidade de banda larga fixa por município (Base dos Dados)                   | 2025-09           | 2026-09-21    | True               |
| Famílias no CadÚnico / 100 domicílios            | Ministério do Desenvolvimento e Assistência Social - Cadastro Único (API MISocial/SAGI) | 2026-09           | 2026-09-21    | True               |
| Corretores de seguros / 10 mil hab.              | Receita Federal - CNPJ, CNAE 6622300 (Base dos Dados)                                   | 2026-01-11        | 2026-09-21    | True               |
| Crédito per capita (R$)                          | Banco Central - ESTBAN, verbete 160 operações de crédito (Base dos Dados)               | 2025-09           | 2026-09-21    | True               |
| Crescimento da população em 1 ano (%)            | IBGE - Estimativas da população, dois anos consecutivos (tabela SIDRA 6579)             | 2026-07-01        | 2026-09-21    | True               |
| Imobiliárias e corretoras / 10 mil hab.          | Receita Federal - CNPJ, CNAE 6821801 (Base dos Dados)                                   | 2026-01-11        | 2026-09-21    | True               |
| Imobiliárias novas em 12 meses (%)               | Receita Federal - CNPJ, CNAE 6821 e 6822 (Base dos Dados)                               | 2026-01-11        | 2026-09-21    | True               |
| Internet móvel 4G/5G de pessoa física / 100 hab. | Anatel - acessos de telefonia móvel por município e tecnologia (dados abertos)          | 2026-07           | 2026-09-21    | True               |
| Admissões de 18 a 30 anos (%)                    | Novo CAGED - microdados de movimentação (Base dos Dados)                                | 2026-01           | 2026-09-21    | True               |
| Pix de pessoa física por habitante               | Banco Central - Transações Pix por Município (API OData)                                | 2026-08           | 2026-09-21    | True               |
| Poupança e depósito a prazo per capita (R$)      | Banco Central - ESTBAN, verbetes 420 e 432 poupança e depósito a prazo (Base dos Dados) | 2025-09           | 2026-09-21    | True               |
| Salário mediano de admissão (R$)                 | Novo CAGED - microdados de movimentação (Base dos Dados)                                | 2026-01           | 2026-09-21    | True               |
| Saldo de emprego / admissões em 12 meses (%)     | Novo CAGED - microdados de movimentação (Base dos Dados)                                | 2026-01           | 2026-09-21    | True               |
| Veículos por habitante                           | Senatran - frota de veículos por município e tipo (Base dos Dados)                      | 2026-07           | 2026-09-21    | True               |
| Domicílios alugados na UF (%)                    | IBGE - PNAD Contínua anual, condição de ocupação do domicílio (tabela SIDRA 6821)       | 2025              | 2026-09-21    | False              |
| Aluguel médio FipeZap (R$/m²)                    | FIPE/ZAP - índice FipeZap, séries históricas de locação residencial                     | 2026-08           | 2026-09-21    | False              |
| Inadimplência de pessoa física na UF (%)         | Banco Central - SCR por sub-região, cliente pessoa física (API OData)                   | 2026-08           | 2026-09-21    | False              |
| População estimada (universo da análise)         | IBGE - Estimativas da população (tabela SIDRA 6579)                                     | 2026-07-01        | 2026-09-21    | False              |
| poupanca_per_capita                              | Banco Central - ESTBAN, verbete 420 depósitos de poupança (Base dos Dados)              | 2025-09           | 2026-09-21    | False              |
| Busca por fiança no Google, por UF (índice)      | Google Trends - termos ['aluguel sem fiador', 'fiança aluguel'] (pytrends)              | 2026-09           | 2026-09-21    | False              |

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

| base                                        | total_no_brasil          | ordem_de_grandeza_esperada                                   | total_nos_municipios_analisados   | parcela_no_universo   |
|:--------------------------------------------|:-------------------------|:-------------------------------------------------------------|:----------------------------------|:----------------------|
| ESTBAN, operações de crédito                | R$ 6.6 trilhões          | estoque de crédito do país: casa dos trilhões de reais       | R$ 6.1 trilhões                   | 93%                   |
| Senatran, automóveis                        | 65.6 milhões             | frota de automóveis do país: algumas dezenas de milhões      | 51.1 milhões                      | 78%                   |
| Anatel, acessos móveis 4G e 5G              | 246.2 milhões            | acessos móveis do país: algumas centenas de milhões          | 193.4 milhões                     | 79%                   |
| CNPJ, imobiliárias e administradoras ativas | 144.872 estabelecimentos | empresas do setor imobiliário: casa das centenas de milhares | 131.316 estabelecimentos          | 91%                   |
| Novo CAGED, admissões em 12 meses           | 26.3 milhões             | contratações formais no país em um ano: dezenas de milhões   | 21.8 milhões                      | 83%                   |
| CadÚnico, famílias cadastradas              | 43.4 milhões             | famílias no Cadastro Único: dezenas de milhões               | 26.9 milhões                      | 62%                   |

O total no Brasil vem do arquivo bruto, com todos os municípios, e é ele que se confronta com a
realidade conhecida. A última coluna mostra quanto disso está nos municípios analisados: se
passasse de 100% haveria linha duplicada em algum merge. É o teste que pega erro de extração
calado, do tipo unidade trocada ou junção que multiplica registros.

20 municípios do universo têm **zero** estabelecimento imobiliário
formal ativo (13 no Norte, 7 no Nordeste). Não é dado faltante: é a ausência real de mercado
formal de locação, e o modelo trata isso como informação. Todos eles caíram no mesmo cluster,
o de Praça sem mercado formal, o que é um sinal de que o agrupamento leu esse fato.

## 3. Método

Pipeline por grupo de variáveis: **log nas variáveis de cauda longa → padronização →
modelo**, com winsorização de 1% nas duas caudas antes do log. Semente fixa em
42.

Variáveis com log nesta execução: Administradoras de imóveis / 10 mil hab..

### 3.1 Corte por correlação

Limiar de 0.80 em módulo na correlação de Spearman. Em cada par acima do
limiar fica a variável que o desenho da POC usa em mais grupos, porque é a que carrega o
sentido de negócio; empatado nisso, fica a de menor VIF.

| rotulo_descartada                       | rotulo_mantida                              |   correlacao_spearman | motivo                                                                                                                                                  |
|:----------------------------------------|:--------------------------------------------|----------------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------|
| Imobiliárias e corretoras / 10 mil hab. | Administradoras de imóveis / 10 mil hab.    |                 0.824 | correlação de 0.82 acima do limiar de 0.80; usada em 4 dos 4 grupos, contra 1                                                                           |
| Veículos por habitante                  | Famílias no CadÚnico / 100 domicílios       |                 0.81  | saiu numa cadeia de variáveis correlacionadas entre si; a sobrevivente que a representa é Famílias no CadÚnico / 100 domicílios, com correlação de 0.81 |
| Corretores de seguros / 10 mil hab.     | Poupança e depósito a prazo per capita (R$) |                 0.802 | correlação de 0.80 acima do limiar de 0.80; mesmo peso no desenho, ficou a de menor VIF                                                                 |

O maior VIF é de 6.56, em Veículos por habitante, bem abaixo do limiar usual de 10. Não há multicolinearidade grave entre as variáveis que sobraram.

### 3.2 Grupos comparados

| grupo   | nome                                     |   n_variaveis | variaveis                                                                                                                                                                                                                              |   k_do_cotovelo |
|:--------|:-----------------------------------------|--------------:|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------:|
| A       | Mercado imobiliário                      |             3 | Administradoras de imóveis / 10 mil hab., Imobiliárias novas em 12 meses (%), Saldo de emprego / admissões em 12 meses (%)                                                                                                             |               4 |
| B       | Capacidade de pagamento                  |             4 | Pix de pessoa física por habitante, Salário mediano de admissão (R$), Famílias no CadÚnico / 100 domicílios, Crédito per capita (R$)                                                                                                   |               4 |
| C       | Mercado + renda                          |             6 | Administradoras de imóveis / 10 mil hab., Imobiliárias novas em 12 meses (%), Pix de pessoa física por habitante, Salário mediano de admissão (R$), Famílias no CadÚnico / 100 domicílios, Crédito per capita (R$)                     |               5 |
| D       | Mercado + renda + marketing              |             6 | Administradoras de imóveis / 10 mil hab., Imobiliárias novas em 12 meses (%), Pix de pessoa física por habitante, Famílias no CadÚnico / 100 domicílios, Internet móvel 4G/5G de pessoa física / 100 hab., Banda larga fixa / 100 hab. |               5 |
| E       | Mercado + risco + concorrência + demanda |             6 | Administradoras de imóveis / 10 mil hab., Imobiliárias novas em 12 meses (%), Crédito sobre poupança (alavancagem), Poupança e depósito a prazo per capita (R$), Crescimento da população em 1 ano (%), Admissões de 18 a 30 anos (%)  |               5 |

Três modelos por grupo: KMeans, Aglomerativo com ligação de Ward e Mistura Gaussiana, com k de
2 a 10.

## 4. Escolha de k, e um achado desconfortável

A silhueta é máxima em **k = 2** em praticamente todas as combinações, e cai de forma
monotônica a partir daí. Isso não é defeito de implementação: significa que o Brasil municipal,
nessas variáveis, é um **contínuo socioeconômico**, não um conjunto de grupos bem separados.

Aceitar k = 2 seria entregar à Loft uma divisão entre praça rica e praça pobre, que não orienta
decisão de mídia. Por isso o k foi escolhido pelo **cotovelo da inércia**, e a qualidade do
resultado foi julgada pela comparação com os baselines, que é o teste que importa.

k do cotovelo por grupo: A = 4, B = 4, C = 5, D = 5, E = 5.

Configuração escolhida: **grupo D (Mercado + renda + marketing), modelo
KMeans, k = 5**. O critério está detalhado
logo abaixo: entre os grupos que respondem à pergunta de negócio e têm todos os clusters acima
de 20 municípios, vale a maior silhueta; quando a diferença de silhueta é menor que 0,02, o
desempate é a estabilidade no bootstrap.

| grupo   | nome_grupo                               | nome_modelo         |   k |   silhueta |   davies_bouldin |   calinski_harabasz |   menor_cluster |
|:--------|:-----------------------------------------|:--------------------|----:|-----------:|-----------------:|--------------------:|----------------:|
| B       | Capacidade de pagamento                  | KMeans              |   4 |   0.325403 |          1.04193 |             474.709 |              79 |
| B       | Capacidade de pagamento                  | Aglomerativo (Ward) |   4 |   0.318937 |          1.0902  |             423.148 |              49 |
| A       | Mercado imobiliário                      | KMeans              |   4 |   0.304609 |          1.05968 |             311.734 |              86 |
| B       | Capacidade de pagamento                  | Mistura Gaussiana   |   4 |   0.25638  |          1.27456 |             296.232 |              49 |
| A       | Mercado imobiliário                      | Aglomerativo (Ward) |   4 |   0.25341  |          1.21873 |             238.371 |              40 |
| C       | Mercado + renda                          | KMeans              |   5 |   0.244021 |          1.30664 |             273.658 |              97 |
| D       | Mercado + renda + marketing              | KMeans              |   5 |   0.236293 |          1.32513 |             283.778 |              73 |
| A       | Mercado imobiliário                      | Mistura Gaussiana   |   4 |   0.231248 |          1.46331 |             200.07  |              68 |
| C       | Mercado + renda                          | Aglomerativo (Ward) |   5 |   0.222848 |          1.37757 |             234.966 |              36 |
| C       | Mercado + renda                          | Mistura Gaussiana   |   5 |   0.197982 |          1.48267 |             199.365 |              70 |
| E       | Mercado + risco + concorrência + demanda | KMeans              |   5 |   0.184086 |          1.4849  |             174.632 |              62 |
| D       | Mercado + renda + marketing              | Aglomerativo (Ward) |   5 |   0.177003 |          1.42773 |             226.545 |              43 |
| D       | Mercado + renda + marketing              | Mistura Gaussiana   |   5 |   0.167716 |          1.76591 |             186.56  |              94 |
| E       | Mercado + risco + concorrência + demanda | Aglomerativo (Ward) |   5 |   0.149123 |          1.60976 |             133.982 |              23 |
| E       | Mercado + risco + concorrência + demanda | Mistura Gaussiana   |   5 |   0.102363 |          1.93732 |             115.497 |              81 |

Sobre a hipótese inicial de que o grupo D separaria melhor: na silhueta pura, quem ganha é o grupo B (Capacidade de pagamento), com 0.325. Isso **não** significa que ele seja o melhor modelo. A silhueta premia espaços com menos variáveis e mais redundantes, porque ali é mais fácil achar corte limpo; e os grupos A e B, sozinhos, não respondem à pergunta do projeto: um só tem mercado e o outro só tem renda, e ninguém decide onde vender fiança olhando apenas um dos dois lados.

Por isso a escolha final ficou restrita aos grupos que têm ao menos uma variável de mercado imobiliário **e** uma de capacidade de pagamento, ou seja C e D. Entre eles:

| grupo   | nome_grupo                  | nome_modelo   |   k |   silhueta |   estabilidade_bootstrap |
|:--------|:----------------------------|:--------------|----:|-----------:|-------------------------:|
| D       | Mercado + renda + marketing | KMeans        |   5 |   0.236293 |                   0.8375 |
| C       | Mercado + renda             | KMeans        |   5 |   0.244021 |                   0.7024 |

C tem silhueta um pouco maior (0.244 contra 0.236). Antes de decidir por isso, essa vantagem foi testada: reamostrando os municípios 200 vezes, refazendo o preparo dentro de cada subamostra e recalculando a silhueta das duas configurações sobre os mesmos municípios.

| configuracao_a   | configuracao_b   |   silhueta_media_a |   silhueta_media_b |   diferenca_media |   intervalo_95_inferior |   intervalo_95_superior |   vezes_que_a_venceu_pct | diferenca_significativa   |   n_reamostragens |
|:-----------------|:-----------------|-------------------:|-------------------:|------------------:|------------------------:|------------------------:|-------------------------:|:--------------------------|------------------:|
| D                | C                |             0.2423 |             0.2561 |           -0.0139 |                 -0.0323 |                  -0.001 |                      1.5 | True                      |               200 |

O intervalo de 95% da diferença vai de -0.0323 a -0.0010 e **não inclui o zero**: a vantagem de C em separação é real, não é ruído. Mas é preciso olhar o tamanho dela.

A vantagem de C em silhueta é de 0.008. Para comparar, a vantagem do próprio agrupamento sobre o baseline de geografia é de cerca de 0.237, ou seja a diferença entre C e D é uma fração pequena do que está em jogo.

Já a diferença de estabilidade vai na direção oposta e é maior: sob subamostragem o Rand ajustado de C é 0.702 contra 0.838 de D, uma distância de 0.135. Os clusters de C mudam de composição quando se troca um quinto dos municípios; os de D não.

O critério aplicado foi esse: trocar 0.008 de separação por 0.135 de reprodutibilidade, porque a decisão de mídia vai ser refeita mês a mês e um agrupamento que se reorganiza a cada rodada não sustenta plano de verba.

**Veredito: a hipótese de que o grupo D é o melhor se sustenta**, não porque D separa mais, e sim porque D separa de forma reprodutível. Acrescentar alcance digital não aumenta a separação, e a razão aparece na descritiva: a variável de menor dispersão entre as do grupo escolhido é **Internet móvel 4G/5G de pessoa física / 100 hab.**, com coeficiente de variação de 0,17. Ou seja, o alcance digital quase não distingue uma praça da outra, porque praticamente todo município de 50 mil habitantes ou mais já tem cobertura. O que essas variáveis fazem é **estabilizar** a solução e trazer para o modelo a dimensão em que a decisão de mídia é executada.

## 5. Baselines: o cluster ganha de geografia e de porte?

Este é o critério de aceite do projeto. Todos os agrupamentos são avaliados **no mesmo espaço
de variáveis**, então a silhueta é comparável.

| agrupamento                               |   n_grupos |   silhueta |   rand_ajustado_vs_cluster |
|:------------------------------------------|-----------:|-----------:|---------------------------:|
| Clusters da POC                           |          5 |     0.2363 |                     1      |
| Baseline: 5 regiões do IBGE               |          5 |    -0.001  |                     0.185  |
| Baseline: faixas de porte populacional    |          5 |    -0.0978 |                     0.0322 |
| Baseline: sorteio aleatório (média de 30) |          5 |    -0.0314 |                    -0.0001 |

Leitura:

- O agrupamento da POC tem silhueta de **0.236**, contra
  **-0.001** das 5 regiões do IBGE e
  **-0.098** das faixas de porte populacional. O baseline aleatório
  fica em -0.031. **O cluster bate a geografia e o porte.**
- O Rand ajustado contra o porte é de apenas **0.032**:
  o modelo **não redescobriu o tamanho da cidade**, que era o risco principal desta análise.
- Contra a região o Rand ajustado é **0.185**: existe
  alguma relação com geografia, o que é esperado num país desigual, mas longe de ser a mesma
  coisa. Se fosse, bastaria comprar mídia por região.

Comparação dos quatro grupos contra os baselines: tabela `10_baselines_por_grupo.csv`.

## 6. Robustez

- **Reamostragem** (99 comparações, subamostras sem reposição de
  80% dos municípios): Rand ajustado médio de
  **0.847** (desvio 0.107,
  faixa de 0.668 a 0.984).
  A reamostragem é sem reposição de propósito: com reposição, os municípios duplicados ficam a
  distância zero um do outro e inflam a concordância entre rodadas.
- **Sementes**: 10 sementes diferentes, Rand ajustado médio contra a solução de
  referência de **0.991** (mínimo
  0.984).
- **Ablação**: remoção de uma variável por vez.

| rotulo                                           |   silhueta_sem_ela |   silhueta_completa |   variacao |   rand_ajustado_vs_completo |
|:-------------------------------------------------|-------------------:|--------------------:|-----------:|----------------------------:|
| Famílias no CadÚnico / 100 domicílios            |             0.2312 |              0.2363 |    -0.0051 |                      0.641  |
| Internet móvel 4G/5G de pessoa física / 100 hab. |             0.2382 |              0.2363 |     0.0019 |                      0.7111 |
| Imobiliárias novas em 12 meses (%)               |             0.2499 |              0.2363 |     0.0136 |                      0.5946 |
| Banda larga fixa / 100 hab.                      |             0.25   |              0.2363 |     0.0137 |                      0.7706 |
| Pix de pessoa física por habitante               |             0.258  |              0.2363 |     0.0217 |                      0.7184 |
| Administradoras de imóveis / 10 mil hab.         |             0.2636 |              0.2363 |     0.0273 |                      0.6396 |

A variável mais crítica é **Famílias no CadÚnico / 100 domicílios**: sem ela a silhueta varia -0.005. A menos crítica é **Administradoras de imóveis / 10 mil hab.** (+0.027). O Rand ajustado contra a solução completa mostra quanto a composição dos grupos muda ao remover cada variável.

### 6.1 A taxa de empresas novas não é artefato de base pequena

A variável de imobiliárias abertas em 12 meses é uma proporção, e proporção com denominador
pequeno engana: num município com 9 imobiliárias, três aberturas já viram 33%. Como é essa a
variável que mais define o cluster de **Praça em formação**, ela foi testada exigindo um número
mínimo de empresas no município.

|   base_minima_de_empresas |   municipios_no_cluster |   mediana_no_cluster |   mediana_no_resto |   p_valor | continua_maior   |
|--------------------------:|------------------------:|---------------------:|-------------------:|----------:|:-----------------|
|                         1 |                      73 |                 27.3 |               12.5 |   1e-37   | True             |
|                        10 |                      36 |                 24.3 |               12.9 |   5.1e-19 | True             |
|                        20 |                      15 |                 21.1 |               13.1 |   1.1e-08 | True             |
|                        50 |                       2 |                 23.6 |               13.3 |   0.011   | True             |

O cluster continua com taxa de abertura muito acima do resto mesmo quando se exige base maior,
e a correlação de Spearman entre a taxa e o número de empresas do município é de apenas
0,178, ou seja **a taxa alta não vem de denominador pequeno**. O achado
sobrevive ao teste. Ainda assim a variável é ruidosa em município de base curta, e é por isso
que ela entra winsorizada.

### 6.2 O cluster serve como variável de um modelo futuro?

Separação interna e estabilidade dizem que o agrupamento é consistente, mas não dizem se ele é
**útil como entrada de modelo**. O teste para isso é outro, e a pergunta certa não é se o
cluster substitui a geografia: é se ele **acrescenta** algo a ela.

Comparamos, em variáveis municipais que ficaram **fora** do modelo, o R² ajustado de
`região + porte` contra `região + porte + cluster`. O R² é ajustado para não premiar o simples
aumento de parâmetros.

| rotulo                                       |   r2_regiao_e_porte |   r2_com_o_cluster |   ganho | o_cluster_acrescenta   |
|:---------------------------------------------|--------------------:|-------------------:|--------:|:-----------------------|
| Corretores de seguros / 10 mil hab.          |              0.404  |             0.5517 |  0.1478 | True                   |
| Imobiliárias e corretoras / 10 mil hab.      |              0.143  |             0.2825 |  0.1395 | True                   |
| Veículos por habitante                       |              0.7353 |             0.8116 |  0.0763 | True                   |
| Motocicletas por habitante                   |              0.159  |             0.2239 |  0.0649 | True                   |
| Salário mediano de admissão (R$)             |              0.5579 |             0.6044 |  0.0465 | True                   |
| Crescimento da população em 1 ano (%)        |              0.2272 |             0.2737 |  0.0465 | True                   |
| Financiamento imobiliário per capita (R$)    |              0.1375 |             0.1641 |  0.0266 | True                   |
| Admissões de 18 a 30 anos (%)                |              0.39   |             0.4132 |  0.0232 | True                   |
| Saldo de emprego / admissões em 12 meses (%) |              0.1509 |             0.174  |  0.0231 | True                   |
| Domicílios alugados na UF (%)                |              0.5466 |             0.563  |  0.0164 | True                   |
| Poupança e depósito a prazo per capita (R$)  |              0.2926 |             0.3076 |  0.015  | True                   |
| Crédito sobre poupança (alavancagem)         |              0.1422 |             0.1504 |  0.0083 | True                   |
| Busca por fiança no Google, por UF (índice)  |              0.8189 |             0.8257 |  0.0068 | True                   |
| Crédito per capita (R$)                      |              0.0756 |             0.0819 |  0.0063 | True                   |
| Inadimplência de pessoa física na UF (%)     |              0.5167 |             0.522  |  0.0054 | True                   |

O cluster acrescenta informação em **15 de 15** variáveis retidas, com ganho médio de **+0.0435** no R² ajustado. Em nenhuma ele piora. **O rótulo do cluster é, portanto, uma variável válida para alimentar um modelo futuro**: ele carrega algo que região e porte, juntos, não carregam. O maior ganho está em Corretores de seguros / 10 mil hab., de 0.404 para 0.552.

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
|         0 | Praça em formação             |           73 |             10.6 |             4.9 |               80435 |
|         1 | Praça intermediária conectada |          219 |             31.9 |            19.2 |               98241 |
|         2 | Praça popular de grande porte |          167 |             24.3 |            23.7 |              119224 |
|         3 | Praça sem mercado formal      |           97 |             14.1 |             4.8 |               64350 |
|         4 | Praça madura de locação       |          131 |             19.1 |            47.5 |              221023 |

Assinatura de cada cluster, em desvios padrão em relação à média dos 687 municípios:

|   cluster | nome                          | marcas_do_cluster                                                                                                                                                     |
|----------:|:------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|         0 | Praça em formação             | Imobiliárias novas em 12 meses (%): +1.71 desvios; Internet móvel 4G/5G de pessoa física / 100 hab.: -0.95 desvios; Pix de pessoa física por habitante: -0.94 desvios |
|         1 | Praça intermediária conectada | Famílias no CadÚnico / 100 domicílios: -0.79 desvios; Banda larga fixa / 100 hab.: +0.53 desvios; Internet móvel 4G/5G de pessoa física / 100 hab.: +0.07 desvios     |
|         2 | Praça popular de grande porte | Famílias no CadÚnico / 100 domicílios: +0.54 desvios; Banda larga fixa / 100 hab.: -0.46 desvios; Internet móvel 4G/5G de pessoa física / 100 hab.: +0.35 desvios     |
|         3 | Praça sem mercado formal      | Internet móvel 4G/5G de pessoa física / 100 hab.: -1.43 desvios; Famílias no CadÚnico / 100 domicílios: +1.20 desvios; Banda larga fixa / 100 hab.: -1.20 desvios     |
|         4 | Praça madura de locação       | Administradoras de imóveis / 10 mil hab.: +1.39 desvios; Banda larga fixa / 100 hab.: +1.08 desvios; Pix de pessoa física por habitante: +1.07 desvios                |

Figuras: `07_perfil_clusters.png` (heatmap), `08_radar_clusters.png` (radar),
`09_mapa_clusters.png` (mapa do Brasil), `10_mapa_de_decisao.png`.

Os dez maiores municípios de cada cluster estão em `18_top_municipios.csv`.

## 8. Valor para a Loft

|   cluster | nome                          |   municipios |   populacao_pct | o_que_significa_para_a_fianca                                                                                                                  | acao_de_marketing_sugerida                                                                                                                |
|----------:|:------------------------------|-------------:|----------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------|
|         0 | Praça em formação             |           73 |             4.9 | Muita imobiliária abrindo agora: o mercado está se organizando e as empresas novas ainda não têm processo de garantia definido.                | Momento de entrada. Mídia de educação de produto para imobiliária nova, custo por lead ainda baixo.                                       |
|         1 | Praça intermediária conectada |          219 |            19.2 | Mercado e renda medianos, mas alcance digital alto: dá para testar barato com boa cobertura de audiência.                                      | Praça de teste A/B de criativo. Verba pequena e recorrente em Meta e TikTok para aprender antes de levar o aprendizado às praças maduras. |
|         2 | Praça popular de grande porte |          167 |            23.7 |                                                                                                                                                |                                                                                                                                           |
|         3 | Praça sem mercado formal      |           97 |             4.8 | Praticamente não existe administradora formal e a vulnerabilidade é alta: não há cliente B2B para vender e o risco de inadimplência é o maior. | Zero verba de mídia paga. Praça de exclusão no planejamento.                                                                              |
|         4 | Praça madura de locação       |          131 |            47.5 | Muitas administradoras e inquilino com capacidade de pagar: o risco da fiança é baixo e o cliente B2B já existe e já vende locação.            | Mídia de conversão para imobiliária (Meta e Google Search em segmentação B2B), com verba concentrada e meta de custo por lead.            |

## 9. Limitações

1. **Sem dado interno da Loft.** Não há receita, CAC, taxa de conversão nem sinistro de fiança
   por praça. O agrupamento descreve o mercado, não o desempenho da Loft nele. Só o dado
   interno transforma "praça promissora" em "praça rentável".
2. **Os grupos não são naturais.** A silhueta cai com k e o melhor valor puro é k = 2. Os
   clusters são um **corte útil de um contínuo**, não fronteiras que existem na natureza. A
   defesa deles é a comparação com os baselines, não a separação absoluta.
3. **Efeito de sede na fonte.** ESTBAN e telefonia móvel registram a operação onde a empresa
   está sediada. Tratamos com winsorização e com o filtro de pessoa física, mas o viés não
   desaparece: praças que sediam banco ou operadora continuam distorcidas.
4. **CNAE não é produto.** CNAE 6821 e 6822 não distinguem locação de venda nem contrato
   residencial de temporada. Por isso as praças de veraneio aparecem com densidade altíssima de
   imobiliária sem serem mercado de fiança.
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
10. **A escolha entre C e D é um julgamento, não um resultado automático.** C separa melhor por
    uma margem pequena mas estatisticamente real; D é muito mais estável. Trocamos separação por
    reprodutibilidade porque a decisão será repetida, e isso está registrado na seção 4 para
    quem quiser decidir diferente.

## 10. Próximos passos

1. **Cruzar com o dado interno da Loft**: receita e sinistro de fiança por município,
   transformando os clusters em faixas de retorno esperado por real investido.
2. **Separar locação de venda** nos estabelecimentos, usando CNAE secundária e razão social,
   para isolar a praça de temporada da praça de locação residencial.
3. **Testar de verdade**: escolher dois municípios por cluster, rodar a mesma campanha e medir
   custo por lead qualificado. É o que valida se o cluster prediz desempenho de mídia.
4. **Cobrir a intenção de busca** por município via Google Ads Keyword Planner, que tem
   granularidade melhor que o Trends.
5. **Repetir de forma mensal** com os mesmos scripts, acompanhando a migração de municípios
   entre clusters como sinal antecedente de mercado em formação.

## 11. Como reproduzir

```bash
make poc
```

Roda tudo do zero: cria o ambiente, coleta as fontes, gera as 33 tabelas em
`reports/tables`, as figuras em `reports/figures` e este relatório. Exige um projeto do Google
Cloud configurado em `.env` para as consultas ao BigQuery da Base dos Dados.
