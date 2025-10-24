# Setup Fly.io Postgres for Pandora (Windows PowerShell)
# Pré-requisitos: flyctl instalado e autenticado (flyctl auth login)
# Uso:
#   1) Abra um PowerShell na raiz do projeto
#   2) Execute: ./scripts/setup_fly_postgres.ps1

param(
    [string]$AppName = 'sistema-pandora',
    [string]$PgName = 'sistema-pandora-pg',
    [string]$Region = 'gru',
    [int]$VolumeSizeGB = 10,
    [switch]$SkipCreate,
    [string]$DatabaseUrl,
    [switch]$RemoveOldMachines
)

Write-Host "[fly-setup] App: $AppName  | PG: $PgName  | Region: $Region  | Vol: ${VolumeSizeGB}GB"

# Verifica flyctl
$fly = (Get-Command flyctl -ErrorAction SilentlyContinue)
if (-not $fly) { Write-Error "flyctl não encontrado. Instale o Fly CLI e rode 'flyctl auth login'."; exit 1 }

# Confirma login
try {
    flyctl auth whoami | Out-Null
}
catch {
    Write-Host "[fly-setup] Autentique-se: abrindo login do Fly.io..."
    flyctl auth login
}

# Mostra status da app (opcional)
Write-Host "[fly-setup] App status (se existir):"
try { flyctl status -a $AppName --json | Out-Null } catch { Write-Host "[fly-setup] App ainda pode não existir (ok)" }

if (-not $SkipCreate) {
    # Cria cluster Postgres (ignora erro se já existir)
    Write-Host "[fly-setup] Criando cluster Postgres (se não existir)..."
    $createArgs = @('pg', 'create', '--name', $PgName, '--region', $Region, '--vm-size', 'shared-cpu-1x', '--volume-size', "$VolumeSizeGB")
    try {
        flyctl @createArgs
    }
    catch {
        Write-Host "[fly-setup] Aviso: criação falhou (talvez já exista): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}
else {
    Write-Host "[fly-setup] SkipCreate=true -> pulando criação do cluster; usaremos existente: $PgName"
}

if ($DatabaseUrl) {
    Write-Host "[fly-setup] Definindo DATABASE_URL a partir do valor fornecido..."
    flyctl secrets set DATABASE_URL=$DatabaseUrl -a $AppName
}
else {
    # Anexa cluster à app (cria DATABASE_URL)
    Write-Host "[fly-setup] Anexando o cluster à app (DATABASE_URL)..."
    try {
        flyctl pg attach --app $AppName $PgName
    }
    catch {
        Write-Host "[fly-setup] Aviso: attach falhou (talvez já esteja anexado ou cluster não encontrado): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Lista secrets para conferir DATABASE_URL
Write-Host "[fly-setup] Conferindo secrets (procure por DATABASE_URL):"
try { flyctl secrets list -a $AppName } catch { Write-Host "[fly-setup] Não foi possível listar secrets: $($_.Exception.Message)" -ForegroundColor Yellow }

# Opcional: remover máquinas antigas (útil quando há volumes no machine atual)
if ($RemoveOldMachines) {
    Write-Host "[fly-setup] Removendo máquinas antigas da app $AppName..."
    try {
        $machinesJson = flyctl machines list -a $AppName --json 2>$null
        if ($LASTEXITCODE -eq 0 -and $machinesJson) {
            $machines = $machinesJson | ConvertFrom-Json
            foreach ($m in $machines) {
                if ($m.id) {
                    Write-Host "[fly-setup] Removendo máquina ${($m.id)}..."
                    flyctl machines remove $m.id -a $AppName --force
                }
            }
        }
        else {
            Write-Host "[fly-setup] Nenhuma máquina listada ou falha ao listar (ok)." -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "[fly-setup] Falha ao remover máquinas antigas: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Deploy (usa fly.toml)
Write-Host "[fly-setup] Fazendo deploy (remote-only)..."
flyctl deploy --remote-only --strategy immediate --wait-timeout 600

# Migrações
Write-Host "[fly-setup] Executando migrações no servidor..."
flyctl ssh console -C "python manage.py migrate --noinput" -a $AppName

Write-Host "[fly-setup] Concluído. Sua app deve estar usando PostgreSQL gerenciado."
