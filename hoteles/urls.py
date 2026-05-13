from django.urls import path
from . import views

app_name = 'hoteles'

urlpatterns = [
    path('', views.HotelListView.as_view(), name='lista'),
    path('nuevo/', views.HotelCreateView.as_view(), name='crear'),
    path('<int:pk>/', views.HotelDetailView.as_view(), name='detalle'),
    path('<int:pk>/editar/', views.HotelUpdateView.as_view(), name='editar'),
    path('<int:pk>/eliminar/', views.HotelDeleteView.as_view(), name='eliminar'),
    path('tipos/', views.TipoHabitacionListView.as_view(), name='tipos_lista'),
    path('tipos/nuevo/', views.TipoHabitacionCreateView.as_view(), name='tipos_crear'),
    path('tipos/<int:pk>/editar/', views.TipoHabitacionUpdateView.as_view(), name='tipos_editar'),
    path('tipos/<int:pk>/eliminar/', views.TipoHabitacionDeleteView.as_view(), name='tipos_eliminar'),
    path('habitaciones/', views.HabitacionListView.as_view(), name='habitaciones_lista'),
    path('habitaciones/nueva/', views.HabitacionCreateView.as_view(), name='habitaciones_crear'),
    path('habitaciones/<int:pk>/editar/', views.HabitacionUpdateView.as_view(), name='habitaciones_editar'),
    path('habitaciones/<int:pk>/eliminar/', views.HabitacionDeleteView.as_view(), name='habitaciones_eliminar'),
]
