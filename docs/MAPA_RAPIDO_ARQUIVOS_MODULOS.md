# Mapa Rápido: Arquivos do Sistema de Módulos

**Referência Rápida** para navegação durante debug/correção

---

## 🎯 ARQUIVOS PRINCIPAIS (ALTA PRIORIDADE)

### 1. core/models.py
**Linhas Críticas:**
- 101: Campo `enabled_modules` (JSONField)
- 659-693: Property `modules` (getter/setter)
- 693-710: Método `has_module()`
- 767-773: Método `is_module_enabled()`
- 719-756: Método `_normalize_enabled_modules()`
- 757-764: Método `_compose_enabled_modules_dict()`
- 774-830: Método `_apply_plan_and_essentials()` ⚠️ CRÍTICO
- 532-543: Constantes de plano

**Responsabilidade:** Modelo de dados, normalização, aplicação de regras de plano

---

### 2. core/wizard_views.py
**Linhas Críticas:**
- 79: Constante `FORM_PREFIX_MAIN = "main"`
- 977-1010: `_augment_step_config_with_post()` ⚠️ CRÍTICO (extrai POST)
- 660-715: `_save_configuration_data()` ⚠️ CRÍTICO (persiste módulos)
- 1338-1346: `_process_complete_configuration_data()`
- 1072-1230: `load_tenant_data_to_wizard()` (linha 1185 crítica)
- 2110-2150: `consolidate_wizard_data()` ⚠️ CRÍTICO (save duplo)

**Responsabilidade:** Orquestração do wizard, processamento de dados, persistência

---

### 3. core/wizard_forms.py
**Linhas Críticas:**
- 927-1050: Classe `TenantConfigurationWizardForm`
- 937-944: Campo `enabled_modules` (MultipleChoiceField)
- 945-1010: Método `__init__()` (popula choices e initial)
- 1011-1045: Property `module_catalog` (dados para template)
- 934: Constante `AVAILABLE_MODULES`

**Responsabilidade:** Formulário de configuração, validação, catálogo para UI

---

### 4. core/module_registry.py
**Linhas Críticas:**
- 30-250: Dict `MODULE_DEFINITIONS` (todos os módulos)
- 250-280: Dict `PLAN_DEFAULT_MODULES` (defaults por plano)
- 282-284: List `ESSENTIAL_MODULES` (sempre incluídos)
- 286-289: Função `get_essential_modules()`
- 349-366: Função `normalize_modules_canonical()`
- 378-409: Função `annotate_modules_for_ui()`
- 426-428: Função `get_all_module_choices()`

**Responsabilidade:** Fonte única de verdade, metadados de módulos, utilidades

---

### 5. core/services/wizard_normalizers.py
**Linhas Críticas:**
- 28-36: Função `dedupe_preserve_order()`
- 40-70: Função `normalize_enabled_modules()` ⚠️ CRÍTICO
- 72-78: Dict `_MODULE_ALIASES` (mapeamento de aliases)
- 80-98: Função `normalize_module_aliases()` ⚠️ CRÍTICO
- 101-130: Função `parse_socials_json()`

**Responsabilidade:** Normalização de formatos, resolução de aliases, deduplicação

---

### 6. templates/core/wizard/step_configuration.html
**Linhas Críticas:**
- 6: `{% with modules_field_name=form.enabled_modules.html_name %}`
- 153: `<span id="moduleCounter">` (contador)
- 158-163: Botões selecionar/limpar todos
- 165-245: Loop de categorias e checkboxes
- 181: `name="{{ modules_field_name }}"` (resolve para `main-enabled_modules`)
- 369-413: JavaScript de interação

**Responsabilidade:** Interface do usuário, renderização de módulos, interação

---

## 🔍 ARQUIVOS SECUNDÁRIOS (MÉDIA PRIORIDADE)

### 7. core/authorization.py
**Linhas Críticas:**
- 95-106: Função `_parse_enabled_modules()`
- 107-135: Função `_tenant_has_module()` (verifica se módulo habilitado)
- 180-220: Função `can_access_module()` (decisão de acesso)

**Responsabilidade:** Verificação de acesso a módulos em runtime

---

### 8. core/middleware.py
**Linhas Críticas:**
- 361-389: Método `_unified_access()` (validação unificada)
- 390-410: Método `_legacy_access()` (fallback legado)
- 396: Usa `tenant.is_module_enabled(target)`

**Responsabilidade:** Interceptação de requests, bloqueio de acesso não autorizado

---

## ✅ COMANDOS DE MANAGEMENT - REMOVIDOS

### ~~9. repair_modules.py~~ - ✅ DELETADO
**Motivo:** Redundante e perigoso (sobrescrevia configs manuais)

### ~~10. sync_modules.py~~ - ✅ DELETADO
**Motivo:** Substituído pela migration 0012

### ~~11. recompute_plan_modules.py~~ - ✅ DELETADO
**Motivo:** PERIGO - apagava seleções manuais

**✅ Substituídos por:**
- Migration `0012_normalize_enabled_modules_format.py` (normalização segura)
- Normalização automática no código (sem perda de dados)

---

## 🧪 SUÍTES DE TESTE

### 12. tests/core/tenant_wizard/test_wizard_module_alias_and_flags.py
**Testa:** Resolução de aliases, flags de módulos

### 13. tests/core/tenant_wizard/test_wizard_module_alias_normalizers.py
**Testa:** Normalização de aliases, pipeline combinada

### 14. tests/core/tenant_wizard/test_wizard_services.py
**Testa:** Funções normalizadoras (normalize_enabled_modules)

### 15. tests/core/authorization/test_authorization.py
**Testa:** Sistema de autorização modular

### 16. tests/core/authorization/test_authorization_strict.py
**Testa:** Modo estrito de autorização

### 17. tests/core/plans/test_plan_modules.py
**Testa:** Aplicação de módulos por plano

### 18. tests/core/enabled_modules/test_enabled_modules_normalization.py
**Testa:** Normalização do campo enabled_modules

---

## 📊 FLUXO DE CHAMADAS (SAVE)

```
POST /wizard/
    ↓
wizard_views.post()
    ↓
wizard_views.finish_wizard()
    ↓
wizard_views.consolidate_wizard_data()
    ↓
┌─────────────────────────────────────┐
│ PRIMEIRO SAVE (linha 2128)          │
│ tenant.save()                       │
│   ↓                                 │
│ models.Tenant.save()                │
│   ↓                                 │
│ models._apply_plan_and_essentials() │
│   (adiciona defaults do plano)      │
└─────────────────────────────────────┘
    ↓
wizard_views._process_complete_configuration_data()
    ↓
wizard_views._save_configuration_data()
    ↓
wizard_normalizers.normalize_enabled_modules()
    ↓
wizard_normalizers.normalize_module_aliases()
    ↓
models.Tenant._compose_enabled_modules_dict()
    ↓
┌─────────────────────────────────────┐
│ SEGUNDO SAVE (linha via 710)        │
│ tenant.save()                       │
│   ↓                                 │
│ models.Tenant.save()                │
│   ↓                                 │
│ models._apply_plan_and_essentials() │
│   (adiciona essenciais)             │
└─────────────────────────────────────┘
```

---

## 📊 FLUXO DE CHAMADAS (READ)

```
Acesso a /clientes/list
    ↓
middleware.ModuleRequiredMixin.process_request()
    ↓
middleware._unified_access() ou _legacy_access()
    ↓
authorization.can_access_module()
    ↓
authorization._tenant_has_module()
    ↓
┌─────────────────────────────────────┐
│ models.Tenant.is_module_enabled()   │
│   ↓                                 │
│ models.Tenant.has_module()          │
│   ↓                                 │
│ models.Tenant.modules (property)    │
│   ↓                                 │
│ models._normalize_enabled_modules() │
└─────────────────────────────────────┘
```

---

## 🎯 PONTOS DE LOG RECOMENDADOS

### LOG 1: Após POST processado
**Arquivo:** `core/wizard_views.py`  
**Linha:** ~1000 (após `_augment_step_config_with_post`)
```python
logger.critical("[DEBUG_MODULES] wizard_data.enabled_modules=%s", main_block.get("enabled_modules"))
```

### LOG 2: Antes do save de configuração
**Arquivo:** `core/wizard_views.py`  
**Linha:** ~693 (antes de save em `_save_configuration_data`)
```python
logger.critical("[DEBUG_MODULES] cleaned.enabled_modules=%s", cleaned.get("enabled_modules"))
```

### LOG 3: Após save de configuração
**Arquivo:** `core/wizard_views.py`  
**Linha:** ~710 (após save)
```python
logger.critical("[DEBUG_MODULES] tenant.enabled_modules=%s", tenant.enabled_modules)
```

### LOG 4: Após aplicar plano
**Arquivo:** `core/models.py`  
**Linha:** ~827 (final de `_apply_plan_and_essentials`)
```python
logger.critical("[DEBUG_MODULES] apply_plan finalizado=%s", self.enabled_modules)
```

---

## 🔧 QUERIES DE DEBUG

### Query 1: Ver formato atual no banco
```sql
SELECT 
    id, 
    name, 
    subdomain, 
    plano_assinatura,
    enabled_modules,
    JSON_TYPE(enabled_modules) as tipo
FROM core_tenant 
ORDER BY id DESC 
LIMIT 10;
```

### Query 2: Ver módulos em formato legível
```sql
SELECT 
    id,
    name,
    JSON_EXTRACT(enabled_modules, '$.modules') as modules_list,
    JSON_LENGTH(JSON_EXTRACT(enabled_modules, '$.modules')) as module_count
FROM core_tenant
WHERE enabled_modules IS NOT NULL;
```

### Query 3: Identificar formatos inconsistentes
```sql
SELECT 
    id,
    name,
    CASE
        WHEN JSON_TYPE(enabled_modules) = 'ARRAY' THEN 'LISTA'
        WHEN JSON_EXTRACT(enabled_modules, '$.modules') IS NOT NULL THEN 'DICT_COMPLETO'
        ELSE 'DICT_LEGADO'
    END as formato
FROM core_tenant
GROUP BY formato;
```

---

## 📞 REFERÊNCIAS CRUZADAS

**Documento Completo:** `AUDITORIA_TECNICA_ATIVACAO_MODULOS.md`  
**Resumo Executivo:** `AUDITORIA_MODULOS_RESUMO_EXECUTIVO.md`  
**Este Documento:** `MAPA_RAPIDO_ARQUIVOS_MODULOS.md`

---

**Última Atualização:** 23/10/2025  
**Versão:** 1.0
