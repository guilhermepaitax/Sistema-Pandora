"""Views do módulo de obras.

Este módulo contém as views para gerenciamento de obras, incluindo:
- ObrasMixin: Mixin base com filtros de tenant e módulo
- Dashboard de obras (obras_home)
- CRUD de obras via Class-Based Views (List, Detail, Delete)
- Gerenciamento de unidades e documentos
- Geração em massa de unidades
- Views legadas para compatibilidade

Nota: A criação e edição de obras é realizada exclusivamente via
wizard_views.py e wizard_forms.py.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, QuerySet, Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, ListView
from django_tables2 import RequestConfig

from core.mixins import ModuleRequiredMixin, TenantRequiredMixin
from core.utils import get_current_tenant
from shared.mixins.ui_permissions import UIPermissionsMixin
from shared.services.ui_permissions import build_ui_permissions

from .forms import DocumentoObraForm, GerarUnidadesEmMassaForm, ModeloUnidadeForm, UnidadeForm
from .models import DocumentoObra, Obra, Unidade
from .tables import ObraTable


class ObrasMixin(LoginRequiredMixin, TenantRequiredMixin, ModuleRequiredMixin):
    """Mixin base para views de obras."""

    model = Obra
    required_module = "obras"

    def get_queryset(self) -> QuerySet[Obra]:
        """Filtra obras por tenant se aplicável."""
        queryset = super().get_queryset()
        tenant = get_current_tenant(self.request)
        if tenant and hasattr(self.model, "tenant"):
            queryset = queryset.filter(tenant=tenant)
        return queryset

    def get_context_data(
        self,
        **kwargs: object,
    ) -> dict[str, object]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Adiciona tenant ao contexto."""
        context = super().get_context_data(**kwargs)
        context["tenant"] = get_current_tenant(self.request)
        return context


@login_required
def obras_home(request: HttpRequest) -> HttpResponse:
    """Dashboard principal do módulo obras."""
    tenant = get_current_tenant(request)

    if not tenant:
        messages.error(request, _("Por favor, selecione uma empresa para ver o dashboard."))
        return redirect(reverse("core:tenant_select"))

    # Queryset base para estatísticas
    obras_qs = Obra.objects.all()
    if hasattr(Obra, "tenant"):
        obras_qs = obras_qs.filter(tenant=tenant)

    # Calcular estatísticas
    total_obras = obras_qs.count()
    obras_ativas = obras_qs.filter(status="em_andamento").count() if hasattr(Obra, "status") else 0
    obras_concluidas = obras_qs.filter(status="concluida").count() if hasattr(Obra, "status") else 0
    obras_pausadas = obras_qs.filter(status="pausada").count() if hasattr(Obra, "status") else 0

    # Valor total em obras
    valor_total_obras = obras_qs.aggregate(total=Sum("valor_contrato"))["total"] or 0

    # Obras recentes (últimos 30 dias)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    obras_recentes = obras_qs.filter(data_inicio__gte=thirty_days_ago).count() if hasattr(Obra, "data_inicio") else 0

    # Obras por status para gráfico
    obras_por_status = []
    if hasattr(Obra, "status"):
        for status in ["em_andamento", "pausada", "concluida", "cancelada"]:
            count = obras_qs.filter(status=status).count()
            if count > 0:
                obras_por_status.append({"status": status.replace("_", " ").title(), "count": count})

    # Últimas obras cadastradas
    ultimas_obras = obras_qs.order_by("-id")[:5]

    # Top obras por valor
    top_obras_valor = obras_qs.order_by("-valor_contrato")[:5] if hasattr(Obra, "valor_contrato") else []

    ui_perms = build_ui_permissions(
        request.user,  # pyright: ignore[reportArgumentType]
        tenant,
        app_label="obras",
        model_name="obra",
    )

    context = {
        "titulo": "Dashboard - Obras",
        "subtitulo": "Visão geral do módulo de obras",
        "tenant": tenant,
        # Estatísticas principais
        "total_obras": total_obras,
        "obras_ativas": obras_ativas,
        "obras_concluidas": obras_concluidas,
        "obras_pausadas": obras_pausadas,
        "valor_total_obras": valor_total_obras,
        "obras_recentes": obras_recentes,
        # Dados para gráficos
        "obras_por_status": obras_por_status,
        # Listas
        "ultimas_obras": ultimas_obras,
        "top_obras_valor": top_obras_valor,
        "ui_perms": ui_perms,
        "perms_ui": ui_perms,
    }

    return render(request, "obras/obras_home.html", context)


class ObraListView(UIPermissionsMixin, ObrasMixin, ListView):
    """View para listagem de obras."""

    template_name = "obras/obras_list.html"
    context_object_name = "obras"
    paginate_by = 20
    app_label = "obras"
    model_name = "obra"

    def get_context_data(
        self,
        **kwargs: object,
    ) -> dict[str, object]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Adiciona tabela e estatísticas ao contexto."""
        context = super().get_context_data(**kwargs)
        obras = self.get_queryset()

        # Configurar tabela
        table = ObraTable(obras)
        RequestConfig(
            self.request,
            paginate={"per_page": self.paginate_by},  # pyright: ignore[reportArgumentType]
        ).configure(table)

        # Estatísticas para cards
        thirty_days_ago = timezone.now() - timedelta(days=30)

        context.update(
            {
                "table": table,
                "titulo": "Obras",
                "subtitulo": "Gerenciamento de Obras",
                "add_url": reverse("obras:obra_wizard"),
                "module": "obras",
                # Estatísticas
                "total_count": obras.count(),
                "active_count": (
                    obras.filter(status="em_andamento").count() if hasattr(Obra, "status") else obras.count()
                ),
                "inactive_count": obras.filter(status="pausada").count() if hasattr(Obra, "status") else 0,
                "recent_count": (
                    obras.filter(data_inicio__gte=thirty_days_ago).count() if hasattr(Obra, "data_inicio") else 0
                ),
            },
        )

        return context


class ObraDetailView(UIPermissionsMixin, ObrasMixin, DetailView):
    """View para detalhes da obra."""

    template_name = "obras/obras_detail.html"
    context_object_name = "obra"
    app_label = "obras"
    model_name = "obra"

    def get_context_data(
        self,
        **kwargs: object,
    ) -> dict[str, object]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Adiciona unidades, documentos e formulários ao contexto."""
        context = super().get_context_data(**kwargs)
        obra = self.object

        # Buscar unidades e documentos relacionados
        unidades = Unidade.objects.filter(obra=obra)
        documentos = DocumentoObra.objects.filter(obra=obra).order_by("-data_upload")

        # Formulários para adicionar unidades e documentos
        unidade_form = UnidadeForm()
        documento_form = DocumentoObraForm()

        context.update(
            {
                "titulo": f"Obra: {obra.nome}",
                "subtitulo": "Detalhes da obra",
                "unidades": unidades,
                "documentos": documentos,
                "unidade_form": unidade_form,
                "documento_form": documento_form,
            },
        )

        return context

    def post(
        self,
        request: HttpRequest,
        *args: object,
        **kwargs: object,
    ) -> HttpResponse:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Processar formulários de documentos."""
        self.object = self.get_object()
        obra = self.object

        documento_form = DocumentoObraForm(request.POST, request.FILES)
        if documento_form.is_valid():
            documento = documento_form.save(commit=False)
            documento.obra = obra
            documento.save()
            messages.success(request, f"Documento '{documento.descricao}' adicionado com sucesso!")
            return redirect("obras:obra_detail", pk=obra.pk)
        messages.error(request, "Erro ao adicionar o documento. Verifique os dados.")
        return self.get(request, *args, **kwargs)


class ObraDeleteView(UIPermissionsMixin, ObrasMixin, DeleteView):
    """View para exclusão de obras."""

    template_name = "obras/obras_confirm_delete.html"
    app_label = "obras"
    model_name = "obra"

    def get_success_url(self) -> str:
        """Retorna URL de redirecionamento após exclusão."""
        return reverse("obras:obras_list")

    def delete(
        self,
        request: HttpRequest,
        *args: object,
        **kwargs: object,
    ) -> HttpResponse:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Executa exclusão com mensagem de sucesso."""
        messages.success(request, "Obra excluída com sucesso!")
        return super().delete(request, *args, **kwargs)  # pyright: ignore[reportArgumentType]


# Views auxiliares para unidades e documentos
@login_required
def unidade_add(request: HttpRequest, obra_pk: int) -> HttpResponse:
    """Adicionar unidade a uma obra."""
    obra = get_object_or_404(Obra, pk=obra_pk)

    if request.method == "POST":
        form = UnidadeForm(request.POST)
        if form.is_valid():
            unidade = form.save(commit=False)
            unidade.obra = obra
            unidade.save()
            messages.success(request, f"Unidade '{unidade.identificador}' adicionada com sucesso!")
    else:
        messages.error(request, "Erro ao adicionar unidade.")

    return redirect("obras:obra_detail", pk=obra.pk)


@login_required
def unidade_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Excluir uma unidade."""
    unidade = get_object_or_404(Unidade, pk=pk)
    obra_pk = unidade.obra.pk

    if request.method == "POST":
        unidade.delete()
        messages.success(request, f"Unidade '{unidade.identificador}' excluída com sucesso!")

    return redirect("obras:obra_detail", pk=obra_pk)


@login_required
def documento_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Excluir um documento."""
    documento = get_object_or_404(DocumentoObra, pk=pk)
    obra_pk = documento.obra.pk

    if request.method == "POST":
        documento.delete()
        messages.success(request, f"Documento '{documento.descricao}' excluído com sucesso!")

    return redirect("obras:obra_detail", pk=obra_pk)


# Views para Modelos e geração em massa
@login_required
def modelo_unidade_create(request: HttpRequest, obra_pk: int) -> HttpResponse:
    """Criar novo modelo de unidade para uma obra."""
    obra = get_object_or_404(Obra, pk=obra_pk)
    if request.method == "POST":
        form = ModeloUnidadeForm(request.POST)
        if form.is_valid():
            modelo = form.save(commit=False)
            modelo.obra = obra
            modelo.save()
            messages.success(request, "Modelo criado com sucesso!")
            return redirect("obras:obra_detail", pk=obra.pk)
    else:
        form = ModeloUnidadeForm(initial={"obra": obra})

    context = {
        "form": form,
        "obra": obra,
    }
    return render(request, "obras/modelo_unidade_form.html", context)


@login_required
def gerar_unidades_em_massa(request: HttpRequest, obra_pk: int) -> HttpResponse:
    """Gerar unidades em massa para uma obra."""
    obra = get_object_or_404(Obra, pk=obra_pk)
    if request.method == "POST":
        form = GerarUnidadesEmMassaForm(request.POST, obra=obra)
        if form.is_valid():
            bloco = form.cleaned_data.get("bloco") or ""
            andar_inicial = form.cleaned_data["andar_inicial"]
            andar_final = form.cleaned_data["andar_final"]
            prefixo_numero = form.cleaned_data.get("prefixo_numero") or ""
            numeros = [n.strip() for n in form.cleaned_data["numeros_por_andar"].split(",") if n.strip()]
            modelo = form.cleaned_data["modelo"]

            created = 0
            with transaction.atomic():
                for andar in range(andar_inicial, andar_final + 1):
                    for sufixo in numeros:
                        numero = f"{andar}{sufixo}" if prefixo_numero == "" else f"{prefixo_numero}{sufixo}"
                        identificador = f"{numero}"
                        if bloco:
                            identificador = f"{bloco}-{identificador}"
                        if not Unidade.objects.filter(obra=obra, identificador=identificador).exists():
                            Unidade.objects.create(
                                obra=obra,
                                identificador=identificador,
                                tipo_unidade=modelo.tipo_unidade if hasattr(modelo, "tipo_unidade") else "apartamento",
                                area_m2=modelo.area_privativa,
                                modelo=modelo,
                                bloco=bloco or None,
                                andar=andar,
                                numero=numero,
                            )
                            created += 1
            messages.success(request, f"{created} unidades geradas com sucesso!")
            return redirect("obras:obra_detail", pk=obra.pk)
    else:
        form = GerarUnidadesEmMassaForm(obra=obra)

    context = {
        "form": form,
        "obra": obra,
    }
    return render(request, "obras/gerar_unidades_form.html", context)


# Views AJAX para funcionalidades adicionais
@login_required
def obra_search_ajax(request: HttpRequest) -> JsonResponse:
    """Busca AJAX para obras."""
    term = request.GET.get("term", "")
    tenant = get_current_tenant(request)

    obras_qs = Obra.objects.all()
    if tenant and hasattr(Obra, "tenant"):
        obras_qs = obras_qs.filter(tenant=tenant)

    if term:
        obras_qs = obras_qs.filter(Q(nome__icontains=term) | Q(endereco__icontains=term) | Q(cidade__icontains=term))

    results = [
        {
            "id": obra.id,
            "text": obra.nome,
            "endereco": f"{obra.endereco}, {obra.cidade}" if hasattr(obra, "endereco") else "",
        }
        for obra in obras_qs[:10]
    ]

    return JsonResponse({"results": results})


# Views funcionais (legacy - redirecionam para class-based views ou wizard)
def obra_list(request: HttpRequest) -> HttpResponse:
    """View funcional para listagem (legacy)."""
    return ObraListView.as_view()(request)


def obra_add(_request: HttpRequest) -> HttpResponse:
    """View funcional para criação (legacy) - redireciona ao wizard."""
    return redirect("obras:obra_wizard")


def obra_edit(_request: HttpRequest, pk: int) -> HttpResponse:
    """View funcional para edição (legacy) - redireciona ao wizard."""
    return redirect("obras:obra_wizard_edit", pk=pk)


def obra_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """View funcional para detalhes (legacy)."""
    return ObraDetailView.as_view()(request, pk=pk)


def obra_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """View funcional para exclusão (legacy)."""
    return ObraDeleteView.as_view()(request, pk=pk)
