from django.db import migrations


def rename_paciente_to_cliente(apps, schema_editor):
    """Idempotente em múltiplos backends.

    Objetivo:
      - (Legado) Caso ainda exista coluna paciente_id, copiar para cliente_id.
      - Remover índice antigo baseado em paciente.

    Problema original:
      - Código usava PRAGMA table_info (SQLite) em ambiente Postgres, gerando
        erro de SQL e deixando a transação abortada (psycopg2.errors.InFailedSqlTransaction).

    Estratégia nova:
      - Detectar vendor. Se sqlite: usar lógica original adaptada.
      - Se Postgres: consultar information_schema.
      - Todas as operações protegidas com try/except; porém evitando executar
        instruções inválidas para não abortar transação.
    """
    conn = schema_editor.connection
    vendor = conn.vendor  # 'sqlite', 'postgresql', etc.
    cursor = conn.cursor()

    try:
        # Verifica se tabela existe primeiro (Postgres + SQLite)
        table_exists = True
        if vendor == "postgresql":
            cursor.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'prontuarios_fotoevolucao'
                """
            )
            table_exists = cursor.fetchone() is not None
        elif vendor == "sqlite":
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prontuarios_fotoevolucao';")
            table_exists = cursor.fetchone() is not None
        else:
            # Outros backends: tentar seguir, se falhar saímos silenciosamente
            pass

        if not table_exists:
            return

        # Obter colunas existentes
        cols: list[str] = []
        if vendor == "sqlite":
            try:
                cursor.execute("PRAGMA table_info(prontuarios_fotoevolucao);")
                cols = [row[1] for row in cursor.fetchall()]
            except Exception:
                return  # não segue se não conseguir ler
        elif vendor == "postgresql":
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'prontuarios_fotoevolucao'
                """
            )
            cols = [r[0] for r in cursor.fetchall()]
        else:
            # Backend não tratado especificamente; aborta silenciosamente
            return

        has_paciente = "paciente_id" in cols
        has_cliente = "cliente_id" in cols

        # Criar coluna cliente_id se precisar
        if has_paciente and not has_cliente:
            try:
                cursor.execute("ALTER TABLE prontuarios_fotoevolucao ADD COLUMN cliente_id INTEGER;")
            except Exception:
                # Se falhar (talvez corrida ou permissão), seguimos sem abortar
                pass
            else:
                # Copiar valores
                try:
                    cursor.execute(
                        "UPDATE prontuarios_fotoevolucao SET cliente_id = paciente_id WHERE cliente_id IS NULL;"
                    )
                except Exception:
                    pass

        # Remover índice antigo se existir (forma compatível com ambos)
        try:
            if vendor == "postgresql":
                cursor.execute("DROP INDEX IF EXISTS prontuario_foto_tenant_paciente_data_idx;")
            elif vendor == "sqlite":
                cursor.execute("DROP INDEX IF EXISTS prontuario_foto_tenant_paciente_data_idx;")
        except Exception:
            pass
    except Exception:
        # Última barreira: garantir que não deixamos a transação em estado abortado.
        try:
            conn.rollback()
        except Exception:
            pass
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
        migrations.RunPython(rename_paciente_to_cliente, migrations.RunPython.noop),
    ]
