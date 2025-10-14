"""Comando unificado para reparar o campo ``enabled_modules`` de Tenants.

Normaliza formato, aplica defaults de plano, garante essenciais e (opcionalmente)
prune módulos inexistentes no registry. Exibe relatório consolidado ou JSON.
"""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:  # pragma: no cover - apenas para tipagem
    from collections.abc import Iterable, Iterator

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from core.models import Tenant
from core.module_registry import ESSENTIAL_MODULES, MODULE_DEFINITIONS, PLAN_DEFAULT_MODULES

logger = logging.getLogger(__name__)


class ReportItem(TypedDict):
    """Item de relatório para cada tenant processado."""

    tenant_id: int
    subdomain: str
    plan: str
    before: list[str]
    after: list[str]
    added: list[str]
    removed: list[str]
    unchanged: int
    normalized: bool
    plan_applied: bool
    essentials_added: bool
    pruned: bool


class Command(BaseCommand):
    """Repara o campo enabled_modules consolidando normalização + plano + essenciais.

    Pipeline por tenant:
      1. Normaliza formato (aceita dict legado / lista / string JSON / CSV).
      2. Aplica defaults de plano (se plano != CUSTOM).
      3. Garante módulos essenciais.
      4. (Opcional) Remove módulos inexistentes no registry (--prune-missing).
      5. Detecta alterações e persiste se --apply.

    Saída:
      - Texto humano ou JSON (--json) com lista detalhada de alterações.
      - --fail-on-dirty retorna exit code 2 se houver divergências não aplicadas.
    """

    help = "Normaliza e repara enabled_modules (formato, plano, essenciais, pruning opcional)."

    def add_arguments(self, parser: CommandParser) -> None:
        """Define argumentos de CLI para o comando."""
        parser.add_argument("--apply", action="store_true", help="Aplica correções (persiste alterações).")
        parser.add_argument("--json", action="store_true", help="Saída em JSON estruturado.")
        parser.add_argument(
            "--fail-on-dirty",
            action="store_true",
            help="Exit code 2 se existirem ajustes pendentes (útil em CI).",
        )
        parser.add_argument(
            "--only",
            help="Filtra tenants por substring do subdomain (case-insensitive).",
        )
        parser.add_argument(
            "--prune-missing",
            action="store_true",
            help="Remove módulos que não constam mais no registry (limpeza).",
        )
        parser.add_argument(
            "--plans",
            action="store_true",
            help="Força re-aplicar defaults de plano mesmo se já presentes.",
        )

    # ---------------- Internal helpers -----------------
    @staticmethod
    def _normalize(raw) -> list[str]:  # noqa: ANN001 - entrada deliberadamente flexível
        """Normaliza diferentes formatos para uma ``list[str]`` básica."""
        if isinstance(raw, dict):
            modules = raw.get("modules")
            if isinstance(modules, (list, tuple)):
                return [str(m).strip() for m in modules if m]
            flags: Iterable[tuple[str, object]] = ((k, v) for k, v in raw.items() if k != "modules")
            return [
                k
                for k, v in flags
                if ((isinstance(v, dict) and v.get("enabled") is True) or (v in (True, 1, "on", "ON", "enabled")))
            ]
        if isinstance(raw, (list, tuple)):
            return [str(m).strip() for m in raw if m]
        if isinstance(raw, str):
            s = raw.strip()
            if s.startswith(("[", "{")):
                try:
                    parsed = json.loads(s)
                    return Command._normalize(parsed)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha parse JSON naive enabled_modules: %s", exc)
            trans_map = str.maketrans({"[": None, "]": None, "'": None, '"': None})
            cleaned = s.translate(trans_map)
            return [p.strip() for p in cleaned.replace(";", ",").split(",") if p.strip()]
        return []

    def _apply_plan_defaults(self, plan: str, modules: set[str], *, force: bool) -> tuple[set[str], bool]:
        """Aplica defaults de plano se aplicável.

        Retorna (novo_set, houve_add).
        """
        if plan == "CUSTOM":
            return modules, False
        defaults = set(PLAN_DEFAULT_MODULES.get(plan, []))
        if force:
            before_len = len(modules)
            modules |= defaults
            return modules, len(modules) > before_len
        missing = defaults - modules
        if missing:
            modules |= missing
            return modules, True
        return modules, False

    def handle(self, *_args, **opts) -> None:  # noqa: ANN002, ANN003
        """Executa o fluxo de reparo sobre os tenants filtrados."""
        apply = bool(opts.get("apply"))
        only = opts.get("only") if isinstance(opts.get("only"), str) else None
        prune_missing = bool(opts.get("prune_missing"))
        force_plans = bool(opts.get("plans"))

        qs = Tenant.objects.all()
        if only:
            qs = qs.filter(subdomain__icontains=only)

        registry_keys = set(MODULE_DEFINITIONS.keys()) | set(ESSENTIAL_MODULES)
        report: list[ReportItem] = []
        dirty = 0
        ctx = transaction.atomic() if apply else self._null_context()
        with ctx:
            for tenant in qs.iterator():
                item, changed = self._process_tenant(
                    tenant,
                    force_plans=force_plans,
                    prune_missing=prune_missing,
                    registry_keys=registry_keys,
                )
                report.append(item)
                if changed:
                    dirty += 1
                    if apply:
                        tenant.enabled_modules = {"modules": item["after"]}
                        tenant.save(update_fields=["enabled_modules"])

        self._emit_output(report, dirty=dirty, total=qs.count(), applied=apply, opts=opts)

    # ---------------- Output helper -----------------
    def _emit_output(
        self,
        report: list[ReportItem],
        *,
        dirty: int,
        total: int,
        applied: bool,
        opts: dict,
    ) -> None:
        json_out = bool(opts.get("json"))
        fail_on_dirty = bool(opts.get("fail_on_dirty"))
        if json_out:
            payload = {"total": total, "dirty": dirty, "applied": applied, "items": report}
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(
                f"Tenants examinados: {total} | Necessitam ajuste: {dirty} | Apply={applied}",
            )
            for r in report:
                if (
                    r["added"]
                    or r["removed"]
                    or (not r["normalized"])
                    or r["plan_applied"]
                    or r["essentials_added"]
                    or r["pruned"]
                ):
                    self.stdout.write(
                        (
                            f"[{r['subdomain']}] plan={r['plan']} +{r['added']} -{r['removed']} "
                            f"essentials={r['essentials_added']} plan_applied={r['plan_applied']} pruned={r['pruned']}"
                        ),
                    )
            if applied:
                self.stdout.write(self.style.SUCCESS("Alterações aplicadas (quando necessárias)."))
            elif dirty:
                self.stdout.write(self.style.WARNING("Existem correções pendentes (execute com --apply)."))
            else:
                self.stdout.write(self.style.SUCCESS("Nenhuma correção necessária."))

        if fail_on_dirty and dirty and not applied:  # exit code control
            raise SystemExit(2)

    def _process_tenant(
        self,
        tenant: Tenant,
        *,
        force_plans: bool,
        prune_missing: bool,
        registry_keys: set[str],
    ) -> tuple[ReportItem, bool]:
        """Processa um tenant e retorna (report_item, changed)."""
        raw = tenant.enabled_modules
        plan = getattr(tenant, "plano_assinatura", "BASIC") or "BASIC"
        before_list = self._normalize(raw)
        before_set = set(before_list)
        normalized_flag = isinstance(raw, dict) and raw.get("modules") == before_list

        after_set, plan_applied_flag = self._apply_plan_defaults(plan, before_set, force=force_plans)

        essentials_added_flag = False
        missing_essentials = set(ESSENTIAL_MODULES) - after_set
        if missing_essentials:
            after_set |= missing_essentials
            essentials_added_flag = True

        pruned_flag = False
        if prune_missing:
            invalid = {m for m in after_set if m not in registry_keys}
            if invalid:
                after_set -= invalid
                pruned_flag = True

        after_list = sorted(after_set)
        added = sorted(after_set - before_set)
        removed = sorted(before_set - after_set)
        unchanged_count = len(after_set & before_set)
        changed = bool(
            added or removed or (not normalized_flag) or plan_applied_flag or essentials_added_flag or pruned_flag,
        )
        item: ReportItem = {
            "tenant_id": tenant.id,
            "subdomain": tenant.subdomain,
            "plan": plan,
            "before": sorted(before_set),
            "after": after_list,
            "added": added,
            "removed": removed,
            "unchanged": unchanged_count,
            "normalized": normalized_flag,
            "plan_applied": plan_applied_flag,
            "essentials_added": essentials_added_flag,
            "pruned": pruned_flag,
        }
        return item, changed

    # Fallback context manager quando não aplicando (faz nada)
    @contextmanager
    def _null_context(self) -> Iterator[None]:  # pragma: no cover - trivial
        """Context manager neutro (placeholder quando não aplicando transação)."""
        yield
