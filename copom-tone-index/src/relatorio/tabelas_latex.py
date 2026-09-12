"""Formata DataFrames como tabelas LaTeX booktabs + threeparttable (padrão
de journal: nota de rodapé dentro da própria tabela), para sair de um
chunk Quarto com `#| output: asis`.

Os rótulos de coluna e a nota são escritos à mão em cada chamada (LaTeX
válido, às vezes com modo matemático como `$\\hat\\beta$") — por isso este
módulo não escapa nada automaticamente: quem chama é sempre o código deste
projeto, nunca texto de terceiros, e escapar cegamente quebraria os
`$...$` intencionais.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def formatar_tabela_booktabs(
    tabela: pd.DataFrame,
    colunas: list[str],
    titulo: str,
    nota: str,
    rotulos_colunas: dict[str, str],
    formatos: dict[str, str] | None = None,
    column_format: str | None = None,
    label: str | None = None,
) -> str:
    """Monta uma tabela LaTeX booktabs dentro de um ambiente threeparttable.

    `formatos` mapeia coluna -> string de formatação estilo `.format()`
    (ex.: `{"beta_hat": "{:.3f}"}`), aplicada antes de renomear as colunas.
    Valores ausentes viram "--". `rotulos_colunas` mapeia o nome da coluna
    (antes de formatar) para o cabeçalho final, já em LaTeX.
    """
    dados = tabela[colunas].copy()
    formatos = formatos or {}

    for coluna, fmt in formatos.items():
        dados[coluna] = dados[coluna].map(
            lambda v, fmt=fmt: fmt.format(v) if pd.notna(v) else "--"
        )

    dados = dados.rename(columns=rotulos_colunas)

    estilo = dados.style.hide(axis="index")
    if column_format is None:
        column_format = "l" + "r" * (len(colunas) - 1)
    tabular = estilo.to_latex(hrules=True, column_format=column_format)

    rotulo_latex = f"\n\\label{{{label}}}" if label else ""

    return (
        "\\begin{table}[ht]\n"
        "\\centering\n"
        f"\\caption{{{titulo}}}{rotulo_latex}\n"
        "\\begin{threeparttable}\n"
        f"{tabular}"
        "\\begin{tablenotes}\n"
        "\\small\n"
        f"\\item {nota}\n"
        "\\end{tablenotes}\n"
        "\\end{threeparttable}\n"
        "\\end{table}"
    )


def nota_dados_ausentes(caminho: str | Path) -> str:
    """Nota em itálico para um chunk de Resultados cujo arquivo de dados
    ainda não existe — usada no lugar da tabela/figura, em vez de deixar o
    chunk simplesmente estourar um traceback bruto no meio do paper.
    """
    # "_" é caractere especial em modo texto do LaTeX (nomes de arquivo
    # como tabela_calibracao.csv têm underscore) — precisa escapar antes
    # de entrar num \texttt{...}, senão o pdflatex lê como início de
    # subscrito e quebra com "Missing $ inserted".
    caminho_escapado = str(caminho).replace("_", "\\_")
    return (
        f"\\textit{{Tabela/figura não gerada: o arquivo \\texttt{{{caminho_escapado}}} "
        "ainda não existe neste ambiente de desenvolvimento (sem acesso de "
        "rede a bcb.gov.br e sem chaves de API reais). Ver seção "
        "``Próximos Passos''.}"
    )
