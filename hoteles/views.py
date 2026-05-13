from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from .models import Hotel, TipoHabitacion, Habitacion
from .forms import HotelForm, TipoHabitacionForm, HabitacionForm


class HotelListView(LoginRequiredMixin, ListView):
    model = Hotel
    template_name = 'hoteles/lista.html'
    context_object_name = 'hoteles'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(nombre__icontains=q) | qs.filter(ciudad__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class HotelDetailView(LoginRequiredMixin, DetailView):
    model = Hotel
    template_name = 'hoteles/detalle.html'
    context_object_name = 'hotel'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['habitaciones'] = self.object.habitaciones.select_related('tipo').order_by('numero')
        return ctx


class HotelCreateView(LoginRequiredMixin, CreateView):
    model = Hotel
    form_class = HotelForm
    template_name = 'hoteles/formulario.html'
    success_url = reverse_lazy('hoteles:lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nuevo hotel'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Hotel creado exitosamente.')
        return super().form_valid(form)


class HotelUpdateView(LoginRequiredMixin, UpdateView):
    model = Hotel
    form_class = HotelForm
    template_name = 'hoteles/formulario.html'

    def get_success_url(self):
        return reverse('hoteles:detalle', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar hotel: {self.object.nombre}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Hotel actualizado.')
        return super().form_valid(form)


class HotelDeleteView(LoginRequiredMixin, DeleteView):
    model = Hotel
    template_name = 'hoteles/confirmar_eliminar.html'
    success_url = reverse_lazy('hoteles:lista')
    context_object_name = 'objeto'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Eliminar hotel: {self.object.nombre}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Hotel eliminado.')
        return super().form_valid(form)


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
        qs = super().get_queryset().select_related('hotel', 'tipo')
        hotel_id = self.request.GET.get('hotel')
        if hotel_id:
            qs = qs.filter(hotel_id=hotel_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hoteles'] = Hotel.objects.filter(activo=True)
        ctx['hotel_sel'] = self.request.GET.get('hotel', '')
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
