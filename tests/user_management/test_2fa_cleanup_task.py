"""Testa a task Celery de limpeza de métricas 2FA antigas."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from user_management.tasks import cleanup_old_2fa_metrics

User = get_user_model()


@pytest.mark.django_db
def test_cleanup_2fa_metrics_resets_excessive_failures() -> None:
    """Verifica que contadores excessivos (>10000) são resetados."""
    user = User.objects.create_user(username="highfail", password="test123")  # noqa: S106
    perfil = user.perfil_estendido
    perfil.autenticacao_dois_fatores = True
    perfil.twofa_failure_count = 15000  # Acima do threshold
    perfil.save()

    result = cleanup_old_2fa_metrics()

    perfil.refresh_from_db()
    assert perfil.twofa_failure_count == 0
    assert result["reset_excessive"] >= 1
    assert result["processed"] >= 1


@pytest.mark.django_db
def test_cleanup_2fa_metrics_clears_orphan_lockouts() -> None:
    """Verifica que lockouts expirados há muito tempo são removidos."""
    user = User.objects.create_user(username="oldlock", password="test123")  # noqa: S106
    perfil = user.perfil_estendido
    perfil.autenticacao_dois_fatores = True
    perfil.twofa_locked_until = timezone.now() - timedelta(days=10)  # Expirado há 10 dias
    perfil.failed_2fa_attempts = 5
    perfil.save()

    result = cleanup_old_2fa_metrics()

    perfil.refresh_from_db()
    assert perfil.twofa_locked_until is None
    assert perfil.failed_2fa_attempts == 0
    assert result["cleared_orphan_locks"] >= 1


@pytest.mark.django_db
def test_cleanup_2fa_metrics_preserves_recent_lockouts() -> None:
    """Verifica que lockouts recentes não são removidos."""
    user = User.objects.create_user(username="recentlock", password="test123")  # noqa: S106
    perfil = user.perfil_estendido
    perfil.autenticacao_dois_fatores = True
    locked_until = timezone.now() + timedelta(minutes=5)  # Ainda ativo
    perfil.twofa_locked_until = locked_until
    perfil.failed_2fa_attempts = 3
    perfil.save()

    result = cleanup_old_2fa_metrics()

    perfil.refresh_from_db()
    assert perfil.twofa_locked_until == locked_until  # Preservado
    assert perfil.failed_2fa_attempts == 3  # Preservado
    assert result["cleared_orphan_locks"] == 0


@pytest.mark.django_db
def test_cleanup_2fa_metrics_ignores_non_2fa_users() -> None:
    """Verifica que usuários sem 2FA não são processados."""
    user = User.objects.create_user(username="no2fa", password="test123")  # noqa: S106
    perfil = user.perfil_estendido
    perfil.autenticacao_dois_fatores = False
    perfil.twofa_failure_count = 20000  # Muito alto, mas sem 2FA
    perfil.save()

    cleanup_old_2fa_metrics()

    perfil.refresh_from_db()
    assert perfil.twofa_failure_count == 20000  # Não foi alterado


@pytest.mark.django_db
def test_cleanup_2fa_metrics_preserves_normal_counters() -> None:
    """Verifica que contadores normais (<10000) não são resetados."""
    user = User.objects.create_user(username="normaluser", password="test123")  # noqa: S106
    perfil = user.perfil_estendido
    perfil.autenticacao_dois_fatores = True
    perfil.twofa_failure_count = 50  # Abaixo do threshold
    perfil.twofa_success_count = 100
    perfil.save()

    result = cleanup_old_2fa_metrics()

    perfil.refresh_from_db()
    assert perfil.twofa_failure_count == 50  # Preservado
    assert perfil.twofa_success_count == 100  # Preservado
    assert result["reset_excessive"] == 0
