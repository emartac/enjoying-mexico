from django.db import models
from django.core.validators import MinValueValidator


class Viaje(models.Model):
    nombre = models.CharField('Nombre del viaje', max_length=200)
    destino = models.CharField('Destino', max_length=200)
    descripcion = models.TextField('Descripción', blank=True)
    fecha_salida = models.DateField('Fecha de salida')
    fecha_regreso = models.DateField('Fecha de regreso')
    precio_por_persona = models.DecimalField(
        'Precio por persona (MXN)', max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    incluye = models.TextField('¿Qué incluye?', blank=True, help_text='Lista de servicios incluidos')
    capacidad_maxima = models.PositiveIntegerField('Capacidad máxima de viajeros', default=0)
    activo = models.BooleanField('Activo', default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Viaje'
        verbose_name_plural = 'Viajes'
        ordering = ['fecha_salida']

    def __str__(self):
        return f'{self.nombre} — {self.destino} ({self.fecha_salida})'

    @property
    def duracion_dias(self):
        return (self.fecha_regreso - self.fecha_salida).days

    @property
    def ocupacion_actual(self):
        return self.reservaciones.exclude(estado='cancelada').values_list(
            'clientes', flat=True
        ).distinct().count()

    @property
    def lugares_disponibles(self):
        if self.capacidad_maxima == 0:
            return None
        return self.capacidad_maxima - self.ocupacion_actual
