from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

# formularios/views.py
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.mixins import ModuleRequiredMixin
from core.utils import get_current_tenant

from .forms import FormularioForm  # CORRIGIDO para importar FormularioForm (singular)
from .models import Formulario  # CORRIGIDO para importar Formulario (singular)


class FormulariosMixin(ModuleRequiredMixin):
    """Mixin base para views de formulários."""

    required_module = "formularios"


@login_required
def formularios_home(request):
    """View para o dashboard de Formulários, mostrando estatísticas e dados relevantes."""
    template_name = "formularios/formularios_home.html"
    tenant = get_current_tenant(request)

    if not tenant:
        messages.error(request, _("Por favor, selecione uma empresa para ver o dashboard."))
        return redirect(reverse("core:tenant_select"))

    context = {
        "titulo": _("Formulários"),
        "subtitulo": _("Visão geral do módulo Formulários"),
        "tenant": tenant,
    }

    return render(request, template_name, context)


class FormulariosListView(FormulariosMixin, ListView):  # O nome da classe da View pode ser plural
    model = Formulario  # CORRIGIDO para Formulario (singular)
    template_name = "formularios/formularios_list_ultra_modern.html"
    context_object_name = "formularios_list"
    paginate_by = 10


class FormulariosDetailView(FormulariosMixin, DetailView):
    model = Formulario  # CORRIGIDO para Formulario (singular)
    template_name = "formularios/formularios_detail_ultra_modern.html"
    context_object_name = "formulario"  # Convenção: singular para o objeto de detalhe


class FormulariosCreateView(FormulariosMixin, CreateView):
    model = Formulario  # CORRIGIDO para Formulario (singular)
    form_class = FormularioForm  # CORRIGIDO para FormularioForm (singular)
    template_name = "formularios/formularios_form_ultra_modern.html"
    success_url = reverse_lazy("formularios:formularios_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Adicionar Formulário"  # Singular
        return context


class FormulariosUpdateView(FormulariosMixin, UpdateView):
    model = Formulario  # CORRIGIDO para Formulario (singular)
    form_class = FormularioForm  # CORRIGIDO para FormularioForm (singular)
    template_name = "formularios/formularios_form_ultra_modern.html"
    success_url = reverse_lazy("formularios:formularios_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Editar Formulário"  # Singular
        return context


class FormulariosDeleteView(FormulariosMixin, DeleteView):
    model = Formulario  # CORRIGIDO para Formulario (singular)
    template_name = "formularios/formularios_confirm_delete_ultra_modern.html"
    success_url = reverse_lazy("formularios:formularios_list")
