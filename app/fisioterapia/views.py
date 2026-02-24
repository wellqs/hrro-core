from django.views.generic import TemplateView


class FisioHomeView(TemplateView):
    template_name = "fisioterapia/home.html"


class FisioCoordenadorView(TemplateView):
    template_name = "fisioterapia/coordenador.html"


class FisioAssistenciaView(TemplateView):
    template_name = "fisioterapia/assistencia.html"

# Create your views here.
