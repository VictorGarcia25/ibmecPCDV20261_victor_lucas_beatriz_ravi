"""Testes da lógica que, se quebrar, contamina o resultado sem dar erro."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ibmecPCDV20261_victor_lucas_beatriz_ravi.poc_clusters import (
    avaliacao,
    clustering,
    config,
    descritiva,
    perfil,
)
from ibmecPCDV20261_victor_lucas_beatriz_ravi.poc_clusters.coleta import pix


def test_mes_incompleto_e_descartado():
    """O mês em andamento chega com volume parcial e não pode entrar na janela."""
    completos = pd.DataFrame(
        {
            "AnoMes": [202601] * 3 + [202602] * 3 + [202603] * 3,
            "VL_PagadorPF": [100, 100, 100, 100, 100, 100, 30, 30, 30],
        }
    )
    assert pix.meses_completos(completos) == [202601, 202602]


def test_mes_completo_com_variacao_normal_nao_e_descartado():
    dados = pd.DataFrame(
        {
            "AnoMes": [202601] * 2 + [202602] * 2 + [202603] * 2,
            "VL_PagadorPF": [100, 100, 95, 95, 105, 105],
        }
    )
    assert pix.meses_completos(dados) == [202601, 202602, 202603]


def test_winsorizacao_corta_as_duas_caudas_e_reduz_assimetria():
    base = pd.DataFrame({"credito_per_capita": list(range(100)) + [1_000_000]})
    tratada, registro = descritiva.winsorizar(base, ["credito_per_capita"], quantil=0.01)
    assert tratada["credito_per_capita"].max() < 1_000_000
    assert abs(registro.loc[0, "assimetria_depois"]) < abs(registro.loc[0, "assimetria_antes"])


def test_log_so_entra_em_variavel_nao_negativa_e_assimetrica():
    assimetrica = pd.Series([1, 1, 1, 1, 2, 3, 100])
    simetrica = pd.Series([1, 2, 3, 4, 5, 6, 7])
    com_negativo = pd.Series([-5, 1, 1, 1, 2, 3, 100])
    assert descritiva.precisa_log(assimetrica)
    assert not descritiva.precisa_log(simetrica)
    assert not descritiva.precisa_log(com_negativo)


def test_corte_de_correlacao_mantem_a_variavel_usada_em_mais_grupos():
    gerador = np.random.default_rng(config.SEMENTE)
    ruido = gerador.normal(size=300)
    base = pd.DataFrame(
        {
            # administradoras aparece em A, C e D; imobiliarias só em A.
            "administradoras_10k": ruido,
            "imobiliarias_10k": ruido + gerador.normal(scale=0.05, size=300),
            "saldo_emprego_pct": gerador.normal(size=300),
        }
    )
    mantidas, decisoes = descritiva.decidir_cortes(base, list(base.columns))
    assert "administradoras_10k" in mantidas
    assert "imobiliarias_10k" not in mantidas
    assert len(decisoes) == 1


def test_sem_par_correlacionado_nada_e_descartado():
    gerador = np.random.default_rng(config.SEMENTE)
    base = pd.DataFrame(
        {
            "administradoras_10k": gerador.normal(size=300),
            "saldo_emprego_pct": gerador.normal(size=300),
        }
    )
    mantidas, decisoes = descritiva.decidir_cortes(base, list(base.columns))
    assert set(mantidas) == set(base.columns)
    assert decisoes.loc[0, "variavel_descartada"] == "nenhuma"


def _base_sintetica(n_por_grupo: int = 60) -> pd.DataFrame:
    """Três grupos bem separados, com as colunas que os baselines exigem."""
    gerador = np.random.default_rng(config.SEMENTE)
    partes = []
    for i, centro in enumerate([0.0, 8.0, 16.0]):
        partes.append(
            pd.DataFrame(
                {
                    "administradoras_10k": gerador.normal(centro, 0.4, n_por_grupo),
                    "pix_pf_por_hab": gerador.normal(centro, 0.4, n_por_grupo),
                    "cadunico_pct": gerador.normal(centro, 0.4, n_por_grupo),
                    "verdadeiro": i,
                }
            )
        )
    base = pd.concat(partes, ignore_index=True)
    base["id_municipio"] = [str(1_000_000 + i) for i in range(len(base))]
    base["populacao"] = gerador.integers(50_000, 2_000_000, len(base))
    base["regiao"] = gerador.choice(["Norte", "Sudeste", "Sul"], len(base))
    base["porte"] = gerador.choice(["pequeno", "medio", "grande"], len(base))
    return base


def test_cotovelo_encontra_o_numero_de_grupos_plantado():
    base = _base_sintetica()
    variaveis = ["administradoras_10k", "pix_pf_por_hab", "cadunico_pct"]
    varredura = clustering.varrer_k(base, {"X": variaveis}, k_maximo=8)
    assert avaliacao.cotovelo(varredura, "X") == 3


def test_modelo_recupera_os_grupos_plantados():
    base = _base_sintetica()
    variaveis = ["administradoras_10k", "pix_pf_por_hab", "cadunico_pct"]
    matriz, _ = clustering.preparar_matriz(base, variaveis)
    rotulos = clustering.rotular(matriz, "kmeans", 3)
    from sklearn.metrics import adjusted_rand_score

    assert adjusted_rand_score(base["verdadeiro"], rotulos) > 0.95


def test_cluster_verdadeiro_supera_geografia_porte_e_sorteio():
    """Se este teste falhar, o comparador de baselines está inflando o resultado."""
    base = _base_sintetica()
    variaveis = ["administradoras_10k", "pix_pf_por_hab", "cadunico_pct"]
    matriz, _ = clustering.preparar_matriz(base, variaveis)
    rotulos = clustering.rotular(matriz, "kmeans", 3)
    comparacao = avaliacao.comparar_baselines(base, variaveis, rotulos, n_repeticoes_aleatorio=5)
    silhueta_cluster = comparacao.iloc[0]["silhueta"]
    assert all(silhueta_cluster > comparacao.iloc[i]["silhueta"] for i in range(1, len(comparacao)))


def test_ablacao_mede_queda_ao_remover_variavel():
    base = _base_sintetica()
    variaveis = ["administradoras_10k", "pix_pf_por_hab", "cadunico_pct"]
    tabela = avaliacao.ablacao(base, variaveis, "kmeans", 3)
    assert len(tabela) == len(variaveis)
    assert tabela["variacao"].notna().all()


def test_nomes_dos_clusters_sao_unicos_e_descrevem_o_perfil():
    perfil_z = pd.DataFrame(
        {
            "administradoras_10k": [1.4, -0.8, -0.3],
            "imobiliarias_novas_pct": [0.0, -1.2, 1.7],
            "pix_pf_por_hab": [1.1, -1.1, -0.9],
            "cadunico_pct": [-0.8, 1.2, 0.9],
            "internet_movel_100": [1.0, -1.4, -0.9],
            "banda_larga_100": [1.1, -1.2, -0.9],
        },
        index=pd.Index([0, 1, 2], name="cluster"),
    )
    nomes = perfil.nomear(perfil_z)
    assert len(set(nomes.values())) == 3
    assert nomes[0] == "Praça madura de locação"
    assert nomes[1] == "Praça sem mercado formal"
    assert nomes[2] == "Praça em formação"


def test_tabela_de_valor_cobre_todos_os_clusters():
    perfil_z = pd.DataFrame(
        {"administradoras_10k": [1.4, -0.8], "pix_pf_por_hab": [1.1, -1.1], "cadunico_pct": [-0.8, 1.2],
         "internet_movel_100": [1.0, -1.4], "banda_larga_100": [1.1, -1.2],
         "imobiliarias_novas_pct": [0.0, -1.2]},
        index=pd.Index([0, 1], name="cluster"),
    )
    nomes = perfil.nomear(perfil_z)
    tamanhos = pd.DataFrame({"cluster": [0, 1], "municipios": [10, 20], "populacao_pct": [60.0, 40.0]})
    valor = perfil.tabela_valor_loft(perfil_z, nomes, tamanhos)
    assert len(valor) == 2
    assert valor["o_que_significa_para_a_fianca"].str.len().gt(20).all()
    assert valor["acao_de_marketing_sugerida"].str.len().gt(20).all()


@pytest.mark.parametrize("grupo", list(config.GRUPOS))
def test_todo_grupo_tem_variavel_declarada(grupo):
    for variavel in config.GRUPOS[grupo]:
        assert variavel in config.VARIAVEIS
