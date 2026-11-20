import uuid
import datetime
import unicodedata
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator
from clientes.models import Cliente
from hoteles.models import Habitacion
from viajes.models import Viaje


def _generar_codigo():
    return f'RES-{uuid.uuid4().hex[:8].upper()}'


def _slug_destino(destino):
    nfkd = unicodedata.normalize('NFKD', destino)
    ascii_str = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    letras = ''.join(c for c in ascii_str if c.isalpha())[:3].upper()
    return letras or 'RES'


class Reservacion(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
    ]

    codigo = models.CharField('Código', max_length=20, unique=True, default=_generar_codigo, editable=False)
    viaje = models.ForeignKey(Viaje, on_delete=models.PROTECT, verbose_name='Viaje', related_name='reservaciones')
    habitacion = models.ForeignKey(Habitacion, on_delete=models.PROTECT, verbose_name='Habitación', related_name='reservaciones', null=True, blank=True)
    clientes = models.ManyToManyField(Cliente, through='ClienteReservacion', verbose_name='Clientes')
    fecha_checkin = models.DateField('Fecha check-in')
    fecha_checkout = models.DateField('Fecha check-out')
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS, default='pendiente')
    precio_personalizado = models.DecimalField(
        'Precio personalizado (MXN)', max_digits=10, decimal_places=2,
        null=True, blank=True, validators=[MinValueValidator(0)],
        help_text='Si se llena, este monto reemplaza el cálculo automático.',
    )
    notas = models.TextField('Notas internas', blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reservación'
        verbose_name_plural = 'Reservaciones'
        ordering = ['-creado']

    def __str__(self):
        return f'{self.codigo} — {self.viaje.destino}'

    def save(self, *args, **kwargs):
        if not self.pk:
            try:
                viaje = self.viaje
                slug = _slug_destino(viaje.destino)
                fecha = viaje.fecha_salida.strftime('%d%m')
                for _ in range(5):
                    sufijo = uuid.uuid4().hex[:4].upper()
                    codigo = f'{slug}-{fecha}-{sufijo}'
                    if not Reservacion.objects.filter(codigo=codigo).exists():
                        self.codigo = codigo
                        break
            except Exception:
                pass
        super().save(*args, **kwargs)

    @property
    def noches(self):
        return (self.fecha_checkout - self.fecha_checkin).days

    @property
    def num_clientes(self):
        return self.clientes.count()

    def precios_unitarios(self):
        """(precio regular, precio frecuente o None) por persona, según habitación o viaje."""
        from decimal import Decimal
        if self.habitacion_id:
            from viajes.models import ViajeHabitacion
            vh = ViajeHabitacion.objects.filter(viaje_id=self.viaje_id, habitacion_id=self.habitacion_id).first()
            if not vh:
                return Decimal(0), None
            return vh.precio_total, vh.precio_frecuente
        return (self.viaje.precio_por_persona or Decimal(0)), self.viaje.precio_frecuente

    def desglose_precio(self):
        """Renglones del cálculo: cada viajero frecuente paga el precio frecuente
        (si el viaje o la habitación lo tiene) y los demás el regular."""
        clientes = [cr.cliente for cr in self.clientes_reservacion.select_related('cliente')]
        regular, frecuente = self.precios_unitarios()
        num_frecuentes = sum(1 for c in clientes if c.viajero_frecuente) if frecuente is not None else 0
        num_regulares = len(clientes) - num_frecuentes
        if not clientes:
            num_regulares = 1  # sin clientes se estima una persona
        renglones = []
        if num_regulares:
            renglones.append({'etiqueta': 'Precio regular', 'cantidad': num_regulares,
                              'unitario': regular, 'subtotal': regular * num_regulares})
        if num_frecuentes:
            renglones.append({'etiqueta': 'Viajero frecuente', 'cantidad': num_frecuentes,
                              'unitario': frecuente, 'subtotal': frecuente * num_frecuentes})
        return renglones

    @property
    def costo_habitacion(self):
        if self.precio_personalizado is not None:
            return self.precio_personalizado
        return sum((r['subtotal'] for r in self.desglose_precio()), 0)

    @property
    def titular(self):
        cr = self.clientes_reservacion.filter(es_titular=True).select_related('cliente').first()
        return cr.cliente if cr else None

    @property
    def costo_viaje(self):
        return 0

    @property
    def total(self):
        return self.costo_habitacion + self.costo_viaje

    @property
    def total_pagado(self):
        result = self.pagos.filter(estado='completado').aggregate(total=Sum('monto'))['total']
        return result or 0

    @property
    def saldo_pendiente(self):
        return self.total - self.total_pagado


class ClienteReservacion(models.Model):
    reservacion = models.ForeignKey(Reservacion, on_delete=models.CASCADE, related_name='clientes_reservacion')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    es_titular = models.BooleanField('Es titular', default=False)

    class Meta:
        verbose_name = 'Cliente en reservación'
        verbose_name_plural = 'Clientes en reservación'
        unique_together = ['reservacion', 'cliente']

    def __str__(self):
        return f'{self.cliente} en {self.reservacion.codigo}'


def almacenamiento_privado():
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def _ruta_comprobante(instance, filename):
    # Nombre aleatorio: no se puede adivinar ni choca con otros archivos
    hoy = datetime.date.today()
    return f'comprobantes/{hoy:%Y/%m}/{uuid.uuid4().hex}.jpg'


class Pago(models.Model):
    METODOS = [
        ('efectivo', 'Efectivo'),
        ('tarjeta_credito', 'Tarjeta de crédito'),
        ('tarjeta_debito', 'Tarjeta de débito'),
        ('transferencia', 'Transferencia bancaria'),
        ('paypal', 'PayPal'),
        ('otro', 'Otro'),
    ]
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('fallido', 'Fallido'),
        ('reembolsado', 'Reembolsado'),
    ]

    reservacion = models.ForeignKey(
        Reservacion, on_delete=models.CASCADE,
        related_name='pagos', verbose_name='Reservación',
    )
    monto = models.DecimalField('Monto (MXN)', max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    fecha = models.DateField('Fecha del pago')
    metodo = models.CharField('Método de pago', max_length=20, choices=METODOS)
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS, default='completado')
    referencia = models.CharField('Referencia / Comprobante', max_length=100, blank=True)
    notas = models.TextField('Notas', blank=True)
    comprobante = models.ImageField(
        'Comprobante', upload_to=_ruta_comprobante, storage=almacenamiento_privado,
        blank=True, help_text='Imagen PNG o JPG. Se reduce automáticamente para ahorrar espacio.')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha']

    def __str__(self):
        return f'${self.monto} — {self.reservacion.codigo}'
