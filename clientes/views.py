import csv
import io
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from .models import Cliente
from .forms import ClienteForm


class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = 'clientes/lista.html'
    context_object_name = 'clientes'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(nombre__icontains=q) | qs.filter(apellido__icontains=q) | qs.filter(email__icontains=q) | qs.filter(numero_documento__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ClienteDetailView(LoginRequiredMixin, DetailView):
    model = Cliente
    template_name = 'clientes/detalle.html'
    context_object_name = 'cliente'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['reservaciones'] = self.object.reservacion_set.select_related('viaje', 'habitacion__tipo').order_by('-creado')
        return ctx


class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'clientes/formulario.html'
    success_url = reverse_lazy('clientes:lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nuevo cliente'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Cliente creado exitosamente.')
        return super().form_valid(form)


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'clientes/formulario.html'

    def get_success_url(self):
        return self.object.get_absolute_url() if hasattr(self.object, 'get_absolute_url') else reverse_lazy('clientes:lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar cliente: {self.object}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Cliente actualizado exitosamente.')
        return super().form_valid(form)

    def get_success_url(self):
        from django.urls import reverse
        return reverse('clientes:detalle', kwargs={'pk': self.object.pk})


class ClienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Cliente
    template_name = 'clientes/confirmar_eliminar.html'
    success_url = reverse_lazy('clientes:lista')
    context_object_name = 'objeto'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Eliminar cliente: {self.object}'
        ctx['back_url'] = self.object.pk
        return ctx

    def form_valid(self, form):
        try:
            messages.success(self.request, f'Cliente {self.object} eliminado.')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, f'No se puede eliminar a {self.object}: tiene reservaciones asociadas.')
            return redirect('clientes:detalle', pk=self.object.pk)


def _parse_bool_csv(val):
    return val.strip().lower() in ('si', 'sí', '1', 'true', 'yes', 's')


@login_required
def carga_masiva(request):
    titulo = 'Carga masiva de clientes'
    if request.method != 'POST':
        return render(request, 'clientes/carga_masiva.html', {'titulo': titulo})

    archivo = request.FILES.get('archivo')
    if not archivo:
        messages.error(request, 'Selecciona un archivo CSV.')
        return render(request, 'clientes/carga_masiva.html', {'titulo': titulo})

    try:
        contenido = archivo.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        archivo.seek(0)
        contenido = archivo.read().decode('latin-1')

    reader = csv.DictReader(io.StringIO(contenido))
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]

    columnas_requeridas = {'correo', 'email', 'nombre'}
    if not (columnas_requeridas & set(headers)):
        messages.error(request, 'El archivo no tiene las columnas requeridas (nombre, correo/email).')
        return render(request, 'clientes/carga_masiva.html', {'titulo': titulo})

    def col(row, *nombres):
        for n in nombres:
            val = row.get(n, '').strip()
            if val:
                return val
        return ''

    resultados = []
    creados = omitidos = errores = 0

    for i, raw_row in enumerate(reader, start=2):
        row = {k.strip().lower(): v for k, v in raw_row.items()}

        nombre_raw = col(row, 'nombre')
        apellido = col(row, 'apellido')
        if not apellido and ' ' in nombre_raw:
            partes = nombre_raw.rsplit(' ', 1)
            nombre_raw, apellido = partes[0].strip(), partes[1].strip()

        email = col(row, 'correo', 'email')
        telefono = col(row, 'telefono', 'teléfono')
        frecuente = _parse_bool_csv(col(row, 'viajero_frecuente', 'frecuente'))

        fila = {'fila': i, 'nombre': f'{nombre_raw} {apellido}'.strip(), 'email': email}

        if not nombre_raw or not email:
            fila['estado'] = 'error'
            fila['detalle'] = 'Nombre y correo son obligatorios.'
            errores += 1
        elif Cliente.objects.filter(email__iexact=email).exists():
            fila['estado'] = 'omitido'
            fila['detalle'] = 'El correo ya existe.'
            omitidos += 1
        else:
            try:
                Cliente.objects.create(
                    nombre=nombre_raw,
                    apellido=apellido,
                    email=email,
                    telefono=telefono,
                    viajero_frecuente=frecuente,
                )
                fila['estado'] = 'creado'
                fila['detalle'] = ''
                creados += 1
            except Exception as e:
                fila['estado'] = 'error'
                fila['detalle'] = str(e)
                errores += 1

        resultados.append(fila)

    return render(request, 'clientes/carga_masiva.html', {
        'titulo': titulo,
        'resultados': resultados,
        'creados': creados,
        'omitidos': omitidos,
        'errores': errores,
    })


@login_required
def cliente_buscar(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'clientes': []})
    qs = Cliente.objects.filter(
        Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(telefono__icontains=q)
    ).order_by('apellido', 'nombre')[:10]
    return JsonResponse({'clientes': [
        {'id': c.pk, 'nombre': str(c), 'email': c.email, 'telefono': c.telefono or ''}
        for c in qs
    ]})


@login_required
def cliente_crear_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    form = ClienteForm(request.POST)
    if form.is_valid():
        cliente = form.save()
        return JsonResponse({
            'ok': True, 'id': cliente.pk,
            'nombre': str(cliente), 'email': cliente.email,
            'telefono': cliente.telefono or '',
        })
    return JsonResponse({
        'ok': False,
        'errors': {k: [str(e) for e in v] for k, v in form.errors.items()},
    }, status=400)
