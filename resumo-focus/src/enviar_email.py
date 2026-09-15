"""Envia o resumo executivo do Boletim Focus por e-mail (Gmail SMTP).

Este módulo é puramente mecânico: localiza o HTML mais recente gerado em
output/focus/ e o envia como corpo do e-mail. Não interpreta nem reescreve
o conteúdo (ver CLAUDE.md — princípio de separação entre determinístico e
julgamento).

Credenciais NUNCA são hardcoded: vêm sempre de variáveis de ambiente (no
CI, de GitHub Secrets):
    GMAIL_USUARIO               endereço Gmail usado para autenticar e enviar
    GMAIL_SENHA_APP              senha de app do Gmail (não é a senha da conta)
    FOCUS_EMAIL_DESTINATARIOS    destinatários, separados por vírgula
"""
from __future__ import annotations

import argparse
import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

SERVIDOR_SMTP_GMAIL = "smtp.gmail.com"
PORTA_SMTP_SSL = 465
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


def montar_mensagem(
    html: str, remetente: str, destinatarios: list[str], assunto: str
) -> EmailMessage:
    """Monta a mensagem MIME com o HTML como corpo (e um texto simples de fallback)."""
    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = remetente
    mensagem["To"] = ", ".join(destinatarios)
    mensagem.set_content(
        "Este e-mail contém HTML. Ative a visualização em HTML para lê-lo."
    )
    mensagem.add_alternative(html, subtype="html")
    return mensagem


def enviar_mensagem(
    mensagem: EmailMessage,
    usuario: str,
    senha: str,
    servidor: str = SERVIDOR_SMTP_GMAIL,
    porta: int = PORTA_SMTP_SSL,
) -> None:
    """Autentica e envia a mensagem via SMTP com SSL."""
    with smtplib.SMTP_SSL(servidor, porta) as smtp:
        smtp.login(usuario, senha)
        smtp.send_message(mensagem)


def enviar_resumo_mais_recente(pasta_html: Path = PASTA_HTML_PADRAO) -> Path:
    """Ponto de entrada: localiza o HTML mais recente e envia por e-mail."""
    caminho_html = encontrar_html_mais_recente(pasta_html)
    html = caminho_html.read_text(encoding="utf-8")

    usuario = ler_variavel_obrigatoria("GMAIL_USUARIO")
    senha = ler_variavel_obrigatoria("GMAIL_SENHA_APP")
    destinatarios = destinatarios_do_ambiente()

    mensagem = montar_mensagem(
        html=html,
        remetente=usuario,
        destinatarios=destinatarios,
        assunto=assunto_do_arquivo(caminho_html),
    )
    enviar_mensagem(mensagem, usuario=usuario, senha=senha)
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
