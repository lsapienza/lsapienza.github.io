"""Gera o post de blog correspondente a um resumo do Focus já escrito.

Este módulo é puramente mecânico: extrai o conteúdo já redigido no e-mail
HTML (output/focus/focus_AAAA-MM-DD.html, produzido pela etapa de redação)
e remonta como post Quarto (posts/focus-AAAA-MM-DD.pt.qmd), para o blog
pessoal hospedado neste mesmo repositório. Não interpreta, resume nem
reescreve nenhum número ou frase — só copia o texto já aprovado na etapa
de redação para outro formato (ver CLAUDE.md — princípio de separação
entre determinístico e julgamento).
"""
from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# posts/ vive na raiz do site (lsapienza.github.io/), não dentro de
# resumo-focus/ — este arquivo está em resumo-focus/src/, então a raiz do
# site é dois níveis acima.
PASTA_POSTS_PADRAO = Path(__file__).resolve().parent.parent.parent / "posts"


class TemplateInesperado(ValueError):
    """O HTML não tem a estrutura esperada do template do e-mail do Focus."""


def _texto(tag: Any) -> str:
    """Extrai o texto de um elemento, colapsando espaços/quebras de linha
    de formatação do HTML-fonte em um único espaço — sem inserir espaço
    extra entre elementos inline adjacentes (ex.: "<strong>X</strong>,"),
    o que get_text(separator=" ") faria incorretamente."""
    if not tag:
        return ""
    return re.sub(r"\s+", " ", tag.get_text()).strip()


def extrair_conteudo(html: str) -> dict:
    """Extrai os campos do template fixo do e-mail do Focus (ver
    output/focus/focus_2026-09-11.html para um exemplo real da estrutura
    esperada: h1.titulo, parágrafos do corpo em cor #2b3040, cada revisão
    como um span.revisao-valor ao lado de um span riscado, e o rodapé
    começando em "Fonte:")."""
    sopa = BeautifulSoup(html, "html.parser")

    titulo = _texto(sopa.find("h1", class_="titulo"))
    if not titulo:
        raise TemplateInesperado(
            "Não encontrei <h1 class='titulo'> no HTML — o template do "
            "e-mail pode ter mudado."
        )

    # Parágrafos do corpo do resumo: no template, a cor #2b3040 está no
    # <td> que envolve os <p> do corpo (não nos <p> em si) — e é usada só
    # ali (cabeçalho e rodapé usam outras cores).
    paragrafos_corpo = [
        _texto(p)
        for td in sopa.find_all(
            "td", style=lambda s: s and "color:#2b3040" in s.replace(" ", "")
        )
        for p in td.find_all("p")
    ]

    # "Três principais revisões da semana": cada linha é uma mini-tabela
    # com um <td> de label (font-weight:600) e dois <span> de valor — um
    # riscado (valor antigo) e outro com a classe revisao-valor (valor novo).
    # find_all("tr") também pega a <tr> externa (que só envolve a tabela
    # aninhada), então dá duplicado se não filtrar — usamos um set para só
    # manter a primeira ocorrência de cada revisão (a da <tr> mais interna).
    revisoes = []
    vistas = set()
    for linha in sopa.find_all("tr"):
        label_td = linha.find(
            "td", style=lambda s: s and "font-weight:600" in s.replace(" ", "")
        )
        novo = linha.find("span", class_="revisao-valor")
        antigo = linha.find(
            "span", style=lambda s: s and "line-through" in s.replace(" ", "")
        )
        if label_td and novo and antigo:
            chave = (_texto(label_td), _texto(antigo), _texto(novo))
            if chave not in vistas:
                vistas.add(chave)
                revisoes.append({"label": chave[0], "antigo": chave[1], "novo": chave[2]})

    rodape = ""
    for p in sopa.find_all("p"):
        if p.get_text(strip=True).startswith("Fonte:"):
            rodape = _texto(p)
            break

    return {
        "titulo": titulo,
        "paragrafos": paragrafos_corpo,
        "revisoes": revisoes,
        "rodape": rodape,
    }


def data_do_arquivo(caminho_html: Path) -> str:
    """Deriva AAAA-MM-DD a partir do nome do arquivo (focus_AAAA-MM-DD.html)."""
    casamento = re.fullmatch(r"focus_(\d{4}-\d{2}-\d{2})", caminho_html.stem)
    if not casamento:
        raise TemplateInesperado(f"Nome de arquivo inesperado: {caminho_html.name}")
    return casamento.group(1)


def montar_qmd(conteudo: dict, data_referencia: str) -> str:
    """Monta o conteúdo do post .pt.qmd a partir do conteúdo já extraído."""
    linhas = [
        "---",
        f'title: "{conteudo["titulo"]}"',
        f"date: {data_referencia}",
        (
            "description: \"Resumo do Boletim Focus do Banco Central — "
            f"semana de referência {data_referencia}.\""
        ),
        f"output-file: focus-{data_referencia}.html",
        "categories: [economia, focus]",
        "---",
        "",
        f"*Semana de referência: {data_referencia} · Fonte: Banco Central do Brasil*",
        "",
    ]

    for paragrafo in conteudo["paragrafos"]:
        linhas.append(paragrafo)
        linhas.append("")

    if conteudo["revisoes"]:
        linhas.append("## Principais revisões da semana")
        linhas.append("")
        for revisao in conteudo["revisoes"]:
            linhas.append(f"- **{revisao['label']}**: {revisao['antigo']} → {revisao['novo']}")
        linhas.append("")

    if conteudo["rodape"]:
        linhas.append(f"*{conteudo['rodape']}*")
        linhas.append("")

    return "\n".join(linhas)


def caminho_post_correspondente(data_referencia: str, pasta_posts: Path) -> Path:
    return pasta_posts / f"focus-{data_referencia}.pt.qmd"


def gerar_post(caminho_html: Path, pasta_posts: Path = PASTA_POSTS_PADRAO) -> Path:
    """Ponto de entrada: lê o HTML do Focus e grava o post .pt.qmd correspondente."""
    data_referencia = data_do_arquivo(caminho_html)
    conteudo = extrair_conteudo(caminho_html.read_text(encoding="utf-8"))
    qmd = montar_qmd(conteudo, data_referencia)

    pasta_posts.mkdir(parents=True, exist_ok=True)
    caminho_post = caminho_post_correspondente(data_referencia, pasta_posts)
    caminho_post.write_text(qmd, encoding="utf-8")
    return caminho_post


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Gera o post de blog a partir do resumo HTML do Focus já escrito."
    )
    parser.add_argument("caminho_html", type=Path, help="Caminho do focus_AAAA-MM-DD.html")
    parser.add_argument(
        "--pasta-posts",
        type=Path,
        default=PASTA_POSTS_PADRAO,
        help="Pasta onde gravar o post (padrão: posts/ na raiz do site)",
    )
    args = parser.parse_args()

    caminho_post = gerar_post(args.caminho_html, args.pasta_posts)
    logger.info("Post gerado em %s", caminho_post)


if __name__ == "__main__":
    main()
