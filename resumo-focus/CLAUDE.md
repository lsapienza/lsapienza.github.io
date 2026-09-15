# resumo-focus

## O que é

Automação do acompanhamento do **Boletim Focus** do Banco Central do Brasil.
O Focus é um relatório semanal (PDF), publicado em
https://www.bcb.gov.br/publicacoes/focus, com as medianas das expectativas do
mercado para IPCA, Selic, PIB, câmbio e outros indicadores. Este projeto baixa
o PDF, extrai o texto e transforma isso em um **resumo executivo enviado por
e-mail**, toda semana, sem intervenção manual.

## Princípio de design central

**Separar rigorosamente o determinístico do que exige julgamento.**

| Camada | Responsabilidade | Natureza |
|---|---|---|
| Scripts Python | Baixar o PDF e extrair o texto bruto | Determinística — nunca interpreta, nunca resume, nunca decide o que é relevante |
| Agente Claude | Ler o texto extraído e redigir o resumo executivo | Julgamento — única camada que interpreta significado |
| GitHub Actions | Orquestrar o fluxo semanal (agendamento, execução, envio) | Determinística — cola as etapas, não decide conteúdo |

Isso não é só uma preferência de arquitetura: é a garantia de que erros de
interpretação (alucinação, viés, leitura errada de tabela) fiquem confinados à
camada que sabemos que pode errar, e que tudo o que é mecânico (download,
parsing, envio de e-mail) seja auditável e determinístico. Se um número está
errado no e-mail final, a causa só pode estar na etapa de redação do agente —
nunca no código Python.

Consequência prática: os scripts Python **não devem conter nenhuma lógica de
"o que é importante" ou "como interpretar"** — isso incluiu não filtrar
indicadores por relevância, não arredondar/ajustar valores, não gerar
frases prontas. Eles só movem e extraem texto.

## REGRA DE OURO: nunca inventar número

Toda mediana, projeção ou valor numérico citado no resumo final precisa
**estar literalmente presente no texto extraído do PDF**. O agente não pode:

- calcular, estimar ou interpolar um valor que não apareça no texto-fonte;
- "arredondar de cabeça" ou "lembrar" de um valor de uma semana anterior;
- preencher lacunas quando a extração do PDF vier incompleta ou malformada.

Se um número necessário não estiver claramente presente no texto extraído, o
resumo deve **dizer explicitamente que a informação não foi encontrada**, em
vez de inferir ou aproximar. É preferível um resumo incompleto a um resumo
com um número inventado. Esta regra é inegociável e vale mais que qualquer
outra consideração de estilo ou completude do resumo.

## Fluxo (visão geral)

1. **Download** (Python): busca a página do Focus, localiza o link do PDF
   mais recente, baixa o arquivo.
2. **Extração** (Python): converte o PDF em texto bruto (ou estrutura mínima,
   como texto por página/seção), sem interpretação.
3. **Redação** (Claude): recebe o texto extraído e produz o resumo executivo,
   citando apenas números que aparecem literalmente no texto.
4. **Envio** (Python + GitHub Actions): formata o resumo em e-mail e envia.
5. **Orquestração** (GitHub Actions): roda o fluxo em agenda semanal (o Focus
   é publicado às segundas-feiras) e trata falhas de cada etapa de forma
   isolada.

## Estrutura de pastas proposta

```
resumo-focus/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example              # variáveis de ambiente (credenciais de e-mail etc.)
├── .github/
│   └── workflows/
│       └── focus-semanal.yml # orquestração: agenda + chama as etapas em sequência
├── src/
│   ├── download/
│   │   └── baixar_pdf.py     # localiza e baixa o PDF mais recente do Focus
│   ├── extract/
│   │   └── extrair_texto.py  # PDF -> texto bruto, sem interpretação
│   ├── summarize/
│   │   └── prompt_resumo.md  # prompt/instruções para o agente Claude redigir o resumo
│   └── deliver/
│       └── enviar_email.py   # formata e envia o e-mail com o resumo
├── data/
│   ├── pdfs/                 # PDFs baixados (histórico bruto)
│   └── textos/               # texto extraído de cada PDF (histórico bruto)
└── tests/
    ├── test_download.py
    ├── test_extract.py
    └── test_deliver.py
```

Notas sobre a estrutura:

- `data/pdfs/` e `data/textos/` guardam o histórico bruto — úteis para
  auditoria (comparar o e-mail enviado com a fonte original) e para
  depuração caso a extração falhe numa semana.
- `src/summarize/` não contém lógica de execução do agente, apenas o prompt/
  instruções que orientam a redação — a execução do agente acontece fora do
  código Python (invocada pela orquestração).
- Cada etapa em `src/` é independente e testável isoladamente, reforçando a
  separação de responsabilidades.

## Decisões ainda em aberto

- Formato de saída da extração (texto corrido vs. estrutura por
  indicador/tabela) — a definir conforme a complexidade real do PDF do Focus.
- Serviço de envio de e-mail (SMTP direto, SendGrid, etc.).
- Onde/como o agente Claude é invocado dentro do GitHub Actions (Claude Code
  Action, API direta, etc.).
