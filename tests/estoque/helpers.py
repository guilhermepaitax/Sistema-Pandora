"""Helpers de teste para o módulo de estoque.

Centraliza criação de usuário + tenant e dados básicos usados nos testes.
"""

from django.contrib.auth import get_user_model
from django.test import Client

from core.models import Tenant, TenantUser
from estoque.models import Deposito, EstoqueSaldo
from produtos.models import Categoria, Produto


def bootstrap_user_tenant(
    client: Client,
    *,
    username: str = "tester",
    password: str = "",
) -> tuple:
    """Cria usuário, tenant vinculado e faz login atribuindo tenant_id na sessão.

    Retorna (user, tenant, client).
    """
    user_model = get_user_model()
    pwd = password or "pass-for-tests"
    user = user_model.objects.create_user(username=username, password=pwd)
    tenant = Tenant.objects.create(name=f"Empresa {username}", subdomain=f"empresa-{username}")
    TenantUser.objects.create(user=user, tenant=tenant)
    client.login(username=username, password=pwd)
    # garantir tenant na sessão
    sess = client.session
    sess["tenant_id"] = tenant.id
    sess.save()
    return user, tenant, client


def create_basic_inventory(
    produto_nome: str = "Produto X",
    deposito_codigo: str = "DEP1",
    qtd: int = 50,
    reservado: int = 5,
) -> tuple:
    """Cria um conjunto básico de entidades de estoque para testes."""
    categoria = Categoria.objects.create(nome="Geral")
    produto = Produto.objects.create(nome=produto_nome, categoria=categoria)
    deposito = Deposito.objects.create(codigo=deposito_codigo, nome="Principal")
    saldo = EstoqueSaldo.objects.create(produto=produto, deposito=deposito, quantidade=qtd, reservado=reservado)
    return categoria, produto, deposito, saldo
