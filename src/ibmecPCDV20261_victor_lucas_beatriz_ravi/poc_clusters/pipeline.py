"""Roda a POC inteira: coleta, estatística, modelos, baselines, robustez e perfil."""

from __future__ import annotations

import time

import pandas as pd

from . import (
    avaliacao,
    clustering,
    config,
    descritiva,
    diagnostico,
    features,
    graficos,
    perfil,
    relatorio,
)
from .io_utils import tabela_fontes

MINIMO_POR_CLUSTER = 20
# Diferença de silhueta abaixo disso é ruído, e o desempate passa a ser estabilidade.
DIFERENCA_IRRELEVANTE = 0.02
VARIAVEIS_MERCADO = ("administradoras_10k", "imobiliarias_10k", "imobiliarias_novas_pct")
VARIAVEIS_PAGAMENTO = (
    "pix_pf_por_hab",
    "salario_admissao",
    "cadunico_pct",
    "credito_per_capita",
    "veiculos_por_hab",
    "reserva_per_capita",
    "alavancagem",
)


def _salvar_tabela(df: pd.DataFrame, nome: str) -> None:
    df.to_csv(config.DIR_TABELAS / f"{nome}.csv", index=False)


def _responde_a_pergunta(variaveis: list[str]) -> bool:
    """Para dizer onde vender fiança o grupo precisa de mercado e de capacidade de pagamento."""
    return any(v in variaveis for v in VARIAVEIS_MERCADO) and any(
        v in variaveis for v in VARIAVEIS_PAGAMENTO
    )


def _escolher_configuracao(
    base: pd.DataFrame, grupos: dict[str, list[str]], candidatos: pd.DataFrame
) -> tuple[str, str, int, pd.DataFrame]:
    """Escolhe grupo, modelo e k: maior silhueta entre os grupos que respondem à pergunta,
    e estabilidade no bootstrap como desempate quando a silhueta empata."""
    elegiveis = candidatos[
        candidatos["grupo"].map(lambda g: _responde_a_pergunta(grupos[g]))
    ].copy()
    if elegiveis.empty:
        elegiveis = candidatos.copy()

    melhor_silhueta = float(elegiveis["silhueta"].max())
    empatados = elegiveis[
        elegiveis["silhueta"] >= melhor_silhueta - DIFERENCA_IRRELEVANTE
    ].copy()

    estabilidades = []
    for _, linha in empatados.iterrows():
        boot = avaliacao.estabilidade_bootstrap(
            base, grupos[linha["grupo"]], str(linha["modelo"]), int(linha["k"]), n_bootstrap=60
        )
        estabilidades.append(float(boot.iloc[0]["rand_ajustado_medio"]))
    empatados["estabilidade_bootstrap"] = estabilidades
    empatados = empatados.sort_values(
        ["estabilidade_bootstrap", "silhueta"], ascending=False
    ).reset_index(drop=True)

    escolha = empatados[
        ["grupo", "nome_grupo", "nome_modelo", "k", "silhueta", "estabilidade_bootstrap", "menor_cluster"]
    ].copy()
    escolha["responde_a_pergunta"] = True
    escolha["escolhido"] = [True] + [False] * (len(escolha) - 1)

    vencedor = empatados.iloc[0]
    return str(vencedor["grupo"]), str(vencedor["modelo"]), int(vencedor["k"]), escolha


def executar(forcar_download: bool = False, k_maximo: int = config.K_MAXIMO) -> dict:
    inicio = time.time()
    passos: dict[str, object] = {}

    print("[1/8] coletando e montando a base municipal")
    base = features.montar(forcar_download)
    features.salvar(base)
    variaveis = list(config.VARIAVEIS)
    _salvar_tabela(features.relatorio_cobertura(base), "01_cobertura_variaveis")
    fontes = tabela_fontes()
    _salvar_tabela(fontes, "02_fontes_data_referencia")

    checagem_datas = diagnostico.verificar_regra_de_datas(fontes)
    _salvar_tabela(checagem_datas, "02b_checagem_regra_de_datas")
    violacoes = diagnostico.violacoes_da_regra_de_datas(fontes)
    if not violacoes.empty:
        raise RuntimeError(
            "Regra de datas violada: estas variáveis do modelo têm referência anterior a "
            f"{diagnostico.ANO_MINIMO_PERMITIDO}:\n{violacoes.to_string(index=False)}"
        )

    print("[2/8] estatística descritiva")
    descritivas = descritiva.tabela_descritiva(base, variaveis)
    _salvar_tabela(descritivas, "03_estatistica_descritiva")
    graficos.histogramas(base, variaveis)
    graficos.boxplots(base, variaveis)

    print("[3/8] winsorização, correlação, VIF e corte de variáveis")
    tratada, registro_winsor = descritiva.winsorizar(base, variaveis)
    _salvar_tabela(registro_winsor, "04_winsorizacao")
    correlacao = descritiva.matriz_correlacao(tratada, variaveis)
    correlacao.round(3).to_csv(config.DIR_TABELAS / "05_correlacao_spearman.csv")
    graficos.heatmap_correlacao(correlacao)
    vif = descritiva.tabela_vif(tratada, variaveis)
    _salvar_tabela(vif, "06_vif")
    mantidas, decisoes = descritiva.decidir_cortes(tratada, variaveis)
    _salvar_tabela(decisoes, "07_cortes_de_variaveis")
    grupos = {g: [v for v in vs if v in mantidas] for g, vs in config.GRUPOS.items()}

    print("[4/8] varrendo k de 2 a %d nos 4 grupos e 3 modelos" % k_maximo)
    varredura = clustering.varrer_k(base, grupos, k_maximo=k_maximo)
    _salvar_tabela(varredura, "08_varredura_k")
    graficos.curvas_k(varredura)
    graficos.comparacao_modelos(varredura)

    print("[5/8] escolhendo configuração e comparando com os baselines")
    cotovelos = {g: avaliacao.cotovelo(varredura, g) for g in grupos}
    candidatos = varredura[
        varredura.apply(lambda r: r["k"] == cotovelos[r["grupo"]], axis=1)
        & (varredura["menor_cluster"] >= MINIMO_POR_CLUSTER)
    ].copy()
    candidatos["k_cotovelo"] = candidatos["grupo"].map(cotovelos)
    candidatos = candidatos.sort_values("silhueta", ascending=False).reset_index(drop=True)
    _salvar_tabela(candidatos, "09_candidatos_no_cotovelo")

    grupo_final, modelo_final, k_final, escolha = _escolher_configuracao(base, grupos, candidatos)
    variaveis_finais = grupos[grupo_final]
    _salvar_tabela(escolha, "09b_escolha_do_modelo")

    comparacoes = []
    for grupo, variaveis_grupo in grupos.items():
        matriz, _ = clustering.preparar_matriz(base, variaveis_grupo)
        rotulos = clustering.rotular(matriz, "kmeans", cotovelos[grupo])
        tabela = avaliacao.comparar_baselines(base, variaveis_grupo, rotulos)
        tabela.insert(0, "grupo", grupo)
        tabela.insert(1, "nome_grupo", config.NOMES_GRUPOS[grupo])
        tabela.insert(2, "k", cotovelos[grupo])
        comparacoes.append(tabela)
    comparacao_baselines = pd.concat(comparacoes, ignore_index=True)
    _salvar_tabela(comparacao_baselines, "10_baselines_por_grupo")

    matriz_final, variaveis_log = clustering.preparar_matriz(base, variaveis_finais)
    rotulos_finais = clustering.rotular(matriz_final, modelo_final, k_final)
    comparacao_final = avaliacao.comparar_baselines(base, variaveis_finais, rotulos_finais)
    _salvar_tabela(comparacao_final, "11_baselines_modelo_final")
    graficos.grafico_baselines(comparacao_final)

    print("[6/8] robustez: sementes, bootstrap e ablação")
    sementes = avaliacao.estabilidade_sementes(base, variaveis_finais, modelo_final, k_final)
    _salvar_tabela(sementes, "12_estabilidade_sementes")
    bootstrap = avaliacao.estabilidade_bootstrap(base, variaveis_finais, modelo_final, k_final)
    _salvar_tabela(bootstrap, "13_estabilidade_bootstrap")
    tabela_ablacao = avaliacao.ablacao(base, variaveis_finais, modelo_final, k_final)
    _salvar_tabela(tabela_ablacao, "14_ablacao")
    graficos.ablacao(tabela_ablacao)

    concorrentes = [
        (str(linha["grupo"]), grupos[str(linha["grupo"])], str(modelo_final), int(linha["k"]))
        for _, linha in escolha.iterrows()
    ]
    diferenca_silhueta = avaliacao.diferenca_silhueta(base, concorrentes)
    _salvar_tabela(diferenca_silhueta, "14b_diferenca_de_silhueta")

    print("[7/8] perfil dos clusters e leitura para a Loft")
    base["cluster"] = rotulos_finais
    perfil_z = perfil.perfil_padronizado(base, variaveis_finais)
    nomes = perfil.nomear(perfil_z)
    base["nome_cluster"] = base["cluster"].map(nomes)
    features.salvar(base)

    perfil_z.to_csv(config.DIR_TABELAS / "15_perfil_padronizado.csv")
    tamanhos = perfil.tamanho_clusters(base)
    _salvar_tabela(tamanhos, "16_tamanho_clusters")
    marcas = perfil.descricao_variaveis_chave(perfil_z, nomes)
    _salvar_tabela(marcas, "17_marcas_dos_clusters")
    _salvar_tabela(perfil.top_municipios(base), "18_top_municipios")
    _salvar_tabela(perfil.composicao_geografica(base), "19_composicao_regiao")
    _salvar_tabela(perfil.composicao_porte(base), "20_composicao_porte")
    descritoras = perfil.media_por_cluster(
        base, config.DESCRITORAS + ["populacao", "imobiliarias_10k", "veiculos_por_hab"]
    )
    _salvar_tabela(descritoras, "21_descritoras_por_cluster")
    valor = perfil.tabela_valor_loft(perfil_z, nomes, tamanhos)
    _salvar_tabela(valor, "22_valor_para_a_loft")
    incremental = avaliacao.valor_incremental(base, variaveis_finais)
    _salvar_tabela(incremental, "25_valor_incremental_do_cluster")
    robustez_denominador = diagnostico.robustez_denominador(base)
    _salvar_tabela(robustez_denominador, "23_robustez_denominador")
    _salvar_tabela(diagnostico.tabela_volumes(base), "24_volumes_nacionais")

    graficos.heatmap_perfil(perfil_z, nomes)
    graficos.radar(perfil_z, nomes)
    graficos.dispersao_decisao(base, nomes)
    mapa_ok = graficos.mapa(base, nomes)

    print("[8/8] escrevendo o relatório")
    passos.update(
        base=base,
        grupos=grupos,
        cotovelos=cotovelos,
        grupo_final=grupo_final,
        modelo_final=modelo_final,
        k_final=k_final,
        variaveis_finais=variaveis_finais,
        variaveis_log=variaveis_log,
        nomes=nomes,
        descritivas=descritivas,
        registro_winsor=registro_winsor,
        decisoes=decisoes,
        varredura=varredura,
        candidatos=candidatos,
        escolha=escolha,
        comparacao_baselines=comparacao_baselines,
        comparacao_final=comparacao_final,
        sementes=sementes,
        bootstrap=bootstrap,
        ablacao=tabela_ablacao,
        diferenca_silhueta=diferenca_silhueta,
        robustez_denominador=robustez_denominador,
        incremental=incremental,
        perfil_z=perfil_z,
        descricao_marcas=marcas,
        tamanhos=tamanhos,
        valor=valor,
        descritoras=descritoras,
        mapa_ok=mapa_ok,
        fontes=fontes,
        checagem_datas=checagem_datas,
        vif=vif,
    )
    relatorio.escrever(passos)
    passos["duracao_minutos"] = round((time.time() - inicio) / 60, 1)
    print(f"concluído em {passos['duracao_minutos']} minutos")
    return passos
