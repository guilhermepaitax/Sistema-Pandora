# Migração para Postgres (Produção Definitiva)

Este guia descreve uma migração limpa do ambiente atual (SQLite em volume /data) para Postgres.

## 1. Preparar Banco Postgres
Crie um banco dedicado (não use o database default `postgres`). Exemplo de URL:

```
postgres://pandora_user:senha_forte@host:5432/pandora_db
```

Para Neon ou outro provider, habilite SSL (a URL normalmente já vem com parâmetros). Para Fly Postgres, use:

```
fly postgres create
fly postgres connect -a <cluster>
-- criar usuário e database dedicados
```

## 2. Configurar Secret

```
fly secrets set DATABASE_URL="postgres://..."
```

Remova (opcional) futuramente as variáveis de SQLite do `fly.toml`:
```
PANDORA_DB_FILE
ALLOW_SQLITE_PROD
```

## 3. Reset Sentinel de Migração
O entrypoint cria `/data/.migrations_done` para evitar migrar novamente. Remova-o para forçar execução das migrações no Postgres:

```
fly ssh console -a sistema-pandora
rm /data/.migrations_done || true
exit
```

## 4. Escalar Memória Temporariamente (se necessário)
Se a criação de schema for pesada, suba para 512MB:
```
fly machine update <MACHINE_ID> --memory 512 --cpus 1
```

## 5. Reiniciar a Máquina
```
fly machine restart <MACHINE_ID>
fly logs -a sistema-pandora --no-tail | findstr /i "Migrações concluídas"
```

Confirme log: `[entrypoint] Migrações concluídas`.

## 6. Validar Aplicação
- Acesse `/admin/` e páginas públicas.
- Verifique que logs não mostram mais aviso de SQLite.

## 7. (Opcional) Rebaixar Memória
Se o uso estiver baixo após cache aquecido:
```
fly machine update <MACHINE_ID> --memory 256 --cpus 1
```

## 8. Remover Variáveis de SQLite (Hardening)
Quando seguro, edite `fly.toml` e remova:
```
PANDORA_DB_FILE
ALLOW_SQLITE_PROD
```
Depois: `fly deploy`.

## 9. Migrar Dados Existentes (Se Houvesse)
No caso atual as migrações ainda não concluíam no SQLite (loop OOM). Se no futuro houver dados:
```
python manage.py dumpdata --natural-primary --natural-foreign \
  --exclude auth.permission --exclude contenttypes > base.json
```
Aplicar Postgres e então:
```
python manage.py loaddata base.json
```

## 10. Troubleshooting
| Sintoma | Causa provável | Ação |
|--------|----------------|------|
| OOM durante migrate | Memória insuficiente | Escale para 512MB temporariamente |
| Timeout conectando | Host/porta/SSL incorretos | Verifique DATABASE_URL e libssl no container |
| Erro SSL: self signed | Provider exige sslmode=require | Confirme parâmetro (dj-database-url define por padrão) |
| Reexecuta migrations sempre | Sentinel ausente / removido | Normal. Após stable, sentinel será criado novamente |

## 11. Checklist Final
- [ ] DATABASE_URL secret set
- [ ] Migrações concluídas no Postgres
- [ ] Sentinel recriado (se /data montado)
- [ ] Removidos avisos de SQLite
- [ ] Memória ajustada para custo alvo

---
_Documento gerado automaticamente para padronizar a transição._
