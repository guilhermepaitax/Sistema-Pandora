"""Wizard de cadastro/edição de Obras com checagem de módulo habilitado.

Este módulo foi ajustado para atender às regras de lint/tipagem do projeto
sem alterar regras de negócio existentes.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

from django import forms
from django.contrib import messages
from django.db import DatabaseError, IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from clientes.models import Cliente
from core.models import TenantUser
from core.utils import get_current_tenant
from core.wizard_forms import TenantAddressWizardForm
from core.wizard_views import TenantCreationWizardView
from documentos.services import consolidate_wizard_temp_to_documents

from .models import Obra
from .wizard_forms import (
    ObraConfigurationWizardForm,
    ObraContactsWizardForm,
    ObraDocumentsWizardForm,
    ObraIdentificationWizardForm,
)

logger = logging.getLogger(__name__)

OBRA_WIZARD_STEPS = {
    1: {
        "name": "Dados Iniciais",
        "form_classes": {"main": ObraIdentificationWizardForm},
        "template": "obras/wizard/step_identification.html",
        "icon": "fas fa-hard-hat",
        "description": "Informações básicas da obra",
    },
    2: {
        "name": "Endereços",
        "form_classes": {"main": TenantAddressWizardForm},
        "template": "core/wizard/step_address.html",
        "icon": "fas fa-map-marker-alt",
        "description": "Endereço principal e adicionais",
    },
    3: {
        "name": "Contatos",
        "form_classes": {"main": ObraContactsWizardForm},
        "template": "obras/wizard/step_contacts.html",
        "icon": "fas fa-user-tie",
        "description": "Responsável e contatos principais",
    },
    4: {
        "name": "Documentos",
        "form_classes": {"main": ObraDocumentsWizardForm},
        "template": "obras/wizard/step_documents.html",
        "icon": "fas fa-file-alt",
        "description": "Envio de documentos (opcional)",
    },
    5: {
        "name": "Configurações",
        "form_classes": {"main": ObraConfigurationWizardForm},
        "template": "obras/wizard/step_configuration.html",
        "icon": "fas fa-cogs",
        "description": "Status, progresso e observações",
    },
}


class ObraWizardView(TenantCreationWizardView):
    """Wizard de criação/edição de Obras com UI de passos e preview."""

    success_url = reverse_lazy("obras:obras_list")

    def test_func(self) -> bool:
        """Permite superusuário OU admin do tenant com módulo obras habilitado.

        Esta verificação ocorre antes de dispatch() e substitui a verificação
        da classe pai que restringe apenas a superusuários.

        Regras de acesso:
        1. Superusuários têm acesso total (gerenciam todas as obras)
        2. Usuários comuns precisam:
           - Estar autenticados
           - Ter um tenant selecionado
           - Ser administrador do tenant (is_tenant_admin=True)
           - Tenant precisa ter o módulo 'obras' habilitado

        Returns:
            bool: True se o usuário tem permissão, False caso contrário

        """
        user = self.request.user

        # Superusuário sempre tem acesso total
        if user.is_superuser:
            return True

        # Usuário precisa estar autenticado
        if not user.is_authenticated:
            return False

        # Obtém o tenant atual da sessão
        tenant = get_current_tenant(self.request)
        if not tenant:
            # Sem tenant selecionado, nega acesso
            # (UserPassesTestMixin redirecionará para login ou página de negação)
            return False

        # Verifica se o usuário é administrador do tenant
        is_admin = TenantUser.objects.filter(
            tenant=tenant,
            user=user,
            is_tenant_admin=True,
        ).exists()

        if not is_admin:
            return False

        # Verifica se o módulo 'obras' está habilitado para este tenant
        # Nota: A verificação adicional em get()/post() fornece mensagem mais amigável
        return tenant.is_module_enabled("obras")

    @property
    def wizard_steps(self) -> dict[int, dict[str, Any]]:
        """Retorna a configuração dos passos do wizard."""
        return OBRA_WIZARD_STEPS

    # Isolar sessão para este wizard
    def get_current_step(self) -> int:
        """Passo corrente salvo em sessão."""
        return self.request.session.get("obra_wizard_step", 1)

    def set_current_step(self, step: int) -> None:
        """Define o passo corrente do wizard na sessão."""
        self.request.session["obra_wizard_step"] = step
        self.request.session.modified = True

    def get_wizard_data(self) -> dict[str, Any]:
        """Retorna os dados do wizard (serializados) guardados em sessão."""
        return self.request.session.get("obra_wizard_data", {})

    def get_editing_tenant(self) -> Obra | None:
        """Retorna a Obra em edição (se houver), respeitando o tenant quando aplicável."""
        pk = self.kwargs.get("pk") if hasattr(self, "kwargs") else None
        if not pk:
            return None
        try:
            tenant = get_current_tenant(self.request)
            qs = Obra.objects
            if not self.request.user.is_superuser and hasattr(Obra, "tenant") and tenant:
                qs = qs.filter(tenant=tenant)
            return qs.get(pk=pk)
        except Obra.DoesNotExist:
            return None

    # Construção de formulários por step
    def create_forms_for_step(
        self,
        current_step: int,
        _editing_entity: Obra | None,
        data_source: str = "POST",
    ) -> dict[str, forms.BaseForm]:
        """Cria instâncias de formulários para o passo atual (GET/POST)."""
        step_config = self.wizard_steps[current_step]
        form_classes = step_config["form_classes"]
        forms_dict: dict[str, forms.BaseForm] = {}
        for form_key, form_class in form_classes.items():
            if data_source == "POST":
                kwargs = {"data": self.request.POST, "files": self.request.FILES, "prefix": form_key}
                # Passar request quando suportado (identificação usa para filtrar clientes)
                try:
                    forms_dict[form_key] = form_class(**kwargs, request=self.request)
                except TypeError:
                    forms_dict[form_key] = form_class(**kwargs)
            else:
                saved = self.get_wizard_data().get(f"step_{current_step}", {})
                initial = saved.get(form_key, {})
                try:
                    forms_dict[form_key] = form_class(initial=initial, prefix=form_key, request=self.request)
                except TypeError:
                    forms_dict[form_key] = form_class(initial=initial, prefix=form_key)
        return forms_dict

    def _serialize_value(self, v: object) -> object:
        """Retorna representação serializável para sessão (JSON-like)."""
        # Arquivos já filtrados em `process_step_data`; manter por segurança
        if getattr(v, "read", None) is not None:
            return None
        # Instância de modelo: persiste PK
        if hasattr(v, "_meta") and hasattr(v, "pk"):
            return getattr(v, "pk", None)
        # Datas e decimais em formatos seguros
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        if isinstance(v, Decimal):
            return str(v)
        # Sequências
        if isinstance(v, (list, tuple)):
            return [self._serialize_value(i) for i in v]
        return v

    def process_step_data(self, forms: dict[str, Any], current_step: int) -> dict[str, Any]:
        """Extrai cleaned_data serializável dos formulários válidos do passo.

        Assinatura compatível com TenantCreationWizardView.
        """
        # Usado apenas para compatibilidade de assinatura com a superclasse
        _ = current_step
        step_data: dict[str, dict[str, object]] = {}
        for key, form in forms.items():
            if form.is_valid():
                cleaned: dict[str, object] = {}
                for k, v in form.cleaned_data.items():
                    if getattr(v, "read", None) is not None:
                        continue  # ignora arquivos na sessão
                    cleaned[k] = self._serialize_value(v)
                step_data[key] = cleaned
        # current_step é recebido para compatibilidade com a superclasse; não é usado aqui
        return step_data

    def _build_wizard_data(self, raw_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Normaliza o dicionário de dados da sessão em {'step_x': {'main': {...}}}."""
        wizard_data: dict[str, dict[str, Any]] = {}
        for step_key, step_val in raw_data.items():
            if isinstance(step_val, dict) and any(k in step_val for k in ("main", "pj", "pf")):
                wizard_data[step_key] = step_val
            else:
                wizard_data[step_key] = {"main": step_val if isinstance(step_val, dict) else {}}
        return wizard_data

    def _compute_preview(
        self,
        wizard_data: dict[str, dict[str, Any]],
        editing: Obra | None,
    ) -> tuple[str, str, str | None, str | None]:
        """Calcula informações de preview (nome, tipo, cliente, endereço)."""
        step1 = wizard_data.get("step_1", {}).get("main", {})
        step2 = wizard_data.get("step_2", {}).get("main", {})
        nome = step1.get("nome") or (getattr(editing, "nome", None)) or "Nova Obra"
        tipo_code = step1.get("tipo_obra") or (getattr(editing, "tipo_obra", None))
        tipo_map = dict(Obra.TIPO_OBRA_CHOICES)
        tipo_txt = tipo_map.get(tipo_code, "Tipo não definido") if tipo_code else "Tipo não definido"
        cliente_id = step1.get("cliente") or (getattr(editing, "cliente_id", None))
        cliente_nome = (
            Cliente.objects.filter(pk=cliente_id).values_list("nome", flat=True).first() if cliente_id else None
        )
        endereco_preview = None
        if step2:
            logradouro = step2.get("logradouro") or ""
            numero = step2.get("numero") or ""
            comp = step2.get("complemento") or ""
            cidade = step2.get("cidade") or ""
            uf = step2.get("uf") or ""
            endereco_preview = logradouro
            if numero:
                endereco_preview = f"{endereco_preview}, {numero}" if endereco_preview else numero
            if comp:
                endereco_preview = f"{endereco_preview} - {comp}" if endereco_preview else comp
            loc = " / ".join([p for p in [cidade, uf] if p])
            if loc:
                endereco_preview = f"{endereco_preview} - {loc}" if endereco_preview else loc
        elif editing:
            endereco_preview = getattr(editing, "endereco", None)
            loc = " / ".join([p for p in [getattr(editing, "cidade", ""), getattr(editing, "estado", "")] if p])
            if loc:
                endereco_preview = f"{endereco_preview} - {loc}" if endereco_preview else loc
        return nome, tipo_txt, cliente_nome, endereco_preview

    def get_context_data(self, **kwargs) -> dict[str, Any]:  # noqa: ANN003
        """Contexto específico para o wizard de Obras (títulos, navegação e preview)."""
        context: dict[str, Any] = {}
        current_step_obj = kwargs.get("current_step")
        current_step: int = current_step_obj if isinstance(current_step_obj, int) else self.get_current_step()
        editing_obj = kwargs.get("editing_tenant")
        editing: Obra | None = editing_obj if isinstance(editing_obj, Obra) else self.get_editing_tenant()
        step_cfg_obj = kwargs.get("step_config")
        if isinstance(step_cfg_obj, dict):
            step_config: dict[str, Any] = step_cfg_obj
        else:
            step_config = self.wizard_steps.get(current_step, {})

        # Forms
        forms_obj = kwargs.get("forms")
        if isinstance(forms_obj, dict):
            context["forms"] = forms_obj
            if len(forms_obj) == 1 and "main" in forms_obj:
                context["form"] = forms_obj["main"]

        # Dados da sessão normalizados e preview
        wizard_data = self._build_wizard_data(self.get_wizard_data() or {})
        nome, tipo_txt, cliente_nome, endereco_preview = self._compute_preview(wizard_data, editing)

        context.update(
            {
                # Títulos e navegação
                "wizard_title": f"Editar Obra - {editing.nome}" if editing else "Cadastro de Nova Obra",
                "current_step": current_step,
                "total_steps": len(self.wizard_steps),
                "step_config": step_config,
                "steps_list": self.wizard_steps,
                "progress_percentage": (float(current_step) / max(1, len(self.wizard_steps))) * 100,
                "can_go_prev": current_step > 1,
                "can_go_next": current_step < len(self.wizard_steps),
                "is_last_step": current_step == len(self.wizard_steps),
                "is_editing": editing is not None,
                "editing_tenant": editing,
                "step_title": (
                    step_config.get("name", f"Passo {current_step}") if step_config else f"Passo {current_step}"
                ),
                "step_icon": (step_config.get("icon", "fas fa-hard-hat") if step_config else "fas fa-hard-hat").replace(
                    "fas fa-",
                    "",
                ),
                # Rotas de navegação específicas do módulo Obras
                "wizard_goto_step_name": "obras:obra_wizard_goto_step",
                "wizard_goto_step_edit_name": "obras:obra_wizard_goto_step_edit",
                "wizard_list_url_name": "obras:obras_list",
                # Dados brutos do wizard
                "wizard_data": wizard_data,
                # Preview personalizado
                "preview_card_title": "Preview da Obra",
                "preview_name": nome,
                "preview_subtext": "Complete os dados da obra",
                "preview_type_text": tipo_txt,
                "preview_email": f"Cliente: {cliente_nome}" if cliente_nome else "Cliente não informado",
                "preview_location": endereco_preview or "Endereço não informado",
                "preview_primary_badge": "Obra",
                "preview_secondary_badge": "Edição" if editing else "Cadastro",
            },
        )

        return context

    # GET/POST (igual aos demais wizards)
    def get(
        self,
        request: HttpRequest,
        *_args: tuple[object, ...],
        **_kwargs: dict[str, object],
    ) -> HttpResponse:
        """Renderizar o passo atual do wizard (GET)."""
        # Bloqueia acesso quando módulo 'obras' não está habilitado no tenant, com mensagem amigável
        tenant = get_current_tenant(request)
        if tenant and not tenant.has_module("obras"):
            context = {
                "title": "Módulo não contratado",
                "headline": "Você não tem acesso a este módulo",
                "message": "Para contratar o módulo Obras, entre em contato com o administrador do sistema.",
                "icon": "fa-hard-hat",
                "back_url": reverse("dashboard"),
            }
            return render(request, "core/module_unavailable.html", context, status=403)
        current_step = self.get_current_step()
        editing = self.get_editing_tenant()
        if current_step not in self.wizard_steps:
            messages.error(request, _("Step inválido."))
            return redirect(self.success_url)
        step_config = self.wizard_steps[current_step]
        forms = self.create_forms_for_step(current_step, editing, data_source="GET")
        ctx = self.get_context_data(
            forms=forms,
            current_step=current_step,
            step_config=step_config,
            editing_tenant=editing,
        )
        return render(request, step_config["template"], ctx)

    def post(
        self,
        request: HttpRequest,
        *_args: tuple[object, ...],
        **_kwargs: dict[str, object],
    ) -> HttpResponse:
        """Processar submissão do passo atual do wizard (POST)."""
        tenant = get_current_tenant(request)
        if tenant and not tenant.has_module("obras"):
            context = {
                "title": "Módulo não contratado",
                "headline": "Você não tem acesso a este módulo",
                "message": "Para contratar o módulo Obras, entre em contato com o administrador do sistema.",
                "icon": "fa-hard-hat",
                "back_url": reverse("dashboard"),
            }
            return render(request, "core/module_unavailable.html", context, status=403)
        current_step = self.get_current_step()
        editing = self.get_editing_tenant()
        if current_step not in self.wizard_steps:
            messages.error(request, _("Step inválido."))
            return redirect(self.success_url)
        step_config = self.wizard_steps[current_step]

        # Navegação para passo anterior (unifica retornos)
        if "wizard_prev" in request.POST:
            if current_step > 1:
                self.set_current_step(current_step - 1)
            return redirect("obras:obra_wizard_edit", pk=editing.pk) if editing else redirect("obras:obra_wizard")

        forms = self.create_forms_for_step(current_step, editing, data_source="POST")
        is_finish = "wizard_finish" in request.POST or current_step == len(self.wizard_steps)

        if is_finish:
            all_valid = all(f.is_valid() for f in forms.values())
            if all_valid:
                self.set_wizard_data(current_step, self.process_step_data(forms, current_step))
                return self.finish_wizard()
            ctx = self.get_context_data(
                forms=forms,
                current_step=current_step,
                step_config=step_config,
                editing_tenant=editing,
            )
            ctx["wizard"] = self
            return render(request, step_config["template"], ctx)
        valid_step_data = self.process_step_data(forms, current_step)
        self.set_wizard_data(current_step, valid_step_data)
        if current_step < len(self.wizard_steps):
            self.set_current_step(current_step + 1)
        return redirect(request.path)

    def _apply_step1(self, obra: Obra, step1: dict[str, Any]) -> None:
        """Aplicar campos do passo 1 na instância de Obra."""
        for field in ("nome", "tipo_obra", "cno", "data_inicio", "data_previsao_termino", "valor_contrato"):
            if field in step1:
                setattr(obra, field, step1.get(field))
        if "cliente" in step1 and step1.get("cliente"):
            try:
                obra.cliente = Cliente.objects.get(pk=step1.get("cliente"))
            except Cliente.DoesNotExist:
                obra.cliente = None

    def _apply_step2(self, obra: Obra, step2: dict[str, Any]) -> None:
        """Aplicar endereço e localização do passo 2."""
        obra.cep = step2.get("cep") or ""
        obra.endereco = step2.get("logradouro") or ""
        numero = step2.get("numero") or ""
        comp = step2.get("complemento") or ""
        if numero or comp:
            obra.endereco = f"{obra.endereco}, {numero}{(' - ' + comp) if comp else ''}"
        obra.cidade = step2.get("cidade") or ""
        obra.estado = step2.get("uf") or ""

    def _apply_step5(self, obra: Obra, step5: dict[str, Any]) -> None:
        """Aplicar configurações finais do passo 5."""
        obra.observacoes = step5.get("observacoes") or ""
        if "status" in step5:
            obra.status = step5.get("status")
        if "progresso" in step5:
            obra.progresso = step5.get("progresso") or 0
        if "valor_total" in step5:
            obra.valor_total = step5.get("valor_total") or obra.valor_contrato
        if "data_termino" in step5:
            obra.data_termino = step5.get("data_termino") or None

    def _append_contact_summary(self, obra: Obra, step3: dict[str, Any]) -> None:
        """Incluir um resumo de contato nas observações da obra (se houver dados)."""
        parts: list[str] = []
        if any(step3.get(k) for k in ("responsavel_nome", "responsavel_email", "responsavel_telefone")):
            parts.append("Contato: ")
            nome = step3.get("responsavel_nome")
            if isinstance(nome, str) and nome:
                parts.append(nome)
            cargo = step3.get("responsavel_cargo")
            if isinstance(cargo, str) and cargo:
                parts.append(f"({cargo})")
            email = step3.get("responsavel_email")
            if isinstance(email, str) and email:
                parts.append(f" - {email}")
            tel = step3.get("responsavel_telefone")
            if isinstance(tel, str) and tel:
                parts.append(f" - {tel}")
        extra = " ".join(parts).strip()
        if extra:
            obra.observacoes = (obra.observacoes or "") + "\n" + extra

    def finish_wizard(self) -> HttpResponse:
        """Consolida dados da sessão em uma instância de Obra e salva."""
        data = self.get_wizard_data() or {}
        step1 = data.get("step_1", {}).get("main", {})
        step2 = data.get("step_2", {}).get("main", {})
        step3 = data.get("step_3", {}).get("main", {})
        step5 = data.get("step_5", {}).get("main", {})

        try:
            with transaction.atomic():
                editing = self.get_editing_tenant()
                obra = editing or Obra()

                self._apply_step1(obra, step1)
                self._apply_step2(obra, step2)
                self._apply_step5(obra, step5)
                self._append_contact_summary(obra, step3)

                obra.save()

                # Consolidar documentos temporários do wizard para a obra
                tenant = get_current_tenant(self.request)
                if tenant:
                    try:
                        consolidate_wizard_temp_to_documents(
                            tenant=tenant,
                            session_key=self.request.session.session_key,
                            user=cast("Any", self.request.user),
                        )
                        logger.info("Documentos do wizard consolidados para a obra %s", obra.pk)
                    except Exception:  # pragma: no cover
                        logger.exception("Falha ao consolidar documentos do wizard para a obra %s", obra.pk)

                # Limpar sessão e redirecionar
                self.clear_wizard_data()
                messages.success(self.request, _("Obra salva com sucesso."))
                return redirect(reverse("obras:obra_detail", kwargs={"pk": obra.pk}))
        except (DatabaseError, IntegrityError, ValueError) as e:
            logger.exception("Erro ao salvar obra via wizard")
            messages.error(self.request, _("Erro ao salvar obra: ") + str(e))
            return redirect(self.success_url)


# Rotas utilitárias (goto step)


def obra_wizard_create(request: HttpRequest) -> HttpResponse:
    """Criar uma nova instância do wizard de Obras (entrada padrão)."""
    return ObraWizardView.as_view()(request)


def obra_wizard_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Abrir o wizard de Obras no modo de edição para a Obra informada."""
    return ObraWizardView.as_view()(request, pk=pk)


def obra_wizard_goto_step(request: HttpRequest, step: int, pk: int | None = None) -> HttpResponse:
    """Alterar o passo corrente do wizard e redirecionar para a rota apropriada."""
    try:
        step = int(step)
    except (TypeError, ValueError):
        messages.error(request, _("Step inválido."))
        return redirect("obras:obras_list")
    if step in OBRA_WIZARD_STEPS:
        request.session["obra_wizard_step"] = step
        request.session.modified = True
        if pk:
            return redirect("obras:obra_wizard_edit", pk=pk)
        return redirect("obras:obra_wizard")
    messages.error(request, _("Step inválido."))
    return redirect("obras:obras_list")
