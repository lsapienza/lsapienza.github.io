# Site

Scaffold gerado a partir de [CONTEXT.md](CONTEXT.md) — a terminologia lá
definida (profile, dispatcher, counterpart, placeholder, language marker) é a
referência para tudo abaixo.

## Estrutura

```
_quarto.yml            config base, compartilhada pelos dois profiles
_quarto-en.yml          profile inglês (output em docs/en/)
_quarto-pt.yml          profile português (output em docs/pt/, é o default)
_includes/               partials compartilhados (ex.: language switch)
styles.css               estilo compartilhado
index.qmd / index.pt.qmd about.qmd / about.pt.qmd
blog.qmd / blog.pt.qmd   páginas do site, em pares EN / PT (contraparte
                          encontrada pelo slug, sufixo .pt opcional)
posts/                   posts do blog, mesmo esquema de pares .qmd / .pt.qmd
cv/                      PDFs de currículo (copiados como estão pelo build)
build.ps1                gera docs/: renderiza os dois profiles, resolve
                          posts placeholder, escreve o dispatcher e os
                          redirects de legacy URL
docs/                    saída publicável (gerada pelo CI a cada push em
                          main — não commitada, não editar manualmente)
.github/workflows/
  publish.yml            roda build.ps1 e publica docs/ no GitHub Pages
                          automaticamente a cada push em main
```

## Publicação

Automática: todo push em `main` dispara `.github/workflows/publish.yml`,
que roda `build.ps1` (sim, PowerShell — os runners do GitHub Actions já
vêm com `pwsh`) e publica `docs/` via GitHub Pages. Não precisa mais
rodar o build localmente nem commitar `docs/`.

**Configuração necessária no GitHub, uma vez só:** em Settings → Pages,
trocar "Source" para **GitHub Actions** (em vez de "Deploy from a
branch"). Sem isso o workflow builda mas o passo de deploy falha.

## Build local (prévia, sem publicar)

Requer o [Quarto CLI](https://quarto.org/docs/get-started/) no PATH.

```powershell
.\build.ps1
```

Para iterar em uma página só, sem passar pelo `build.ps1`:

```powershell
quarto preview --profile pt   # ou --profile en
```

## O que é placeholder e precisa de conteúdo real

- **Nome, bio, descrição do site** — em `index.qmd`/`index.pt.qmd`,
  `about.qmd`/`about.pt.qmd`, e no `website.title`/`website.description` de
  cada `_quarto-<profile>.yml`.
- **Posts de exemplo** em `posts/` — `hello-world.pt.qmd` demonstra o estado
  *placeholder* (só existe em PT); `second-post.qmd` / `second-post.pt.qmd`
  demonstram o estado *traduzido* (marcado com `en-version: true`). Ambos
  são exemplos e podem ser apagados quando houver posts reais.
- **CV PDFs** — `cv/` está vazio; ver `cv/README.md`.
- **Legacy URLs** — `$legacyRedirects` em `build.ps1` está vazio; preencher
  quando os endereços antigos do site em inglês forem conhecidos.
- **Estilo** — `styles.css` só define `max-width`; tema é o `cosmo` padrão
  do Quarto.

## Não testado

O Quarto CLI não está instalado nesta máquina, então nada aqui foi
renderizado ainda. Depois de instalar, rode `.\build.ps1` e confira
principalmente: a listagem de posts em `blog.qmd`/`blog.pt.qmd`, o
comportamento do post placeholder, e o language switch da navbar.
