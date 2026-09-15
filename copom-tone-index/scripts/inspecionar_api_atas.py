"""Teste de fumaça do pipeline de coleta, contra a API real do BCB.

Este script já serviu para descobrir o formato real da API de listagem
(`nroReuniao`, `dataReferencia`) e o padrão de URL do PDF de cada ata
(`/content/copom/atascopom/Copom{nro}-not{AAAAMMDD}{nro}.pdf`) — ambos já
confirmados e embutidos em `src/coleta/atas_copom.py`. Agora ele serve
para validar rapidamente, antes de rodar a coleta completa (que baixa
dezenas de PDFs) ou os loops de pontuação (que gastam créditos de API):
lista as reuniões, baixa o PDF de UMA delas, extrai o texto e mostra o
recorte das seções A/B.

Uso:
    python scripts/inspecionar_api_atas.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from coleta.atas_copom import (  # noqa: E402
    REUNIAO_MINIMA,
    baixar_pdf_ata,
    criar_sessao_com_retry,
    extrair_secoes_a_b,
    extrair_texto_pdf,
    listar_reunioes,
)


def main() -> None:
    sessao = criar_sessao_com_retry()

    reunioes = listar_reunioes(sessao)
    print(f"{len(reunioes)} reuniões encontradas a partir da {REUNIAO_MINIMA}ª.")
    if not reunioes:
        print("Nenhuma reunião encontrada — confira listar_reunioes() manualmente.")
        return

    primeira = reunioes[0]
    print(f"\nBaixando o PDF da reunião {primeira.numero_reuniao} ({primeira.data})...")
    conteudo_pdf = baixar_pdf_ata(sessao, primeira)
    print(f"PDF baixado: {len(conteudo_pdf)} bytes.")

    texto = extrair_texto_pdf(conteudo_pdf)
    print(f"Texto extraído: {len(texto)} caracteres.")
    print("\n--- Primeiros 500 caracteres do texto extraído ---")
    print(texto[:500])

    recorte = extrair_secoes_a_b(texto)
    print(f"\nRecorte das seções A/B: {len(recorte)} caracteres.")
    print("\n--- Primeiros 500 caracteres do recorte A/B ---")
    print(recorte[:500])


if __name__ == "__main__":
    main()
