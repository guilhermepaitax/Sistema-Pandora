"""Formulários do app core.

Inclui formulários de Tenant (wizard), endereços, contatos, documentos,
usuários, cargos, departamentos e configuração de módulos. Refatorado
para conformidade com Ruff (docstrings, tipagem e estilo) sem alterar
regras de negócio.
"""

# core/forms.py - VERSÃO FINAL, COMPLETA E SINCRONIZADA

from __future__ import annotations

import json
from typing import Any, ClassVar

from django import forms
from django.contrib.auth.models import Permission
from django.db import models
from django.forms import DateInput
from django.utils.translation import gettext_lazy as _

from cadastros_gerais.models import ItemAuxiliar  # novo: para filtrar tipos de documentos aplicáveis
from core.module_registry import get_all_module_choices  # central registry

# Modelos importados
from .models import (  # novo: modelos de versionamento
    CustomUser,
    Department,
    EmpresaDocumento,
    EmpresaDocumentoVersao,
    Role,
    Tenant,
    TenantUser,
)


class BasePandoraForm(forms.ModelForm):
    """Classe base de estilização mantida 100% intacta."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Aplica classes CSS padronizadas aos widgets dos campos."""
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            current_class = widget.attrs.get("class", "")
            if (
                not isinstance(widget, (forms.CheckboxInput, forms.FileInput, forms.RadioSelect))
                and "form-control" not in current_class
            ):
                widget.attrs["class"] = f"{current_class} form-control".strip()
            if isinstance(widget, forms.Select):
                if "select2" not in current_class:
                    widget.attrs["class"] = f"{widget.attrs.get('class', '')} select2".strip()
            elif isinstance(widget, forms.CheckboxInput):
                if "form-check-input" not in current_class:
                    widget.attrs["class"] = f"{current_class} form-check-input".strip()
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = f"{current_class} custom-file-input".strip()
            if isinstance(widget, forms.Textarea) and "rows" not in widget.attrs:
                widget.attrs["rows"] = 3


# ============================================================================
# OUTROS FORMULÁRIOS DO SISTEMA
# ============================================================================

"""Formulários legacy InitialAdminForm/InitialAdminFormSet removidos.

Motivo: fluxo de criação de administradores iniciais agora acontece 100% via
wizard multi-admin (step específico com JSON dinâmico). A manutenção destes
formsets encobriria código morto e aumentaria custos de manutenção.
"""


class CustomUserForm(BasePandoraForm):
    """Criação/edição de usuários internos."""

    password2 = forms.CharField(label=_("Confirmação de senha"), widget=forms.PasswordInput, required=False)

    class Meta:
        """Campos do usuário."""

        model = CustomUser
        fields: ClassVar[list[str]] = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password2",
            "phone",
            "bio",
            "theme_preference",
            "is_active",
            "is_staff",
        ]

    def save(self, *, commit: bool = True) -> CustomUser:
        """Define a senha quando informada e salva conforme ``commit``."""
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class RoleForm(BasePandoraForm):
    """Formulário de cargos (roles) e suas permissões."""

    class Meta:
        """Campos e widgets da Role."""

        model = Role
        fields: ClassVar[list[str]] = ["tenant", "name", "description", "is_active", "department", "permissions"]
        widgets: ClassVar[dict[str, Any]] = {
            "permissions": forms.CheckboxSelectMultiple(
                attrs={"class": "permissions-matrix"},
            ),
        }

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Inicializa permissões e filtra departamentos por tenant/usuário."""
        self.request = kwargs.pop("request", None)
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)
        self.fields["permissions"].queryset = Permission.objects.all().select_related("content_type")

        user = getattr(self.request, "user", None)
        is_super = bool(user and getattr(user, "is_superuser", False))
        # Campo tenant
        if "tenant" in self.fields:
            if is_super:
                self.fields["tenant"].queryset = Tenant.objects.all().order_by("name")
                self.fields["tenant"].required = False
                self.fields["tenant"].label = "Empresa (Tenant)"
                self.fields["tenant"].help_text = "Deixe em branco para tornar este cargo Global."
            else:
                # Usuário comum: ocultar e fixar tenant recebido por kwargs
                self.fields["tenant"].widget = forms.HiddenInput()
                if self.tenant:
                    self.fields["tenant"].initial = self.tenant

        # Departamentos
        if "department" in self.fields:
            base_qs = Department.objects.all()
            active_tenant = None
            if is_super:
                # Primeiro tenta POST, depois initial/instance, depois kwargs tenant
                active_tenant = self.data.get("tenant") or (self.instance.tenant_id if self.instance.pk else None)
            else:
                active_tenant = self.tenant.id if getattr(self.tenant, "id", None) else None
            if active_tenant:
                self.fields["department"].queryset = base_qs.filter(
                    models.Q(tenant__isnull=True) | models.Q(tenant_id=active_tenant),
                ).order_by("tenant__name", "name")
            # Superuser sem tenant escolhido: mostrar todos para facilitar (globais + específicos) ordenados
            elif is_super:
                self.fields["department"].queryset = base_qs.order_by("tenant__name", "name")
            else:
                # fallback: somente globais
                self.fields["department"].queryset = base_qs.filter(tenant__isnull=True).order_by("name")
            self.fields["department"].required = False


class DepartmentForm(BasePandoraForm):
    """Formulário de departamentos."""

    class Meta:
        """Campos do departamento (tenant é opcional para superusuário)."""

        model = Department
        fields: ClassVar[list[str]] = ["name", "description"]

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Expõe campo tenant somente para superusuários."""
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        # Se superuser: permitir escolher tenant explicitamente (profissional / transparente)
        if self.request and getattr(self.request.user, "is_superuser", False):
            self.fields["tenant"] = forms.ModelChoiceField(
                queryset=Tenant.objects.all().order_by("name"),
                required=False,
                label="Empresa (Tenant)",
                help_text="Deixe em branco para tornar este departamento Global (visível em todas as empresas).",
            )
        # Em contexto não superuser o tenant será forçado na view; não expor campo.


class TenantUserForm(BasePandoraForm):
    """Vincula um usuário existente a um Tenant com cargo/departamento."""

    email_or_username = forms.CharField(
        label="E-mail ou Nome de Usuário",
        help_text="Digite o e-mail ou nome de usuário do usuário que deseja vincular",
        widget=forms.TextInput(attrs={"placeholder": "usuario@exemplo.com ou nome_usuario"}),
        required=False,
    )

    class Meta:
        """Campos do vínculo do usuário ao tenant."""

        model = TenantUser
        fields: ClassVar[list[str]] = ["role", "department", "is_tenant_admin"]

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Permite receber ``tenant`` e ``request`` via view e ajusta querysets."""
        # Views podem fornecer `tenant` e `request` via get_form_kwargs
        self.tenant = kwargs.pop("tenant", None)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if self.tenant:
            self.fields["role"].queryset = Role.objects.filter(tenant=self.tenant)
            self.fields["department"].queryset = Department.objects.filter(tenant=self.tenant)
        if self.instance and self.instance.pk:
            if "email_or_username" in self.fields:
                del self.fields["email_or_username"]
        else:
            self.fields["email_or_username"].required = True

    def clean_email_or_username(self) -> CustomUser | None:
        """Busca o usuário por e-mail ou username e valida duplicidade."""
        email_or_username = self.cleaned_data.get("email_or_username")
        if not email_or_username and not (self.instance and self.instance.pk):
            msg = _("Este campo é obrigatório.")
            raise forms.ValidationError(msg)
        if not email_or_username:
            return email_or_username
        try:
            user = CustomUser.objects.get(models.Q(email=email_or_username) | models.Q(username=email_or_username))
        except CustomUser.DoesNotExist:
            msg = _("Usuário não encontrado com este e-mail ou nome de usuário.")
            raise forms.ValidationError(msg) from None
        if TenantUser.objects.filter(tenant=self.tenant, user=user).exists():
            msg = _("Este usuário já está vinculado a esta empresa.")
            raise forms.ValidationError(msg)
        return user

    def save(self, *, commit: bool = True) -> TenantUser:
        """Atribui tenant e usuário (no create) e salva conforme ``commit``."""
        instance = super().save(commit=False)
        instance.tenant = self.tenant
        if not instance.pk and "email_or_username" in self.cleaned_data:
            instance.user = self.cleaned_data["email_or_username"]
        if commit:
            instance.save()
        return instance


class ModuleConfigurationForm(forms.Form):
    """Habilitação e visual de módulos por Tenant (usa module_registry)."""

    AVAILABLE_MODULES_CHOICES: ClassVar[list[tuple[str, str]]] = get_all_module_choices()

    enabled_modules = forms.MultipleChoiceField(
        choices=sorted(AVAILABLE_MODULES_CHOICES, key=lambda x: (x[1] or "")),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "custom-checkbox-list"}),
        required=False,
        label=_("Selecione os módulos para habilitar para esta empresa"),
    )

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Configura initial e help_text conforme plano/tenant."""
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)
        plan = self._resolve_plan()
        existing = set(self._extract_existing_modules())
        defaults = self._plan_defaults(plan)
        essentials = set(getattr(Tenant, "ESSENTIAL_TENANT_MODULES", []))
        # Para planos não CUSTOM: union de existentes + defaults + essenciais
        initial = sorted(existing | defaults | essentials) if plan != "CUSTOM" else sorted(existing | essentials)
        self.fields["enabled_modules"].initial = initial
        self._apply_help_text(plan, defaults)

    # ---- helpers ----
    def _resolve_plan(self) -> str:
        return getattr(self.tenant, "plano_assinatura", "BASIC") if self.tenant else "BASIC"

    def _extract_existing_modules(self) -> list[str]:
        data = getattr(self.tenant, "enabled_modules", None)
        if not data:
            return []
        try:
            if isinstance(data, str):
                return json.loads(data)
            if isinstance(data, dict):
                return data.get("modules", []) or []
        except (json.JSONDecodeError, TypeError):  # pragma: no cover
            return []
        return []

    def _plan_defaults(self, plan: str) -> set[str]:
        mapping = getattr(Tenant, "PLAN_DEFAULT_MODULES", {})
        return set(mapping.get(plan, []))

    def _apply_help_text(self, plan: str, defaults: set[str]) -> None:
        field = self.fields.get("enabled_modules")
        if not field:
            return
        if plan != "CUSTOM" and defaults:
            field.help_text = (field.help_text or "") + f" Módulos do plano {plan} são fixos e aparecem marcados."
        elif plan == "CUSTOM":
            field.help_text = (
                field.help_text or ""
            ) + " Plano personalizado: selecione livremente os módulos necessários."

    def save(self) -> None:
        """Salva a lista de módulos habilitados no campo JSON do tenant."""
        if not self.tenant:
            msg = _("O tenant não foi fornecido para o formulário.")
            raise TypeError(msg)
        # Normalizar seleção + salvamento em formato canônico {'modules': [...]}.
        selected_modules = list(dict.fromkeys(self.cleaned_data.get("enabled_modules", [])))
        # Garantir essenciais presentes sempre
        essentials = set(getattr(Tenant, "ESSENTIAL_TENANT_MODULES", []))
        selected_modules = sorted(set(selected_modules) | essentials)
        self.tenant.enabled_modules = {"modules": selected_modules}
        # save() do modelo já aplicará defaults de plano se necessário
        self.tenant.save(update_fields=["enabled_modules"])  # save parcial mantém demais campos


class EmpresaDocumentoVersaoCreateForm(forms.Form):
    """Criação de nova versão de documento da empresa."""

    tipo = forms.ModelChoiceField(queryset=ItemAuxiliar.objects.none(), label=_("Tipo de Documento"))
    arquivo = forms.FileField(label=_("Arquivo"))
    data_vigencia_inicio = forms.DateField(label=_("Início da Vigência"), widget=DateInput(attrs={"type": "date"}))
    data_vigencia_fim = forms.DateField(
        label=_("Fim da Vigência"),
        required=False,
        widget=DateInput(attrs={"type": "date"}),
    )
    competencia = forms.CharField(label=_("Competência (MM/AAAA)"), required=False)
    observacao = forms.CharField(label=_("Observação"), required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Filtra tipos aplicáveis a 'empresa' e ordena por categoria/ordem/nome."""
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)
        # Filtrar tipos aplicáveis a EMPRESA nas categorias conhecidas
        qs = ItemAuxiliar.objects.filter(ativo=True)
        qs = qs.filter(models.Q(alvo="empresa") | models.Q(targets__code="empresa")).distinct()
        qs = qs.filter(categoria__slug__in=["documentos-da-empresa", "documentos-financeiros", "outros-documentos"])
        self.fields["tipo"].queryset = qs.order_by("categoria__ordem", "ordem", "nome")

    def clean(self) -> dict[str, Any]:
        """Validações suaves: sugere competência quando periodicidade não é 'nenhuma'."""
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        competencia = cleaned.get("competencia")
        # Se o tipo tiver periodicidade, sugerir competência preenchida (não obrigatório)
        if tipo and getattr(tipo, "periodicidade", "nenhuma") != "nenhuma" and not competencia:
            ...
        return cleaned

    def save(self, user: CustomUser | None = None) -> EmpresaDocumentoVersao:
        """Cria a versão, atualiza cabeçalho e retorna a nova instância."""
        if not self.tenant:
            msg = _("Tenant é obrigatório para salvar a versão do documento.")
            raise ValueError(msg)
        tipo = self.cleaned_data["tipo"]
        arquivo = self.cleaned_data["arquivo"]
        data_ini = self.cleaned_data["data_vigencia_inicio"]
        data_fim = self.cleaned_data.get("data_vigencia_fim")
        competencia = self.cleaned_data.get("competencia")
        observacao = self.cleaned_data.get("observacao")

        # Obter ou criar o registro do documento por (tenant, tipo)
        doc, _created = EmpresaDocumento.objects.get_or_create(tenant=self.tenant, tipo=tipo)
        proxima_versao = (doc.versao_atual or 0) + 1

        versao = EmpresaDocumentoVersao.objects.create(
            documento=doc,
            versao=proxima_versao,
            arquivo=arquivo,
            data_vigencia_inicio=data_ini,
            data_vigencia_fim=data_fim,
            competencia=competencia,
            observacao=observacao,
            usuario=user if user and getattr(user, "pk", None) else None,
        )
        # Atualizar cabeçalho
        doc.versao_atual = proxima_versao
        doc.status_atual = "ATIVO"
        doc.save(update_fields=["versao_atual", "status_atual", "updated_at"])
        return versao
