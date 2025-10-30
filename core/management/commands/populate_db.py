import random
from datetime import timedelta, datetime
import calendar

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User
from django.utils import timezone
from faker import Faker

from core.models import Surgery, Sector, Indicator

# --- DICIONÁRIO ATUALIZADO
INDICATORS_DATA = {
    'AMBULATÓRIO': [
        'NÚMERO TOTAL DE ATENDIMENTOS',
    ],
    'C.C (CENTRO CIRÚRGICO)': [
        'NÚMERO DE CIRURGIAS REALIZADAS POR DIA',
        'NÚMERO DE ÓBITOS OPERATÓRIOS',
        'NÚMERO DE CIRURGIAS LIMPAS REALIZADA',
        'NÚMERO DE CIRURGIAS INFECTADAS REALIZADAS',
        'NÚMERO TOTAL DE CIRURGIAS CANCELADAS OU NÃO REALIZADAS',
        'NÚMERO DE CIRURGIAS CANCELADAS POR MOTIVOS RELACIONADOS AO PACIENTE',
        'NÚMERO DE CIRURGIAS CANCELADAS POR MOTIVOS NÃO RELACIONADOS AO PACIENTE',
        'NÚMERO DE PACIENTES COM RETORNO NÃO PLANEJADO À SALA CIRÚRGICA',
        'NÚMERO DE CIRURGIAS ELETIVAS REALIZADAS',
        'NÚMERO DE CIRURGIAS EM QUE A LISTA DE VERIFICAÇÃO DE CIRURGIA SEGURA FOI UTILIZADA',
        'NÚMERO DE CHECK LIST DE CIRURGIA SEGURA PREENCHIDO EM CONFORMIDADE',
    ],
    'EPIDEMIOLOGIA': [
        'NÚMERO TOTAL DE ÓBITOS',
    ],
    'FARMÁCIA': [
        'NÚMERO DE PRESCRIÇÕES MÉDICAS AVALIADAS NO MÊS',
        'NÚMERO DE PRESCRIÇÕES COM ERRO DE PRESCRIÇÃO DE MEDICAMENTO',
        'NÚMERO DE PRESCRIções PREENCHIDAS ELETRONICAMENTE OU DIGITALIZADAS',
        'NÚMERO DE MEDICAMENTOS DE ALTA VIGILÂNCIA PRESCRITOS',
    ],
    'FATURAMENTO': [
        'TOTAL DE LEITOS CADASTRADOS',
        'NÚMERO DE PRONTUÁRIOS AVALIADOS NO MÊS',
        'NÚMERO DE PRONTUÁRIOS EM CONFORMIDADE',
        'NÚMERO DE PRONTUÁRIOS COM EVOLUÇÃO MÉDICA',
        'NÚMERO DE PRONTUÁRIOS COM ESCALAS (GLASGOW, RASS, RAMSAY, BRADEN, MORSE, DOR, FUGULIN)',
        'NÚMERO DE PRONTUÁRIOS COM EVOLUÇÃO DE ENFERMAGEM',
    ],
    'LABORATÓRIO': [
        'NÚMERO DE EXAMES LABORATORIAIS REALIZADOS',
    ],
    'NEP (NÚCLEO DE EDUCAÇÃO PERMANENTE)': [
        'NÚMERO DE TREINAMENTO REALIZADO NA INSTITUIÇÃO NO PERÍODO',
        'NÚMERO DE SERVIDORES CAPACITADOS NO PERÍODO',
    ],
    'NIR (NÚCLEO INTERNO DE REGULAÇÃO)': [
        'MÉDIA DE PERMANÊNCIA',
        'NÚMERO TOTAL DE LEITOS OCUPADOS',
        'NÚMERO DE EVASÕES',
        'NÚMERO DE CIRURGIAS AGENDADAS',
        'NÚMERO DE LEITOS DESOCUPADO',
        'NÚMERO TOTAL DE INTERNAÇÃO DIA',
        'NÚMERO DE INTERNAÇÃO DIA NA ORTOPEDIA',
        'NÚMERO DE INTERNAÇÃO NA CIRURGIA GERAL',
        'NÚMERO DE PACIENTES - DIA NA UNIDADE',
        'NÚMERO DE SAÍDAS TOTAL (ALTA + ÓBITO + TRANSFERÊNCIA)',
    ],
    'NSP (NÚCLEO DE SEGURANÇA DO PACIENTE)': [
        'NÚMERO DE EVENTOS ADVERSOS NOTIFICADOS AO NÚCLEO DE SEGURANÇA DO PACIENTE',
        'NÚMERO DE EVENTO ADVERSOS NOTIFICADOS NO SISTEMA NOTIVISA',
        'TOTAL DE PACIENTES AVALIADOS QUANTO A IDENTIFICAÇÃO CORRETA',
    ],
    'RAIO X': [
        'NÚMERO DE EXAMES DE IMAGENS REALIZADOS',
        'NÚMERO DE EXAMES AGENDADOS',
    ],
    'RECEPÇÃO': [
        'NÚMERO DE PACIENTES COM PULSEIRA DE IDENTIFICAÇÃO PADRONIZADA',
    ],
    'RH (RECURSOS HUMANOS)': [
        'NÚMERO TOTAL DE PROFISSIONAIS NA INSTITUIÇÃO',
    ],
    'SCIH (SERVIÇO DE CONTROLE DE INFECÇÃO HOSPITALAR)': [
        'NÚMERO DE INFECÇÃO EM SÍTIO CIRÚRGICO NO PERÍODO',
    ],
    'SEM RESPONSÁVEL DEFINIDO (STATUS SUSPENSO)': [
        'TAXA DE CIRURGIAS SUSPENSA POR MOTIVOS RELACIONADOS AO PACIENTE',
        'TAXA DE CIRURGIA SUSPENSA POR MOTIVOS NÃO RELACIONADOS AO PACIENTE',
        'TAXA DE CONFORMIDADE EM PREENCHIMENTO DE PRONTUÁRIOS',
        'TAXA GERAL DE SUSPENSÃO DE CIRURGIAS',
        'TAXA DE CONFORMIDADE NA IDENTIFICAÇÃO DO PACIENTE',
        'TAXA DE CONFORMIDADE DO CHECK LIST DE CIRURGIA SEGURA',
    ],
    'ENFERMAGEM': [
        'QUANTIDADE DE PACIENTE COM AVALIAÇÃO DE RISCO DE QUEDA',
        'QUANTIDADE DE PACIENTE COM AVALIAÇÃO DE RISCO DE LESÃO POR PRESSÃO',
    ],
    'COMISSÃO DE CURATIVO': [
        'QUANTIDADE DE PACIENTE APRESENTANDO SINAIS DE INFECÇÃO NA FERIDA OPERATÓRIA',
        'QUANTIDADE DE PACIENTES COM CURATIVO DE PREVENÇÃO DE LESÃO',
    ],
}

class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de teste para Cirurgias, Setores e Indicadores.'

    def add_arguments(self, parser):
        parser.add_argument('--number', type=int, default=0, help='Define o número de cirurgias a serem criadas.')
        parser.add_argument('--clear-surgeries', action='store_true', help='Limpa a tabela de cirurgias antes de popular.')
        parser.add_argument('--populate-indicators', action='store_true', help='Popula Setores, Grupos e Indicadores.')
        parser.add_argument('--clear-indicators', action='store_true', help='Limpa Setores, Grupos e Indicadores.')

    def handle(self, *args, **options):

        if options['clear_indicators']:
            Indicator.objects.all().delete()
            Sector.objects.all().delete()

            Group.objects.filter(name__in=INDICATORS_DATA.keys()).delete()

            Group.objects.filter(name__in=[
                'C.C (Centro Cirúrgico)', 'NEP (Núcleo de Educação Permanente)',
                'NIR (Núcleo Interno de Regulação)', 'NSP (Núcleo de Segurança do Paciente)',
                'RH (Recursos Humanos)', 'SCIH (Serviço de Controle de Infecção Hospitalar)',
                'Sem Responsável Definido (Status Suspenso)', 'Enfermagem', 'Comissão de Curativo' # Inclui os novos caso já existissem
            ]).delete()
            self.stdout.write(self.style.SUCCESS('Setores, Indicadores e Grupos associados (antigos e novos) foram removidos.'))

        if options['populate_indicators']:
            self.stdout.write(self.style.WARNING('Iniciando a população de Setores (MAIÚSCULAS), Grupos e Indicadores...'))
            for sector_name, indicators_list in INDICATORS_DATA.items():

                sector, sector_created = Sector.objects.update_or_create(
                    name=sector_name.upper(), # Salva o nome em maiúsculas
                    defaults={'name': sector_name.upper()} # Garante que o nome seja maiúsculo ao criar
                )
                if sector_created: self.stdout.write(f'  Setor criado: {sector.name}')
                else: self.stdout.write(f'  Setor "{sector.name}" encontrado/atualizado.')

                # Cria grupo com nome maiúsculo
                group, group_created = Group.objects.get_or_create(name=sector_name.upper())
                if group_created: self.stdout.write(f'    -> Grupo de permissão "{group.name}" criado.')

                # Associa o setor ao grupo
                if not sector.group or sector.group != group:
                    sector.group = group
                    sector.save()
                    self.stdout.write(f'    -> Setor "{sector.name}" associado ao grupo "{group.name}".')

                # Cria os indicadores
                for indicator_name in indicators_list:
                    Indicator.objects.get_or_create(sector=sector, name=indicator_name)
            self.stdout.write(self.style.SUCCESS('População de Indicadores (MAIÚSCULAS) concluída!'))

        # Lógica para Cirurgias (permanece a mesma)
        number_of_surgeries = options['number']
        if number_of_surgeries > 0:
            # ... (código de criação de cirurgias omitido para brevidade) ...
            pass # Mantenha seu código de criação de cirurgias aqui