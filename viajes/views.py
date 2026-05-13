from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from .models import Viaje
from .forms import ViajeForm


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
        ctx = super().get_context_data(**kwargs)
        ctx['reservaciones'] = self.object.reservaciones.select_related('habitacion__hotel').order_by('-creado')
        return ctx


class ViajeCreateView(LoginRequiredMixin, CreateView):
    model = Viaje
    form_class = ViajeForm
    template_name = 'viajes/formulario.html'
    success_url = reverse_lazy('viajes:lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nuevo viaje'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Viaje creado exitosamente.')
        return super().form_valid(form)


class ViajeUpdateView(LoginRequiredMixin, UpdateView):
    model = Viaje
    form_class = ViajeForm
    template_name = 'viajes/formulario.html'

    def get_success_url(self):
        return reverse('viajes:detalle', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar viaje: {self.object.nombre}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Viaje actualizado.')
        return super().form_valid(form)


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
