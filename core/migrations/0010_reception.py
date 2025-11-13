from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_hospitalization_avaliacao_nurse_nutri_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PatientExtra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cpf', models.CharField(blank=True, max_length=14, null=True, unique=True, verbose_name='CPF')),
                ('cns', models.CharField(blank=True, max_length=15, null=True, unique=True, verbose_name='CNS')),
                ('patient', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='extra', to='core.patient', verbose_name='Paciente')),
            ],
            options={
                'verbose_name': 'Dados Adicionais do Paciente',
                'verbose_name_plural': 'Dados Adicionais dos Pacientes',
            },
        ),
        migrations.CreateModel(
            name='ReceptionAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('origin_sector', models.CharField(default='Recepção', max_length=100, verbose_name='Setor de Origem')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='Observações')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='reception_attendances', to='core.patient', verbose_name='Paciente')),
            ],
            options={
                'verbose_name': 'Atendimento (Recepção)',
                'verbose_name_plural': 'Atendimentos (Recepção)',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReceptionQueueEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('destination_sector', models.CharField(max_length=100, verbose_name='Setor de Destino')),
                ('priority', models.CharField(choices=[('NORMAL', 'Normal'), ('PREFERENCIAL', 'Preferencial'), ('EMERGENCIA', 'Emergência')], default='NORMAL', max_length=15, verbose_name='Prioridade')),
                ('status', models.CharField(choices=[('AGUARDANDO', 'Aguardando'), ('CHAMADO', 'Chamado'), ('ENCAMINHADO', 'Encaminhado'), ('FINALIZADO', 'Finalizado')], default='AGUARDANDO', max_length=15, verbose_name='Status')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('called_at', models.DateTimeField(blank=True, null=True, verbose_name='Chamado em')),
                ('finished_at', models.DateTimeField(blank=True, null=True, verbose_name='Finalizado em')),
                ('attendance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='queue_entries', to='core.receptionattendance', verbose_name='Atendimento')),
            ],
            options={
                'verbose_name': 'Entrada de Fila (Recepção)',
                'verbose_name_plural': 'Fila de Espera (Recepção)',
                'ordering': ['created_at'],
            },
        ),
    ]

