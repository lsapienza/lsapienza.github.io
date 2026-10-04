from pathlib import Path

import pytest

from src.gerar_post_blog import (
    TemplateInesperado,
    data_do_arquivo,
    extrair_conteudo,
    gerar_post,
    montar_qmd,
)

CAMINHO_HTML_REAL = (
    Path(__file__).parent.parent / "output" / "focus" / "focus_2026-09-11.html"
)


def test_data_do_arquivo():
    assert data_do_arquivo(Path("focus_2026-09-11.html")) == "2026-09-11"


def test_data_do_arquivo_rejeita_nome_inesperado():
    with pytest.raises(TemplateInesperado):
        data_do_arquivo(Path("resumo-qualquer.html"))


def test_extrair_conteudo_do_html_real():
    html = CAMINHO_HTML_REAL.read_text(encoding="utf-8")
    conteudo = extrair_conteudo(html)

    assert conteudo["titulo"] == "Focus revisa IPCA e PIB de 2026 para baixo"
    assert len(conteudo["paragrafos"]) == 2
    assert "4,90%" in conteudo["paragrafos"][0]
    assert conteudo["rodape"].startswith("Fonte:")

    assert conteudo["revisoes"] == [
        {"label": "IPCA (2026)", "antigo": "5,00", "novo": "4,90"},
        {"label": "PIB Total (2026)", "antigo": "1,93", "novo": "1,89"},
        {"label": "Câmbio (2027)", "antigo": "5,30", "novo": "5,28"},
    ]


def test_extrair_conteudo_rejeita_html_sem_titulo():
    with pytest.raises(TemplateInesperado):
        extrair_conteudo("<html><body><p>sem h1.titulo</p></body></html>")


def test_montar_qmd_inclui_front_matter_e_revisoes():
    conteudo = {
        "titulo": "Título de teste",
        "paragrafos": ["Primeiro parágrafo.", "Segundo parágrafo."],
        "revisoes": [{"label": "IPCA (2026)", "antigo": "5,00", "novo": "4,90"}],
        "rodape": "Fonte: Boletim Focus, 11 de setembro de 2026.",
    }

    qmd = montar_qmd(conteudo, "2026-09-11")

    assert 'title: "Título de teste"' in qmd
    assert "date: 2026-09-11" in qmd
    assert "output-file: focus-2026-09-11.html" in qmd
    assert "categories: [economia, focus]" in qmd
    assert "Primeiro parágrafo." in qmd
    assert "- **IPCA (2026)**: 5,00 → 4,90" in qmd
    assert "*Fonte: Boletim Focus, 11 de setembro de 2026.*" in qmd


def test_gerar_post_grava_arquivo_esperado(tmp_path):
    caminho_post = gerar_post(CAMINHO_HTML_REAL, pasta_posts=tmp_path)

    assert caminho_post == tmp_path / "focus-2026-09-11.pt.qmd"
    conteudo_gravado = caminho_post.read_text(encoding="utf-8")
    assert "Focus revisa IPCA e PIB de 2026 para baixo" in conteudo_gravado
