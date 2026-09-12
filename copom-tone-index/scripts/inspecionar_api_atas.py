"""Script de apoio único: confirma o formato real das APIs de atas do Copom.

Este ambiente de desenvolvimento não tem acesso de rede a bcb.gov.br, então
os nomes de campo usados em src/coleta/atas_copom.py (candidatos passados a
_obter_campo) são suposições defensivas, não confirmadas. Rode este script
num ambiente com rede liberada, compare as chaves impressas com os
candidatos usados no módulo de coleta e ajuste-os se não baterem — antes
disso, não confie em nenhum resultado de coletar_atas().

Uso:
    python scripts/inspecionar_api_atas.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from coleta.atas_copom import URL_DETALHES, URL_LISTA, _criar_sessao, _extrair_lista  # noqa: E402


def main() -> None:
    sessao = _criar_sessao()

    resposta_lista = sessao.get(URL_LISTA, params={"quantidade": 3}, timeout=30)
    resposta_lista.raise_for_status()
    itens = _extrair_lista(resposta_lista.json())

    print("=== Lista de atas (atas) ===")
    if not itens:
        print("Lista vazia — confira o envelope do JSON manualmente.")
        return
    print("Chaves do primeiro item:", list(itens[0].keys()))
    print(json.dumps(itens[0], ensure_ascii=False, indent=2)[:2000])

    print("\n=== Detalhes da primeira ata da lista (atas_detalhes) ===")
    print(
        "Ajuste os parâmetros abaixo manualmente conforme o que a lista "
        "sugerir (ex.: usar a própria URL do item, se houver um campo Url)."
    )
    resposta_detalhe = sessao.get(
        URL_DETALHES, params={"numeroReuniao": itens[0].get("NumeroReuniao")}, timeout=30
    )
    print("Status:", resposta_detalhe.status_code)
    if resposta_detalhe.ok:
        print(json.dumps(resposta_detalhe.json(), ensure_ascii=False, indent=2)[:2000])
    else:
        print("Corpo da resposta:", resposta_detalhe.text[:2000])


if __name__ == "__main__":
    main()
