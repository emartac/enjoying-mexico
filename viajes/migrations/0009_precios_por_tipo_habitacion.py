import django.core.validators
from django.db import migrations, models


def copiar_precios_de_habitaciones(apps, schema_editor):
    """Para viajes que ya tienen habitaciones con precio, crea el precio por
    tipo de habitación tomando el de la primera habitación de cada tipo."""
    ViajeHabitacion = apps.get_model('viajes', 'ViajeHabitacion')
    ViajeHabitacionPrecio = apps.get_model('viajes', 'ViajeHabitacionPrecio')
    vistos = set(ViajeHabitacionPrecio.objects.values_list('viaje_id', 'tipo_habitacion_id'))
    for vh in ViajeHabitacion.objects.select_related('habitacion').order_by('pk'):
        clave = (vh.viaje_id, vh.habitacion.tipo_id)
        if clave in vistos or vh.precio_total is None:
            continue
        ViajeHabitacionPrecio.objects.create(
            viaje_id=vh.viaje_id,
            tipo_habitacion_id=vh.habitacion.tipo_id,
            precio_por_persona=vh.precio_total,
            precio_frecuente=vh.precio_frecuente,
        )
        vistos.add(clave)


class Migration(migrations.Migration):

    dependencies = [
        ('viajes', '0008_viaje_imagen_pase'),
        ('hoteles', '0005_habitacion_nombre_hotel_remove_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='viajehabitacionprecio',
            name='precio_frecuente',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Precio viajero frecuente por persona (MXN)'),
        ),
        migrations.AlterField(
            model_name='viajehabitacion',
            name='precio_total',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Precio por persona anterior (MXN)'),
        ),
        migrations.AlterField(
            model_name='viajehabitacion',
            name='precio_frecuente',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Precio viajero frecuente anterior (MXN)'),
        ),
        migrations.RunPython(copiar_precios_de_habitaciones, migrations.RunPython.noop),
    ]
