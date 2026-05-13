from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Hotel(models.Model):
    nombre = models.CharField('Nombre', max_length=200)
    direccion = models.TextField('Dirección')
    ciudad = models.CharField('Ciudad', max_length=100)
    pais = models.CharField('País', max_length=100)
    estrellas = models.IntegerField(
        'Estrellas', default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    telefono = models.CharField('Teléfono', max_length=25, blank=True)
    email = models.EmailField('Correo electrónico', blank=True)
    sitio_web = models.URLField('Sitio web', blank=True)
    descripcion = models.TextField('Descripción', blank=True)
    activo = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Hotel'
        verbose_name_plural = 'Hoteles'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} — {self.ciudad}'


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
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='habitaciones', verbose_name='Hotel')
    tipo = models.ForeignKey(TipoHabitacion, on_delete=models.PROTECT, verbose_name='Tipo de habitación')
    numero = models.CharField('Número / Identificador', max_length=20)
    num_camas = models.PositiveIntegerField('Número de camas', default=1)
    precio_por_noche = models.DecimalField('Precio por noche (MXN)', max_digits=10, decimal_places=2)
    descripcion = models.TextField('Descripción adicional', blank=True)
    disponible = models.BooleanField('Disponible', default=True)

    class Meta:
        verbose_name = 'Habitación'
        verbose_name_plural = 'Habitaciones'
        ordering = ['hotel', 'numero']
        unique_together = ['hotel', 'numero']

    def __str__(self):
        return f'Hab. {self.numero} — {self.tipo.nombre} | {self.hotel.nombre}'
