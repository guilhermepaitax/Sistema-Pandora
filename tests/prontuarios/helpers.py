"""Helper functions for prontuarios tests (fixtures and test data creation)."""

from datetime import timedelta
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

from clientes.models import Cliente, PessoaFisica
from core.models import Tenant, TenantUser
from servicos.models import CategoriaServico, Servico, ServicoClinico

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser as User
else:
    User = get_user_model()


def bootstrap_clinica(*, nome_clinica: str = "Clinica X", subdomain: str = "clinica-x") -> Tenant:
    """Cria um tenant básico com módulos habilitados para testes."""
    return Tenant.objects.create(
        name=nome_clinica,
        subdomain=subdomain,
        enabled_modules={"modules": ["agendamentos", "prontuarios", "servicos", "clientes"]},
    )


def create_profissionais(tenant: Tenant, qnt: int = 2) -> list:
    """Cria profissionais vinculados ao tenant para testes."""
    profs = []
    for i in range(1, qnt + 1):
        u = User.objects.create_user(username=f"prof{i}", password="pass")  # noqa: S106
        TenantUser.objects.create(tenant=tenant, user=u)
        profs.append(u)
    return profs


def create_profissionais_staff(tenant: Tenant, qnt: int = 1) -> list:
    """Cria profissionais com is_staff=True vinculados ao tenant (auxiliar para testes)."""
    profs = []
    for i in range(1, qnt + 1):
        u = User.objects.create_user(username=f"profstaff{i}", password="pass", is_staff=True)  # noqa: S106
        TenantUser.objects.create(tenant=tenant, user=u)
        profs.append(u)
    return profs


def create_superuser_tenant(tenant: Tenant) -> User:
    """Cria um superusuário vinculado ao tenant para testes."""
    su = User.objects.create_superuser(username="root", email="root@test.com", password="pass")  # noqa: S106
    TenantUser.objects.create(tenant=tenant, user=su, is_tenant_admin=True)
    return su


def create_clientes_basicos(tenant: Tenant, total: int = 2) -> list:
    """Cria clientes pessoa física básicos para testes."""
    clientes = []
    for i in range(1, total + 1):
        c = Cliente.objects.create(tenant=tenant, tipo="PF", status="active")
        PessoaFisica.objects.create(cliente=c, nome_completo=f"Cliente {i}", cpf=f"000.000.000-0{i}")
        clientes.append(c)
    return clientes


def create_servico_basico(tenant: Tenant, nome: str = "Limpeza") -> Servico:
    """Cria um serviço clínico básico para testes (use este helper)."""
    categoria, _ = CategoriaServico.objects.get_or_create(
        nome="Default",
        defaults={"descricao": "Categoria padrão para testes"},
    )
    serv = Servico.objects.create(
        tenant=tenant,
        nome_servico=nome,
        descricao="Desc",
        categoria=categoria,
        ativo=True,
        is_clinical=True,
    )
    ServicoClinico.objects.create(servico=serv, duracao_estimada=timedelta(minutes=30))
    return serv
