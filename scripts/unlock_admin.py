import os
import sys
from pathlib import Path

# Garante que o diretório raiz do projeto esteja no sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pandora_erp.settings")

try:
    import django
    django.setup()
except Exception as e:
    print("[ERRO] Não foi possível inicializar o Django:", e)
    sys.exit(1)

from django.contrib.auth import get_user_model

try:
    from user_management.models import PerfilUsuarioEstendido, StatusUsuario
except Exception as e:
    print("[ERRO] Importando modelos de user_management:", e)
    sys.exit(1)


def main():
    User = get_user_model()
    u = User.objects.filter(is_superuser=True).order_by("id").first()
    if not u:
        print("[ERRO] Nenhum superusuário encontrado.")
        return 2

    print(f"Superuser: {u.username} is_staff={u.is_staff} is_active={u.is_active}")

    try:
        p = PerfilUsuarioEstendido.objects.get(user=u)
    except PerfilUsuarioEstendido.DoesNotExist:
        print("[ERRO] PerfilUsuarioEstendido não encontrado para o superusuário.")
        return 3

    print(f"Perfil status antes: {p.status}")

    changed_user = False
    changed_profile = False

    if not u.is_staff:
        u.is_staff = True
        changed_user = True

    if not u.is_active:
        u.is_active = True
        changed_user = True

    if p.status != StatusUsuario.ATIVO:
        p.status = StatusUsuario.ATIVO
        changed_profile = True

    if changed_profile:
        p.save(update_fields=["status"])
        print("Perfil status ajustado para ATIVO")

    # Define uma senha temporária previsível para recuperação imediata
    temp_password = "AdminTemp!2025"
    u.set_password(temp_password)

    if changed_user:
        u.save(update_fields=["is_staff", "is_active", "password"])  # salva também senha
        print("is_staff/is_active ajustados e senha temporária definida")
    else:
        u.save(update_fields=["password"])  # salva apenas senha
        print("Senha temporária definida")

    print("Use estas credenciais temporárias para logar:")
    print(f"  usuário: {u.username}")
    print(f"  senha:   {temp_password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
