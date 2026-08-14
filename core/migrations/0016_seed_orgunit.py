from django.db import migrations

# Organograma institucional real do HRRO.
# (codigo, nome, tipo, nivel, parent_codigo)
ORG_UNITS = [
    ('DG', 'Direção Geral', 'direcao', 0, None),

    ('DASS', 'Direção Assistencial', 'diretoria', 1, 'DG'),
    ('DGA', 'Direção Geral Adjunta', 'direcao', 1, 'DG'),
    ('DIRTEC', 'Direção Técnica', 'direcao', 1, 'DG'),

    ('ASTEC', 'Assessoria Técnica', 'administrativo', 2, 'DG'),
    ('ACOMP', 'Central de Acompanhantes', 'assistencial', 2, 'DG'),
    ('AMB', 'Central de Ambulatório', 'assistencial', 2, 'DG'),
    ('OPME', 'Central de OPME', 'assistencial', 2, 'DG'),
    ('ROUP', 'Central de Rouparia', 'assistencial', 2, 'DG'),
    ('CIPA', 'Comissão Interna de Prevenção de Acidentes', 'comissao', 2, 'DGA'),
    ('CCIH', 'Comissão de Controle de Infecção Hospitalar', 'comissao', 2, 'DGA'),
    ('DCLIN', 'Diretoria Clínica', 'diretoria', 2, 'DIRTEC'),
    ('GAB', 'Gabinete', 'administrativo', 2, 'DG'),
    ('GAD', 'Gerência Administrativa', 'administrativo', 2, 'DGA'),
    ('GMED', 'Gerência Médica', 'gerencia', 2, 'DIRTEC'),
    ('ASOCIAL', 'Gerência de Assistência Social', 'gerencia', 2, 'DASS'),
    ('GENF', 'Gerência de Enfermagem', 'gerencia', 2, 'DASS'),
    ('GEPIDEMIO', 'Gerência de Epidemiologia', 'gerencia', 2, 'DG'),
    ('GFAH', 'Gerência de Farmácia', 'gerencia', 2, 'DASS'),
    ('GFISIO', 'Gerência de Fisioterapia', 'gerencia', 2, 'DASS'),
    ('GFONO', 'Gerência de Fonoaudiologia', 'gerencia', 2, 'DASS'),
    ('GNUD', 'Gerência de Nutrição e Dietética', 'gerencia', 2, 'DASS'),
    ('GPSIC', 'Gerência de Psicologia', 'gerencia', 2, 'DASS'),
    ('NCME', 'Núcleo CME', 'nucleo', 2, 'DASS'),
    ('NIR', 'Núcleo Interno de Regulação', 'nucleo', 2, 'DG'),
    ('NSESMT', 'Núcleo SESMT', 'nucleo', 2, 'DG'),
    ('NCOMPEHEX', 'Núcleo de Comissão de Avaliação de Plantão', 'nucleo', 2, 'DG'),
    ('NEP', 'Núcleo de Educação Permanente', 'nucleo', 2, 'DGA'),
    ('NOUVI', 'Núcleo de Ouvidoria', 'administrativo', 2, 'DG'),
    ('NURADIO', 'Núcleo de Radiologia', 'assistencial', 2, 'DASS'),
    ('NRH', 'Núcleo de Recursos Humanos', 'administrativo', 2, 'DGA'),
    ('NSP', 'Núcleo de Segurança do Paciente', 'nucleo', 2, 'DGA'),
    ('NOBITO', 'Núcleo de Óbito', 'assistencial', 2, 'DG'),

    ('LAB', 'Laboratório', 'unidade', 3, 'DASS'),
    ('UTI', 'Unidade de Terapia Intensiva (UTI)', 'unidade', 3, 'DIRTEC'),
]


def seed_org_units(apps, schema_editor):
    OrgUnit = apps.get_model('core', 'OrgUnit')
    by_codigo = {}
    for codigo, nome, tipo, nivel, parent_codigo in ORG_UNITS:
        obj, _ = OrgUnit.objects.update_or_create(
            codigo=codigo,
            defaults={'nome': nome, 'tipo': tipo, 'nivel': nivel},
        )
        by_codigo[codigo] = obj

    for codigo, _, _, _, parent_codigo in ORG_UNITS:
        if parent_codigo:
            unit = by_codigo[codigo]
            unit.parent = by_codigo[parent_codigo]
            unit.save(update_fields=['parent'])


def unseed_org_units(apps, schema_editor):
    OrgUnit = apps.get_model('core', 'OrgUnit')
    OrgUnit.objects.filter(codigo__in=[c for c, *_ in ORG_UNITS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_orgunit'),
    ]

    operations = [
        migrations.RunPython(seed_org_units, unseed_org_units),
    ]
