param(
    [string]$Region = "southamerica-east1",
    [string]$Service = "pandora-service", # CORRIGIDO: Nome do serviço ajustado para 'pandora-service' que estamos usando no Cloud Run.
    [string]$Image = "gcr.io/pandora-474013/pandora-app:latest",
    [string]$CloudSqlInstance = "pandora-474013:southamerica-east1:pandora-db",
    [string]$EnvFile = "env.yaml"
)
Write-Host "[deploy_fast] Preparando..." -ForegroundColor Cyan
$gcloudCmdObj = Get-Command gcloud -ErrorAction SilentlyContinue
if ($gcloudCmdObj) { $gcloud = $gcloudCmdObj.Source } else { $gcloud = $null }
if (-not $gcloud) {
    $gcloud = Join-Path $env:USERPROFILE 'AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.ps1'
    if (-not (Test-Path $gcloud)) { Write-Host "[deploy_fast] ERRO: 'gcloud' não localizado." -ForegroundColor Red; exit 1 }
}
function Get-EnvVarsFromFile {
    param([string]$Path)
    if (!(Test-Path $Path)) { return @() }
    # CORRIGIDO: Ignora a primeira linha 'env_variables:' para ler apenas os pares chave-valor.
    $lines = Get-Content $Path | Select-Object -Skip 1 | Where-Object { $_ -match '^\s*[A-Z0-9_]+:' }
    $pairs = @()
    foreach ($l in $lines) {
        if ($l -match '^\s*([A-Z0-9_]+):\s*"?(.*?)"?\s*$') {
            $k = $matches[1]
            $v = $matches[2].Trim()
            if ($v -ne '') { $pairs += "$k=$v" }
        }
    }
    return $pairs
}

# Garante que o arquivo temporário será limpo no final
$envYaml = [System.IO.Path]::GetTempFileName() + '.yaml'

try {
    $envPairs = Get-EnvVarsFromFile -Path $EnvFile
    $envPairs = $envPairs | Where-Object { $_ -notmatch '^EMAIL_HOST_PASSWORD=' }
    if (-not ($envPairs -match '^ENABLE_WHITENOISE=')) { $envPairs += 'ENABLE_WHITENOISE=1' }

    Write-Host "[deploy_fast] Variáveis detectadas: $($envPairs.Count) (mascarando sensíveis)" -ForegroundColor DarkGray
    foreach ($p in $envPairs) { if ($p -match 'DJANGO_SECRET_KEY=') { Write-Host '[env] DJANGO_SECRET_KEY=***' -ForegroundColor DarkGray } }

    powershell -ExecutionPolicy Bypass -File $gcloud builds submit --tag $Image --quiet
    if ($LASTEXITCODE -ne 0) { throw "Build falhou (exit $LASTEXITCODE)" }

    Write-Host "[deploy_fast] Preparando arquivo YAML para --env-vars-file..." -ForegroundColor Cyan
    if (-not ($envPairs -match '^DJANGO_DEBUG=')) { $envPairs += 'DJANGO_DEBUG=False' }
    
    $dict = @{}
    foreach ($p in $envPairs) { $kv = $p.Split('=', 2); if ($kv.Count -eq 2) { $dict[$kv[0]] = $kv[1] } }
    
    $yamlLines = @()
    foreach ($k in $dict.Keys) {
        $val = $dict[$k]
        if ($null -eq $val) { continue }
        $val = [string]$val
        $val = $val -replace '\\', '\\\\' -replace '"', '\"'
        $val = $val -replace "`r", ""
        # CORRIGIDO: Formatação da linha YAML para ser válida (sem espaço extra dentro das aspas).
        $yamlLines += ('{0}: "{1}"' -f $k, $val)
    }
    
    # CORRIGIDO: Salva o arquivo temporário no formato UTF-8 SEM o caractere BOM que causa o erro.
    $utf8NoBOM = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($envYaml, $yamlLines, $utf8NoBOM)

    Write-Host "[deploy_fast] env-vars YAML: $envYaml" -ForegroundColor DarkGray
    Write-Host "[deploy_fast] Preview YAML:" -ForegroundColor DarkGray
    Get-Content $envYaml | Select-Object -First 6 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }

    Write-Host "[deploy_fast] Deploy iniciando (usando --env-vars-file)..." -ForegroundColor Cyan
    powershell -ExecutionPolicy Bypass -File $gcloud run deploy $Service `
        --image $Image `
        --region $Region `
        --platform managed `
        --allow-unauthenticated `
        --add-cloudsql-instances $CloudSqlInstance `
        --env-vars-file $envYaml `
        --quiet
        
    if ($LASTEXITCODE -ne 0) { throw "Deploy falhou (exit $LASTEXITCODE)" }
    Write-Host "[deploy_fast] Concluído com sucesso." -ForegroundColor Green
}
catch {
    Write-Error "[deploy_fast] Erro: $_"; exit 1
}
finally {
    # Limpa o arquivo temporário, não importa se deu erro ou sucesso
    if (Test-Path $envYaml) {
        Remove-Item $envYaml -Force
        Write-Host "[deploy_fast] Arquivo temporário limpo." -ForegroundColor DarkGray
    }
}

