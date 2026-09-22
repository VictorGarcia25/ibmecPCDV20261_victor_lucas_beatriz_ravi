# Roteiro da fala — POC de clusterização de municípios

Beatriz Babinski · Projeto em Ciência de Dados V · IBMEC

Para ler junto com `apresentacao_poc_aula.pdf`. Está escrito como fala, não como texto
formal. Tempo estimado: 10 a 12 minutos. Onde tem **[SLIDE X]** é para virar o slide.

---

## [SLIDE 1 — capa]

Boa tarde, gente. O pessoal do outro grupo já explicou o problema da Loft, então eu vou
pular essa parte e ir direto pro que eu fiz.

Só pra situar em uma frase: a Loft tem sete produtos, mas quase três quartos dos anúncios
dela são de um produto só, que é a fiança. E quem compra fiança não é o inquilino, é a
imobiliária. Então a pergunta que sobrou foi: **onde** vender isso. Em que cidade.

E é aí que entra a minha parte, que é uma prova de conceito **não supervisionada**.

## [SLIDE 2 — em uma frase]

Deixa eu explicar o que isso quer dizer, porque muda tudo no jeito de avaliar.

Num problema supervisionado, você tem a resposta certa. Você tem lá "esse cliente comprou,
esse não comprou", e o modelo aprende a diferença. Aqui eu **não tenho** isso. Não existe
uma lista de "cidade boa pra vender fiança" pra eu aprender. Ninguém nunca rotulou isso.

Então eu não posso medir acurácia. Não existe acurácia sem gabarito.

O que eu posso fazer é agrupar. Pegar os municípios e deixar o algoritmo descobrir quais se
parecem entre si. E aí a prova de que deu certo não é "acertei X por cento". A prova é
outra, e é essa: **eu separo melhor do que aquilo que a Loft já teria de graça?**

Porque a Loft, sem modelo nenhum, já pode dividir o Brasil por região — Norte, Nordeste,
Sudeste, Sul, Centro-Oeste. E já pode dividir por tamanho de cidade. Isso é de graça. Se o
meu modelo não for melhor do que isso, ele não serve pra nada.

Guarda essa ideia, porque ela volta no final e é o coração da apresentação.

Ah, e a unidade de análise: são os 687 municípios brasileiros com 50 mil habitantes ou
mais. E tudo que eu meço é **por habitante**. Isso é de propósito: se eu usasse número
absoluto, o modelo ia só me dizer que São Paulo é grande e Jaru é pequena. Isso eu já sei.

---

# 1. A escolha das variáveis

## [SLIDE 3 — como escolhemos as variáveis]

Essa foi a parte que mais me tomou tempo, e é onde eu acho que tem mais decisão minha.

Eu **não** comecei perguntando "que dado tem disponível?". Isso é a armadilha clássica:
você acaba usando o que é fácil de baixar, não o que importa.

Eu comecei pelo contrário. Eu me perguntei: se eu fosse a pessoa que decide se a Loft vai
investir numa cidade, o que eu precisaria saber? E saiu uma lista de seis perguntas.

**Primeira: existe mercado?** Não adianta a cidade ser rica se não tem imobiliária. A
fiança é vendida *para* a imobiliária, ela é o cliente. Então eu fui na base de CNPJ da
Receita Federal e contei quantas administradoras de imóveis e quantas imobiliárias existem
ativas em cada cidade, por 10 mil habitantes. E contei também quantas abriram nos últimos
12 meses, que é um sinal de mercado se formando agora.

**Segunda: o inquilino consegue pagar?** Porque a fiança garante o aluguel. Se o inquilino
não paga, a Loft paga. Aqui eu usei o Pix de pessoa física por habitante — que é um proxy
muito bom de renda circulando *hoje*, atualizado todo mês —, o salário mediano de quem foi
contratado na cidade, a poupança por habitante e a frota de automóveis.

**Terceira: qual o risco?** Que é o outro lado da mesma moeda. Aqui entrou o percentual de
famílias no CadÚnico, que é vulnerabilidade social, e uma variável que eu gosto bastante,
que é a **alavancagem**: quanto a cidade toma emprestado dividido por quanto ela poupa. Se
a cidade deve muito e poupa pouco, o risco de inadimplência é maior.

**Quarta: tem demanda entrando?** Aluguel é movido por gente chegando. Então eu peguei o
crescimento da população em um ano e a fatia de contratações na faixa de 18 a 30 anos, que
é exatamente a idade de quem sai da casa dos pais e aluga.

**Quinta: dá pra anunciar?** Que é a pergunta de marketing mesmo. Internet móvel 4G/5G e
banda larga fixa por 100 habitantes.

**Sexta: tem concorrente?** Porque fiança compete com seguro-fiança. Então eu contei os
corretores de seguros por 10 mil habitantes.

Deu 16 variáveis. E todas elas, sem exceção, respondem a uma dessas seis perguntas. Não tem
nenhuma variável ali que entrou porque era fácil.

---

# 2. Os dados

## [SLIDE 4 — de onde veio cada dado]

Todas as fontes são públicas e oficiais. Banco Central, Receita Federal, CAGED do
Ministério do Trabalho, IBGE, Anatel, Ministério do Desenvolvimento Social e Senatran.

E aqui tem uma regra que a gente se impôs e que foi mais difícil de cumprir do que parece:
**nada anterior a 2025**. Nada de Censo 2022, nada de dado velho.

Isso parece detalhe, mas não é. Muita análise de município no Brasil é feita em cima do
Censo, que é de 2022, e aí você está decidindo verba de 2026 com retrato de quatro anos
atrás. A gente não quis isso.

E eu não deixei essa regra como promessa no texto. Ela é **verificada por código**. Tem uma
função que confere a data de referência de cada variável, e se alguma delas regredir pra
antes de 2025, o programa **para com erro**. Ele se recusa a rodar.

Isso já teve consequência prática: eu ia usar o Índice Brasileiro de Conectividade da
Anatel, que seria perfeito pra medir 4G e 5G. Só que o dado mais recente dele é de 2024.
Então ele foi descartado, e eu tive que ir buscar os acessos de telefonia móvel direto no
dado aberto da Anatel, que tem até julho de 2026.

## [SLIDE 5 — os dados batem com a realidade?]

Antes de rodar qualquer modelo, eu fiz uma coisa que eu acho que todo mundo deveria fazer e
quase ninguém faz: eu somei cada base inteira e comparei com a ordem de grandeza conhecida
do Brasil.

Por quê? Porque erro de extração não dá erro. Ele passa calado. Você troca uma unidade,
você faz um join que duplica linha, e o código roda lindo — só que o resultado está errado.

Então: o ESTBAN me deu R$ 6,6 trilhões de crédito. O estoque de crédito do Brasil é da casa
dos trilhões. Bate. O Senatran me deu 65,6 milhões de automóveis. Bate. O CNPJ me deu 144
mil imobiliárias ativas no país. Bate.

E a última coluna é um segundo teste: quanto disso está dentro dos meus 687 municípios.
Nenhuma passa de 100% — se passasse, seria sinal de linha duplicada em algum merge.

Aliás, essa coluna me deu um achado que eu nem estava procurando: o crédito e as
imobiliárias estão uns 92% concentrados nas cidades grandes, mas o CadÚnico só tem 62%. Ou
seja, **a vulnerabilidade social está desproporcionalmente fora das cidades grandes**. Pra
fiança isso importa muito: o risco não está onde está o mercado.

Resultado final da base: zero valores faltantes. 16 variáveis, 687 municípios, nenhum buraco.

---

# 3. A estatística descritiva

## [SLIDE 6 — o que a distribuição obrigou]

Aqui é onde a estatística descritiva deixa de ser enfeite e vira decisão.

Eu olhei a distribuição de cada variável, e 7 das 16 tinham **cauda longa à direita** —
assimetria acima de 1. Isso quer dizer que a maioria das cidades está amontoada num valor
baixo e umas poucas estão lá longe. Se eu jogo isso num modelo de distância, como o KMeans,
essas poucas cidades extremas dominam tudo.

Então nessas 7 eu apliquei **logaritmo**, que comprime a cauda.

Mas antes do log eu fiz outra coisa: **winsorizei** 1% nas duas pontas, ou seja, cortei os
valores mais extremos no percentil 1 e no 99.

E o motivo disso é muito concreto, olha a tabela. O crédito per capita tinha assimetria de
**20,2**. Vinte. Um valor normal está entre menos 1 e 1. E quando eu fui ver quem era o
extremo: **Osasco, com R$ 1 milhão de crédito por habitante**.

Osasco não tem um milhão de reais de crédito por morador. O que acontece é que o Banco
Central registra a carteira de crédito **onde o banco está sediado**, e tem um banco grande
sediado em Osasco. Aquilo é a carteira nacional do banco inteiro, atribuída a uma cidade.

Se eu não tratasse isso, o modelo ia criar um cluster com Osasco sozinha dentro. Depois do
corte, a assimetria cai de 20,2 pra 2,0.

Esse tipo de coisa apareceu em várias fontes, e cada uma virou uma decisão documentada. Só
pra dar mais dois exemplos rápidos:

- O Pix: eu peguei setembro de 2026 e o volume estava 30% abaixo do normal. É porque o mês
  ainda estava em andamento na data da coleta. Se eu usasse, todas as cidades apareceriam
  mais pobres do que são. Escrevi uma regra que detecta e descarta mês incompleto sozinha.
- A internet móvel: com pessoa jurídica incluída, Jaboticabal aparecia com 881 acessos por
  100 habitantes. Oito celulares por pessoa. São chips de máquina, de IoT, registrados ali.
  Filtrando só pessoa física, a assimetria cai de 8,1 pra menos 0,6.

## [SLIDE 7 — a distribuição de cada variável]

Esses são os histogramas de todas as 16. Dá pra ver a olho nu quais são as assimétricas —
aquelas todas espremidas no canto esquerdo com uma cauda comprida à direita.

## [SLIDE 8 — correlação e VIF]

Última etapa antes de modelar: tirar variável redundante.

A regra que eu usei: se duas variáveis têm correlação de Spearman acima de 0,80 em módulo,
fica só uma. Porque as duas estão dizendo a mesma coisa, e manter as duas dá peso dobrado
pra aquela dimensão sem que ninguém perceba.

Saíram três. E aqui tem uma decisão que eu quero destacar, porque ela **não foi
automática**.

Imobiliárias e administradoras de imóveis tinham correlação de 0,82. Eu tinha que escolher
uma. Se eu deixasse o critério puramente estatístico decidir, ele manteria "imobiliárias",
que é a mais comum.

Mas eu mantive **administradoras**. E o motivo é de negócio: administradora de imóveis é o
CNAE 6822, que é especificamente quem **administra locação**. Imobiliária é o 6821, que
inclui venda. E o produto aqui é fiança, que é um produto de **locação**. Então a variável
certa é administradoras, mesmo que a estatística não se importe.

Eu programei essa regra: em caso de correlação alta, fica a variável que o desenho do
estudo usa em mais grupos, que é a que carrega sentido de negócio. Empatou nisso, aí sim
vai pro VIF.

E o VIF: depois dos cortes, o maior ficou em 6,56. O limiar usual é 10. Então não tem
multicolinearidade grave.

---

# 4. Os conjuntos e os testes

## [SLIDE 9 — os 5 conjuntos]

Agora, uma escolha de método que eu acho importante.

Eu podia ter escolhido um conjunto de variáveis e defendido ele. Mas isso é fácil demais de
enviesar — você escolhe o que dá o resultado bonito.

Então eu montei **cinco conjuntos diferentes** e deixei competir:

- **A** — só mercado imobiliário
- **B** — só capacidade de pagamento
- **C** — mercado + renda
- **D** — mercado + renda + marketing
- **E** — mercado + risco + concorrência + demanda

Cada um testa uma hipótese diferente sobre o que define uma praça. E a minha hipótese
inicial, que eu escrevi antes de rodar, era que o **D** ia ganhar, porque ele é o único que
tem a dimensão de alcance digital, que é onde a mídia acontece.

O E aí nasceu depois, e eu conto essa história daqui a pouco porque ela é interessante.

## [SLIDE 10 — os testes que rodamos]

O pipeline é o mesmo pra todos, sem exceção: winsoriza, aplica log nas assimétricas,
padroniza, e só então entra no modelo. Padronizar é obrigatório porque as variáveis estão
em escalas completamente diferentes — uma é em reais, outra é percentual.

E aí rodei **cinco conjuntos, vezes três algoritmos, vezes k de 2 a 10**. Dá 135
combinações.

Os três algoritmos são KMeans, Aglomerativo com ligação de Ward, e Mistura Gaussiana. Usei
três de propósito, porque cada um tem um viés diferente: o KMeans assume grupos esféricos
do mesmo tamanho, o Ward junta por menor aumento de variância, e a Mistura Gaussiana
permite grupos de formatos diferentes. Se os três concordam, é sinal de que a estrutura é
real e não artefato do algoritmo.

Em cada combinação eu medi quatro métricas: inércia, pro cotovelo; silhueta; Davies-Bouldin;
e Calinski-Harabasz. Semente fixa em 42 em tudo, então qualquer pessoa roda e dá igual.

## [SLIDE 11 — a escolha de k]

E aqui apareceu o resultado que mais me incomodou, e que eu decidi contar em vez de
esconder.

**A silhueta é máxima em k = 2 em quase todas as combinações.** E cai a partir daí,
monotonicamente. Olha as curvas.

Isso não é bug. Isso quer dizer uma coisa sobre o Brasil: nessas variáveis, o país municipal
é um **contínuo**. Não existem cinco grupinhos bem separados esperando pra serem
descobertos. Existe uma escada, de cidade mais pobre a cidade mais rica, e eu estou
escolhendo onde cortar.

Se eu obedecesse cegamente a métrica, eu entregaria k=2: "cidade rica e cidade pobre". Está
estatisticamente correto e é **completamente inútil** pra decidir mídia.

Então eu fiz duas coisas. Primeiro, escolhi o k pelo **cotovelo da inércia**, que é o ponto
onde adicionar mais um cluster para de compensar — deu 5. E segundo, e mais importante: eu
transferi o ônus da prova pro **baseline**. Se os grupos são um corte arbitrário de um
contínuo, então eles têm que provar o valor deles ganhando da alternativa, não tendo
silhueta alta em absoluto.

---

# 5. O baseline

## [SLIDE 12 — o baseline]

Esse é o slide central da apresentação. É aqui que a prova de conceito passa ou não passa.

A pergunta é: meu agrupamento é melhor do que aquilo que já existe sem modelo nenhum?

Eu comparei com três baselines:
1. **As 5 regiões do IBGE** — o mapa que qualquer um tem de graça.
2. **Faixas de porte populacional** — cidade pequena, média, grande.
3. **Sorteio aleatório** — pra ter um piso.

E todos os quatro avaliados **no mesmo espaço de variáveis**, então a silhueta é
comparável. Isso é importante: não adianta comparar silhueta de espaços diferentes.

O resultado: meus clusters dão silhueta de **0,236**. As regiões do IBGE dão **-0,001**. O
porte dá **-0,098**. O sorteio dá **-0,031**.

Silhueta negativa quer dizer que os pontos estão, em média, mais perto do grupo vizinho do
que do próprio grupo. Ou seja: **dividir o Brasil por região, nessas variáveis, é pior do
que sortear.** O que faz sentido quando você pensa: dentro do Sudeste cabe São Paulo e cabe
cidade pequena do interior de Minas, que não têm nada a ver uma com a outra.

E tem um número aqui que eu acho o mais importante de todos, que é o Rand ajustado contra o
porte: **0,032**.

O Rand ajustado mede o quanto duas divisões concordam. Zero é concordância nenhuma, um é
idêntico. Deu 0,032, que é praticamente zero. Isso significa que **o meu modelo não
redescobriu o tamanho da cidade**. Esse era o risco número um dessa análise, e é por isso
que eu relativizei tudo por habitante lá no começo. Funcionou.

Contra a região deu 0,185 — tem alguma relação com geografia, o que é esperado num país
desigual, mas está longe de ser a mesma coisa. Se fosse, bastava comprar mídia por região.

## [SLIDE 13 — robustez]

Passar no baseline não basta se o resultado for frágil. Então eu testei três coisas.

**Estabilidade:** eu tiro 20% dos municípios aleatoriamente, rodo de novo, e vejo se os
grupos continuam os mesmos. Fiz isso 99 vezes. A concordância média deu **0,85** de Rand
ajustado, o que é alto.

Um detalhe técnico que eu fiz questão de acertar: a padronização e o log são **refeitos
dentro de cada subamostra**, não herdados da base cheia. Se eu herdasse, informação do
conjunto todo vazaria pra dentro de cada rodada e a estabilidade sairia otimista. Quando eu
corrigi isso, o número caiu de 0,94 pra 0,84 — ou seja, eu estava me enganando antes.

**Sementes:** rodei com 10 sementes aleatórias diferentes. Praticamente a mesma solução.

**Ablação:** tirei uma variável por vez e vi o quanto a separação cai. Nenhuma variável
sozinha sustenta o resultado — o que é bom, quer dizer que não é uma variável fazendo todo
o trabalho.

## [SLIDE 14 — valor incremental]

E agora a prova que eu considero a mais importante, porque é a que responde se isso serve
pro projeto seguir.

A pergunta: **o rótulo do cluster acrescenta informação que região e porte já não dão?**

Porque pensa comigo: se num modelo futuro eu já tenho região e já tenho porte como
variáveis, faz sentido incluir o cluster também? Ou ele é redundante?

O teste: eu pego variáveis municipais que ficaram **de fora** do modelo, e comparo o R²
ajustado de "região + porte" contra "região + porte + cluster". Usei R² **ajustado** de
propósito, que penaliza parâmetro a mais — senão qualquer variável aleatória "melhoraria" o
modelo só por adicionar graus de liberdade.

Resultado: o cluster acrescenta em **15 de 15** variáveis testadas. Em nenhuma ele piora. O
ganho médio é de 0,044 no R² ajustado, e nas duas maiores chega a 0,148 e 0,140.

Então sim: **o cluster é uma variável válida pra alimentar um modelo futuro.**

E aqui eu preciso contar um erro que eu cometi, porque ele quase me fez jogar a análise fora.

O **primeiro** teste que eu fiz foi outro. Eu testei se o cluster **vencia** a região. E ele
perdeu feio — ganhou em 2 de 7, com ganho médio negativo. Eu cheguei a concluir que a
análise não servia.

Aí eu parei e olhei de novo, e o teste é que estava mal formulado. No Brasil, quase toda
variável socioeconômica municipal é muito explicada pela região, porque a desigualdade aqui
é regional. Exigir que um agrupamento **derrote** a geografia é exigir que ele seja um proxy
melhor de desigualdade regional — e essa não é a função dele.

A função dele é separar praças que devem receber o mesmo tratamento de mídia. Pra isso, o
que importa é se ele **acrescenta**, não se ele substitui. Mudei a pergunta, e a resposta
virou 15 de 15.

---

# 6. Os resultados

## [SLIDE 15 — os 5 tipos de praça]

Então, o que saiu disso tudo. Cinco tipos de praça:

**Praça madura de locação** — 131 municípios, mas quase **metade da população** do universo.
São São Paulo, Rio, Brasília, Fortaleza. Muita administradora, renda alta, alcance digital
alto, vulnerabilidade baixa. É o mercado consolidado.

**Praça popular de grande porte** — 167 municípios, 24% da população. Manaus, Belém, Maceió,
São Gonçalo. Cidade grande, muita gente, mas o mercado formal de locação é **raso pro
tamanho dela**, e a vulnerabilidade é acima da média.

**Praça intermediária conectada** — 219 municípios, 19%. Caxias do Sul, Mogi das Cruzes,
Betim. Tudo perto da média, vulnerabilidade baixa, banda larga acima da média. É o Sul e o
Sudeste industrial.

**Praça em formação** — 73 municípios, 5%. Belford Roxo, Caucaia, Águas Lindas. Periferia
metropolitana. O que define ela é uma coisa só e muito forte: **muita imobiliária abrindo
agora**. Mediana de 27% de empresas novas, contra 13% do resto.

**Praça sem mercado formal** — 97 municípios, 5%. Interior do Maranhão e da Paraíba. Tudo
negativo. E aqui tem um dado que me marcou: **20 municípios com mais de 50 mil habitantes
têm literalmente ZERO imobiliária formal ativa.** Zero. E os 20 caíram todos nesse mesmo
cluster, o que é um ótimo sinal de que o agrupamento leu esse fato.

## [SLIDE 16 — o mapa]

No mapa dá pra ver bem. O laranja, que é a praça intermediária conectada, cobre o Sul e o
Sudeste. O vermelho, sem mercado formal, é Norte e Nordeste. O roxo, a praça madura, está
pulverizado nas capitais e regiões metropolitanas.

Repara que **não é um mapa de regiões**. Tem cluster vermelho no meio do Sudeste e tem
cluster roxo no Nordeste. Se fosse só geografia, ia sair um mapa em blocos contínuos.

## [SLIDE 17 — o perfil]

Esse é o heatmap do perfil. Cada linha é um cluster, cada coluna é uma variável, e a cor é
quantos desvios padrão aquele cluster está acima ou abaixo da média nacional.

Dá pra ler a assinatura de cada um. A praça madura, azul em tudo que é bom. A sem mercado
formal, vermelha em tudo. E a praça em formação, que é aquela linha com um pico isolado na
coluna de imobiliárias novas.

Ah, e uma validação que eu gosto de mostrar: eu tinha variáveis **descritoras**, que não
entraram no modelo — inadimplência por estado, percentual de domicílios alugados, busca no
Google por "fiança aluguel". Quando eu olho elas por cluster, elas ordenam certinho sozinhas.
A praça sem mercado formal tem a **maior** inadimplência e a **menor** busca por fiança. A
praça madura tem o maior percentual de domicílios alugados. Isso é validação externa: o
modelo não viu esses dados e mesmo assim os grupos fazem sentido neles.

## [SLIDE 18 — o que muda na mídia]

E aí o que isso vira na prática, que é o ponto:

- **Praça madura**: mídia de conversão pra imobiliária, verba concentrada, meta de custo por
  lead. É onde o dinheiro tem que estar.
- **Praça popular de grande porte**: aqui a decisão muda. Não é conversão, é **captação**. O
  gargalo não é demanda, é falta de imobiliária pra vender. Então a meta é custo por
  imobiliária cadastrada, não por lead de inquilino.
- **Praça em formação**: momento de entrada, mídia de educação de produto, custo por lead
  ainda baixo.
- **Praça intermediária conectada**: praça de teste A/B de criativo, verba pequena, pra
  aprender barato antes de levar o aprendizado pras praças maduras.
- **Praça sem mercado formal**: **zero verba**. Praça de exclusão.

Essa última linha é, na minha opinião, a mais valiosa da análise inteira. Porque dizer onde
**não** gastar é tão útil quanto dizer onde gastar, e é o tipo de coisa que ninguém olha.

---

# 7. Conclusão

## [SLIDE 19 — conclusão]

Fechando.

**A prova de conceito passou.** O agrupamento tem silhueta de 0,236 contra praticamente zero
da geografia e negativo do porte. Ele é estável sob reamostragem. E ele acrescenta
informação em 15 de 15 variáveis que ficaram fora do modelo, o que quer dizer que dá pra
usar o rótulo dele como variável num modelo futuro.

**Mas tem uma ressalva que eu faço questão de dizer**, porque seria fácil omitir: esses
grupos **não são naturais**. A métrica disse k=2. O Brasil municipal é um contínuo. O que eu
entreguei é um **corte útil** desse contínuo, e a defesa dele é a comparação com o baseline,
não a separação absoluta. Quem apresentar isso como "descobri cinco grupos que existem na
natureza" está exagerando.

**E o que a análise ainda não faz**: ela não diz quanto a Loft ganha em cada praça. Ela
descreve o **mercado**, não o desempenho da Loft dentro dele. Pra isso eu precisaria de
receita e de sinistro de fiança por município, que é dado interno que a gente não tem.

Que é exatamente o próximo passo: cruzar esses clusters com o dado interno e transformar
"praça promissora" em **retorno esperado por real investido**. Aí sim a pergunta do projeto
— onde colocar o próximo real — fica respondida com número, e não com tipo.

É isso. Obrigada.

---

# Perguntas que podem vir, e a resposta curta

**"Isso não é só geografia com outro nome?"**
Não. O Rand ajustado contra as 5 regiões é 0,185, e contra porte é 0,032. E no teste de
valor incremental o cluster acrescenta informação **em cima** de região e porte em 15 de 15
variáveis. Se fosse a mesma coisa, o ganho seria zero.

**"Por que k=5 se a silhueta é melhor em k=2?"**
Porque k=2 é estatisticamente melhor e praticamente inútil — separa rico de pobre. Escolhi
pelo cotovelo da inércia e transferi a prova pro baseline. E isso está escrito no relatório,
não escondido.

**"Como você validou sem ter rótulo?"**
Quatro formas: separação interna com três métricas, comparação com três baselines,
estabilidade sob reamostragem, e valor incremental em variáveis retidas. A quarta é a mais
forte porque usa dado que o modelo nunca viu.

**"Por que KMeans e não outro?"**
Testei três: KMeans, Ward e Mistura Gaussiana, em 135 combinações. O KMeans ganhou no
conjunto escolhido. Os três estão na tabela.

**"E se os dados mudarem no mês que vem?"**
Roda de novo com um comando. As dependências estão fixadas, a semente é fixa, e o relatório
e a apresentação leem os números das tabelas — nada é digitado à mão. Se alguma fonte
regredir pra antes de 2025, o programa para com erro em vez de entregar resultado velho.

**"Qual foi a maior dificuldade?"**
Duas. A primeira foi o efeito de sede nas fontes bancárias — Osasco com R$1 milhão de
crédito por habitante. A segunda foi eu ter formulado o teste de validação errado no começo
e quase ter concluído que a análise não servia.
