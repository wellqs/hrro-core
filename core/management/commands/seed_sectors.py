from django.core.management.base import BaseCommand
from core.models import Sector


DEFAULT_SECTORS = [
    'Recepção',
    'NIR / Regulação',
    'Ambulatório',
    'Internação',
    'Pronto Atendimento / Urgência',
    'Centro Cirúrgico',
    'Exames',
    'Laboratório',
    'Imagem',
    'Farmácia / Almoxarifado',
    'Faturamento',
    'CCIH',
    'NSP (Segurança do Paciente)',
    'SESMT (Segurança do Trabalho)',
]


class Command(BaseCommand):
    help = 'Popula a tabela de Setores com uma lista padrão do hospital.'

    def handle(self, *args, **options):
        created = 0
        for name in DEFAULT_SECTORS:
            obj, was_created = Sector.objects.get_or_create(name=name)
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Setores verificados. Criados: {created}.'))

