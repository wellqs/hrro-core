from django.urls import path

from . import views

app_name = "fisioterapia"

urlpatterns = [
    path("", views.FisioHomeView.as_view(), name="home"),
    path("coordenador/", views.FisioCoordenadorView.as_view(), name="coordenador"),
    path("assistencia/", views.FisioAssistenciaView.as_view(), name="assistencia"),
    path("assistencia/delete/<int:report_id>/", views.FisioAssistenciaDeleteView.as_view(), name="assistencia_delete"),
]
