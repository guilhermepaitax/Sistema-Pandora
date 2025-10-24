"""Centraliza definição e utilidades de módulos habilitáveis do sistema.

Objetivos:
- Fonte única de verdade para metadados de módulos (nome, descrição, categoria, premium, ícone, cor).
- Funções utilitárias para: defaults de planos, essenciais, normalização, montagem de catálogo UI.
- Evitar duplicação em `core.forms` e `core.wizard_forms`.

Uso:
from core.module_registry import (
    MODULE_DEFINITIONS, MODULE_VISUAL, get_plan_default_modules,
    compute_initial_modules, annotate_modules_for_ui,
    normalize_modules_canonical, ensure_essentials,
    get_all_module_choices,
)
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable, Sequence

# -----------------------------
# Metadados dos módulos
# -----------------------------
MODULE_DEFINITIONS: dict[str, dict[str, Any]] = {
    # Gestão Básica
    "clientes": {
        "name": "Clientes",
        "description": "Gestão de clientes",
        "category": "Gestão Básica",
        "premium": False,
    },
    "fornecedores": {
        "name": "Fornecedores",
        "description": "Gestão de fornecedores",
        "category": "Gestão Básica",
        "premium": False,
    },
    "produtos": {
        "name": "Produtos",
        "description": "Catálogo de produtos",
        "category": "Gestão Básica",
        "premium": False,
    },
    "servicos": {
        "name": "Serviços",
        "description": "Gestão de serviços",
        "category": "Gestão Básica",
        "premium": False,
    },
    "funcionarios": {
        "name": "Funcionários",
        "description": "Gestão de colaboradores",
        "category": "Gestão Básica",
        "premium": False,
    },
    "cadastros_gerais": {
        "name": "Cadastros Gerais",
        "description": "Cadastros auxiliares",
        "category": "Gestão Básica",
        "premium": False,
    },
    # Obras e Projetos
    "obras": {
        "name": "Obras",
        "description": "Gestão de obras e projetos",
        "category": "Obras e Projetos",
        "premium": False,
    },
    "orcamentos": {
        "name": "Orçamentos",
        "description": "Gestão de orçamentos",
        "category": "Obras e Projetos",
        "premium": False,
    },
    "quantificacao_obras": {
        "name": "Quantificação de Obras",
        "description": "Quantificações e cálculos",
        "category": "Obras e Projetos",
        "premium": True,
    },
    "apropriacao": {
        "name": "Apropriação",
        "description": "Apropriação de custos",
        "category": "Obras e Projetos",
        "premium": True,
    },
    "mao_obra": {
        "name": "Mão de Obra",
        "description": "Equipes e mão de obra",
        "category": "Obras e Projetos",
        "premium": False,
    },
    # Financeiro
    "compras": {
        "name": "Compras",
        "description": "Processos de compra",
        "category": "Financeiro e Operacional",
        "premium": False,
    },
    "financeiro": {
        "name": "Financeiro",
        "description": "Controle financeiro",
        "category": "Financeiro e Operacional",
        "premium": False,
    },
    "estoque": {
        "name": "Estoque",
        "description": "Gestão de estoque",
        "category": "Financeiro e Operacional",
        "premium": False,
    },
    "aprovacoes": {
        "name": "Aprovações",
        "description": "Workflows de aprovação",
        "category": "Financeiro e Operacional",
        "premium": True,
    },
    # Saúde
    "prontuarios": {
        "name": "Prontuários",
        "description": "Prontuários eletrônicos",
        "category": "Saúde e Clínicas",
        "premium": True,
    },
    "sst": {
        "name": "SST",
        "description": "Segurança e Saúde do Trabalho",
        "category": "Saúde e Clínicas",
        "premium": True,
    },
    # Comunicação
    "agenda": {
        "name": "Agenda",
        "description": "Agenda e eventos",
        "category": "Comunicação e Organização",
        "premium": False,
    },
    "agendamentos": {
        "name": "Agendamentos Avançados",
        "description": "Regras de agendamento",
        "category": "Comunicação e Organização",
        "premium": False,
    },
    "chat": {
        "name": "Chat",
        "description": "Chat interno",
        "category": "Comunicação e Organização",
        "premium": True,
    },
    "notifications": {
        "name": "Notificações",
        "description": "Alertas e notificações",
        "category": "Comunicação e Organização",
        "premium": False,
    },
    # Formulários / Docs
    "formularios": {
        "name": "Formulários",
        "description": "Formulários customizados",
        "category": "Formulários e Documentação",
        "premium": False,
    },
    "formularios_dinamicos": {
        "name": "Formulários Dinâmicos",
        "description": "Builder avançado",
        "category": "Formulários e Documentação",
        "premium": True,
    },
    "documentos": {
        "name": "Documentos",
        "description": "Gestão de documentos",
        "category": "Formulários e Documentação",
        "premium": False,
    },
    # Capacitação
    "treinamento": {
        "name": "Treinamentos",
        "description": "Gestão de treinamentos",
        "category": "Capacitação e Gestão",
        "premium": True,
    },
    "user_management": {
        "name": "Gestão de Usuários",
        "description": "Usuários e permissões",
        "category": "Capacitação e Gestão",
        "premium": False,
    },
    # Inteligência
    "relatorios": {
        "name": "Relatórios",
        "description": "Relatórios gerenciais",
        "category": "Análise e Inteligência",
        "premium": False,
    },
    "bi": {
        "name": "Business Intelligence",
        "description": "Dashboards e BI",
        "category": "Análise e Inteligência",
        "premium": True,
    },
    "ai_auditor": {
        "name": "Auditor IA",
        "description": "Auditoria automática",
        "category": "Análise e Inteligência",
        "premium": True,
    },
    # Administrativos / Portais / Assistentes
    "admin": {
        "name": "Dashboard Admin",
        "description": "Painel administrativo",
        "category": "Administrativo",
        "premium": False,
    },
    "portal_cliente": {
        "name": "Portal do Cliente",
        "description": "Portal externo clientes",
        "category": "Portais Externos",
        "premium": False,
    },
    "portal_fornecedor": {
        "name": "Portal do Fornecedor",
        "description": "Portal fornecedores",
        "category": "Portais Externos",
        "premium": False,
    },
    "assistente_web": {
        "name": "Assistente Web",
        "description": "Assistente interativo IA",
        "category": "Suporte e Automação",
        "premium": True,
    },
}

# -----------------------------
# Planos / Essenciais
# -----------------------------

PLAN_DEFAULT_MODULES: dict[str, list[str]] = {
    "BASIC": [
        "admin",
        "user_management",
        "clientes",
        "fornecedores",
        "produtos",
        "servicos",
        "funcionarios",
    ],
    "PRO": [
        "admin",
        "user_management",
        "clientes",
        "fornecedores",
        "produtos",
        "servicos",
        "funcionarios",
        "relatorios",
        "formularios",
    ],
    "ENTERPRISE": [
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
    ],
    "CUSTOM": ["admin", "user_management"],
}

ESSENTIAL_MODULES: list[str] = ["admin"]

"""Mapeamento visual (ícones/cores) por módulo para uso em templates/UI."""
MODULE_VISUAL: dict[str, dict[str, str]] = {
    "clientes": {"icon": "fas fa-users", "color": "text-primary"},
    "fornecedores": {"icon": "fas fa-truck", "color": "text-info"},
    "produtos": {"icon": "fas fa-box", "color": "text-success"},
    "servicos": {"icon": "fas fa-tools", "color": "text-warning"},
    "funcionarios": {"icon": "fas fa-id-badge", "color": "text-secondary"},
    "cadastros_gerais": {"icon": "fas fa-database", "color": "text-dark"},
    "obras": {"icon": "fas fa-hard-hat", "color": "text-primary"},
    "orcamentos": {"icon": "fas fa-calculator", "color": "text-info"},
    "quantificacao_obras": {"icon": "fas fa-ruler-combined", "color": "text-success"},
    "apropriacao": {"icon": "fas fa-chart-pie", "color": "text-warning"},
    "mao_obra": {"icon": "fas fa-users-cog", "color": "text-secondary"},
    "compras": {"icon": "fas fa-shopping-cart", "color": "text-success"},
    "financeiro": {"icon": "fas fa-dollar-sign", "color": "text-warning"},
    "estoque": {"icon": "fas fa-warehouse", "color": "text-secondary"},
    "aprovacoes": {"icon": "fas fa-check-circle", "color": "text-success"},
    "prontuarios": {"icon": "fas fa-file-medical", "color": "text-danger"},
    "sst": {"icon": "fas fa-shield-alt", "color": "text-danger"},
    "agenda": {"icon": "fas fa-calendar", "color": "text-success"},
    "agendamentos": {"icon": "fas fa-clock", "color": "text-success"},
    "chat": {"icon": "fas fa-comments", "color": "text-warning"},
    "notifications": {"icon": "fas fa-bell", "color": "text-info"},
    "formularios": {"icon": "fas fa-file-alt", "color": "text-secondary"},
    "formularios_dinamicos": {"icon": "fas fa-magic", "color": "text-purple"},
    "treinamento": {"icon": "fas fa-graduation-cap", "color": "text-info"},
    "user_management": {"icon": "fas fa-users-cog", "color": "text-dark"},
    "relatorios": {"icon": "fas fa-chart-bar", "color": "text-primary"},
    "bi": {"icon": "fas fa-chart-line", "color": "text-info"},
    "ai_auditor": {"icon": "fas fa-robot", "color": "text-success"},
    "admin": {"icon": "fas fa-tachometer-alt", "color": "text-dark"},
    "portal_cliente": {"icon": "fas fa-handshake", "color": "text-primary"},
    "portal_fornecedor": {"icon": "fas fa-people-carry", "color": "text-primary"},
    "assistente_web": {"icon": "fas fa-assistive-listening-systems", "color": "text-info"},
    "documentos": {"icon": "fas fa-folder-open", "color": "text-secondary"},
}


# -----------------------------
# Funções utilitárias
# -----------------------------
@lru_cache(maxsize=32)
def get_plan_default_modules(plan: str) -> set[str]:
    """Retorna o conjunto de módulos padrão (excluindo essenciais) para o plano informado.

    Import tardio evita import cíclico com `core.models`.
    """
    return set(PLAN_DEFAULT_MODULES.get(plan, []))


@lru_cache(maxsize=1)
def get_essential_modules() -> set[str]:
    """Retorna o conjunto de módulos essenciais (sempre habilitados)."""
    return set(ESSENTIAL_MODULES)


def ensure_essentials(mods: Iterable[str]) -> list[str]:
    """Garante que a lista contenha todos os essenciais e retorna ordenada."""
    return sorted(set(mods) | get_essential_modules())


def normalize_modules_canonical(raw: object) -> list[str]:
    """Normaliza qualquer representação de módulos para lista simples.

    Aceita: dict, list/tuple, string JSON ou CSV. Usa normalizador do modelo.
    """
    # Implementa normalização mínima (espelha lógica principal do modelo Tenant)
    if isinstance(raw, dict):
        if "modules" in raw and isinstance(raw["modules"], (list, tuple)):
            return [str(m).strip() for m in raw["modules"] if m]
        return [k for k, v in raw.items() if v in (True, 1, "on", "ON")]
    if isinstance(raw, (list, tuple)):
        return [str(m).strip() for m in raw if m]
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith(("[", "{")):
            try:
                parsed = _json.loads(s)
                return normalize_modules_canonical(parsed)
            except _json.JSONDecodeError:  # pragma: no cover
                pass
        cleaned = s.replace("[", "").replace("]", "").replace('"', "").replace("'", "")
        return [m.strip() for m in cleaned.replace(";", ",").split(",") if m.strip()]
    return []


def compute_initial_modules(plan: str, existing: Sequence[str] | None) -> list[str]:
    """Calcula lista inicial para UI considerando plano, existentes e essenciais."""
    existing_set = set(existing or [])
    base = existing_set | get_essential_modules()
    if plan != "CUSTOM":
        base |= get_plan_default_modules(plan)
    return sorted(m for m in base if m in MODULE_DEFINITIONS or m in get_essential_modules())


@dataclass(frozen=True)
class ModuleUIData:
    """Estrutura enriquecida para renderização de módulos na UI."""

    key: str
    label: str
    category: str
    description: str
    premium: bool
    icon: str
    color: str
    is_default: bool
    is_essential: bool
    locked: bool


def annotate_modules_for_ui(plan: str, _selected: Sequence[str]) -> list[ModuleUIData]:
    """Gera lista de objetos ModuleUIData com flags para renderização.

    Bloqueia apenas módulos essenciais para proteger funcionalidade crítica do sistema.
    Módulos do plano ficam marcados (is_default) mas podem ser desmarcados se necessário.

    Args:
        plan: Plano de assinatura (BASIC, PRO, ENTERPRISE, CUSTOM).
        _selected: Módulos atualmente selecionados (não usado, mantido para compatibilidade).

    """
    defaults = get_plan_default_modules(plan) if plan != "CUSTOM" else set()
    essentials = get_essential_modules()
    data: list[ModuleUIData] = []
    for code, meta in MODULE_DEFINITIONS.items():
        is_default = code in defaults
        is_essential = code in essentials
        visual = MODULE_VISUAL.get(code, {})
        data.append(
            ModuleUIData(
                key=code,
                label=str(meta.get("name") or code),
                category=str(meta.get("category") or "Outros"),
                description=str(meta.get("description") or ""),
                premium=bool(meta.get("premium")),
                icon=str(visual.get("icon") or "fas fa-puzzle-piece"),
                color=str(visual.get("color") or "text-muted"),
                is_default=is_default,
                is_essential=is_essential,
                locked=is_essential,  # Bloquear apenas essenciais
            ),
        )
    data.sort(key=lambda d: (d.category, d.label))
    return data


def group_ui_catalog(modules: Sequence[ModuleUIData]) -> list[tuple[str, list[ModuleUIData]]]:
    """Agrupa para UI: [(categoria, [ModuleUIData,...]), ...] ordenado."""
    grouped: dict[str, list[ModuleUIData]] = {}
    for m in modules:
        grouped.setdefault(m.category, []).append(m)
    for items in grouped.values():
        items.sort(key=lambda d: d.label)
    ordered: list[tuple[str, list[ModuleUIData]]] = []
    if "Gestão Básica" in grouped:
        ordered.append(("Gestão Básica", grouped.pop("Gestão Básica")))
    ordered.extend(sorted(grouped.items(), key=lambda t: t[0]))
    return ordered


@lru_cache(maxsize=1)
def get_all_module_choices() -> list[tuple[str, str]]:
    """Tuplas (codigo, nome) ordenadas para campos de formulário."""
    return sorted(((k, str(v.get("name") or k)) for k, v in MODULE_DEFINITIONS.items()), key=lambda x: x[1])
