from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from clientes.models import Cliente
from viajes.models import Viaje
from reservaciones.models import Reservacion, Pago
from django.db.models import Sum


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_clientes'] = Cliente.objects.count()
        ctx['total_viajes'] = Viaje.objects.filter(activo=True).count()
        ctx['total_reservaciones'] = Reservacion.objects.count()
        ctx['pendientes'] = Reservacion.objects.filter(estado='pendiente').count()
        ctx['confirmadas'] = Reservacion.objects.filter(estado='confirmada').count()
        ctx['canceladas'] = Reservacion.objects.filter(estado='cancelada').count()
        ctx['recientes'] = (
            Reservacion.objects
            .select_related('viaje', 'habitacion__hotel', 'habitacion__tipo')
            .order_by('-creado')[:8]
        )
        return ctx
