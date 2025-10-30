import csv
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.models import Patient # Importa apenas o modelo Patient
import logging

logger = logging.getLogger(__name__)

# Função auxiliar para parsear apenas data (para data de nascimento)
def parse_date_flexible_patient(date_str):
    if not date_str: return None
    possible_formats = ["%d/%m/%Y", "%Y-%m-%d"] # Formatos comuns para data de nascimento
    for fmt in possible_formats:
        try:
            # Retorna o objeto date diretamente
            return datetime.strptime(date_str.strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    logger.warning(f"Não foi possível parsear a data de nascimento: '{date_str}'")
    return None

class Command(BaseCommand):
    help = 'Popula a tabela Patient com dados de pacientes únicos de um arquivo CSV de ocupação.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='O caminho para o arquivo CSV com os dados de ocupação.')
        parser.add_argument(
            '--encoding', type=str, default='utf-8-sig',
            help='Define a codificação do CSV (padrão: utf-8-sig). Tente latin-1 ou cp1252 se falhar.'
        )
        parser.add_argument(
            '--delimiter', type=str, default=',',
            help='Define o delimitador do CSV (padrão: ","). Tente ";" se falhar.'
        )
        # Opcional: Argumento para limpar pacientes (CUIDADO!)
        parser.add_argument(
            '--clear-patients', action='store_true',
            help='Limpa TODOS os pacientes existentes (exceto superusers) antes de popular. Use com MUITO CUIDADO!',
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        encoding = options['encoding']
        delimiter = options['delimiter']

        if options['clear_patients']:
            confirmation = input(self.style.WARNING(
                "ATENÇÃO! Tem certeza que deseja deletar TODOS os pacientes (exceto superusers)? Digite 'sim': "
            ))
            if confirmation.lower() == 'sim':
                self.stdout.write(self.style.WARNING('Limpando pacientes...'))
                # Cuidado para não deletar usuários administradores se Patient estivesse ligado a User
                Patient.objects.all().delete() # Assuming Patient is separate
                self.stdout.write(self.style.SUCCESS('Pacientes limpos.'))
            else:
                self.stdout.write(self.style.ERROR('Operação cancelada.'))
                return

        self.stdout.write(self.style.WARNING(f'Importando pacientes de: {csv_file_path} (Encoding: {encoding}, Delimiter: "{delimiter}")'))

        created_count = 0
        skipped_count = 0
        error_count = 0
        processed_prontuarios = set() # Para garantir a unicidade no processamento do arquivo

        try:
            with open(csv_file_path, mode='r', encoding=encoding, newline='') as file:
                reader = csv.DictReader(file, delimiter=delimiter)

                # Colunas essenciais para criar o paciente
                required_cols = ['PRONTUÁRIO', 'PACIENTE']
                if not reader.fieldnames:
                     raise CommandError("Erro: Cabeçalho não encontrado ou arquivo vazio.")

                cleaned_fieldnames = {fn.strip().upper(): fn for fn in reader.fieldnames}

                missing = [col for col in required_cols if col not in cleaned_fieldnames]
                if missing:
                    raise CommandError(f"Erro: Colunas obrigatórias para pacientes não encontradas: {', '.join(missing)}")

                for row_num, row_data in enumerate(reader, start=2):
                    def get_value(col_name):
                        return row_data.get(cleaned_fieldnames.get(col_name.upper()), '').strip()

                    prontuario = get_value('PRONTUÁRIO')
                    nome_paciente = get_value('PACIENTE')

                    if not prontuario or not nome_paciente:
                        self.stdout.write(self.style.NOTICE(f"Linha {row_num}: PRONTUÁRIO e PACIENTE são necessários. Ignorada para cadastro de paciente."))
                        # Não incrementa erro aqui, pois a linha pode ser válida para internação
                        continue

                    # Se já processamos este prontuário neste arquivo, pula
                    if prontuario in processed_prontuarios:
                        continue
                    processed_prontuarios.add(prontuario)

                    # Tenta buscar ou criar o paciente
                    try:
                        # Busca por prontuário
                        patient, created = Patient.objects.get_or_create(
                            medical_record_number=prontuario,
                            defaults={
                                'name': nome_paciente,
                                # Adiciona outros campos se disponíveis no CSV e no modelo
                                'date_of_birth': parse_date_flexible_patient(get_value('DATA DE NASCIMENTO')), # Ajuste o nome da coluna se necessário
                                #'cns': get_value('CNS'),
                                #'gender': get_value('SEXO'), # Precisa tratar M/F/O
                                #'alergia_latex': parse_boolean(get_value('ALERGIA A LÁTEX')),
                            }
                        )

                        if created:
                            self.stdout.write(f"  Paciente CRIADO: Prontuário {prontuario} - {nome_paciente}")
                            created_count += 1
                        else:
                            # Opcional: Atualizar o nome se encontrado?
                            # if patient.name != nome_paciente:
                            #     patient.name = nome_paciente
                            #     patient.save()
                            #     self.stdout.write(f"  Paciente ATUALIZADO (nome): Prontuário {prontuario} - {nome_paciente}")
                            skipped_count += 1 # Conta como pulado se não foi criado

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Linha {row_num}: Erro ao criar/buscar paciente prontuário {prontuario}: {e}. Ignorada."))
                        error_count += 1

        except FileNotFoundError: raise CommandError(f'Erro: Arquivo "{csv_file_path}" não encontrado.')
        except CommandError as e: self.stdout.write(self.style.ERROR(str(e)))
        except Exception as e: raise CommandError(f'Erro inesperado ao ler CSV: {e}')

        self.stdout.write(self.style.SUCCESS(f'\nImportação de pacientes concluída! {created_count} criados, {skipped_count} já existentes, {error_count} erros.'))