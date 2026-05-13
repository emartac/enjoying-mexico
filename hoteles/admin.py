from django.contrib import admin
from .models import Hotel, TipoHabitacion, Habitacion


class HabitacionInline(admin.TabularInline):
    model = Habitacion
    extra = 0
    fields = ['numero', 'tipo', 'precio_por_noche', 'disponible']


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ciudad', 'pais', 'estrellas', 'activo']
    search_fields = ['nombre', 'ciudad', 'pais']
    list_filter = ['estrellas', 'activo', 'pais']
    inlines = [HabitacionInline]


@admin.register(TipoHabitacion)
class TipoHabitacionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'capacidad', 'descripcion']


@admin.register(Habitacion)
class HabitacionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'hotel', 'tipo', 'precio_por_noche', 'disponible']
    list_filter = ['hotel', 'tipo', 'disponible']
    search_fields = ['numero', 'hotel__nombre']
