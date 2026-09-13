"""Script de apoio único: confirma o formato real das APIs de atas do Copom.

Formato da LISTAGEM (`atas`) já confirmado contra a API real: as chaves são
`nroReuniao`, `dataReferencia`, `dataPublicacao`, `titulo` — sem campo de
URL de detalhe. `src/coleta/atas_copom.py` já foi ajustado para isso.

O formato de DETALHES (`atas_detalhes`) ainda não foi confirmado: a
primeira tentativa usando `nroReuniao` como parâmetro pode não ser a forma
certa de chamar esse endpoint (a listagem não trouxe pista nenhuma de como
navegar até o detalhe). Rode este script e cole a saída de volta para
ajustar `buscar_html_ata` — em especial o nome do campo que carrega o HTML
da ata dentro do JSON de resposta.

Uso:
    python scripts/inspecionar_api_atas.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from coleta.atas_copom import URL_DETALHES, URL_LISTA, criar_sessao_com_retry, _extrair_lista  # noqa: E402


def main() -> None:
    sessao = criar_sessao_com_retry()

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
    print(f"Tentando com nroReuniao={itens[0].get('nroReuniao')}...")
    resposta_detalhe = sessao.get(
        URL_DETALHES, params={"nroReuniao": itens[0].get("nroReuniao")}, timeout=30
    )
    print("Status:", resposta_detalhe.status_code)
    if resposta_detalhe.ok:
        print(json.dumps(resposta_detalhe.json(), ensure_ascii=False, indent=2)[:2000])
    else:
        print("Corpo da resposta:", resposta_detalhe.text[:2000])


if __name__ == "__main__":
    main()
