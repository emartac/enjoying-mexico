import unicodedata
import datetime
from django.db import models
from django.utils.text import slugify


def _slug(texto):
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    return slugify(texto)


class Tour(models.Model):
    titulo = models.CharField('Título', max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    duracion = models.CharField('Duración', max_length=100, help_text='Ej: 1 Día, 2 Días / 1 Noche')
    lugar_salida = models.TextField('Lugar de salida', help_text='Un lugar por línea')
    inicio_registro = models.CharField('Inicio de registro', max_length=50, help_text='Ej: 06:30 AM')
    hora_salida = models.CharField('Hora de salida', max_length=50, help_text='Ej: 07:00 AM')
    hora_regreso = models.CharField('Hora / fecha de regreso', max_length=100, help_text='Ej: 10:30 PM')
    titulo_descripcion = models.CharField('Título de la descripción', max_length=200)
    descripcion = models.TextField('Descripción')
    costo = models.DecimalField('Costo', max_digits=10, decimal_places=2)
    costo_frecuente = models.DecimalField('Costo viajero frecuente', max_digits=10, decimal_places=2,
                                          null=True, blank=True)
    incluye = models.TextField('Incluye', help_text='Un elemento por línea')
    no_incluye = models.TextField('No incluye', help_text='Un elemento por línea')
    imagen_principal = models.ImageField('Imagen principal (portada)', upload_to='tours/principal/')
    imagen_index = models.ImageField('Imagen para el índice', upload_to='tours/index/')
    imagen_incluye = models.ImageField('Imagen sección incluye', upload_to='tours/incluye/', blank=True)
    imagen_itinerario = models.ImageField('Imagen itinerario', upload_to='tours/itinerario/', blank=True)
    activo = models.BooleanField('Publicado', default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tour'
        verbose_name_plural = 'Tours'
        ordering = ['titulo']

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            base = _slug(self.titulo)
            slug, n = base, 1
            while Tour.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def proximas_fechas(self):
        hoy = datetime.date.today()
        return self.fechas.filter(fecha__gte=hoy).order_by('fecha')

    @property
    def ultima_fecha(self):
        return self.fechas.order_by('fecha').last()


class FechaSalida(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='fechas')
    fecha = models.DateField('Fecha de salida')

    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return self.fecha.strftime('%d/%m/%Y')


class ImagenCarrusel(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='carrusel')
    imagen = models.ImageField('Imagen', upload_to='tours/carrusel/')
    orden = models.PositiveIntegerField('Orden', default=0)

    class Meta:
        ordering = ['orden']


class DiaItinerario(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='itinerario')
    dia = models.PositiveIntegerField('Día')
    titulo = models.CharField('Título del día', max_length=200, blank=True)
    actividades = models.TextField('Actividades', help_text='Una actividad por línea')

    class Meta:
        ordering = ['dia']

    def __str__(self):
        return f'Día {self.dia}'
