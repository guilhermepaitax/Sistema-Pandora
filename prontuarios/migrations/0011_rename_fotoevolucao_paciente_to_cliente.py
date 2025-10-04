from django.db import migrations


def noop_forward(apps, schema_editor):
    """NO-OP definitivo.

    Esta migração foi convertida para não executar nenhum SQL porque as
    alterações que pretendia aplicar já estão refletidas no estado atual
    do schema nos ambientes alvo (Postgres). Manter lógica defensiva aqui
    vinha causando estado de transação abortado. Registrar apenas.
    """
    return


class Migration(migrations.Migration):
    dependencies = [
        ("prontuarios", "0010_cleanup_paciente_residuos"),
        ("clientes", "0002_initial"),
    ]

    # Evita que um erro silenciosamente capturado deixe a transação abortada
    # impedindo o registro da migração em django_migrations.
    atomic = False

    operations = [
        migrations.RunPython(noop_forward, migrations.RunPython.noop),
    ]
