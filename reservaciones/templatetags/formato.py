from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def dinero(valor):
    """12500 -> '$12,500.00'"""
    try:
        numero = Decimal(valor or 0)
    except (InvalidOperation, TypeError, ValueError):
        return valor
    signo = '-' if numero < 0 else ''
    return f'{signo}${abs(numero):,.2f}'


@register.filter
def porcentaje(parte, total):
    """Porcentaje entero (0-100) para barras de progreso."""
    try:
        return max(0, min(100, round(float(parte) * 100 / float(total))))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0
