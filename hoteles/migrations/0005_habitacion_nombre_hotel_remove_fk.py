from django.db import migrations, models


def copiar_nombre_hotel(apps, schema_editor):
    Habitacion = apps.get_model('hoteles', 'Habitacion')
    for hab in Habitacion.objects.select_related('hotel').all():
        hab.nombre_hotel = hab.hotel.nombre
        hab.save(update_fields=['nombre_hotel'])


class Migration(migrations.Migration):

    dependencies = [
        ('hoteles', '0004_remove_hotel_estrellas_remove_hotel_pais'),
    ]

    operations = [
        # 1. Agregar campo nombre_hotel temporal (nullable)
        migrations.AddField(
            model_name='habitacion',
            name='nombre_hotel',
            field=models.CharField(max_length=200, verbose_name='Hotel', default=''),
            preserve_default=False,
        ),
        # 2. Copiar datos del FK al CharField
        migrations.RunPython(copiar_nombre_hotel, migrations.RunPython.noop),
        # 3. Quitar la relación unique_together que involucra hotel
        migrations.AlterUniqueTogether(
            name='habitacion',
            unique_together=set(),
        ),
        # 4. Quitar el FK a Hotel
        migrations.RemoveField(
            model_name='habitacion',
            name='hotel',
        ),
        # 5. Eliminar el modelo Hotel
        migrations.DeleteModel(
            name='Hotel',
        ),
        # 6. Actualizar ordering
        migrations.AlterModelOptions(
            name='habitacion',
            options={
                'ordering': ['nombre_hotel', 'numero'],
                'verbose_name': 'Habitación',
                'verbose_name_plural': 'Habitaciones',
            },
        ),
    ]
