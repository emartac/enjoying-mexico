from django.contrib import admin
from .models import Reservacion, ClienteReservacion, Pago


class ClienteReservacionInline(admin.TabularInline):
    model = ClienteReservacion
    extra = 0
    autocomplete_fields = ['cliente']


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    fields = ['monto', 'fecha', 'metodo', 'estado', 'referencia']


@admin.register(Reservacion)
class ReservacionAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'viaje', 'habitacion', 'estado', 'fecha_checkin', 'fecha_checkout', 'creado']
    list_filter = ['estado', 'viaje', 'habitacion__hotel']
    search_fields = ['codigo', 'viaje__nombre', 'clientes__nombre', 'clientes__apellido']
    readonly_fields = ['codigo', 'creado', 'actualizado']
    inlines = [ClienteReservacionInline, PagoInline]


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ['reservacion', 'monto', 'fecha', 'metodo', 'estado', 'referencia']
    list_filter = ['metodo', 'estado', 'fecha']
    search_fields = ['reservacion__codigo', 'referencia']
