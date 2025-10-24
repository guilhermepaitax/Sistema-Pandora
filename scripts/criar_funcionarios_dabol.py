"""Script para criar funcionários da Dabol Engenharia e Construções Ltda."""

# ruff: noqa: E402, T201, F841, BLE001

import os
import sys
import traceback
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Configurar path do Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pandora_erp.settings")

import django

django.setup()

from core.models import Tenant
from funcionarios.models import Funcionario

# Lista de nomes dos funcionários
FUNCIONARIOS = [
    "Adailton De Jesus Ribeiro Rodrigues",
    "Ademir Oviedo",
    "Adilson Santos",
    "Alex Bruno Silva Dos Santos",
    "Alex Felix Fernandes",
    "Alexandre Alves De Oliveira",
    "Alice Dias Ribeiro",
    "Andre Ribeiro Rosa",
    "Andreia Cristiani Alves De Lima",
    "Antonio De Oliveira Soares",
    "Arisma Arilus",
    "Arlindo Sandeski Camargo",
    "Auricelia Lima Sousa",
    "Bruno Cesar Cardozo",
    "Bruno Rodrigues",
    "Carlos Eduardo Vieira",
    "Carolayne Machado Koslovski",
    "Celia Araujo De Lima Gomes",
    "Celio Dos Santos",
    "Cezar Silverio",
    "Cicero Trajano De França",
    "Cleberson Geronimo",
    "Clebson Lacerda",
    "Cleiton De Jesus Pereira",
    "Crysthian Gabriel Lima Fernandes",
    "Daniel Jose Velasquez Zapata",
    "Darwin Rafael Torres Aponte",
    "Delsi Jose Peraro",
    "Denia Cruz Rodriguez",
    "Dickson Rodrigo Rocha",
    "Diogo Henrique Uez",
    "Douglas Leandro Tobias",
    "Edenilson Gaspar Alves",
    "Ederval Ribeiro Ferreira",
    "Edison De Andrade",
    "Edner Dervis",
    "Edson Afonso Da Silva",
    "Edson Da Silva Costa",
    "Edson Martins Lemos Nepomuceno",
    "Elenildo Almeida Costa",
    "Eli Cezar Do Nascimento",
    "Eli Terezinha Cordova De Lima",
    "Elizandra De Freitas Silverio",
    "Erivelto Da Maia Cunha",
    "Eronides De Oliveira Lima",
    "Fabio Barbosa",
    "Franceau Victor",
    "Francisco De Assis Rosa",
    "Francisco Goularte",
    "Gabriel Moreira Dos Santos",
    "Giovane Pedro De Andrade",
    "Halana Gabriella Da Costa Ribeiro",
    "Iaguba Sonco",
    "Isac Maciel Da Rosa",
    "Isadora Gomes Ribeiro",
    "Izael Alves De Assis",
    "Joao Clemente Brito De Souza",
    "Joao Paulo Da Cruz",
    "Joao Victor Pinheiro Rocha",
    "Joel Jhonatan Alves Pereira",
    "Joel Soares Santos Lira",
    "Jose Gabriel Martinez",
    "Jose Ribamar Costa",
    "Julenilson Tavares De Souza",
    "Juvelino Silva Dos Santos",
    "Kamilly Selbmann Carniel",
    "Keyson Rodrigo F Ferreira",
    "Leoclides Vitor Gehlen",
    "Leonildo Costa",
    "Lisiane Dos Santos Pinheiro Da Cruz",
    "Lucas Eduardo Pelison",
    "Luis Alves Paco Ribeiro",
    "Luiz Carlos Ribeiro Da Cruz",
    "Marcelo Bruno S Pereira Silva",
    "Marcia Aparecida Galon",
    "Marcia De Melo",
    "Marcio Gonzaga De Oliveira",
    "Marcos Lemes Cavalheiro",
    "Marcos Roberto Ribas",
    "Marinalva Ferreira Dos Santos De Jesus",
    "Maycon Douglas De Paiva",
    "Miguel Diodato De Oliveira",
    "Natan Alisson Aragon",
    "Nathalia Beatriz Oliveira Milanez",
    "Nilton Cesar Custodio",
    "Oscalino Moreira Proença",
    "Paulo De Lima Rosa",
    "Paulo Sergio Carvalho",
    "Pedro Donizeti Da Silva",
    "Reginaldo Dias Machado",
    "Riam Da Silva Ribeiro",
    "Riomar Luis Da Silva",
    "Robert Batista Da Silva",
    "Robson Rodrigo De Oliveira",
    "Rodrigo Araujo De Morais",
    "Romario Barbosa Da Silva",
    "Romildo Ferreira",
    "Rudy Bombale Figueroa",
    "Sidiney Deluca",
    "Thayna Thiane Ferri",
    "Valdecir Dos Santos",
    "Valdir Fernandes Dos Reis",
    "Valmyr Casseus",
    "Victor Inocencio Rodriguez Ruiz",
    "Vilmar Domingues Barbosa",
    "Wandson Alves De Oliveira",
    "Weliton Da Cunha",
    "Welleson Rodrigo De Freitas Arruda",
    "Yoarvis Josue Del Mar Valero",
    "Thais Sandy Ludvig",
    "Nivaldo Mattos Da Silva",
]


def gerar_cpf_ficticio(index: int) -> str:
    """Gera CPF fictício para testes."""
    # CPF no formato: 000.000.00X-YY onde X é o índice
    base = f"{index:09d}"
    return f"{base[:3]}.{base[3:6]}.{base[6:9]}-{index % 100:02d}"


def criar_funcionarios() -> None:
    """Cria os funcionários para o tenant Dabol."""
    try:
        # Buscar tenant Dabol
        tenant = Tenant.objects.get(name="Dabol Engenharia e Construções")
        print(f"✓ Tenant encontrado: {tenant.name}")

        # Data base de admissão (varia para simular admissões diferentes)
        data_base_admissao = date(2023, 1, 1)

        criados = 0
        ja_existentes = 0

        for index, nome in enumerate(FUNCIONARIOS, start=1):
            cpf = gerar_cpf_ficticio(index)

            # Verificar se já existe
            if Funcionario.objects.filter(tenant=tenant, cpf=cpf).exists():
                print(f"  ⚠ Funcionário já existe: {nome}")
                ja_existentes += 1
                continue

            # Criar funcionário
            funcionario = Funcionario.objects.create(
                tenant=tenant,
                nome_completo=nome,
                cpf=cpf,
                data_nascimento=date(1980, 1, 1) + timedelta(days=index * 30),  # Datas variadas
                sexo="M",  # Padrão (pode ser ajustado manualmente depois)
                data_admissao=data_base_admissao + timedelta(days=index * 7),  # Admissões espaçadas
                cargo="Operário",  # Cargo padrão
                salario_base=Decimal("1800.00"),  # Salário base padrão
                ativo=True,
                nacionalidade="Brasileira",
            )

            print(f"  ✓ Criado: {nome} (CPF: {cpf})")
            criados += 1

        print("\n" + "=" * 60)
        print("✓ Processo concluído!")
        print(f"  - Funcionários criados: {criados}")
        print(f"  - Já existentes: {ja_existentes}")
        print(f"  - Total na lista: {len(FUNCIONARIOS)}")
        print("=" * 60)

    except Tenant.DoesNotExist:
        print("❌ ERRO: Tenant 'Dabol Engenharia e Construções' não encontrado!")
        print("   Verifique se o nome está correto no banco de dados.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERRO: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("CRIAÇÃO DE FUNCIONÁRIOS - DABOL ENGENHARIA E CONSTRUÇÕES")
    print("=" * 60)
    criar_funcionarios()
