"""Script utilitário: lista usuários administradores com status de perfil e 2FA."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Garante que o diretório raiz do projeto esteja no sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pandora_erp.settings")

try:
    import django
    django.setup()
except Exception as e:  # noqa: BLE001 - script utilitário
    print("[ERRO] Não foi possível inicializar o Django:", e)
    raise

from django.contrib.auth import get_user_model  # noqa: E402
from django.db.models import Q  # noqa: E402

try:
    from user_management.models import PerfilUsuarioEstendido  # noqa: E402
except Exception:
    PerfilUsuarioEstendido = None  # type: ignore


def fmt(dt: Any) -> str:
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "-"
    except Exception:  # noqa: BLE001
        return str(dt) if dt else "-"


def main() -> int:
    User = get_user_model()
    users = (
        User.objects.filter(Q(is_superuser=True) | Q(is_staff=True))
        .order_by("-is_superuser", "-is_staff", "username")
    )
    if not users.exists():
        print("Nenhum usuário admin/staff encontrado.")
        return 0

    print("\n=== Usuários Administradores (superuser/staff) ===")
    for u in users:
        print(
            f"\nID={u.id} | username='{u.username}' | superuser={u.is_superuser} | "
            f"staff={u.is_staff} | active={u.is_active}"
        )
        print(f"email={u.email or '-'} | last_login={fmt(u.last_login)} | joined={fmt(u.date_joined)}")
        if PerfilUsuarioEstendido:
            try:
                p = PerfilUsuarioEstendido.objects.get(user=u)
                print(
                    "perfil: status=", getattr(p, "status", "-"),
                    "2FA=", bool(getattr(p, "autenticacao_dois_fatores", False)),
                    "confirmed=", bool(getattr(p, "totp_confirmed_at", None)),
                    "failed_2fa=", int(getattr(p, "failed_2fa_attempts", 0) or 0),
                    "locked_until=", fmt(getattr(p, "twofa_locked_until", None)),
                )
            except Exception as e:  # noqa: BLE001
                print("[aviso] Sem PerfilUsuarioEstendido ou erro ao buscar:", e)
        else:
            print("[aviso] app user_management indisponível para detalhar perfil.")
    print("\nTotal:", users.count())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
