## Migração / Sincronização de Dados (SQLite local -> Postgres Cloud SQL)

Este guia descreve caminhos para levar seus dados locais para o banco gerenciado.

### 1. Verifique qual banco local você está usando

Se `DATABASE_URL` não está definido localmente, provavelmente está usando SQLite em `db.sqlite3`.

### 2. Estratégias

1. Dump/Load via JSON (rápido, simples)  
2. pgloader (mais robusto para bases grandes)  
3. Dump parcial por app (selecionar só algumas apps)  

### 3. Dump/Load via JSON

No ambiente local (onde os dados existem):

```
python manage.py dumpdata --natural-foreign --natural-primary \
  --exclude contenttypes --exclude auth.permission \
  > data_full.json
```

Opcional: gerar dump só de alguns apps:
```
python manage.py dumpdata cadastros_gerais clientes produtos > data_parcial.json
```

Faça upload do arquivo `data_full.json` para a máquina onde você pode alcançar o Postgres (ou simplesmente o inclua local e rode com sua `DATABASE_URL` apontando para o Cloud SQL via proxy/socket):

Carregar (atenção: execute migrations antes):
```
python manage.py migrate --noinput
python manage.py loaddata data_full.json
```

Se já existir dados conflitantes (chaves únicas), pode ser necessário limpar tabelas específicas antes. Exemplo:
```
python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.all().delete()"
```

### 4. Ajuste de sequências (Postgres)

Após `loaddata`, para modelos com AutoField/BigAutoField, pode ser preciso reajustar sequência:
```
python manage.py shell <<'PY'
from django.apps import apps
from django.db import connection
with connection.cursor() as cur:
    for model in apps.get_models():
        from django.db.models import AutoField, BigAutoField
        pk = model._meta.pk
        if isinstance(pk, (AutoField, BigAutoField)) and connection.vendor == 'postgresql':
            table = model._meta.db_table
            seq = f"{table}_{pk.column}_seq"
            try:
                cur.execute(f"SELECT setval('{seq}', (SELECT COALESCE(MAX({pk.column}),1) FROM {table}), true)")
            except Exception as e:  # noqa: BLE001
                print('Aviso ao ajustar sequência', table, e)
PY
```

### 5. pgloader (opcional)

Instale `pgloader` e execute algo como:
```
pgloader db.sqlite3 postgresql://usuario:senha@/pandora_app?host=/cloudsql/PROJECT:REGION:INSTANCE
```

### 6. Conferências pós-migração

1. Contar registros de tabelas críticas (ex: usuários).  
2. Acessar a aplicação e verificar login.  
3. Conferir logs de warnings de sequências.  

### 7. Remoção de variáveis de bootstrap

Após os dados e superusuário estarem ok, remover do ambiente:
```
DJANGO_SUPERUSER_USERNAME
DJANGO_SUPERUSER_PASSWORD
DJANGO_SUPERUSER_EMAIL
```
O sistema não recriará o superusuário se já existir um.

### 8. Problemas comuns

| Sintoma | Causa provável | Ação |
|--------|----------------|------|
| Migrations reaplicando sempre | Conectando em outro DB vazio | Verificar DATABASE_URL / socket |
| Superusuário recriado | Usuário não persistiu ou DB errado | Confirmar se Cloud SQL está sendo usado |
| Erros de chave duplicada em loaddata | Dados já existem | Limpar ou fazer dump parcial |

### 9. Dica

Mantenha um dump limpo versionado (criptografado) para facilitar reconstruções rápidas em novos ambientes.
