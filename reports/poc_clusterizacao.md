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
| Banda larga fixa / 100 hab.                      | Anatel - densidade de banda larga fixa por município (Base dos Dados)                   | 2025-09           | 2026-09-21    | True               |
| Famílias no CadÚnico / 100 domicílios            | Ministério do Desenvolvimento e Assistência Social - Cadastro Único (API MISocial/SAGI) | 2026-09           | 2026-09-21    | True               |
| Crédito per capita (R$)                          | Banco Central - ESTBAN, verbete 160 operações de crédito (Base dos Dados)               | 2025-09           | 2026-09-21    | True               |
| Imobiliárias e corretoras / 10 mil hab.          | Receita Federal - CNPJ, CNAE 6821801 (Base dos Dados)                                   | 2026-01-11        | 2026-09-21    | True               |
| Imobiliárias novas em 12 meses (%)               | Receita Federal - CNPJ, CNAE 6821 e 6822 (Base dos Dados)                               | 2026-01-11        | 2026-09-21    | True               |
| Internet móvel 4G/5G de pessoa física / 100 hab. | Anatel - acessos de telefonia móvel por município e tecnologia (dados abertos)          | 2026-07           | 2026-09-21    | True               |
| Pix de pessoa física por habitante               | Banco Central - Transações Pix por Município (API OData)                                | 2026-08           | 2026-09-21    | True               |
| Salário mediano de admissão (R$)                 | Novo CAGED - microdados de movimentação (Base dos Dados)                                | 2026-01           | 2026-09-21    | True               |
| Saldo de emprego / admissões em 12 meses (%)     | Novo CAGED - microdados de movimentação (Base dos Dados)                                | 2026-01           | 2026-09-21    | True               |
| Veículos por habitante                           | Senatran - frota de veículos por município e tipo (Base dos Dados)                      | 2026-07           | 2026-09-21    | True               |
| Domicílios alugados na UF (%)                    | IBGE - PNAD Contínua anual, condição de ocupação do domicílio (tabela SIDRA 6821)       | 2025              | 2026-09-21    | False              |
| Aluguel médio FipeZap (R$/m²)                    | FIPE/ZAP - índice FipeZap, séries históricas de locação residencial                     | 2026-08           | 2026-09-21    | False              |
| Inadimplência de pessoa física na UF (%)         | Banco Central - SCR por sub-região, cliente pessoa física (API OData)                   | 2026-08           | 2026-09-21    | False              |
| População estimada (universo da análise)         | IBGE - Estimativas da população (tabela SIDRA 6579)                                     | 2026-07-01        | 2026-09-21    | False              |
| Busca por fiança no Google, por UF (índice)      | Google Trends - termos ['aluguel sem fiador', 'fiança aluguel'] (pytrends)              | 2026-09           | 2026-09-21    | False              |

Regra do projeto cumprida: **nenhuma variável do modelo usa dado anterior a 2025**, e não há
uso do Censo 2022. O Índice Brasileiro de Conectividade da Anatel foi **descartado** por ter
2024 como ano mais recente; no lugar dele entraram os acessos de telefonia móvel dos dados
abertos da Anatel, com referência de 2026-07.

### 2.2 Decisões de tratamento que mudaram o resultado

| Decisão | Motivo |
| --- | --- |
| Pix: descartar o mês em andamento | Setembro de 2026 aparecia com R$ 784 bi contra cerca de R$ 1.100 bi dos meses fechados. Usamos os 12 meses completos. |
| Salário de admissão: usar a mediana, não a média | Em Belo Jardim (PE) a média era R$ 3.634 e a mediana R$ 1.612: poucos salários altos distorciam a comparação entre praças. |
| Internet móvel: usar só linhas de pessoa física | Com PJ incluído, Jaboticabal (SP) marcava 881 acessos por 100 habitantes (linhas de máquina e corporativas). Só com PF a assimetria caiu de 8,13 para -0,58. |
| Veículos: usar automóveis, não a frota toda | No Brasil a moto cresce onde a renda cai, então a frota total misturaria dois sinais opostos de patrimônio. |
| Crédito: winsorizar as caudas em 1% | O ESTBAN registra a carteira onde o banco está sediado: Osasco (SP) aparecia com R$ 1 milhão de crédito por habitante, que é a carteira nacional do banco ali sediado. |
| Google Trends: virou descritora | Mesmo pedindo resolução de cidade, a API devolve unidade da federação. A cobertura municipal foi de 0,3%, contra o mínimo de 80% combinado. |
| CadÚnico: denominador estimado | A competência disponível não preenche a contagem de pessoas, então usamos famílias sobre domicílios estimados (2.8 moradores por domicílio, PNAD Contínua). Sendo constante nacional, não altera a posição relativa dos municípios. |

### 2.3 Qualidade da base

Cobertura final: **zero valores faltantes** nas 11 variáveis candidatas,
nos 687 municípios. Conferência de volume contra a realidade, que é o teste que pega
erro de extração:

| Base | Total nacional obtido | Confere com a realidade |
| --- | --- | --- |
| ESTBAN, operações de crédito | R$ 6,6 trilhões | Sim, ordem do estoque de crédito do país |
| Senatran, automóveis | 65,6 milhões | Sim |
| Anatel, acessos móveis | 279,2 milhões, sendo 246,2 milhões em 4G/5G | Sim |
| CNPJ, imobiliárias e administradoras ativas | 144.872 estabelecimentos | Sim |
| Novo CAGED, admissões em 12 meses | 26,3 milhões, saldo de +1,2 milhão | Sim |
| CadÚnico, famílias cadastradas | 43,4 milhões | Sim |

Vinte municípios do universo têm **zero** estabelecimento imobiliário formal ativo, treze no
Norte e sete no Nordeste. Não é dado faltante: é a ausência real de mercado formal de locação,
e o modelo trata isso como informação.

## 3. Método

Pipeline por grupo de variáveis: **log nas variáveis de cauda longa → padronização →
modelo**, com winsorização de 1% nas duas caudas antes do log. Semente fixa em
42.

Variáveis com log nesta execução: Administradoras de imóveis / 10 mil hab..

### 3.1 Corte por correlação

Limiar de 0.80 em módulo na correlação de Spearman. Em cada par acima do
limiar fica a variável que o desenho da POC usa em mais grupos, porque é a que carrega o
sentido de negócio; empatado nisso, fica a de menor VIF.

| rotulo_descartada                       | rotulo_mantida                           |   correlacao_spearman | motivo                                                                        |
|:----------------------------------------|:-----------------------------------------|----------------------:|:------------------------------------------------------------------------------|
| Imobiliárias e corretoras / 10 mil hab. | Administradoras de imóveis / 10 mil hab. |                 0.824 | correlação de 0.82 acima do limiar de 0.80; usada em 3 dos 4 grupos, contra 1 |
| Veículos por habitante                  | Famílias no CadÚnico / 100 domicílios    |                 0.81  | correlação de 0.81 acima do limiar de 0.80; usada em 3 dos 4 grupos, contra 1 |

Todos os VIF ficaram abaixo de 5, então não há multicolinearidade grave entre as
sobreviventes.

### 3.2 Grupos comparados

| grupo   | nome                        |   n_variaveis | variaveis                                                                                                                                                                                                                              |   k_do_cotovelo |
|:--------|:----------------------------|--------------:|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------:|
| A       | Mercado imobiliário         |             3 | Administradoras de imóveis / 10 mil hab., Imobiliárias novas em 12 meses (%), Saldo de emprego / admissões em 12 meses (%)                                                                                                             |               4 |
| B       | Capacidade de pagamento     |             4 | Pix de pessoa física por habitante, Salário mediano de admissão (R$), Famílias no CadÚnico / 100 domicílios, Crédito per capita (R$)                                                                                                   |               4 |
| C       | Mercado + renda             |             6 | Administradoras de imóveis / 10 mil hab., Imobiliárias novas em 12 meses (%), Pix de pessoa física por habitante, Salário mediano de admissão (R$), Famílias no CadÚnico / 100 domicílios, Crédito per capita (R$)                     |               5 |
| D       | Mercado + renda + marketing |             6 | Administradoras de imóveis / 10 mil hab., Imobiliárias novas em 12 meses (%), Pix de pessoa física por habitante, Famílias no CadÚnico / 100 domicílios, Internet móvel 4G/5G de pessoa física / 100 hab., Banda larga fixa / 100 hab. |               5 |

Três modelos por grupo: KMeans, Aglomerativo com ligação de Ward e Mistura Gaussiana, com k de
2 a 10.

## 4. Escolha de k, e um achado desconfortável

A silhueta é máxima em **k = 2** em praticamente todas as combinações, e cai de forma
monotônica a partir daí. Isso não é defeito de implementação: significa que o Brasil municipal,
nessas variáveis, é um **contínuo socioeconômico**, não um conjunto de grupos bem separados.

Aceitar k = 2 seria entregar à Loft uma divisão entre praça rica e praça pobre, que não orienta
decisão de mídia. Por isso o k foi escolhido pelo **cotovelo da inércia**, e a qualidade do
resultado foi julgada pela comparação com os baselines, que é o teste que importa.

k do cotovelo por grupo: A = 4, B = 4, C = 5, D = 5.

Configuração escolhida: **grupo D (Mercado + renda + marketing), modelo
KMeans, k = 5**. O critério está detalhado
logo abaixo: entre os grupos que respondem à pergunta de negócio e têm todos os clusters acima
de 20 municípios, vale a maior silhueta; quando a diferença de silhueta é menor que 0,02, o
desempate é a estabilidade no bootstrap.

| grupo   | nome_grupo                  | nome_modelo         |   k |   silhueta |   davies_bouldin |   calinski_harabasz |   menor_cluster |
|:--------|:----------------------------|:--------------------|----:|-----------:|-----------------:|--------------------:|----------------:|
| B       | Capacidade de pagamento     | KMeans              |   4 |   0.325386 |          1.04193 |             474.627 |              79 |
| B       | Capacidade de pagamento     | Aglomerativo (Ward) |   4 |   0.322432 |          1.09028 |             425.223 |              49 |
| A       | Mercado imobiliário         | KMeans              |   4 |   0.304609 |          1.05968 |             311.734 |              86 |
| B       | Capacidade de pagamento     | Mistura Gaussiana   |   4 |   0.256395 |          1.27452 |             296.247 |              49 |
| A       | Mercado imobiliário         | Aglomerativo (Ward) |   4 |   0.25341  |          1.21873 |             238.371 |              40 |
| C       | Mercado + renda             | KMeans              |   5 |   0.243999 |          1.30668 |             273.625 |              97 |
| D       | Mercado + renda + marketing | KMeans              |   5 |   0.236293 |          1.32513 |             283.778 |              73 |
| A       | Mercado imobiliário         | Mistura Gaussiana   |   4 |   0.231248 |          1.46331 |             200.07  |              68 |
| C       | Mercado + renda             | Aglomerativo (Ward) |   5 |   0.222841 |          1.37759 |             234.941 |              36 |
| C       | Mercado + renda             | Mistura Gaussiana   |   5 |   0.196851 |          1.49698 |             198.25  |              70 |
| D       | Mercado + renda + marketing | Aglomerativo (Ward) |   5 |   0.177003 |          1.42773 |             226.545 |              43 |
| D       | Mercado + renda + marketing | Mistura Gaussiana   |   5 |   0.167716 |          1.76591 |             186.56  |              94 |

Sobre a hipótese inicial de que o grupo D separaria melhor: na silhueta pura, quem ganha é o grupo B (Capacidade de pagamento), com 0.325. Isso **não** significa que ele seja o melhor modelo. A silhueta premia espaços com menos variáveis e mais redundantes, porque ali é mais fácil achar corte limpo; e os grupos A e B, sozinhos, não respondem à pergunta do projeto: um só tem mercado e o outro só tem renda, e ninguém decide onde vender fiança olhando apenas um dos dois lados.

Por isso a escolha final ficou restrita aos grupos que têm ao menos uma variável de mercado imobiliário **e** uma de capacidade de pagamento, ou seja C e D. Entre eles:

| grupo   | nome_grupo                  | nome_modelo   |   k |   silhueta |   estabilidade_bootstrap |
|:--------|:----------------------------|:--------------|----:|-----------:|-------------------------:|
| D       | Mercado + renda + marketing | KMeans        |   5 |   0.236293 |                   0.937  |
| C       | Mercado + renda             | KMeans        |   5 |   0.243999 |                   0.7583 |

C tem silhueta um pouco maior (0.244 contra 0.236), diferença de menos de 0,01 que está dentro do ruído. Mas os clusters de C **não se reproduzem**: no bootstrap o Rand ajustado de C é 0.758 contra 0.937 de D. Para uma decisão de mídia que vai ser repetida mês a mês, estabilidade vale mais que um terceiro decimal de silhueta.

**Veredito: a hipótese de que o grupo D é o melhor se sustenta**, não porque D separa mais, e sim porque D separa de forma reprodutível. Acrescentar alcance digital não aumenta a separação — o alcance de internet móvel é a variável menos dispersa de todas, com coeficiente de variação de 0,17, já que praticamente todo município de 50 mil habitantes ou mais tem cobertura — mas **estabiliza** a solução e traz para o modelo a dimensão em que a decisão de mídia é executada.

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

- **Bootstrap** (99 comparações, reamostras de 80% dos municípios):
  Rand ajustado médio de **0.923**
  (desvio 0.075, faixa de
  0.749 a 0.991).
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

Roda tudo do zero: cria o ambiente, coleta as fontes, gera as 29 tabelas em
`reports/tables`, as figuras em `reports/figures` e este relatório. Exige um projeto do Google
Cloud configurado em `.env` para as consultas ao BigQuery da Base dos Dados.
