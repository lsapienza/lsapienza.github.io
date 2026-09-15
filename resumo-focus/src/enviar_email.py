"""Envia o resumo executivo do Boletim Focus por e-mail via API do Resend.

Este módulo é puramente mecânico: localiza o HTML mais recente gerado em
output/focus/ e o envia como corpo do e-mail. Não interpreta nem reescreve
o conteúdo (ver CLAUDE.md — princípio de separação entre determinístico e
julgamento).

Usamos a API do Resend (REST simples via `requests`) em vez de SMTP do
Gmail: contas Gmail nem sempre disponibilizam "senha de app" (depende de
política da conta/organização — 2FA obrigatória, e mesmo assim algumas
contas simplesmente não têm a opção), então uma API baseada em chave é mais
previsível para automação.

Credenciais NUNCA são hardcoded: vêm sempre de variáveis de ambiente (no
CI, de GitHub Secrets):
    RESEND_API_KEY               chave de API do Resend (resend.com)
    FOCUS_EMAIL_REMETENTE         remetente (opcional; ver REMETENTE_PADRAO)
    FOCUS_EMAIL_DESTINATARIOS     destinatários, separados por vírgula
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import requests

RESEND_API_URL = "https://api.resend.com/emails"
# onboarding@resend.dev é o domínio de testes do Resend: funciona sem
# verificar domínio próprio, mas só entrega para o e-mail da conta Resend
# cadastrada. Para enviar a destinatários variados no futuro, troque via
# FOCUS_EMAIL_REMETENTE por um endereço de um domínio verificado.
REMETENTE_PADRAO = "Boletim Focus <onboarding@resend.dev>"
PASTA_HTML_PADRAO = Path("output/focus")

logger = logging.getLogger(__name__)


class ConfiguracaoAusente(RuntimeError):
    """Erro para variável de ambiente obrigatória não configurada."""


def encontrar_html_mais_recente(pasta: Path = PASTA_HTML_PADRAO) -> Path:
    """Localiza o .html mais recente pelo nome (focus_AAAA-MM-DD.html ordena
    cronologicamente por ser ISO 8601)."""
    arquivos = sorted(pasta.glob("focus_*.html"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum HTML encontrado em {pasta}")
    return arquivos[-1]


def assunto_do_arquivo(caminho_html: Path) -> str:
    """Deriva o assunto do e-mail a partir do nome do arquivo (data de referência)."""
    data_referencia = caminho_html.stem.removeprefix("focus_")
    return f"Boletim Focus — Resumo Executivo ({data_referencia})"


def ler_variavel_obrigatoria(nome: str) -> str:
    """Lê uma variável de ambiente obrigatória, ou levanta erro claro se ausente."""
    valor = os.environ.get(nome)
    if not valor:
        raise ConfiguracaoAusente(f"Variável de ambiente '{nome}' não configurada.")
    return valor


def destinatarios_do_ambiente(variavel: str = "FOCUS_EMAIL_DESTINATARIOS") -> list[str]:
    """Lê e separa a lista de destinatários (separados por vírgula)."""
    bruto = ler_variavel_obrigatoria(variavel)
    return [endereco.strip() for endereco in bruto.split(",") if endereco.strip()]


def montar_payload(
    html: str, remetente: str, destinatarios: list[str], assunto: str
) -> dict:
    """Monta o corpo JSON esperado pela API do Resend."""
    return {
        "from": remetente,
        "to": destinatarios,
        "subject": assunto,
        "html": html,
    }


def enviar_via_resend(payload: dict, api_key: str) -> None:
    """Envia o e-mail através da API REST do Resend."""
    resposta = requests.post(
        RESEND_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if not resposta.ok:
        raise RuntimeError(
            f"Resend recusou o envio (HTTP {resposta.status_code}): {resposta.text}"
        )


def enviar_resumo_mais_recente(pasta_html: Path = PASTA_HTML_PADRAO) -> Path:
    """Ponto de entrada: localiza o HTML mais recente e envia por e-mail."""
    caminho_html = encontrar_html_mais_recente(pasta_html)
    html = caminho_html.read_text(encoding="utf-8")

    api_key = ler_variavel_obrigatoria("RESEND_API_KEY")
    remetente = os.environ.get("FOCUS_EMAIL_REMETENTE", REMETENTE_PADRAO)
    destinatarios = destinatarios_do_ambiente()

    payload = montar_payload(
        html=html,
        remetente=remetente,
        destinatarios=destinatarios,
        assunto=assunto_do_arquivo(caminho_html),
    )
    enviar_via_resend(payload, api_key=api_key)
    return caminho_html


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Envia por e-mail o resumo executivo do Focus mais recente."
    )
    parser.add_argument(
        "--pasta-html",
        type=Path,
        default=PASTA_HTML_PADRAO,
        help="Pasta onde procurar o HTML mais recente (padrão: output/focus)",
    )
    args = parser.parse_args()

    caminho_html = enviar_resumo_mais_recente(args.pasta_html)
    logger.info("E-mail enviado com o conteúdo de %s", caminho_html)


if __name__ == "__main__":
    main()
