from pathlib import Path

import pytest

from src.tabular_focus import tabular

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.mark.parametrize("txt", sorted(DATA.glob("focus_*.txt")), ids=lambda p: p.name)
def test_todos_os_textos_historicos_sao_tabulados(txt):
    d = tabular(txt.read_text(encoding="utf-8"))
    anual, mensal = d["paginas"]
    assert anual["colunas"][0].isdigit() and len(anual["colunas"]) == 4
    assert len(anual["linhas"]) == 12
    assert len(mensal["linhas"]) == 4


def test_valores_sao_copiados_literalmente():
    d = tabular((DATA / "focus_2026-10-09.txt").read_text(encoding="utf-8"))
    assert d["data_relatorio"] == "9 de outubro de 2026"
    ipca = d["paginas"][0]["linhas"][0]
    assert ipca["indicador"] == "IPCA (variação %)"
    assert ipca["blocos"][0] == {
        "h4": "4,90", "h1": "5,01", "hoje": "5,22", "comp": "▲",
        "semanas": "4", "resp": "144", "5d": "5,19", "resp5": "54",
    }
    selic_mensal = d["paginas"][1]["linhas"][2]
    assert selic_mensal["blocos"][0] == {"h4": "-", "h1": "-", "hoje": "-"}
    assert len(selic_mensal["blocos"]) == 3
