#############################
# AUTO SETUP GCP SIMPLIFICADO
#############################
$ErrorActionPreference = 'Stop'

# Valores padrão (altere aqui se quiser)
$Project = [System.Environment]::GetEnvironmentVariable('PANDORA_GCP_PROJECT'); if ([string]::IsNullOrEmpty($Project)) { $Project = 'pandora-474013' }
$Instance = [System.Environment]::GetEnvironmentVariable('PANDORA_GCP_INSTANCE'); if ([string]::IsNullOrEmpty($Instance)) { $Instance = 'pandora' }
$Region = [System.Environment]::GetEnvironmentVariable('PANDORA_GCP_REGION'); if ([string]::IsNullOrEmpty($Region)) { $Region = 'us-central1' }
$DbName = [System.Environment]::GetEnvironmentVariable('PANDORA_DB_NAME'); if ([string]::IsNullOrEmpty($DbName)) { $DbName = 'pandora_app' }
$DbUser = [System.Environment]::GetEnvironmentVariable('PANDORA_DB_USER'); if ([string]::IsNullOrEmpty($DbUser)) { $DbUser = 'pandora_user' }
$DbPassword = [System.Environment]::GetEnvironmentVariable('PANDORA_DB_PASSWORD')
$PostgresAdminPassword = [System.Environment]::GetEnvironmentVariable('PANDORA_PG_ADMIN_PASS')
$ResetDb = $false; if ([System.Environment]::GetEnvironmentVariable('PANDORA_DB_RESET') -eq '1') { $ResetDb = $true }
$SeedTenants = $false; if ([System.Environment]::GetEnvironmentVariable('PANDORA_SEED_TENANTS') -eq '1') { $SeedTenants = $true }
$SeedTenantCodes = [System.Environment]::GetEnvironmentVariable('PANDORA_SEED_TENANTS_CODES'); if ([string]::IsNullOrEmpty($SeedTenantCodes)) { $SeedTenantCodes = '01,02' }
$SkipDeploy = $false
if ([System.Environment]::GetEnvironmentVariable('PANDORA_SKIP_DEPLOY') -eq '1') { $SkipDeploy = $true }

function Log($l, $m) {
    $color = 'White'
    if ($l -eq 'INFO') { $color = 'Cyan' } elseif ($l -eq 'WARN') { $color = 'Yellow' } elseif ($l -eq 'ERRO') { $color = 'Red' }
    Write-Host ("[$l] $m") -ForegroundColor $color
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) { Log ERRO 'gcloud não encontrado'; exit 1 }
if (-not (Test-Path env.yaml)) { Log ERRO 'env.yaml não encontrado'; exit 1 }

if ([string]::IsNullOrWhiteSpace($DbPassword)) {
    Log INFO "Gerando senha forte para $DbUser"
    $DbPassword = -join ((33..126) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    if ($DbPassword -notmatch '[!@#$%^&*]') { $DbPassword += '!' }
    if ($DbPassword -notmatch '\d') { $DbPassword += '9' }
}

Log INFO 'Habilitando APIs'
gcloud services enable appengine.googleapis.com sqladmin.googleapis.com --project $Project | Out-Null

$appExists = $true; try { gcloud app describe --project $Project | Out-Null } catch { $appExists = $false }
if (-not $appExists) { Log INFO "Criando App Engine ($Region)"; gcloud app create --project $Project --region $Region | Out-Null } else { Log INFO 'App Engine já existe' }

$instanceExists = $true; try { gcloud sql instances describe $Instance --project $Project | Out-Null } catch { $instanceExists = $false }
if (-not $instanceExists) {
    Log INFO "Criando instância Cloud SQL $Instance"
    gcloud sql instances create $Instance --project $Project --database-version POSTGRES_17 --tier db-f1-micro --region $Region --storage-auto-increase | Out-Null
}
else { Log INFO 'Instância Cloud SQL já existe' }

if ($PostgresAdminPassword) {
    Log INFO 'Atualizando senha do postgres (admin)'
    gcloud sql users set-password postgres --instance $Instance --project $Project --password $PostgresAdminPassword | Out-Null
}

# Nome de conexão Cloud SQL (formato projeto:região:instância) usando format para evitar parsing de ':'
$connNameReal = "{0}:{1}:{2}" -f $Project, $Region, $Instance

$dbs = gcloud sql databases list --instance $Instance --project $Project --format 'value(name)'
if ($ResetDb -and ($dbs -split "\r?\n" | Where-Object { $_ -eq $DbName })) {
    Log WARN "Reset solicitado: removendo database existente $DbName"
    gcloud sql databases delete $DbName --instance $Instance --project $Project --quiet | Out-Null
    # Atualiza lista após remoção
    $dbs = gcloud sql databases list --instance $Instance --project $Project --format 'value(name)'
}
if (-not ($dbs -split "\r?\n" | Where-Object { $_ -eq $DbName })) {
    Log INFO "Criando database $DbName (limpo)"
    gcloud sql databases create $DbName --instance $Instance --project $Project | Out-Null
}
else { Log INFO 'Database já existe (nenhum reset solicitado)' }

$users = gcloud sql users list --instance $Instance --project $Project --format 'value(name)'
if (-not ($users -split "\r?\n" | Where-Object { $_ -eq $DbUser })) {
    Log INFO "Criando usuário $DbUser"
    gcloud sql users create $DbUser --instance $Instance --project $Project --password $DbPassword | Out-Null
}
else { Log INFO 'Usuário já existe – ajustando senha'; gcloud sql users set-password $DbUser --instance $Instance --project $Project --password $DbPassword | Out-Null }

function Encode([string]$s) { $bytes = [System.Text.Encoding]::UTF8.GetBytes($s); $sb = New-Object System.Text.StringBuilder; foreach ($b in $bytes) { $ch = [char]$b; if ($ch -match '[A-Za-z0-9._~-]') { [void]$sb.Append($ch) } else { [void]$sb.AppendFormat('%{0:X2}', $b) } }; $sb.ToString() }
$passEnc = Encode $DbPassword
$dbUrl = 'postgres://' + $DbUser + ':' + $passEnc + '@/' + $DbName + '?host=/cloudsql/' + $connNameReal

Log INFO 'Atualizando DATABASE_URL em env.yaml'
$existing = Get-Content env.yaml
$other = $existing | Where-Object { ($_ -notmatch '^\s*DATABASE_URL:') -and ($_ -notmatch '^\s*PANDORA_SEED_TENANTS:') -and ($_ -notmatch '^\s*PANDORA_SEED_TENANTS_CODES:') }
$seedFlag = if ($SeedTenants) { '1' } else { '0' }
$linesOut = @()
foreach ($l in $other) { $linesOut += $l }
$linesOut += ('  DATABASE_URL: "' + $dbUrl + '"')
$linesOut += ('  PANDORA_SEED_TENANTS: "' + $seedFlag + '"')
if ($SeedTenants) { $linesOut += ('  PANDORA_SEED_TENANTS_CODES: "' + $SeedTenantCodes + '"') }
$linesOut | Set-Content env.yaml -Encoding UTF8

if (-not $SkipDeploy) {
    Log INFO 'Deployando...'
    gcloud app deploy app.yaml --quiet --project $Project
    Log INFO 'Logs (CTRL+C para parar)'
    gcloud app logs tail -s default --project $Project
}
else { Log WARN 'SkipDeploy=1 -> sem deploy' }

Write-Host "`n================= RESUMO =================" -ForegroundColor Green
Write-Host ('Projeto:        ' + $Project)
Write-Host ('Instância:      ' + $Instance)
Write-Host ('ConnectionName (deploy): ' + $connNameReal)
Write-Host ('Database:       ' + $DbName)
Write-Host ('User:           ' + $DbUser)
Write-Host ('Senha (plana):  ' + $DbPassword) -ForegroundColor Yellow
Write-Host ('Senha (URL):    ' + $passEnc)
Write-Host ('DATABASE_URL:   ' + $dbUrl)
Write-Host ('Reset DB:       ' + ($ResetDb))
Write-Host ('Seed Tenants:   ' + ($SeedTenants))
if ($SeedTenants) { Write-Host ('Tenants Codes:  ' + $SeedTenantCodes) }
Write-Host '==========================================='
