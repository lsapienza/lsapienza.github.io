"""Converte o texto extraído do Focus (data/focus_AAAA-MM-DD.txt) em JSON.

Este módulo é puramente mecânico: separa cada linha de indicador nas colunas
do PDF e devolve os valores como STRINGS, exatamente como aparecem no texto
(vírgula decimal, sinais, "-" para ausente). Não arredonda, não calcula
variações, não decide o que é relevante (ver CLAUDE.md — princípio de
separação entre determinístico e julgamento). Serve para que a página do site
mostre as tabelas sem transcrição manual de números.

Estrutura de cada bloco (um por ano ou mês) no texto do PDF:
    Há 4 semanas, Há 1 semana, Hoje, [▲|▼], (semanas), Resp.**,
    [5 dias úteis, [Resp.***]]
O símbolo de estabilidade não sobrevive à extração — sem seta, "comp" fica "=".
Quando "Hoje" é "-", o bloco não tem as demais colunas.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

NUM = r"-?\d{1,3}(?:\.\d{3})*,\d{2}|-"
RE_LINHA = re.compile(rf"^(?P<nome>.+?) (?P<resto>(?:{NUM}) .*)$")
RE_DATA = re.compile(r"Expectativas de Mercado (\d{1,2} de \w+ de \d{4})")

# Colunas de cada bloco, por página: (tem "5 dias úteis", tem "Resp. ***")
LAYOUT_ANUAL = [(True, True), (True, True), (False, False), (False, False)]
LAYOUT_MENSAL = [(True, False)] * 4


def _bloco(tokens: list[str], tem_5d: bool, tem_resp5: bool) -> dict:
    b = {"h4": tokens.pop(0), "h1": tokens.pop(0), "hoje": tokens.pop(0)}
    if b["hoje"] == "-":
        return b
    b["comp"] = tokens.pop(0) if tokens and tokens[0] in ("▲", "▼") else "="
    b["semanas"] = tokens.pop(0).strip("()")
    b["resp"] = tokens.pop(0)
    if tem_5d:
        b["5d"] = tokens.pop(0)
        if tem_resp5:
            b["resp5"] = tokens.pop(0)
    return b


def _parse_linha(linha: str, layout) -> dict | None:
    m = RE_LINHA.match(linha)
    if not m:
        return None
    tokens = m.group("resto").split()
    if not all(re.fullmatch(rf"{NUM}|▲|▼|\(\d+\)|\d+", t) for t in tokens):
        return None  # cabeçalho/legenda (ex.: "Mediana - Agregado")
    # Câmbio e Selic não têm a coluna "Infl. 12 m suav." — a linha acaba antes.
    blocos = [_bloco(tokens, *cols) for cols in layout if tokens]
    if tokens:
        raise ValueError(f"Sobraram tokens não reconhecidos em: {linha!r}")
    return {"indicador": m.group("nome"), "blocos": blocos}


def _cabecalho_colunas(pagina: str) -> list[str]:
    # A linha logo após "▲Aumento ▼Diminuição Estabilidade" lista os
    # rótulos das colunas (anos na pág. 1; meses + "Infl. 12 m suav." na 2).
    linhas = pagina.splitlines()
    for i, l in enumerate(linhas):
        if l.startswith("▲Aumento"):
            rotulos = linhas[i + 1]
            return re.findall(r"Infl\. 12 m suav\.|\S+/\d{4}|\d{4}", rotulos)
    raise ValueError("Cabeçalho de colunas não encontrado")


def tabular(texto: str) -> dict:
    paginas = [p for p in texto.split("\n\n") if p.strip()]
    if len(paginas) != 2:
        raise ValueError(f"Esperava 2 páginas, achei {len(paginas)}")
    data = RE_DATA.search(texto)
    saida = {"data_relatorio": data.group(1) if data else None, "paginas": []}
    for pagina, layout in zip(paginas, (LAYOUT_ANUAL, LAYOUT_MENSAL)):
        colunas = _cabecalho_colunas(pagina)
        linhas = []
        for l in pagina.splitlines():
            if l.startswith(("Há ", "Hoje", "semanas", "*", "Focus", "Expectativas")):
                continue
            r = _parse_linha(l, layout)
            if r:
                linhas.append(r)
        saida["paginas"].append({"colunas": colunas, "linhas": linhas})
    return saida


def main() -> None:
    p = argparse.ArgumentParser(description="Texto do Focus -> JSON (valores literais).")
    p.add_argument("caminho_txt", type=Path)
    args = p.parse_args()
    dados = tabular(args.caminho_txt.read_text(encoding="utf-8"))
    print(json.dumps(dados, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
