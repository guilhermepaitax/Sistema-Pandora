# Diagnóstico Rápido Fly.io (Sistema Pandora)

Use este guia para resolver erros 502 / falhas de inicialização.

## Passo 0: Pré-requisitos
- Secret `DATABASE_URL` definido (Postgres)
- Imagem atualizada com `fly deploy`
- Volume montado se ainda usa SQLite (não mais após Postgres)

## Passo 1: Status da aplicação
```bash
fly status -a sistema-pandora
```
Verifique se há máquinas `started`. Se `stopped` ou `failed`, prossiga para logs.

## Passo 2: Logs iniciais
```bash
fly logs -a sistema-pandora --tail
```
Procure:
- `[entrypoint] Iniciando Pandora ERP`
- `Migrações concluídas`
- Erros (`Traceback`, `OperationalError`, `Out of memory`)

## Passo 3: Migrações travando?
Remova sentinel e reinicie:
```bash
fly ssh console -a sistema-pandora
rm /data/.migrations_done || true
exit
fly machine restart <MACHINE_ID> -a sistema-pandora
```
Se OOM, suba memória:
```bash
fly machine update <MACHINE_ID> --memory 512 --cpus 1 -a sistema-pandora
```

## Passo 4: Testar saúde
```bash
curl -i https://sistema-pandora.fly.dev/healthz
```
Esperado: `200 ok`.

## Passo 5: Testar conexão Postgres
```bash
fly ssh console -a sistema-pandora
python - <<'PY'
import os, psycopg2
url=os.environ.get('DATABASE_URL')
print('URL=', url)
conn=psycopg2.connect(url)
cur=conn.cursor(); cur.execute('SELECT 1'); print(cur.fetchone()); conn.close()
PY
exit
```
Falhas comuns:
| Erro | Causa | Ação |
|------|-------|------|
| password authentication failed | Senha trocada/girada | Rotacionar e atualizar secret |
| could not translate host name | Host DNS demorando ou errado | Confirmar host pgbouncer vs direct; tentar novamente |
| SSL error | Falta `sslmode=require` | Acrescentar `?sslmode=require` na URL |

## Passo 6: Gunicorn não inicia
Verifique se logs param após migrations. Se sim, talvez memória insuficiente ou erro de import. Aumentar memória e reolhar logs.

## Passo 7: Reinicialização limpa
Após ajustes:
```bash
fly machine restart <MACHINE_ID> -a sistema-pandora
fly status -a sistema-pandora --json
```
Certifique que `State` = `started`.

## Passo 8: Hardening final
- Remover variáveis SQLite (já removido do `fly.toml`).
- Garantir `DEBUG=False` em produção (definir `DJANGO_DEBUG=False` secret).

## Passo 9: Superuser
Se não criado automaticamente:
```bash
fly ssh console -a sistema-pandora
python manage.py createsuperuser
exit
```

## Passo 10: Checklist Final
- [ ] DATABASE_URL secret presente
- [ ] Migrações concluídas
- [ ] Healthz 200
- [ ] /admin acessível
- [ ] Sem loops de restart
- [ ] Memória ajustada (256MB ou 512MB conforme necessidade)

---
Documento auxiliar. Mantenha-o atualizado conforme aprendizados.
