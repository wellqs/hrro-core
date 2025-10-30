import re
from django.core.management.base import BaseCommand
from core.models import Bed

# A lista de leitos fornecida, formatada para facilitar o processamento
BED_LIST = """
LEITOCLÍNICA A
A 1 / 1
A 1 / 2
A 1 / 3
A 1 / 4
A 1 / 5
A 1 / 6
A 1 / 7
A 1 / 8
A 1 / 9
A 1 / 10
A 1 / 11
A 1 / 12
A 1 / 13
EXTENSÃO
A 2 / 14
A 2 / 15
A 2 / 16
A 2 / 17
CLÍNICA A - INFECTADOS
A 3 / 18
A 4 / 19
A 5 / 20
A 6 / 21
A 7 / 22
A 7 / 23
A 7 / 24
A 7 / 25
A 8 / 26
A 8 / 27
A 8 / 28
A 8 / 29
A 9 / 30
A 9 / 31
A 10 / 32
A 10 / 33
A 11 / 34
A 11 / 35
A 12 / 36
A 12 / 37
A 12 / 38
CLÍNICA B - INFECTADO
B 13 / 39
B 13 / 40
B 13 / 41
B 13 / 42
B 14 / 43
B 14 / 44
B 14 / 45
B 14 / 46
B 15 / 47
B 15 / 48
B 15 / 49
B 15 / 50
B 16 / 51
B 16 / 52
B 16 / 53
B 16 / 54
B 16 / 55
B 17 / 56
B 17 / 57
B 17 / 58
B 17 / 59
B 17 / 60
B 18 / 61
B 18 / 62
B 18 / 63
B 18 / 64
B 19 / 65
B 19 / 66
B 19 / 67
B 19 / 68
B 20 / 69
B 20 / 70
B 21 / 71
B 21 / 72
B 21 / 73
B 22 / 74
B 22 / 75
B 23 / 76
B 23 / 77
B 23 / 78
CLÍNICA C
C 24 / 79
C 24 / 80
C 24 / 81
C 24 / 82
C 25 / 83
C 25 / 84
C 25 / 85
C 25 / 86
C 26 / 87
C 26 / 88
C 26 / 89
C 26 / 90
C 26 / 91
C 27 / 92
C 27 / 93
C 27 / 94
C 27 / 95
C 27 / 96
C 28 / 97
C 28 / 98
C 28 / 99
C 28 / 100
C 29 / 101
C 29 / 102
C 29 / 103
C 29 / 104
C 30 / 105
C 30 / 106
C 30 / 107
C 30 / 108
C 31 / 109
C 31 / 110
C 31 / 111
C 31 / 112
C 31 / 113
C 31 / 114
C 32 / 115
C 32 / 116
C 32 / 117
C 32 / 118
C 32 / 119
C 32 / 120
C 32 / 121
C 32 / 122
C 32 / 123
C 32 / 124
C 32 / 125
919.109 EXTRA
"""

class Command(BaseCommand):
    help = 'Popula o banco de dados com a lista fixa de leitos do hospital.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpa a tabela de leitos antes de popular.',
        )

    # --- MÉTODO HANDLE CORRIGIDO ---
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Limpando a tabela de leitos...'))
            Bed.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Tabela de leitos limpa.'))

        self.stdout.write(self.style.WARNING('Iniciando a população da tabela de leitos...'))

        current_clinic = None
        current_category = Bed.CATEGORY_CHOICES[0][0] # Default 'NORMAL'
        created_count = 0
        skipped_count = 0

        # Processa cada linha da lista
        for line in BED_LIST.strip().split('\n'):
            line = line.strip()
            identifier = None # Reset identifier for each line initially

            if not line:
                continue

            # Prioriza a verificação das linhas de definição de clínica/categoria
            if line.startswith('LEITOCLÍNICA A'): # Trata a primeira linha
                current_clinic = 'CLÍNICA A'
                current_category = 'NORMAL'
                continue # Pula para a próxima linha após definir a clínica
            elif line.startswith('CLÍNICA A - INFECTADOS'): # Trata a linha específica
                current_clinic = 'CLÍNICA A'
                current_category = 'INFECTADO'
                continue
            elif line.startswith('CLÍNICA A'): # Trata CLÍNICA A (caso haja sem INFECTADOS depois)
                current_clinic = 'CLÍNICA A'
                current_category = 'NORMAL'
                continue
            elif line.startswith('CLÍNICA B - INFECTADO'): # Trata a linha específica
                current_clinic = 'CLÍNICA B'
                current_category = 'INFECTADO'
                continue
            elif line.startswith('CLÍNICA B'): # Trata CLÍNICA B (caso haja sem INFECTADO depois)
                current_clinic = 'CLÍNICA B'
                current_category = 'NORMAL'
                continue
            elif line.startswith('CLÍNICA C'):
                current_clinic = 'CLÍNICA C'
                current_category = 'NORMAL'
                continue
            elif line == 'EXTENSÃO':
                current_category = 'EXTENSAO'
                # Assume que a clínica A é a atual baseado na ordem da lista
                if current_clinic == 'CLÍNICA A':
                     pass # Mantém a clínica atual
                continue
            elif line == '919.109 EXTRA':
                identifier = line
                current_clinic = 'EXTRA' # Define uma clínica específica ou 'N/A'
                current_category = 'EXTRA'
            elif '/' in line and current_clinic: # Garante que só processa linhas de leito se uma clínica já foi definida
                 identifier = line

            # Se for um identificador de leito válido E já tivermos uma clínica definida
            if identifier and current_clinic:
                try:
                    bed, created = Bed.objects.get_or_create(
                        identifier=identifier,
                        defaults={
                            'clinic': current_clinic,
                            'category': current_category,
                            'is_active': True
                        }
                    )

                    if created:
                        self.stdout.write(f'  Leito criado: {identifier} (Clínica: {current_clinic}, Categoria: {current_category})')
                        created_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Erro ao processar linha '{line}': {e}"))
            # Opcional: Adicionar um else aqui para avisar sobre linhas não processadas, se necessário


        self.stdout.write