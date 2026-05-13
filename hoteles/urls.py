from django.urls import path
from . import views

app_name = 'hoteles'

urlpatterns = [
    path('tipos/', views.TipoHabitacionListView.as_view(), name='tipos_lista'),
    path('tipos/nuevo/', views.TipoHabitacionCreateView.as_view(), name='tipos_crear'),
    path('tipos/<int:pk>/editar/', views.TipoHabitacionUpdateView.as_view(), name='tipos_editar'),
    path('tipos/<int:pk>/eliminar/', views.TipoHabitacionDeleteView.as_view(), name='tipos_eliminar'),
    path('', views.HabitacionListView.as_view(), name='habitaciones_lista'),
    path('nueva/', views.HabitacionCreateView.as_view(), name='habitaciones_crear'),
    path('<int:pk>/editar/', views.HabitacionUpdateView.as_view(), name='habitaciones_editar'),
    path('<int:pk>/eliminar/', views.HabitacionDeleteView.as_view(), name='habitaciones_eliminar'),
]
