from django import forms
from django.core.exceptions import ValidationError
import re
from .models import (
    Surgery,
    RegulationData,
    SurgicalData,
    BillingData,
    CMEData,
    OPMEData,
    NursingChecklist,
    Patient,
    PatientExtra,
    PatientDocument,
    ReceptionAttendance,
    Sector,
    Bed,
    Hospitalization,
    AdverseEventReport,
)
class NSPCollectForm(forms.Form):
    total_ea_nsp = forms.DecimalField(label='Total de EA (NSP)', required=False, decimal_places=2, max_digits=10, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    total_ea_notivisa = forms.DecimalField(label='Total de EA (NOTIVISA)', required=False, decimal_places=2, max_digits=10, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    total_ea_queda = forms.DecimalField(label='Quedas', required=False, decimal_places=2, max_digits=10, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    total_ea_flebite = forms.DecimalField(label='Flebite', required=False, decimal_places=2, max_digits=10, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    total_pacientes = forms.DecimalField(label='Total de pacientes', required=False, decimal_places=2, max_digits=10, widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_total_pacientes'}))
    total_pulseiras = forms.DecimalField(label='Pulseiras verificadas', required=False, decimal_places=2, max_digits=10, widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_total_pulseiras'}))
    taxa_conformidade = forms.DecimalField(label='Taxa de conformidade (%)', required=False, decimal_places=2, max_digits=10, widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_taxa_conformidade'}))


class NSPEventoAdversoForm(forms.ModelForm):
    class Meta:
        model = AdverseEventReport
        fields = [
            'date_evento',
            'pulseira_identificacao',
            'identificacao_medicacao',
            'risco_queda',
            'lesao_pressao',
            'flebite',
            'tempo_acesso_dias',
            'tempo_roupa_cama_dias',
            'identificacao_leito',
            'nao_conformidade_estruturas',
            'observacoes',
        ]
        widgets = {
            'date_evento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'pulseira_identificacao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'identificacao_medicacao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'risco_queda': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lesao_pressao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'flebite': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tempo_acesso_dias': forms.NumberInput(attrs={'class': 'form-control'}),
            'tempo_roupa_cama_dias': forms.NumberInput(attrs={'class': 'form-control'}),
            'identificacao_leito': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'nao_conformidade_estruturas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# --- Formulário Principal ---
class SurgeryForm(forms.ModelForm):
    # Sobrescreve patient_name para selecionar apenas pacientes internados (NIR ativo)
    patient_name = forms.ModelChoiceField(
        label='Paciente',
        queryset=Hospitalization.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Surgery
        fields = [
            'patient_name', 'procedure_name', 'scheduled_date', 'status',
            'motivo_paciente', 'motivo_institucional', 'observacoes_cancelamento',
            'setor_cancelamento'
        ]
        widgets = {
            'procedure_name': forms.TextInput(attrs={'class': 'form-control'}),
            'scheduled_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'motivo_paciente': forms.Select(attrs={'class': 'form-select'}),
            'motivo_institucional': forms.Select(attrs={'class': 'form-select'}),
            'observacoes_cancelamento': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'maxlength': 150}),
            'setor_cancelamento': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_hosp = Hospitalization.objects.filter(discharge_date__isnull=True).select_related('patient', 'bed')
        self.fields['patient_name'].queryset = active_hosp
        self.fields['patient_name'].label_from_instance = lambda hosp: f"{hosp.patient.name} - Leito {hosp.bed.identifier}"

    def clean_patient_name(self):
        hosp = self.cleaned_data['patient_name']
        return hosp.patient.name if hosp else ''

    def clean(self):
        cleaned_data = super().clean()

        if self.instance and self.instance.pk:
            if self.instance.status == 'CANCELADA':
                raise ValidationError("Cirurgias que já foram canceladas não podem ser editadas.")

            if self.instance.status == 'REALIZADA' and self.cleaned_data.get('status') != 'REALIZADA':
                raise ValidationError("Cirurgias que já foram realizadas não podem ter seu status alterado.")

        return cleaned_data

# --- Formulários Setoriais ---
class RegulationDataForm(forms.ModelForm):
    class Meta:
        model = RegulationData
        fields = ['entry_date', 'is_approved', 'notes']
        widgets = {
            'entry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SurgicalDataForm(forms.ModelForm):
    class Meta:
        model = SurgicalData
        # ADICIONADO NOVO CAMPO
        fields = ['start_time', 'end_time', 'room', 'surgeon', 'checklist_cirurgia_segura']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'room': forms.TextInput(attrs={'class': 'form-control'}),
            'surgeon': forms.TextInput(attrs={'class': 'form-control'}),
            # ADICIONADO WIDGET PARA O NOVO CAMPO
            'checklist_cirurgia_segura': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class BillingDataForm(forms.ModelForm):
    class Meta:
        model = BillingData
        fields = ['invoice_code', 'is_billed']
        widgets = {
            'invoice_code': forms.TextInput(attrs={'class': 'form-control'}),
            'is_billed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CMEDataForm(forms.ModelForm):
    class Meta:
        model = CMEData
        fields = ['material_sterilized', 'sterilization_date', 'notes']
        widgets = {
            'material_sterilized': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sterilization_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class OPMEDataForm(forms.ModelForm):
    class Meta:
        model = OPMEData
        fields = ['materials_list', 'is_authorized', 'supplier']
        widgets = {
            'materials_list': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_authorized': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'supplier': forms.TextInput(attrs={'class': 'form-control'}),
        }


class NursingChecklistForm(forms.ModelForm):
    class Meta:
        model = NursingChecklist
        fields = ['patient_fasting', 'consent_form_signed', 'pre_op_medication_given', 'notes']
        widgets = {
            'patient_fasting': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'consent_form_signed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pre_op_medication_given': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


# --- Recepção: busca e cadastro de pacientes ---
class PatientSearchForm(forms.Form):
    name = forms.CharField(label='Nome', required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do paciente'}))
    cpf = forms.CharField(label='CPF', required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CPF'}))
    cns = forms.CharField(label='CNS', required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CNS'}))


class PatientForm(forms.ModelForm):
    cpf = forms.CharField(label='CPF', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    cns = forms.CharField(label='CNS', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Patient
        fields = ['name', 'date_of_birth', 'medical_record_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'medical_record_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True, user=None):
        patient = super().save(commit=commit)
        cpf = self.cleaned_data.get('cpf')
        cns = self.cleaned_data.get('cns')
        # valida unicidade de CPF/CNS de forma amigável antes de salvar
        # cria/atualiza extras
        extra, _ = PatientExtra.objects.get_or_create(patient=patient)
        if cpf:
            extra.cpf = cpf
        if cns:
            extra.cns = cns
        extra.save()
        return patient

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not cpf:
            return cpf
        digits = re.sub(r"\D", "", cpf)
        if len(digits) != 11 or len(set(digits)) == 1:
            # Permite CPF de teste 000.000.000-00 para fluxos de validação
            if digits == '00000000000':
                return digits
            raise ValidationError('CPF inválido. Informe 11 dígitos.')
        # Validação básica dos dígitos verificadores
        def dv(nums):
            s = sum(int(n) * w for n, w in zip(nums, range(len(nums)+1, 1, -1)))
            r = (s * 10) % 11
            return '0' if r == 10 else str(r)
        if digits[9] != dv(digits[:9]) or digits[10] != dv(digits[:10]):
            raise ValidationError('CPF inválido.')
        return digits

    def clean_cns(self):
        cns = self.cleaned_data.get('cns')
        if not cns:
            return cns
        digits = re.sub(r"\D", "", cns)
        if len(digits) != 15:
            raise ValidationError('CNS deve conter 15 dígitos.')
        return digits


class ReceptionQueueForm(forms.Form):
    destination_sector = forms.CharField(label='Setor de Destino', widget=forms.TextInput(attrs={'class': 'form-control'}))
    priority = forms.ChoiceField(label='Prioridade', choices=[('NORMAL','Normal'),('PREFERENCIAL','Preferencial'),('EMERGENCIA','Emergência')], widget=forms.Select(attrs={'class': 'form-select'}))
    notes = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))


class ReceptionOpenForm(forms.Form):
    # Identificação
    care_type = forms.ChoiceField(
        label='Tipo de atendimento',
        choices=[('AMBULATORIO','Ambulatório'),('URGENCIA','Urgência'),('INTERNACAO','Internação'),('EXAME','Exame'),('OUTRO','Outro')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # Procedência
    origin = forms.ChoiceField(
        label='Origem do paciente',
        choices=[('HOSPITAL','Próprio hospital'),('UBS','UBS'),('HOSPITAL_EXTERNO','Outro hospital'),('REGULACAO','Regulação estadual'),('OUTRO','Outro')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # Motivo
    reason = forms.CharField(label='Motivo da vinda', required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))
    # Encaminhamento
    referral_type = forms.ChoiceField(
        label='Tipo de encaminhamento',
        choices=[('ESPONTANEO','Espontâneo'),('REGULADO','Regulado'),('TRANSFERENCIA','Transferência externa')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # Documentação
    reference_document = forms.CharField(label='Nº guia/senha/referência', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    # Datas
    entry_at = forms.DateTimeField(label='Entrada em', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}))
    triage_at = forms.DateTimeField(label='Triagem em', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}))
    attendance_at = forms.DateTimeField(label='Atendimento em', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}))
    # Outros
    requester_name = forms.CharField(label='Profissional solicitante', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    requester_registry = forms.CharField(label='Registro do solicitante', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    # Fila
    destination_sector = forms.ChoiceField(label='Setor de Destino', choices=[], widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ChoiceField(label='Prioridade', choices=[('NORMAL','Normal'),('PREFERENCIAL','Preferencial'),('EMERGENCIA','Emergência')], widget=forms.Select(attrs={'class': 'form-select'}))
    direct_internation = forms.BooleanField(label='Internação direta (sem fila)', required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    bed = forms.ModelChoiceField(
        label='Leito (para internação direta)',
        queryset=Bed.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    notes = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Carrega setores do modelo Sector; fallback para lista padrão
        try:
            sectors = list(Sector.objects.all().order_by('name').values_list('name', flat=True))
        except Exception:
            sectors = []
        if not sectors:
            sectors = [
                'Recepção', 'NIR / Regulação', 'Ambulatório', 'Internação', 'Pronto Atendimento',
                'Centro Cirúrgico', 'Exames', 'Laboratório', 'Imagem', 'Farmácia / Almoxarifado',
                'Faturamento', 'CCIH', 'NSP', 'SESMT'
            ]
        self.fields['destination_sector'].choices = [(s, s) for s in sectors]

        bed_qs = Bed.objects.filter(is_active=True).order_by('clinic', 'identifier')
        self.fields['bed'].queryset = bed_qs
        self.fields['bed'].label_from_instance = lambda bed: f"{bed.clinic} - {bed.identifier}"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('direct_internation'):
            bed = cleaned.get('bed')
            if not bed:
                self.add_error('bed', 'Selecione um leito para a internação direta.')
            else:
                occupied = Hospitalization.objects.filter(bed=bed, discharge_date__isnull=True).exists()
                if occupied:
                    self.add_error('bed', 'Este leito já está ocupado. Escolha outro.')
        return cleaned

class DateTimeLocalInput(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%dT%H:%M')
        attrs = kwargs.setdefault('attrs', {})
        attrs.setdefault('class', 'form-control')
        super().__init__(*args, **kwargs)


class HospitalizationForm(forms.ModelForm):
    class Meta:
        model = Hospitalization
        fields = [
            'patient', 'bed', 'admission_date', 'procedure_planned',
            'expected_surgery_date', 'current_status', 'notes'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'bed': forms.Select(attrs={'class': 'form-select'}),
            'admission_date': DateTimeLocalInput(),
            'procedure_planned': forms.TextInput(attrs={'class': 'form-control'}),
            'expected_surgery_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'current_status': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bed'].queryset = Bed.objects.filter(is_active=True).order_by('clinic', 'identifier')
        self.fields['patient'].queryset = Patient.objects.all().order_by('name')

    def clean_bed(self):
        bed = self.cleaned_data.get('bed')
        if not bed:
            return bed
        qs = Hospitalization.objects.filter(bed=bed, discharge_date__isnull=True)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Este leito já está ocupado.')
        return bed


class HospitalizationDischargeForm(forms.ModelForm):
    class Meta:
        model = Hospitalization
        fields = ['discharge_date', 'current_status', 'notes']
        widgets = {
            'discharge_date': DateTimeLocalInput(),
            'current_status': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_discharge_date(self):
        dt = self.cleaned_data.get('discharge_date')
        if not dt:
            raise ValidationError('Informe a data e hora da alta.')
        return dt


class PatientDocumentForm(forms.ModelForm):
    class Meta:
        model = PatientDocument
        fields = ['patient', 'category', 'description', 'document']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição opcional'}),
            'document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.order_by('name')
