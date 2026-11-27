from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models.deletion import ProtectedError
from .models import Viaje, ViajeHabitacion
from .forms import ViajeForm, ViajeHabitacionForm, PuntoAbordajeFormSet, PreciosTipoForm


class ViajeListView(LoginRequiredMixin, ListView):
    model = Viaje
    template_name = 'viajes/lista.html'
    context_object_name = 'viajes'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(nombre__icontains=q) | qs.filter(destino__icontains=q)
        activo = self.request.GET.get('activo')
        if activo in ('1', '0'):
            qs = qs.filter(activo=(activo == '1'))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['activo'] = self.request.GET.get('activo', '')
        return ctx


class ViajeDetailView(LoginRequiredMixin, DetailView):
    model = Viaje
    template_name = 'viajes/detalle.html'
    context_object_name = 'viaje'

    def get_context_data(self, **kwargs):
        from reservaciones.models import ClienteReservacion
        from collections import defaultdict
        ctx = super().get_context_data(**kwargs)

        ctx['reservaciones'] = self.object.reservaciones.select_related(
            'habitacion__tipo'
        ).order_by('-creado')

        from collections import OrderedDict
        viajeros_qs = (
            ClienteReservacion.objects
            .filter(reservacion__viaje=self.object)
            .exclude(reservacion__estado='cancelada')
            .select_related('cliente', 'reservacion', 'reservacion__habitacion__tipo')
            .order_by('reservacion__codigo', '-es_titular', 'cliente__apellido')
        )
        grupos_viajeros = OrderedDict()
        for cr in viajeros_qs:
            rid = cr.reservacion_id
            if rid not in grupos_viajeros:
                grupos_viajeros[rid] = {'reservacion': cr.reservacion, 'viajeros': []}
            grupos_viajeros[rid]['viajeros'].append(cr)
        ctx['grupos_viajeros'] = list(grupos_viajeros.values())

        ctx['puntos_abordaje'] = self.object.puntos_abordaje.all()
        from hoteles.models import TipoHabitacion, Habitacion
        ctx['tipos_habitacion'] = TipoHabitacion.objects.all()
        ya_asignadas = self.object.viaje_habitaciones.values_list('habitacion_id', flat=True)
        ctx['habitaciones_disponibles'] = Habitacion.objects.select_related('tipo').exclude(pk__in=ya_asignadas).order_by('nombre_hotel', 'numero')

        habitaciones_reservadas = set(
            self.object.reservaciones
            .exclude(estado='cancelada')
            .values_list('habitacion_id', flat=True)
        )
        grupos = defaultdict(lambda: {
            'tipo': None, 'habitaciones': [], 'total': 0, 'reservadas': 0, 'disponibles': 0
        })
        viaje_habs = (
            self.object.viaje_habitaciones
            .select_related('habitacion__tipo')
            .order_by('habitacion__tipo__nombre')
        )
        for vh in viaje_habs:
            tipo_nombre = vh.habitacion.tipo.nombre
            g = grupos[tipo_nombre]
            g['tipo'] = vh.habitacion.tipo
            g['habitaciones'].append(vh)
            g['total'] += 1
            if vh.habitacion_id in habitaciones_reservadas:
                g['reservadas'] += 1
            else:
                g['disponibles'] += 1
        ctx['grupos_habitacion'] = dict(grupos)
        precios = {p.tipo_habitacion_id: p for p in self.object.precios.select_related('tipo_habitacion')}
        for g in grupos.values():
            g['precio'] = precios.get(g['tipo'].pk)
        ctx['precios_tipo'] = sorted(precios.values(), key=lambda p: (p.tipo_habitacion.capacidad, p.tipo_habitacion.nombre))
        total_capacidad = sum(
            vh.habitacion.tipo.capacidad
            for g in grupos.values()
            for vh in g['habitaciones']
        )
        ctx['total_viajeros'] = viajeros_qs.count()
        ctx['cupo'] = self.object.capacidad_maxima if self.object.capacidad_maxima > 0 else total_capacidad
        ctx['disponibles'] = ctx['cupo'] - ctx['total_viajeros'] if ctx['cupo'] else None
        return ctx


def _es_de_varios_dias(form):
    salida = form.cleaned_data.get('fecha_salida')
    regreso = form.cleaned_data.get('fecha_regreso')
    return bool(salida and regreso and regreso > salida)


class ViajeCreateView(LoginRequiredMixin, CreateView):
    model = Viaje
    form_class = ViajeForm
    template_name = 'viajes/formulario.html'
    success_url = reverse_lazy('viajes:lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nuevo viaje'
        ctx['abordaje_formset'] = PuntoAbordajeFormSet(self.request.POST or None, prefix='abordaje')
        ctx['precios_form'] = PreciosTipoForm(self.request.POST or None, prefix='precios')
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        abordaje_formset = ctx['abordaje_formset']
        precios_form = ctx['precios_form']
        varios_dias = _es_de_varios_dias(form)
        if abordaje_formset.is_valid() and (not varios_dias or precios_form.is_valid()):
            with transaction.atomic():
                self.object = form.save()
                abordaje_formset.instance = self.object
                abordaje_formset.save()
                if varios_dias:
                    precios_form.save(self.object)
            messages.success(self.request, 'Viaje creado exitosamente.')
            return redirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form))


class ViajeUpdateView(LoginRequiredMixin, UpdateView):
    model = Viaje
    form_class = ViajeForm
    template_name = 'viajes/formulario.html'

    def get_success_url(self):
        return reverse('viajes:detalle', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar viaje: {self.object.nombre}'
        ctx['abordaje_formset'] = PuntoAbordajeFormSet(self.request.POST or None, instance=self.object, prefix='abordaje')
        ctx['precios_form'] = PreciosTipoForm(self.request.POST or None, viaje=self.object, prefix='precios')
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        abordaje_formset = ctx['abordaje_formset']
        precios_form = ctx['precios_form']
        varios_dias = _es_de_varios_dias(form)
        if abordaje_formset.is_valid() and (not varios_dias or precios_form.is_valid()):
            with transaction.atomic():
                self.object = form.save()
                abordaje_formset.instance = self.object
                abordaje_formset.save()
                if varios_dias:
                    precios_form.save(self.object)
            messages.success(self.request, 'Viaje actualizado.')
            return redirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form))


class ViajeHabitacionesView(LoginRequiredMixin, DetailView):
    model = Viaje
    template_name = 'viajes/habitaciones.html'
    context_object_name = 'viaje'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservaciones = (
            self.object.reservaciones
            .exclude(estado='cancelada')
            .exclude(habitacion__isnull=True)
            .select_related('habitacion__tipo')
            .prefetch_related('clientes_reservacion__cliente')
            .order_by('habitacion__nombre_hotel', 'habitacion__numero')
        )
        habitaciones = []
        for res in reservaciones:
            ocupantes = list(res.clientes_reservacion.all())
            capacidad = res.habitacion.tipo.capacidad
            num_ocupantes = len(ocupantes)
            habitaciones.append({
                'reservacion': res,
                'habitacion': res.habitacion,
                'ocupantes': ocupantes,
                'num_ocupantes': num_ocupantes,
                'capacidad': capacidad,
                'lugares_libres': capacidad - num_ocupantes,
                'llena': num_ocupantes >= capacidad,
            })
        ctx['habitaciones'] = habitaciones
        return ctx


class ViajeHabitacionAgregarView(LoginRequiredMixin, CreateView):
    model = ViajeHabitacion
    form_class = ViajeHabitacionForm
    template_name = 'viajes/habitacion_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.viaje = get_object_or_404(Viaje, pk=kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['viaje'] = self.viaje
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['viaje'] = self.viaje
        ctx['titulo'] = f'Agregar habitación — {self.viaje.nombre}'
        return ctx

    def form_valid(self, form):
        form.instance.viaje = self.viaje
        messages.success(self.request, 'Habitación agregada al viaje.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('viajes:detalle', kwargs={'pk': self.viaje.pk})


@login_required
def viaje_habitacion_editar(request, pk, vh_pk):
    viaje = get_object_or_404(Viaje, pk=pk)
    vh = get_object_or_404(ViajeHabitacion, pk=vh_pk, viaje=viaje)
    if request.method == 'POST':
        form = ViajeHabitacionForm(request.POST, instance=vh)
        if form.is_valid():
            form.save()
            messages.success(request, 'Habitación actualizada.')
            return redirect('viajes:detalle', pk=viaje.pk)
    else:
        form = ViajeHabitacionForm(instance=vh)
    return render(request, 'viajes/habitacion_form.html', {
        'form': form, 'viaje': viaje, 'titulo': f'Editar habitación — {vh.habitacion}'
    })


@login_required
def viaje_habitacion_quitar(request, pk, vh_pk):
    viaje = get_object_or_404(Viaje, pk=pk)
    vh = get_object_or_404(ViajeHabitacion, pk=vh_pk, viaje=viaje)
    if request.method == 'POST':
        nombre = str(vh.habitacion)
        vh.delete()
        messages.success(request, f'Habitación {nombre} quitada del viaje.')
    return redirect('viajes:detalle', pk=viaje.pk)


@login_required
def viaje_habitacion_agregar_ajax(request, pk):
    """Agrega una habitación (existente o nueva) al viaje.

    Opcionalmente guarda el precio por persona de su tipo en este viaje
    (precio_tipo / frecuente_tipo). Con exigir_precio=1 no deja agregar una
    habitación cuyo tipo no tenga precio (se usa desde la reservación)."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    viaje = get_object_or_404(Viaje, pk=pk)
    from decimal import Decimal, InvalidOperation
    from hoteles.models import Habitacion, TipoHabitacion
    from .models import ViajeHabitacionPrecio

    modo = request.POST.get('modo', 'nueva')
    errors = {}

    # 1. Qué habitación y de qué tipo
    if modo == 'existente':
        hab_id = request.POST.get('habitacion_id', '').strip()
        hab = Habitacion.objects.select_related('tipo').filter(pk=hab_id).first() if hab_id.isdigit() else None
        if not hab:
            return JsonResponse({'ok': False, 'errors': {'habitacion_id': 'Selecciona una habitación.'}}, status=400)
        if ViajeHabitacion.objects.filter(viaje=viaje, habitacion=hab).exists():
            return JsonResponse({'ok': False, 'errors': {'habitacion_id': 'Esa habitación ya está en este viaje.'}}, status=400)
        tipo = hab.tipo
    else:
        hab = None
        nombre_hotel = request.POST.get('nombre_hotel', '').strip()
        tipo_id      = request.POST.get('tipo', '').strip()
        numero       = request.POST.get('numero', '').strip()
        num_camas    = request.POST.get('num_camas', '1').strip()
        if not nombre_hotel: errors['nombre_hotel'] = 'Escribe el nombre del hotel.'
        if not tipo_id:      errors['tipo']         = 'Elige el tipo de habitación.'
        if not numero:       errors['numero']       = 'Escribe el número de habitación.'
        tipo = TipoHabitacion.objects.filter(pk=tipo_id).first() if tipo_id.isdigit() else None
        if tipo_id and not tipo:
            errors['tipo'] = 'Elige el tipo de habitación.'

    # 2. Precio del tipo en este viaje
    def decimal_o_none(nombre, etiqueta):
        valor = request.POST.get(nombre, '').strip()
        if not valor:
            return None
        try:
            d = Decimal(valor)
        except InvalidOperation:
            errors[nombre] = f'{etiqueta}: escribe solo números.'
            return None
        if d < 0:
            errors[nombre] = f'{etiqueta}: no puede ser negativo.'
            return None
        return d

    precio_tipo = decimal_o_none('precio_tipo', 'Precio por persona')
    frecuente_tipo = decimal_o_none('frecuente_tipo', 'Precio frecuente')
    precio_existente = ViajeHabitacionPrecio.objects.filter(viaje=viaje, tipo_habitacion=tipo).first() if tipo else None
    if tipo and not precio_existente and precio_tipo is None and request.POST.get('exigir_precio') == '1':
        errors['precio_tipo'] = f'Este viaje aún no tiene precio para {tipo.nombre}. Escribe el precio por persona.'
    if frecuente_tipo is not None and precio_tipo is None and not precio_existente:
        errors['precio_tipo'] = 'Escribe también el precio normal por persona.'

    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    # 3. Guardar todo junto
    with transaction.atomic():
        if hab is None:
            hab = Habitacion.objects.create(
                nombre_hotel=nombre_hotel, tipo=tipo, numero=numero,
                num_camas=int(num_camas) if num_camas.isdigit() else 1,
            )
        ViajeHabitacion.objects.create(viaje=viaje, habitacion=hab)
        if not precio_existente and precio_tipo is not None:
            precio_existente = ViajeHabitacionPrecio.objects.create(
                viaje=viaje, tipo_habitacion=tipo,
                precio_por_persona=precio_tipo, precio_frecuente=frecuente_tipo)

    num = lambda d: float(d) if d is not None else None
    return JsonResponse({
        'ok': True,
        'habitacion': {'id': hab.pk, 'etiqueta': str(hab), 'tipo_id': tipo.pk},
        'precio': ([num(precio_existente.precio_por_persona), num(precio_existente.precio_frecuente)]
                   if precio_existente else None),
    })


class ViajeDeleteView(LoginRequiredMixin, DeleteView):
    model = Viaje
    template_name = 'viajes/confirmar_eliminar.html'
    success_url = reverse_lazy('viajes:lista')
    context_object_name = 'objeto'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Eliminar viaje: {self.object.nombre}'
        return ctx

    def form_valid(self, form):
        try:
            messages.success(self.request, 'Viaje eliminado.')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, f'No se puede eliminar "{self.object.nombre}": tiene reservaciones asociadas.')
            return redirect('viajes:detalle', pk=self.object.pk)
