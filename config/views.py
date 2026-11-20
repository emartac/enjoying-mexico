import os
import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import redirect


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
        # Las páginas de viajes viejos se borraron; sus enlaces (compartidos en
        # redes o indexados en Google) llevan al índice de viajes
        if path.endswith('.html'):
            return redirect('/')
        raise Http404

    content_type, _ = mimetypes.guess_type(str(full_path))
    content_type = content_type or 'application/octet-stream'

    return FileResponse(open(full_path, 'rb'), content_type=content_type)
