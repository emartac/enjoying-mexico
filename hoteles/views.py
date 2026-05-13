from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import TipoHabitacion, Habitacion
from .forms import TipoHabitacionForm, HabitacionForm


class TipoHabitacionListView(LoginRequiredMixin, ListView):
    model = TipoHabitacion
    template_name = 'hoteles/tipos_lista.html'
    context_object_name = 'tipos'


class TipoHabitacionCreateView(LoginRequiredMixin, CreateView):
    model = TipoHabitacion
    form_class = TipoHabitacionForm
    template_name = 'hoteles/formulario.html'
    success_url = reverse_lazy('hoteles:tipos_lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nuevo tipo de habitación'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de habitación creado.')
        return super().form_valid(form)


class TipoHabitacionUpdateView(LoginRequiredMixin, UpdateView):
    model = TipoHabitacion
    form_class = TipoHabitacionForm
    template_name = 'hoteles/formulario.html'
    success_url = reverse_lazy('hoteles:tipos_lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar tipo: {self.object.nombre}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Tipo actualizado.')
        return super().form_valid(form)


class TipoHabitacionDeleteView(LoginRequiredMixin, DeleteView):
    model = TipoHabitacion
    template_name = 'hoteles/confirmar_eliminar.html'
    success_url = reverse_lazy('hoteles:tipos_lista')
    context_object_name = 'objeto'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Eliminar tipo: {self.object.nombre}'
        return ctx


class HabitacionListView(LoginRequiredMixin, ListView):
    model = Habitacion
    template_name = 'hoteles/habitaciones_lista.html'
    context_object_name = 'habitaciones'

    def get_queryset(self):
        qs = super().get_queryset().select_related('tipo')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(nombre_hotel__icontains=q) | qs.filter(numero__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        from collections import OrderedDict
        from viajes.models import ViajeHabitacion
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '')
        ctx['q'] = q

        vh_qs = (
            ViajeHabitacion.objects
            .select_related('viaje', 'habitacion__tipo')
            .order_by('viaje__fecha_salida', 'viaje__nombre', 'habitacion__nombre_hotel', 'habitacion__numero')
        )
        if q:
            vh_qs = vh_qs.filter(habitacion__nombre_hotel__icontains=q) | vh_qs.filter(habitacion__numero__icontains=q)

        grupos = OrderedDict()
        asignadas_ids = set()
        for vh in vh_qs:
            vid = vh.viaje_id
            if vid not in grupos:
                grupos[vid] = {'viaje': vh.viaje, 'habitaciones': []}
            grupos[vid]['habitaciones'].append(vh.habitacion)
            asignadas_ids.add(vh.habitacion_id)

        sin_viaje = [h for h in ctx['habitaciones'] if h.pk not in asignadas_ids]
        ctx['grupos'] = grupos.values()
        ctx['sin_viaje'] = sin_viaje
        return ctx


class HabitacionCreateView(LoginRequiredMixin, CreateView):
    model = Habitacion
    form_class = HabitacionForm
    template_name = 'hoteles/formulario.html'
    success_url = reverse_lazy('hoteles:habitaciones_lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nueva habitación'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Habitación creada exitosamente.')
        return super().form_valid(form)


class HabitacionUpdateView(LoginRequiredMixin, UpdateView):
    model = Habitacion
    form_class = HabitacionForm
    template_name = 'hoteles/formulario.html'
    success_url = reverse_lazy('hoteles:habitaciones_lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar habitación: {self.object}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Habitación actualizada.')
        return super().form_valid(form)


class HabitacionDeleteView(LoginRequiredMixin, DeleteView):
    model = Habitacion
    template_name = 'hoteles/confirmar_eliminar.html'
    success_url = reverse_lazy('hoteles:habitaciones_lista')
    context_object_name = 'objeto'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Eliminar habitación: {self.object}'
        return ctx
