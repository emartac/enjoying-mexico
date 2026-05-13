from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'apellido', 'email', 'telefono', 'tipo_documento', 'numero_documento', 'creado']
    search_fields = ['nombre', 'apellido', 'email', 'numero_documento']
    list_filter = ['tipo_documento', 'nacionalidad']
    readonly_fields = ['creado', 'actualizado']
