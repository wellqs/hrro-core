import csv
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
# Assume que os modelos já foram atualizados com os novos campos
from core.models import Bed, Patient, Hospitalization
import logging

logger = logging.getLogger(__name__)

# Funções auxiliares (parse_datetime_flexible, parse_date_flexible) - Mantidas iguais
def parse_datetime_flexible(date_str):
    if not date_str: return None
    possible_formats = ["%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for fmt in possible_formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt) # Adicionado strip()
            return timezone.make_aware(dt, timezone.get_current_timezone())
        except (ValueError, TypeError): continue
    logger.warning(f"Não foi possível parsear a data/hora: '{date_str}'")
    return None

def parse_date_flexible(date_str):
     if not date_str: return None
     dt = parse_datetime_flexible(date_str) # Reutiliza a função de datetime
     return dt.date() if dt else None

# Função auxiliar para converter Sim/Não para Booleano
def parse_boolean(bool_str):
    if not bool_str:
        return None
    val = bool_str.strip().lower()
    if val in ['sim', 's', 'true', 't', '1', 'yes', 'y']:
        return True
    if val in ['não', 'nao', 'n', 'false', 'f', '0', 'no']:
        return False
    logger.warning(f"Não foi possível parsear o valor booleano: '{bool_str}'")
    return None # Ou False como padrão?

class Command(BaseCommand):
    help = 'Popula a tabela de Hospitalization com dados de um arquivo CSV, mapeando colunas específicas.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='O caminho para o arquivo CSV com os dados de ocupação.')
        parser.add_argument('--clear', action='store_true', help='Limpa TODAS as internações existentes antes de popular (Use com CUIDADO!).')
        parser.add_argument('--encoding', type=str, default='utf-8-sig', help='Define a codificação do CSV (padrão: utf-8-sig para tratar BOM). Tente latin-1 ou cp1252 se falhar.')
        parser.add_argument('--delimiter', type=str, default=',', help='Define o delimitador do CSV (padrão: ","). Tente ";" se falhar.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        encoding = options['encoding']
        delimiter = options['delimiter']

        if options['clear']:
            # ... (código de limpeza) ...
            confirmation = input(self.style.WARNING(
                "ATENÇÃO! Tem certeza que deseja deletar TODAS as internações existentes? Digite 'sim': "
            ))
            if confirmation.lower() == 'sim':
                self.stdout.write(self.style.WARNING('Limpando internações...'))
                Hospitalization.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('Internações limpas.'))
            else:
                self.stdout.write(self.style.ERROR('Operação cancelada.'))
                return

        self.stdout.write(self.style.WARNING(f'Importando de: {csv_file_path} (Encoding: {encoding}, Delimiter: "{delimiter}")'))

        created_count = 0
        updated_count = 0
        error_count = 0

        try:
            with open(csv_file_path, mode='r', encoding=encoding, newline='') as file:
                reader = csv.DictReader(file, delimiter=delimiter)

                required_cols = ['LEITO', 'PRONTUÁRIO', 'DATA DE ADMISSÃO'] # Mantenha apenas os essenciais aqui
                if not reader.fieldnames:
                     raise CommandError("Erro: Cabeçalho não encontrado ou arquivo vazio.")

                cleaned_fieldnames = {fn.strip().upper(): fn for fn in reader.fieldnames} # Mapeamento limpo

                # Verifica se as colunas obrigatórias existem no mapeamento
                missing = [col for col in required_cols if col not in cleaned_fieldnames]
                if missing:
                    raise CommandError(f"Erro: Colunas obrigatórias não encontradas: {', '.join(missing)}")

                for row_num, row_data in enumerate(reader, start=2):
                    # Função auxiliar para pegar valor usando o mapeamento limpo
                    def get_value(col_name):
                        return row_data.get(cleaned_fieldnames.get(col_name.upper()), '').strip()

                    leito_id = get_value('LEITO')
                    prontuario = get_value('PRONTUÁRIO')
                    data_adm_str = get_value('DATA DE ADMISSÃO')
                    data_alta_str = get_value('DATA ALTA/OBITO')

                    if not leito_id or not prontuario or not data_adm_str:
                        self.stdout.write(self.style.ERROR(f"Linha {row_num}: LEITO, PRONTUÁRIO e DATA DE ADMISSÃO são obrigatórios. Ignorada."))
                        error_count += 1; continue

                    # --- Busca Leito e Paciente ---
                    try: bed = Bed.objects.get(identifier=leito_id)
                    except Bed.DoesNotExist: self.stdout.write(self.style.ERROR(f"Linha {row_num}: Leito '{leito_id}' não encontrado. Ignorada.")); error_count += 1; continue
                    try: patient = Patient.objects.get(medical_record_number=prontuario)
                    except Patient.DoesNotExist: self.stdout.write(self.style.ERROR(f"Linha {row_num}: Paciente prontuário '{prontuario}' não encontrado. Ignorada.")); error_count += 1; continue
                    except Patient.MultipleObjectsReturned: self.stdout.write(self.style.ERROR(f"Linha {row_num}: Múltiplos pacientes com prontuário '{prontuario}'. Ignorada.")); error_count += 1; continue

                    # --- Processa Datas ---
                    admission_datetime = parse_datetime_flexible(data_adm_str)
                    if not admission_datetime: self.stdout.write(self.style.ERROR(f"Linha {row_num}: Data de Admissão inválida ('{data_adm_str}'). Ignorada.")); error_count += 1; continue
                    discharge_datetime = parse_datetime_flexible(data_alta_str)
                    expected_surgery_dt = parse_date_flexible(get_value('PREVISÃO DE ALTA/CIRURGIA'))

                    # --- Concatena Observações ---
                    obs_geral = get_value('OBSERVAÇÃO GERAL')
                    obs_nir = get_value('OBSERVAÇÃO NIR')
                    all_notes = []
                    if obs_geral: all_notes.append(f"Geral: {obs_geral}")
                    if obs_nir: all_notes.append(f"NIR: {obs_nir}")
                    notes_concatenated = "\n".join(all_notes) if all_notes else None

                    # --- Mapeamento Completo para 'defaults' ---
                    defaults = {
                        'bed': bed,
                        'discharge_date': discharge_datetime,
                        'procedure_planned': get_value('PROCEDIMENTO') or None,
                        'current_status': get_value('STATUS CIRURGICO') or None,
                        'expected_surgery_date': expected_surgery_dt,
                        'notes': notes_concatenated, # Observações concatenadas

                        # Novos campos mapeados (ajuste os nomes dos campos do MODELO se forem diferentes)
                        'numero_atendimento': get_value('Nº DO AT') or None, # Assumindo 'numero_atendimento' no modelo
                        'hipotese_diagnostica': get_value('HIPÓTESE DIAGNÓSTICA') or None, # Assumindo 'hipotese_diagnostica'
                        'convenio': get_value('CONVÊNIO') or None, # Assumindo 'convenio'
                        'exames_pendentes': get_value('EXAMES PENDENTES') or None, # Assumindo 'exames_pendentes' (TextField?)
                        'parecer_especialidade': get_value('PARECER DE ESPECIALIDADE') or None, # Assumindo 'parecer_especialidade' (TextField?)
                        'avaliacao_nurse_nutri': get_value('AVALIAÇÃO NURSE/NUTRI') or None, # Assumindo 'avaliacao_nurse_nutri' (TextField?)
                        'necessidade_isolamento': get_value('NECESSIDADE DE ISOLAMENTO') or None, # Assumindo 'necessidade_isolamento' (CharField?)
                        'precaucoes_especificas': get_value('PRECAUÇÕES ESPECÍFICAS') or None, # Assumindo 'precaucoes_especificas' (TextField?)
                        'risco_cirurgico_alto': parse_boolean(get_value('RISCO CIRÚRGICO ALTO')), # Assumindo 'risco_cirurgico_alto' (BooleanField)
                        'nome_cirurgiao': get_value('NOME CIRURGIÃO') or None, # Assumindo 'nome_cirurgiao' (CharField?)
                        'opme_necessario': parse_boolean(get_value('OPME NECESSÁRIO')), # Assumindo 'opme_necessario' (BooleanField)
                        'avaliacao_social': get_value('AVALIAÇÃO SOCIAL') or None, # Assumindo 'avaliacao_social' (TextField ou Boolean?)
                        'internacao_prolongada': parse_boolean(get_value('INTERNAÇÃO PROLONGADA')), # Assumindo 'internacao_prolongada' (BooleanField)

                        # Campos do Paciente (NÃO atualizamos aqui, apenas usamos o paciente encontrado)
                        # 'patient.cns': get_value('CNS'), <-- NÃO FAZER AQUI
                        # 'patient.nome_social': get_value('NOME SOCIAL'), <-- NÃO FAZER AQUI
                        # 'patient.sexo': get_value('SEXO'), <-- NÃO FAZER AQUI
                        # 'patient.alergia_latex': parse_boolean(get_value('ALERGIA A LÁTEX')), <-- NÃO FAZER AQUI
                    }

                    try:
                        hospitalization, created = Hospitalization.objects.update_or_create(
                            patient=patient, admission_date=admission_datetime, # Chave composta
                            defaults=defaults
                        )
                        if created: created_count += 1
                        else: updated_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Linha {row_num}: Erro ao salvar internação para prontuário {prontuario}: {e}. Ignorada."))
                        error_count += 1

        except FileNotFoundError: raise CommandError(f'Erro: Arquivo "{csv_file_path}" não encontrado.')
        except CommandError as e: self.stdout.write(self.style.ERROR(str(e)))
        except Exception as e: raise CommandError(f'Erro inesperado ao ler CSV (verifique encoding/delimiter): {e}')

        self.stdout.write(self.style.SUCCESS(f'\nImportação concluída! {created_count} criadas, {updated_count} atualizadas, {error_count} erros.'))