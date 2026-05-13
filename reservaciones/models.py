import uuid
from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator
from clientes.models import Cliente
from hoteles.models import Habitacion
from viajes.models import Viaje


def _generar_codigo():
    return f'RES-{uuid.uuid4().hex[:8].upper()}'


class Reservacion(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
    ]

    codigo = models.CharField('Código', max_length=20, unique=True, default=_generar_codigo, editable=False)
    viaje = models.ForeignKey(Viaje, on_delete=models.PROTECT, verbose_name='Viaje', related_name='reservaciones')
    habitacion = models.ForeignKey(Habitacion, on_delete=models.PROTECT, verbose_name='Habitación', related_name='reservaciones')
    clientes = models.ManyToManyField(Cliente, through='ClienteReservacion', verbose_name='Clientes')
    fecha_checkin = models.DateField('Fecha check-in')
    fecha_checkout = models.DateField('Fecha check-out')
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS, default='pendiente')
    notas = models.TextField('Notas internas', blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reservación'
        verbose_name_plural = 'Reservaciones'
        ordering = ['-creado']

    def __str__(self):
        return f'{self.codigo} — {self.viaje.destino}'

    @property
    def noches(self):
        return (self.fecha_checkout - self.fecha_checkin).days

    @property
    def num_clientes(self):
        return self.clientes.count()

    @property
    def costo_habitacion(self):
        from viajes.models import ViajeHabitacion
        try:
            vh = ViajeHabitacion.objects.get(viaje=self.viaje, habitacion=self.habitacion)
            titular = self.clientes_reservacion.filter(es_titular=True).select_related('cliente').first()
            num_personas = self.clientes_reservacion.count() or 1
            if titular and titular.cliente.viajero_frecuente and vh.precio_frecuente is not None:
                return vh.precio_frecuente * num_personas
            return vh.precio_total * num_personas
        except ViajeHabitacion.DoesNotExist:
            return 0

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
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha']

    def __str__(self):
        return f'${self.monto} — {self.reservacion.codigo}'
