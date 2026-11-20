"""Cálculos de dinero y ocupación compartidos por la lista de reservaciones y el tablero."""
from decimal import Decimal

from .models import ClienteReservacion


def anotar_finanzas(reservaciones):
    """Calcula una sola vez total, pagado y saldo de cada reservación.

    Deja los valores en r.fin_total, r.fin_pagado y r.fin_saldo. Las canceladas
    no cuentan como saldo pendiente.
    """
    for r in reservaciones:
        r.fin_total = Decimal(r.total or 0)
        r.fin_pagado = Decimal(r.total_pagado or 0)
        r.fin_saldo = Decimal(0) if r.estado == 'cancelada' else r.fin_total - r.fin_pagado
    return reservaciones


def sumar(reservaciones, campo):
    return sum((getattr(r, campo) for r in reservaciones if r.estado != 'cancelada'), Decimal(0))


def ocupacion_viaje(viaje):
    """(viajeros, cupo) con la misma regla que el detalle del viaje."""
    viajeros = (ClienteReservacion.objects
                .filter(reservacion__viaje=viaje)
                .exclude(reservacion__estado='cancelada')
                .count())
    if viaje.capacidad_maxima > 0:
        cupo = viaje.capacidad_maxima
    else:
        cupo = sum(vh.habitacion.tipo.capacidad
                   for vh in viaje.viaje_habitaciones.select_related('habitacion__tipo'))
    return viajeros, cupo
