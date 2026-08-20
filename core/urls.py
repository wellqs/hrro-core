# Em core/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    LandingView,
    HomeView,
    OrganogramaView,
    OrgUnitDetailView,
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
    NSPLandingView,
    NSPClinicLandingView,
    NSPClinicBedListView,
    NSPClinicBedGroupView,
    NSPEquipeView,
    NSPEventoAdversoView,
    NSPEventoAdversoBulkView,
    NSPEventoAdversoUpdateView,
    NSPEventoAdversoDeleteView,
    NSPEventoAdversoListView,
    NSPEventoAdversoPDFView,
    NIREntryView,
    NIRPanelView,
    # --- IMPORTAÇÃO ADICIONADA PARA A VIEW DA LISTA DE LEITOS DA CLÍNICA ---
    ClinicBedListView,
    NIRHospitalizationCreateView,
    NIRHospitalizationUpdateView,
    NIRHospitalizationDischargeView,
    NIRHospitalizationHistoryView,
    NIRCensoUploadView,
    PatientDocumentListView,
    ExamsLandingView,
    PatientExamsView,
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
    # Apresentação institucional (antes do login)
    path('', LandingView.as_view(), name='landing'),

    # URLs de Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Painel (organograma institucional, tela principal após login)
    path('painel/', HomeView.as_view(), name='home'),
    path('painel/organograma/', OrganogramaView.as_view(), name='organograma'),

    # URLs do Dashboard e CRUD de Cirurgias
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('surgeries/', SurgeryListView.as_view(), name='surgery_list'),
    path('surgery/new/', SurgeryCreateView.as_view(), name='surgery_create'),
    path('surgery/<int:pk>/', SurgeryDetailView.as_view(), name='surgery_detail'),
    path('surgery/<int:pk>/update/', SurgeryUpdateView.as_view(), name='surgery_update'),

    # URLs de Indicadores
    path('indicators/', IndicatorDashboardView.as_view(), name='indicator_dashboard'),
    path('painel/setor/NSP/dashboard/', IndicatorDashboardView.as_view(), name='nsp_dashboard'),
    path('indicators/pdf/', IndicatorPDFView.as_view(), name='indicator_pdf'),
    path('indicators/history/', IndicatorHistoryView.as_view(), name='indicator_history'),
    path('indicators/analysis/', IndicatorAnalysisView.as_view(), name='indicator_analysis'),

    # Setor NSP (Núcleo de Segurança do Paciente) — módulo implantado no organograma
    path('painel/setor/NSP/', NSPLandingView.as_view(), name='nsp_landing'),
    path('painel/setor/NSP/coleta/', NSPClinicLandingView.as_view(), name='nsp_coleta'),
    path('painel/setor/NSP/coleta/clinic/<slug:clinic_name_slug>/', NSPClinicBedListView.as_view(), name='nsp_coleta_clinic'),
    path('painel/setor/NSP/coleta/grupo/<slug:group_key>/', NSPClinicBedGroupView.as_view(), name='nsp_coleta_group'),
    path('painel/setor/NSP/equipe/', NSPEquipeView.as_view(), name='nsp_equipe'),
    path('painel/setor/NSP/eventos/paciente/<int:patient_id>/', NSPEventoAdversoView.as_view(), name='nsp_evento_adverso'),
    path('painel/setor/NSP/eventos/lote/', NSPEventoAdversoBulkView.as_view(), name='nsp_evento_adverso_bulk'),
    path('painel/setor/NSP/eventos/<int:pk>/editar/', NSPEventoAdversoUpdateView.as_view(), name='nsp_evento_adverso_edit'),
    path('painel/setor/NSP/eventos/<int:pk>/excluir/', NSPEventoAdversoDeleteView.as_view(), name='nsp_evento_adverso_delete'),
    path('painel/setor/NSP/eventos/', NSPEventoAdversoListView.as_view(), name='nsp_eventos_list'),
    path('painel/setor/NSP/eventos/pdf/', NSPEventoAdversoPDFView.as_view(), name='nsp_eventos_pdf'),

    # Setor NIR (Núcleo Interno de Regulação) — módulo implantado no organograma
    path('painel/setor/NIR/', NIREntryView.as_view(), name='nir_entry'), # Página de entrada
    path('painel/setor/NIR/painel/', NIRPanelView.as_view(), name='nir_panel'), # Painel de leitos
    # --- NOVA URL ADICIONADA PARA A LISTA DE LEITOS DA CLÍNICA ---
    path('painel/setor/NIR/clinic/<slug:clinic_name_slug>/', ClinicBedListView.as_view(), name='clinic_bed_list'), # Página de detalhes da clínica
    path('painel/setor/NIR/hospitalization/new/', NIRHospitalizationCreateView.as_view(), name='nir_hospitalization_create'),
    path('painel/setor/NIR/hospitalization/new/bed/<int:bed_id>/', NIRHospitalizationCreateView.as_view(), name='nir_hospitalization_create_bed'),
    path('painel/setor/NIR/hospitalization/<int:pk>/edit/', NIRHospitalizationUpdateView.as_view(), name='nir_hospitalization_edit'),
    path('painel/setor/NIR/hospitalization/<int:pk>/discharge/', NIRHospitalizationDischargeView.as_view(), name='nir_hospitalization_discharge'),

    path('painel/setor/NIR/hospitalizations/', NIRHospitalizationHistoryView.as_view(), name='nir_hospitalization_history'),
    path('painel/setor/NIR/censo/upload/', NIRCensoUploadView.as_view(), name='nir_censo_upload'),
    path('painel/setor/NIR/patient/<int:patient_id>/documents/', PatientDocumentListView.as_view(), name='patient_documents'),

    path('exams/', ExamsLandingView.as_view(), name='exams_landing'),
    path('painel/setor/NIR/patient/<int:patient_id>/exams/', PatientExamsView.as_view(), name='patient_exams'),

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

    # Fallback: setores do organograma ainda sem módulo implantado (deve ficar por último,
    # depois das rotas específicas acima, para não capturar codigos como NSP/NIR/GFISIO)
    path('painel/setor/<slug:codigo>/', OrgUnitDetailView.as_view(), name='orgunit_detail'),
]
