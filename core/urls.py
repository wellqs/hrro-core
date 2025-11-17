# Em core/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    DashboardView,
    SurgeryListView,
    SurgeryDetailView,
    SurgeryCreateView,
    SurgeryUpdateView,
    RegulationDataUpdateView,
    SurgicalDataUpdateView,
    BillingDataUpdateView,
    CMEDataUpdateView,
    OPMEDataUpdateView,
    NursingChecklistUpdateView,
    IndicatorDashboardView,
    IndicatorPDFView,
    IndicatorHistoryView,
    IndicatorAnalysisView,
    NIRPanelView,
    # --- IMPORTAÇÃO ADICIONADA PARA A VIEW DA LISTA DE LEITOS DA CLÍNICA ---
    ClinicBedListView,
    NIRHospitalizationCreateView,
    NIRHospitalizationUpdateView,
    NIRHospitalizationDischargeView,
    NIRHospitalizationHistoryView,
    PatientDocumentListView,
    # Recepção
    ReceptionHomeView,
    PatientCreateReceptionView,
    ReceptionQueueCreateView,
    ReceptionQueueListView,
    ReceptionQueueCallView,
    ReceptionQueueForwardView,
    ReceptionQueueFinishView,
)

urlpatterns = [
    # URLs de Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # URLs do Dashboard e CRUD de Cirurgias
    path('', DashboardView.as_view(), name='dashboard'),
    path('surgeries/', SurgeryListView.as_view(), name='surgery_list'),
    path('surgery/new/', SurgeryCreateView.as_view(), name='surgery_create'),
    path('surgery/<int:pk>/', SurgeryDetailView.as_view(), name='surgery_detail'),
    path('surgery/<int:pk>/update/', SurgeryUpdateView.as_view(), name='surgery_update'),

    # URLs de Indicadores
    path('indicators/', IndicatorDashboardView.as_view(), name='indicator_dashboard'),
    path('indicators/pdf/', IndicatorPDFView.as_view(), name='indicator_pdf'),
    path('indicators/history/', IndicatorHistoryView.as_view(), name='indicator_history'),
    path('indicators/analysis/', IndicatorAnalysisView.as_view(), name='indicator_analysis'),

    # URLs do NIR
    path('nir/', NIRPanelView.as_view(), name='nir_panel'), # Página inicial com resumos
    # --- NOVA URL ADICIONADA PARA A LISTA DE LEITOS DA CLÍNICA ---
    path('nir/clinic/<slug:clinic_name_slug>/', ClinicBedListView.as_view(), name='clinic_bed_list'), # Página de detalhes da clínica
    path('nir/hospitalization/new/', NIRHospitalizationCreateView.as_view(), name='nir_hospitalization_create'),
    path('nir/hospitalization/new/bed/<int:bed_id>/', NIRHospitalizationCreateView.as_view(), name='nir_hospitalization_create_bed'),
    path('nir/hospitalization/<int:pk>/edit/', NIRHospitalizationUpdateView.as_view(), name='nir_hospitalization_edit'),
    path('nir/hospitalization/<int:pk>/discharge/', NIRHospitalizationDischargeView.as_view(), name='nir_hospitalization_discharge'),

    path('nir/hospitalizations/', NIRHospitalizationHistoryView.as_view(), name='nir_hospitalization_history'),
    path('nir/patient/<int:patient_id>/documents/', PatientDocumentListView.as_view(), name='patient_documents'),

    # URLs dos Formulários Setoriais
    path('surgery/<int:pk>/regulation/', RegulationDataUpdateView.as_view(), name='regulation_update'),
    path('surgery/<int:pk>/surgical/', SurgicalDataUpdateView.as_view(), name='surgical_update'),
    path('surgery/<int:pk>/billing/', BillingDataUpdateView.as_view(), name='billing_update'),
    path('surgery/<int:pk>/cme/', CMEDataUpdateView.as_view(), name='cme_update'),
    path('surgery/<int:pk>/opme/', OPMEDataUpdateView.as_view(), name='opme_update'),
    path('surgery/<int:pk>/nursing/', NursingChecklistUpdateView.as_view(), name='nursing_update'),

    # Recepção
    path('reception/', ReceptionHomeView.as_view(), name='reception_home'),
    path('reception/patient/new/', PatientCreateReceptionView.as_view(), name='reception_patient_new'),
    path('reception/attendance/<int:patient_id>/open/', ReceptionQueueCreateView.as_view(), name='reception_queue_new'),
    path('reception/queue/', ReceptionQueueListView.as_view(), name='reception_queue'),
    path('reception/queue/<int:pk>/call/', ReceptionQueueCallView.as_view(), name='reception_queue_call'),
    path('reception/queue/<int:pk>/forward/', ReceptionQueueForwardView.as_view(), name='reception_queue_forward'),
    path('reception/queue/<int:pk>/finish/', ReceptionQueueFinishView.as_view(), name='reception_queue_finish'),
]
