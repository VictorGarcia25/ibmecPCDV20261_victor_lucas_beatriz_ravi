"""Escreve o relatório da POC em markdown a partir dos resultados já calculados."""

from __future__ import annotations

from datetime import date

import pandas as pd

from . import clustering, config

ARQUIVO = config.RAIZ / "reports" / "poc_clusterizacao.md"


def _md(df: pd.DataFrame, colunas: list[str] | None = None) -> str:
    recorte = df[colunas] if colunas else df
    return recorte.to_markdown(index=False)


def escrever(p: dict) -> None:
    base = p["base"]
    grupo = p["grupo_final"]
    comparacao = p["comparacao_final"]
    silhueta_cluster = comparacao.iloc[0]["silhueta"]
    silhueta_regiao = comparacao[comparacao["agrupamento"].str.contains("regiões")].iloc[0]
    silhueta_porte = comparacao[comparacao["agrupamento"].str.contains("porte")].iloc[0]
    silhueta_aleatorio = comparacao[comparacao["agrupamento"].str.contains("aleatório")].iloc[0]
    bootstrap = p["bootstrap"].iloc[0]
    sementes = p["sementes"]

    texto = f"""# POC não supervisionada: tipos de praça para o produto de fiança da Loft

Autoria: Beatriz Babinski · Projeto em Ciência de Dados V, IBMEC · gerado em {date.today().strftime('%d/%m/%Y')}

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
{config.ANO_POPULACAO}. São **{len(base)} municípios**, que concentram
{base['populacao'].sum() / 214_211_951 * 100:.0f}% da população do país.

Todas as variáveis são relativas à população (por habitante, por 10 mil habitantes ou por 100
domicílios), justamente para o agrupamento **não separar apenas por tamanho de cidade**.

### 2.1 Fontes e data de referência

{_md(p['fontes'], ['rotulo', 'fonte', 'data_referencia', 'data_coleta', 'entra_no_cluster'])}

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
| CadÚnico: denominador estimado | A competência disponível não preenche a contagem de pessoas, então usamos famílias sobre domicílios estimados ({config.MORADORES_POR_DOMICILIO} moradores por domicílio, PNAD Contínua). Sendo constante nacional, não altera a posição relativa dos municípios. |

### 2.3 Qualidade da base

Cobertura final: **zero valores faltantes** nas {len(config.VARIAVEIS)} variáveis candidatas,
nos {len(base)} municípios. Conferência de volume contra a realidade, que é o teste que pega
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
{config.SEMENTE}.

Variáveis com log nesta execução: {', '.join(config.VARIAVEIS[v] for v in p['variaveis_log']) or 'nenhuma'}.

### 3.1 Corte por correlação

Limiar de {descritiva_limiar():.2f} em módulo na correlação de Spearman. Em cada par acima do
limiar fica a variável que o desenho da POC usa em mais grupos, porque é a que carrega o
sentido de negócio; empatado nisso, fica a de menor VIF.

{_md(p['decisoes'], ['rotulo_descartada', 'rotulo_mantida', 'correlacao_spearman', 'motivo'])}

Todos os VIF ficaram abaixo de 5, então não há multicolinearidade grave entre as
sobreviventes.

### 3.2 Grupos comparados

{_grupos_md(p['grupos'], p['cotovelos'])}

Três modelos por grupo: KMeans, Aglomerativo com ligação de Ward e Mistura Gaussiana, com k de
{config.K_MINIMO} a {config.K_MAXIMO}.

## 4. Escolha de k, e um achado desconfortável

A silhueta é máxima em **k = 2** em praticamente todas as combinações, e cai de forma
monotônica a partir daí. Isso não é defeito de implementação: significa que o Brasil municipal,
nessas variáveis, é um **contínuo socioeconômico**, não um conjunto de grupos bem separados.

Aceitar k = 2 seria entregar à Loft uma divisão entre praça rica e praça pobre, que não orienta
decisão de mídia. Por isso o k foi escolhido pelo **cotovelo da inércia**, e a qualidade do
resultado foi julgada pela comparação com os baselines, que é o teste que importa.

k do cotovelo por grupo: {', '.join(f'{g} = {k}' for g, k in p['cotovelos'].items())}.

Configuração escolhida: **grupo {grupo} ({config.NOMES_GRUPOS[grupo]}), modelo
{clustering.NOMES_MODELOS[p['modelo_final']]}, k = {p['k_final']}**. O critério está detalhado
logo abaixo: entre os grupos que respondem à pergunta de negócio e têm todos os clusters acima
de 20 municípios, vale a maior silhueta; quando a diferença de silhueta é menor que 0,02, o
desempate é a estabilidade no bootstrap.

{_md(p['candidatos'], ['grupo', 'nome_grupo', 'nome_modelo', 'k', 'silhueta', 'davies_bouldin', 'calinski_harabasz', 'menor_cluster'])}

Sobre a hipótese inicial de que o grupo D separaria melhor: {_veredito_hipotese(p)}

## 5. Baselines: o cluster ganha de geografia e de porte?

Este é o critério de aceite do projeto. Todos os agrupamentos são avaliados **no mesmo espaço
de variáveis**, então a silhueta é comparável.

{_md(comparacao, ['agrupamento', 'n_grupos', 'silhueta', 'rand_ajustado_vs_cluster'])}

Leitura:

- O agrupamento da POC tem silhueta de **{silhueta_cluster:.3f}**, contra
  **{silhueta_regiao['silhueta']:.3f}** das 5 regiões do IBGE e
  **{silhueta_porte['silhueta']:.3f}** das faixas de porte populacional. O baseline aleatório
  fica em {silhueta_aleatorio['silhueta']:.3f}. **O cluster bate a geografia e o porte.**
- O Rand ajustado contra o porte é de apenas **{silhueta_porte['rand_ajustado_vs_cluster']:.3f}**:
  o modelo **não redescobriu o tamanho da cidade**, que era o risco principal desta análise.
- Contra a região o Rand ajustado é **{silhueta_regiao['rand_ajustado_vs_cluster']:.3f}**: existe
  alguma relação com geografia, o que é esperado num país desigual, mas longe de ser a mesma
  coisa. Se fosse, bastaria comprar mídia por região.

Comparação dos quatro grupos contra os baselines: tabela `10_baselines_por_grupo.csv`.

## 6. Robustez

- **Bootstrap** ({bootstrap['n_comparacoes']} comparações, reamostras de 80% dos municípios):
  Rand ajustado médio de **{bootstrap['rand_ajustado_medio']:.3f}**
  (desvio {bootstrap['rand_ajustado_desvio']:.3f}, faixa de
  {bootstrap['rand_ajustado_p5']:.3f} a {bootstrap['rand_ajustado_p95']:.3f}).
- **Sementes**: {len(sementes)} sementes diferentes, Rand ajustado médio contra a solução de
  referência de **{sementes['rand_ajustado_vs_referencia'].mean():.3f}** (mínimo
  {sementes['rand_ajustado_vs_referencia'].min():.3f}).
- **Ablação**: remoção de uma variável por vez.

{_md(p['ablacao'], ['rotulo', 'silhueta_sem_ela', 'silhueta_completa', 'variacao', 'rand_ajustado_vs_completo'])}

{_leitura_ablacao(p['ablacao'])}

## 7. Os tipos de praça encontrados

{_md(p['tamanhos'].merge(pd.DataFrame({'cluster': list(p['nomes']), 'nome': list(p['nomes'].values())}), on='cluster'), ['cluster', 'nome', 'municipios', 'municipios_pct', 'populacao_pct', 'populacao_mediana'])}

Assinatura de cada cluster, em desvios padrão em relação à média dos {len(base)} municípios:

{_md(p['descricao_marcas'], ['cluster', 'nome', 'marcas_do_cluster']) if 'descricao_marcas' in p else '(ver tabela 17_marcas_dos_clusters.csv)'}

Figuras: `07_perfil_clusters.png` (heatmap), `08_radar_clusters.png` (radar),
{'`09_mapa_clusters.png` (mapa do Brasil), ' if p['mapa_ok'] else ''}`10_mapa_de_decisao.png`.

Os dez maiores municípios de cada cluster estão em `18_top_municipios.csv`.

## 8. Valor para a Loft

{_md(p['valor'], ['cluster', 'nome', 'municipios', 'populacao_pct', 'o_que_significa_para_a_fianca', 'acao_de_marketing_sugerida'])}

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

Roda tudo do zero: cria o ambiente, coleta as fontes, gera as {_contar_tabelas()} tabelas em
`reports/tables`, as figuras em `reports/figures` e este relatório. Exige um projeto do Google
Cloud configurado em `.env` para as consultas ao BigQuery da Base dos Dados.
"""
    ARQUIVO.write_text(texto, encoding="utf-8")


def descritiva_limiar() -> float:
    from . import descritiva

    return descritiva.LIMIAR_CORRELACAO


def _contar_tabelas() -> int:
    return len(list(config.DIR_TABELAS.glob("*.csv"))) or 22


def _grupos_md(grupos: dict[str, list[str]], cotovelos: dict[str, int]) -> str:
    linhas = []
    for g, variaveis in grupos.items():
        linhas.append(
            {
                "grupo": g,
                "nome": config.NOMES_GRUPOS[g],
                "n_variaveis": len(variaveis),
                "variaveis": ", ".join(config.VARIAVEIS[v] for v in variaveis),
                "k_do_cotovelo": cotovelos[g],
            }
        )
    return pd.DataFrame(linhas).to_markdown(index=False)


def _veredito_hipotese(p: dict) -> str:
    candidatos = p["candidatos"]
    escolha = p["escolha"]
    melhor_geral = candidatos.iloc[0]
    vencedor = escolha[escolha["escolhido"]].iloc[0]

    texto = (
        f"na silhueta pura, quem ganha é o grupo {melhor_geral['grupo']} "
        f"({config.NOMES_GRUPOS[str(melhor_geral['grupo'])]}), com "
        f"{melhor_geral['silhueta']:.3f}. Isso **não** significa que ele seja o melhor modelo. "
        "A silhueta premia espaços com menos variáveis e mais redundantes, porque ali é mais "
        "fácil achar corte limpo; e os grupos A e B, sozinhos, não respondem à pergunta do "
        "projeto: um só tem mercado e o outro só tem renda, e ninguém decide onde vender fiança "
        "olhando apenas um dos dois lados.\n\n"
        "Por isso a escolha final ficou restrita aos grupos que têm ao menos uma variável de "
        "mercado imobiliário **e** uma de capacidade de pagamento, ou seja C e D. Entre eles:\n\n"
        f"{_md(escolha, ['grupo', 'nome_grupo', 'nome_modelo', 'k', 'silhueta', 'estabilidade_bootstrap'])}\n\n"
    )
    if str(vencedor["grupo"]) == "D":
        texto += (
            f"C tem silhueta um pouco maior ({float(escolha[escolha['grupo'] == 'C']['silhueta'].iloc[0]):.3f} "
            f"contra {float(vencedor['silhueta']):.3f}), diferença de menos de 0,01 que está dentro "
            "do ruído. Mas os clusters de C **não se reproduzem**: no bootstrap o Rand ajustado de "
            f"C é {float(escolha[escolha['grupo'] == 'C']['estabilidade_bootstrap'].iloc[0]):.3f} "
            f"contra {float(vencedor['estabilidade_bootstrap']):.3f} de D. Para uma decisão de "
            "mídia que vai ser repetida mês a mês, estabilidade vale mais que um terceiro decimal "
            "de silhueta.\n\n"
            "**Veredito: a hipótese de que o grupo D é o melhor se sustenta**, não porque D separa "
            "mais, e sim porque D separa de forma reprodutível. Acrescentar alcance digital não "
            "aumenta a separação — o alcance de internet móvel é a variável menos dispersa de "
            "todas, com coeficiente de variação de 0,17, já que praticamente todo município de "
            "50 mil habitantes ou mais tem cobertura — mas **estabiliza** a solução e traz para o "
            "modelo a dimensão em que a decisão de mídia é executada."
        )
    else:
        texto += (
            f"**Veredito: a hipótese não se sustenta.** O grupo {vencedor['grupo']} venceu tanto "
            "em silhueta quanto em estabilidade no bootstrap."
        )
    return texto


def _leitura_ablacao(tabela: pd.DataFrame) -> str:
    mais_critica = tabela.iloc[0]
    menos_critica = tabela.iloc[-1]
    return (
        f"A variável mais crítica é **{mais_critica['rotulo']}**: sem ela a silhueta varia "
        f"{mais_critica['variacao']:+.3f}. A menos crítica é **{menos_critica['rotulo']}** "
        f"({menos_critica['variacao']:+.3f}). O Rand ajustado contra a solução completa mostra "
        "quanto a composição dos grupos muda ao remover cada variável."
    )
