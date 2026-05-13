from django.contrib import admin
from django.urls import path, include
from .views import HomeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('django.contrib.auth.urls')),
    path('', HomeView.as_view(), name='home'),
    path('clientes/', include('clientes.urls', namespace='clientes')),
    path('hoteles/', include('hoteles.urls', namespace='hoteles')),
    path('viajes/', include('viajes.urls', namespace='viajes')),
    path('reservaciones/', include('reservaciones.urls', namespace='reservaciones')),
]
