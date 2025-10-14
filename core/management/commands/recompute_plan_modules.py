"""Comando para recomputar módulos habilitados a partir do plano de assinatura.

Uso típico:
    python manage.py recompute_plan_modules
    python manage.py recompute_plan_modules --dry-run
    python manage.py recompute_plan_modules --only=demo
"""

from typing import TypedDict

from django.core.management.base import BaseCommand, CommandParser

from core.models import Tenant


class _Options(TypedDict, total=False):
    dry_run: bool
    only: str


class Command(BaseCommand):
    """Recalcula enabled_modules conforme plano e garante módulos essenciais."""

    help = "Recalcula enabled_modules para todos os tenants conforme plano e módulos essenciais"

    def add_arguments(self, parser: CommandParser) -> None:
        """Adicionar argumentos de linha de comando."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Apenas exibe o que seria alterado sem persistir",
        )
        parser.add_argument(
            "--only",
            dest="only",
            help="Filtrar por subdomain (substring, case-insensitive)",
        )

    def handle(self, **options: object) -> None:
        """Executar recomputação para cada tenant."""
        opts: _Options = {k: v for k, v in options.items() if k in ("dry_run", "only")}  # type: ignore[assignment]
        dry_run: bool = bool(opts.get("dry_run", False))
        only: str | None = opts.get("only") if isinstance(opts.get("only"), str) else None
        qs = Tenant.objects.all()
        if only:
            qs = qs.filter(subdomain__icontains=only)
        updated = 0
        for tenant in qs.iterator():
            before = set(tenant.enabled_modules.get("modules", []) if isinstance(tenant.enabled_modules, dict) else [])
            modules = tenant.recompute_modules_from_plan(persist=not dry_run)
            after = set(modules)
            changed = before != after
            if changed:
                updated += 1
            self.stdout.write(
                "{}: {} plan={} modules={}".format(
                    tenant.subdomain,
                    "CHANGED" if changed else "OK",
                    tenant.plano_assinatura,
                    sorted(after),
                ),
            )
        self.stdout.write(self.style.SUCCESS(f"Processados {qs.count()} tenants; alterados: {updated}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: nenhuma alteração persistida."))
