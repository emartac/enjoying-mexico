from django.db import models
from django.core.validators import MinValueValidator


class TipoHabitacion(models.Model):
    nombre = models.CharField('Nombre', max_length=50)
    capacidad = models.IntegerField('Capacidad máxima (personas)', validators=[MinValueValidator(1)])
    descripcion = models.TextField('Descripción', blank=True)

    class Meta:
        verbose_name = 'Tipo de habitación'
        verbose_name_plural = 'Tipos de habitación'
        ordering = ['capacidad', 'nombre']

    def __str__(self):
        return f'{self.nombre} (hasta {self.capacidad} persona{"s" if self.capacidad > 1 else ""})'


class Habitacion(models.Model):
    nombre_hotel = models.CharField('Hotel', max_length=200)
    tipo = models.ForeignKey(TipoHabitacion, on_delete=models.PROTECT, verbose_name='Tipo de habitación')
    numero = models.CharField('Número / Identificador', max_length=20)
    num_camas = models.PositiveIntegerField('Número de camas', default=1)
    descripcion = models.TextField('Descripción adicional', blank=True)
    disponible = models.BooleanField('Disponible', default=True)

    class Meta:
        verbose_name = 'Habitación'
        verbose_name_plural = 'Habitaciones'
        ordering = ['nombre_hotel', 'numero']

    def __str__(self):
        return f'Hab. {self.numero} — {self.tipo.nombre} | {self.nombre_hotel}'
