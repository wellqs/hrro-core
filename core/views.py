from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, FormView, DeleteView
from django.views import View
from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
import unicodedata
import re
from collections import OrderedDict
try:
    from weasyprint import HTML
except Exception:
    HTML = None
from django.urls import reverse_lazy, reverse # Adicionado reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q, Min, Max, Sum, Avg, OuterRef, Subquery, Case, When
from django.db import models, transaction
from django.db.models.functions import TruncMonth, TruncDay
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
import unicodedata

from .models import (
    Surgery, RegulationData, SurgicalData, BillingData, CMEData, OPMEData, NursingChecklist,
    Sector, Indicator, IndicatorData,
    Patient, Bed, Hospitalization,
    PatientExtra, PatientDocument, ReceptionAttendance, ReceptionQueueEntry, AdverseEventReport,
    OrgUnit, ORG_TIPO_COLORS,
)
from .forms import (
    SurgeryForm,
    RegulationDataForm, SurgicalDataForm, BillingDataForm,
    CMEDataForm, OPMEDataForm, NursingChecklistForm
)
from .forms import PatientForm, PatientSearchForm, ReceptionQueueForm, ReceptionOpenForm, HospitalizationForm, HospitalizationDischargeForm, PatientDocumentForm, NSPCollectForm, NSPEventoAdversoForm
from .filters import SurgeryFilter
from .censo_import import parse_censo_csv, import_censo, VACANT_LABELS

NIR_GROUP_NAME = "NIR (NUCLEO INTERNO DE REGULACAO)"


def normalize_ascii(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value or '')
    return normalized.encode('ascii', 'ignore').decode('ascii').lower()


def nir_clinic_slug(name: str) -> str:
    # replace non-alphanumeric with hyphen to keep URL-safe slugs
    slug = re.sub(r'[^a-z0-9]+', '-', normalize_ascii(name))
    return slug.strip('-')


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
        return redirect('home')


class LandingView(TemplateView):
    template_name = "core/apresentacao.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().get(request, *args, **kwargs)


def build_org_niveis_context():
    units = (
        OrgUnit.objects.filter(is_active=True)
        .annotate(subordinados_count=Count('subordinados', filter=Q(subordinados__is_active=True)))
        .select_related('parent')
        .order_by('nivel', 'nome')
    )
    niveis = OrderedDict((nivel_value, {'label': nivel_label, 'units': []})
                          for nivel_value, nivel_label in OrgUnit.NIVEL_CHOICES)
    for unit in units:
        unit.cor = ORG_TIPO_COLORS.get(unit.tipo, '#64748b')
        niveis[unit.nivel]['units'].append(unit)
    return {
        'org_niveis': [v for v in niveis.values() if v['units']],
        'org_tipos': OrgUnit.TIPO_CHOICES,
    }


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        hour = timezone.localtime().hour
        if hour < 12:
            context['saudacao'] = 'Bom dia'
        elif hour < 18:
            context['saudacao'] = 'Boa tarde'
        else:
            context['saudacao'] = 'Boa noite'

        # Dados fictícios — protótipo do Painel. Substituir por consultas reais
        # conforme cada módulo for integrado (servidores, pendências, avisos, atividade).
        context['painel_stats'] = [
            {'label': 'Servidores', 'value': '370', 'icon': 'bi-people', 'color': '#0284c7'},
            {'label': 'Setores', 'value': '32', 'icon': 'bi-diagram-3', 'color': '#059669'},
            {'label': 'Pendências', 'value': '12', 'icon': 'bi-exclamation-triangle', 'color': '#d97706'},
            {'label': 'Indicadores', 'value': '94%', 'icon': 'bi-bar-chart-line', 'color': '#4338ca'},
        ]
        context['painel_alertas'] = [
            '3 EPIs aguardando entrega',
            '2 treinamentos vencendo',
            '7 Contratos próximos do vencimento',
        ]
        context['painel_avisos'] = [
            {'titulo': 'Manutenção do gerador', 'mensagem': 'Manutenção preventiva programada para amanhã 21/08/2026 às 14h.'},
        ]
        context['painel_atividades'] = [
            {'texto': 'João atualizou o setor NIR', 'tempo': 'há 12 min'},
            {'texto': 'Maria registrou um atendimento na Recepção', 'tempo': 'há 27 min'},
            {'texto': 'Carlos alterou um documento de paciente', 'tempo': 'há 1h'},
        ]
        context['painel_indicadores'] = [
            {'label': 'Ocupação', 'valor': 82, 'color': '#0284c7'},
            {'label': 'Cirurgias', 'valor': 68, 'color': '#059669'},
            {'label': 'Pendências', 'valor': 18, 'color': '#d97706'},
        ]
        context['painel_modulos'] = {
            'recepcao': {'valor': '8', 'legenda': 'pacientes na fila agora'},
            'nir': {'valor': '116/121', 'legenda': 'leitos ocupados'},
            'cc': {'valor': '5', 'legenda': 'cirurgias agendadas hoje'},
            'nsp': {'valor': '3', 'legenda': 'eventos adversos registrados no mês'},
            'indicadores': {'valor': '9/10', 'legenda': 'metas dentro da faixa'},
            'fisio': {'valor': '12', 'legenda': 'atendimentos hoje'},
        }
        return context


class OrganogramaView(LoginRequiredMixin, TemplateView):
    template_name = "core/organograma.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_org_niveis_context())
        return context


class OrgUnitDetailView(LoginRequiredMixin, DetailView):
    model = OrgUnit
    template_name = "core/orgunit_detail.html"
    slug_field = 'codigo'
    slug_url_kwarg = 'codigo'
    context_object_name = 'unit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subordinados'] = self.object.subordinados.filter(is_active=True).order_by('nome')
        context['cor'] = ORG_TIPO_COLORS.get(self.object.tipo, '#64748b')
        return context


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
        active_patient_names = Hospitalization.objects.filter(discharge_date__isnull=True).values_list('patient__name', flat=True).distinct()
        queryset = super().get_queryset().filter(patient_name__in=active_patient_names)
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
    template_name = 'nsp/dashboard.html'
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

        # --- NSP: estatisticas a partir dos eventos adversos ---
        year = self.request.GET.get('ano')
        month = self.request.GET.get('mes')
        current_year = date.today().year
        try:
            year = int(year) if year else current_year
        except ValueError:
            year = current_year
        try:
            month = int(month) if month else None
        except ValueError:
            month = None

        qs = AdverseEventReport.objects.all()
        if year:
            qs = qs.filter(date_evento__year=year)
        if month:
            qs = qs.filter(date_evento__month=month)

        def sum_bool(field):
            return Sum(Case(When(**{field: True}, then=1), default=0, output_field=models.IntegerField()))

        agg = qs.aggregate(
            pulseira=sum_bool('pulseira_identificacao'),
            medicacao=sum_bool('identificacao_medicacao'),
            queda=sum_bool('risco_queda'),
            lesao=sum_bool('lesao_pressao'),
            flebite=sum_bool('flebite'),
            leito=sum_bool('identificacao_leito'),
            estruturas=sum_bool('nao_conformidade_estruturas'),
            acesso=Avg('tempo_acesso_dias'),
            roupa=Avg('tempo_roupa_cama_dias'),
            pacientes=Count('patient', distinct=True),
        )
        for k, v in agg.items():
            if v is None:
                agg[k] = 0

        event_q = (
            Q(pulseira_identificacao=True) |
            Q(identificacao_medicacao=True) |
            Q(risco_queda=True) |
            Q(lesao_pressao=True) |
            Q(flebite=True) |
            Q(identificacao_leito=True) |
            Q(nao_conformidade_estruturas=True) |
            Q(tempo_acesso_dias__isnull=False) |
            Q(tempo_roupa_cama_dias__isnull=False)
        )
        total_ea_nsp = qs.filter(event_q).count()
        total_pacientes = Patient.objects.count()
        pulseira_pacientes = qs.filter(pulseira_identificacao=True).values('patient').distinct().count()
        total_pulseiras = pulseira_pacientes
        total_sem_pulseira = max(total_pacientes - total_pulseiras, 0)
        taxa_conformidade = round((total_pulseiras / total_pacientes) * 100, 2) if total_pacientes else 0
        taxa_inconformidade = round((total_sem_pulseira / total_pacientes) * 100, 2) if total_pacientes else 0

        context['stats'] = {
            'total_ea_nsp': total_ea_nsp,
            'total_ea_notivisa': 0,
            'total_ea_queda': agg['queda'],
            'total_ea_flebite': agg['flebite'],
            'total_pacientes': total_pacientes,
            'total_pulseiras': total_pulseiras,
            'total_sem_pulseira': total_sem_pulseira,
            'taxa_conformidade': taxa_conformidade,
            'taxa_inconformidade': taxa_inconformidade,
            'total_ident_medicacao': agg['medicacao'],
            'total_lesao_pressao': agg['lesao'],
            'total_ident_leito': agg['leito'],
            'total_nao_conformidade': agg['estruturas'],
            'total_tempo_acesso': round(agg['acesso'], 2) if agg['acesso'] else 0,
            'total_tempo_roupa': round(agg['roupa'], 2) if agg['roupa'] else 0,
        }

        monthly = AdverseEventReport.objects.filter(date_evento__year=year).annotate(
            month=TruncMonth('date_evento')
        ).values('month').annotate(
            eventos=Count('id', filter=event_q),
        ).order_by('month')

        chart_labels = []
        chart_ea_nsp = []
        for row in monthly:
            chart_labels.append(row['month'].strftime('%b/%Y'))
            chart_ea_nsp.append(row.get('eventos') or 0)

        context['chart_data'] = {
            'chart_labels': chart_labels,
            'chart_ea_nsp': chart_ea_nsp,
        }

        anos = AdverseEventReport.objects.dates('date_evento', 'year')
        context['anos'] = [d.year for d in anos] or [current_year]
        context['ano_selecionado'] = year
        context['meses'] = [
            (1, 'Jan'), (2, 'Fev'), (3, 'Mar'), (4, 'Abr'), (5, 'Mai'), (6, 'Jun'),
            (7, 'Jul'), (8, 'Ago'), (9, 'Set'), (10, 'Out'), (11, 'Nov'), (12, 'Dez')
        ]
        context['mes_selecionado'] = month
        month_map = dict(context['meses'])
        context['periodo_label'] = f"{month_map.get(month, 'Ano inteiro')} de {year}" if month else f"Ano inteiro de {year}"
        context['titulo'] = 'NSP Dashboard'
        context['setores'] = list(Sector.objects.order_by('name').values_list('name', flat=True))
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
        date_str = request.GET.get('date')
        if not date_str:
            return HttpResponse("Data nÆo fornecida.", status=400)
        if HTML is None:
            return HttpResponse("Dependência do WeasyPrint ausente no ambiente.", status=500)
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        sectors = Sector.objects.prefetch_related('indicators').filter(indicators__is_active=True).distinct()
        existing_data = IndicatorData.objects.filter(period=selected_date)
        indicator_data_map = {entry.indicator_id: (entry.value, entry.notes) for entry in existing_data}
        for sector in sectors:
            for indicator in sector.indicators.all():
                indicator.current_value, indicator.current_notes = indicator_data_map.get(indicator.id, (None, None))
        context = {'sectors': sectors, 'selected_date': selected_date}
        html_string = render_to_string('core/indicator_report_pdf.html', context)
        base_url = request.build_absolute_uri('/')
        html = HTML(string=html_string, base_url=base_url)
        pdf = html.write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment="relatorio_indicadores_{date_str}.pdf"'
        return response


class IndicatorHistoryView(LoginRequiredMixin, ListView):
    template_name = 'core/indicator_history.html'; context_object_name = 'report_dates'; paginate_by = 15
    def get_queryset(self): return IndicatorData.objects.values_list('period', flat=True).distinct().order_by('-period')


class IndicatorAnalysisView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/indicator_analysis.html'; NSP_GROUP_NAME = "NSP (NÚCLEO DE SEGURANÇA DO PACIENTE)"
    def test_func(self): user = self.request.user; return user.is_superuser or user.groups.filter(name=self.NSP_GROUP_NAME).exists()
    def handle_no_permission(self): messages.error(self.request, "Você não tem permissão para acessar esta página."); return redirect('home')
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


class NSPLandingView(LoginRequiredMixin, TemplateView):
    template_name = 'nsp/landing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user_display'] = user.first_name or user.username
        return context


class NSPClinicLandingView(LoginRequiredMixin, TemplateView):
    template_name = 'nsp/coleta.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group_meta = {
            'A': {'badge': 'A', 'name': 'Clínica A'},
            'B': {'badge': 'B', 'name': 'Clínica B'},
            'C': {'badge': 'C', 'name': 'Clínica C'},
            'OUTROS': {'badge': '+', 'name': 'Outros'},
        }
        beds = Bed.objects.filter(is_active=True).values_list('identifier', flat=True)
        groups = OrderedDict((k, {'name': group_meta[k]['name'], 'beds': []}) for k in ('A', 'B', 'C'))
        groups['OUTROS'] = {'name': group_meta['OUTROS']['name'], 'beds': []}
        for identifier in beds:
            first = (identifier or '').strip()[:1].upper()
            key = first if first in ('A', 'B', 'C') else 'OUTROS'
            groups[key]['beds'].append(identifier)

        group_data = []
        for key, group in groups.items():
            if not group['beds']:
                continue
            total_beds = Bed.objects.filter(is_active=True, identifier__istartswith=key).count() if key != 'OUTROS' else Bed.objects.filter(is_active=True).exclude(identifier__regex=r'^[ABC]').count()
            occupied_beds = Hospitalization.objects.filter(
                bed__is_active=True,
                discharge_date__isnull=True
            ).filter(
                bed__identifier__istartswith=key if key != 'OUTROS' else Bed.objects.exclude(identifier__regex=r'^[ABC]').values('identifier')
            ).count()
            vacant_beds = total_beds - occupied_beds
            occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
            group_data.append({
                'key': key,
                'badge': group_meta[key]['badge'],
                'name': group['name'],
                'total_beds': total_beds,
                'occupied_beds': occupied_beds,
                'vacant_beds': vacant_beds,
                'occupancy_rate': round(occupancy_rate, 1),
                'chart_data': [occupied_beds, vacant_beds],
                'detail_url': reverse('nsp_coleta_group', kwargs={'group_key': key.lower()})
            })
        context['clinic_data'] = group_data
        return context





class NSPEquipeView(LoginRequiredMixin, TemplateView):
    template_name = 'nsp/equipe.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['members'] = [
            {'nome': 'Coordenador NSP', 'cargo': 'Coordenação', 'email': 'coordenacao@nsp.local'},
            {'nome': 'Enfermeiro NSP', 'cargo': 'Enfermagem', 'email': 'enfermagem@nsp.local'},
            {'nome': 'Analista de Qualidade', 'cargo': 'Qualidade', 'email': 'qualidade@nsp.local'},
        ]
        return context


class NSPEventoAdversoView(LoginRequiredMixin, FormView):
    template_name = 'nsp/evento_adverso.html'
    form_class = NSPEventoAdversoForm

    def dispatch(self, request, *args, **kwargs):
        self.patient = get_object_or_404(Patient, pk=kwargs.get('patient_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault('date_evento', date.today())
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        return context

    def form_valid(self, form):
        report = form.save(commit=False)
        report.patient = self.patient
        report.created_by = self.request.user
        report.save()
        messages.success(self.request, 'Evento adverso registrado.')
        return redirect('nsp_eventos_list')

    def form_invalid(self, form):
        messages.error(self.request, 'Não foi possível salvar. Verifique os campos obrigatórios.')
        return super().form_invalid(form)


class NSPEventoAdversoBulkView(LoginRequiredMixin, FormView):
    template_name = 'nsp/evento_adverso_bulk.html'
    form_class = NSPEventoAdversoForm

    def dispatch(self, request, *args, **kwargs):
        raw_ids = request.POST.getlist('patient_ids') if request.method == 'POST' else request.GET.getlist('patient_ids')
        self.patient_ids = list(OrderedDict.fromkeys(pid for pid in raw_ids if pid))
        self.patients = list(Patient.objects.filter(pk__in=self.patient_ids).order_by('name'))
        self.return_url = request.POST.get('next') or request.GET.get('next') or reverse('nsp_coleta')

        if not self.patients:
            messages.error(request, 'Selecione ao menos um paciente para lançamento em massa.')
            return redirect(self.return_url)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patients'] = self.patients
        context['patient_count'] = len(self.patients)
        context['return_url'] = self.return_url
        return context

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        report_fields = [
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

        with transaction.atomic():
            for patient in self.patients:
                AdverseEventReport.objects.create(
                    patient=patient,
                    created_by=self.request.user,
                    **{field: cleaned_data.get(field) for field in report_fields},
                )

        messages.success(self.request, f'Evento adverso registrado para {len(self.patients)} pacientes.')
        return redirect(self.return_url)

    def form_invalid(self, form):
        messages.error(self.request, 'Não foi possível salvar o lançamento em massa. Verifique os campos obrigatórios.')
        return super().form_invalid(form)


class NSPEventoAdversoListView(LoginRequiredMixin, ListView):
    template_name = 'nsp/eventos_list.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        qs = AdverseEventReport.objects.select_related('patient', 'created_by')
        date_str = self.request.GET.get('date')
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                qs = qs.filter(date_evento=selected_date)
            except ValueError:
                pass
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_str = self.request.GET.get('date')
        context['selected_date'] = date_str or ''
        return context


class NSPEventoAdversoUpdateView(LoginRequiredMixin, UpdateView):
    model = AdverseEventReport
    form_class = NSPEventoAdversoForm
    template_name = 'nsp/evento_adverso.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        context['report'] = self.object
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Evento adverso atualizado.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Não foi possível atualizar. Verifique os campos obrigatórios.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('nsp_eventos_list')


class NSPEventoAdversoDeleteView(LoginRequiredMixin, DeleteView):
    model = AdverseEventReport
    template_name = 'nsp/evento_adverso_confirm_delete.html'
    success_url = reverse_lazy('nsp_eventos_list')
    context_object_name = 'report'

    def form_valid(self, form):
        messages.success(self.request, 'Evento adverso excluído.')
        return super().form_valid(form)


class NSPEventoAdversoPDFView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if HTML is None:
            return HttpResponse("Dependência do WeasyPrint ausente no ambiente.", status=500)

        date_str = request.GET.get('date')
        selected_date = None
        qs = AdverseEventReport.objects.select_related('patient', 'created_by')
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                qs = qs.filter(date_evento=selected_date)
            except ValueError:
                selected_date = None

        reports = qs.order_by('-date_evento', '-created_at')
        context = {
            'reports': reports,
            'selected_date': selected_date,
            'generated_at': timezone.now(),
        }

        html_string = render_to_string('nsp/eventos_report_pdf.html', context)
        base_url = request.build_absolute_uri('/')
        pdf = HTML(string=html_string, base_url=base_url).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        suffix = date_str or 'todos'
        response['Content-Disposition'] = f'inline; filename=\"relatorio_eventos_adversos_{suffix}.pdf\"'
        return response

# --- VIEWS DO NIR (ATUALIZADAS) ---

# Página de entrada do NIR
class NIREntryView(LoginRequiredMixin, NIRPermissionMixin, TemplateView):
    template_name = 'core/nir_entry.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user_display'] = user.first_name or user.username
        context['can_edit_nir'] = user.is_superuser or user.groups.filter(name=NIR_GROUP_NAME).exists()
        return context

# View para a página inicial do NIR com todos os leitos agrupados por clínica
class NIRPanelView(LoginRequiredMixin, NIRPermissionMixin, TemplateView):
    template_name = 'core/nir_landing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['can_edit_nir'] = user.is_superuser or user.groups.filter(name=NIR_GROUP_NAME).exists()

        # Subquery para pegar a internação ativa de cada leito
        active_hosp_subquery = Hospitalization.objects.filter(
            bed=OuterRef('pk'),
            discharge_date__isnull=True
        ).order_by('-admission_date')

        group_defs = OrderedDict([
            ('A', {'label': 'Clínica A', 'badge': 'A'}),
            ('B', {'label': 'Clínica B', 'badge': 'B'}),
            ('C', {'label': 'Clínica C', 'badge': 'C'}),
            ('EXTRA', {'label': 'EXTRA', 'badge': 'E'}),
        ])

        clinic_data = []
        for key, meta in group_defs.items():
            if key in ('A', 'B', 'C'):
                bed_qs = Bed.objects.filter(is_active=True, identifier__istartswith=key)
            else:
                bed_qs = Bed.objects.filter(is_active=True).exclude(identifier__regex=r'^[ABC]')

            beds = (
                bed_qs
                .annotate(active_hospitalization_id=Subquery(active_hosp_subquery.values('id')[:1]))
                .prefetch_related('hospitalizations', 'hospitalizations__patient')
                .order_by('identifier')
            )

            # Anexa a internação ativa a cada leito
            for bed in beds:
                bed.active_hospitalization = next(
                    (h for h in bed.hospitalizations.all() if h.id == bed.active_hospitalization_id),
                    None
                )

            total = beds.count()
            occupied = sum(1 for b in beds if b.active_hospitalization)
            vacant = total - occupied

            clinic_data.append({
                'key': key,
                'name': meta['label'],
                'badge': meta['badge'],
                'slug': key.lower(),
                'total_beds': total,
                'occupied_beds': occupied,
                'vacant_beds': vacant,
                'occupancy_rate': round(occupied / total * 100, 1) if total else 0,
                'beds': beds,
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

class ExamsLandingView(LoginRequiredMixin, TemplateView):
    template_name = 'core/exams_landing.html'


class PatientExamsView(LoginRequiredMixin, NIRPermissionMixin, TemplateView):
    template_name = 'core/patient_exams.html'

    def get_patient(self):
        return get_object_or_404(Patient, pk=self.kwargs.get('patient_id'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_patient()
        docs = PatientDocument.objects.filter(patient=patient).order_by('-uploaded_at')
        # Mapear categorias: usamos 'EXAME' como laboratório e 'LAUDO' como imagem por enquanto
        context['patient'] = patient
        context['lab_docs'] = docs.filter(category='EXAME')
        context['img_docs'] = docs.filter(category='LAUDO')
        context['other_docs'] = docs.exclude(category__in=['EXAME', 'LAUDO'])
        return context


class NSPClinicBedListView(ClinicBedListView):
    template_name = 'nsp/clinic_bed_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clinic_name = context.get('clinic_name')
        if clinic_name:
            total_beds = Bed.objects.filter(is_active=True, clinic=clinic_name).count()
            occupied_beds = Hospitalization.objects.filter(
                bed__clinic=clinic_name,
                bed__is_active=True,
                discharge_date__isnull=True
            ).count()
            context['total_beds'] = total_beds
            context['occupied_beds'] = occupied_beds
            context['available_beds'] = total_beds - occupied_beds
        else:
            context['total_beds'] = 0
            context['occupied_beds'] = 0
            context['available_beds'] = 0
        clinics = Bed.objects.filter(is_active=True).values_list('clinic', flat=True).distinct()
        context['clinics'] = [{'name': c, 'slug': nir_clinic_slug(c)} for c in clinics]

        def group_key(identifier: str) -> str:
            s = (identifier or '').strip()
            if not s:
                return 'OUTROS'
            first = s[0].upper()
            if first in ('A', 'B', 'C'):
                return first
            return 'OUTROS'

        grouped = OrderedDict((k, []) for k in ('A', 'B', 'C', 'OUTROS'))
        for bed in context.get('beds', []):
            grouped[group_key(bed.identifier)].append(bed)
        context['grouped_beds'] = [
            {'key': k, 'label': f'Enfermaria {k}' if k != 'OUTROS' else 'Outros', 'beds': v}
            for k, v in grouped.items() if v
        ]
        return context


class NSPClinicBedGroupView(ListView):
    model = Bed
    template_name = 'nsp/clinic_bed_list.html'
    context_object_name = 'beds'
    paginate_by = 30

    def get_queryset(self):
        group_key = (self.kwargs.get('group_key') or '').upper()
        self.group_key = group_key
        active_hospitalization_subquery = Hospitalization.objects.filter(
            bed=OuterRef('pk'),
            discharge_date__isnull=True
        ).order_by('-admission_date')

        if group_key in ('A', 'B', 'C'):
            qs = Bed.objects.filter(is_active=True, identifier__istartswith=group_key)
        else:
            qs = Bed.objects.filter(is_active=True).exclude(identifier__regex=r'^[ABC]')

        return qs.annotate(
            active_hospitalization_id=Subquery(active_hospitalization_subquery.values('id')[:1]),
        ).prefetch_related(
            'hospitalizations', 'hospitalizations__patient'
        ).order_by('identifier')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['can_edit_nir'] = user.is_superuser or user.groups.filter(name=NIR_GROUP_NAME).exists()
        label = f'Enfermaria {self.group_key}' if self.group_key in ('A','B','C') else 'Outros'
        context['clinic_name'] = label
        total_beds = context['beds'].count()
        occupied_beds = Hospitalization.objects.filter(
            bed__in=context['beds'],
            discharge_date__isnull=True
        ).count()
        context['total_beds'] = total_beds
        context['occupied_beds'] = occupied_beds
        context['available_beds'] = total_beds - occupied_beds
        context['grouped_beds'] = [{'label': label, 'beds': context['beds']}]
        for bed in context['beds']:
            bed.active_hospitalization = None
            for hosp in bed.hospitalizations.all():
                if hosp.id == bed.active_hospitalization_id:
                    bed.active_hospitalization = hosp
                    break
        return context

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

class NIRCensoUploadView(LoginRequiredMixin, NIRPermissionMixin, View):
    template_name = 'core/nir_censo_upload.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        sync_hosp = request.POST.get('sync_hosp') == 'on'

        if not csv_file:
            messages.error(request, 'Selecione um arquivo CSV antes de enviar.')
            return render(request, self.template_name)

        if not csv_file.name.lower().endswith('.csv'):
            messages.error(request, 'O arquivo deve ter extensão .csv.')
            return render(request, self.template_name)

        try:
            rows = parse_censo_csv(csv_file)
        except Exception as e:
            messages.error(request, f'Erro ao ler o arquivo: {e}')
            return render(request, self.template_name)

        if not rows:
            messages.warning(request, 'Nenhum leito encontrado no arquivo. Verifique o formato do CSV.')
            return render(request, self.template_name)

        try:
            stats = import_censo(rows, sync_hosp=sync_hosp)
        except Exception as e:
            messages.error(request, f'Erro durante a importação: {e}')
            return render(request, self.template_name)

        occupied = stats['hosp_created'] + stats['patients_updated']
        return render(request, self.template_name, {'stats': stats, 'filename': csv_file.name})


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




