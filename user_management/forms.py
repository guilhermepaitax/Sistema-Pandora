"""Formulários para o módulo de gerenciamento de usuários."""

import logging
from datetime import timedelta
from typing import Any, ClassVar

from django import forms
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import ConviteUsuario, PerfilUsuarioEstendido, PermissaoPersonalizada, StatusUsuario, TipoUsuario

logger = logging.getLogger(__name__)

# O aplicativo de funcionários é opcional.
FuncionarioModel: type[Any] | None = None
try:
    from funcionarios.models import Funcionario

    FuncionarioModel = Funcionario
except ImportError:
    pass  # Mantém FuncionarioModel como None se o app não existir

User = get_user_model()


class UsuarioCreateForm(UserCreationForm):
    """Formulário para criação de usuários com perfil estendido."""

    first_name: ClassVar[forms.CharField] = forms.CharField(max_length=30, required=True, label="Nome")
    last_name: ClassVar[forms.CharField] = forms.CharField(max_length=30, required=True, label="Sobrenome")
    email: ClassVar[forms.EmailField] = forms.EmailField(required=True, label="E-mail")
    avatar: ClassVar[forms.ImageField] = forms.ImageField(
        required=False,
        label="Foto do Perfil",
        help_text="Imagem para o avatar do usuário (PNG, JPG, máx. 5MB)",
    )
    tipo_usuario: ClassVar[forms.ChoiceField] = forms.ChoiceField(
        choices=TipoUsuario.choices,
        required=True,
        label="Tipo de Usuário",
    )
    cpf: ClassVar[forms.CharField] = forms.CharField(
        max_length=14,
        required=False,
        label="CPF",
        widget=forms.TextInput(attrs={"placeholder": "000.000.000-00"}),
    )
    telefone: ClassVar[forms.CharField] = forms.CharField(max_length=20, required=False, label="Telefone")
    celular: ClassVar[forms.CharField] = forms.CharField(max_length=20, required=False, label="Celular")
    cargo: ClassVar[forms.CharField] = forms.CharField(max_length=100, required=False, label="Cargo")
    departamento: ClassVar[forms.CharField] = forms.CharField(max_length=100, required=False, label="Departamento")
    is_active: ClassVar[forms.BooleanField] = forms.BooleanField(required=False, label="Usuário Ativo", initial=True)
    is_staff: ClassVar[forms.BooleanField] = forms.BooleanField(required=False, label="Acesso Staff", initial=False)
    is_superuser: ClassVar[forms.BooleanField] = forms.BooleanField(required=False, label="Superusuário", initial=False)
    # Grupos (opcional, só exposto para superusuário na UI)
    groups: ClassVar[forms.ModelMultipleChoiceField] = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Grupos",
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
    )

    class Meta:
        """Meta opções para o formulário de criação de usuário."""

        model = User
        fields: ClassVar[tuple[str, ...]] = ("username", "first_name", "last_name", "email")

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Inicializa o formulário e injeta o usuário da requisição e o tenant."""
        self.request_user = kwargs.pop("request_user", None)
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)

        if self.request_user and not self.request_user.is_superuser:
            self.fields["tipo_usuario"].choices = [
                (k, v) for k, v in TipoUsuario.choices if k not in [TipoUsuario.SUPER_ADMIN, TipoUsuario.ADMIN_EMPRESA]
            ]

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        for fname in ("is_active", "is_staff", "is_superuser"):
            if fname in self.fields and getattr(self.fields[fname].widget, "input_type", "") == "checkbox":
                self.fields[fname].widget.attrs["class"] = "form-check-input"

        if not (self.request_user and self.request_user.is_superuser):
            for fname in ("is_staff", "is_superuser"):
                if fname in self.fields:
                    self.fields[fname].disabled = True
            # Oculta o campo de grupos para não-superusuários por segurança (escopo global de grupos)
            self.fields.pop("groups", None)

    def clean_email(self) -> str:
        """Valida se o e-mail já está em uso."""
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            msg = "Este e-mail já está em uso."
            raise ValidationError(msg)
        return email

    def clean_cpf(self) -> str | None:
        """Valida se o CPF já está cadastrado."""
        cpf = self.cleaned_data.get("cpf")
        if cpf and PerfilUsuarioEstendido.objects.filter(cpf=cpf).exists():
            msg = "Este CPF já está cadastrado."
            raise ValidationError(msg)
        return cpf

    def save(self, *, commit: bool = True) -> AbstractUser:
        """Salva o usuário e seu perfil estendido."""
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.is_active = self.cleaned_data.get("is_active", True)

        if self.request_user and getattr(self.request_user, "is_superuser", False):
            user.is_staff = self.cleaned_data.get("is_staff", False)
            user.is_superuser = self.cleaned_data.get("is_superuser", False)

        if commit:
            user.save()
            # Atribuir grupos se fornecido e se o campo estiver presente
            if "groups" in self.cleaned_data:
                try:
                    user.groups.set(self.cleaned_data.get("groups") or [])
                except Exception:
                    logger.exception("Falha ao atribuir grupos ao usuário %s", user.username)
            perfil, created = PerfilUsuarioEstendido.objects.get_or_create(
                user=user,
                defaults={
                    "tipo_usuario": self.cleaned_data["tipo_usuario"],
                    "cpf": self.cleaned_data.get("cpf"),
                    "telefone": self.cleaned_data.get("telefone"),
                    "celular": self.cleaned_data.get("celular"),
                    "cargo": self.cleaned_data.get("cargo"),
                    "departamento": self.cleaned_data.get("departamento"),
                    "status": StatusUsuario.ATIVO,
                    "criado_por": self.request_user,
                },
            )
            if not created:
                self._atualizar_perfil_existente(perfil)

            if self.tenant:
                self._associar_tenant_user(user)

        return user

    def _atualizar_perfil_existente(self, perfil: PerfilUsuarioEstendido) -> None:
        """Atualiza os campos de um perfil de usuário existente."""
        campos_update = ["tipo_usuario", "cpf", "telefone", "celular", "cargo", "departamento"]
        alterado = False
        for campo in campos_update:
            novo_valor = self.cleaned_data.get(campo)
            if novo_valor and getattr(perfil, campo) != novo_valor:
                setattr(perfil, campo, novo_valor)
                alterado = True
        if perfil.status != StatusUsuario.ATIVO:
            perfil.status = StatusUsuario.ATIVO
            alterado = True
        if alterado:
            perfil.save()

    def _associar_tenant_user(self, user: AbstractUser) -> None:
        """Associa um usuário a um tenant."""
        try:
            tenant_user_model = apps.get_model("core", "TenantUser")
            tenant_user_model.objects.get_or_create(tenant=self.tenant, user=user)
        except Exception:
            logger.exception("Falha ao associar TenantUser para o usuário %s", user.username)


class UsuarioUpdateForm(forms.ModelForm):
    """Formulário para atualização de usuários."""

    first_name: ClassVar[forms.CharField] = forms.CharField(max_length=30, required=True, label="Nome")
    last_name: ClassVar[forms.CharField] = forms.CharField(max_length=30, required=True, label="Sobrenome")
    email: ClassVar[forms.EmailField] = forms.EmailField(required=True, label="E-mail")
    is_active: ClassVar[forms.BooleanField] = forms.BooleanField(required=False, label="Usuário Ativo")
    is_staff: ClassVar[forms.BooleanField] = forms.BooleanField(required=False, label="Acesso Staff")
    is_superuser: ClassVar[forms.BooleanField] = forms.BooleanField(required=False, label="Superusuário")

    class Meta:
        """Meta opções para o formulário de atualização de usuário."""

        model = PerfilUsuarioEstendido
        fields: ClassVar[list[str]] = [
            "avatar",
            "tipo_usuario",
            "status",
            "cpf",
            "rg",
            "data_nascimento",
            "telefone",
            "celular",
            "endereco",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "cep",
            "cargo",
            "departamento",
            "data_admissao",
            "salario",
            "autenticacao_dois_fatores",
            "receber_email_notificacoes",
            "receber_sms_notificacoes",
            "receber_push_notificacoes",
        ]
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
            "data_admissao": forms.DateInput(attrs={"type": "date"}),
            "salario": forms.NumberInput(attrs={"step": "0.01"}),
            "avatar": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Inicializa o formulário de atualização com dados do usuário/perfil."""
        self.request_user = kwargs.pop("request_user", None)
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)

        self._preencher_campos_iniciais()
        self._restringir_opcoes_tipo_usuario()
        self._aplicar_estilos_css()
        self._desabilitar_campos_privilegiados()
        self._desabilitar_campos_funcionario()

    def _preencher_campos_iniciais(self) -> None:
        """Preenche os campos do formulário com os dados iniciais do usuário."""
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email
            self.fields["is_active"].initial = self.instance.user.is_active
            self.fields["is_staff"].initial = self.instance.user.is_staff
            self.fields["is_superuser"].initial = self.instance.user.is_superuser

    def _restringir_opcoes_tipo_usuario(self) -> None:
        """Restringe as opções de tipo de usuário para não superusuários."""
        if self.request_user and not self.request_user.is_superuser:
            self.fields["tipo_usuario"].choices = [
                (k, v) for k, v in TipoUsuario.choices if k not in [TipoUsuario.SUPER_ADMIN, TipoUsuario.ADMIN_EMPRESA]
            ]
            if self.instance.tipo_usuario in [TipoUsuario.SUPER_ADMIN, TipoUsuario.ADMIN_EMPRESA]:
                self.fields["tipo_usuario"].disabled = True

    def _aplicar_estilos_css(self) -> None:
        """Aplica classes CSS aos campos do formulário."""
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"

    def _desabilitar_campos_privilegiados(self) -> None:
        """Desabilita campos que só podem ser editados por superusuários."""
        if not (self.request_user and self.request_user.is_superuser):
            for fname in ["is_staff", "is_superuser"]:
                if fname in self.fields:
                    self.fields[fname].disabled = True

    def _desabilitar_campos_funcionario(self) -> None:
        """Desabilita campos relacionados a funcionário se houver vínculo."""
        if FuncionarioModel and self.instance and getattr(self.instance, "user", None):
            try:
                if FuncionarioModel.objects.filter(user=self.instance.user).exists():
                    for fname in ["cargo", "salario"]:
                        if fname in self.fields:
                            self.fields[fname].disabled = True
            except FuncionarioModel.DoesNotExist:
                pass
            except Exception:
                logger.exception("Falha ao verificar vínculo com Funcionário.")

    def clean_email(self) -> str:
        """Valida se o e-mail já está em uso por outro usuário."""
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exclude(pk=self.instance.user.pk).exists():
            msg = "Este e-mail já está em uso."
            raise ValidationError(msg)
        return email

    def clean_cpf(self) -> str | None:
        """Valida se o CPF já está cadastrado para outro usuário."""
        cpf = self.cleaned_data.get("cpf")
        if cpf and PerfilUsuarioEstendido.objects.filter(cpf=cpf).exclude(pk=self.instance.pk).exists():
            msg = "Este CPF já está cadastrado."
            raise ValidationError(msg)
        return cpf

    def save(self, *, commit: bool = True) -> PerfilUsuarioEstendido:
        """Salva o perfil e os dados do usuário associado."""
        perfil = super().save(commit=False)
        user = perfil.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.is_active = self.cleaned_data["is_active"]

        if self.request_user and self.request_user.is_superuser:
            user.is_staff = self.cleaned_data.get("is_staff", user.is_staff)
            user.is_superuser = self.cleaned_data.get("is_superuser", user.is_superuser)

        if commit:
            user.save()
            perfil.save()

        return perfil


class ConviteUsuarioForm(forms.ModelForm):
    """Formulário para envio de convites de usuário."""

    class Meta:
        """Meta opções para o formulário de convite."""

        model = ConviteUsuario
        fields: ClassVar[list[str]] = [
            "email",
            "tipo_usuario",
            "nome_completo",
            "cargo",
            "departamento",
            "mensagem_personalizada",
        ]
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "mensagem_personalizada": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Inicializa o formulário de convite com tenant e usuário da requisição."""
        self.tenant = kwargs.pop("tenant", None)
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean_email(self) -> str:
        """Valida o e-mail do convite."""
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            msg = "Já existe um usuário cadastrado com este e-mail."
            raise ValidationError(msg)
        if ConviteUsuario.objects.filter(email=email, usado=False, tenant=self.tenant).exists():
            msg = "Já existe um convite pendente para este e-mail neste tenant."
            raise ValidationError(msg)
        return email

    def save(self, *, commit: bool = True) -> ConviteUsuario:
        """Salva o convite de usuário."""
        convite = super().save(commit=False)
        convite.expirado_em = timezone.now() + timedelta(days=7)
        convite.enviado_por = self.request_user
        convite.tenant = self.tenant

        if commit:
            convite.save()

        return convite


class PermissaoPersonalizadaForm(forms.ModelForm):
    """Formulário para gerenciar permissões personalizadas."""

    class Meta:
        """Meta opções para o formulário de permissão."""

        model = PermissaoPersonalizada
        fields: ClassVar[list[str]] = [
            "user",
            "scope_tenant",
            "modulo",
            "acao",
            "recurso",
            "concedida",
            "data_expiracao",
            "observacoes",
        ]
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "data_expiracao": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Inicializa o formulário de permissão com escopo de tenant."""
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)

        if "scope_tenant" in self.fields:
            tenant_model = apps.get_model("core", "Tenant")
            if self.tenant:
                self.fields["scope_tenant"].queryset = tenant_model.objects.filter(pk=self.tenant.pk)
                self.fields["scope_tenant"].initial = self.tenant
            else:
                self.fields["scope_tenant"].queryset = tenant_model.objects.all()
                self.fields["scope_tenant"].required = False

        if self.tenant:
            self.fields["user"].queryset = self.tenant.user_set.all()
        else:
            self.fields["user"].queryset = User.objects.all()

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs["class"] = "form-control"
            else:
                field.widget.attrs["class"] = "form-control"

    def clean(self) -> dict[str, Any]:
        """Valida os dados do formulário para evitar permissões duplicadas."""
        data = super().clean()
        user = data.get("user")
        modulo = data.get("modulo")
        acao = data.get("acao")
        recurso = data.get("recurso") or None
        scope_tenant = data.get("scope_tenant") or None

        if user and modulo and acao:
            qs = PermissaoPersonalizada.objects.filter(
                user=user,
                modulo=modulo,
                acao=acao,
                recurso=recurso,
                scope_tenant=scope_tenant,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                msg = "Já existe uma permissão com estes parâmetros (mesmo escopo)."
                raise ValidationError(msg)
        return data


class FiltroUsuarioForm(forms.Form):
    """Formulário para filtrar a lista de usuários."""

    busca: ClassVar[forms.CharField] = forms.CharField(
        max_length=100,
        required=False,
        label="Buscar",
        widget=forms.TextInput(attrs={"placeholder": "Nome, email, CPF...", "class": "form-control"}),
    )
    tipo_usuario: ClassVar[forms.ChoiceField] = forms.ChoiceField(
        choices=[("", "Todos os tipos"), *list(TipoUsuario.choices)],
        required=False,
        label="Tipo de Usuário",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    status: ClassVar[forms.ChoiceField] = forms.ChoiceField(
        choices=[("", "Todos os status"), *list(StatusUsuario.choices)],
        required=False,
        label="Status",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    departamento: ClassVar[forms.CharField] = forms.CharField(
        max_length=100,
        required=False,
        label="Departamento",
        widget=forms.TextInput(attrs={"placeholder": "Departamento...", "class": "form-control"}),
    )
    ativo: ClassVar[forms.ChoiceField] = forms.ChoiceField(
        choices=[("", "Todos"), ("true", "Ativos"), ("false", "Inativos")],
        required=False,
        label="Usuário Ativo",
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class MeuPerfilForm(forms.ModelForm):
    """Formulário para o usuário editar seu próprio perfil."""

    first_name: ClassVar[forms.CharField] = forms.CharField(max_length=30, required=True, label="Nome")
    last_name: ClassVar[forms.CharField] = forms.CharField(max_length=30, required=True, label="Sobrenome")
    email: ClassVar[forms.EmailField] = forms.EmailField(required=True, label="E-mail")

    class Meta:
        """Meta opções para o formulário 'Meu Perfil'."""

        model = PerfilUsuarioEstendido
        fields: ClassVar[list[str]] = [
            "avatar",
            "cpf",
            "rg",
            "data_nascimento",
            "telefone",
            "celular",
            "endereco",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "cep",
            "cargo",
            "departamento",
            "receber_email_notificacoes",
            "receber_sms_notificacoes",
            "receber_push_notificacoes",
        ]
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
            "avatar": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Inicializa o formulário 'Meu Perfil' preenchendo os dados do usuário."""
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

        if self.instance and self.instance.cpf:
            self.fields["cpf"].widget.attrs["readonly"] = True
        else:
            self.fields["cpf"].widget.attrs["placeholder"] = "XXX.XXX.XXX-XX"

    def save(self, *, commit: bool = True) -> PerfilUsuarioEstendido:
        """Salva tanto o User quanto o PerfilUsuarioEstendido."""
        perfil = super().save(commit=False)

        if perfil.user:
            perfil.user.first_name = self.cleaned_data["first_name"]
            perfil.user.last_name = self.cleaned_data["last_name"]
            perfil.user.email = self.cleaned_data["email"]
            if commit:
                perfil.user.save()

        if commit:
            perfil.save()

        return perfil
