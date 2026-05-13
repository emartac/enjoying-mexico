from django.urls import path
from . import views

app_name = 'viajes'

urlpatterns = [
    path('', views.ViajeListView.as_view(), name='lista'),
    path('nuevo/', views.ViajeCreateView.as_view(), name='crear'),
    path('<int:pk>/', views.ViajeDetailView.as_view(), name='detalle'),
    path('<int:pk>/editar/', views.ViajeUpdateView.as_view(), name='editar'),
    path('<int:pk>/eliminar/', views.ViajeDeleteView.as_view(), name='eliminar'),
    path('<int:pk>/habitaciones/', views.ViajeHabitacionesView.as_view(), name='habitaciones'),
]
