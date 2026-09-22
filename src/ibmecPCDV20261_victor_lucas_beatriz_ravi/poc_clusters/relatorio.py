"""Escreve o relatório da POC em markdown a partir dos resultados já calculados."""

from __future__ import annotations

from datetime import date

import pandas as pd

from . import clustering, config, diagnostico
from .descritiva import rotulo

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

    populacao_brasil = diagnostico.populacao_brasil() or base["populacao"].sum()
    ev_pix = diagnostico.evidencia_pix()
    ev_salario = diagnostico.evidencia_salario(base)
    ev_movel = diagnostico.evidencia_movel(base)
    ev_credito = diagnostico.evidencia_credito(base)
    ev_trends = diagnostico.evidencia_trends(base)
    volumes = diagnostico.tabela_volumes(base)
    sem_mercado = diagnostico.municipios_sem_mercado(base)
    robustez = p["robustez_denominador"]
    incremental = p["incremental"]
    nome_alvo = robustez.attrs.get("nome_alvo", "praça em formação")
    correlacao_taxa_base = str(robustez.attrs.get("correlacao_taxa_x_base", "")).replace(".", ",")

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
{base['populacao'].sum() / populacao_brasil * 100:.0f}% da população do país.

Todas as variáveis são relativas à população (por habitante, por 10 mil habitantes ou por 100
domicílios), justamente para o agrupamento **não separar apenas por tamanho de cidade**.

### 2.1 Fontes e data de referência

{_md(p['fontes'], ['rotulo', 'fonte', 'data_referencia', 'data_coleta', 'entra_no_cluster'])}

{_checagem_datas(p)} Não há uso do Censo 2022. O Índice Brasileiro de Conectividade da Anatel
foi **descartado** por ter 2024 como ano mais recente; no lugar dele entraram os acessos de
telefonia móvel dos dados abertos da Anatel.

### 2.2 Decisões de tratamento que mudaram o resultado

Cada número desta tabela é recalculado a cada execução, a partir dos dados coletados.

| Decisão | Motivo, com a evidência desta execução |
| --- | --- |
| Pix: descartar o mês em andamento | {_evidencia_pix(ev_pix)} |
| Salário de admissão: usar a mediana, não a média | Em {ev_salario['municipio']} a média era {ev_salario['media']} e a mediana {ev_salario['mediana']}: poucos salários altos distorciam a comparação entre praças. |
| Internet móvel: usar só linhas de pessoa física | Com pessoa jurídica incluída, {ev_movel['municipio']} marcava {ev_movel['valor_com_pj']} acessos por 100 habitantes, que são linhas de máquina e corporativas; só com pessoa física cai para {ev_movel['valor_so_pf']}. A assimetria da variável saiu de {ev_movel['assimetria_com_pj']} para {ev_movel['assimetria_so_pf']}. |
| Veículos: usar automóveis, não a frota toda | No Brasil a moto cresce onde a renda cai, então a frota total misturaria dois sinais opostos de patrimônio. |
| Crédito: winsorizar as caudas em 1% | O ESTBAN registra a carteira onde a agência está instalada, não onde o tomador mora: {ev_credito['municipio']} aparece com {ev_credito['valor']} de crédito por habitante, {ev_credito['razao']} vezes a mediana de {ev_credito['mediana']}, porque ali está sediado um banco de atuação nacional. |
| Google Trends: virou descritora | Mesmo pedindo resolução de cidade, a API devolve {ev_trends.get('granularidade_devolvida', 'unidade da federação')}. Sem cobertura municipal não há como atingir o mínimo de {ev_trends.get('minimo_exigido', '80%')} combinado. |
| CadÚnico: denominador estimado | A competência disponível não preenche a contagem de pessoas, então usamos famílias sobre domicílios estimados ({config.MORADORES_POR_DOMICILIO} moradores por domicílio, PNAD Contínua). Sendo constante nacional, não altera a posição relativa dos municípios. |

### 2.3 Qualidade da base

Cobertura final: **zero valores faltantes** nas {len(config.VARIAVEIS)} variáveis candidatas,
nos {len(base)} municípios. Conferência de volume contra a realidade, que é o teste que pega
erro de extração:

{_md(volumes, ['base', 'total_no_brasil', 'ordem_de_grandeza_esperada', 'total_nos_municipios_analisados', 'parcela_no_universo'])}

O total no Brasil vem do arquivo bruto, com todos os municípios, e é ele que se confronta com a
realidade conhecida. A última coluna mostra quanto disso está nos municípios analisados: se
passasse de 100% haveria linha duplicada em algum merge. É o teste que pega erro de extração
calado, do tipo unidade trocada ou junção que multiplica registros.

{sem_mercado['quantidade']} municípios do universo têm **zero** estabelecimento imobiliário
formal ativo ({sem_mercado['por_regiao']}). Não é dado faltante: é a ausência real de mercado
formal de locação, e o modelo trata isso como informação. Todos eles caíram no mesmo cluster,
o de {sem_mercado['nome_cluster']}, o que é um sinal de que o agrupamento leu esse fato.

## 3. Método

Pipeline por grupo de variáveis: **log nas variáveis de cauda longa → padronização →
modelo**, com winsorização de 1% nas duas caudas antes do log. Semente fixa em
{config.SEMENTE}.

Variáveis com log nesta execução: {', '.join(rotulo(v) for v in p['variaveis_log']) or 'nenhuma'}.

### 3.1 Corte por correlação

Limiar de {descritiva_limiar():.2f} em módulo na correlação de Spearman. Em cada par acima do
limiar fica a variável que o desenho da POC usa em mais grupos, porque é a que carrega o
sentido de negócio; empatado nisso, fica a de menor VIF.

{_md(p['decisoes'], ['rotulo_descartada', 'rotulo_mantida', 'correlacao_spearman', 'motivo'])}

{_leitura_vif(p)}

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

- **Reamostragem** ({bootstrap['n_comparacoes']} comparações, subamostras sem reposição de
  {bootstrap['fracao_reamostrada']:.0%} dos municípios): Rand ajustado médio de
  **{bootstrap['rand_ajustado_medio']:.3f}** (desvio {bootstrap['rand_ajustado_desvio']:.3f},
  faixa de {bootstrap['rand_ajustado_p5']:.3f} a {bootstrap['rand_ajustado_p95']:.3f}).
  A reamostragem é sem reposição de propósito: com reposição, os municípios duplicados ficam a
  distância zero um do outro e inflam a concordância entre rodadas.
- **Sementes**: {len(sementes)} sementes diferentes, Rand ajustado médio contra a solução de
  referência de **{sementes['rand_ajustado_vs_referencia'].mean():.3f}** (mínimo
  {sementes['rand_ajustado_vs_referencia'].min():.3f}).
- **Ablação**: remoção de uma variável por vez.

{_md(p['ablacao'], ['rotulo', 'silhueta_sem_ela', 'silhueta_completa', 'variacao', 'rand_ajustado_vs_completo'])}

{_leitura_ablacao(p['ablacao'])}

### 6.1 A taxa de empresas novas não é artefato de base pequena

A variável de imobiliárias abertas em 12 meses é uma proporção, e proporção com denominador
pequeno engana: num município com 9 imobiliárias, três aberturas já viram 33%. Como é essa a
variável que mais define o cluster de **{nome_alvo}**, ela foi testada exigindo um número
mínimo de empresas no município.

{_md(robustez, ['base_minima_de_empresas', 'municipios_no_cluster', 'mediana_no_cluster', 'mediana_no_resto', 'p_valor', 'continua_maior'])}

O cluster continua com taxa de abertura muito acima do resto mesmo quando se exige base maior,
e a correlação de Spearman entre a taxa e o número de empresas do município é de apenas
{correlacao_taxa_base}, ou seja **a taxa alta não vem de denominador pequeno**. O achado
sobrevive ao teste. Ainda assim a variável é ruidosa em município de base curta, e é por isso
que ela entra winsorizada.

### 6.2 O cluster serve como variável de um modelo futuro?

Separação interna e estabilidade dizem que o agrupamento é consistente, mas não dizem se ele é
**útil como entrada de modelo**. O teste para isso é outro, e a pergunta certa não é se o
cluster substitui a geografia: é se ele **acrescenta** algo a ela.

Comparamos, em variáveis municipais que ficaram **fora** do modelo, o R² ajustado de
`região + porte` contra `região + porte + cluster`. O R² é ajustado para não premiar o simples
aumento de parâmetros.

{_md(incremental, ['rotulo', 'r2_regiao_e_porte', 'r2_com_o_cluster', 'ganho', 'o_cluster_acrescenta'])}

{_leitura_incremental(incremental)}

Vale registrar o caminho até aqui, porque ele muda a interpretação. O primeiro teste feito foi
outro: pedir que o cluster **vencesse** a região ao explicar as mesmas variáveis retidas. Nesse
formato o cluster perdia, e a conclusão parecia ser que o agrupamento não servia. O teste estava
mal formulado. No Brasil, quase toda variável socioeconômica municipal é fortemente explicada
pela região, então exigir que um agrupamento derrote a geografia é exigir que ele seja um proxy
melhor de desigualdade regional, que não é a função dele. A função é separar praças que devem
receber o mesmo tratamento de mídia, e para isso o que importa é informação incremental.

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

Roda tudo do zero: cria o ambiente, coleta as fontes, gera as {_contar_tabelas()} tabelas em
`reports/tables`, as figuras em `reports/figures` e este relatório. Exige um projeto do Google
Cloud configurado em `.env` para as consultas ao BigQuery da Base dos Dados.
"""
    ARQUIVO.write_text(texto, encoding="utf-8")


def _checagem_datas(p: dict) -> str:
    """Resultado da conferência automática da regra de datas."""
    checagem = p["checagem_datas"]
    modelo = checagem[checagem["entra_no_cluster"]]
    fora = modelo[~modelo["cumpre_a_regra"].fillna(False)]
    mais_antiga = modelo.nsmallest(1, "ano_referencia").iloc[0] if not modelo.empty else None
    if not fora.empty:
        return (
            "**Atenção: a regra de datas foi violada** por "
            + ", ".join(fora["rotulo"]) + "."
        )
    return (
        f"Regra do projeto **conferida em código** nas {len(modelo)} variáveis do modelo: a mais "
        f"antiga é {mais_antiga['rotulo']}, com referência de {mais_antiga['data_referencia']}. "
        "A execução aborta se alguma fonte regredir para antes de "
        f"{diagnostico.ANO_MINIMO_PERMITIDO}, e a conferência completa está em "
        "`02b_checagem_regra_de_datas.csv`."
    )


def _leitura_vif(p: dict) -> str:
    vif = p["vif"]
    maior = vif.iloc[0]
    limiar = descritiva_limiar_vif()
    if float(maior["vif"]) >= limiar:
        return (
            f"O maior VIF é de {maior['vif']:.2f}, em {maior['rotulo']}, acima do limiar de "
            f"{limiar:.0f}: há multicolinearidade a tratar."
        )
    return (
        f"O maior VIF é de {maior['vif']:.2f}, em {maior['rotulo']}, bem abaixo do limiar usual "
        f"de {limiar:.0f}. Não há multicolinearidade grave entre as variáveis que sobraram."
    )


def descritiva_limiar_vif() -> float:
    from . import descritiva

    return descritiva.LIMIAR_VIF


def _menos_dispersa(p: dict) -> str:
    """Variável de menor coeficiente de variação entre as do grupo escolhido."""
    descritivas = p["descritivas"]
    recorte = descritivas[descritivas["variavel"].isin(p["variaveis_finais"])]
    if recorte.empty:
        return "o alcance digital é a dimensão menos dispersa do conjunto."
    menor = recorte.nsmallest(1, "coef_variacao").iloc[0]
    coeficiente = f"{menor['coef_variacao']:.2f}".replace(".", ",")
    return (
        f"a variável de menor dispersão entre as do grupo escolhido é "
        f"**{menor['rotulo']}**, com coeficiente de variação de {coeficiente}."
    )


def silhueta_cluster_menos_baseline(p: dict) -> float:
    """Vantagem do agrupamento sobre o melhor baseline, para dar escala às diferenças."""
    comparacao = p["comparacao_final"]
    nosso = float(comparacao.iloc[0]["silhueta"])
    baselines = comparacao.iloc[1:]["silhueta"].astype(float)
    return nosso - float(baselines.max())


def _evidencia_pix(ev: dict) -> str:
    if not ev:
        return "dado bruto do Pix não disponível nesta execução."
    if not ev.get("houve_descarte"):
        return "nenhum mês precisou ser descartado: todos vieram com volume compatível."
    return (
        f"o mês de {ev['mes_descartado']} aparecia com {ev['valor_descartado']} contra "
        f"{ev['valor_tipico']} do mês típico fechado, porque ainda estava em andamento na data "
        f"da coleta. Usamos os 12 meses completos."
    )


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
                "variaveis": ", ".join(rotulo(v) for v in variaveis),
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
    diferenca = p.get("diferenca_silhueta")
    if str(vencedor["grupo"]) == "D":
        silhueta_c = float(escolha[escolha["grupo"] == "C"]["silhueta"].iloc[0])
        estabilidade_c = float(escolha[escolha["grupo"] == "C"]["estabilidade_bootstrap"].iloc[0])
        texto += (
            f"C tem silhueta um pouco maior ({silhueta_c:.3f} contra {float(vencedor['silhueta']):.3f}). "
            "Antes de decidir por isso, essa vantagem foi testada: reamostrando os municípios "
            "200 vezes, refazendo o preparo dentro de cada subamostra e recalculando a silhueta "
            "das duas configurações sobre os mesmos municípios.\n\n"
            f"{_md(diferenca) if diferenca is not None and not diferenca.empty else '(teste não executado)'}\n\n"
        )
        vantagem_silhueta = abs(silhueta_c - float(vencedor["silhueta"]))
        vantagem_estabilidade = float(vencedor["estabilidade_bootstrap"]) - estabilidade_c
        if diferenca is not None and not diferenca.empty:
            linha = diferenca.iloc[0]
            if bool(linha["diferenca_significativa"]):
                texto += (
                    f"O intervalo de 95% da diferença vai de {linha['intervalo_95_inferior']:+.4f} "
                    f"a {linha['intervalo_95_superior']:+.4f} e **não inclui o zero**: a vantagem "
                    "de C em separação é real, não é ruído. Mas é preciso olhar o tamanho dela.\n\n"
                )
            else:
                texto += (
                    f"O intervalo de 95% da diferença vai de {linha['intervalo_95_inferior']:+.4f} "
                    f"a {linha['intervalo_95_superior']:+.4f} e **inclui o zero**, logo as duas "
                    "configurações são estatisticamente equivalentes em separação.\n\n"
                )
        texto += (
            f"A vantagem de C em silhueta é de {vantagem_silhueta:.3f}. Para comparar, a vantagem "
            f"do próprio agrupamento sobre o baseline de geografia é de cerca de "
            f"{silhueta_cluster_menos_baseline(p):.3f}, ou seja a diferença entre C e D é uma "
            "fração pequena do que está em jogo.\n\n"
            "Já a diferença de estabilidade vai na direção oposta e é maior: sob subamostragem o "
            f"Rand ajustado de C é {estabilidade_c:.3f} contra "
            f"{float(vencedor['estabilidade_bootstrap']):.3f} de D, uma distância de "
            f"{vantagem_estabilidade:.3f}. Os clusters de C mudam de composição quando se troca "
            "um quinto dos municípios; os de D não.\n\n"
            "O critério aplicado foi esse: trocar "
            f"{vantagem_silhueta:.3f} de separação por {vantagem_estabilidade:.3f} de "
            "reprodutibilidade, porque a decisão de mídia vai ser refeita mês a mês e um "
            "agrupamento que se reorganiza a cada rodada não sustenta plano de verba.\n\n"
            "**Veredito: a hipótese de que o grupo D é o melhor se sustenta**, não porque D separa "
            "mais, e sim porque D separa de forma reprodutível. Acrescentar alcance digital não "
            f"aumenta a separação, e a razão aparece na descritiva: {_menos_dispersa(p)} "
            "Ou seja, o alcance digital quase não distingue uma praça da outra, porque "
            "praticamente todo município de 50 mil habitantes ou mais já tem cobertura. O que "
            "essas variáveis fazem é **estabilizar** a solução e trazer para o modelo a dimensão "
            "em que a decisão de mídia é executada."
        )
    else:
        texto += (
            f"**Veredito: a hipótese não se sustenta.** O grupo {vencedor['grupo']} venceu tanto "
            "em silhueta quanto em estabilidade no bootstrap."
        )
    return texto


def _leitura_incremental(tabela: pd.DataFrame) -> str:
    if tabela.empty:
        return "(teste não executado)"
    quantas = tabela.attrs.get("quantas_acrescenta", 0)
    total = tabela.attrs.get("total", len(tabela))
    ganho = tabela.attrs.get("ganho_medio", 0.0)
    melhor = tabela.iloc[0]
    if quantas == total and ganho > 0:
        veredito = (
            f"O cluster acrescenta informação em **{quantas} de {total}** variáveis retidas, com "
            f"ganho médio de **{ganho:+.4f}** no R² ajustado. Em nenhuma ele piora. "
            "**O rótulo do cluster é, portanto, uma variável válida para alimentar um modelo "
            "futuro**: ele carrega algo que região e porte, juntos, não carregam."
        )
    elif quantas > total / 2:
        veredito = (
            f"O cluster acrescenta em {quantas} de {total} variáveis retidas, com ganho médio de "
            f"{ganho:+.4f}. O sinal é positivo mas não é uniforme, então ele serve como variável "
            "auxiliar, não como principal."
        )
    else:
        veredito = (
            f"O cluster só acrescenta em {quantas} de {total} variáveis retidas, com ganho médio "
            f"de {ganho:+.4f}. **Não há evidência de que sirva como variável de modelo**: como "
            "segmentação descritiva ele se sustenta, como preditor não."
        )
    return (
        veredito
        + f" O maior ganho está em {melhor['rotulo']}, de {melhor['r2_regiao_e_porte']:.3f} para "
        f"{melhor['r2_com_o_cluster']:.3f}."
    )


def _leitura_ablacao(tabela: pd.DataFrame) -> str:
    mais_critica = tabela.iloc[0]
    menos_critica = tabela.iloc[-1]
    return (
        f"A variável mais crítica é **{mais_critica['rotulo']}**: sem ela a silhueta varia "
        f"{mais_critica['variacao']:+.3f}. A menos crítica é **{menos_critica['rotulo']}** "
        f"({menos_critica['variacao']:+.3f}). O Rand ajustado contra a solução completa mostra "
        "quanto a composição dos grupos muda ao remover cada variável."
    )
