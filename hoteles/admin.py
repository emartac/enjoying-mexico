from django.contrib import admin
from .models import Hotel, TipoHabitacion, Habitacion


class HabitacionInline(admin.TabularInline):
    model = Habitacion
    extra = 0
    fields = ['numero', 'tipo', 'num_camas', 'disponible']


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ciudad', 'activo']
    search_fields = ['nombre', 'ciudad']
    list_filter = ['activo']
    inlines = [HabitacionInline]


@admin.register(TipoHabitacion)
class TipoHabitacionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'capacidad', 'descripcion']


@admin.register(Habitacion)
class HabitacionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'hotel', 'tipo', 'num_camas', 'disponible']
    list_filter = ['hotel', 'tipo', 'disponible']
    search_fields = ['numero', 'hotel__nombre']
