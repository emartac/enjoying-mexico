import datetime
from collections import OrderedDict
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Min
from django.forms import inlineformset_factory
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse

from .models import Tour, FechaSalida, ImagenCarrusel, DiaItinerario
from .forms import TourForm, DiaItinerarioForm


# ── Formsets ────────────────────────────────────────────────────────────────
from django import forms as dj_forms

FechaSalidaFormSet = inlineformset_factory(
    Tour, FechaSalida,
    fields=['fecha'],
    widgets={'fecha': dj_forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}, format='%Y-%m-%d')},
    extra=1, can_delete=True,
)


# ── Vistas públicas ─────────────────────────────────────────────────────────

class IndexView(ListView):
    model = Tour
    template_name = 'tours/public/index.html'
    context_object_name = 'tours'

    def get_queryset(self):
        hoy = datetime.date.today()
        return (Tour.objects
                .filter(activo=True, fechas__fecha__gte=hoy)
                .annotate(proxima_fecha=Min('fechas__fecha'))
                .prefetch_related('fechas')
                .distinct()
                .order_by('proxima_fecha'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Agrupar por mes de la próxima fecha
        grupos = OrderedDict()
        MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        for tour in ctx['tours']:
            proxima = tour.proximas_fechas.first()
            if proxima:
                clave = (proxima.fecha.year, proxima.fecha.month)
                nombre = f'{MESES[proxima.fecha.month]} {proxima.fecha.year}'
                if clave not in grupos:
                    grupos[clave] = {'nombre': nombre, 'tours': []}
                grupos[clave]['tours'].append(tour)
        ctx['grupos'] = list(grupos.values())
        return ctx


class TourDetailView(DetailView):
    model = Tour
    template_name = 'tours/public/detalle.html'
    context_object_name = 'tour'

    def get_queryset(self):
        return Tour.objects.filter(activo=True).prefetch_related(
            'fechas', 'carrusel', 'itinerario'
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tour = self.object
        ctx['incluye_items'] = [l.strip() for l in tour.incluye.splitlines() if l.strip()]
        ctx['no_incluye_items'] = [l.strip() for l in tour.no_incluye.splitlines() if l.strip()]
        ctx['lugares_salida'] = [l.strip() for l in tour.lugar_salida.splitlines() if l.strip()]
        costo = tour.costo
        ctx['meses'] = [
            {'n': 3,  'cuota': round(costo / 3, 2)},
            {'n': 6,  'cuota': round(costo / 6, 2)},
            {'n': 9,  'cuota': round(costo / 9, 2)},
            {'n': 12, 'cuota': round(costo / 12, 2)},
        ]
        return ctx


# ── Panel de administración (tours) ─────────────────────────────────────────

class TourPanelListView(LoginRequiredMixin, ListView):
    model = Tour
    template_name = 'tours/panel/lista.html'
    context_object_name = 'tours'
    queryset = Tour.objects.prefetch_related('fechas').order_by('-creado')


@login_required
def tour_crear(request):
    if request.method == 'POST':
        form = TourForm(request.POST, request.FILES)
        formset = FechaSalidaFormSet(request.POST, prefix='fechas')
        if form.is_valid() and formset.is_valid():
            tour = form.save()
            formset.instance = tour
            formset.save()
            messages.success(request, f'Tour "{tour.titulo}" creado.')
            return redirect('tours:panel_lista')
    else:
        form = TourForm()
        formset = FechaSalidaFormSet(prefix='fechas')
    return render(request, 'tours/panel/formulario.html', {
        'titulo': 'Nuevo tour',
        'form': form,
        'formset': formset,
    })


@login_required
def tour_editar(request, slug):
    tour = get_object_or_404(Tour, slug=slug)
    if request.method == 'POST':
        form = TourForm(request.POST, request.FILES, instance=tour)
        formset = FechaSalidaFormSet(request.POST, instance=tour, prefix='fechas')
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Tour actualizado.')
            return redirect('tours:panel_lista')
    else:
        form = TourForm(instance=tour)
        formset = FechaSalidaFormSet(instance=tour, prefix='fechas')
    return render(request, 'tours/panel/formulario.html', {
        'titulo': f'Editar — {tour.titulo}',
        'form': form,
        'formset': formset,
        'tour': tour,
    })


@login_required
def tour_eliminar(request, slug):
    tour = get_object_or_404(Tour, slug=slug)
    if request.method == 'POST':
        nombre = tour.titulo
        tour.delete()
        messages.success(request, f'Tour "{nombre}" eliminado.')
        return redirect('tours:panel_lista')
    return render(request, 'tours/panel/confirmar_eliminar.html', {'tour': tour})


# ── Carrusel ─────────────────────────────────────────────────────────────────

@login_required
def carrusel_manage(request, slug):
    tour = get_object_or_404(Tour, slug=slug)
    if request.method == 'POST':
        if 'agregar' in request.POST:
            imagenes = request.FILES.getlist('imagenes')
            orden = tour.carrusel.count()
            for img in imagenes:
                ImagenCarrusel.objects.create(tour=tour, imagen=img, orden=orden)
                orden += 1
            messages.success(request, f'{len(imagenes)} imagen(es) agregada(s).')
        elif 'eliminar' in request.POST:
            pk = request.POST.get('pk')
            ImagenCarrusel.objects.filter(pk=pk, tour=tour).delete()
            messages.success(request, 'Imagen eliminada.')
        return redirect('tours:carrusel', slug=slug)
    return render(request, 'tours/panel/carrusel.html', {'tour': tour})


# ── Itinerario ───────────────────────────────────────────────────────────────

@login_required
def itinerario_manage(request, slug):
    tour = get_object_or_404(Tour, slug=slug)
    return render(request, 'tours/panel/itinerario.html', {'tour': tour})


@login_required
def dia_crear(request, slug):
    tour = get_object_or_404(Tour, slug=slug)
    siguiente_dia = (tour.itinerario.order_by('dia').last().dia + 1) if tour.itinerario.exists() else 1
    if request.method == 'POST':
        form = DiaItinerarioForm(request.POST)
        if form.is_valid():
            dia = form.save(commit=False)
            dia.tour = tour
            dia.save()
            messages.success(request, f'Día {dia.dia} agregado.')
            return redirect('tours:itinerario', slug=slug)
    else:
        form = DiaItinerarioForm(initial={'dia': siguiente_dia})
    return render(request, 'tours/panel/dia_formulario.html', {
        'titulo': 'Agregar día',
        'form': form, 'tour': tour,
    })


@login_required
def dia_editar(request, slug, dia_pk):
    tour = get_object_or_404(Tour, slug=slug)
    dia = get_object_or_404(DiaItinerario, pk=dia_pk, tour=tour)
    if request.method == 'POST':
        form = DiaItinerarioForm(request.POST, instance=dia)
        if form.is_valid():
            form.save()
            messages.success(request, f'Día {dia.dia} actualizado.')
            return redirect('tours:itinerario', slug=slug)
    else:
        form = DiaItinerarioForm(instance=dia)
    return render(request, 'tours/panel/dia_formulario.html', {
        'titulo': f'Editar día {dia.dia}',
        'form': form, 'tour': tour,
    })


@login_required
def dia_eliminar(request, slug, dia_pk):
    tour = get_object_or_404(Tour, slug=slug)
    dia = get_object_or_404(DiaItinerario, pk=dia_pk, tour=tour)
    if request.method == 'POST':
        dia.delete()
        messages.success(request, 'Día eliminado.')
        return redirect('tours:itinerario', slug=slug)
    return render(request, 'tours/panel/dia_formulario.html', {
        'titulo': f'Eliminar día {dia.dia}',
        'confirmar_eliminar': True, 'form': None, 'tour': tour, 'dia': dia,
    })
