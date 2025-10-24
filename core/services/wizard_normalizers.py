"""Normalizadores e utilidades de parsing usados pelo wizard de Tenants.

Inclui:
 - Normalização de listas heterogêneas de módulos (strings, json, dict legado);
 - Deduplicação preservando ordem;
 - Parsing de redes sociais;
 - Normalização de aliases de módulos (ex.: agendamentos -> agenda).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - apenas para tipagem estática
    from collections.abc import Iterable, Sequence

logger = logging.getLogger(__name__)

__all__ = [
    "dedupe_preserve_order",
    "normalize_enabled_modules",
    "normalize_module_aliases",
    "parse_socials_json",
]


def dedupe_preserve_order(items: Sequence[str]) -> list[str]:
    """Remove duplicados mantendo a ordem de primeira ocorrência."""
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            out.append(it)
    return out


def normalize_enabled_modules(value: object) -> list[str]:
    """Normalizar entrada heterogênea de módulos para lista limpa.

    SEMPRE retorna lista de strings (nunca dict).
    Aceita vários formatos de entrada mas output é consistente.

    Args:
        value: String CSV/JSON, lista, set, ou dict no formato moderno

    Returns:
        Lista ordenada alfabeticamente sem duplicados

    Examples:
        >>> normalize_enabled_modules("clientes, produtos")
        ['clientes', 'produtos']
        >>> normalize_enabled_modules(['clientes', 'produtos'])
        ['clientes', 'produtos']
        >>> normalize_enabled_modules({"modules": ["clientes"]})
        ['clientes']

    """
    if not value:
        return []

    modules: list[str] = []

    try:
        if isinstance(value, str):  # CSV ou JSON
            stripped = value.strip()
            if stripped.startswith("["):
                # Tentar parsear como JSON
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    modules.extend(str(x).strip() for x in parsed if x)
                else:
                    # Fallback CSV
                    modules.extend(v.strip() for v in stripped.split(",") if v.strip())
            else:
                # Tratar como CSV
                modules.extend(v.strip() for v in stripped.split(",") if v.strip())

        elif isinstance(value, dict):
            # Formato moderno: extrair lista "modules"
            seq = value.get("modules")
            if isinstance(seq, (list, tuple, set)):
                modules.extend(str(v).strip() for v in seq if v)
            else:
                # Formato legado: dict sem "modules" - extrair chaves com enabled=True
                for key, val in value.items():
                    if isinstance(val, dict) and val.get("enabled") is True:
                        modules.append(str(key).strip())
                    elif isinstance(val, list):
                        # Caso: {"legacy": ["x", "y"]}
                        modules.extend(str(v).strip() for v in val if v)

        elif isinstance(value, (list, tuple, set)):
            modules.extend(str(v).strip() for v in value if v)

    except Exception as e:  # noqa: BLE001
        logger.warning("Falha ao normalizar enabled_modules: %s", e)

    return sorted(dedupe_preserve_order(modules))


_MODULE_ALIASES: dict[str, str] = {
    # Alias históricos ou variações comuns digitadas pelo usuário / front
    "agendamento": "agenda",
    "agendamentos": "agenda",
    "agendamentos_avancados": "agenda",
}


def normalize_module_aliases(mods: Iterable[str] | None) -> list[str]:
    """Normaliza aliases conhecidos de módulos (ex.: agendamentos -> agenda).

    Mantém ordem relativa (após dedupe) e não valida existência — validação fica a cargo
    do form de configuração. Útil para limpeza antes de persistir/mesclar valores.
    """
    if not mods:
        return []
    resolved: list[str] = []
    for raw in mods:
        if not raw:
            continue
        k = str(raw).strip()
        resolved.append(_MODULE_ALIASES.get(k, k))
    return dedupe_preserve_order(resolved)


def parse_socials_json(raw: str | None) -> dict[str, str]:
    """Interpretar lista JSON de {'nome','link'} para dict nome->link.

    Ignora entradas inválidas; a última ocorrência de cada nome prevalece.
    """
    if not raw:
        return {}
    raw = raw.strip()
    try:
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        logger.warning("socials_json inválido: %s", e)
        return {}
    else:
        if not isinstance(data, list):
            return {}
        result: dict[str, str] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            nome = (item.get("nome") or "").strip()
            link = (item.get("link") or "").strip()
            if nome and link:
                result[nome] = link
        return result
