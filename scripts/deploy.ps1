param(
  [string]$SshTarget = "root@69.6.250.186",
  [int]$Port = 22022,
  [string]$Branch = "main",
  [string]$ProjectDir = "/opt/pandora",
  [string]$Service = "web",
  [string]$RepoUrl = "",
  [switch]$Maintenance
)

# Fail fast in PowerShell
$ErrorActionPreference = "Stop"

function Test-ToolExists {
  param([string]$Tool)
  if (-not (Get-Command $Tool -ErrorAction SilentlyContinue)) {
    throw "Ferramenta obrigatória não encontrada: $Tool"
  }
}

function Test-SSHReachable {
  param(
    [string]$Target,
    [int]$Port
  )
  Write-Host "[local] Testando conexão SSH com ${Target}:$Port..." -ForegroundColor Cyan
  $cmd = @(
    "-p", $Port,
    "-o", "ConnectTimeout=10",
    "-o", "StrictHostKeyChecking=accept-new",
    $Target,
    "echo '[remote] reachable'"
  )
  & ssh @cmd | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "Falha ao conectar via SSH em ${Target}:$Port" }
}

function Invoke-RemoteScript {
  param(
    [string]$Target,
    [int]$Port,
    [string]$ScriptContent
  )
  Write-Host "[local] Executando script remoto..." -ForegroundColor Cyan
  $cmd = @(
    "-p", $Port,
    "-o", "ConnectTimeout=10",
    "-o", "StrictHostKeyChecking=accept-new",
    $Target,
    "bash -s"
  )
  # Normaliza EOL para LF para evitar erros no bash remoto (CRLF causa "invalid option").
  $normalized = $ScriptContent -replace "`r`n", "`n" -replace "`r", "`n"
  $normalized | & ssh @cmd
  if ($LASTEXITCODE -ne 0) { throw "Script remoto retornou código $LASTEXITCODE" }
}

# Pré-checagens
Test-ToolExists -Tool "ssh"

# Exibe parâmetros efetivos
Write-Host "Host:       $SshTarget" -ForegroundColor Yellow
Write-Host "Porta:      $Port" -ForegroundColor Yellow
Write-Host "Branch:     $Branch" -ForegroundColor Yellow
Write-Host "Projeto:    $ProjectDir" -ForegroundColor Yellow
Write-Host "Serviço:    $Service" -ForegroundColor Yellow
Write-Host "Manutenção: $($Maintenance.IsPresent)" -ForegroundColor Yellow
$repoDisplay = if ([string]::IsNullOrWhiteSpace($RepoUrl)) { 'N/A' } else { $RepoUrl }
Write-Host "Repo URL:   $repoDisplay" -ForegroundColor Yellow

# Valida conexão SSH e aceita host key (se primeira vez)
Test-SSHReachable -Target $SshTarget -Port $Port

# Monta script remoto (Bash) com placeholders substituídos
$remoteScript = @'
#!/usr/bin/env bash
# Modo seguro com fallback: ativa -e e -u sempre; ativa pipefail apenas se suportado.
set -e
set -u
if set -o 2>/dev/null | grep -q 'pipefail'; then
  set -o pipefail
fi

PROJECT_DIR="__PROJECT_DIR__"
BRANCH="__BRANCH__"
SERVICE="__SERVICE__"
MAINT="__MAINT__"
REPO_URL="__REPO_URL__"

log(){ echo -e "[remote] $1"; }

log "Acessando diretório: ${PROJECT_DIR}"
mkdir -p "${PROJECT_DIR}"
cd "${PROJECT_DIR}"

log "Preparando variáveis de ambiente (.env) para Postgres"
if [ ! -f .env ]; then
  touch .env
fi

# Função para definir ou atualizar chave=valor em .env
ensure_kv(){
  local key="$1"; local val="$2";
  if grep -q "^${key}=" .env 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|g" .env
  else
    echo "${key}=${val}" >> .env
  fi
}

# Garante valores padrão para o Postgres local (em Docker)
if ! grep -q '^POSTGRES_DB=' .env 2>/dev/null; then ensure_kv POSTGRES_DB pandora_db; fi
if ! grep -q '^POSTGRES_USER=' .env 2>/dev/null; then ensure_kv POSTGRES_USER pandora_app; fi
if ! grep -q '^POSTGRES_PASSWORD=' .env 2>/dev/null; then
  # Gera senha forte com charset seguro para URL (evita precisar url-encode)
  PWGEN=$(tr -dc 'A-Za-z0-9_-' </dev/urandom | head -c 32 || true)
  ensure_kv POSTGRES_PASSWORD "${PWGEN:-pandora_app_pwd}"
fi

# Constrói DATABASE_URL se ausente
if ! grep -q '^DATABASE_URL=' .env 2>/dev/null; then
  # Lê valores atuais do arquivo
  # shellcheck disable=SC1091
  . ./.env
  ensure_kv DATABASE_URL "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
fi

log "Atualizando código (branch=${BRANCH})"
if git rev-parse --git-dir >/dev/null 2>&1; then
  git fetch --all --prune || true
  if git rev-parse --verify "${BRANCH}" >/dev/null 2>&1; then
    git checkout "${BRANCH}" || true
  fi
  git pull --ff-only origin "${BRANCH}" || true
else
  if command -v git >/dev/null 2>&1 && [ -n "${REPO_URL}" ]; then
    if [ -z "$(ls -A . 2>/dev/null)" ]; then
      log "Clonando repositório (${REPO_URL}) em ${PROJECT_DIR}"
      git clone "${REPO_URL}" . || { log "Falha ao clonar. Prosseguindo sem atualizar código."; }
      git checkout "${BRANCH}" >/dev/null 2>&1 || true
    else
      log "Diretório não-vazio e sem Git; prosseguindo sem atualizar código."
    fi
  else
    log "${PROJECT_DIR} não é um repositório Git e REPO_URL não informado. Prosseguindo sem atualização de código."
  fi
fi

# Detecta arquivo compose
COMPOSE_ARGS=""
for f in docker-compose.yml docker-compose.yaml compose.yaml compose.yml; do
  if [ -f "$f" ]; then
    COMPOSE_ARGS="-f $f"
    export COMPOSE_FILE="$f"
    log "Usando compose file: $f"
    break
  fi
done

if [ -z "$COMPOSE_ARGS" ]; then
  log "ATENÇÃO: Nenhum arquivo docker-compose encontrado em ${PROJECT_DIR}."
  log "Dica: copie os arquivos do projeto (incluindo docker-compose.yml) via scp ou forneça -RepoUrl para clonar."
  exit 2
fi

log "Build das imagens (docker compose build --pull)"
docker compose $COMPOSE_ARGS build --pull

if [ "${MAINT}" = "1" ]; then
  log "Modo manutenção: derrubando containers antigos (down --remove-orphans)"
  docker compose $COMPOSE_ARGS down --remove-orphans
else
  log "Sem manutenção explícita: prosseguindo com up -d"
fi

log "Subindo nova versão (up -d)"
docker compose $COMPOSE_ARGS up -d --remove-orphans

log "Aplicando migrações"
docker compose $COMPOSE_ARGS exec -T "${SERVICE}" python manage.py migrate --noinput

log "Coletando estáticos"
docker compose $COMPOSE_ARGS exec -T "${SERVICE}" python manage.py collectstatic --noinput

log "Limpando imagens e objetos antigos (docker system prune -f)"
docker system prune -f >/dev/null 2>&1 || true

log "Status dos serviços"
docker compose ps

log "Deploy finalizado com sucesso."
'@

$remoteScript = $remoteScript.Replace("__PROJECT_DIR__", $ProjectDir)
$remoteScript = $remoteScript.Replace("__BRANCH__", $Branch)
$remoteScript = $remoteScript.Replace("__SERVICE__", $Service)
$remoteScript = $remoteScript.Replace("__MAINT__", ($(if ($Maintenance.IsPresent) { "1" } else { "0" })))
$remoteScript = $remoteScript.Replace("__REPO_URL__", $RepoUrl)

# Executa
Invoke-RemoteScript -Target $SshTarget -Port $Port -ScriptContent $remoteScript

Write-Host "[local] Deploy concluído sem erros." -ForegroundColor Green
