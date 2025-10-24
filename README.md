# Pandora ERP - Sistema de Gestão Empresarial

![CI](https://github.com/example-org/pandora-erp/actions/workflows/ci.yml/badge.svg)
![Security Scan](https://github.com/example-org/pandora-erp/actions/workflows/security.yml/badge.svg)
![License](https://img.shields.io/badge/license-Proprietary-lightgrey)
![Python](https://img.shields.io/badge/python-3.12%20|%203.13-blue)
![Coverage](https://codecov.io/gh/example-org/pandora-erp/branch/main/graph/badge.svg)

Sistema ERP multi-tenant desenvolvido em Django para gestão completa de empresas.

> Nota de higiene: **ruff** é o linter/formatter padrão do projeto. Um teste de higiene garante que configurações e dependências legadas de linters não retornem.
>
> Atualização: `sitecustomize.py` removido (era apenas para suprimir warning DRF). Teste `test_sitecustomize_optional` assegura que ausência não impacta inicialização. Pipeline de CI agora agrega cobertura entre Python 3.12 e 3.13 antes de publicar artefato combinado.

## 🧼 Higiene de Repositório

- Scripts obsoletos bloqueados: `parse_ci.py`, `limpar_migracoes.py`, `_clean_caches.py`, `tmp_list_tu.py`, `sitecustomize.py`.
- Hook pre-commit `forbid-legacy-scripts` impede commit se eles reaparecerem (inclusive tamanho >0). Arquivos vazios com esses nomes são auto-removidos pelo hook.
- Testes `tests/test_repo_higiene.py` garantem:
  1. Ausência de arquivos estranhos sem extensão na raiz.
  2. Não reintrodução de scripts obsoletos.
  3. Ausência de configs de linters legados (ex.: `.flake8`).
  4. (Novo) Ausência de arquivos `.md` ou testes vazios (exceto `__init__.py`).

Detalhes adicionais em `docs/REPO_HYGIENE.md`.

## 🧪 Organização dos Testes
Guia completo: [Guia Unificado de Testes](docs/TESTES_ORGANIZACAO.md) — marcadores, estrutura por domínio, execução segmentada, roadmap de cobertura.

### 🔐 Sistema de Permissões
Documentação completa e consolidada: **[SISTEMA_PERMISSOES_COMPLETO.md](docs/SISTEMA_PERMISSOES_COMPLETO.md)**

Este documento unifica toda a documentação sobre:
- Arquitetura multi-camadas (6 camadas de autorização)
- Hierarquia de usuários (Superuser, Admin, Funcionário, Portal)
- Permission Resolver (API, cache, invalidação)
- UI Permissions (padrão module_key)
- Permissões específicas de módulos
- Troubleshooting e casos de uso práticos

**Quick Start:**
```python
# Verificar permissão simples
from shared.services.permission_resolver import has_permission
if has_permission(user, tenant, "CREATE_OBRA"):
    # Usuário pode criar obra

# UI Permissions (templates)
from shared.services.ui_permissions import build_ui_permissions
context['perms_ui'] = build_ui_permissions(user, tenant, module_key='FORNECEDOR')
# Template: {% if perms_ui.can_add %}...{% endif %}
```

## 🚀 Visão Geral Rápida

Plataforma ERP modular, multi-tenant, orientada a domínios (DDD light), com foco em extensibilidade e padronização de UI/UX (familia de templates *ultra_modern*).

## 🚀 Funcionalidades Principais

- **Multi-tenant**: Suporte a múltiplas empresas em uma única instalação
- **Gestão de Usuários**: Sistema completo de autenticação e permissões
- **Módulos Integrados (núcleo atual)**:
  - Core (Empresas, Usuários, Departamentos, Tenancy)
  - Agendamentos (Slots, Disponibilidades, Waitlist, Auditoria de eventos) [Novo]
  - Prontuários (Serviços Clínicos, Atendimentos, Fotos Evolução, Anamneses, Perfil Clínico) [Reestruturado]
  - Financeiro (Contas a Pagar/Receber, Fluxos)
  - Estoque (Picking, Valuation, BOM, Auditoria, WebSockets)
  - Compras / Fornecedores
  - Funcionários / RH
  - Notificações & Chat interno
  - BI / Relatórios
  - Documentos e Uploads
  ### 🔐 Autenticação de Dois Fatores (2FA)
  - Auditoria Técnica Avançada
  - Guia consolidado de gestão de usuários: veja `docs/USER_MANAGEMENT.md`
  - Documentação operacional de 2FA (rotação de chaves, troubleshooting): `docs/TWOFA_SERVICE.md`
  - **Sistema de Permissões completo**: `docs/SISTEMA_PERMISSOES_COMPLETO.md`

## 🛠️ Tecnologias

- **Backend**: Django 5.1.5
- **Frontend**: Bootstrap 5 + jQuery
- **Banco de Dados**: SQLite (desenvolvimento) / PostgreSQL (produção)
- **Autenticação**: Django Auth + Sistema Multi-tenant

## 🧱 Arquitetura (Resumo)

| Camada | Principais Elementos | Observações |
| ------ | -------------------- | ----------- |
| Apresentação | Templates base: `pandora_ultra_modern_base`, `pandora_home_ultra_modern`, `pandora_list_ultra_modern`, `pandora_form_ultra_modern` | Blocos padronizados para título, ações, estatísticas |
| Domínio | Apps por módulo (`estoque`, `agendamentos`, `prontuarios`, etc.) | Lógica de negócio distribuída em *services* quando necessário |
| Persistência | Django ORM / PostgreSQL (prod) | Migrations versionadas por app |
| Multi-tenant | Campo `tenant` + `get_current_tenant(request)` | Abordagem simples (single DB) com isolamento lógico |
| Wizard Tenants | `TenantCreationWizardView` (core/wizard_views.py) | Única fonte de criação/edição de empresas |
| Assíncrono | Celery + Redis | Fila adicional para vídeo/imagem (ex: thumbnails) |
| Tempo Real | WebSockets (Channels / grupos ex: `estoque_stream`) | Eventos de picking e movimentos |
| Observabilidade | Métricas Prometheus + Logs estruturados | Counters para tasks e transcodificação |
| Agendamentos - Métricas | Vide docs/MODULO_AGENDAMENTOS.md §10.4 | Counters CRUD + waitlist + sync_evento |

Detalhes completos em `docs/ARCHITECTURE.md`.

## 📋 Pré-requisitos

- Python 3.8+
- pip
- Git

## 🔧 Instalação (Desenvolvimento Clássico)

1. **Clone o repositório:**
```bash
git clone https://github.com/SEU_USUARIO/Pandora-ERP.git
cd Pandora-ERP/backend
```

2. **Crie um ambiente virtual:**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente:**
```bash
# Copie o arquivo de exemplo
copy .env.example .env
# Edite o arquivo .env com suas configurações
```

5. **Execute as migrações:**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Crie um superusuário:**
```bash
python manage.py createsuperuser
```

7. **Execute o servidor (modo dev):**
```bash
python manage.py runserver
```

**Acesse:** http://localhost:8000

### 🚢 Docker (Multi-stage)
Produção:
```bash
docker build -t pandora-erp:prod .
docker run -p 8000:8000 pandora-erp:prod
```
Desenvolvimento (hot reload):
```bash
docker build --target dev -t pandora-erp:dev .
docker run -p 8000:8000 -v $(pwd):/app pandora-erp:dev
```
Stack completa:
```bash
docker compose up --build
```

### 📦 Versionamento & Changelog
Commits: Conventional Commits (Commitizen).
Gerar novo release:
```bash
pip install commitizen
cz bump --changelog
git push --follow-tags
```
Histórico em `docs/CHANGELOG.md`.

## 🧙‍♂️ Wizard de Criação/Edição de Empresas (Tenant)

Fluxo legacy (views TenantCreateView / TenantUpdateView + template tenant_form.html) foi removido e substituído integralmente pelo wizard multi-step `TenantCreationWizardView`.

Rotas canônicas ativas:
- Criar: `/core/tenants/create/`  (name: `core:tenant_create`)
- Editar: `/core/tenants/<pk>/edit/` (name: `core:tenant_update`)

Compatibilidade temporária (redirecionos 301) até 2025-10:
- `/core/tenants/wizard/` → `tenant_create`
- `/core/tenants/wizard/<pk>/edit/` → `tenant_update`

Teste sentinel garante que nenhum `tenant_form*.html` volte a existir (`core/tests/test_no_legacy_tenant_form.py`). Para desfazer rotas antigas remova-as de `core/urls.py` após expirar prazo e ajuste qualquer documentação externa.

Documentação detalhada do fluxo, validações e testes: veja `core/WIZARD_TENANT_README.md`.
Suporte AJAX para checagem de subdomínio: rota `core:check_subdomain` (`/core/tenants/check-subdomain/`).

Endpoint interno de métricas do wizard (staff-only): `GET /core/wizard/metrics/`.

#### Observabilidade Avançada do Wizard (2025-09)
Snapshot JSON (`wizard_metrics`) inclui:
- `counters`: `finish_success`, `finish_subdomain_duplicate`, `finish_exception`.
- `latency`: estatísticas gerais (amostragem in-memory rotacionada p50/p90/p95/p99/max + count).
- `latency_by_outcome`: latência segmentada por resultado (`success|duplicate|exception`).
- `last_errors`: deque (até `WIZARD_MAX_ERRORS`, default 25) de erros recentes com timestamp.
- `active_sessions`: quantidade de sessões registradas como ativas na finalização.
- `abandoned_sessions`: quantidade prunada nesta coleta (não cumulativo) com base em inatividade > `WIZARD_ABANDON_THRESHOLD_SECONDS` (default 1800s).
- `time_to_abandon`: estatísticas de duração (p50/p90/p95/p99/max + avg) entre primeiro toque da sessão e abandono detectado.
- `last_finish_correlation_id`: último correlation id finalizado (sucesso ou erro).
- `prometheus_enabled`: indica se counters/histogram/gauges de Prometheus estão ativos.

Prometheus (quando instalado) expõe:
- Counters: `wizard_finish_success_total`, `wizard_finish_subdomain_duplicate_total`, `wizard_finish_exception_total`.
- Histogram geral: `wizard_finish_latency_seconds`.
- Histogram por outcome: `wizard_finish_latency_success_seconds`, `wizard_finish_latency_duplicate_seconds`, `wizard_finish_latency_exception_seconds`.
- Gauges: `wizard_active_sessions`, `wizard_abandoned_sessions`.

Headers HTTP: redirecionamentos finais (sucesso, duplicidade, erro) incluem `X-Wizard-Correlation-Id` para suporte operacional.

Hook externo de latência: definir em `settings.py` um callable `WIZARD_LATENCY_SINK(seconds, correlation_id, outcome=None)`. Retrocompatível com assinatura antiga de 2 parâmetros.

Configurações opcionais:
```
WIZARD_ABANDON_THRESHOLD_SECONDS = 1800           # Inatividade para considerar abandono
WIZARD_MAX_LATENCIES = 200                        # Janela rotacionada de latências
WIZARD_MAX_ERRORS = 25                            # Tamanho do buffer de erros
WIZARD_MAX_ABANDON_LATENCIES = 200                # Janela de time_to_abandon
# WIZARD_LATENCY_SINK = callable(seconds, correlation_id, outcome=None)
```

Flag de debug: `WIZARD_DEBUG` controla logs DEBUG do namespace `core.wizard` (via filtro instalado).

## ⚙️ Novos Utilitários de Observabilidade & Segurança (2025-09)
### Métricas do Módulo de Agendamentos
Se `prometheus_client` estiver instalado e o endpoint `/metrics` exposto (ex: via `django-prometheus` ou view custom), você verá linhas similares:

```
ag_agendamentos_criados_total 42
ag_agendamentos_cancelados_total 5
ag_agendamentos_reagendados_total 3
ag_agendamentos_checkin_total 12
ag_agendamentos_concluidos_total 10
ag_slots_reservados_total 55
ag_waitlist_inscricoes_total 4
ag_evento_sync_total 9
```

Se a lib não estiver presente os counters são no-op (não aparecem). Detalhes e propostas de histogramas: ver `docs/MODULO_AGENDAMENTOS.md` seção 10.4.

Resumo de melhorias recentes focadas em performance, auditoria e 2FA:

- Permission Resolver (cache avançado):
  - Chaves agora incluem `global_era` + hash do mapa de ações (invalidação instantânea em mudanças estruturais).
  - API dinâmica de pipeline (`add_pipeline_step`, `remove_pipeline_step`, `list_pipeline_steps`).
  - Scoring otimizado para permissões personalizadas (deny prioritário e ordenação linear).
  - Invalidação seletiva via `invalidate_cache(user_id=..., tenant_id=...)` ou global (sem argumentos).
- Métricas & Auditoria:
  - Contadores de negações de módulo agora incrementam com utilitário resiliente (`shared.cache_utils.incr_atomic`).
  - Comando `python manage.py metrics_dump` para listar ou limpar chaves de métricas (`--reset`, `--contains=substring`).
  - Comando existente `audit_auth` ganhou suporte a `--reset` e limite de listagem.
- Two-Factor (2FA):
  - Serviço `user_management.services.twofa_service` provê: rotação de segredo TOTP, geração de códigos de recuperação (hash armazenado), consumo com remoção atômica e registro de métricas (sucesso/falha/rate-limit).
  - Campos de métricas (`twofa_*_count`) já no modelo `PerfilUsuarioEstendido` são atualizados via `register_twofa_result`.
  - Documentação detalhada: `docs/TWOFA_SERVICE.md`.
  - Nota de migração do campo de logs estruturados: `docs/MIGRATION_0012_EXTRA_JSON.md`.
  - Notas técnicas do Permission Resolver (pipeline, era global, TTL trace): `docs/SISTEMA_PERMISSOES_COMPLETO.md`
  - Criptografia opcional de segredos: definir `TWOFA_ENCRYPT_SECRETS=True` e lista `TWOFA_FERNET_KEYS`.
  - Comando `python manage.py twofa_reencrypt` para migrar segredos legados (usar `--dry-run` primeiro).
  - Comando `python manage.py prune_expired_permissions` remove permissões personalizadas expiradas.

Testes adicionados cobrem pipeline dinâmica, invalidação global, serviço 2FA e métricas de comandos.

Guia rápido:
```bash
python manage.py metrics_dump              # lista métricas
python manage.py metrics_dump --reset      # reseta métricas
python manage.py audit_auth                # audita contadores de deny
python manage.py audit_auth --reset        # zera contadores de deny
```

### 🔄 Auto Seleção de Tenant em Testes
Durante a suíte de testes há um monkeypatch em `conftest.py` que, ao autenticar um usuário com **exatamente um** vínculo `TenantUser`, injeta automaticamente `tenant_id` na sessão. Objetivo:
- Reduzir redirects 302 desnecessários para telas de seleção.
- Simplificar cenários de wizard e APIs multi-tenant.

Casos cobertos por testes:
- Seleção automática para único tenant (`test_auto_select_single_tenant_session`).
- Nenhuma seleção quando houver múltiplos vínculos (`test_no_auto_select_when_multiple`).

Se o comportamento for removido, os testes relacionados devem falhar — garantindo rastreabilidade.


## 📁 Estrutura do Projeto (Simplificada)

```
backend/
├── pandora_erp/          # Configurações principais
├── core/                 # Módulo principal (empresas, usuários)
├── financeiro/           # Módulo financeiro
├── estoque/             # Módulo de estoque (valuation, picking, BOM)
├── agendamentos/        # Novo módulo: slots, disponibilidades, waitlist, auditoria
├── prontuarios/         # Saúde/estética clínica (serviços clínicos & atendimentos)
├── compras/             # Módulo de compras
├── static/              # Arquivos estáticos
├── templates/           # Templates globais
├── requirements.txt     # Dependências Python
└── manage.py           # Script de gerenciamento Django
```

## 🔐 Configuração de Produção

1. **Variáveis de Ambiente (.env):**
```env
DEBUG=False
DJANGO_SECRET_KEY=sua-chave-secreta-super-segura
ALLOWED_HOSTS=seu-dominio.com,www.seu-dominio.com
DATABASE_URL=postgresql://user:password@localhost:5432/pandora_erp
```

2. **Banco de Dados PostgreSQL:**
```bash
# Instale o psycopg2
pip install psycopg2-binary

# Configure DATABASE_URL no .env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/pandora_erp
```

3. **Coleta de arquivos estáticos:**
```bash
python manage.py collectstatic
```

## ☁️ Deploy no Google App Engine + Cloud SQL (PostgreSQL)

Resumo dos passos implementados no projeto para rodar em App Engine Standard com Cloud SQL via Unix Socket.

### 1. Pré-requisitos GCP
1. Projeto criado (ex: `pandora-474013`).
2. APIs habilitadas:
   - App Engine Admin API
   - Cloud SQL Admin API
   - Secret Manager (opcional)
3. App Engine inicializado na região desejada (ex: `gcloud app create --region=us-central`).

### 2. Instância Cloud SQL
```
gcloud sql instances create pandora \
  --database-version=POSTGRES_17 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-auto-increase \
  --backup-start-time=03:00
```
Defina a senha do usuário `postgres`:
```
gcloud sql users set-password postgres --instance=pandora --password=STRONG_PASSWORD
```

### 3. Criar DB e Usuário Dedicado
Via proxy ou Cloud Console (psql):
```
CREATE DATABASE pandora_app ENCODING 'UTF8' TEMPLATE template0;
CREATE USER pandora_user WITH PASSWORD 'SENHA_FORTE';
GRANT ALL PRIVILEGES ON DATABASE pandora_app TO pandora_user;
ALTER DATABASE pandora_app OWNER TO pandora_user;
```
Script auxiliar: `scripts/cloudsql_init.sql`.

### 4. Configurar `env.yaml`
Entrada típica (Unix socket):
```
DATABASE_URL=postgres://pandora_user:SENHA_URL@/pandora_app?host=/cloudsql/PROJETO:REGIAO:INSTANCIA
```
Exemplo real:
```
postgres://pandora_user:Mal13dad%40@/pandora_app?host=/cloudsql/pandora-474013:us-central1:pandora
```
Importante: encode de caracteres especiais na senha (`@` → `%40`).

### 5. Arquivo `app.yaml`
Já incluído no repositório:
```
runtime: python311
entrypoint: ./entrypoint.sh
beta_settings:
  cloud_sql_instances: PROJETO:REGIAO:INSTANCIA
includes:
  - env.yaml
```

### 6. Retry de Migrações
`entrypoint.sh` possui loop exponencial (padrão 10 tentativas). Ajuste variáveis:
```
MIGRATION_MAX_RETRIES=10
MIGRATION_INITIAL_SLEEP_SECONDS=3
MIGRATION_BACKOFF_FACTOR=1.6
```

### 7. Deploy
```
gcloud app deploy app.yaml --quiet
```
Verifique logs:
```
gcloud app logs tail -s default
```

### 8. Hardening Pós-Sucesso
Defina hosts/CSRF:
```
PANDORA_ALLOWED_HOSTS=meuapp.ue.r.appspot.com,www.seudominio.com
PANDORA_CSRF_ORIGINS=https://meuapp.ue.r.appspot.com,https://www.seudominio.com
```
Ative cabeçalhos extras (HSTS, cookies) via variáveis já suportadas em `settings.py`.

### 9. Problemas Comuns
| Sintoma | Causa Provável | Ação |
|--------|----------------|------|
| connection refused | API Cloud SQL não habilitada / socket name incorreto | Confirmar `cloud_sql_instances` e APIs |
| password auth failed | Senha não encode / senha errada | Atualizar `env.yaml` com URL-encoded |
| Timeout inicial | DB ainda iniciando | Retry já cobre; aumentar `MIGRATION_MAX_RETRIES` se necessário |

---

## ☁️ Deploy no Cloud Run (Moderno)

Nova abordagem (recomendada) usando build de imagem + Cloud Run:

1. Provisionar/Postgres: `scripts/provision_cloudsql.ps1` (gera DATABASE_URL sugerida)
2. Criar arquivo `deploy.env.yaml` a partir de `deploy.env.example.yaml` preenchendo segredos
3. Executar: `scripts/deploy_fast.ps1 -EnvFile deploy.env.yaml`

Entrypoint atual oferece duas opções de servidor ASGI:
```
USE_GUNICORN=1  -> Gunicorn + UvicornWorker (multi-worker CPU bound)
USE_GUNICORN=0  -> Daphne (padrão; bom para websockets)
```

Variáveis de migração:
```
MIGRATION_MAX_RETRIES (default 1)
MIGRATION_INITIAL_SLEEP_SECONDS (default 3)
MIGRATION_BACKOFF_FACTOR (default 1.6)
WAIT_FOR_CLOUDSQL=1 (aguarda socket Unix)
```

WhiteNoise (estáticos) é habilitado com `ENABLE_WHITENOISE=1` e os assets são coletados em build (imagem) reduzindo cold start.

### Exemplo de `deploy.env.yaml`
```
DJANGO_SECRET_KEY: "<chave>"
DJANGO_DEBUG: "False"
DATABASE_URL: "postgres://pandora_user:XXXX@/pandora_app?host=/cloudsql/PROJETO:REGIAO:INSTANCIA"
ENABLE_WHITENOISE: "1"
MIGRATION_MAX_RETRIES: "10"
WAIT_FOR_CLOUDSQL: "1"
USE_GUNICORN: "0"
```

### Principais diferenças vs modelo App Engine
| Item | App Engine | Cloud Run Moderno |
|------|------------|-------------------|
| Coleta estáticos | Runtime | Build-time (imagem) |
| Migrações | Sem retry estruturado | Retry + backoff + espera socket |
| Servidor | Gunicorn fixo | Daphne ou Gunicorn configurável |
| Config Vars | env.yaml (blocagem) | YAML simples via `--env-vars-file` |
| Proteção SQLite | Indireta | Bloqueio quando DEBUG=False sem DATABASE_URL |


### 10. Próximos Melhoramentos
- Mover segredos para Secret Manager (usando substituição em tempo de build ou fetch no startup).
- Configurar VPC Serverless Connector (se precisar acessar recursos privados).
- Adicionar monitoramento (Cloud Monitoring dashboards / alertas de erro).

---

## 🌟 Características do Sistema

- ✅ **Multi-tenant**: Cada empresa isolada
- ✅ **Sistema de Permissões**: Controle granular de acesso
- ✅ **Dashboard Interativo**: Métricas em tempo real
- ✅ **API REST**: Endpoints para integrações
- ✅ **Responsivo**: Interface adaptável a dispositivos
- ✅ **Auditoria**: Log completo de ações
- ✅ **Estoque Moderno**: Multi-depósito, reservas, picking com mensagens, workflow de aprovação de perdas, valuation básico FIFO, consumo BOM, KPIs avançadas e WebSockets.
- ✅ **Agendamentos Moderno**: Listas com cartões de estatísticas dinâmicos, slot capacity & utilization, waitlist priorizada.
- ✅ **Prontuários Integrado**: Serviços clínicos parametrizados + vínculo com agendamentos.
- ✅ **Sistema de Templates Unificado**: Bases *ultra_modern* para listas, formulários e dashboards.

## 📱 Módulos Disponíveis

| Módulo | Status | Descrição |
|--------|--------|-----------|
| Core | ✅ | Empresas, usuários, departamentos |
| Agendamentos | ✅ | Slots, Disponibilidades, Auditoria, Waitlist |
| Prontuários | ✅ | Serviços Clínicos, Atendimentos, Fotos, Anamnese |
| Admin Dashboard | ✅ | Painel administrativo |
| Financeiro | ✅ | Contas a pagar/receber |
| Estoque | ✅ | Controle de produtos |
| Compras | ✅ | Gestão de fornecedores |
| RH | ✅ | Gestão de funcionários |
| BI | ✅ | Business Intelligence |
| Chat | ✅ | Comunicação interna |

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

- 📧 Email: seu-email@dominio.com
- 📱 WhatsApp: (xx) xxxxx-xxxx
- 🌐 Website: https://seu-dominio.com

## 🔄 Changelog (Resumo)

Changelog completo agora em `docs/CHANGELOG.md`.

Principais entradas recentes:
| Data | Tema | Destaques |
|------|------|-----------|
| 2025-08-22 | Agendamentos & Prontuários | Estatísticas em listas, botão dashboard unificado, form Procedimento corrigido, TenantSafeMixin |
| 2025-08 (WIP) | Modernização Estoque | Endpoints ampliação, picking em tempo real, KPIs, valuation manutenção |
| 2025-09-19 | Wizard Observabilidade | Latency outcomes, gauges, abandono (tempo), correlation header, hook outcome |
| 2025-07-28 | v1.0.0 | Lançamento inicial |


## ⚙️ Tarefas Assíncronas (Celery + Redis)

Defina `REDIS_URL=redis://localhost:6379/0` no `.env`.

Serviços (docker-compose incluído):
```
docker compose up --build
```

Manual (Windows / cmd):
```
celery -A pandora_erp worker -l info -Q default,media
celery -A pandora_erp beat -l info
python manage.py runserver
```

Principais tasks:
- `prontuarios.tasks.gerar_thumbnail_foto` – thumbnail JPEG rápida
- `prontuarios.tasks.gerar_variacao_webp` – versão otimizada WebP (`imagem_webp`)
- `prontuarios.tasks.extrair_video_poster` – frame de pré-visualização (`video_poster`) via ffmpeg
- Limpeza semanal / verificações diárias agendadas via Beat

Testes podem usar:
```
CELERY_TASK_ALWAYS_EAGER=True
```

## 🖼️ Otimização de Mídia Clínica

Campos em `FotoEvolucao`:
- `imagem_thumbnail`: pré-visualização leve
- `imagem_webp`: versão comprimida moderna (fallback automático em `<picture>`)
- `video_poster`: frame extraído de vídeos curtos
 - `video_meta`: metadados/estado (duração, dimensões, validação, transcodificação)

Instale `ffmpeg` para habilitar geração de posters (senão a task falha silenciosamente sem interromper upload).

## 📊 Métricas Prometheus

Endpoint: `/metrics`

Principais counters:
- `pandora_task_success_total{task="..."}`
- `pandora_task_failure_total{task="..."}`
- `pandora_video_transcodes_total{profile="h264|webm"}`
- `pandora_video_validation_success_total`
- `pandora_video_validation_failure_total{motivo="..."}`

### PermissionResolver (autorização)

Expostos quando `prometheus_client` disponível:
- `permission_resolver_decisions_total{action="VIEW_COTACAO",source="role",allowed="True"}`
- `permission_resolver_cache_hits_total`
- `permission_resolver_cache_misses_total`
- `permission_resolver_latency_seconds` (histogram)

Ativar trace detalhado em testes/debug:
```
PERMISSION_RESOLVER_TRACE=True
```
Exemplo de razão com trace: `Role Admin permite VIEW_COTACAO|src=role|trace=role_allow`.

**Para detalhes completos do Permission Resolver:** veja `docs/SISTEMA_PERMISSOES_COMPLETO.md`

Fila dedicada de vídeo (`video`) com worker separado em `docker-compose.yml` (`worker-video`).

## 🧩 Padrões de Templates (Resumo)

- Listas: estender `pandora_list_ultra_modern` e fornecer blocks `page_icon`, `page_title`, `page_subtitle`, contexto `statistics` (lista de dicts) e `dashboard_url` opcional.
- Formulários: estender `pandora_form_ultra_modern`, usar bloco `form_main` encapsulando `<form>`; ações via include `partials/_form_actions.html`.
- Home/Dashboard: `pandora_home_ultra_modern` para cards e áreas hero.
- Filtro utilitário criado: `get_field` (agendamentos.templatetags) + `add_class` para ajuste dinâmico.

Detalhes completos em `docs/FRONTEND_TEMPLATES.md`.

## 🛡️ Multi-tenant & Segurança

- Função central: `core.utils.get_current_tenant(request)` com cache por request.
- Mixins: `TenantMixin` (agendamentos) e `TenantSafeMixin` (prontuários) previnem `AttributeError` quando tenant não selecionado.
- Todas as queries sensíveis usam filtro `tenant=...` explícito.

### 🔐 2FA (TOTP) & Rate Limiting

Configurações em `settings.py` (defina se não existentes):

```
TWOFA_LOCK_THRESHOLD = 5              # Falhas consecutivas que disparam lock
TWOFA_LOCK_MINUTES = 5                # Duração do lock em minutos
TWOFA_ALERT_THRESHOLDS = (20, 50, 100)  # Contagens cumulativas para email de alerta
TWOFA_ALERT_EMAIL_COOLDOWN_MINUTES = 30 # Cooldown por threshold
TWOFA_GLOBAL_IP_LIMIT = 60            # Tentativas totais (token+recovery) por IP por janela
TWOFA_GLOBAL_IP_WINDOW = 300          # Janela (segundos) do rate limit global
```

Métricas agregadas: endpoint `/user-management/2fa/metrics.json` retorna
`total, habilitados, confirmados, sucessos, falhas, recovery, rl_blocks, ip_blocks`.

Snapshot e reset opcional:
```
python manage.py twofa_metrics_snapshot --include-ip-blocks
python manage.py twofa_metrics_snapshot --reset --include-ip-blocks
```

### 🔑 Rotação de Chaves Fernet (Segredo TOTP Criptografado)

1. Gerar nova chave: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. Adicionar como primeira em `FERNET_KEYS = [NEW_KEY, *OLD_KEYS]`
3. Deploy: leitura aceita antigas, grava com a nova
4. (Opcional) Script/command para recriptografar segredos antigos
5. Após período seguro, remover chaves antigas gradualmente

Princípio: primeira chave = ativa; demais somente para decrypt. Nunca remover chave antiga enquanto ainda houver segredos não migrados.

## 🧪 Testes & Qualidade

- Priorizar testes de serviço (ex: geração de slots) isolando side effects.
- Evitar contar sobre querysets já paginados (usar `self.get_queryset()` antes de slice para estatísticas).
- Validar templates novos com `runserver` + inspeção de blocos obrigatórios.

### Padrão Oficial de Execução de Testes

O projeto usa `pytest` como runner principal. Configuração em `pytest.ini` define descoberta (`test_*.py`) e cobertura padrão (`--cov=core --cov=user_management --cov=shared`).

Comandos típicos:
```
pytest                   # executa tudo
pytest -q                # modo silencioso
pytest -k twofa          # filtra por substring
pytest user_management/tests/test_twofa_flow.py::test_twofa_full_flow
pytest --cov --cov-report=term-missing
```

### 🏃 Execução Rápida (Desenvolvimento Local)

Para ciclos TDD curtos, utilize o script Windows `run_fast.bat` que:
- Desativa cobertura (exporta `NO_COV=1`).
- Pula testes marcados `@pytest.mark.slow` por padrão.

Uso:
```
run_fast.bat                         # roda tudo (sem slow, sem cobertura)
run_fast.bat -k twofa                # filtra
run_fast.bat tests/core/..::Test::test_case
```
Variáveis / flags suportados:
| Variável / Flag | Efeito |
|-----------------|--------|
| NO_COV=1        | Remove coleta de cobertura (hook em `conftest.py`). |
| ENFORCE_COVERAGE=1 | Força manter threshold mesmo em execução parcial. |
| RUN_SLOW=1      | Inclui testes `slow` sem precisar `--runslow`. |
| --runslow       | Inclui testes `slow` (equivalente a RUN_SLOW=1). |

Execução parcial (≤3 testes) sem `ENFORCE_COVERAGE` desativa automaticamente o `cov_fail_under` e normaliza o exit code se apenas a cobertura falharia.

Para CI: **não** definir `NO_COV` / `RUN_SLOW` (cobertura integral + inclusão de testes lentos conforme configurado no pipeline).

Otimizações automáticas em modo teste (ativadas por `PYTEST_CURRENT_TEST`):
- Hash de senha MD5 (rápido)
- Desabilitados validadores de senha
- Email backend in-memory (`locmem`)
- Tasks Celery (quando configurado) em modo eager

Para manter compatibilidade temporária, ainda é possível usar:
```
python manage.py test app_label.TestCaseClasse
```
Mas recomenda-se migrar novos testes para formato função + fixtures do pytest.

### Diretrizes de Padronização de Testes
1. Nome de arquivo: `test_<contexto>_<aspecto>.py` (ex: `test_twofa_enforcement.py`).
2. Sem dependência entre testes; cada teste cria seus dados.
3. Usar fixtures (`client`, `db`, `settings`, `tenant_with_all_modules`) ao invés de setup manual repetido.
4. Marcar testes lentos com `@pytest.mark.slow` (futuro: habilitar skip default).
5. Afirmar mensagens ou campos críticos, não HTML inteiro.
6. Para performance, evitar `time.sleep` > 0.2s; preferir monkeypatch em funções de tempo.

### Metas de Cobertura (proposta)
- Núcleo de segurança (user_management, core.permission resolver): >= 90%
- Demais módulos gradualmente para >= 70%.

### 📈 Permission Resolver (Observabilidade e Pipeline)
O `PermissionResolver` agora possui:
- Pipeline configurável (`PermissionResolver.pipeline`) com steps: `role`, `implicit`, `default` (podendo ser estendido em runtime para novos módulos sem alterar código base).
- Métricas Prometheus:
  - `permission_resolver_decisions_total{action,source,allowed}`
  - `permission_resolver_cache_hits_total` / `permission_resolver_cache_misses_total`
  - `permission_resolver_latency_seconds` (buckets p50..p99 baseados em latências sub-milisegundo a 1s)
- Trace on-demand: habilitar via `settings.PERMISSION_RESOLVER_TRACE=True` (recalcula decisão mesmo com cache para enriquecer razão).
- Cache versionado por (user, tenant) eliminando necessidade de `delete_pattern` em Redis.

**Documentação completa:** `docs/SISTEMA_PERMISSOES_COMPLETO.md`

Extensão de pipeline (exemplo):
```python
from shared.services.permission_resolver import permission_resolver

def _step_custom_report(user, tenant, action, resource, context):
    if action == 'VIEW_CUSTOM_REPORT' and user.is_staff:
        return True, 'Staff pode ver relatório custom', 'custom'
    return None

permission_resolver.pipeline.insert(0, '_step_custom_report')  # alta precedência
```

### 🔍 Badge de Cobertura (CI)
Integrar com Codecov:
1. Criar token no Codecov (se privado) e adicionar como secret `CODECOV_TOKEN`.
2. Adicionar step ao workflow CI após geração de `coverage.xml`:
```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    files: coverage.xml
    fail_ci_if_error: true
```
3. Substituir badge `Coverage` no topo por (exemplo):
```
![Coverage](https://codecov.io/gh/ORG/REPO/branch/main/graph/badge.svg)
```

### 🛡️ Hardening de Segurança (Resumo Próximo Passo)
- Ativar cabeçalhos: `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` em produção.
- Auditar permissões personalizadas expiradas (job diário limpando registros expirados para reduzir custo de varredura).

- Acompanhar tendência (arquivo futuro `docs/TEST_METRICS.md`).


## ⚙️ Feature Flags / Configuração

- Variáveis sugeridas:
  - `REQUIRE_SERVICO` (força seleção de serviço em agendamento se True)
  - `CLIENT_PORTAL_URL` (exposto em home de agendamentos)

  - `PRESERVE_WIZARD_SESSION_ON_EXCEPTION` (default: True)
    Controla se, ao ocorrer exceção na finalização do wizard de tenant, os dados da sessão são preservados para facilitar correção pelo usuário (True) ou limpos imediatamente (False, mais seguro contra retenção de dados sensíveis).

  Exemplo (settings.py):
  ```python
  # Wizard Tenants – sessão no erro (default True)
  PRESERVE_WIZARD_SESSION_ON_EXCEPTION = True  # ou False
  ```

  Exemplo (Windows PowerShell):
  ```powershell
  $env:PRESERVE_WIZARD_SESSION_ON_EXCEPTION = "False"
  ```

## 📎 Documentação Expandida

Ver pasta `docs/` para guias aprofundados por módulo e arquitetura.
