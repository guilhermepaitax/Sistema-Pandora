from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("prontuarios", "0010_cleanup_paciente_residuos"),
        ("clientes", "0002_initial"),
    ]

    # Evita que um erro silenciosamente capturado deixe a transação abortada
    # impedindo o registro da migração em django_migrations.
    atomic = False

    operations: list = []
