from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, FormView
from django.views import View
from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
import unicodedata
from weasyprint import HTML
from django.urls import reverse_lazy, reverse # Adicionado reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q, Min, Max, Sum, Avg, OuterRef, Subquery
from django.db import models
from django.db.models.functions import TruncMonth, TruncDay
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
import unicodedata

from .models import (
    Surgery, RegulationData, SurgicalData, BillingData, CMEData, OPMEData, NursingChecklist,
    Sector, Indicator, IndicatorData,
    Patient, Bed, Hospitalization,
    PatientExtra, PatientDocument, ReceptionAttendance, ReceptionQueueEntry,
)
from .forms import (
    SurgeryForm,
    RegulationDataForm, SurgicalDataForm, BillingDataForm,
    CMEDataForm, OPMEDataForm, NursingChecklistForm
)
from .forms import PatientForm, PatientSearchForm, ReceptionQueueForm, ReceptionOpenForm, HospitalizationForm, HospitalizationDischargeForm, PatientDocumentForm
from .filters import SurgeryFilter

NIR_GROUP_NAME = "NIR (NUCLEO INTERNO DE REGULACAO)"



def normalize_ascii(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value or '')
    return normalized.encode('ascii', 'ignore').decode('ascii').lower()


def nir_clinic_slug(name: str) -> str:
    return normalize_ascii(name).replace(' ', '-')


def nir_clinic_name_from_slug(slug: str) -> str:
    slug_normalized = (slug or '').lower()
    clinics = Bed.objects.values_list('clinic', flat=True).distinct()
    mapping = {nir_clinic_slug(c): c for c in clinics}
    return mapping.get(slug_normalized, slug.replace('-', ' ').upper())

class NIRPermissionMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.groups.filter(name=NIR_GROUP_NAME).exists()

    def handle_no_permission(self):
        messages.error(self.request, 'Você não tem permissão para acessar esta área do NIR.')
        return redirect('dashboard')


# --- Views existentes (sem alterações) ---
# ... (DashboardView, SurgeryListView, ..., IndicatorAnalysisView) ...
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_surgeries = Surgery.objects.count()
        realizadas_count = Surgery.objects.filter(status='REALIZADA').count()
        canceladas_count = Surgery.objects.filter(status='CANCELADA').count()
        agendadas_count = Surgery.objects.filter(status='AGENDADA').count()
        context['total_surgeries'] = total_surgeries
        context['realizadas_count'] = realizadas_count
        context['canceladas_count'] = canceladas_count
        context['agendadas_count'] = agendadas_count
        status_distribution = {
            'labels': ['Realizadas', 'Canceladas', 'Agendadas'],
            'data': [realizadas_count, canceladas_count, agendadas_count]
        }
        context['status_distribution_json'] = status_distribution
        monthly_data = (
            Surgery.objects
            .annotate(month=TruncMonth('scheduled_date'))
            .values('month')
            .annotate(
                realizadas=Count('pk', filter=Q(status='REALIZADA')),
                canceladas=Count('pk', filter=Q(status='CANCELADA')),
                agendadas=Count('pk', filter=Q(status='AGENDADA'))
            )
            .order_by('month')
        )
        labels = [item['month'].strftime('%b/%Y') for item in monthly_data]
        monthly_chart_data = {
            'labels': labels,
            'datasets': {
                'realizadas': [item['realizadas'] for item in monthly_data],
                'canceladas': [item['canceladas'] for item in monthly_data],
                'agendadas': [item['agendadas'] for item in monthly_data]
            }
        }
        context['monthly_chart_data_json'] = monthly_chart_data
        return context

# --- Recepção ---
class ReceptionHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'core/reception_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PatientSearchForm(self.request.GET or None)
        patients = Patient.objects.none()
        if form.is_valid() and (form.cleaned_data.get('name') or form.cleaned_data.get('cpf') or form.cleaned_data.get('cns')):
            qs = Patient.objects.all()
            name = form.cleaned_data.get('name')
            cpf = form.cleaned_data.get('cpf')
            cns = form.cleaned_data.get('cns')
            if name:
                qs = qs.filter(name__icontains=name)
            if cpf:
                qs = qs.filter(extra__cpf__iexact=cpf)
            if cns:
                qs = qs.filter(extra__cns__iexact=cns)
            patients = qs.select_related('extra')[:50]
        context['form'] = form
        context['patients'] = patients
        return context

class PatientCreateReceptionView(LoginRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'core/reception_patient_form.html'
    success_url = reverse_lazy('reception_home')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # Deixe o CreateView salvar (chama form.save) para evitar salvar duas vezes
        response = super().form_valid(form)
        messages.success(self.request, 'Paciente cadastrado com sucesso.')
        return response

    def get_success_url(self):
        # Após cadastrar, direciona direto para a abertura de atendimento (inserção na fila)
        return reverse('reception_queue_new', kwargs={'patient_id': self.object.id})

class ReceptionQueueCreateView(LoginRequiredMixin, FormView):
    template_name = 'core/reception_queue_form.html'
    form_class = ReceptionOpenForm

    def dispatch(self, request, *args, **kwargs):
        self.patient = get_object_or_404(Patient, pk=kwargs.get('patient_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        return context

    def form_valid(self, form):
        attendance = ReceptionAttendance.objects.create(
            patient=self.patient,
            origin_sector='Recepção',
            notes=form.cleaned_data.get('notes'),
            care_type=form.cleaned_data.get('care_type'),
            origin=form.cleaned_data.get('origin'),
            reason=form.cleaned_data.get('reason'),
            referral_type=form.cleaned_data.get('referral_type'),
            reference_document=form.cleaned_data.get('reference_document'),
            entry_at=form.cleaned_data.get('entry_at'),
            triage_at=form.cleaned_data.get('triage_at'),
            attendance_at=form.cleaned_data.get('attendance_at'),
            requester_name=form.cleaned_data.get('requester_name'),
            requester_registry=form.cleaned_data.get('requester_registry')
        )
        if form.cleaned_data.get('direct_internation'):
            bed = form.cleaned_data.get('bed')
            admission_dt = form.cleaned_data.get('entry_at') or timezone.now()
            expected_date = None
            if form.cleaned_data.get('attendance_at'):
                expected_date = form.cleaned_data['attendance_at'].date()
            notes_parts = []
            if form.cleaned_data.get('reason'):
                notes_parts.append(f"Motivo: {form.cleaned_data['reason']}")
            if form.cleaned_data.get('notes'):
                notes_parts.append(form.cleaned_data['notes'])
            Hospitalization.objects.create(
                patient=self.patient,
                bed=bed,
                admission_date=admission_dt,
                procedure_planned=form.cleaned_data.get('reason'),
                current_status='Internação direta pela Recepção',
                expected_surgery_date=expected_date,
                notes='\n'.join(notes_parts) if notes_parts else None,
                numero_atendimento=form.cleaned_data.get('reference_document'),
                hipotese_diagnostica=form.cleaned_data.get('reason'),
                created_by=self.request.user
            )
            messages.success(self.request, f"Paciente direcionado diretamente ao leito {bed.identifier}.")
            return redirect(nir_redirect_to_clinic(bed))

        ReceptionQueueEntry.objects.create(
            attendance=attendance,
            destination_sector=form.cleaned_data['destination_sector'],
            priority=form.cleaned_data['priority'],
            status='AGUARDANDO'
        )
        messages.success(self.request, 'Atendimento aberto e paciente inserido na fila.')
        return redirect('reception_queue')

class ReceptionQueueListView(LoginRequiredMixin, ListView):
    model = ReceptionQueueEntry
    template_name = 'core/reception_queue_list.html'
    context_object_name = 'queue'

    def get_queryset(self):
        qs = ReceptionQueueEntry.objects.select_related('attendance__patient').exclude(status='FINALIZADO')
        priority_order = models.Case(
            models.When(priority='EMERGENCIA', then=models.Value(0)),
            models.When(priority='PREFERENCIAL', then=models.Value(1)),
            default=models.Value(2),
            output_field=models.IntegerField(),
        )
        return qs.order_by(priority_order, 'created_at')

class ReceptionQueueCallView(LoginRequiredMixin, View):
    def post(self, request, pk):
        entry = get_object_or_404(ReceptionQueueEntry, pk=pk)
        if entry.status == 'AGUARDANDO':
            entry.status = 'CHAMADO'
            entry.called_at = timezone.now()
            entry.save(update_fields=['status', 'called_at'])
            messages.success(request, f"Paciente {entry.attendance.patient.name} chamado.")
        return redirect('reception_queue')

class ReceptionQueueForwardView(LoginRequiredMixin, View):
    def post(self, request, pk):
        entry = get_object_or_404(ReceptionQueueEntry, pk=pk)
        if entry.status in ['AGUARDANDO', 'CHAMADO']:
            if not entry.called_at:
                entry.called_at = timezone.now()
            entry.status = 'ENCAMINHADO'
            entry.save(update_fields=['status', 'called_at'])
            messages.success(request, f"Paciente {entry.attendance.patient.name} encaminhado.")
        return redirect('reception_queue')

class ReceptionQueueFinishView(LoginRequiredMixin, View):
    def post(self, request, pk):
        entry = get_object_or_404(ReceptionQueueEntry, pk=pk)
        if entry.status != 'FINALIZADO':
            entry.status = 'FINALIZADO'
            entry.finished_at = timezone.now()
            entry.save(update_fields=['status', 'finished_at'])
            messages.success(request, f"Atendimento de {entry.attendance.patient.name} finalizado.")
        return redirect('reception_queue')


class SurgeryListView(LoginRequiredMixin, ListView):
    model = Surgery
    template_name = 'core/surgery_list.html'
    context_object_name = 'surgeries'
    paginate_by = 10
    def get_queryset(self):
        queryset = super().get_queryset()
        self.filterset = SurgeryFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filterset'] = self.filterset
        filtered_queryset = self.get_queryset()
        total_results = filtered_queryset.count()
        context['total_results'] = total_results
        if total_results > 0:
            status_counts = filtered_queryset.values('status').annotate(count=Count('status'))
            data_map = {item['status']: item['count'] for item in status_counts}
            canceladas_count_filtered = data_map.get('CANCELADA', 0)
            cancellation_rate = (canceladas_count_filtered / total_results) * 100
        else:
            data_map = {}
            cancellation_rate = 0
        context['cancellation_rate'] = cancellation_rate
        daily_average = None
        if total_results > 0:
            date_range = filtered_queryset.aggregate(min_date=Min('scheduled_date'), max_date=Max('scheduled_date'))
            first_surgery_date = date_range.get('min_date')
            last_surgery_date = date_range.get('max_date')
            if first_surgery_date and last_surgery_date:
                number_of_days = (last_surgery_date.date() - first_surgery_date.date()).days + 1
                if number_of_days > 0:
                    daily_average = total_results / number_of_days
        context['daily_average'] = daily_average
        status_distribution = {
            'labels': ['Realizadas', 'Canceladas', 'Agendadas'],
            'data': [
                data_map.get('REALIZADA', 0),
                data_map.get('CANCELADA', 0),
                data_map.get('AGENDADA', 0)
            ]
        }
        context['status_distribution_json'] = status_distribution
        if context.get('is_paginated'):
            paginator = context['paginator']
            page_obj = context['page_obj']
            elided_page_range = paginator.get_elided_page_range(number=page_obj.number, on_each_side=2, on_ends=1)
            context['elided_page_range'] = elided_page_range
        return context


class SurgeryDetailView(LoginRequiredMixin, DetailView):
    model = Surgery
    template_name = 'core/surgery_detail.html'
    context_object_name = 'surgery'


class SurgeryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Surgery
    form_class = SurgeryForm
    template_name = 'core/surgery_form.html'
    success_url = reverse_lazy('surgery_list')
    permission_required = 'core.add_surgery'
    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.created_by = self.request.user
        return super().form_valid(form)


class SurgeryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Surgery
    form_class = SurgeryForm
    template_name = 'core/surgery_form.html'
    success_url = reverse_lazy('surgery_list')
    permission_required = 'core.change_surgery'


class RegulationDataUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = RegulationData; form_class = RegulationDataForm; template_name = 'core/regulation_form.html'; permission_required = 'core.change_regulationdata'
    def get_object(self, queryset=None): obj, c = RegulationData.objects.get_or_create(surgery=get_object_or_404(Surgery, pk=self.kwargs.get('pk'))); return obj
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context['surgery'] = self.get_object().surgery; return context
    def get_success_url(self): return reverse_lazy('surgery_detail', kwargs={'pk': self.kwargs.get('pk')})


class SurgicalDataUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = SurgicalData; form_class = SurgicalDataForm; template_name = 'core/surgical_form.html'; permission_required = 'core.change_surgicaldata'
    def get_object(self, queryset=None): obj, c = SurgicalData.objects.get_or_create(surgery=get_object_or_404(Surgery, pk=self.kwargs.get('pk'))); return obj
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context['surgery'] = self.get_object().surgery; return context
    def get_success_url(self): return reverse_lazy('surgery_detail', kwargs={'pk': self.kwargs.get('pk')})


class BillingDataUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = BillingData; form_class = BillingDataForm; template_name = 'core/billing_form.html'; permission_required = 'core.change_billingdata'
    def get_object(self, queryset=None): obj, c = BillingData.objects.get_or_create(surgery=get_object_or_404(Surgery, pk=self.kwargs.get('pk'))); return obj
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context['surgery'] = self.get_object().surgery; return context
    def get_success_url(self): return reverse_lazy('surgery_detail', kwargs={'pk': self.kwargs.get('pk')})


class CMEDataUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CMEData; form_class = CMEDataForm; template_name = 'core/cme_form.html'; permission_required = 'core.change_cmedata'
    def get_object(self, queryset=None): obj, c = CMEData.objects.get_or_create(surgery=get_object_or_404(Surgery, pk=self.kwargs.get('pk'))); return obj
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context['surgery'] = self.get_object().surgery; return context
    def get_success_url(self): return reverse_lazy('surgery_detail', kwargs={'pk': self.kwargs.get('pk')})


class OPMEDataUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = OPMEData; form_class = OPMEDataForm; template_name = 'core/opme_form.html'; permission_required = 'core.change_opmedata'
    def get_object(self, queryset=None): obj, c = OPMEData.objects.get_or_create(surgery=get_object_or_404(Surgery, pk=self.kwargs.get('pk'))); return obj
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context['surgery'] = self.get_object().surgery; return context
    def get_success_url(self): return reverse_lazy('surgery_detail', kwargs={'pk': self.kwargs.get('pk')})


class NursingChecklistUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = NursingChecklist; form_class = NursingChecklistForm; template_name = 'core/nursing_form.html'; permission_required = 'core.change_nursingchecklist'
    def get_object(self, queryset=None): obj, c = NursingChecklist.objects.get_or_create(surgery=get_object_or_404(Surgery, pk=self.kwargs.get('pk'))); return obj
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context['surgery'] = self.get_object().surgery; return context
    def get_success_url(self): return reverse_lazy('surgery_detail', kwargs={'pk': self.kwargs.get('pk')})


class IndicatorDashboardView(LoginRequiredMixin, ListView):
    model = Sector
    template_name = 'core/indicator_dashboard.html'
    context_object_name = 'sectors'
    def get_queryset(self):
        return Sector.objects.prefetch_related('indicators').filter(indicators__is_active=True).distinct()
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_superuser: permitted_sector_ids = list(Sector.objects.values_list('id', flat=True))
        else: user_groups = user.groups.all(); permitted_sector_ids = list(Sector.objects.filter(group__in=user_groups).values_list('id', flat=True))
        context['permitted_sector_ids'] = permitted_sector_ids
        today_str = date.today().strftime('%Y-%m-%d'); selected_date_str = self.request.GET.get('date', today_str)
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date(); context['selected_date'] = selected_date
        existing_data = IndicatorData.objects.filter(period=selected_date)
        indicator_data_map = {entry.indicator_id: (entry.value, entry.notes) for entry in existing_data}
        for sector in context['sectors']:
            for indicator in sector.indicators.all(): indicator.current_value, indicator.current_notes = indicator_data_map.get(indicator.id, (None, None))
        return context
    def post(self, request, *args, **kwargs):
        date_str = request.POST.get('date'); period = datetime.strptime(date_str, '%Y-%m-%d').date()
        for indicator in Indicator.objects.filter(is_active=True):
            value_key = f'value-{indicator.id}'; notes_key = f'notes-{indicator.id}'
            if value_key in request.POST:
                value_str = request.POST.get(value_key); notes_str = request.POST.get(notes_key)
                if value_str:
                    IndicatorData.objects.update_or_create(indicator=indicator, period=period, defaults={'value': value_str, 'notes': notes_str, 'recorded_by': request.user})
        messages.success(request, f"Dados para {period.strftime('%d/%m/%Y')} salvos com sucesso!")
        return redirect(f"{request.path}?date={date_str}")


class IndicatorPDFView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        date_str = request.GET.get('date');
        if not date_str: return HttpResponse("Data não fornecida.", status=400)
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        sectors = Sector.objects.prefetch_related('indicators').filter(indicators__is_active=True).distinct()
        existing_data = IndicatorData.objects.filter(period=selected_date)
        indicator_data_map = {entry.indicator_id: (entry.value, entry.notes) for entry in existing_data}
        for sector in sectors:
            for indicator in sector.indicators.all(): indicator.current_value, indicator.current_notes = indicator_data_map.get(indicator.id, (None, None))
        context = {'sectors': sectors, 'selected_date': selected_date}
        html_string = render_to_string('core/indicator_report_pdf.html', context); base_url = request.build_absolute_uri('/')
        html = HTML(string=html_string, base_url=base_url); pdf = html.write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf'); response['Content-Disposition'] = f'attachment; filename="relatorio_indicadores_{date_str}.pdf"'
        return response


class IndicatorHistoryView(LoginRequiredMixin, ListView):
    template_name = 'core/indicator_history.html'; context_object_name = 'report_dates'; paginate_by = 15
    def get_queryset(self): return IndicatorData.objects.values_list('period', flat=True).distinct().order_by('-period')


class IndicatorAnalysisView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/indicator_analysis.html'; NSP_GROUP_NAME = "NSP (NÚCLEO DE SEGURANÇA DO PACIENTE)"
    def test_func(self): user = self.request.user; return user.is_superuser or user.groups.filter(name=self.NSP_GROUP_NAME).exists()
    def handle_no_permission(self): messages.error(self.request, "Você não tem permissão para acessar esta página."); return redirect('dashboard')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs); context['page_title'] = "Análise de Indicadores NSP"; context['all_sectors'] = Sector.objects.order_by('name')
        start_date_str = self.request.GET.get('start_date'); end_date_str = self.request.GET.get('end_date'); sector_id_str = self.request.GET.get('sector')
        if not end_date_str: end_date = date.today()
        else: end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        if not start_date_str: start_date = end_date - timedelta(days=29)
        else: start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        context['start_date'] = start_date; context['end_date'] = end_date; context['selected_sector_id'] = int(sector_id_str) if sector_id_str else None
        queryset = IndicatorData.objects.filter(period__range=(start_date, end_date))
        if sector_id_str: queryset = queryset.filter(indicator__sector_id=sector_id_str)
        results = queryset.values('indicator__name', 'indicator__sector__name').annotate(total_value=Sum('value'), average_value=Avg('value'), days_count=Count('id')).order_by('indicator__sector__name', 'indicator__name')
        context['results'] = [{'indicator_name': item['indicator__name'], 'sector_name': item['indicator__sector__name'], 'total_value': item['total_value'], 'average_value': item['average_value'], 'days_count': item['days_count']} for item in results]
        return context

# --- VIEWS DO NIR (ATUALIZADAS) ---

# View para a página inicial do NIR com resumos das clínicas
class NIRPanelView(LoginRequiredMixin, NIRPermissionMixin, TemplateView):
    template_name = 'core/nir_landing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clinic_names = Bed.objects.filter(is_active=True).values_list('clinic', flat=True)
        unique_clinics = {}
        for name in clinic_names:
            slug = nir_clinic_slug(name)
            if slug not in unique_clinics:
                unique_clinics[slug] = name
        clinics = unique_clinics.values()
        clinic_data = []
        for clinic_name in clinics:
            total_beds = Bed.objects.filter(is_active=True, clinic=clinic_name).count()
            occupied_beds = Hospitalization.objects.filter(
                bed__clinic=clinic_name,
                bed__is_active=True,
                discharge_date__isnull=True
            ).count()
            vacant_beds = total_beds - occupied_beds
            occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
            clinic_data.append({
                'name': clinic_name,
                'total_beds': total_beds,
                'occupied_beds': occupied_beds,
                'vacant_beds': vacant_beds,
                'occupancy_rate': round(occupancy_rate, 1),
                'chart_data': [occupied_beds, vacant_beds],
                'detail_url': reverse('clinic_bed_list', kwargs={'clinic_name_slug': nir_clinic_slug(clinic_name)})
            })
        context['clinic_data'] = clinic_data
        return context


class ClinicBedListView(LoginRequiredMixin, NIRPermissionMixin, ListView):
    model = Bed
    template_name = 'core/clinic_bed_list.html'
    context_object_name = 'beds'
    paginate_by = 30

    def get_queryset(self):
        clinic_slug = self.kwargs['clinic_name_slug']
        self.clinic_slug = clinic_slug
        clinic_name = nir_clinic_name_from_slug(clinic_slug)
        self.clinic_name = clinic_name

        active_hospitalization_subquery = Hospitalization.objects.filter(
            bed=OuterRef('pk'),
            discharge_date__isnull=True
        ).order_by('-admission_date')

        return Bed.objects.filter(
            is_active=True,
            clinic=clinic_name
        ).annotate(
            active_hospitalization_id=Subquery(active_hospitalization_subquery.values('id')[:1]),
        ).prefetch_related(
            'hospitalizations', 'hospitalizations__patient'
        ).order_by('identifier')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['can_edit_nir'] = user.is_superuser or user.groups.filter(name=NIR_GROUP_NAME).exists()
        context['clinic_name'] = self.clinic_name
        context['clinic_slug'] = getattr(self, 'clinic_slug', self.kwargs.get('clinic_name_slug'))

        for bed in context['beds']:
            bed.active_hospitalization = None
            for hosp in bed.hospitalizations.all():
                if hosp.id == bed.active_hospitalization_id:
                    bed.active_hospitalization = hosp
                    break
        return context

def nir_redirect_to_clinic(bed):
    return reverse('clinic_bed_list', kwargs={'clinic_name_slug': nir_clinic_slug(bed.clinic)})


def get_hospitalization_success_url(hospitalization):
    return nir_redirect_to_clinic(hospitalization.bed)


class NIRHospitalizationCreateView(LoginRequiredMixin, NIRPermissionMixin, CreateView):
    model = Hospitalization
    form_class = HospitalizationForm
    template_name = 'core/nir_hospitalization_form.html'

    def get_initial(self):
        initial = super().get_initial()
        bed_id = self.kwargs.get('bed_id')
        if bed_id:
            initial['bed'] = get_object_or_404(Bed, pk=bed_id)
        initial.setdefault('admission_date', timezone.now())
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Alocar Paciente em Leito'
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Internação registrada com sucesso.')
        return response

    def get_success_url(self):
        return get_hospitalization_success_url(self.object)


class NIRHospitalizationUpdateView(LoginRequiredMixin, NIRPermissionMixin, UpdateView):
    model = Hospitalization
    form_class = HospitalizationForm
    template_name = 'core/nir_hospitalization_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Editar Internação'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Internação atualizada com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        return get_hospitalization_success_url(self.object)


class NIRHospitalizationDischargeView(LoginRequiredMixin, NIRPermissionMixin, UpdateView):
    model = Hospitalization
    form_class = HospitalizationDischargeForm
    template_name = 'core/nir_hospitalization_discharge_form.html'

    def get_initial(self):
        initial = super().get_initial()
        if not self.object.discharge_date:
            initial['discharge_date'] = timezone.now()
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Registrar Alta'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Alta registrada com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        return get_hospitalization_success_url(self.object)


class PatientDocumentListView(LoginRequiredMixin, NIRPermissionMixin, FormView):
    form_class = PatientDocumentForm
    template_name = 'core/patient_documents.html'

    def get_patient(self):
        return get_object_or_404(Patient, pk=self.kwargs.get('patient_id'))

    def get_initial(self):
        initial = super().get_initial()
        initial['patient'] = self.get_patient()
        return initial

    def form_valid(self, form):
        doc = form.save(commit=False)
        doc.patient = self.get_patient()
        doc.uploaded_by = self.request.user
        doc.save()
        messages.success(self.request, 'Documento anexado com sucesso.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('patient_documents', kwargs={'patient_id': self.kwargs.get('patient_id')})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_patient()
        docs = PatientDocument.objects.filter(patient=patient).order_by('-uploaded_at')
        context['patient'] = patient
        context['documents'] = docs
        context['page_title'] = f'Documentos de {patient.name}'
        return context

class NIRHospitalizationHistoryView(LoginRequiredMixin, NIRPermissionMixin, ListView):
    model = Hospitalization
    template_name = 'core/nir_hospitalization_history.html'
    context_object_name = 'hospitalizations'
    paginate_by = 25

    def get_queryset(self):
        qs = Hospitalization.objects.select_related('patient', 'bed').order_by('-admission_date')
        status_filter = self.request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(discharge_date__isnull=True)
        elif status_filter == 'discharged':
            qs = qs.filter(discharge_date__isnull=False)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Histórico de Internações'
        context['status_filter'] = self.request.GET.get('status', '')
        context['active_count'] = Hospitalization.objects.filter(discharge_date__isnull=True).count()
        context['discharged_count'] = Hospitalization.objects.filter(discharge_date__isnull=False).count()
        return context


