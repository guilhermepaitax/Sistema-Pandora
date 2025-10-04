#!/bin/sh

# Fail fast on syntax errors, but vamos controlar falhas de migração manualmente
set -u

echo "==> Iniciando entrypoint (timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ))"

MAX_RETRIES=${MIGRATION_MAX_RETRIES:-10}
INITIAL_SLEEP=${MIGRATION_INITIAL_SLEEP_SECONDS:-3}
BACKOFF_FACTOR=${MIGRATION_BACKOFF_FACTOR:-1.6}

attempt=1
sleep_time=$INITIAL_SLEEP

VERBOSITY=${MIGRATION_VERBOSITY:-1}
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
	# converte sleep_time para inteiro ou mantem decimal
	printf "==> Migração falhou. Nova tentativa (%d/%d) em %.1f s...\n" "$attempt" "$MAX_RETRIES" "$sleep_time"
	# sleep aceita inteiros; para suportar decimal, usamos awk se disponível
	# fallback para inteiro
	if command -v awk >/dev/null 2>&1; then
		awk -v t="$sleep_time" 'BEGIN { system("sleep " t) }'
	else
		sleep $(printf '%.*f' 0 "$sleep_time")
	fi
	# calcula próximo backoff (limitando em 45s)
	# usamos awk para multiplicar float; se não existir, dobramos com shell inteiro
	if command -v awk >/dev/null 2>&1; then
		sleep_time=$(awk -v t="$sleep_time" -v f="$BACKOFF_FACTOR" 'BEGIN { v=t*f; if (v>45) v=45; printf "%.2f", v }')
	else
		sleep_time=$((sleep_time * 2))
		[ "$sleep_time" -gt 45 ] && sleep_time=45
	fi
done

echo "==> Seed inicial (tenants) se habilitado"
python manage.py shell <<'PY'
import os
from django.db import transaction
from core.models import Tenant

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
PY

echo "==> Garantindo superuser padrão (se configurado)"
python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

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
		# Garante flags caso alguém tenha alterado manualmente
		if not user.is_staff or not user.is_superuser:
			user.is_staff = True
			user.is_superuser = True
			changed = True
		if user.email != email:
			user.email = email
			changed = True
		if changed:
			user.save(update_fields=["email", "is_staff", "is_superuser"])
	# Só seta senha se ele ainda não tiver uma utilizável (evita sobrescrever alterações posteriores)
	force_reset = os.environ.get("DJANGO_SUPERUSER_PASSWORD_FORCE") == "1"
	if force_reset or not user.has_usable_password():
		user.set_password(password)
		user.save(update_fields=["password"])
	print(f"[superuser] OK username={username} created={created} force_reset={force_reset}")
else:
	print("[superuser] Variáveis de ambiente incompletas; pulando criação.")
PY

echo "==> Ignorando collectstatic em runtime (feito no build ou servido direto)"

# echo "$(date)" > build_time.txt  # opcional: gerar carimbo de build

echo "==> Iniciando Gunicorn (workers=3 timeout=120)"
# Usamos 'python -m gunicorn' para garantir que o módulo é encontrado mesmo se PATH não incluir binários
exec python -m gunicorn -b :$PORT pandora_erp.wsgi:application --log-file - --access-logfile - --workers 3 --timeout 120
