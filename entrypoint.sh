#!/bin/sh

# Fail fast on syntax errors, but vamos controlar falhas de migração manualmente
set -u

# Cloud Run exige porta 8080; se PORT vier vazio definimos 8080
PORT="${PORT:-8080}"
echo "==> Iniciando entrypoint (timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)) PORT=$PORT"

# Espera básica por Postgres se DATABASE_URL apontar para postgres
if printf '%s' "${DATABASE_URL:-}" | grep -qi 'postgres'; then
  echo "==> Checando disponibilidade do banco antes das migrações"
  python - <<'PY'
import os, time, socket
from urllib.parse import urlparse, parse_qs
url = os.environ.get('DATABASE_URL')
if url:
	u = urlparse(url)
	host = u.hostname or 'localhost'
	port = u.port or 5432
	q = parse_qs(u.query)
	sock_path = q.get('host', [''])[0]
	for attempt in range(1, 11):
		ok = False
		if sock_path and sock_path.startswith('/cloudsql/'):
			ok = os.path.exists(sock_path)
		else:
			try:
				with socket.create_connection((host, port), timeout=2):
					ok = True
			except Exception:
				ok = False
		if ok:
			print(f"[db-wait] Conectividade ok (tentativa {attempt})")
			break
		print(f"[db-wait] Aguardando banco (tentativa {attempt})...")
		time.sleep(min(1+attempt,6))
	else:
		print("[db-wait] Prosseguindo mesmo sem confirmação de conexão")
PY
fi

MAX_RETRIES=${MIGRATION_MAX_RETRIES:-10}
INITIAL_SLEEP=${MIGRATION_INITIAL_SLEEP_SECONDS:-3}
BACKOFF_FACTOR=${MIGRATION_BACKOFF_FACTOR:-1.6}

attempt=1
sleep_time=$INITIAL_SLEEP

VERBOSITY=${MIGRATION_VERBOSITY:-1}
if [ "${SKIP_STARTUP_MIGRATIONS:-0}" = "1" ]; then
    echo "==> SKIP_STARTUP_MIGRATIONS=1 - pulando aplicação de migrações no startup"
else
    echo "==> Aplicando migrations (máx ${MAX_RETRIES} tentativas, verbosity=${VERBOSITY})"
    while true; do
    	if python manage.py migrate --noinput --verbosity ${VERBOSITY}; then
    		echo "==> Migrações aplicadas com sucesso na tentativa ${attempt}"
    		break
    	fi

    	if [ "$attempt" -ge "$MAX_RETRIES" ]; then
    		echo "[ERRO] Falha ao aplicar migrações após ${attempt} tentativas. Abortando." >&2
    		exit 1
    	fi

    	attempt=$((attempt + 1))
    	printf "==> Migração falhou. Nova tentativa (%d/%d) em %.1f s...\n" "$attempt" "$MAX_RETRIES" "$sleep_time"
    	if command -v awk >/dev/null 2>&1; then
    		awk -v t="$sleep_time" 'BEGIN { system("sleep " t) }'
    	else
    		sleep $(printf '%.*f' 0 "$sleep_time")
    	fi
    	if command -v awk >/dev/null 2>&1; then
    		sleep_time=$(awk -v t="$sleep_time" -v f="$BACKOFF_FACTOR" 'BEGIN { v=t*f; if (v>45) v=45; printf "%.2f", v }')
    	else
    		sleep_time=$((sleep_time * 2))
    		[ "$sleep_time" -gt 45 ] && sleep_time=45
    	fi
    done
fi

if [ "${SKIP_STARTUP_MIGRATIONS:-0}" = "1" ]; then
  echo "==> SKIP_STARTUP_MIGRATIONS=1 - pulando seed de tenants e criação de superuser (tabelas podem não existir)"
else
  echo "==> Seed inicial (tenants) se habilitado"
  python manage.py shell <<'PY'
import os
from django.db import transaction
from core.models import Tenant

try:
	if os.environ.get("PANDORA_SEED_TENANTS", "0") == "1":
		if Tenant.objects.count() == 0:
			codes_raw = os.environ.get("PANDORA_SEED_TENANTS_CODES", "01,02")
			codes = [c.strip() for c in codes_raw.split(',') if c.strip()]
			if not codes:
				codes = ["01", "02"]
			created = []
			with transaction.atomic():
				for code in codes:
					sub = f"tenant{code.lower()}"
					name = f"Empresa {code}"
					t = Tenant.objects.create(
						name=name,
						subdomain=sub,
						codigo_interno=code,
						status="active",
						enabled_modules={"core": True},
					)
					created.append(t.codigo_interno)
			print(f"[seed tenants] Criados tenants iniciais: {created}")
		else:
			print("[seed tenants] Já existem tenants; seed não executado")
	else:
		print("[seed tenants] Variável PANDORA_SEED_TENANTS != 1; ignorando")
except Exception as e:  # pragma: no cover
	print(f"[seed tenants] ERRO não crítico: {e}")
PY

  echo "==> Garantindo superuser padrão (se configurado)"
  python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

try:
	User = get_user_model()
	username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
	email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
	password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

	if username and email and password:
		created = False
		user, created = User.objects.get_or_create(
			username=username,
			defaults={
				"email": email,
				"is_staff": True,
				"is_superuser": True,
			},
		)
		changed = False
		if not created:
			if not user.is_staff or not user.is_superuser:
				user.is_staff = True
				user.is_superuser = True
				changed = True
			if user.email != email:
				user.email = email
				changed = True
			if changed:
				user.save(update_fields=["email", "is_staff", "is_superuser"])
		force_reset = os.environ.get("DJANGO_SUPERUSER_PASSWORD_FORCE") == "1"
		if force_reset or not user.has_usable_password():
			user.set_password(password)
			user.save(update_fields=["password"])
		print(f"[superuser] OK username={username} created={created} force_reset={force_reset}")
	else:
		print("[superuser] Variáveis de ambiente incompletas; pulando criação.")
except Exception as e:  # pragma: no cover
	print(f"[superuser] ERRO não crítico: {e}")
PY
fi

echo "==> Ignorando collectstatic em runtime (feito no build ou servido direto)"

# echo "$(date)" > build_time.txt  # opcional: gerar carimbo de build

echo "==> Iniciando servidor ASGI (Daphne) em 0.0.0.0:$PORT"
exec python -m daphne -b 0.0.0.0 -p "$PORT" pandora_erp.asgi:application
