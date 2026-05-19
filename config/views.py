import os
import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.views.generic import TemplateView
from django.db.models import Sum

from clientes.models import Cliente
from viajes.models import Viaje
from reservaciones.models import Reservacion


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_clientes'] = Cliente.objects.count()
        ctx['total_viajes'] = Viaje.objects.filter(activo=True).count()
        ctx['total_reservaciones'] = Reservacion.objects.count()
        ctx['pendientes'] = Reservacion.objects.filter(estado='pendiente').count()
        ctx['confirmadas'] = Reservacion.objects.filter(estado='confirmada').count()
        ctx['canceladas'] = Reservacion.objects.filter(estado='cancelada').count()
        ctx['recientes'] = (
            Reservacion.objects
            .select_related('viaje', 'habitacion__tipo')
            .order_by('-creado')[:8]
        )
        return ctx


def serve_sitio_publico(request, path=''):
    """Sirve los archivos del sitio HTML estático público."""
    site_root = Path(getattr(settings, 'STATIC_SITE_ROOT', ''))
    if not site_root or not site_root.exists():
        raise Http404

    # Página raíz → index.html
    if not path:
        path = 'index.html'

    full_path = (site_root / path).resolve()

    # Seguridad: prevenir directory traversal
    if not str(full_path).startswith(str(site_root.resolve())):
        raise Http404

    # Si es directorio, intentar index.html dentro
    if full_path.is_dir():
        full_path = full_path / 'index.html'

    if not full_path.is_file():
        raise Http404

    content_type, _ = mimetypes.guess_type(str(full_path))
    content_type = content_type or 'application/octet-stream'

    return FileResponse(open(full_path, 'rb'), content_type=content_type)
