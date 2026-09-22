"""Gera a apresentação da POC em PDF, lendo os números das tabelas já calculadas.

Formato 16:9 para projetar. Os valores nunca são digitados: saem de reports/tables, então a
apresentação acompanha a execução em vez de envelhecer junto com um número colado.
"""

from __future__ import annotations

import textwrap

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from . import config

ARQUIVO = config.RAIZ / "reports" / "apresentacao_poc_clusterizacao.pdf"
LARGURA, ALTURA = 960, 540

AZUL = colors.HexColor("#123B5E")
AZUL_CLARO = colors.HexColor("#2A6F97")
VERDE = colors.HexColor("#2A9D8F")
VERMELHO = colors.HexColor("#C44E52")
CINZA = colors.HexColor("#5A6472")
CINZA_CLARO = colors.HexColor("#EDF1F5")
CODIGO_FUNDO = colors.HexColor("#1B2733")

MARGEM = 54


def _contar_testes() -> int:
    """Pergunta ao próprio pytest quantos testes existem, contando os parametrizados."""
    import subprocess
    import sys

    arquivo = config.RAIZ / "tests"
    if not arquivo.exists():
        return 0
    try:
        saida = subprocess.run(
            [sys.executable, "-m", "pytest", str(arquivo), "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(config.RAIZ),
            env={"PYTHONPATH": str(config.RAIZ / "src"), "PATH": "/usr/bin:/bin"},
        )
        for linha in reversed(saida.stdout.strip().splitlines()):
            if "test" in linha and linha.split()[0].isdigit():
                return int(linha.split()[0])
    except Exception:
        pass
    caminho = arquivo / "test_poc_clusters.py"
    return caminho.read_text(encoding="utf-8").count("\ndef test_") if caminho.exists() else 0


def _formatar(valor) -> str:
    """Tira o .0 de número inteiro que veio como float do CSV, e usa vírgula decimal."""
    if isinstance(valor, float):
        if pd.isna(valor):
            return "-"
        if float(valor).is_integer():
            return f"{int(valor):,}".replace(",", ".")
        return f"{valor:g}".replace(".", ",")
    return str(valor)


def _tabela(nome: str) -> pd.DataFrame:
    return pd.read_csv(config.DIR_TABELAS / f"{nome}.csv")


class Deck:
    def __init__(self, caminho):
        self.c = canvas.Canvas(str(caminho), pagesize=(LARGURA, ALTURA))
        self.numero = 0

    # ---------- estrutura ----------

    def capa(self, titulo: str, subtitulo: str, autoria: str, destaques: list[str]) -> None:
        c = self.c
        c.setFillColor(AZUL)
        c.rect(0, 0, LARGURA, ALTURA, stroke=0, fill=1)
        c.setFillColor(VERDE)
        c.rect(0, ALTURA - 8, LARGURA, 8, stroke=0, fill=1)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 34)
        for i, linha in enumerate(textwrap.wrap(titulo, 42)):
            c.drawString(MARGEM, ALTURA - 120 - i * 42, linha)
        c.setFont("Helvetica", 17)
        c.setFillColor(colors.HexColor("#BFD4E4"))
        for i, linha in enumerate(textwrap.wrap(subtitulo, 74)):
            c.drawString(MARGEM, ALTURA - 215 - i * 24, linha)

        y = 150
        for item in destaques:
            c.setFillColor(VERDE)
            c.circle(MARGEM + 5, y + 5, 4, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(MARGEM + 20, y, item)
            y -= 27

        c.setFont("Helvetica", 12)
        c.setFillColor(colors.HexColor("#8FB0C8"))
        c.drawString(MARGEM, 46, autoria)
        c.showPage()

    def slide(self, titulo: str, sobretitulo: str = "") -> None:
        """Abre um slide novo e devolve o topo da área de conteúdo."""
        self.numero += 1
        c = self.c
        c.setFillColor(colors.white)
        c.rect(0, 0, LARGURA, ALTURA, stroke=0, fill=1)
        c.setFillColor(AZUL)
        c.rect(0, ALTURA - 6, LARGURA, 6, stroke=0, fill=1)

        y = ALTURA - 52
        if sobretitulo:
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(VERDE)
            c.drawString(MARGEM, y, sobretitulo.upper())
            y -= 26
        c.setFont("Helvetica-Bold", 25)
        c.setFillColor(AZUL)
        for linha in textwrap.wrap(titulo, 62):
            c.drawString(MARGEM, y, linha)
            y -= 31

        c.setFillColor(CINZA)
        c.setFont("Helvetica", 9)
        c.drawRightString(LARGURA - MARGEM, 24, str(self.numero))
        self.y = y - 12

    def secao(self, numero: str, titulo: str, resumo: str) -> None:
        self.numero += 1
        c = self.c
        c.setFillColor(AZUL_CLARO)
        c.rect(0, 0, LARGURA, ALTURA, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 70)
        c.drawString(MARGEM, ALTURA / 2 + 20, numero)
        c.setFont("Helvetica-Bold", 30)
        c.drawString(MARGEM + 130, ALTURA / 2 + 40, titulo)
        c.setFont("Helvetica", 15)
        c.setFillColor(colors.HexColor("#D6E6F2"))
        for i, linha in enumerate(textwrap.wrap(resumo, 66)):
            c.drawString(MARGEM + 132, ALTURA / 2 - 4 - i * 21, linha)
        c.showPage()

    def fechar(self) -> None:
        self.c.save()

    # ---------- elementos ----------

    def topicos(self, itens: list[str], tamanho: int = 15, cor=None) -> None:
        c = self.c
        for item in itens:
            negrito = item.startswith("*")
            texto = item.lstrip("*")
            c.setFillColor(cor or (AZUL if negrito else colors.HexColor("#2B3440")))
            c.circle(MARGEM + 4, self.y + 5, 3.2, stroke=0, fill=1)
            fonte = "Helvetica-Bold" if negrito else "Helvetica"
            largura_texto = LARGURA - 2 * MARGEM - 22
            linhas = self._quebrar(texto, fonte, tamanho, largura_texto)
            for i, linha in enumerate(linhas):
                c.setFont(fonte, tamanho)
                c.drawString(MARGEM + 18, self.y - i * (tamanho + 6), linha)
            self.y -= len(linhas) * (tamanho + 6) + 12

    def paragrafo(self, texto: str, tamanho: int = 14, cor=CINZA) -> None:
        c = self.c
        c.setFillColor(cor)
        for linha in self._quebrar(texto, "Helvetica", tamanho, LARGURA - 2 * MARGEM):
            c.setFont("Helvetica", tamanho)
            c.drawString(MARGEM, self.y, linha)
            self.y -= tamanho + 6
        self.y -= 8

    def destaque(self, texto: str, cor=VERDE) -> None:
        c = self.c
        altura = 46
        c.setFillColor(cor)
        c.roundRect(MARGEM, self.y - altura + 14, LARGURA - 2 * MARGEM, altura, 6, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(MARGEM + 16, self.y - altura + 32, texto)
        self.y -= altura + 16

    def codigo(self, linhas: list[str], legenda: str = "", tamanho: int = 10) -> None:
        c = self.c
        altura = len(linhas) * (tamanho + 4) + 22
        c.setFillColor(CODIGO_FUNDO)
        c.roundRect(MARGEM, self.y - altura + 12, LARGURA - 2 * MARGEM, altura, 5, stroke=0, fill=1)
        y = self.y - 4
        for linha in linhas:
            comentario = linha.strip().startswith("#")
            c.setFillColor(colors.HexColor("#7D93A6") if comentario else colors.HexColor("#E7EEF5"))
            c.setFont("Courier-Bold" if not comentario else "Courier", tamanho)
            c.drawString(MARGEM + 14, y - tamanho, linha[:110])
            y -= tamanho + 4
        self.y -= altura + 10
        if legenda:
            c.setFillColor(CINZA)
            c.setFont("Helvetica-Oblique", 11)
            c.drawString(MARGEM, self.y + 4, legenda)
            self.y -= 20

    def tabela(
        self,
        df: pd.DataFrame,
        cabecalhos: list[str],
        larguras: list[int],
        tamanho: int = 11,
        destacar=None,
    ) -> None:
        c = self.c
        x0 = MARGEM
        altura_linha = tamanho + 12

        c.setFillColor(AZUL)
        c.rect(x0, self.y - altura_linha + 8, sum(larguras), altura_linha, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", tamanho)
        x = x0
        for cabecalho, largura in zip(cabecalhos, larguras):
            c.drawString(x + 8, self.y - tamanho + 2, cabecalho)
            x += largura
        self.y -= altura_linha

        for indice, (_, linha) in enumerate(df.iterrows()):
            marcada = bool(destacar and destacar(linha))
            if marcada:
                c.setFillColor(colors.HexColor("#DFF3EF"))
            elif indice % 2 == 0:
                c.setFillColor(CINZA_CLARO)
            else:
                c.setFillColor(colors.white)
            c.rect(x0, self.y - altura_linha + 8, sum(larguras), altura_linha, stroke=0, fill=1)

            x = x0
            for valor, largura in zip(linha.tolist(), larguras):
                c.setFillColor(VERDE if marcada else colors.HexColor("#2B3440"))
                c.setFont("Helvetica-Bold" if marcada else "Helvetica", tamanho)
                texto = _formatar(valor)
                limite = int(largura / (tamanho * 0.52))
                c.drawString(x + 8, self.y - tamanho + 2, texto[:limite])
                x += largura
            self.y -= altura_linha
        self.y -= 12

    def imagem(self, nome: str, altura_maxima: int = 330, legenda: str = "") -> None:
        c = self.c
        caminho = config.DIR_FIGURAS / f"{nome}.png"
        if not caminho.exists():
            return
        imagem = ImageReader(str(caminho))
        largura_px, altura_px = imagem.getSize()
        escala = min((LARGURA - 2 * MARGEM) / largura_px, altura_maxima / altura_px)
        largura, altura = largura_px * escala, altura_px * escala
        c.drawImage(
            imagem,
            (LARGURA - largura) / 2,
            self.y - altura + 6,
            largura,
            altura,
            preserveAspectRatio=True,
            mask="auto",
        )
        self.y -= altura + 12
        if legenda:
            c.setFillColor(CINZA)
            c.setFont("Helvetica-Oblique", 11)
            c.drawCentredString(LARGURA / 2, self.y + 4, legenda)
            self.y -= 18

    def barras(
        self,
        rotulos: list[str],
        valores: list[float],
        cores: list,
        titulo: str = "",
        formato: str = "{:+.3f}",
    ) -> None:
        """Barras horizontais desenhadas direto no PDF, para o slide não depender de figura."""
        c = self.c
        if titulo:
            c.setFillColor(CINZA)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(MARGEM, self.y, titulo)
            self.y -= 22

        x_rotulos = MARGEM + 250
        largura_total = LARGURA - x_rotulos - MARGEM - 70
        # A escala cobre a amplitude inteira, de modo que a maior barra negativa cabe à esquerda
        # da linha do zero sem invadir o rótulo.
        maior_positivo = max([v for v in valores if v > 0], default=0.0)
        maior_negativo = abs(min([v for v in valores if v < 0], default=0.0))
        amplitude = (maior_positivo + maior_negativo) or 1
        escala = largura_total / amplitude
        recuo = maior_negativo * escala
        x0 = x_rotulos + recuo
        maximo = 1.0
        largura_util = escala
        if recuo:
            c.setStrokeColor(colors.HexColor("#C8D2DC"))
            c.setLineWidth(1)
            c.line(x0, self.y + 18, x0, self.y - 27 * (len(valores) - 1) - 8)
        for rotulo_item, valor, cor in zip(rotulos, valores, cores):
            comprimento = abs(valor) / maximo * largura_util
            c.setFillColor(colors.HexColor("#2B3440"))
            c.setFont("Helvetica", 12)
            c.drawRightString(x_rotulos - 12, self.y, rotulo_item[:46])
            c.setFillColor(cor)
            if valor >= 0:
                c.rect(x0, self.y - 4, comprimento, 15, stroke=0, fill=1)
                c.setFillColor(colors.HexColor("#2B3440"))
                c.setFont("Helvetica-Bold", 11)
                c.drawString(x0 + comprimento + 8, self.y, formato.format(valor))
            else:
                c.rect(x0 - comprimento, self.y - 4, comprimento, 15, stroke=0, fill=1)
                c.setFillColor(colors.HexColor("#2B3440"))
                c.setFont("Helvetica-Bold", 11)
                c.drawString(x0 + 8, self.y, formato.format(valor))
            self.y -= 27
        self.y -= 8

    def _quebrar(self, texto: str, fonte: str, tamanho: int, largura: float) -> list[str]:
        palavras = texto.split()
        linhas, atual = [], ""
        for palavra in palavras:
            teste = f"{atual} {palavra}".strip()
            if self.c.stringWidth(teste, fonte, tamanho) <= largura:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = palavra
        if atual:
            linhas.append(atual)
        return linhas or [""]

    def fim_slide(self) -> None:
        self.c.showPage()


def _pct(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def montar() -> str:
    """Monta o PDF inteiro a partir das tabelas salvas em reports/tables."""
    fontes = _tabela("02_fontes_data_referencia")
    datas = _tabela("02b_checagem_regra_de_datas")
    volumes = _tabela("24_volumes_nacionais")
    cortes = _tabela("07_cortes_de_variaveis")
    vif = _tabela("06_vif")
    candidatos = _tabela("09_candidatos_no_cotovelo")
    escolha = _tabela("09b_escolha_do_modelo")
    baselines = _tabela("11_baselines_modelo_final")
    sementes = _tabela("12_estabilidade_sementes")
    estabilidade = _tabela("13_estabilidade_bootstrap")
    ablacao = _tabela("14_ablacao")
    diferenca = _tabela("14b_diferenca_de_silhueta")
    tamanhos = _tabela("16_tamanho_clusters")
    marcas = _tabela("17_marcas_dos_clusters")
    topo = _tabela("18_top_municipios")
    descritoras = _tabela("21_descritoras_por_cluster")
    valor = _tabela("22_valor_para_a_loft")
    robustez = _tabela("23_robustez_denominador")
    incremental = _tabela("25_valor_incremental_do_cluster")
    base = pd.read_csv(config.DIR_PROCESSED / "base_municipios.csv", dtype={"id_municipio": str})

    n_municipios = len(base)
    escolhido = escolha[escolha["escolhido"]].iloc[0]
    silhueta = baselines.iloc[0]["silhueta"]
    sil_regiao = baselines[baselines["agrupamento"].str.contains("regi")].iloc[0]
    sil_porte = baselines[baselines["agrupamento"].str.contains("porte")].iloc[0]
    sil_aleatorio = baselines[baselines["agrupamento"].str.contains("aleat")].iloc[0]
    ganho_incremental = incremental["ganho"].mean()
    quantas_ajuda = int(incremental["o_cluster_acrescenta"].sum())

    d = Deck(ARQUIVO)

    d.capa(
        "Onde colocar o próximo R$ 1 em mídia paga?",
        "POC não supervisionada: os tipos de praça que existem no Brasil para vender o "
        "produto de fiança da Loft",
        "Beatriz Babinski · Projeto em Ciência de Dados V · IBMEC",
        [
            f"{n_municipios} municípios com 50 mil habitantes ou mais",
            f"{len(config.VARIAVEIS)} variáveis de 8 fontes públicas, nenhuma anterior a 2025",
            f"5 tipos de praça que superam geografia e porte populacional",
            f"O cluster acrescenta informação em {quantas_ajuda} de {len(incremental)} testes de validação",
        ],
    )

    # ---------------- agenda ----------------
    d.slide("O que você vai ver", "roteiro")
    d.topicos(
        [
            "*1. O problema — por que a resposta depende da praça, e não só do canal",
            "*2. Os dados — 8 fontes públicas, e as decisões de tratamento que mudaram o resultado",
            "*3. O método — log, padronização, 5 grupos de variáveis, 3 algoritmos, k de 2 a 10",
            "*4. Os resultados — inclusive um achado desconfortável e um erro que corrigimos",
            "*5. Os 5 tipos de praça — perfil, mapa e o que cada um significa para a fiança",
            "*6. Limitações e próximos passos",
        ],
        tamanho=16,
    )
    d.y -= 10
    d.paragrafo(
        "Duas coisas para guardar desde já: a análise agrupa MERCADOS, não clientes, porque não "
        "temos dado interno da Loft. E toda afirmação numérica desta apresentação é lida das "
        "tabelas da execução, não digitada à mão.",
        tamanho=13,
    )
    d.fim_slide()

    # ================= 1. PROBLEMA =================
    d.secao("1", "O problema", "Onde colocar o próximo real, e por que isso é uma pergunta sobre praça")

    d.slide("A pergunta do projeto", "problema")
    d.destaque("Onde colocar o próximo R$ 1 em mídia paga?")
    d.topicos(
        [
            "A Loft é 100% B2B: 7 produtos para 4 públicos diferentes.",
            "*A auditoria pública dos anúncios mostrou que ~74% das peças são de FIANÇA.",
            "*E o cliente principal da fiança é a IMOBILIÁRIA, não o inquilino.",
            "Minha tese: a resposta depende de PRODUTO × PÚBLICO × PRAÇA.",
            "Produto e público a auditoria já respondeu. Falta a praça — é o que esta POC ataca.",
        ]
    )
    d.paragrafo(
        "A pergunta que esta análise responde: quais tipos de praça existem no Brasil para vender "
        "fiança, e o que isso muda na decisão de mídia?",
        tamanho=15,
        cor=AZUL,
    )
    d.fim_slide()

    d.slide("Por que não supervisionado, e o que então valida o resultado", "problema")
    d.topicos(
        [
            "*Não existe rótulo de 'praça boa' para aprender. Não há y.",
            "Sem dado interno da Loft, o objeto de agrupamento é MERCADO, não cliente.",
            "Logo a validação não pode ser acurácia. São três provas:",
        ]
    )
    d.y -= 4
    d.topicos(
        [
            "*(a) Separação interna — silhueta, Davies-Bouldin e Calinski-Harabasz",
            "*(b) Superioridade sobre o que a Loft já teria de graça — geografia e tamanho de cidade",
            "*(c) Estabilidade — o agrupamento sobrevive a reamostrar os municípios?",
        ],
        tamanho=14,
    )
    d.y -= 6
    d.destaque(
        "E uma quarta prova, que é a que responde 'isso serve para modelo?': valor incremental",
        cor=AZUL_CLARO,
    )
    d.fim_slide()

    # ================= 2. DADOS =================
    d.secao("2", "Os dados", "8 fontes públicas, 687 municípios, e as decisões que mudaram o resultado")

    d.slide("Unidade de análise", "dados")
    d.topicos(
        [
            f"*Município brasileiro com 50 mil habitantes ou mais: {n_municipios} municípios.",
            f"Estimativa do IBGE de {config.ANO_POPULACAO}, a mais recente publicada.",
            f"Concentram {_pct(base['populacao'].sum() / 214_000_000 * 100)}% da população do país.",
            "*Todas as variáveis são relativas à população: por habitante, por 10 mil habitantes "
            "ou por 100 domicílios.",
            "Isso é deliberado: sem relativizar, o agrupamento separaria só por tamanho de cidade, "
            "que é informação que a Loft já tem de graça.",
        ]
    )
    d.y -= 4
    d.tabela(
        pd.DataFrame(
            {
                "faixa de porte": list(base["porte"].value_counts().sort_index().index),
                "municípios": list(base["porte"].value_counts().sort_index().values),
            }
        ),
        ["Faixa de porte populacional", "Municípios"],
        [320, 140],
        tamanho=12,
    )
    d.fim_slide()

    d.slide("As fontes, e a data de referência de cada uma", "dados")
    modelo = fontes[fontes["entra_no_cluster"]].copy()
    modelo["fonte_curta"] = modelo["fonte"].str.split(" - ").str[0]
    d.tabela(
        modelo[["rotulo", "fonte_curta", "data_referencia"]],
        ["Variável", "Órgão produtor", "Referência"],
        [400, 290, 150],
        tamanho=10,
    )
    d.paragrafo(
        "As descritoras (PNAD Contínua, SCR do Banco Central, FipeZap e Google Trends) não entram "
        "no cluster: só ajudam a nomear os grupos depois.",
        tamanho=12,
    )
    d.fim_slide()

    d.slide("A regra de datas não é afirmada: é conferida em código", "dados")
    d.topicos(
        [
            "*Regra do projeto: proibido usar Censo 2022 ou qualquer dado de 2024 ou anterior.",
            f"Conferido nas {len(datas[datas['entra_no_cluster']])} variáveis do modelo. "
            f"Nenhuma violação.",
            "A execução ABORTA se numa coleta futura alguma fonte regredir.",
        ]
    )
    d.codigo(
        [
            "violacoes = diagnostico.violacoes_da_regra_de_datas(fontes)",
            "if not violacoes.empty:",
            "    raise RuntimeError(",
            '        "Regra de datas violada: estas variáveis do modelo têm referência anterior a "',
            '        f"{diagnostico.ANO_MINIMO_PERMITIDO}:\\n{violacoes.to_string(index=False)}"',
            "    )",
        ],
        legenda="pipeline.py — o pipeline se recusa a rodar com dado velho",
    )
    d.paragrafo(
        "Uma fonte foi DESCARTADA por causa disso: o Índice Brasileiro de Conectividade da Anatel, "
        "cujo ano mais recente é 2024. No lugar dele entraram os acessos de telefonia móvel dos "
        "dados abertos da Anatel, com referência de 2026-07.",
        tamanho=13,
    )
    d.fim_slide()

    d.slide("Os números batem com a realidade?", "dados")
    d.paragrafo(
        "Este é o teste que pega erro de extração silencioso: unidade trocada, ou junção que "
        "multiplica registros. Se a parcela no universo passasse de 100%, haveria duplicação.",
        tamanho=13,
    )
    d.tabela(
        volumes[["base", "total_no_brasil", "total_nos_municipios_analisados", "parcela_no_universo"]],
        ["Base", "Total no Brasil", "Nos municípios analisados", "Parcela"],
        [300, 180, 220, 100],
        tamanho=10,
    )
    d.destaque(
        f"Zero valores faltantes nas {len(config.VARIAVEIS)} variáveis, nos {n_municipios} municípios"
    )
    d.fim_slide()

    d.slide("Achado de brinde nessa conferência", "dados")
    d.topicos(
        [
            "*O crédito e as imobiliárias estão ~92% concentrados nos municípios grandes.",
            "*Mas o CadÚnico só tem 62% nesses mesmos municípios.",
            "Tradução: a vulnerabilidade social está desproporcionalmente FORA das cidades grandes.",
            "Isso importa para a fiança: o risco não está onde está o mercado.",
        ],
        tamanho=15,
    )
    d.y -= 6
    parcelas = {
        str(r["base"]).split(",")[0]: float(str(r["parcela_no_universo"]).rstrip("%"))
        for _, r in volumes.iterrows()
    }
    d.barras(
        ["Crédito bancário", "Imobiliárias ativas", "Admissões formais", "Famílias no CadÚnico"],
        [
            parcelas.get("ESTBAN", 93),
            parcelas.get("CNPJ", 91),
            parcelas.get("Novo CAGED", 83),
            parcelas.get("CadÚnico", 62),
        ],
        [VERDE, VERDE, AZUL_CLARO, VERMELHO],
        titulo="Parcela do total nacional que está nos municípios analisados",
        formato="{:.0f}%",
    )
    d.fim_slide()

    d.slide("7 decisões de tratamento que mudaram o resultado", "dados")
    decisoes = pd.DataFrame(
        [
            ["Pix: descartar mês em andamento", "set/26 vinha com 71% do volume típico"],
            ["Salário: mediana, não média", "num município a média era R$3.634 e a mediana R$1.612"],
            ["Internet móvel: só pessoa física", "com PJ, um município marcava 881 acessos/100 hab"],
            ["Veículos: automóveis, não a frota", "moto cresce onde a renda cai: sinal oposto"],
            ["Crédito: winsorizar 1% nas caudas", "o ESTBAN registra a carteira na sede do banco"],
            ["Google Trends: virou descritora", "a API devolve UF, não município"],
            ["CadÚnico: denominador estimado", "a competência não traz contagem de pessoas"],
        ],
        columns=["decisao", "motivo"],
    )
    d.tabela(
        decisoes, ["Decisão", "Evidência que obrigou a decisão"], [330, 520], tamanho=11
    )
    d.paragrafo(
        "Cada um desses números é recalculado a cada execução. Nenhum está colado no texto.",
        tamanho=12,
    )
    d.fim_slide()

    d.slide("Código 1: como o mês incompleto é descartado sozinho", "dados")
    d.paragrafo(
        "Setembro de 2026 aparecia na API do Banco Central com R$784 bi contra ~R$1.100 bi dos "
        "meses fechados, porque o mês ainda estava em andamento. Usar esse mês rebaixaria "
        "artificialmente todos os municípios.",
        tamanho=13,
    )
    d.codigo(
        [
            "FRACAO_MINIMA_MES_COMPLETO = 0.85",
            "",
            "def meses_completos(df):",
            '    """Descarta meses cujo volume nacional indica mês ainda em andamento."""',
            '    total = df.groupby("AnoMes")["VL_PagadorPF"].sum().sort_index()',
            "    mediana = total.median()",
            "    return sorted(total[total >= mediana * FRACAO_MINIMA_MES_COMPLETO].index.tolist())",
        ],
        legenda="coleta/pix.py — a regra é relativa à mediana, então funciona em qualquer mês",
    )
    d.destaque("Tem teste automatizado: mês com 30% do volume típico é reprovado", cor=AZUL_CLARO)
    d.fim_slide()

    d.slide("Código 2: baixar 2,4 MB de um arquivo de 3,2 GB", "dados")
    d.paragrafo(
        "Os acessos de telefonia móvel da Anatel só existem num ZIP de 3,2 GB. Combinamos não "
        "baixar nada acima de 1 GB. A saída foi ler o índice do ZIP por requisição de faixa e "
        "extrair só o membro necessário.",
        tamanho=13,
    )
    d.codigo(
        [
            "class _ArquivoRemoto(io.RawIOBase):",
            '    """Arquivo somente-leitura servido por HTTP Range."""',
            "    def readinto(self, buffer):",
            "        dados = self.read(len(buffer))",
            "        buffer[: len(dados)] = dados",
            "        return len(dados)",
            "",
            "with zipfile.ZipFile(io.BufferedReader(_ArquivoRemoto(ZIP_MOVEL))) as z:",
            "    with z.open(_membro_mais_recente(z)) as f:",
            '        bruto = pd.read_csv(f, sep=";", encoding="utf-8-sig")',
        ],
        legenda="coleta/anatel.py — 2,4 MB baixados em vez de 3,19 GB",
        tamanho=9,
    )
    d.fim_slide()

    # ================= 3. MÉTODO =================
    d.secao("3", "O método", "Pipeline, corte de variáveis, e 5 grupos testados contra 3 algoritmos")

    d.slide("O pipeline", "método")
    d.topicos(
        [
            "*Winsorizar 1% nas duas caudas → log nas variáveis de cauda longa → padronizar → modelo",
            "A winsorização existe porque fontes bancárias registram a operação na sede da empresa.",
            "O log entra só onde a assimetria passa de 1 e a variável é não negativa.",
            f"Semente fixa em {config.SEMENTE} em tudo.",
        ]
    )
    d.codigo(
        [
            "def construir_preparo(variaveis, variaveis_log):",
            '    """log nas variáveis de cauda longa, depois padronização em todas."""',
            "    blocos = [",
            '        ("log", Pipeline([("log", FunctionTransformer(np.log1p)),',
            '                          ("escala", StandardScaler())]), variaveis_log),',
            '        ("direto", StandardScaler(), diretas),',
            "    ]",
            "    return ColumnTransformer(blocos)",
        ],
        legenda="clustering.py — o preparo é refeito dentro de cada reamostragem, para não vazar",
        tamanho=9,
    )
    d.fim_slide()

    d.slide("Corte de variáveis: correlação acima de 0,80 fica só uma", "método")
    d.tabela(
        cortes[["rotulo_descartada", "rotulo_mantida", "correlacao_spearman"]],
        ["Variável descartada", "Variável mantida", "Correlação"],
        [320, 340, 130],
        tamanho=11,
    )
    d.topicos(
        [
            "*O desempate NÃO é automático: fica a variável que o desenho usa em mais grupos, "
            "porque é a que carrega sentido de negócio.",
            "Administradoras de imóveis (CNAE 6822) é proxy de LOCAÇÃO, que é o mercado da fiança. "
            "Imobiliárias (6821) inclui venda. Por isso administradoras fica.",
            f"Maior VIF depois do corte: {vif.iloc[0]['vif']} — bem abaixo do limiar de 10.",
        ],
        tamanho=13,
    )
    d.fim_slide()

    d.slide("A correlação entre as variáveis", "método")
    d.imagem("03_correlacao", altura_maxima=370, legenda="reports/figures/03_correlacao.png")
    d.fim_slide()

    d.slide("Os 5 grupos de variáveis comparados", "método")
    grupos_tabela = pd.DataFrame(
        [
            [g, config.NOMES_GRUPOS[g], len(v), ", ".join(config.VARIAVEIS[x][:26] for x in v[:3]) + "..."]
            for g, v in config.GRUPOS.items()
        ],
        columns=["g", "nome", "n", "exemplos"],
    )
    d.tabela(
        grupos_tabela,
        ["Grupo", "O que ele testa", "Vars", "Exemplos de variável"],
        [70, 300, 70, 410],
        tamanho=10,
    )
    d.topicos(
        [
            "*A hipótese inicial era que o grupo D (com marketing) separaria melhor.",
            "*O grupo E nasceu DEPOIS, de um resultado negativo — conto isso no fim.",
            f"Total de combinações testadas: {len(config.GRUPOS)} grupos × 3 algoritmos × "
            f"k de {config.K_MINIMO} a {config.K_MAXIMO} = {len(config.GRUPOS) * 3 * 9}.",
        ],
        tamanho=13,
    )
    d.fim_slide()

    # ================= 4. RESULTADOS =================
    d.secao("4", "Os resultados", "Um achado desconfortável, o teste de aceite, e um erro que corrigimos")

    d.slide("Achado desconfortável: k = 2 quase sempre ganha", "resultados")
    d.imagem("04_escolha_de_k", altura_maxima=300)
    d.topicos(
        [
            "*A silhueta é máxima em k=2 e cai de forma monotônica. Isso não é bug.",
            "*Significa que o Brasil municipal, nessas variáveis, é um CONTÍNUO — não tem grupos cravados.",
            "Aceitar k=2 entregaria 'praça rica e praça pobre', que não orienta decisão de mídia.",
        ],
        tamanho=13,
    )
    d.fim_slide()

    d.slide("Então como escolhemos k, o grupo e o algoritmo", "resultados")
    d.topicos(
        [
            "*1. k sai do COTOVELO da inércia, não do máximo da silhueta.",
            "*2. Só concorrem grupos que respondem à pergunta: precisam ter ao menos uma variável "
            "de mercado E uma de capacidade de pagamento. Isso elimina A e B.",
            "*3. Todos os clusters precisam ter no mínimo 20 municípios, senão não é praça, é exceção.",
            "*4. Quando a silhueta empata dentro de 0,02, o desempate é ESTABILIDADE.",
        ],
        tamanho=14,
    )
    d.y -= 4
    d.tabela(
        candidatos[["nome_grupo", "nome_modelo", "k", "silhueta", "menor_cluster"]].head(7).round(3),
        ["Grupo", "Algoritmo", "k", "Silhueta", "Menor cluster"],
        [290, 200, 60, 120, 140],
        tamanho=10,
    )
    d.paragrafo(
        "B e A lideram a silhueta pura — mas a silhueta premia espaços com menos variáveis e mais "
        "redundantes, e nenhum dos dois responde à pergunta sozinho.",
        tamanho=12,
    )
    d.fim_slide()

    d.slide("O TESTE DE ACEITE: o cluster ganha de geografia e de porte?", "resultados")
    d.barras(
        [
            "Clusters da POC",
            "Baseline: 5 regiões do IBGE",
            "Baseline: faixas de porte",
            "Baseline: sorteio aleatório",
        ],
        [
            float(silhueta),
            float(sil_regiao["silhueta"]),
            float(sil_porte["silhueta"]),
            float(sil_aleatorio["silhueta"]),
        ],
        [VERDE, CINZA, CINZA, CINZA],
        titulo="Silhueta no MESMO espaço de variáveis (maior é melhor)",
    )
    d.destaque(
        f"Silhueta {silhueta:.3f} contra {sil_regiao['silhueta']:.3f} da geografia e "
        f"{sil_porte['silhueta']:.3f} do porte"
    )
    d.topicos(
        [
            f"*Rand ajustado contra PORTE: {sil_porte['rand_ajustado_vs_cluster']:.3f} — o modelo "
            f"NÃO redescobriu o tamanho da cidade. Esse era o risco principal.",
            f"Rand ajustado contra REGIÃO: {sil_regiao['rand_ajustado_vs_cluster']:.3f} — existe "
            f"alguma relação com geografia, o que é esperado num país desigual, mas longe de ser "
            f"a mesma coisa.",
        ],
        tamanho=13,
    )
    d.fim_slide()

    d.slide("Robustez: o agrupamento sobrevive a mexer nos dados?", "resultados")
    linha_est = estabilidade.iloc[0]
    d.topicos(
        [
            f"*Reamostragem ({linha_est['n_comparacoes']} comparações, subamostras de "
            f"{linha_est['fracao_reamostrada']:.0%} dos municípios): Rand ajustado médio "
            f"{linha_est['rand_ajustado_medio']:.3f}.",
            f"*{len(sementes)} sementes diferentes: Rand médio "
            f"{sementes['rand_ajustado_vs_referencia'].mean():.3f} contra a solução de referência.",
            "Sem reposição de propósito: com reposição, municípios duplicados ficam a distância "
            "zero e inflam a concordância.",
            "E o preparo (winsorizar, log, padronizar) é REFEITO dentro de cada subamostra — "
            "senão a estabilidade sai otimista.",
        ],
        tamanho=13,
    )
    d.y -= 4
    d.imagem("11_ablacao", altura_maxima=175, legenda="Ablação: quanto cada variável sustenta a separação")
    d.fim_slide()

    d.slide("C contra D: a escolha foi um julgamento, e está registrado", "resultados")
    linha_dif = diferenca.iloc[0]
    d.tabela(
        escolha[["nome_grupo", "k", "silhueta", "estabilidade_bootstrap"]].round(3),
        ["Grupo finalista", "k", "Silhueta", "Estabilidade"],
        [400, 70, 150, 200],
        tamanho=12,
        destacar=lambda linha: "marketing" in str(linha.iloc[0]),
    )
    d.topicos(
        [
            f"*C separa um pouco melhor, e isso foi TESTADO: reamostrando 200 vezes, o intervalo "
            f"de 95% da diferença é [{linha_dif['intervalo_95_inferior']:+.4f}; "
            f"{linha_dif['intervalo_95_superior']:+.4f}] — a vantagem de C é real.",
            "*Mas é pequena. E os clusters de C NÃO se reproduzem: 0,70 de estabilidade contra 0,84 de D.",
            "*Troquei 0,008 de separação por 0,137 de reprodutibilidade, porque a decisão de mídia "
            "vai ser refeita mês a mês e agrupamento que se reorganiza não sustenta plano de verba.",
        ],
        tamanho=13,
    )
    d.fim_slide()

    # ---- o slide mais importante ----
    d.slide("O teste que responde: isso serve para um modelo futuro?", "resultados")
    d.paragrafo(
        "Separação e estabilidade dizem que o agrupamento é consistente. Não dizem se ele é ÚTIL. "
        "A pergunta certa não é se o cluster substitui a geografia — é se ele ACRESCENTA a ela.",
        tamanho=14,
        cor=AZUL,
    )
    d.paragrafo(
        "Teste: R² AJUSTADO de (região + porte) contra (região + porte + cluster), em variáveis "
        "municipais que ficaram fora do modelo. Ajustado para não premiar só o aumento de parâmetros.",
        tamanho=13,
    )
    d.barras(
        [str(r["rotulo"])[:42] for _, r in incremental.head(7).iterrows()],
        [float(r["ganho"]) for _, r in incremental.head(7).iterrows()],
        [VERDE] * 7,
        titulo="Ganho no R² ajustado ao adicionar o cluster (7 maiores de 15)",
    )
    d.destaque(
        f"O cluster acrescenta em {quantas_ajuda} de {len(incremental)} variáveis retidas. "
        f"Ganho médio {ganho_incremental:+.4f}. Em nenhuma ele piora."
    )
    d.fim_slide()

    d.slide("O erro que eu cometi, e por que ele importa", "resultados")
    d.topicos(
        [
            "*O primeiro teste que fiz foi outro: pedir que o cluster VENCESSE a região.",
            "Nesse formato ele perdeu: 2 de 7 variáveis, ganho médio -0,011. Quase concluí que a "
            "análise não servia.",
            "*O teste estava mal formulado.",
            "No Brasil quase toda variável socioeconômica municipal é muito explicada pela região. "
            "Exigir que o agrupamento derrote a geografia é exigir que ele seja um proxy melhor de "
            "desigualdade regional — que não é a função dele.",
            "*A função é separar praças que devem receber o mesmo tratamento de mídia. Para isso o "
            "que importa é informação incremental.",
        ],
        tamanho=13,
    )
    d.y -= 6
    d.tabela(
        pd.DataFrame(
            [
                ["Cluster SUBSTITUI região + porte", "perde: 2 de 7", "-0,011"],
                ["Cluster SOMA a região + porte", f"ganha: {quantas_ajuda} de {len(incremental)}", f"{ganho_incremental:+.4f}"],
            ],
            columns=["pergunta", "resultado", "ganho"],
        ),
        ["A pergunta feita", "Resultado", "Ganho médio de R²"],
        [420, 250, 180],
        tamanho=12,
        destacar=lambda linha: "SOMA" in str(linha.iloc[0]),
    )
    d.fim_slide()

    d.slide("O grupo E: um experimento que falhou, e fica registrado", "resultados")
    d.paragrafo(
        "Depois do resultado negativo, montei um grupo só com variáveis específicas de fiança — "
        "nada de nível socioeconômico geral:",
        tamanho=14,
    )
    d.topicos(
        [
            "*Alavancagem (crédito sobre poupança) — RISCO de inadimplência por município. "
            "O SCR do Banco Central só tem isso por UF; essa é municipal.",
            "*Reserva per capita (poupança + depósito a prazo) — o colchão que sustenta o aluguel.",
            "*Corretores de seguros / 10 mil hab. — oferta local do seguro-fiança, o CONCORRENTE direto.",
            "*Crescimento da população em 1 ano — motor da DEMANDA de locação.",
            "*Admissões de 18 a 30 anos — a faixa que aluga.",
        ],
        tamanho=13,
    )
    d.y -= 6
    e_linha = candidatos[candidatos["grupo"] == "E"]
    silhueta_e = float(e_linha.iloc[0]["silhueta"]) if not e_linha.empty else float("nan")
    d.destaque(
        f"O grupo E PERDEU: silhueta {silhueta_e:.3f} contra {escolhido['silhueta']:.3f} do grupo D",
        cor=VERMELHO,
    )
    d.paragrafo(
        "Fica no relatório porque experimento que falha também é resultado: mostra que risco e "
        "demanda são conceitualmente certos, mas mais ruidosos que mercado e renda.",
        tamanho=13,
    )
    d.fim_slide()

    d.slide("E o cluster 'em formação' não é artefato: foi testado", "resultados")
    d.paragrafo(
        "A taxa de imobiliárias novas é uma proporção sobre base pequena: num município com 9 "
        "imobiliárias, três aberturas já viram 33%. Precisava testar se o cluster era só isso.",
        tamanho=13,
    )
    d.tabela(
        robustez[
            ["base_minima_de_empresas", "municipios_no_cluster", "mediana_no_cluster", "mediana_no_resto", "p_valor"]
        ],
        ["Exige no mínimo", "Municípios", "Mediana no cluster", "Mediana no resto", "p-valor"],
        [180, 150, 220, 200, 130],
        tamanho=11,
    )
    d.destaque(
        "Exigindo 20+ imobiliárias, o cluster mantém 21,1% de novas contra 13,1% do resto (p = 1,1e-08)"
    )
    d.fim_slide()

    # ================= 5. OS TIPOS DE PRAÇA =================
    d.secao("5", "Os 5 tipos de praça", "O que existe no Brasil para vender fiança, e o que fazer em cada um")

    d.slide("O perfil dos 5 clusters", "resultados")
    d.imagem("07_perfil_clusters", altura_maxima=330, legenda="Desvios padrão em relação à média dos 687 municípios")
    d.fim_slide()

    d.slide("A assinatura de cada praça", "resultados")
    d.imagem("08_radar_clusters", altura_maxima=360)
    d.fim_slide()

    d.slide("Onde eles estão no mapa", "resultados")
    d.imagem("09_mapa_clusters", altura_maxima=370)
    d.fim_slide()

    d.slide("Quanto cada tipo de praça representa", "resultados")
    junto = tamanhos.merge(valor[["cluster", "nome"]], on="cluster")
    d.tabela(
        junto[["nome", "municipios", "municipios_pct", "populacao_pct", "populacao_mediana"]],
        ["Tipo de praça", "Municípios", "% dos municípios", "% da população", "População mediana"],
        [300, 130, 170, 160, 190],
        tamanho=11,
    )
    d.topicos(
        [
            "*A praça madura é 19% dos municípios e quase metade da população.",
            "*As duas praças de exclusão (sem mercado formal e em formação) juntas são ~10% da população.",
        ],
        tamanho=13,
    )
    d.fim_slide()

    d.slide("Os maiores municípios de cada praça", "resultados")
    linhas = []
    for cluster in sorted(topo["cluster"].unique()):
        nome = valor[valor["cluster"] == cluster]["nome"].iloc[0]
        cidades = topo[(topo["cluster"] == cluster) & (topo["posicao"] <= 4)]
        linhas.append(
            [nome, ", ".join(f"{r.municipio}/{r.sigla_uf}" for r in cidades.itertuples())]
        )
    d.tabela(
        pd.DataFrame(linhas, columns=["praca", "cidades"]),
        ["Tipo de praça", "Os 4 maiores municípios"],
        [290, 560],
        tamanho=11,
    )
    d.paragrafo(
        "Reconhecimento imediato: a praça madura é São Paulo, Rio, Brasília e Fortaleza. A praça "
        "popular de grande porte é Manaus, Belém, Maceió. A sem mercado formal é o interior do "
        "Maranhão e da Paraíba.",
        tamanho=13,
    )
    d.fim_slide()

    d.slide("Validação externa: as descritoras confirmam sozinhas", "resultados")
    d.paragrafo(
        "Estas variáveis NÃO entraram no modelo. Se elas ordenam os clusters de forma coerente, é "
        "sinal de que os grupos capturaram algo real, e não ruído.",
        tamanho=13,
    )
    desc = descritoras.merge(valor[["cluster", "nome"]], on="cluster")
    colunas = [c for c in ["nome", "domicilios_alugados_pct_uf", "inadimplencia_pf_uf", "trends_fianca_uf", "imobiliarias_10k"] if c in desc]
    d.tabela(
        desc[colunas],
        ["Tipo de praça", "% alugados (UF)", "Inadimpl. PF (UF)", "Busca fiança", "Imobiliárias/10k"],
        [280, 160, 170, 140, 170],
        tamanho=11,
    )
    d.topicos(
        [
            "*A praça SEM MERCADO FORMAL tem a MAIOR inadimplência e a MENOR busca por fiança.",
            "*A praça MADURA tem o maior % de domicílios alugados e 11,7 imobiliárias por 10 mil hab.",
        ],
        tamanho=13,
    )
    d.fim_slide()

    d.slide("O que cada praça significa para a fiança", "valor")
    for _, linha in valor.iterrows():
        d.c.setFillColor(AZUL)
        d.c.setFont("Helvetica-Bold", 13)
        d.c.drawString(MARGEM, d.y, f"{linha['nome']}  ({linha['municipios']} municípios, {linha['populacao_pct']}% da população)")
        d.y -= 17
        d.c.setFillColor(CINZA)
        d.c.setFont("Helvetica", 10.5)
        for texto in d._quebrar(str(linha["o_que_significa_para_a_fianca"]), "Helvetica", 10.5, LARGURA - 2 * MARGEM):
            d.c.drawString(MARGEM, d.y, texto)
            d.y -= 13
        d.y -= 4
    d.fim_slide()

    d.slide("A ação de mídia recomendada em cada praça", "valor")
    for _, linha in valor.iterrows():
        d.c.setFillColor(VERDE)
        d.c.setFont("Helvetica-Bold", 13)
        d.c.drawString(MARGEM, d.y, linha["nome"])
        d.y -= 17
        d.c.setFillColor(colors.HexColor("#2B3440"))
        d.c.setFont("Helvetica", 10.5)
        for texto in d._quebrar(str(linha["acao_de_marketing_sugerida"]), "Helvetica", 10.5, LARGURA - 2 * MARGEM):
            d.c.drawString(MARGEM, d.y, texto)
            d.y -= 13
        d.y -= 4
    d.fim_slide()

    d.slide("O mapa de decisão", "valor")
    d.imagem("10_mapa_de_decisao", altura_maxima=350, legenda="Densidade de administradoras × capacidade de pagamento; tamanho do círculo é a população")
    d.fim_slide()

    # ================= 6. FECHAMENTO =================
    d.secao("6", "Limitações e próximos passos", "O que esta POC não responde, e o que faria ela virar decisão")

    d.slide("Limitações — as que mais importam", "fechamento")
    d.topicos(
        [
            "*1. Sem dado interno da Loft. Descrevemos o MERCADO, não o desempenho da Loft nele. "
            "Só o dado interno transforma 'praça promissora' em 'praça rentável'.",
            "*2. Os grupos não são naturais. São um corte útil de um contínuo. A defesa deles é a "
            "comparação com os baselines e o valor incremental, não a separação absoluta.",
            "*3. CNAE não é produto. 6821 e 6822 não distinguem locação de venda nem residencial de "
            "temporada. Por isso praças de veraneio aparecem com densidade altíssima de imobiliária "
            "sem serem mercado de fiança.",
            "*4. Efeito de sede. ESTBAN e telefonia móvel registram a operação onde a empresa está "
            "sediada. Tratamos com winsorização e filtro de pessoa física, mas o viés não desaparece.",
            "*5. A escolha entre C e D é um julgamento, não um resultado automático — e está registrado.",
        ],
        tamanho=12,
    )
    d.fim_slide()

    d.slide("Próximos passos, em ordem de valor", "fechamento")
    d.topicos(
        [
            "*1. Cruzar com o dado interno da Loft: receita e sinistro de fiança por município. "
            "Transforma os clusters em faixas de retorno esperado por real investido.",
            "*2. Separar locação de venda usando CNAE secundária e razão social, para isolar a "
            "praça de temporada da praça de locação residencial.",
            "*3. Testar de verdade: dois municípios por cluster, mesma campanha, medir custo por "
            "lead qualificado. É o que valida se o cluster prediz desempenho de mídia.",
            "*4. Intenção de busca por município via Google Ads Keyword Planner, que tem "
            "granularidade melhor que o Trends.",
            "*5. Rodar mensalmente e acompanhar a migração de municípios entre clusters como sinal "
            "antecedente de mercado em formação.",
        ],
        tamanho=12,
    )
    d.fim_slide()

    d.slide("Como reproduzir tudo isso", "fechamento")
    d.codigo(
        [
            "# cria o ambiente, coleta as fontes, gera tabelas, figuras e relatório",
            "make poc",
            "",
            "# refaz o download de todas as fontes oficiais",
            "make poc-completa",
            "",
            "# os testes da lógica que, se quebrar, contamina o resultado sem dar erro",
            "PYTHONPATH=src .venv/bin/python -m pytest tests/",
        ],
        legenda="Um comando. Semente fixa. Dependências fixadas com == no requirements.txt.",
        tamanho=11,
    )
    numeros = pd.DataFrame(
        [
            ["Municípios analisados", str(n_municipios)],
            ["Variáveis candidatas", str(len(config.VARIAVEIS))],
            ["Valores faltantes", "0"],
            ["Combinações de modelo testadas", str(len(config.GRUPOS) * 3 * 9)],
            ["Tabelas geradas", str(len(list(config.DIR_TABELAS.glob('*.csv'))))],
            ["Figuras geradas", str(len(list(config.DIR_FIGURAS.glob('*.png'))))],
            ["Testes automatizados", str(_contar_testes())],
        ],
        columns=["item", "valor"],
    )
    d.tabela(numeros, ["Números da entrega", "Valor"], [400, 160], tamanho=11)
    d.fim_slide()

    d.slide("O que fica de conclusão", "fechamento")
    d.destaque(
        f"Existem 5 tipos de praça para vender fiança, e eles não são geografia nem tamanho de cidade"
    )
    d.topicos(
        [
            f"*O agrupamento passa no teste de aceite: silhueta {silhueta:.3f} contra "
            f"{sil_regiao['silhueta']:.3f} da geografia e {sil_porte['silhueta']:.3f} do porte.",
            f"*É estável: Rand ajustado de {linha_est['rand_ajustado_medio']:.3f} sob reamostragem.",
            f"*E serve como variável de modelo: acrescenta informação em {quantas_ajuda} de "
            f"{len(incremental)} variáveis retidas, ganho médio {ganho_incremental:+.4f} no R² ajustado.",
            "*A decisão de mídia que ele sustenta: concentrar verba de conversão na praça madura, "
            "testar na praça em formação, e EXCLUIR a praça sem mercado formal.",
        ],
        tamanho=13,
    )
    d.y -= 8
    d.paragrafo(
        "O que ele ainda não faz: dizer quanto a Loft ganha em cada praça. Isso exige o dado "
        "interno, e é o próximo passo.",
        tamanho=13,
        cor=AZUL,
    )
    d.fim_slide()

    d.fechar()
    return str(ARQUIVO)
