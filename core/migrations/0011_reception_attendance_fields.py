from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_reception'),
    ]

    operations = [
        migrations.AddField(
            model_name='receptionattendance',
            name='care_type',
            field=models.CharField(choices=[('AMBULATORIO', 'Ambulatório'), ('URGENCIA', 'Urgência'), ('INTERNACAO', 'Internação'), ('EXAME', 'Exame'), ('OUTRO', 'Outro')], default='AMBULATORIO', max_length=20, verbose_name='Tipo de atendimento'),
        ),
        migrations.AddField(
            model_name='receptionattendance',
            name='origin',
            field=models.CharField(choices=[('HOSPITAL', 'Próprio hospital'), ('UBS', 'Unidade Básica de Saúde (UBS)'), ('HOSPITAL_EXTERNO', 'Outro hospital'), ('REGULACAO', 'Regulação estadual'), ('OUTRO', 'Outro')], default='HOSPITAL', max_length=20, verbose_name='Origem do paciente'),
        ),
        migrations.AddField(
            model_name='receptionattendance',
            name='reason',
            field=models.TextField(blank=True, null=True, verbose_name='Motivo da vinda'),
        ),
        migrations.AddField(
            model_name='receptionattendance',
            name='referral_type',
            field=models.CharField(choices=[('ESPONTANEO', 'Espontâneo'), ('REGULADO', 'Regulado'), ('TRANSFERENCIA', 'Transferência externa')], default='ESPONTANEO', max_length=20, verbose_name='Tipo de encaminhamento'),
        ),
        migrations.AddField(
            model_name='receptionattendance',
            name='reference_document',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Nº guia/senha/referência'),
        ),
        migrations.AddField(
            model_name='receptionattendance',
            name='entry_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Entrada em'),
        ),
        migrations.AddField(
            model_name='receptionattendance',
            name='triage_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Triagem em'),
        ),
        migrations.AddField(
            model_name='receptionattendance',
            name='attendance_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Atendimento em'),
        ),
        migrations.AddField(
            model_name='receptionattendance',
            name='requester_name',
            field=models.CharField(blank=True, max_length=150, null=True, verbose_name='Profissional solicitante'),
        ),
        migrations.AddField(
            model_name='receptionattendance',
            name='requester_registry',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Registro do solicitante'),
        ),
    ]

