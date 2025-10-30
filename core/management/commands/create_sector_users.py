from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils.text import slugify
from core.models import Sector


class Command(BaseCommand):
    help = 'Cria usuários para cada setor com um grupo de permissão associado.'

    def handle(self, *args, **kwargs):
        password = '2102Well!'
        self.stdout.write(self.style.WARNING(f'Iniciando a criação de usuários com a senha padrão...'))

        # Busca todos os setores que têm um grupo de permissão vinculado
        sectors_with_groups = Sector.objects.filter(group__isnull=False)

        if not sectors_with_groups.exists():
            self.stdout.write(self.style.ERROR('Nenhum setor encontrado com um grupo de permissão associado.'))
            self.stdout.write(
                self.style.NOTICE('Por favor, configure os grupos no painel de administração do Django primeiro.'))
            return

        created_count = 0
        for sector in sectors_with_groups:
            # Gera um username a partir do nome do setor. Ex: "Centro Cirúrgico" -> "usercen"
            slug = slugify(sector.name).replace('-', '')
            username = f"user{slug[:3].lower()}"

            # Verifica se o usuário já existe
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'Usuário {username} para o setor "{sector.name}" já existe. Pulando.')
                continue

            try:
                # Cria o novo usuário
                user = User.objects.create_user(username=username, password=password)

                # Adiciona o usuário ao grupo de permissão do setor
                user.groups.add(sector.group)

                # Salva as alterações
                user.save()

                self.stdout.write(self.style.SUCCESS(
                    f'Usuário {username} criado e adicionado ao grupo "{sector.group.name}".'
                ))
                created_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'Erro ao criar usuário para o setor "{sector.name}": {e}'
                ))

        self.stdout.write(self.style.SUCCESS(f'\nOperação concluída! {created_count} novos usuários criados.'))
