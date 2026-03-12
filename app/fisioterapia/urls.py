from django.urls import path

from . import views

app_name = "fisioterapia"

urlpatterns = [
    path("", views.FisioHomeView.as_view(), name="home"),
    path("coordenador/", views.FisioCoordenadorView.as_view(), name="coordenador"),
    path("coordenador/equipe/", views.FisioEquipeView.as_view(), name="equipe"),
    path("coordenador/equipe/deactivate/<int:user_id>/", views.FisioEquipeDeactivateView.as_view(), name="equipe_deactivate"),
    path("coordenador/equipe/reactivate/<int:user_id>/", views.FisioEquipeReactivateView.as_view(), name="equipe_reactivate"),
    path("coordenador/relatorios/novo/", views.FisioCoordinatorReportView.as_view(), name="coordenador_report_new"),
    path("coordenador/relatorios/<int:report_id>/", views.FisioCoordinatorReportDetailView.as_view(), name="coordenador_report_detail"),
    path("coordenador/relatorios/<int:report_id>/editar/", views.FisioCoordinatorReportView.as_view(), name="coordenador_report_edit"),
    path("coordenador/relatorios/<int:report_id>/excluir/", views.FisioCoordinatorReportDeleteView.as_view(), name="coordenador_report_delete"),
    path("coordenador/relatorios/<int:report_id>/pdf/", views.FisioCoordinatorReportPDFView.as_view(), name="coordenador_report_pdf"),
    path("coordenador/relatorios/pdf/", views.FisioCoordinatorReportsPDFView.as_view(), name="coordenador_reports_pdf"),
    path("assistencia/", views.FisioAssistenciaView.as_view(), name="assistencia"),
    path("assistencia/delete/<int:report_id>/", views.FisioAssistenciaDeleteView.as_view(), name="assistencia_delete"),
]
