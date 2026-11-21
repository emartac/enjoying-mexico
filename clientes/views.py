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
        for palabra in q.split():
            qs = qs.filter(
                Q(nombre__icontains=palabra) | Q(apellido__icontains=palabra) |
                Q(telefono__icontains=palabra) | Q(email__icontains=palabra) |
                Q(numero_documento__icontains=palabra)
            )
        marca = self.request.GET.get('marca', '')
        if marca == 'tingo':
            qs = qs.filter(es_tingo=True)
        elif marca == 'no_deseado':
            qs = qs.filter(no_deseado=True)
        elif marca == 'frecuente':
            qs = qs.filter(viajero_frecuente=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['marca'] = self.request.GET.get('marca', '')
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

    if 'nombre' not in headers:
        messages.error(request, 'El archivo no tiene la columna requerida "nombre".')
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

        if not nombre_raw:
            fila['estado'] = 'error'
            fila['detalle'] = 'El nombre es obligatorio.'
            errores += 1
        elif email and Cliente.objects.filter(email__iexact=email).exists():
            fila['estado'] = 'omitido'
            fila['detalle'] = 'El correo ya existe.'
            omitidos += 1
        else:
            try:
                Cliente.objects.create(
                    nombre=nombre_raw,
                    apellido=apellido,
                    email=email or None,
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
    qs = Cliente.objects.all()
    # Cada palabra debe coincidir con algún campo (permite "Juan Pérez")
    for palabra in q.split():
        qs = qs.filter(
            Q(nombre__icontains=palabra) | Q(apellido__icontains=palabra) |
            Q(telefono__icontains=palabra) | Q(email__icontains=palabra) |
            Q(numero_documento__icontains=palabra)
        )
    qs = qs.order_by('apellido', 'nombre')[:10]
    return JsonResponse({'clientes': [
        {'id': c.pk, 'nombre': str(c), 'email': c.email or '', 'telefono': c.telefono or '',
         'frecuente': c.viajero_frecuente, 'tingo': c.es_tingo,
         'no_deseado': c.no_deseado, 'motivo_no_deseado': c.motivo_no_deseado}
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
            'nombre': str(cliente), 'email': cliente.email or '',
            'telefono': cliente.telefono or '', 'frecuente': cliente.viajero_frecuente,
            'tingo': cliente.es_tingo, 'no_deseado': cliente.no_deseado, 'motivo_no_deseado': cliente.motivo_no_deseado,
        })
    return JsonResponse({
        'ok': False,
        'errors': {k: [str(e) for e in v] for k, v in form.errors.items()},
    }, status=400)


@login_required
def cliente_marcas(request, pk):
    """Activa o desactiva las marcas Tingo / No deseado desde cualquier pantalla (AJAX o formulario)."""
    from django.shortcuts import get_object_or_404, redirect
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    marca = request.POST.get('marca')
    if marca not in ('es_tingo', 'no_deseado'):
        return JsonResponse({'ok': False, 'error': 'Marca inválida.'}, status=400)
    valor = request.POST.get('valor') == '1'
    setattr(cliente, marca, valor)
    campos = [marca]
    if marca == 'no_deseado':
        cliente.motivo_no_deseado = request.POST.get('motivo', '').strip()[:255] if valor else ''
        campos.append('motivo_no_deseado')
    cliente.save(update_fields=campos)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'tingo': cliente.es_tingo, 'no_deseado': cliente.no_deseado,
                             'motivo_no_deseado': cliente.motivo_no_deseado})
    siguiente = request.POST.get('next') or ''
    from django.utils.http import url_has_allowed_host_and_scheme
    if not url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
        siguiente = ''
    return redirect(siguiente or 'clientes:detalle', **({} if siguiente else {'pk': pk}))
