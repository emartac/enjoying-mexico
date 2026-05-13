from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from .models import Viaje
from .forms import ViajeForm, PrecioFormSet, HabitacionFormSet


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
            'habitacion__hotel', 'habitacion__tipo'
        ).order_by('-creado')

        ctx['viajeros'] = (
            ClienteReservacion.objects
            .filter(reservacion__viaje=self.object)
            .exclude(reservacion__estado='cancelada')
            .select_related('cliente', 'reservacion', 'reservacion__habitacion__hotel', 'reservacion__habitacion__tipo')
            .order_by('reservacion__codigo', 'cliente__apellido')
        )

        # Habitaciones agrupadas por tipo
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
            .select_related('habitacion__tipo', 'habitacion__hotel')
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
        ctx['precio_formset'] = PrecioFormSet(self.request.POST or None, prefix='precios')
        ctx['habitacion_formset'] = HabitacionFormSet(self.request.POST or None, prefix='habitaciones')
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        precio_formset = ctx['precio_formset']
        habitacion_formset = ctx['habitacion_formset']
        if precio_formset.is_valid() and habitacion_formset.is_valid():
            self.object = form.save()
            precio_formset.instance = self.object
            precio_formset.save()
            habitacion_formset.instance = self.object
            habitacion_formset.save()
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
        ctx['precio_formset'] = PrecioFormSet(self.request.POST or None, instance=self.object, prefix='precios')
        ctx['habitacion_formset'] = HabitacionFormSet(self.request.POST or None, instance=self.object, prefix='habitaciones')
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        precio_formset = ctx['precio_formset']
        habitacion_formset = ctx['habitacion_formset']
        if precio_formset.is_valid() and habitacion_formset.is_valid():
            self.object = form.save()
            precio_formset.instance = self.object
            precio_formset.save()
            habitacion_formset.instance = self.object
            habitacion_formset.save()
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
            .select_related('habitacion__hotel', 'habitacion__tipo')
            .prefetch_related('clientes_reservacion__cliente')
            .order_by('habitacion__hotel__nombre', 'habitacion__numero')
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
        messages.success(self.request, 'Viaje eliminado.')
        return super().form_valid(form)
