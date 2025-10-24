"""Tarefas Celery de manutenção para user_management.

Separadas para permitir agendamento via CELERY_BEAT_SCHEDULE.
Inclui limpeza periódica de métricas 2FA.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.utils import timezone

from user_management.signals import desbloquear_usuarios, limpar_logs_antigos, limpar_sessoes_expiradas

logger = logging.getLogger(__name__)


def _safe_exec(fn: Any, label: str) -> Any:  # noqa: ANN401
    """Executa função com tratamento de erro seguro."""
    try:
        return fn()
    except Exception:
        logger.exception("[user_management.tasks] ERRO %s", label)
        return None


@shared_task
def desbloquear_usuarios_periodico() -> int | None:
    """Desbloqueia usuários com lockout expirado periodicamente."""
    return _safe_exec(desbloquear_usuarios, "desbloquear_usuarios")


@shared_task
def limpar_sessoes_expiradas_periodico() -> bool | None:
    """Limpa sessões Django expiradas periodicamente."""
    _safe_exec(limpar_sessoes_expiradas, "limpar_sessoes_expiradas")
    return True


@shared_task
def limpar_logs_antigos_periodico(dias: int = 90) -> bool | None:
    """Remove logs de atividade antigos periodicamente."""
    _safe_exec(lambda: limpar_logs_antigos(dias=dias), "limpar_logs_antigos")
    return True


@shared_task(name="user_management.cleanup_old_2fa_metrics")
def cleanup_old_2fa_metrics() -> dict[str, int]:
    """Limpa métricas 2FA antigas e normaliza contadores excessivos.

    Executado periodicamente (recomendado: semanal).

    Returns:
        dict com contadores de perfis processados e resetados.

    """
    from user_management.models import PerfilUsuarioEstendido  # noqa: PLC0415 (evita import circular)

    # Limite para considerar métrica "excessiva" (ex: >10000 falhas acumuladas)
    threshold_excessive = 10000

    # Limite de tempo para considerar lockout "órfão" (ex: >7 dias no passado)
    lockout_orphan_days = 7

    processed = 0
    reset_excessive = 0
    cleared_orphan_locks = 0

    now = timezone.now()
    cutoff_orphan = now - timedelta(days=lockout_orphan_days)

    # Processar perfis com métricas excessivas ou lockouts órfãos
    for perfil in PerfilUsuarioEstendido.objects.filter(
        autenticacao_dois_fatores=True,
    ).iterator():
        processed += 1
        updated_fields = []

        # Resetar contadores excessivos (indicam possível anomalia ou spam histórico)
        if getattr(perfil, "twofa_failure_count", 0) > threshold_excessive:
            perfil.twofa_failure_count = 0
            updated_fields.append("twofa_failure_count")
            reset_excessive += 1
            logger.info(
                "Reset excessive twofa_failure_count for user %s (was >%d)",
                perfil.user_id,
                threshold_excessive,
            )

        # Limpar lockouts órfãos (expirados há muito tempo)
        if perfil.twofa_locked_until and perfil.twofa_locked_until < cutoff_orphan:
            perfil.twofa_locked_until = None
            perfil.failed_2fa_attempts = 0
            updated_fields.extend(["twofa_locked_until", "failed_2fa_attempts"])
            cleared_orphan_locks += 1
            logger.info(
                "Cleared orphan lockout for user %s (expired %s)",
                perfil.user_id,
                perfil.twofa_locked_until,
            )

        if updated_fields:
            perfil.save(update_fields=updated_fields)

    result = {
        "processed": processed,
        "reset_excessive": reset_excessive,
        "cleared_orphan_locks": cleared_orphan_locks,
    }

    logger.info("2FA metrics cleanup completed: %s", result)
    return result
