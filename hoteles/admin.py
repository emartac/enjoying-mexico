from django.contrib import admin
from .models import TipoHabitacion, Habitacion


@admin.register(TipoHabitacion)
class TipoHabitacionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'capacidad', 'descripcion']


@admin.register(Habitacion)
class HabitacionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nombre_hotel', 'tipo', 'num_camas', 'disponible']
    list_filter = ['tipo', 'disponible']
    search_fields = ['numero', 'nombre_hotel']
