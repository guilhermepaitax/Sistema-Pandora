# User Management — Guia Consolidado (estado atual)

**Última atualização:** 2025-10-22  
**Status:** ✅ Sistema 100% funcional e documentado

Este documento consolida visão geral, fluxos, operações frequentes e comandos do módulo `user_management`. Substitui: `USER_MANAGEMENT_OVERVIEW.md`, `USER_MANAGEMENT_OPERACOES_FREQUENTES.md` e `USER_MANAGEMENT_PENDING.md`.

## 1. Escopo e Arquitetura
- Multi-tenant: ciclo de vida de usuários, perfis estendidos, status/bloqueios, 2FA (TOTP), permissões granulares e acesso modular.
- Middleware e sinais: inatividade de sessão, warm-up de permissões no login, auditoria estruturada.
- Observabilidade: métricas 2FA no perfil e auditorias/contadores complementares.

### Fronteira com Core (Admins via Wizard)
- Criação de administradores: acontece exclusivamente no Core, dentro do fluxo do Wizard (`core/wizard_views.py`). Esse fluxo cria Admins do tenant e relacionamentos iniciais (por exemplo, `TenantUser` e papéis padrão).
- Gestão global de usuários e permissões: é responsabilidade do módulo `user_management` (listas, detalhes, edição de perfil estendido, 2FA, permissões personalizadas, sessões e auditoria).
- Importante: manter essa separação. O `user_management` não cria Admins do wizard nem interfere nas rotas RBAC do Core; ele opera sobre qualquer usuário do sistema (inclusive admins já criados), respeitando o escopo multi-tenant e as permissões.

## 2. Modelos-chaves
- **PerfilUsuarioEstendido**: flags de segurança (bloqueios, 2FA, métricas) e campos auxiliares.
- **SessaoUsuario**: sessões ativas e expiração lógica.
- **PermissaoPersonalizada**: allow/deny por módulo/ação/(recurso)/escopo tenant/global.
- **ConviteUsuario**: convites de usuários para tenants com token e expiração.
- **LogAtividadeUsuario**: auditoria de ações com metadados (IP, user_agent, timestamp).
- **Tenant / TenantUser / Role**: relacionamento usuário↔tenant (módulo core).

## 3. Fluxos principais
### 3.1 Criação/Admin
1) Core/Wizard: cria Admin do tenant (User + TenantUser/Role default). 2) Signals garantem `PerfilUsuarioEstendido` e sincronizam status. 3) Auditoria do evento.

### 3.2 Convite e onboarding
Valida token, cria/associa usuário ao tenant, define status ATIVO, marca token usado, registra auditoria.

### 3.3 Login + 2FA
- Backend custom bloqueia por status/bloqueios antes da autenticação final; incrementa falhas e aplica lockout; sucesso zera contadores.
- 2FA TOTP com recovery codes (hash) e rate limit; segredo pode ser criptografado (Fernet multi-key) com rotação.
- Warm-up de permissões no login para melhorar latência inicial.

### 3.4 Permissões granulares
- Resolver com precedência DENY>ALLOW, escopo tenant/global e opcional recurso. Cache versionado com invalidadores e métricas de hit/miss/latência/TTL.
- Comando de auditoria para permissões órfãs.

## 4. Segurança (2FA)
- Segredo TOTP: geração/rotação, criptografia opcional (Fernet) e rotação de chaves suportada.
- Recovery codes: armazenados como SHA-256; consumidos após uso.
- Métricas por perfil: sucessos/falhas/uso de recovery/rate-limit blocks, com snapshot por comando.
- Documentação detalhada: ver `docs/TWOFA_SERVICE.md` (inclui operação, rotação de chaves e troubleshooting).

## 5. Sessões e auditoria
- Middleware de inatividade marca sessões como inativas após tempo configurado.
- Logs de atividade centralizados com metadados (ip, user_agent, ação).

## 6. Observabilidade
- Métricas em perfil 2FA e comandos para snapshot.
- PermissionResolver: contadores, latência e TTL por decisão; warm-up no login.

## 7. Comandos de management
- `twofa_reencrypt` (recriptografa segredos conforme chaves atuais; `--dry-run`, `--force`).
- `twofa_reencrypt_secrets` (recifra em massa; `--dry-run`, `--unencrypted-only`, `--limit`).
- `twofa_status_report` (status agregado de 2FA; `--json`, `--detailed`).
- `twofa_metrics_snapshot` (snapshot de métricas 2FA; `--reset` para zerar após captura).
- `cleanup_sessions_logs` (limpeza de sessões e logs antigos; `--dry-run`, `--logs-days=90`).
- `sync_profiles` (cria perfis ausentes; idempotente; `--dry-run`, `--verbose`).
- `create_missing_profiles` (alias para sync_profiles; cria perfis faltantes).
- `prune_expired_permissions` (remove permissões expiradas).
- `audit_orphan_permissions` (lista permissões personalizadas órfãs frente ao mapa de ações vigente).

## 7.1 Tarefas Celery Automáticas
Executadas periodicamente quando `ENABLE_USER_MGMT_MAINTENANCE=True`:

- **`desbloquear_usuarios_periodico`**: A cada 30min - Desbloqueia usuários com lockout expirado
- **`limpar_sessoes_expiradas_periodico`**: A cada 30min - Remove sessões Django antigas
- **`limpar_logs_antigos_periodico`**: Diariamente - Remove logs de atividade >90 dias
- **`cleanup_old_2fa_metrics`**: Semanalmente - Limpa métricas 2FA excessivas (>10.000) e lockouts órfãos (>7 dias)

## 8. Operações frequentes (how-to)
### Resetar 2FA de um usuário
```python
from user_management.models import PerfilUsuarioEstendido
p = PerfilUsuarioEstendido.objects.get(user__username='usuario')
from user_management.twofa import disable_2fa
disable_2fa(p)
```

### Regenerar recovery codes
```python
from user_management.twofa import setup_2fa
from user_management.models import PerfilUsuarioEstendido
p = PerfilUsuarioEstendido.objects.get(user__username='usuario')
secret, codes = setup_2fa(p)  # secret exibido uma vez; codes lista nova
```

### Desbloquear usuário (tentativas)
```python
from user_management.models import PerfilUsuarioEstendido, StatusUsuario
p = PerfilUsuarioEstendido.objects.get(user__username='usuario')
p.status = StatusUsuario.ATIVO
p.bloqueado_ate = None
p.tentativas_login_falhadas = 0
p.save(update_fields=['status','bloqueado_ate','tentativas_login_falhadas'])
```

### Forçar sync de perfis ausentes
```bash
python manage.py sync_profiles
```

### Snapshot (e reset opcional) de métricas 2FA
```bash
python manage.py twofa_metrics_snapshot --reset
```

### Recriptografar segredos (rotação de chaves)
1) Ajuste `settings.TWOFA_FERNET_KEYS` (nova chave na posição 0; antigas após). 2) Execute:
```bash
python manage.py twofa_reencrypt_secrets --dry-run
python manage.py twofa_reencrypt_secrets
```
3) Remova chaves antigas após estabilização.

### Auditoria de permissões órfãs
```bash
python manage.py audit_orphan_permissions
```

### Diagnóstico de negação de acesso
```python
from shared.services.permission_resolver import permission_resolver
ok, reason = permission_resolver.resolve(user, tenant, 'VIEW_USER_MANAGEMENT')
print(ok, reason)
# Invalidação de cache (se necessário):
permission_resolver.invalidate_cache(user_id=user.id, tenant_id=tenant.id)
```

## 9. Feature flags e settings
- TWOFA_ENCRYPT_SECRETS, TWOFA_FERNET_KEYS, thresholds e rate limits (2FA).
- FEATURE_UNIFIED_ACCESS, FEATURE_LOG_MODULE_DENIALS, FEATURE_MODULE_DENY_403.
- SESSION_MAX_INACTIVITY_MINUTES.

## 10. Testes e cobertura
- Suite cobre: 2FA (lockout, rate-limit, recovery), snapshot/relatórios, limpeza de sessões, resolver permissões (precedência), comandos de manutenção.
- Cobertura atual: ≥52% (última medição ~54–55% na suite completa). Em execuções parciais, o conftest relaxa o fail-under localmente.

## 11. Estado atual e próximos incrementos (opcionais)
- Estado: módulo funcional e documentado; comandos e serviços estáveis.
- Incrementos sugeridos (quando planejar):
  - Export Prometheus de métricas 2FA.
  - Testes adicionais de precedência complexa no resolver e whitelist de portal.
  - Política de retenção/rotação de métricas e pruning de logs.
  - Integração opcional do botão “Redefinir Senha” com endpoint do Core (`core:tenant_user_reset_password`) quando definido o mapeamento `PerfilUsuarioEstendido`→`TenantUser` no contexto da tela.

## 12. Referências
- 2FA detalhado: `docs/2FA.md` (atualizado em 2025-10-21).
- Auditoria de módulos: `docs/AUDITORIA_CONFORMIDADE_MODULOS.md`.
- Auditoria completa: `docs/AUDITORIA_COMPLETA_MODULOS_TEMPLATES.md`.
- Documentação sistema: `docs/DOCUMENTACAO_SISTEMA_PANDORA_ERP.md`.

---

## 13. Notas Arquiteturais

### 13.1 ModuleRequiredMixin
O módulo `user_management` é considerado **essencial** do sistema e **não usa** `ModuleRequiredMixin` por design:

**Razão:** Diferente dos módulos opcionais (clientes, obras, etc.), o `user_management` é necessário para o funcionamento básico do sistema (autenticação, autorização, perfis).

**Proteção:** Views são protegidas por:
1. `LoginRequiredMixin` - Autenticação obrigatória
2. `TenantRequiredMixin` - Contexto empresarial
3. `TenantAdminOrSuperuserMixin` - Permissões administrativas
4. `PermissionRequiredMixin` - Permissões granulares customizadas

**Módulos na mesma categoria:**
- `core` - Gerenciamento de empresas (superuser)
- `admin` - Administração da empresa
- `user_management` - Gerenciamento de usuários

**Arquitetura:** Segue padrão "defense in depth" com múltiplas camadas de autenticação e autorização, mas sem verificação de módulo habilitado (sempre disponível).
