from django.contrib import admin
from .models import (
    Surgery, RegulationData, SurgicalData, CMEData,
    OPMEData, BillingData, NursingChecklist
)


# --- Inlines para os Modelos Setoriais ---
# Cada classe "Inline" permite que um modelo setorial seja editado
# dentro da página do modelo principal 'Surgery'.

class RegulationDataInline(admin.StackedInline):
    model = RegulationData
    can_delete = False
    verbose_name_plural = 'Dados de Regulação (NIR)'


class SurgicalDataInline(admin.StackedInline):
    model = SurgicalData
    can_delete = False
    verbose_name_plural = 'Dados do Centro Cirúrgico'


class CMEDataInline(admin.StackedInline):
    model = CMEData
    can_delete = False
    verbose_name_plural = 'Dados da CME'


class OPMEDataInline(admin.StackedInline):
    model = OPMEData
    can_delete = False
    verbose_name_plural = 'Dados de OPME'


class BillingDataInline(admin.StackedInline):
    model = BillingData
    can_delete = False
    verbose_name_plural = 'Dados de Faturamento'


class NursingChecklistInline(admin.StackedInline):
    model = NursingChecklist
    can_delete = False
    verbose_name_plural = 'Checklist de Enfermagem (GENF)'


# --- Configuração do Admin Principal ---

@admin.register(Surgery)
class SurgeryAdmin(admin.ModelAdmin):
    """
    Configuração da exibição do modelo Surgery na área administrativa.
    """
    # Campos que aparecerão na lista de cirurgias
    list_display = ('patient_name', 'procedure_name', 'scheduled_date', 'status')

    # Filtros que aparecerão na barra lateral
    list_filter = ('status', 'scheduled_date')

    # Campos pelos quais se pode buscar
    search_fields = ('patient_name', 'procedure_name')

    # Anexa todos os formulários setoriais a esta página
    inlines = [
        RegulationDataInline,
        SurgicalDataInline,
        CMEDataInline,
        OPMEDataInline,
        BillingDataInline,
        NursingChecklistInline,
    ]

    fieldsets = (
        ('Informações Principais', {
            'fields': ('patient_name', 'procedure_name', 'scheduled_date', 'status')
        }),
        ('Controle', {
            'fields': ('created_by',),
        }),
    )
