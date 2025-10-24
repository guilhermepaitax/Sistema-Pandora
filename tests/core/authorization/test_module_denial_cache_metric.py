"""Teste de métrica de negação de módulo baseada em cache.

Migrado de `tests/core/test_module_denial_metric.py`.
"""

import pytest
from django.contrib.auth.models import AbstractBaseUser
from django.core.cache import cache

from core.authorization import REASON_MODULE_DISABLED, log_module_denial
from core.models import Tenant


@pytest.mark.django_db
def test_module_denial_metric_increment(django_user_model: type[AbstractBaseUser]) -> None:
    """Testa incremento da métrica de negação de módulo."""
    user = django_user_model.objects.create(username="muser")

    # Criar tenant real com módulo desabilitado
    tenant = Tenant.objects.create(
        nome="TestTenant",
        slug="test",
        enabled_modules={"modules": [], "financeiro": {"enabled": False}},
    )

    key = f"module_deny_count:financeiro:{REASON_MODULE_DISABLED}"
    cache.delete(key)

    log_module_denial(user, tenant, "financeiro", REASON_MODULE_DISABLED)
    v1 = cache.get(key)
    assert v1 == 1
    log_module_denial(user, tenant, "financeiro", REASON_MODULE_DISABLED)
    v2 = cache.get(key)
    assert v2 == 2
