"""Calibração dos índices de tom contra a variação da Selic — etapa de
Evaluation do CRISP-DM.

Para cada modelo (Gemini, Claude, OpenAI, léxico), ajusta

    variacao_Selic(t) = alpha + beta * score(t) + erro(t)

via OLS (statsmodels) e reporta os coeficientes. Além da tabela de
calibração por modelo, oferece um teste formal — Vuong (1989), para
modelos não aninhados — para responder à pergunta que uma tabela de R²
sozinha não responde: quando a diferença de ajuste entre dois modelos é
grande o bastante para não ser explicada por acaso amostral.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

# (nome da coluna de score na tabela final, rótulo do modelo na tabela de saída)
ESPECIFICACOES_MODELOS = [
    ("score_gemini", "Gemini"),
    ("score_claude", "Claude"),
    ("score_openai", "OpenAI"),
    ("score_lexico", "Léxico (baseline)"),
]


@dataclass
class ResultadoCalibracao:
    modelo: str
    n: int
    alpha_hat: float
    beta_hat: float
    erro_padrao_beta: float
    estatistica_t: float
    p_valor: float
    ic95_beta_inferior: float
    ic95_beta_superior: float
    r2: float
    r2_ajustado: float
    resultado_statsmodels: sm.regression.linear_model.RegressionResultsWrapper


def calibrar_modelo(
    tabela: pd.DataFrame, coluna_score: str, nome_modelo: str
) -> ResultadoCalibracao:
    """Ajusta variacao_selic = alpha + beta*score via OLS para um modelo.

    Descarta linhas em que o score ou a variação da Selic estão ausentes.
    Cada modelo pode acabar com um `n` diferente: nem toda ata foi
    pontuada com sucesso pelos três LLMs (erros de API deixam buracos no
    cache), enquanto o léxico, por ser determinístico, cobre todas.
    """
    dados = tabela[[coluna_score, "variacao_selic"]].dropna()
    y = dados["variacao_selic"]
    x = sm.add_constant(dados[[coluna_score]])
    resultado = sm.OLS(y, x).fit()

    ic = resultado.conf_int(alpha=0.05).loc[coluna_score]

    return ResultadoCalibracao(
        modelo=nome_modelo,
        n=int(resultado.nobs),
        alpha_hat=resultado.params["const"],
        beta_hat=resultado.params[coluna_score],
        erro_padrao_beta=resultado.bse[coluna_score],
        estatistica_t=resultado.tvalues[coluna_score],
        p_valor=resultado.pvalues[coluna_score],
        ic95_beta_inferior=ic.iloc[0],
        ic95_beta_superior=ic.iloc[1],
        r2=resultado.rsquared,
        r2_ajustado=resultado.rsquared_adj,
        resultado_statsmodels=resultado,
    )


def montar_tabela_calibracao(tabela: pd.DataFrame) -> pd.DataFrame:
    """Roda calibrar_modelo para os modelos presentes na tabela e junta o resultado."""
    linhas = []
    for coluna, nome in ESPECIFICACOES_MODELOS:
        if coluna not in tabela.columns:
            continue
        resultado = calibrar_modelo(tabela, coluna, nome)
        linhas.append(
            {
                "modelo": resultado.modelo,
                "n": resultado.n,
                "alpha_hat": resultado.alpha_hat,
                "beta_hat": resultado.beta_hat,
                "erro_padrao_beta": resultado.erro_padrao_beta,
                "estatistica_t": resultado.estatistica_t,
                "p_valor": resultado.p_valor,
                "ic95_beta_inferior": resultado.ic95_beta_inferior,
                "ic95_beta_superior": resultado.ic95_beta_superior,
                "r2": resultado.r2,
                "r2_ajustado": resultado.r2_ajustado,
            }
        )
    return pd.DataFrame(linhas)


def teste_vuong(
    tabela: pd.DataFrame,
    coluna_score_a: str,
    coluna_score_b: str,
    nome_a: str,
    nome_b: str,
) -> dict:
    """Teste de Vuong (1989) para comparar o ajuste de dois modelos não aninhados.

    R² maior não basta para dizer que um modelo é melhor — pode ser
    diferença de acaso amostral. O teste de Vuong compara, observação a
    observação, a log-verossimilhança de cada modelo sob normalidade dos
    erros (a mesma hipótese usual do OLS) e testa se a diferença média é
    grande o bastante frente à variabilidade dela mesma.

    Os dois modelos são recalibrados aqui na INTERSEÇÃO das observações
    não-nulas de `coluna_score_a` e `coluna_score_b` — comparação só faz
    sentido calculada sobre exatamente a mesma amostra (mesmas reuniões).

    Retorna a estatística V (~ N(0,1) sob H0 de equivalência) e o p-valor
    bicaudal. V > 0 favorece o modelo A; V < 0 favorece o modelo B.
    |V| > 1.96 (p < 0.05) é o critério usual para chamar a diferença de
    estatisticamente robusta.
    """
    dados = tabela[[coluna_score_a, coluna_score_b, "variacao_selic"]].dropna()
    n = len(dados)
    y = dados["variacao_selic"].to_numpy()

    modelo_a = sm.OLS(y, sm.add_constant(dados[[coluna_score_a]])).fit()
    modelo_b = sm.OLS(y, sm.add_constant(dados[[coluna_score_b]])).fit()

    erro_a = modelo_a.resid.to_numpy()
    erro_b = modelo_b.resid.to_numpy()

    # Variância residual estimada por máxima verossimilhança (divide por n,
    # não por n-k) — é a que entra na log-verossimilhança gaussiana usada
    # pelo teste de Vuong.
    sigma2_a = np.sum(erro_a**2) / n
    sigma2_b = np.sum(erro_b**2) / n

    log_verossim_a = (
        -0.5 * np.log(2 * np.pi) - 0.5 * np.log(sigma2_a) - (erro_a**2) / (2 * sigma2_a)
    )
    log_verossim_b = (
        -0.5 * np.log(2 * np.pi) - 0.5 * np.log(sigma2_b) - (erro_b**2) / (2 * sigma2_b)
    )

    diferenca = log_verossim_a - log_verossim_b
    desvio_diferenca = diferenca.std(ddof=0)

    if desvio_diferenca == 0:
        estatistica_v = 0.0
    else:
        estatistica_v = np.sqrt(n) * diferenca.mean() / desvio_diferenca

    p_valor = 2 * (1 - stats.norm.cdf(abs(estatistica_v)))

    if p_valor < 0.05:
        favorecido = nome_a if estatistica_v > 0 else nome_b
        conclusao = (
            f"{favorecido} explica variacao_selic significativamente melhor "
            f"(Vuong, p={p_valor:.4f} < 0.05)"
        )
    else:
        conclusao = (
            f"Diferença entre {nome_a} e {nome_b} NÃO é estatisticamente "
            f"robusta (Vuong, p={p_valor:.4f})"
        )

    return {
        "modelo_a": nome_a,
        "modelo_b": nome_b,
        "n": n,
        "estatistica_v": estatistica_v,
        "p_valor": p_valor,
        "conclusao": conclusao,
    }


def montar_tabela_comparacoes(tabela: pd.DataFrame) -> pd.DataFrame:
    """Roda teste_vuong para todo par de modelos presentes na tabela final."""
    presentes = [(c, n) for c, n in ESPECIFICACOES_MODELOS if c in tabela.columns]

    linhas = []
    for i in range(len(presentes)):
        for j in range(i + 1, len(presentes)):
            coluna_a, nome_a = presentes[i]
            coluna_b, nome_b = presentes[j]
            linhas.append(teste_vuong(tabela, coluna_a, coluna_b, nome_a, nome_b))
    return pd.DataFrame(linhas)
