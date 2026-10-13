# Publicação semanal do Focus no site (lsapienza.github.io/focus/)

Mesmo esquema do calendário econômico (`/calendario/`): uma página HTML pronta,
fora do Quarto, que o `build.ps1` copia para `docs/focus/`. A página fica no
menu do site como "Boletim Focus".

## Etapas

| # | Quem | O quê |
|---|---|---|
| 1 | GitHub Actions (`focus-download.yml`, seg. 08h30) | Baixa o PDF e extrai o texto para `data/focus_AAAA-MM-DD.{pdf,txt}` (data = sexta de referência). |
| 2 | Script (`src/tabular_focus.py`) | Texto extraído → JSON com os valores **como strings literais** (sem arredondar nem calcular). |
| 3 | Claude (tarefa agendada `boletim-focus`) | Escreve só os "Destaques da semana" e monta a página com o JSON do passo 2. |
| 4 | Commit em `main` | `focus/index.html` + cópia em `focus/arquivo/AAAA-MM-DD.html`; o push dispara `publish.yml`. |

## Roteiro da tarefa agendada

1. `git pull` em `C:\Sapienza\VSC\Site`.
2. Se não houver `data/focus_*.txt` da última sexta (feriado, Action atrasada),
   rodar `baixar_focus.py` + `extrair_texto.py` localmente e commitar os dois arquivos.
3. `python src/tabular_focus.py data/focus_AAAA-MM-DD.txt > focus.json`
   (se o script falhar, o layout do PDF mudou: não publicar com números digitados à mão).
4. Copiar `focus/index.html` da semana anterior como modelo e trocar: título,
   subtítulo, a constante `D=` (JSON do passo 3), o comentário com o nome do
   .txt e a lista de destaques.
5. Destaques: 4 a 6 itens. **Todo número citado precisa aparecer no .txt da
   semana** (ver "Regra de ouro" no CLAUDE.md). Nada de diferenças calculadas
   (ex.: "corte de 0,25 p.p.") nem valores de semanas anteriores que não estejam
   nas colunas "Há 1/Há 4 semanas" do relatório atual.
6. Conferir a página (servidor local + navegador), commitar e dar push.

## Etapas antigas (e-mail e post de blog)

`focus-email.yml` e `focus-blog.yml` continuam no repositório, mas só disparam
quando chega um `output/focus/focus_*.html`, o que não acontece desde 11/09/2026.
O site passou a ser o canal principal. Se o e-mail voltar a ser desejado, basta
a tarefa agendada também gerar esse HTML.
