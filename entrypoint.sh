#!/bin/bash
set -e

PORT="${PORT:-8080}"
echo "[entrypoint] Iniciando Pandora ERP na porta ${PORT} (PID $$)"

# Aguarda opcionalmente o socket do Cloud SQL aparecer quando usamos conexão via Unix Socket.
# Ativado por padrão (defina WAIT_FOR_CLOUDSQL=0 para desabilitar).
wait_for_cloudsql() {
  if [ "${WAIT_FOR_CLOUDSQL:-1}" != "1" ]; then
    return 0
  fi
  if [ -z "${DATABASE_URL}" ]; then
    return 0
  fi
  # Extrai o valor de host= (query param) se existir na URL
  # Formato esperado: ...?host=/cloudsql/PROJ:REGIAO:INSTANCIA
  local socket_dir
  socket_dir="$(echo "$DATABASE_URL" | sed -n 's/.*host=\([^&]*\).*/\1/p')"
  # Só prossegue se contiver /cloudsql/
  if [ -z "$socket_dir" ] || [[ "$socket_dir" != *"/cloudsql/"* ]]; then
    return 0
  fi
  # Remove possíveis escapes de URL (%2F)
  socket_dir="${socket_dir//%2F//}"
  echo "[entrypoint] Detectado socket Cloud SQL em $socket_dir (aguardando disponibilidade)"
  local tries=0
  local max_tries=${CLOUDSQL_WAIT_MAX_TRIES:-20}
  local sleep_s=${CLOUDSQL_WAIT_INTERVAL_SECONDS:-1}
  while [ $tries -lt $max_tries ]; do
    if [ -S "$socket_dir/.s.PGSQL.5432" ] || [ -d "$socket_dir" ]; then
      echo "[entrypoint] Socket Cloud SQL disponível (tries=$tries)"
      return 0
    fi
    tries=$((tries+1))
    sleep $sleep_s
  done
  echo "[entrypoint] Aviso: socket Cloud SQL não detectado após $((max_tries*sleep_s))s; prosseguindo assim mesmo" >&2
  return 0
}

wait_for_cloudsql

run_migrations() {
  local max_retries=${MIGRATION_MAX_RETRIES:-1}
  local sleep_seconds=${MIGRATION_INITIAL_SLEEP_SECONDS:-3}
  local backoff=${MIGRATION_BACKOFF_FACTOR:-1.6}
  local attempt=1
  echo "[entrypoint] Iniciando migrações (max_retries=$max_retries sleep=$sleep_seconds backoff=$backoff)"
  while [ $attempt -le $max_retries ]; do
    echo "[entrypoint] migrate tentativa $attempt..."
    if python manage.py migrate --noinput; then
      echo "[entrypoint] Migrações concluídas"
      return 0
    fi
    if [ $attempt -eq $max_retries ]; then
      echo "[entrypoint] Migrações falharam após $attempt tentativas" >&2
      return 1
    fi
    echo "[entrypoint] Falha na tentativa $attempt, aguardando $sleep_seconds segundos"
    sleep $sleep_seconds
    # limitar crescimento exagerado
    sleep_seconds=$(python - <<PY
import math
v=$sleep_seconds*$backoff
print(min(int(v)+1,45))
PY
)
    attempt=$((attempt+1))
  done
}

if [ "${SKIP_STARTUP_MIGRATIONS}" != "1" ]; then
  run_migrations || exit 1
else
  echo "[entrypoint] SKIP_STARTUP_MIGRATIONS=1 -> pulando migrate"
fi

# collectstatic removido do runtime (feito em build). RUN_COLLECTSTATIC descontinuado.

# Criar superuser se variáveis presentes
python manage.py shell <<'PYCODE' || true
"""Bootstrap de superusuário idempotente.
Regras:
1. Se já existe qualquer superuser -> não faz nada.
2. Se não existe superuser e variáveis DJANGO_SUPERUSER_* existem -> cria usando elas.
3. Se não existe superuser e variáveis não existem -> cria 'admin' com senha aleatória e exibe no log.
"""
from django.contrib.auth import get_user_model
from django.db import OperationalError
import os, secrets, string
User = get_user_model()
try:
  force_reset = os.environ.get('DJANGO_SUPERUSER_FORCE_RESET') == '1'
  target_username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
  target_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
  target_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')

  any_superuser = User.objects.filter(is_superuser=True).exists()
  if not any_superuser:
    # Cenário inicial: criar superuser (usa variáveis se fornecidas, senão gera)
    u = target_username or 'admin'
    p = target_password
    if not p:
      alphabet = string.ascii_letters + string.digits
      p = ''.join(secrets.choice(alphabet) for _ in range(16))
      print('[entrypoint] SUPERUSER AUTO-GERADO (anote a senha abaixo)')
      print(f"[entrypoint] username={u} password={p}")
    obj, created = User.objects.get_or_create(
      username=u,
      defaults={'email': target_email, 'is_staff': True, 'is_superuser': True},
    )
    if created:
      obj.set_password(p)
      obj.is_superuser = True
      obj.is_staff = True
      obj.save()
      print(f'[entrypoint] superuser criado username={u}')
    else:
      print(f'[entrypoint] superuser já existia username={u} (race?) -> senha preservada')
  else:
    # Já existe superuser. Apenas reset se explicitamente solicitado e credenciais presentes.
    if force_reset and target_username and target_password:
      try:
        su = User.objects.get(username=target_username)
      except User.DoesNotExist:
        # Cria novo superuser adicional se não existe com esse username
        su = User(username=target_username, email=target_email, is_staff=True, is_superuser=True)
      su.set_password(target_password)
      su.is_superuser = True
      su.is_staff = True
      su.save()
      print(f'[entrypoint] superuser reset/aplicado username={target_username}')
    else:
      print('[entrypoint] superuser já existente -> skip criação (nenhum reset solicitado)')
except OperationalError as exc:
  print(f'[entrypoint] ERRO ao checar/criar superuser: {exc!r}')
except Exception as exc:  # noqa: BLE001
  print(f'[entrypoint] Erro inesperado superuser: {exc!r}')
PYCODE

if [ "${USE_GUNICORN}" = "1" ]; then
  : "${GUNICORN_WORKERS:=3}"
  : "${GUNICORN_TIMEOUT:=90}"
  echo "[entrypoint] Iniciando Gunicorn (workers=${GUNICORN_WORKERS} timeout=${GUNICORN_TIMEOUT})"
  exec gunicorn pandora_erp.asgi:application \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:"${PORT}" \
    --workers "${GUNICORN_WORKERS}" \
    --timeout "${GUNICORN_TIMEOUT}" \
    --access-logfile - \
    --error-logfile -
else
  echo "[entrypoint] Iniciando Daphne ASGI..."
  exec python -m daphne -b 0.0.0.0 -p "${PORT}" pandora_erp.asgi:application
fi
