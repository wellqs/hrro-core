# Em core/filters.py

import django_filters
from django import forms
from .models import Surgery

class SurgeryFilter(django_filters.FilterSet):
    # 1. Declaração explícita para o nome do paciente
    patient_name = django_filters.CharFilter(
        field_name='patient_name',
        lookup_expr='icontains',  # Modo de busca (contém, ignorando maiúsculas/minúsculas)
        label='Nome do Paciente'
    )

    # 2. Declaração explícita para o status (melhorada para usar ChoiceFilter)
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=Surgery.STATUS_CHOICES,  # Pega as opções diretamente do modelo
        label='Status'
    )

    # 3. Declaração explícita para a data (continua a mesma)
    scheduled_date = django_filters.DateFromToRangeFilter(
        field_name='scheduled_date',
        label='Período Agendado',
        widget=django_filters.widgets.RangeWidget(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    class Meta:
        model = Surgery
        # Agora 'fields' é apenas uma lista para conectar os filtros ao modelo.
        # A lógica de cada filtro já foi definida acima.
        fields = ['patient_name', 'status', 'scheduled_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Como os labels já foram definidos acima, o __init__ fica muito mais limpo.
        # Apenas garantimos que os campos tenham a classe CSS correta.
        for name, field in self.form.fields.items():
            if name not in ['scheduled_date_0', 'scheduled_date_1']:
                field.widget.attrs.update({'class': 'form-control'})

