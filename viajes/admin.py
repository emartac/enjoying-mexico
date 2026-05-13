from django.contrib import admin
from .models import Viaje


@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'destino', 'fecha_salida', 'fecha_regreso', 'precio_por_persona', 'activo']
    search_fields = ['nombre', 'destino']
    list_filter = ['activo', 'fecha_salida']
    readonly_fields = ['creado']
