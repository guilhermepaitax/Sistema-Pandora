# Auditoria: Wizard de Tenants — Step 5 (Módulos e Configurações)

Status: INVESTIGAÇÃO (apenas análise, sem correção aplicada)
Data: 2025-10-17
Escopo: Seleção de módulos no Step 5 (“Selecionar todos” marca os checkboxes mas os módulos não são persistidos como acesso inicial do Tenant após finalizar o wizard).

## Sintoma observado
- No Step 5, ao clicar em “Selecionar todos”, todos os checkboxes ficam marcados na UI.
- Após concluir o wizard, o Tenant resultante não recebe os módulos selecionados como “habilitados” (acesso inicial ausente ou incompleto).

## Fluxo técnico envolvido (end-to-end)
1) UI/Template
   - Arquivo: `templates/core/wizard/step_configuration.html`
   - Os checkboxes de módulos são inputs HTML “puros” com:
     - name="enabled_modules"
     - value="<codigo_modulo>"
     - Alguns essenciais aparecem “checked disabled” (bloqueados)
   - Botões auxiliares (JS) para “Selecionar todos” e “Limpar”.

2) Recepção no servidor (POST do Step 5)
   - Arquivo: `core/wizard_views.py`
   - Método: `_augment_step_config_with_post`
     - Lê os valores via `request.POST.getlist("enabled_modules")` (sem prefixo), normaliza aliases e coloca em `wizard_data["step_5"]["main"]["enabled_modules"]`.
     - Também captura `main-subdomain` e `main-status`.

3) Consolidação/finalização do wizard
   - Arquivo: `core/wizard_views.py`
   - Método: `consolidate_wizard_data`
     - Ordem aplicada:
       1. Step 1 em memória
       2. Step 5 (subdomain/status) em memória
       3. `tenant.save()` (gera PK e aplica plano/essenciais)
       4. Step 2 e 3 (endereços/contatos)
       5. Step 5 completo (módulos): `_process_complete_configuration_data` → `_save_configuration_data`
       6. Step 6 (admins)

4) Persistência dos módulos
   - Arquivo: `core/wizard_views.py`
   - Método: `_save_configuration_data`
     - Opcionalmente valida via `ModuleConfigurationForm` (choices do registry).
     - Normaliza `enabled_modules` (lista) e faz `setattr(tenant, "enabled_modules", lista)`.
     - `tenant.save()` chama `Tenant._apply_plan_and_essentials` e persiste no formato canônico `{ "modules": [...], <flags_legacy> }`.

5) Modelo do Tenant
   - Arquivo: `core/models.py`
   - Campo: `enabled_modules = models.JSONField(default=dict, ...)` (suporta dict/legado/list/str e normaliza no `save()`).
   - Método: `_apply_plan_and_essentials`
     - Essenciais sempre garantidos.
     - Quando há seleção manual não-vazia, não aplica defaults de plano (apenas essenciais).

## Pontos críticos que podem explicar o sintoma
1) JS “Selecionar todos” altera apenas aparência mas não o atributo `checked` dos inputs reais.
   - Efeito: `request.POST.getlist("enabled_modules")` vem vazio/ parcial.
   - Verificação: Inspecionar DOM devtools e ver se os inputs `name=enabled_modules` estão `checked` antes de submeter.

2) Inputs “disabled” não são enviados no POST.
   - Essenciais aparecem “checked disabled”; por padrão, inputs `disabled` não são enviados.
   - Mitigação: o modelo adiciona essenciais no `save()`; portanto, ausência dos essenciais no POST não deveria remover acesso.
   - Risco: Se a seleção total depende de inputs “disabled”, o POST pode não refletir o “selecionar todos” integral (exceto essenciais, que o modelo repõe).

3) Prefixos e mistura de abordagens (form vs inputs puros).
   - O form de Step 5 é criado com `prefix="main"`, então campos do form seriam `main-enabled_modules`.
   - O template usa `name="enabled_modules"` (sem prefixo). Isso está compensado por `_augment_step_config_with_post()`, que lê diretamente sem prefixo.
   - Risco: Se o usuário clicar em “Finalizar” num step que não reprocessa o POST corrente, os dados podem não entrar no `wizard_data` (ver item 5).

4) Validação de choices via `ModuleConfigurationForm` (core/forms.py)
   - Caso haja divergência entre os módulos exibidos no Step 5 e os choices do form, `is_valid()` pode falhar.
   - O código prevê fallback (“usar dados crus”), mas vale checar logs:
     - `logger.warning("ModuleConfigurationForm inválido, usando dados crus: %s", form.errors)`
   - Risco: Se houver normalização extra no form que limpe módulos, mas como há fallback, o impacto deve ser baixo.

5) Botão “Finalizar” pulando a coleta do POST do step corrente
   - No `post()` do wizard: se `finish_requested`, a view chama `finish_wizard()` sem processar `process_step_data()` do step atual.
   - O template `pandora_wizard_form_ultra_modern.html` só mostra “Finalizar” no último passo; porém, se existir um caminho que permita finalizar direto a partir do Step 5 (ex.: atalho, ação custom), o `enabled_modules` recém-marcado não entraria no `wizard_data`.
   - Verificação: Confirmar que o usuário avançou para Step 6/7 após marcar módulos, ou que o Step 5 recebeu um POST com `wizard_action=next` antes de “Finalizar”.

6) Divergência entre os códigos exibidos e os esperados pelo back-end
   - O template usa `m.key` vindo do `module_catalog` (registry). Isso deve coincidir com `ModuleConfigurationForm.AVAILABLE_MODULES_CHOICES`.
   - Verificação: auditar se todos os 33 módulos do catálogo estão também em `get_all_module_choices()` e se não há alias faltando.

## Evidências (trechos-chave)
- `_augment_step_config_with_post` (POST → wizard_data):
  - `core/wizard_views.py` L. 856–881
- `_save_configuration_data` (wizard_data → Tenant.save):
  - `core/wizard_views.py` L. 564–607
- `Tenant._apply_plan_and_essentials` (normalização final):
  - `core/models.py` L. 772–839
- `ModuleConfigurationForm` (choices/validação):
  - `core/forms.py` L. 251–324

## Plano de verificação (sem correção ainda)
1) Capturar o POST real no Step 5 (ambiente de dev):
   - Logar `len(request.POST.getlist("enabled_modules"))` e os primeiros N códigos.
   - Confirmar presença de `main-subdomain` e `main-status` no mesmo POST.

2) Validar o `wizard_data` após o POST do Step 5:
   - Logar `wizard_data["step_5"]["main"].get("enabled_modules")` antes da consolidação.

3) Validar a entrada em `_save_configuration_data`:
   - Logar o total de módulos de `config_data["enabled_modules"]` recebido.
   - Logar `form.is_valid()`, `form.errors` quando aplicável.

4) Validar após `tenant.save()` no Step 5 completo:
   - Logar `tenant.enabled_modules` (tamanho e alguns códigos) após a chamada.

5) Conferir o JS de “Selecionar todos” no template:
   - Confirmar que a função realmente seta `checkbox.checked = true` nos inputs com `name="enabled_modules"`.
   - Confirmar que a seleção global percorre todos os checkboxes visíveis (e não apenas os que estão dentro de uma categoria ativa/expandida), e que não interfere com `disabled` além do esperado.

## Hipótese principal (para teste)
- Ação “Selecionar todos” não está marcando efetivamente os inputs `name=enabled_modules` (ou marca mas há subset parcial/filtrado), resultando em POST incompleto. Alternativamente, a finalização pode estar ocorrendo sem persistir o POST do Step 5 (quando “Finalizar” é acionado antes de `process_step_data()` atualizar o `wizard_data`).

## Próximas ações sugeridas (ainda sem aplicar fix)
- Inserir logs leves e temporários nas funções citadas para confirmar a trajetória dos dados (POST → wizard_data → persistência).
- Validar no DevTools do navegador se, ao clicar “Selecionar todos”, os inputs `enabled_modules` ficam `checked` de fato.
- Rodar um teste manual:
  1) Entrar no Step 5, clicar “Selecionar todos”, clicar “Próximo” (não “Finalizar”), avançar ao Step 6.
  2) Voltar ao Step 5 e verificar se os módulos permanecem selecionados (confirmando que o `wizard_data` foi populado).
  3) Finalizar e checar, no banco, `tenant.enabled_modules`.

## Observações adicionais sobre `portal_ativo`
- A validação do form (`TenantConfigurationWizardForm.clean`) desativa `portal_ativo` quando o módulo `portal_cliente` não está presente.
- Como o wizard usa inputs puros para módulos e não o campo do form, a coerência de `portal_ativo` depende do fluxo de persistência final em `_save_configuration_data` + checagem pós-save (que já força `portal_ativo=False` se o módulo não está ativo). Isso garante consistência mesmo se o form não capturou os módulos.

## Conclusão parcial
- O pipeline de back-end está preparado para aceitar `enabled_modules` via POST sem prefixo e persistir corretamente. As duas causas mais prováveis para o sintoma são: (1) problema de JS/DOM que não marca efetivamente todos os checkboxes; (2) finalização do wizard sem que o Step 5 tenha sido consolidado no `wizard_data` (pular o `process_step_data` do step corrente). A próxima etapa é instrumentar logs pontuais e validar o comportamento no navegador para isolar a causa raiz.
