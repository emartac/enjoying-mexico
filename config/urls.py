from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from .views import serve_sitio_publico, tablero

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticación
    path('', include('django.contrib.auth.urls')),

    # Inicio del sistema — tablero con próximas salidas, saldos y pagos
    path('panel/', tablero, name='home'),

    # Apps del sistema de reservas
    path('clientes/', include('clientes.urls', namespace='clientes')),
    path('hoteles/', include('hoteles.urls', namespace='hoteles')),
    path('viajes/', include('viajes.urls', namespace='viajes')),
    path('reservaciones/', include('reservaciones.urls', namespace='reservaciones')),

    # El índice estático viejo (enlazado desde "VIAJES" en las páginas antiguas)
    # redirige al índice dinámico
    path('index.html', RedirectView.as_view(url='/', permanent=False)),

    # Tours (índice dinámico + panel + detalle)
    path('', include('tours.urls', namespace='tours')),

    # Sitio estático (páginas HTML antiguas y assets) — SIEMPRE AL FINAL
    re_path(r'^(?P<path>.+)$', serve_sitio_publico, name='sitio_publico_archivo'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
