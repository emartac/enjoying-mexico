from django.urls import path
from . import views

app_name = 'reservaciones'

urlpatterns = [
    path('', views.ReservacionListView.as_view(), name='lista'),
    path('nueva/', views.ReservacionCreateView.as_view(), name='crear'),
    path('<int:pk>/', views.ReservacionDetailView.as_view(), name='detalle'),
    path('<int:pk>/editar/', views.ReservacionUpdateView.as_view(), name='editar'),
    path('<int:pk>/eliminar/', views.ReservacionDeleteView.as_view(), name='eliminar'),
    path('<int:pk>/confirmar/', views.cambiar_estado, {'nuevo_estado': 'confirmada'}, name='confirmar'),
    path('<int:pk>/cancelar/', views.cambiar_estado, {'nuevo_estado': 'cancelada'}, name='cancelar'),
    path('<int:pk>/completar/', views.cambiar_estado, {'nuevo_estado': 'completada'}, name='completar'),
    path('<int:pk>/clientes/agregar/', views.agregar_cliente, name='agregar_cliente'),
    path('<int:pk>/clientes/<int:cr_pk>/remover/', views.remover_cliente, name='remover_cliente'),
    path('<int:pk>/clientes/<int:cr_pk>/titular/', views.marcar_titular, name='marcar_titular'),
    path('<int:pk>/pagos/nuevo/', views.PagoCreateView.as_view(), name='pago_crear'),
    path('<int:pk>/pagos/<int:pago_pk>/editar/', views.PagoUpdateView.as_view(), name='pago_editar'),
    path('<int:pk>/pagos/<int:pago_pk>/eliminar/', views.pago_eliminar, name='pago_eliminar'),
    path('<int:pk>/pdf/', views.generar_pdf, name='pdf'),
    path('<int:pk>/enviar-email/', views.enviar_email_confirmacion, name='enviar_email'),
]
