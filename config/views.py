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


# ── Tablero de inicio del panel ─────────────────────────────────────────────

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def tablero(request):
    import datetime
    from decimal import Decimal
    from django.db.models import Prefetch, Sum
    from reservaciones.models import Reservacion, ClienteReservacion, Pago
    from reservaciones.resumen import anotar_finanzas, ocupacion_viaje
    from viajes.models import Viaje

    hoy = datetime.date.today()

    # Próximas salidas (incluye viajes en curso)
    proximos = list(Viaje.objects.filter(activo=True, fecha_regreso__gte=hoy).order_by('fecha_salida')[:6])
    for v in proximos:
        v.viajeros, v.cupo = ocupacion_viaje(v)
        v.dias_faltan = (v.fecha_salida - hoy).days
        res_v = anotar_finanzas(list(v.reservaciones.exclude(estado='cancelada')))
        v.cobrado = sum((r.fin_pagado for r in res_v), Decimal(0))
        v.por_cobrar = sum((r.fin_saldo for r in res_v), Decimal(0))

    # Saldos por cobrar en viajes que aún no terminan, del más cercano al más lejano
    activas = anotar_finanzas(list(
        Reservacion.objects
        .filter(viaje__fecha_regreso__gte=hoy)
        .exclude(estado='cancelada')
        .select_related('viaje')
        .prefetch_related(Prefetch(
            'clientes_reservacion',
            queryset=ClienteReservacion.objects.filter(es_titular=True).select_related('cliente'),
            to_attr='titulares'))
        .order_by('viaje__fecha_salida', 'creado')
    ))
    con_saldo = [r for r in activas if r.fin_saldo > 0]

    inicio_mes = hoy.replace(day=1)
    cobrado_mes = (Pago.objects.filter(estado='completado', fecha__gte=inicio_mes, fecha__lte=hoy)
                   .aggregate(t=Sum('monto'))['t'] or Decimal(0))

    contexto = {
        'hoy': hoy,
        'proximos': proximos,
        'con_saldo': con_saldo[:10],
        'num_con_saldo': len(con_saldo),
        'total_por_cobrar': sum((r.fin_saldo for r in con_saldo), Decimal(0)),
        'cobrado_mes': cobrado_mes,
        'reservaciones_activas': len(activas),
        'pendientes_confirmar': sum(1 for r in activas if r.estado == 'pendiente'),
        'ultimos_pagos': (Pago.objects.select_related('reservacion__viaje')
                          .order_by('-fecha', '-creado')[:8]),
        'ultimas_reservaciones': (Reservacion.objects.select_related('viaje')
                                  .prefetch_related(Prefetch(
                                      'clientes_reservacion',
                                      queryset=ClienteReservacion.objects.filter(es_titular=True).select_related('cliente'),
                                      to_attr='titulares'))
                                  .order_by('-creado')[:6]),
    }
    return render(request, 'tablero.html', contexto)
