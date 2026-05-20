from django.urls import path
from . import views

app_name = 'tours'

urlpatterns = [
    # Índice público (reemplaza al estático)
    path('', views.IndexView.as_view(), name='index'),

    # Detalle público de un tour
    path('tour/<slug:slug>/', views.TourDetailView.as_view(), name='detalle'),

    # Panel de administración de tours
    path('tours/panel/', views.TourPanelListView.as_view(), name='panel_lista'),
    path('tours/panel/nuevo/', views.tour_crear, name='crear'),
    path('tours/panel/<slug:slug>/editar/', views.tour_editar, name='editar'),
    path('tours/panel/<slug:slug>/eliminar/', views.tour_eliminar, name='eliminar'),
    path('tours/panel/<slug:slug>/carrusel/', views.carrusel_manage, name='carrusel'),
    path('tours/panel/<slug:slug>/itinerario/', views.itinerario_manage, name='itinerario'),
    path('tours/panel/<slug:slug>/itinerario/nuevo/', views.dia_crear, name='dia_crear'),
    path('tours/panel/<slug:slug>/itinerario/<int:dia_pk>/editar/', views.dia_editar, name='dia_editar'),
    path('tours/panel/<slug:slug>/itinerario/<int:dia_pk>/eliminar/', views.dia_eliminar, name='dia_eliminar'),
]
