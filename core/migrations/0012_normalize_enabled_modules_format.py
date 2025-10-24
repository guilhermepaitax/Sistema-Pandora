# Generated migration - Normalize enabled_modules to modern format

from django.db import migrations


def normalize_all_enabled_modules(apps, schema_editor):
    """Normaliza TODOS os tenants para formato moderno único.

    Formato moderno definitivo:
    {
        "modules": ["clientes", "produtos", "admin"],
        "clientes": {"enabled": True},
        "produtos": {"enabled": True},
        "admin": {"enabled": True}
    }

    Elimina formatos legados:
    - Lista simples: ["clientes", "produtos"]
    - Dict sem "modules": {"clientes": {"enabled": True}}
    - String JSON/CSV
    """
    Tenant = apps.get_model("core", "Tenant")

    total_tenants = Tenant.objects.count()
    converted_count = 0
    skipped_count = 0

    print(f"\n🔄 Normalizando enabled_modules de {total_tenants} tenants...")

    for tenant in Tenant.objects.all():
        raw = tenant.enabled_modules

        # Já está no formato moderno?
        if (
            isinstance(raw, dict)
            and "modules" in raw
            and isinstance(raw["modules"], list)
            and all(isinstance(raw.get(m), dict) and raw[m].get("enabled") is True for m in raw["modules"])
        ):
            skipped_count += 1
            continue

        # Extrair lista de módulos de qualquer formato
        modules_list = []

        if isinstance(raw, list):
            # Formato legado: lista simples
            modules_list = [str(m).strip() for m in raw if m]

        elif isinstance(raw, dict):
            if "modules" in raw and isinstance(raw["modules"], (list, tuple)):
                # Formato parcialmente moderno: tem "modules" mas pode não ter flags
                modules_list = [str(m).strip() for m in raw["modules"] if m]
            else:
                # Formato legado: dict de flags {mod: {enabled: True/False}}
                modules_list = [
                    key for key, value in raw.items() if isinstance(value, dict) and value.get("enabled") is True
                ]

        elif isinstance(raw, str):
            # Formato string JSON/CSV
            import json as _json

            s = raw.strip()
            if s.startswith(("[", "{")):
                try:
                    parsed = _json.loads(s)
                    if isinstance(parsed, list):
                        modules_list = [str(m).strip() for m in parsed if m]
                    elif isinstance(parsed, dict) and "modules" in parsed:
                        modules_list = [str(m).strip() for m in parsed["modules"] if m]
                except _json.JSONDecodeError:
                    # Tratar como CSV
                    cleaned = s.replace("[", "").replace("]", "").replace('"', "").replace("'", "")
                    modules_list = [m.strip() for m in cleaned.replace(";", ",").split(",") if m.strip()]
            else:
                # CSV simples
                modules_list = [m.strip() for m in s.replace(";", ",").split(",") if m.strip()]

        # Remover duplicados e ordenar
        unique_modules = sorted(set(m for m in modules_list if m))

        # Compor formato moderno definitivo
        modern_format = {
            "modules": unique_modules,
            **{m: {"enabled": True} for m in unique_modules},
        }

        # Atualizar tenant
        tenant.enabled_modules = modern_format
        tenant.save(update_fields=["enabled_modules"])
        converted_count += 1

        if converted_count % 50 == 0:
            print(f"  ✅ Convertidos: {converted_count} / Ignorados: {skipped_count}")

    print(f"\n✅ Migração concluída!")
    print(f"  • Total de tenants: {total_tenants}")
    print(f"  • Convertidos para formato moderno: {converted_count}")
    print(f"  • Já estavam no formato correto: {skipped_count}")


def reverse_migration(apps, schema_editor):
    """Reversão não suportada - formato moderno é definitivo.

    Para reverter, seria necessário decidir qual formato legado usar,
    o que não faz sentido pois estamos eliminando formatos legados.
    """
    print("\n⚠️  AVISO: Reversão desta migration não é suportada.")
    print("   O formato moderno é definitivo e não pode ser revertido para formato legado.")


class Migration(migrations.Migration):
    """Normaliza enabled_modules para formato moderno único.

    Esta migration elimina TODOS os formatos legados e garante que
    100% dos tenants usem o formato moderno definitivo.
    """

    dependencies = [
        ("core", "0011_alter_certificacao_options_alter_contato_options_and_more"),
    ]

    operations = [
        migrations.RunPython(
            normalize_all_enabled_modules,
            reverse_code=reverse_migration,
        ),
    ]
