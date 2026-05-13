from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.ClienteListView.as_view(), name='lista'),
    path('nuevo/', views.ClienteCreateView.as_view(), name='crear'),
    path('buscar/', views.cliente_buscar, name='buscar'),
    path('crear-ajax/', views.cliente_crear_ajax, name='crear_ajax'),
    path('<int:pk>/', views.ClienteDetailView.as_view(), name='detalle'),
    path('<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='editar'),
    path('<int:pk>/eliminar/', views.ClienteDeleteView.as_view(), name='eliminar'),
]
