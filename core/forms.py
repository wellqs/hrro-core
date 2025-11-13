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
    ReceptionAttendance,
    Sector,
)


# --- Formulário Principal ---
class SurgeryForm(forms.ModelForm):
    class Meta:
        model = Surgery
        fields = [
            'patient_name', 'procedure_name', 'scheduled_date', 'status',
            'motivo_paciente', 'motivo_institucional', 'observacoes_cancelamento',
            'setor_cancelamento'
        ]
        widgets = {
            'patient_name': forms.TextInput(attrs={'class': 'form-control'}),
            'procedure_name': forms.TextInput(attrs={'class': 'form-control'}),
            'scheduled_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'motivo_paciente': forms.Select(attrs={'class': 'form-select'}),
            'motivo_institucional': forms.Select(attrs={'class': 'form-select'}),
            'observacoes_cancelamento': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'maxlength': 150}),
            'setor_cancelamento': forms.Select(attrs={'class': 'form-select'}),
        }

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
        if cpf:
            qs = PatientExtra.objects.filter(cpf=cpf)
            if self.instance.pk:
                qs = qs.exclude(patient=self.instance)
            if qs.exists():
                raise ValidationError({'cpf': 'CPF já cadastrado para outro paciente.'})
        if cns:
            qs = PatientExtra.objects.filter(cns=cns)
            if self.instance.pk:
                qs = qs.exclude(patient=self.instance)
            if qs.exists():
                raise ValidationError({'cns': 'CNS já cadastrado para outro paciente.'})
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
