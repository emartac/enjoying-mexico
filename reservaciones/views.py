from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.template.loader import render_to_string
from django.contrib import messages
from django.db.models.deletion import ProtectedError

from django.db import transaction
from django.db.models import Prefetch
from clientes.models import Cliente
from .models import Reservacion, ClienteReservacion, Pago
from .forms import ReservacionForm, AgregarClienteForm, PagoForm
from .utils import generar_pdf_reservacion, enviar_email_reservacion, enviar_pases_abordaje


class ReservacionListView(LoginRequiredMixin, ListView):
    model = Reservacion
    template_name = 'reservaciones/lista.html'
    context_object_name = 'reservaciones'

    PERIODOS = [('proximos', 'Próximos y en curso'), ('pasados', 'Pasados'), ('todos', 'Todos')]

    def _params(self):
        g = self.request.GET
        return {
            'q': g.get('q', '').strip(),
            'estado': g.get('estado', ''),
            'viaje': g.get('viaje', ''),
            'saldo': g.get('saldo', '') == '1',
            'periodo': g.get('periodo', 'proximos') if g.get('periodo') in dict(self.PERIODOS) else 'proximos',
            'orden': 'saldo' if g.get('orden') == 'saldo' else 'fecha',
        }

    def get_queryset(self):
        import datetime
        from django.db.models import Q
        p = self._params()
        qs = super().get_queryset().select_related('viaje', 'habitacion__tipo').prefetch_related(
            Prefetch(
                'clientes_reservacion',
                queryset=ClienteReservacion.objects.filter(es_titular=True).select_related('cliente'),
                to_attr='titulares',
            )
        ).order_by('viaje__fecha_salida', 'viaje__nombre', '-creado')

        hoy = datetime.date.today()
        if p['periodo'] == 'proximos':
            qs = qs.filter(viaje__fecha_regreso__gte=hoy)
        elif p['periodo'] == 'pasados':
            qs = qs.filter(viaje__fecha_regreso__lt=hoy).order_by('-viaje__fecha_salida', 'viaje__nombre', '-creado')
        if p['estado']:
            qs = qs.filter(estado=p['estado'])
        if p['viaje'].isdigit():
            qs = qs.filter(viaje_id=int(p['viaje']))
        # Cada palabra debe coincidir con el código, el viaje o algún cliente de la reservación
        for palabra in p['q'].split():
            qs = qs.filter(
                Q(codigo__icontains=palabra) | Q(viaje__nombre__icontains=palabra) |
                Q(viaje__destino__icontains=palabra) |
                Q(clientes__nombre__icontains=palabra) | Q(clientes__apellido__icontains=palabra) |
                Q(clientes__telefono__icontains=palabra) | Q(clientes__email__icontains=palabra)
            )
        return qs.distinct()

    def get_context_data(self, **kwargs):
        from collections import OrderedDict
        from viajes.models import Viaje
        from .resumen import anotar_finanzas, sumar
        ctx = super().get_context_data(**kwargs)
        p = self._params()

        reservaciones = anotar_finanzas(list(ctx['reservaciones']))
        if p['saldo']:
            reservaciones = [r for r in reservaciones if r.fin_saldo > 0]

        grupos = OrderedDict()
        for res in reservaciones:
            grupos.setdefault(res.viaje_id, {'viaje': res.viaje, 'reservaciones': []})['reservaciones'].append(res)
        for g in grupos.values():
            if p['orden'] == 'saldo':
                g['reservaciones'].sort(key=lambda r: r.fin_saldo, reverse=True)
            g['total'] = sumar(g['reservaciones'], 'fin_total')
            g['pagado'] = sumar(g['reservaciones'], 'fin_pagado')
            g['saldo'] = sumar(g['reservaciones'], 'fin_saldo')
            g['personas'] = sum(len(r.clientes_reservacion.all()) for r in g['reservaciones'] if r.estado != 'cancelada')

        ctx['grupos'] = list(grupos.values())
        ctx['num_resultados'] = len(reservaciones)
        ctx['gran_saldo'] = sumar(reservaciones, 'fin_saldo')
        ctx['gran_pagado'] = sumar(reservaciones, 'fin_pagado')
        ctx['estados'] = Reservacion.ESTADOS
        ctx['periodos'] = self.PERIODOS
        ctx['viajes_filtro'] = Viaje.objects.filter(reservaciones__isnull=False).distinct().order_by('-fecha_salida')
        ctx['p'] = p
        ctx['hay_filtros'] = any([p['q'], p['estado'], p['viaje'], p['saldo'], p['orden'] == 'saldo', p['periodo'] != 'proximos'])
        return ctx


class ReservacionDetailView(LoginRequiredMixin, DetailView):
    model = Reservacion
    template_name = 'reservaciones/detalle.html'
    context_object_name = 'reservacion'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['clientes_res'] = self.object.clientes_reservacion.select_related('cliente').order_by('-es_titular', 'cliente__apellido')
        clientes = [cr.cliente for cr in ctx['clientes_res']]
        titular = next((cr.cliente for cr in ctx['clientes_res'] if cr.es_titular), None)
        ctx['titular'] = titular
        if titular is None:
            ctx['aviso_titular'] = 'Esta reservación no tiene titular.'
        elif not titular.datos_contacto_completos:
            ctx['aviso_titular'] = f'Al titular {titular} le falta {" y ".join(titular.datos_faltantes)}.'
        ctx['con_correo'] = [c for c in clientes if c.email]
        ctx['sin_correo'] = [c for c in clientes if not c.email]
        ctx['desglose'] = self.object.desglose_precio() if self.object.precio_personalizado is None else []
        ctx['pagos'] = self.object.pagos.order_by('-fecha')
        ctx['agregar_form'] = AgregarClienteForm(self.object)
        ctx['pago_form'] = PagoForm()
        if self.object.habitacion:
            ocupados = ClienteReservacion.objects.filter(
                reservacion__habitacion=self.object.habitacion,
                reservacion__viaje=self.object.viaje,
            ).exclude(reservacion__estado='cancelada').count()
            ctx['hab_ocupados'] = ocupados
            ctx['hab_llena'] = ocupados >= self.object.habitacion.tipo.capacidad
        else:
            ctx['hab_ocupados'] = 0
            ctx['hab_llena'] = False
        return ctx


class ClientesReservacionMixin:
    """Clientes elegidos en la misma pantalla de crear/editar reservación."""

    def _viaje_id(self):
        valor = self.request.GET.get('viaje') or self.request.POST.get('viaje')
        if valor and str(valor).isdigit():
            return int(valor)
        return getattr(self.object, 'viaje_id', None) if getattr(self, 'object', None) else None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        viaje_id = self._viaje_id()
        if viaje_id:
            kwargs['viaje_id'] = viaje_id
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        viaje_id = self.request.GET.get('viaje')
        if viaje_id:
            initial['viaje'] = viaje_id
        return initial

    def _clientes_seleccionados(self):
        """[{id, nombre, email, telefono, frecuente, titular}] según POST, la URL
        (al cambiar de viaje) o, al editar, los clientes que ya tiene la reservación."""
        data = self.request.POST if self.request.method == 'POST' else self.request.GET
        obj = getattr(self, 'object', None)
        if self.request.method != 'POST' and 'clientes' not in data and obj and obj.pk:
            existentes = obj.clientes_reservacion.select_related('cliente').order_by('-es_titular', 'pk')
            ids = [cr.cliente_id for cr in existentes]
            titular = next((str(cr.cliente_id) for cr in existentes if cr.es_titular), '')
        else:
            ids = []
            for v in data.getlist('clientes'):
                if v.isdigit() and int(v) not in ids:
                    ids.append(int(v))
            titular = data.get('titular', '')
        encontrados = Cliente.objects.in_bulk(ids)
        seleccion = [
            {'id': c.pk, 'nombre': str(c), 'email': c.email or '', 'telefono': c.telefono or '',
             'frecuente': c.viajero_frecuente, 'tingo': c.es_tingo, 'no_deseado': c.no_deseado,
             'motivo_no_deseado': c.motivo_no_deseado, 'titular': str(c.pk) == titular}
            for c in (encontrados.get(i) for i in ids) if c
        ]
        if seleccion and not any(s['titular'] for s in seleccion):
            seleccion[0]['titular'] = True
        return seleccion

    def _precios_para_js(self):
        """Precios por persona para calcular el total en vivo en el formulario."""
        from viajes.models import Viaje, ViajeHabitacion
        viaje_id = self._viaje_id()
        if not viaje_id:
            return {}
        viaje = Viaje.objects.filter(pk=viaje_id).first()
        if not viaje:
            return {}
        num = lambda d: float(d) if d is not None else None
        return {
            'viaje': [num(viaje.precio_por_persona or 0), num(viaje.precio_frecuente)],
            'habitaciones': {
                str(vh.habitacion_id): [num(vh.precio_total), num(vh.precio_frecuente)]
                for vh in ViajeHabitacion.objects.filter(viaje=viaje)
            },
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['clientes_seleccionados'] = self._clientes_seleccionados()
        ctx['precios'] = self._precios_para_js()
        return ctx

    def _validar_clientes(self, form, seleccion):
        """Devuelve True si los clientes son válidos; si no, agrega el error al formulario."""
        if not seleccion:
            form.add_error(None, 'Agrega al menos un cliente: la reservación necesita un titular.')
            return False
        titular = next(s for s in seleccion if s['titular'])
        faltan = [n for n, v in (('correo', titular['email']), ('teléfono', titular['telefono'])) if not v]
        if faltan:
            form.add_error(None,
                f'El titular {titular["nombre"]} no tiene {" ni ".join(faltan)}. '
                'Completa sus datos o elige como titular a otro cliente que los tenga.')
            return False

        habitacion = form.cleaned_data.get('habitacion')
        viaje = form.cleaned_data['viaje']
        if habitacion:
            ocupados = ClienteReservacion.objects.filter(
                reservacion__habitacion=habitacion, reservacion__viaje=viaje,
            ).exclude(reservacion__estado='cancelada')
            if getattr(self, 'object', None) and self.object.pk:
                ocupados = ocupados.exclude(reservacion_id=self.object.pk)
            libres = habitacion.tipo.capacidad - ocupados.count()
            if len(seleccion) > libres:
                form.add_error('habitacion',
                    f'La habitación {habitacion.numero} solo tiene {max(libres, 0)} lugar(es) libre(s) '
                    f'y seleccionaste {len(seleccion)} cliente(s).')
                return False
        return True

    def _guardar_clientes(self, reservacion, seleccion):
        """Deja en la reservación exactamente los clientes elegidos, con su titular."""
        ids = [s['id'] for s in seleccion]
        titular_id = next(s['id'] for s in seleccion if s['titular'])
        reservacion.clientes_reservacion.exclude(cliente_id__in=ids).delete()
        existentes = {cr.cliente_id: cr for cr in reservacion.clientes_reservacion.all()}
        for cid in ids:
            es_titular = cid == titular_id
            cr = existentes.get(cid)
            if cr is None:
                ClienteReservacion.objects.create(reservacion=reservacion, cliente_id=cid, es_titular=es_titular)
            elif cr.es_titular != es_titular:
                cr.es_titular = es_titular
                cr.save(update_fields=['es_titular'])

    def form_valid(self, form):
        seleccion = self._clientes_seleccionados()
        if not self._validar_clientes(form, seleccion):
            return self.form_invalid(form)
        viaje = form.cleaned_data['viaje']
        form.instance.fecha_checkin = viaje.fecha_salida
        form.instance.fecha_checkout = viaje.fecha_regreso
        with transaction.atomic():
            response = super().form_valid(form)
            self._guardar_clientes(self.object, seleccion)
        messages.success(self.request, self.mensaje_exito(len(seleccion)))
        return response

    def get_success_url(self):
        return reverse('reservaciones:detalle', kwargs={'pk': self.object.pk})


class ReservacionCreateView(LoginRequiredMixin, ClientesReservacionMixin, CreateView):
    model = Reservacion
    form_class = ReservacionForm
    template_name = 'reservaciones/formulario.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nueva reservación'
        return ctx

    def mensaje_exito(self, num):
        return f'Reservación {self.object.codigo} creada con {num} cliente(s).'


class ReservacionUpdateView(LoginRequiredMixin, ClientesReservacionMixin, UpdateView):
    model = Reservacion
    form_class = ReservacionForm
    template_name = 'reservaciones/formulario.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar reservación {self.object.codigo}'
        return ctx

    def mensaje_exito(self, num):
        return f'Reservación actualizada ({num} cliente(s)).'


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
        try:
            messages.success(self.request, f'Reservación {self.object.codigo} eliminada.')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, f'No se puede eliminar {self.object.codigo}: tiene pagos u otros registros asociados.')
            return redirect('reservaciones:detalle', pk=self.object.pk)


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
        if reservacion.habitacion:
            ocupados = ClienteReservacion.objects.filter(
                reservacion__habitacion=reservacion.habitacion,
                reservacion__viaje=reservacion.viaje,
            ).exclude(reservacion__estado='cancelada').count()
            if ocupados >= reservacion.habitacion.tipo.capacidad:
                messages.error(request,
                    f'La habitación {reservacion.habitacion.numero} ya está llena '
                    f'({ocupados}/{reservacion.habitacion.tipo.capacidad} lugar(es)).')
                return redirect('reservaciones:detalle', pk=pk)
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

    def _es_ajax(self):
        return self.request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def form_valid(self, form):
        form.instance.reservacion = self.reservacion
        messages.success(self.request, 'Pago registrado exitosamente.')
        respuesta = super().form_valid(form)
        if self._es_ajax():
            return JsonResponse({'ok': True, 'redirect': self.get_success_url()})
        return respuesta

    def form_invalid(self, form):
        if self._es_ajax():
            html = render_to_string(
                'reservaciones/partials/pago_form_campos.html',
                {'form': form}, request=self.request,
            )
            return JsonResponse({'ok': False, 'html': html}, status=400)
        return super().form_invalid(form)

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
        if pago.comprobante:
            try:
                pago.comprobante.delete(save=False)
            except OSError:
                pass
        pago.delete()
        messages.success(request, 'Pago eliminado.')
    return redirect('reservaciones:detalle', pk=pk)


@login_required
def pago_comprobante(request, pk, pago_pk):
    """Muestra el comprobante solo a usuarios con sesión (no es un archivo público)."""
    pago = get_object_or_404(Pago, pk=pago_pk, reservacion_id=pk)
    if not pago.comprobante:
        raise Http404
    try:
        archivo = pago.comprobante.open('rb')
    except FileNotFoundError:
        raise Http404
    respuesta = FileResponse(archivo, content_type='image/jpeg')
    respuesta['Cache-Control'] = 'private, max-age=3600'
    return respuesta


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
            enviados, omitidos = enviar_pases_abordaje(request, reservacion)
            messages.success(request, f'Pases de abordaje enviados a {enviados} viajero(s).')
            if omitidos:
                messages.warning(request, 'Sin correo, no recibieron su pase: ' + ', '.join(str(c) for c in omitidos) + '.')
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
            messages.success(request, 'Correo de confirmación enviado.')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al enviar el email: {e}')
    return redirect('reservaciones:detalle', pk=pk)
