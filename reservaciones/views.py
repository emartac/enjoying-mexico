from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages

from .models import Reservacion, ClienteReservacion, Pago
from .forms import ReservacionForm, AgregarClienteForm, PagoForm
from .utils import generar_pdf_reservacion, enviar_email_reservacion, enviar_pases_abordaje


class ReservacionListView(LoginRequiredMixin, ListView):
    model = Reservacion
    template_name = 'reservaciones/lista.html'
    context_object_name = 'reservaciones'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('viaje', 'habitacion__tipo')
        estado = self.request.GET.get('estado', '')
        if estado:
            qs = qs.filter(estado=estado)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(codigo__icontains=q) | qs.filter(viaje__nombre__icontains=q) | qs.filter(viaje__destino__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estados'] = Reservacion.ESTADOS
        ctx['estado_sel'] = self.request.GET.get('estado', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ReservacionDetailView(LoginRequiredMixin, DetailView):
    model = Reservacion
    template_name = 'reservaciones/detalle.html'
    context_object_name = 'reservacion'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['clientes_res'] = self.object.clientes_reservacion.select_related('cliente').order_by('-es_titular', 'cliente__apellido')
        ctx['pagos'] = self.object.pagos.order_by('-fecha')
        ctx['agregar_form'] = AgregarClienteForm(self.object)
        ctx['pago_form'] = PagoForm()
        return ctx


class ReservacionCreateView(LoginRequiredMixin, CreateView):
    model = Reservacion
    form_class = ReservacionForm
    template_name = 'reservaciones/formulario.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        viaje_id = self.request.GET.get('viaje') or self.request.POST.get('viaje')
        if viaje_id:
            kwargs['viaje_id'] = int(viaje_id)
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        viaje_id = self.request.GET.get('viaje')
        if viaje_id:
            initial['viaje'] = viaje_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nueva reservación'
        return ctx

    def get_success_url(self):
        return reverse('reservaciones:detalle', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        viaje = form.cleaned_data['viaje']
        form.instance.fecha_checkin = viaje.fecha_salida
        form.instance.fecha_checkout = viaje.fecha_regreso
        response = super().form_valid(form)
        messages.success(self.request, f'Reservación {self.object.codigo} creada. Agrega los clientes a continuación.')
        return response


class ReservacionUpdateView(LoginRequiredMixin, UpdateView):
    model = Reservacion
    form_class = ReservacionForm
    template_name = 'reservaciones/formulario.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['viaje_id'] = self.object.viaje_id
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar reservación {self.object.codigo}'
        return ctx

    def get_success_url(self):
        return reverse('reservaciones:detalle', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        viaje = form.cleaned_data['viaje']
        form.instance.fecha_checkin = viaje.fecha_salida
        form.instance.fecha_checkout = viaje.fecha_regreso
        messages.success(self.request, 'Reservación actualizada.')
        return super().form_valid(form)


class ReservacionDeleteView(LoginRequiredMixin, DeleteView):
    model = Reservacion
    template_name = 'reservaciones/confirmar_eliminar.html'
    success_url = reverse_lazy('reservaciones:lista')
    context_object_name = 'objeto'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Eliminar reservación {self.object.codigo}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Reservación {self.object.codigo} eliminada.')
        return super().form_valid(form)


@login_required
def cambiar_estado(request, pk, nuevo_estado):
    reservacion = get_object_or_404(Reservacion, pk=pk)
    if request.method == 'POST':
        reservacion.estado = nuevo_estado
        reservacion.save()
        etiquetas = dict(Reservacion.ESTADOS)
        messages.success(request, f'Reservación {reservacion.codigo} marcada como {etiquetas[nuevo_estado]}.')
    return redirect('reservaciones:detalle', pk=pk)


@login_required
def agregar_cliente(request, pk):
    reservacion = get_object_or_404(Reservacion, pk=pk)
    if request.method == 'POST':
        form = AgregarClienteForm(reservacion, request.POST)
        if form.is_valid():
            cliente = form.cleaned_data['cliente']
            es_titular = form.cleaned_data['es_titular']
            if es_titular:
                reservacion.clientes_reservacion.filter(es_titular=True).update(es_titular=False)
            ClienteReservacion.objects.create(
                reservacion=reservacion,
                cliente=cliente,
                es_titular=es_titular,
            )
            messages.success(request, f'{cliente} agregado a la reservación.')
        else:
            messages.error(request, 'Por favor selecciona un cliente válido.')
    return redirect('reservaciones:detalle', pk=pk)


@login_required
def remover_cliente(request, pk, cr_pk):
    cr = get_object_or_404(ClienteReservacion, pk=cr_pk, reservacion_id=pk)
    if request.method == 'POST':
        nombre = str(cr.cliente)
        cr.delete()
        messages.success(request, f'{nombre} removido de la reservación.')
    return redirect('reservaciones:detalle', pk=pk)


@login_required
def marcar_titular(request, pk, cr_pk):
    cr = get_object_or_404(ClienteReservacion, pk=cr_pk, reservacion_id=pk)
    if request.method == 'POST':
        ClienteReservacion.objects.filter(reservacion_id=pk, es_titular=True).update(es_titular=False)
        cr.es_titular = True
        cr.save()
        messages.success(request, f'{cr.cliente} marcado como titular.')
    return redirect('reservaciones:detalle', pk=pk)


class PagoCreateView(LoginRequiredMixin, CreateView):
    model = Pago
    form_class = PagoForm
    template_name = 'reservaciones/pago_formulario.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.reservacion = get_object_or_404(Reservacion, pk=kwargs['pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['reservacion'] = self.reservacion
        ctx['titulo'] = 'Registrar pago'
        return ctx

    def form_valid(self, form):
        form.instance.reservacion = self.reservacion
        messages.success(self.request, 'Pago registrado exitosamente.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('reservaciones:detalle', kwargs={'pk': self.reservacion.pk})


class PagoUpdateView(LoginRequiredMixin, UpdateView):
    model = Pago
    form_class = PagoForm
    template_name = 'reservaciones/pago_formulario.html'
    pk_url_kwarg = 'pago_pk'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.reservacion = get_object_or_404(Reservacion, pk=kwargs['pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['reservacion'] = self.reservacion
        ctx['titulo'] = 'Editar pago'
        return ctx

    def get_success_url(self):
        return reverse('reservaciones:detalle', kwargs={'pk': self.reservacion.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Pago actualizado.')
        return super().form_valid(form)


@login_required
def pago_eliminar(request, pk, pago_pk):
    pago = get_object_or_404(Pago, pk=pago_pk, reservacion_id=pk)
    if request.method == 'POST':
        pago.delete()
        messages.success(request, 'Pago eliminado.')
    return redirect('reservaciones:detalle', pk=pk)


@login_required
def generar_pdf(request, pk):
    reservacion = get_object_or_404(Reservacion, pk=pk)
    pdf_bytes = generar_pdf_reservacion(request, reservacion)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="reservacion_{reservacion.codigo}.pdf"'
    return response


@login_required
def enviar_pases(request, pk):
    reservacion = get_object_or_404(Reservacion, pk=pk)
    if request.method == 'POST':
        try:
            enviar_pases_abordaje(request, reservacion)
            messages.success(request, f'Pases de abordaje enviados a {reservacion.num_clientes} pasajero(s).')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al enviar los pases: {e}')
    return redirect('reservaciones:detalle', pk=pk)


@login_required
def enviar_email_confirmacion(request, pk):
    reservacion = get_object_or_404(Reservacion, pk=pk)
    if request.method == 'POST':
        try:
            enviar_email_reservacion(request, reservacion)
            messages.success(request, 'Email de confirmación enviado exitosamente.')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al enviar el email: {e}')
    return redirect('reservaciones:detalle', pk=pk)
