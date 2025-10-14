"""Template filters related to permission handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import template
from django.apps import apps
from django.contrib.auth.models import Permission
from django.utils.text import capfirst

if TYPE_CHECKING:
    from collections.abc import Iterable

register = template.Library()

_ACTION_LABELS: dict[str, str] = {
    "add": "Adicionar",
    "change": "Editar",
    "delete": "Excluir",
    "view": "Visualizar",
    "create": "Criar",
    "update": "Atualizar",
    "export": "Exportar",
    "import": "Importar",
    "approve": "Aprovar",
    "reject": "Rejeitar",
    "cancel": "Cancelar",
    "send": "Enviar",
    "run": "Executar",
    "schedule": "Agendar",
    "sync": "Sincronizar",
    "manage": "Gerenciar",
}


def _humanize_identifier(value: str | None) -> str:
    if not value:
        return ""
    return str(capfirst(str(value).replace("_", " ")))


def _cap_text(value: str | None) -> str:
    if not value:
        return ""
    return str(capfirst(str(value)))


@register.filter(name="filter_by_app")
def filter_by_app(permissions: Iterable[Permission] | None, app_label: str) -> list[Permission]:
    """Return permissions that belong to a given application label."""
    if not app_label or permissions is None:
        return []

    if hasattr(permissions, "filter"):
        return list(permissions.filter(content_type__app_label=app_label))

    filtered: list[Permission] = []
    for permission in permissions:
        if not isinstance(permission, Permission):
            continue
        content_type = getattr(permission, "content_type", None)
        if getattr(content_type, "app_label", None) == app_label:
            filtered.append(permission)
    return filtered


@register.filter(name="permission_label")
def permission_label(permission: Permission | None) -> str:
    """Return permission name translated to Portuguese when possible."""
    if not isinstance(permission, Permission):
        return ""

    codename = permission.codename or ""
    action, _, remainder = codename.partition("_")
    action_label = _ACTION_LABELS.get(action, _humanize_identifier(action))

    model_label = _permission_model_label(permission, remainder)
    return " ".join(part for part in (action_label, model_label) if part).strip()


def _permission_model_label(permission: Permission, remainder: str) -> str:
    """Best-effort attempt to return the target entity label in Portuguese."""
    content_type = getattr(permission, "content_type", None)
    if content_type is None:
        remainder = remainder or permission.codename or ""
        return _humanize_identifier(remainder)

    model_class = content_type.model_class()
    if model_class is not None:
        meta = getattr(model_class, "_meta", None)
        verbose = getattr(meta, "verbose_name", None)
        if verbose:
            return _cap_text(str(verbose))

    if getattr(content_type, "name", None):
        return _cap_text(str(content_type.name))

    if remainder:
        return _humanize_identifier(remainder)

    return _humanize_identifier(permission.codename)


@register.filter(name="app_verbose_name")
def app_verbose_name(app_label: str | None) -> str:
    """Return the human-friendly name of a Django app label."""
    if not app_label:
        return ""

    label = str(app_label)

    try:
        app_config = apps.get_app_config(label)
    except LookupError:
        app_config = None

    if app_config and getattr(app_config, "verbose_name", None):
        return str(app_config.verbose_name)

    return _humanize_identifier(label)
