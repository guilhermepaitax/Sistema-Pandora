"""Testes para validar correção de carregamento de módulos em edição de tenant.

Bug corrigido em 24/out/2025: load_tenant_data_to_wizard() agora extrai apenas
a lista de módulos do dict, não o dict completo, permitindo que checkboxes
sejam pré-marcados corretamente.
"""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from core.models import Tenant
from core.wizard_views import TenantCreationWizardView

User = get_user_model()


class TestWizardEditModules(TestCase):
    """Testa carregamento correto de módulos para edição no wizard."""

    def setUp(self):
        """Configura ambiente de teste."""
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            "super",
            "super@example.com",
            "Pass!123",
        )
        self.tenant = Tenant.objects.create(
            name="Empresa Teste",
            subdomain="teste",
            tipo_pessoa="PJ",
            enabled_modules={
                "modules": ["admin", "clientes", "obras", "produtos"],
                "admin": {"enabled": True},
                "clientes": {"enabled": True},
                "obras": {"enabled": True},
                "produtos": {"enabled": True},
            },
        )

    def test_load_tenant_extracts_module_list_not_dict(self):
        """Valida que load_tenant_data_to_wizard extrai lista de módulos, não dict completo.

        Bug: estava passando dict completo {"modules": [...], "mod": {"enabled": True}}
        Fix: agora extrai apenas ["admin", "clientes", "obras", "produtos"]
        """
        request = self.factory.get("/wizard/")
        request.user = self.superuser
        request.session = {}

        view = TenantCreationWizardView()
        view.request = request

        # Carregar dados do tenant para wizard
        view.load_tenant_data_to_wizard(self.tenant)

        # Verificar que wizard_data foi criado
        wizard_data = request.session.get("tenant_wizard_data")
        self.assertIsNotNone(wizard_data, "wizard_data deve estar na sessão")

        # Verificar step_5 (configuração)
        step_5 = wizard_data.get("step_5")
        self.assertIsNotNone(step_5, "step_5 deve existir")

        main_data = step_5.get("main", {})
        enabled_modules = main_data.get("enabled_modules")

        # ✅ VALIDAÇÃO PRINCIPAL: deve ser LISTA, não dict
        self.assertIsInstance(
            enabled_modules,
            list,
            "enabled_modules deve ser lista, não dict completo",
        )

        # Verificar conteúdo
        self.assertEqual(
            set(enabled_modules),
            {"admin", "clientes", "obras", "produtos"},
            "Lista deve conter todos os módulos do tenant",
        )

        # Verificar que comparação "in" funciona (crítico para template)
        self.assertIn("obras", enabled_modules, '"obras" deve estar na lista')
        self.assertIn("clientes", enabled_modules, '"clientes" deve estar na lista')

    def test_load_tenant_handles_empty_modules(self):
        """Valida que tenant sem módulos retorna lista vazia."""
        tenant_empty = Tenant.objects.create(
            name="Sem Módulos",
            subdomain="semmod",
            tipo_pessoa="PJ",
            enabled_modules={"modules": []},
        )

        request = self.factory.get("/wizard/")
        request.user = self.superuser
        request.session = {}

        view = TenantCreationWizardView()
        view.request = request
        view.load_tenant_data_to_wizard(tenant_empty)

        wizard_data = request.session.get("tenant_wizard_data")
        enabled_modules = wizard_data["step_5"]["main"]["enabled_modules"]

        self.assertIsInstance(enabled_modules, list)
        self.assertEqual(enabled_modules, [])

    def test_load_tenant_handles_legacy_list_format(self):
        """Valida que formato legado (lista) também é tratado corretamente."""
        tenant_legacy = Tenant.objects.create(
            name="Formato Legado",
            subdomain="legacy",
            tipo_pessoa="PJ",
            enabled_modules=["admin", "clientes"],  # Formato antigo
        )

        request = self.factory.get("/wizard/")
        request.user = self.superuser
        request.session = {}

        view = TenantCreationWizardView()
        view.request = request
        view.load_tenant_data_to_wizard(tenant_legacy)

        wizard_data = request.session.get("tenant_wizard_data")
        enabled_modules = wizard_data["step_5"]["main"]["enabled_modules"]

        # Deve retornar lista vazia (formato legado não tem "modules" key)
        self.assertIsInstance(enabled_modules, list)
        self.assertEqual(enabled_modules, [])

    def test_load_tenant_handles_null_modules(self):
        """Valida que tenant com enabled_modules=None retorna lista vazia."""
        tenant_null = Tenant.objects.create(
            name="Null Modules",
            subdomain="nullmod",
            tipo_pessoa="PJ",
        )
        tenant_null.enabled_modules = None
        tenant_null.save(update_fields=["enabled_modules"])

        request = self.factory.get("/wizard/")
        request.user = self.superuser
        request.session = {}

        view = TenantCreationWizardView()
        view.request = request
        view.load_tenant_data_to_wizard(tenant_null)

        wizard_data = request.session.get("tenant_wizard_data")
        enabled_modules = wizard_data["step_5"]["main"]["enabled_modules"]

        self.assertIsInstance(enabled_modules, list)
        self.assertEqual(enabled_modules, [])
