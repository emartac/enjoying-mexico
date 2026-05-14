from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse
from django.db.models.deletion import ProtectedError
from .models import Viaje, ViajeHabitacion
from .forms import ViajeForm, ViajeHabitacionForm, PuntoAbordajeFormSet


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
        return ctx


class ViajeCreateView(LoginRequiredMixin, CreateView):
    model = Viaje
    form_class = ViajeForm
    template_name = 'viajes/formulario.html'
    success_url = reverse_lazy('viajes:lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nuevo viaje'
        ctx['abordaje_formset'] = PuntoAbordajeFormSet(self.request.POST or None, prefix='abordaje')
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        abordaje_formset = ctx['abordaje_formset']
        if abordaje_formset.is_valid():
            self.object = form.save()
            abordaje_formset.instance = self.object
            abordaje_formset.save()
            messages.success(self.request, 'Viaje creado exitosamente.')
            return super().form_valid(form)
        return self.form_invalid(form)


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
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        abordaje_formset = ctx['abordaje_formset']
        if abordaje_formset.is_valid():
            self.object = form.save()
            abordaje_formset.instance = self.object
            abordaje_formset.save()
            messages.success(self.request, 'Viaje actualizado.')
            return super().form_valid(form)
        return self.form_invalid(form)


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
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    viaje = get_object_or_404(Viaje, pk=pk)
    from hoteles.models import Habitacion, TipoHabitacion

    modo         = request.POST.get('modo', 'nueva')
    precio_total = request.POST.get('precio_total', '').strip()
    precio_frec  = request.POST.get('precio_frecuente', '').strip() or None

    if not precio_total:
        return JsonResponse({'ok': False, 'errors': {'precio_total': 'Campo requerido.'}}, status=400)

    try:
        if modo == 'existente':
            hab_id = request.POST.get('habitacion_id', '').strip()
            if not hab_id:
                return JsonResponse({'ok': False, 'errors': {'habitacion_id': 'Selecciona una habitación.'}}, status=400)
            hab = get_object_or_404(Habitacion, pk=hab_id)
        else:
            nombre_hotel = request.POST.get('nombre_hotel', '').strip()
            tipo_id      = request.POST.get('tipo', '').strip()
            numero       = request.POST.get('numero', '').strip()
            num_camas    = request.POST.get('num_camas', '1').strip()
            errors = {}
            if not nombre_hotel: errors['nombre_hotel'] = 'Campo requerido.'
            if not tipo_id:      errors['tipo']         = 'Campo requerido.'
            if not numero:       errors['numero']       = 'Campo requerido.'
            if errors:
                return JsonResponse({'ok': False, 'errors': errors}, status=400)
            tipo = get_object_or_404(TipoHabitacion, pk=tipo_id)
            hab = Habitacion.objects.create(
                nombre_hotel=nombre_hotel, tipo=tipo, numero=numero,
                num_camas=int(num_camas) if num_camas.isdigit() else 1,
            )

        ViajeHabitacion.objects.create(
            viaje=viaje, habitacion=hab,
            precio_total=precio_total, precio_frecuente=precio_frec,
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'errors': {'__all__': str(e)}}, status=400)


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
