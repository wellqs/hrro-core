from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Surgery,
    RegulationData,
    SurgicalData,
    BillingData,
    CMEData,
    OPMEData,
    NursingChecklist
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