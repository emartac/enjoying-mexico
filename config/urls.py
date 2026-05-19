from django.contrib import admin
from django.urls import path, include, re_path
from .views import HomeView, serve_sitio_publico

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticación (login / logout / password reset)
    path('', include('django.contrib.auth.urls')),

    # Dashboard (requiere login)
    path('panel/', HomeView.as_view(), name='home'),

    # Apps del sistema
    path('clientes/', include('clientes.urls', namespace='clientes')),
    path('hoteles/', include('hoteles.urls', namespace='hoteles')),
    path('viajes/', include('viajes.urls', namespace='viajes')),
    path('reservaciones/', include('reservaciones.urls', namespace='reservaciones')),

    # Sitio público estático — SIEMPRE AL FINAL
    # Sirve el HTML de Enjoying México en / y cualquier ruta no reconocida
    path('', serve_sitio_publico, {'path': ''}, name='sitio_publico'),
    re_path(r'^(?P<path>.+)$', serve_sitio_publico, name='sitio_publico_archivo'),
]
