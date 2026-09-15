# Índice de Tom do Copom — Briefing do Projeto

## Objetivo

Construir um **Índice de Tom** das atas do Comitê de Política Monetária
(Copom), numa escala contínua de **-3 (muito dovish) a +3 (muito hawkish)**,
e **calibrá-lo contra a variação efetiva da Selic** na reunião seguinte à
publicação de cada ata.

A hipótese de trabalho: o tom da ata — hawkish (sinaliza aperto monetário) ou
dovish (sinaliza afrouxamento) — carrega informação que antecipa ou explica a
decisão de juros subsequente. O produto final é um **paper em Quarto**
reportando a construção do índice, a comparação entre os métodos de
classificação e a força dessa relação.

## Fontes de dados

1. **Atas do Copom** — API pública do Banco Central em `bcb.gov.br`
   (Copom / atas de reunião). Cada ata é um documento de texto associado a
   uma reunião numerada e datada.
2. **Série SGS 432 (Selic)** — Sistema Gerenciador de Séries Temporais do
   BCB, série 432, meta Selic definida pelo Copom. Usada para calcular a
   variação (Δ) da Selic entre reuniões consecutivas, que serve de variável
   de calibração/validação do índice de tom.

Nenhuma outra fonte substitui estas duas para os números centrais do paper.

## Metodologia — CRISP-DM

O projeto segue as fases do CRISP-DM:

1. **Business Understanding** — definido acima: prever/explicar Δ-Selic a
   partir do tom textual da ata.
2. **Data Understanding** — coleta e inspeção das atas (texto bruto) e da
   série 432; checagem de cobertura temporal, datas de reunião e alinhamento
   ata → decisão seguinte.
3. **Data Preparation** — limpeza e segmentação do texto das atas;
   construção do dataset alinhado (ata, data, Δ-Selic subsequente).
4. **Modeling** — quatro classificadores de tom rodando em paralelo sobre o
   mesmo texto:
   - Baseline léxico (dicionário hawkish/dovish, sem LLM);
   - LLM #1 — Gemini;
   - LLM #2 — Claude;
   - LLM #3 — OpenAI.
   Cada um produz uma nota na escala -3 a +3 por ata.
5. **Evaluation** — calibração/correlação de cada índice (baseline e cada
   LLM) contra a variação real da Selic; comparação entre os quatro métodos.
6. **Deployment** — o paper em Quarto, com todas as tabelas e gráficos
   gerados a partir do pipeline de dados, não escritos à mão.

## REGRA DE OURO

**Nunca inventar um número.** Todo valor citado no paper — índice de tom,
Δ-Selic, correlação, estatística de qualquer tipo — precisa vir do resultado
de uma célula que efetivamente roda no notebook/Quarto. Nada de números
"de memória", estimados de cabeça ou copiados de uma execução anterior sem
re-executar. Se um valor não pode ser reproduzido a partir do código no
documento, ele não entra no paper.

## Status

Projeto em fase inicial. Próximos passos: definir e preencher
`requirements.txt`, estruturar o pipeline de coleta (atas + SGS 432).
