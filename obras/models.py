"""Modelos para gerenciamento de obras, unidades e documentos.

Este módulo contém os modelos principais do sistema de obras:
- Obra: Representa uma obra de construção
- ModeloUnidade: Define tipos/plantas de unidades
- Unidade: Unidades individuais (apartamentos, salas, lotes, etc.)
- DocumentoObra: Documentos relacionados às obras
"""

from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from clientes.models import Cliente

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


def get_documento_upload_path(instance: "DocumentoObra", filename: str) -> str:
    """Define o caminho de upload dos documentos de forma organizada.

    Args:
        instance: Instância de DocumentoObra.
        filename: Nome do arquivo original.

    Returns:
        Caminho relativo onde o arquivo será salvo.

    """
    return f"obra_{instance.obra.id}/documentos/{filename}"


class Obra(models.Model):
    """Representa uma obra de construção civil.

    Gerencia informações sobre obras, incluindo dados de identificação,
    localização, prazos, valores, status e progresso.

    Attributes:
        nome: Nome identificador da obra.
        tipo_obra: Tipo de obra (construção, reforma, manutenção, etc.).
        cno: Cadastro Nacional de Obras (opcional).
        cliente: Cliente principal/contratante (opcional).
        endereco: Endereço completo da obra.
        status: Status atual da obra.
        progresso: Percentual de conclusão (0-100).

    """

    # Choices como ClassVar
    TIPO_OBRA_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("construcao", "Construção Nova"),
        ("reforma", "Reforma"),
        ("manutencao", "Manutenção"),
        ("ampliacao", "Ampliação"),
        ("demolicao", "Demolição"),
        ("loteamento", "Loteamento"),
    ]

    STATUS_OBRA_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("planejamento", "Planejamento"),
        ("em_andamento", "Em Andamento"),
        ("pausada", "Pausada"),
        ("concluida", "Concluída"),
        ("cancelada", "Cancelada"),
    ]

    # TYPE_CHECKING para managers
    if TYPE_CHECKING:
        modelos: "RelatedManager[ModeloUnidade]"
        unidades: "RelatedManager[Unidade]"
        documentos: "RelatedManager[DocumentoObra]"

    # --- Identificação e Tipo ---
    nome = models.CharField(max_length=200, verbose_name="Nome da Obra")
    tipo_obra = models.CharField(
        max_length=20,
        choices=TIPO_OBRA_CHOICES,
        default="construcao",
        verbose_name="Tipo de Obra",
    )
    cno = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="CNO (Cadastro Nacional de Obras)",
        help_text="Cadastro Nacional de Obras, se aplicável.",
        null=True,
        blank=True,
    )

    # --- Cliente Principal (Contratante) ---
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        related_name="obras_principais",
        verbose_name="Cliente Principal (Contratante)",
        help_text="Cliente principal ou contratante. Deixe em branco se for uma obra da própria construtora.",
        null=True,
        blank=True,
    )

    # --- Localização ---
    endereco = models.TextField(verbose_name="Endereço")
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = models.CharField(max_length=2, verbose_name="Estado")
    cep = models.CharField(max_length=10, verbose_name="CEP")

    # --- Prazos e Valores ---
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_previsao_termino = models.DateField(verbose_name="Previsão de Término")
    data_termino = models.DateField(null=True, blank=True, verbose_name="Data de Término Real")
    valor_contrato = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor do Contrato (Principal)")
    valor_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal(0),
        verbose_name="Custo Total Estimado da Obra",
    )

    # --- Status e Progresso ---
    status = models.CharField(
        max_length=20,
        choices=STATUS_OBRA_CHOICES,
        default="planejamento",
        verbose_name="Status da Obra",
    )
    progresso = models.PositiveSmallIntegerField(
        verbose_name="Progresso (%)",
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # --- Outras Informações ---
    observacoes = models.TextField(blank=True, default="", verbose_name="Observações Gerais")

    class Meta:
        """Metadados do modelo Obra."""

        verbose_name = "Obra"
        verbose_name_plural = "Obras"
        ordering = ["-data_inicio"]  # noqa: RUF012

    def __str__(self) -> str:
        """Retorna representação em string da obra."""
        return self.nome

    def get_absolute_url(self) -> str:
        """Retorna URL absoluta para visualização da obra."""
        return reverse("obras:obra_detail", args=[str(self.id)])


class ModeloUnidade(models.Model):
    """Modelo/planta de unidade para uma Obra (ex.: Tipo 01, 02, 03, 04).

    Define tipos padronizados de unidades que serão construídas,
    incluindo características como área, número de cômodos e preço sugerido.

    Attributes:
        obra: Obra à qual este modelo pertence.
        codigo: Código identificador do modelo (ex.: 01, 02, 03).
        nome: Nome descritivo do modelo.
        tipo_unidade: Tipo de unidade (apartamento, casa, lote, etc.).
        ambientes: Lista JSON de ambientes com nome e área.

    """

    # Choices como ClassVar
    TIPO_UNIDADE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("apartamento", "Apartamento"),
        ("sala_comercial", "Sala Comercial"),
        ("casa", "Casa"),
        ("lote", "Lote"),
        ("andar", "Andar Corporativo"),
        ("loja", "Loja"),
    ]

    # TYPE_CHECKING para managers
    if TYPE_CHECKING:
        unidades: "RelatedManager[Unidade]"

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="modelos", verbose_name="Obra")
    codigo = models.CharField(max_length=20, verbose_name="Código", help_text="Ex.: 01, 02, 03, 04")
    nome = models.CharField(max_length=100, verbose_name="Nome do Modelo", help_text="Ex.: Apto Tipo 01")
    tipo_unidade = models.CharField(
        max_length=20,
        choices=TIPO_UNIDADE_CHOICES,
        default="apartamento",
        verbose_name="Tipo",
    )
    dormitorios = models.PositiveSmallIntegerField(default=0, verbose_name="Dormitórios")
    suites = models.PositiveSmallIntegerField(default=0, verbose_name="Suítes")
    banheiros = models.PositiveSmallIntegerField(default=1, verbose_name="Banheiros")
    vagas = models.PositiveSmallIntegerField(default=0, verbose_name="Vagas de Garagem")
    area_privativa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Área Privativa (m²)",
    )
    area_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Área Total (m²)",
    )
    preco_sugerido = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Preço Sugerido",
    )
    ambientes = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Ambientes",
        help_text='Lista de ambientes com nome e área. Ex.: [{"nome":"Sala","area":20}]',
    )

    class Meta:
        """Metadados do modelo ModeloUnidade."""

        verbose_name = "Modelo de Unidade"
        verbose_name_plural = "Modelos de Unidade"
        unique_together = ("obra", "codigo")
        ordering = ["codigo"]  # noqa: RUF012

    def __str__(self) -> str:
        """Retorna representação em string do modelo de unidade."""
        return f"{self.codigo} - {self.nome}"

    def save(self, *args: object, **kwargs: object) -> None:
        """Salva o modelo de unidade, gerando código automaticamente se necessário.

        Args:
            *args: Argumentos posicionais para o save do Django.
            **kwargs: Argumentos nomeados para o save do Django.

        """
        if not self.codigo or not str(self.codigo).strip():
            self.codigo = self._generate_next_codigo()
        super().save(*args, **kwargs)  # pyright: ignore[reportArgumentType]

    def _generate_next_codigo(self) -> str:
        """Gera próximo código sequencial por obra.

        Usa zero-fill com largura mínima 2. Considera apenas códigos
        totalmente numéricos; se não houver, começa em 1.
        Garante unicidade incrementando até achar um livre.

        Returns:
            Próximo código disponível formatado com zeros à esquerda.

        """
        if not self.obra_id:
            return "01"

        existing = list(ModeloUnidade.objects.filter(obra_id=self.obra_id).values_list("codigo", flat=True))
        numeric_vals = []
        width = 2

        for c in existing:
            c_str = str(c).strip()
            if c_str.isdigit():
                numeric_vals.append(int(c_str))
                width = max(width, len(c_str))

        next_num = (max(numeric_vals) + 1) if numeric_vals else 1
        attempt = next_num

        while True:
            candidate = str(attempt).zfill(width)
            if not ModeloUnidade.objects.filter(obra_id=self.obra_id, codigo=candidate).exists():
                return candidate
            attempt += 1


class Unidade(models.Model):
    """Unidade individual dentro de uma obra (apartamento, sala, lote, etc.).

    Representa unidades específicas que podem ser vendidas ou reservadas,
    vinculadas a uma obra e opcionalmente a um modelo padrão.

    Attributes:
        obra: Obra à qual esta unidade pertence.
        modelo: Modelo de unidade utilizado (opcional).
        identificador: Código único identificador da unidade.
        cliente: Proprietário/comprador da unidade (opcional).
        status: Situação atual da unidade (disponível, reservado, vendido).

    """

    # Choices como ClassVar
    TIPO_UNIDADE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("apartamento", "Apartamento"),
        ("sala_comercial", "Sala Comercial"),
        ("casa", "Casa"),
        ("lote", "Lote"),
        ("andar", "Andar Corporativo"),
        ("loja", "Loja"),
    ]

    STATUS_UNIDADE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("disponivel", "Disponível"),
        ("reservado", "Reservado"),
        ("vendido", "Vendido"),
    ]

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="unidades", verbose_name="Obra")
    modelo = models.ForeignKey(
        "ModeloUnidade",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unidades",
        verbose_name="Modelo",
    )
    bloco = models.CharField(max_length=50, blank=True, default="", verbose_name="Bloco/Torre")
    andar = models.IntegerField(null=True, blank=True, verbose_name="Andar")
    numero = models.CharField(max_length=20, blank=True, default="", verbose_name="Número")
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        related_name="unidades_adquiridas",
        verbose_name="Cliente (Proprietário da Unidade)",
        null=True,
        blank=True,
    )
    identificador = models.CharField(
        max_length=100,
        verbose_name="Identificador da Unidade",
        help_text="Ex: Apartamento 101, Lote 15, Sala 302",
    )
    tipo_unidade = models.CharField(max_length=20, choices=TIPO_UNIDADE_CHOICES, verbose_name="Tipo de Unidade")
    area_m2 = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Área (m²)", null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_UNIDADE_CHOICES,
        default="disponivel",
        verbose_name="Status da Unidade",
    )

    class Meta:
        """Metadados do modelo Unidade."""

        verbose_name = "Unidade da Obra"
        verbose_name_plural = "Unidades da Obra"
        ordering = ["identificador"]  # noqa: RUF012
        unique_together = (("obra", "identificador"),)

    def __str__(self) -> str:
        """Retorna representação em string da unidade."""
        return f"{self.identificador} (Obra: {self.obra.nome})"


class DocumentoObra(models.Model):
    """Documento relacionado a uma obra.

    Armazena documentos importantes da obra como projetos, licenças,
    contratos, orçamentos, fotos de andamento, etc.

    Attributes:
        obra: Obra à qual este documento pertence.
        descricao: Descrição do documento.
        arquivo: Arquivo digital do documento.
        categoria: Categoria do documento (projeto, licença, contrato, etc.).
        data_upload: Data e hora do upload do documento.

    """

    # Choices como ClassVar
    CATEGORIA_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("projeto", "Projeto"),
        ("licenca", "Licença / Alvará"),
        ("contrato", "Contrato"),
        ("orcamento", "Orçamento"),
        ("memorial", "Memorial Descritivo"),
        ("foto", "Foto de Andamento"),
        ("outro", "Outro"),
    ]

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="documentos", verbose_name="Obra")
    descricao = models.CharField(max_length=255, verbose_name="Descrição do Documento")
    arquivo = models.FileField(upload_to=get_documento_upload_path, verbose_name="Arquivo")
    data_upload = models.DateTimeField(auto_now_add=True, verbose_name="Data de Upload")
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default="outro", verbose_name="Categoria")

    class Meta:
        """Metadados do modelo DocumentoObra."""

        verbose_name = "Documento da Obra"
        verbose_name_plural = "Documentos da Obra"
        ordering = ["-data_upload"]  # noqa: RUF012

    def __str__(self) -> str:
        """Retorna representação em string do documento."""
        return self.descricao
