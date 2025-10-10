from django.db import migrations


def recompute_modules(apps, schema_editor):
    Tenant = apps.get_model("core", "Tenant")
    updated = 0
    for tenant in Tenant.objects.all().iterator():
        try:
            # Usa método recém adicionado (pode não existir em histórico -> fallback manual)
            if hasattr(tenant, "recompute_modules_from_plan"):
                before = set(
                    tenant.enabled_modules.get("modules", []) if isinstance(tenant.enabled_modules, dict) else []
                )
                after = set(tenant.recompute_modules_from_plan(persist=True))
                if after != before:
                    updated += 1
            else:  # Fallback: manter dado como está
                continue
        except Exception:  # noqa: BLE001
            continue
    # Não precisamos logar via logger porque em migrations pode não haver config de logging
    print(f"[0010_recompute_plan_modules] Tenants atualizados: {updated}")


def noop_reverse(apps, schema_editor):
    # Reversão não altera módulos retroativamente
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_add_dadosbancarios_titular_documento"),
    ]

    operations = [
        migrations.RunPython(recompute_modules, noop_reverse),
    ]
