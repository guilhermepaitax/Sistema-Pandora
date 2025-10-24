"""Testes de validação do Step 1 (Identificação) do Wizard de Tenants.

Valida os cenários básicos para PF e PJ e a ausência de tipo.
"""

import pytest
from django.test import RequestFactory

from core.models import CustomUser
from core.wizard_views import STEP_IDENT, TenantCreationWizardView


@pytest.mark.django_db
def test_validate_step1_pj_valid(admin_user: CustomUser) -> None:
    """PJ: deve validar quando nome e CNPJ são fornecidos."""
    rf = RequestFactory()
    request = rf.post(
        "/core/tenants/create/",
        data={
            "tipo_pessoa": "PJ",
            "pj-name": "Empresa X",
            "pj-cnpj": "11.222.333/0001-81",
        },
    )
    request.user = admin_user

    view = TenantCreationWizardView()
    view.setup(request)
    view.set_current_step(STEP_IDENT)

    forms = view.create_forms_for_step(STEP_IDENT, editing_tenant=None, data_source="POST")
    assert view.validate_step_1_forms(forms) is True


@pytest.mark.django_db
def test_validate_step1_pf_valid(admin_user: CustomUser) -> None:
    """PF: deve validar quando nome e CPF são fornecidos."""
    rf = RequestFactory()
    request = rf.post(
        "/core/tenants/create/",
        data={
            "tipo_pessoa": "PF",
            "pf-name": "Fulano",
            "pf-cpf": "123.456.789-09",
        },
    )
    request.user = admin_user

    view = TenantCreationWizardView()
    view.setup(request)
    view.set_current_step(STEP_IDENT)

    forms = view.create_forms_for_step(STEP_IDENT, editing_tenant=None, data_source="POST")
    assert view.validate_step_1_forms(forms) is True


@pytest.mark.django_db
def test_validate_step1_missing_type(admin_user: CustomUser) -> None:
    """Sem tipo_pessoa, a validação deve falhar."""
    rf = RequestFactory()
    request = rf.post(
        "/core/tenants/create/",
        data={
            "pj-name": "Empresa Z",
            "pj-cnpj": "11.222.333/0001-81",
        },
    )
    request.user = admin_user

    view = TenantCreationWizardView()
    view.setup(request)
    view.set_current_step(STEP_IDENT)

    forms = view.create_forms_for_step(STEP_IDENT, editing_tenant=None, data_source="POST")
    assert view.validate_step_1_forms(forms) is False
