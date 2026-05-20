from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from .views import HomeView, serve_sitio_publico

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticación
    path('', include('django.contrib.auth.urls')),

    # Dashboard (requiere login)
    path('panel/', HomeView.as_view(), name='home'),

    # Apps del sistema de reservas
    path('clientes/', include('clientes.urls', namespace='clientes')),
    path('hoteles/', include('hoteles.urls', namespace='hoteles')),
    path('viajes/', include('viajes.urls', namespace='viajes')),
    path('reservaciones/', include('reservaciones.urls', namespace='reservaciones')),

    # Tours (índice dinámico + panel + detalle)
    path('', include('tours.urls', namespace='tours')),

    # Sitio estático (páginas HTML antiguas y assets) — SIEMPRE AL FINAL
    re_path(r'^(?P<path>.+)$', serve_sitio_publico, name='sitio_publico_archivo'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
