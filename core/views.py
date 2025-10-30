from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.views import View
from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from weasyprint import HTML
from django.urls import reverse_lazy, reverse # Adicionado reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from datetime import date, datetime, timedelta
from django.db.models import Count, Q, Min, Max, Sum, Avg, OuterRef, Subquery
from django.db.models.functions import TruncMonth, TruncDay
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin

from .models import (
    Surgery, RegulationData, SurgicalData, BillingData, CMEData, OPMEData, NursingChecklist,
    Sector, Indicator, IndicatorData,
    Patient, Bed, Hospitalization
)
from .forms import (
    SurgeryForm,
    RegulationDataForm, SurgicalDataForm, BillingDataForm,
    CMEDataForm, OPMEDataForm, NursingChecklistForm
)
from .filters import SurgeryFilter


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
class NIRPanelView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/nir_landing.html' # Novo template para a página inicial
    NIR_GROUP_NAME = "NIR (NÚCLEO INTERNO DE REGULAÇÃO)"

    def test_func(self):
        # Permite acesso a todos por enquanto, mas podemos restringir depois
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clinics = ['CLÍNICA A', 'CLÍNICA B', 'CLÍNICA C', 'EXTRA'] # Clínicas a serem analisadas
        clinic_data = []

        for clinic_name in clinics:
            # Total de leitos ativos na clínica
            total_beds = Bed.objects.filter(is_active=True, clinic=clinic_name).count()

            # Conta internações ativas (sem data de saída) nos leitos da clínica
            occupied_beds = Hospitalization.objects.filter(
                bed__clinic=clinic_name,
                bed__is_active=True,
                discharge_date__isnull=True
            ).count()

            vacant_beds = total_beds - occupied_beds
            occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0

            clinic_info = {
                'name': clinic_name,
                'total_beds': total_beds,
                'occupied_beds': occupied_beds,
                'vacant_beds': vacant_beds,
                'occupancy_rate': round(occupancy_rate, 1),
                # Prepara dados para o gráfico Chart.js ([ocupados, vagos])
                'chart_data': [occupied_beds, vacant_beds],
                # Gera a URL para a lista de leitos da clínica
                'detail_url': reverse('clinic_bed_list', kwargs={'clinic_name_slug': clinic_name.lower().replace('í', 'i').replace(' ', '-')})
            }
            clinic_data.append(clinic_info)

        context['clinic_data'] = clinic_data
        return context

# View para listar os leitos de uma clínica específica
class ClinicBedListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Bed
    template_name = 'core/clinic_bed_list.html' # Usaremos este template para a lista
    context_object_name = 'beds'
    paginate_by = 30
    NIR_GROUP_NAME = "NIR (NÚCLEO INTERNO DE REGULAÇÃO)"

    def test_func(self):
        return True # Permite acesso a todos por enquanto

    def get_queryset(self):
        # Pega o nome da clínica da URL (vem como slug)
        clinic_name_slug = self.kwargs['clinic_name_slug']
        # Converte o slug de volta para o nome original da clínica (precisa ser robusto)
        # Esta é uma forma simples, pode precisar de ajustes se os nomes forem complexos
        clinic_name = clinic_name_slug.replace('-', ' ').replace('i', 'í').upper() # Tenta reverter
        # Correção específica para 'CLÍNICA A', 'CLÍNICA B', 'CLÍNICA C'
        if clinic_name_slug == 'clinica-a': clinic_name = 'CLÍNICA A'
        elif clinic_name_slug == 'clinica-b': clinic_name = 'CLÍNICA B'
        elif clinic_name_slug == 'clinica-c': clinic_name = 'CLÍNICA C'
        elif clinic_name_slug == 'extra': clinic_name = 'EXTRA' # Adicionado
        # Se não encontrar, pode retornar erro ou queryset vazio

        self.clinic_name = clinic_name # Armazena para usar no get_context_data

        active_hospitalization_subquery = Hospitalization.objects.filter(
            bed=OuterRef('pk'),
            discharge_date__isnull=True
        ).order_by('-admission_date')

        queryset = Bed.objects.filter(
            is_active=True,
            clinic=self.clinic_name # Filtra pela clínica da URL
        ).annotate(
            active_hospitalization_id=Subquery(active_hospitalization_subquery.values('id')[:1]),
        ).prefetch_related(
            'hospitalizations',
            'hospitalizations__patient'
        ).order_by('identifier') # Ordena pelo identificador dentro da clínica

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['can_edit_nir'] = user.is_superuser or user.groups.filter(name=self.NIR_GROUP_NAME).exists()
        context['clinic_name'] = self.clinic_name # Envia o nome da clínica para o template

        for bed in context['beds']:
            bed.active_hospitalization = None
            for hosp in bed.hospitalizations.all():
                if hosp.id == bed.active_hospitalization_id:
                    bed.active_hospitalization = hosp
                    break
        return context