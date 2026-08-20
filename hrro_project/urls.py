from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Setor GFISIO (Gerência de Fisioterapia) — módulo implantado no organograma.
    # Precisa vir antes do include de core.urls, cujo fallback genérico
    # 'painel/setor/<slug:codigo>/' também casaria com /painel/setor/GFISIO/.
    path('painel/setor/GFISIO/', include('app.fisioterapia.urls')),

    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

