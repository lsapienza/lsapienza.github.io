<#
Builds both versions of the site and assembles docs/ for publishing.

Steps:
  1. Materialize placeholder posts (PT posts with no EN counterpart and no
     en-version marker) as temporary EN copies, so Quarto's native listing
     picks them up like any other English post. See CONTEXT.md "Placeholder".
  2. Render the English profile, then the Portuguese profile.
  3. Write the root dispatcher (docs/index.html) that sends the bare root to
     /pt/, the default version. See CONTEXT.md "Dispatcher".
  4. Write legacy URL redirect stubs and copy CV PDFs outright.
     See CONTEXT.md "Legacy URL".

Requires the Quarto CLI on PATH: https://quarto.org/docs/get-started/
Run from the project root: .\build.ps1
#>

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

if (-not (Get-Command quarto -ErrorAction SilentlyContinue)) {
    Write-Error "Quarto CLI not found on PATH. Install it from https://quarto.org/docs/get-started/ before running this script."
    exit 1
}

$postsDir = Join-Path $root "posts"
$tempPlaceholders = @()

try {
    Write-Host "Resolving placeholder posts..." -ForegroundColor Cyan
    if (Test-Path $postsDir) {
        Get-ChildItem $postsDir -Filter "*.pt.qmd" | ForEach-Object {
            $slug = $_.BaseName -replace '\.pt$', ''
            $enSibling = Join-Path $postsDir "$slug.qmd"
            if (-not (Test-Path $enSibling)) {
                $frontMatter = Get-Content $_.FullName -Raw
                if ($frontMatter -notmatch '(?m)^en-version:\s*true\s*$') {
                    Copy-Item $_.FullName $enSibling
                    $tempPlaceholders += $enSibling
                    Write-Host "  Placeholder: posts/$($_.Name) -> posts/$slug.qmd (temporary)" -ForegroundColor DarkYellow
                }
            }
        }
    }

    Write-Host "Rendering English profile..." -ForegroundColor Cyan
    quarto render --profile en
}
finally {
    foreach ($temp in $tempPlaceholders) {
        Remove-Item $temp -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Rendering Portuguese profile..." -ForegroundColor Cyan
quarto render --profile pt

# --- Root dispatcher: sends the bare root to /pt/, the default version.
Write-Host "Writing root dispatcher..." -ForegroundColor Cyan
$dispatcher = @'
<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <title>Redirecionando...</title>
  <meta http-equiv="refresh" content="0; url=/pt/index.html">
  <link rel="canonical" href="/pt/index.html">
</head>
<body>
  <p>Redirecionando para <a href="/pt/index.html">/pt/</a>...</p>
</body>
</html>
'@
$docsDir = Join-Path $root "docs"
New-Item -ItemType Directory -Force -Path $docsDir | Out-Null
Set-Content -Path (Join-Path $docsDir "index.html") -Value $dispatcher -Encoding utf8

# --- Legacy URLs: English addresses from before /en/ existed. Add entries
# here as "old/path.html" = "en/new-path.html" once the real old paths are
# known (e.g. from analytics or an old sitemap). Empty by default.
$legacyRedirects = @{
    # "cv.html" = "en/about.html"
}
foreach ($old in $legacyRedirects.Keys) {
    $new = $legacyRedirects[$old]
    $stubPath = Join-Path $docsDir $old
    New-Item -ItemType Directory -Force -Path (Split-Path $stubPath) | Out-Null
    $stub = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=/$new">
  <link rel="canonical" href="/$new">
</head>
<body><p>Moved to <a href="/$new">/$new</a>.</p></body>
</html>
"@
    Set-Content -Path $stubPath -Value $stub -Encoding utf8
    Write-Host "  Legacy redirect: $old -> /$new" -ForegroundColor DarkYellow
}

# --- CV PDFs: copied outright, since a redirect stub can't stand in for a PDF.
$cvSourceDir = Join-Path $root "cv"
if (Test-Path $cvSourceDir) {
    Get-ChildItem $cvSourceDir -Filter "*.pdf" -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $docsDir $_.Name) -Force
        Write-Host "  Copied CV: $($_.Name)" -ForegroundColor DarkYellow
    }
}

Write-Host "Build complete. Output in docs/." -ForegroundColor Green
