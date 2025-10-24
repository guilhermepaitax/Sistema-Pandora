"""Wrapper legado (DEPRECATED) - mantido apenas para compatibilidade temporária.

Este módulo delega para o resolver unificado em ``shared.services.permission_resolver``.
REMOVER após confirmar inexistência de imports residuais em ambos ambientes de desenvolvimento.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from django.contrib.auth.models import AbstractBaseUser

logger = logging.getLogger(__name__)

try:
    from shared.services.permission_resolver import (
        has_permission as _shared_has_permission,
    )
except Exception:  # pragma: no cover
    _shared_has_permission = None
    logger.exception("Resolver unificado indisponível - verifique instalação de ''shared''.")


def user_has_permission(  # noqa: PLR0913
    user: AbstractBaseUser | Any,  # noqa: ANN401
    modulo: str,
    acao: str,
    recurso: str | None = None,
    scope_tenant_id: int | None = None,
    request: Any = None,  # noqa: ARG001, ANN401
) -> bool:
    """Verifica permissão do usuário (interface legada).

    Args:
        user: Usuário para verificação
        modulo: Nome do módulo
        acao: Ação a ser verificada
        recurso: Recurso específico (opcional)
        scope_tenant_id: ID do tenant para escopo
        request: Request HTTP (mantido por compatibilidade, não utilizado)

    Returns:
        True se o usuário possui a permissão, False caso contrário.

    Note:
        Converte para o formato de ação esperado pelo resolver novo: ``ACAO_MODULO`` (upper).
        Mantém semântica básica: recurso é passado se fornecido.

    """
    if _shared_has_permission is None:
        return False
    # Normaliza ação no formato usado pelo resolver novo (ex: view_dashboard -> VIEW_DASHBOARD)
    action = f"{acao}_{modulo}".upper()
    # Recupera tenant dinamicamente apenas quando necessário (lazy import)
    from core.models import Tenant  # noqa: PLC0415

    try:
        tenant = Tenant.objects.get(id=scope_tenant_id)
    except Tenant.DoesNotExist:
        return False
    return _shared_has_permission(user, tenant, action, recurso)


# Alias compatível com código que importava a classe antiga
class PermissionResolver:  # pragma: no cover - wrapper fino
    """Mantido por compatibilidade (deprecated).

    Use shared.services.permission_resolver.PermissionResolver.

    Args:
        user: Usuário para verificação de permissões
        scope_tenant_id: ID do tenant para escopo (opcional)
        request_cache: Cache de request (mantido por compatibilidade, não utilizado)
        use_cache: Flag de uso de cache (mantido por compatibilidade, não utilizado)

    """

    def __init__(
        self,
        user: AbstractBaseUser | Any,  # noqa: ANN401
        scope_tenant_id: int | None = None,
        request_cache: dict[str, Any] | None = None,  # noqa: ARG002
        *,
        use_cache: bool = True,  # noqa: ARG002
    ) -> None:
        """Inicializa o resolver de permissões."""
        self.user = user
        self.scope_tenant_id = scope_tenant_id

    def has_permission(self, modulo: str, acao: str, recurso: str | None = None) -> bool:
        """Verifica se o usuário possui permissão para a ação no módulo.

        Args:
            modulo: Nome do módulo
            acao: Ação a ser verificada
            recurso: Recurso específico (opcional)

        Returns:
            True se possui permissão, False caso contrário.

        """
        return user_has_permission(self.user, modulo, acao, recurso, self.scope_tenant_id)


__all__ = ["PermissionResolver", "user_has_permission"]
