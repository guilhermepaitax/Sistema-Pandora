"""Testes para garantir mapeamento definitivo de módulos por plano de assinatura."""

import pytest

from core.models import Tenant

pytestmark = pytest.mark.django_db

PLAN_EXPECTED = {
    "BASIC": {"admin", "user_management", "clientes", "fornecedores", "produtos", "servicos", "funcionarios"},
    "PRO": {
        "admin",
        "user_management",
        "clientes",
        "fornecedores",
        "produtos",
        "servicos",
        "funcionarios",
        "relatorios",
        "formularios",
    },
    "ENTERPRISE": {
        "admin",
        "user_management",
        "clientes",
        "fornecedores",
        "produtos",
        "servicos",
        "funcionarios",
        "relatorios",
        "formularios",
        "bi",
        "ai_auditor",
        "treinamento",
        "formularios_dinamicos",
    },
}


def create_tenant(plan: str) -> Tenant:
    """Criar tenant com plano específico."""
    return Tenant.objects.create(name=f"Empresa {plan}", subdomain=f"emp-{plan.lower()}", plano_assinatura=plan)


def test_basic_plan_modules() -> None:
    """BASIC deve conter módulos essenciais + básicos de operação."""
    t = create_tenant("BASIC")
    mods = set(t.enabled_modules.get("modules", []))
    assert PLAN_EXPECTED["BASIC"].issubset(mods)
    assert t.is_module_enabled("admin") is True


def test_pro_plan_modules() -> None:
    """PRO agrega módulos adicionais (relatorios, formularios) aos do BASIC."""
    t = create_tenant("PRO")
    mods = set(t.enabled_modules.get("modules", []))
    assert PLAN_EXPECTED["PRO"].issubset(mods)
    assert PLAN_EXPECTED["BASIC"].issubset(mods)


def test_enterprise_plan_modules() -> None:
    """ENTERPRISE inclui todos os módulos avançados."""
    t = create_tenant("ENTERPRISE")
    mods = set(t.enabled_modules.get("modules", []))
    assert PLAN_EXPECTED["ENTERPRISE"].issubset(mods)


def test_custom_plan_manual_preservation() -> None:
    """CUSTOM preserva seleção manual e apenas garante essenciais."""
    t = Tenant.objects.create(
        name="Empresa Custom",
        subdomain="emp-custom",
        plano_assinatura="CUSTOM",
        enabled_modules={"modules": ["clientes", "produtos"]},
    )
    mods = set(t.enabled_modules.get("modules", []))
    assert {"clientes", "produtos", "admin"}.issubset(mods)


def test_recompute_modules_from_plan_idempotent() -> None:
    """Recomputar módulos sem alterar seleção quando nada mudou."""
    t = create_tenant("BASIC")
    before = set(t.enabled_modules.get("modules", []))
    t.recompute_modules_from_plan()
    after = set(t.enabled_modules.get("modules", []))
    assert before == after


def test_core_always_enabled_logically() -> None:
    """Core deve ser sempre considerado habilitado."""
    t = create_tenant("BASIC")
    assert t.is_module_enabled("core") is True
