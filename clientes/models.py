from django.db import models


class Cliente(models.Model):
    TIPO_DOC = [
        ('pasaporte', 'Pasaporte'),
        ('dni', 'DNI / INE'),
        ('cedula', 'Cédula'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField('Nombre', max_length=100)
    apellido = models.CharField('Apellido', max_length=100)
    email = models.EmailField('Correo electrónico', unique=True)
    telefono = models.CharField('Teléfono', max_length=25)
    tipo_documento = models.CharField('Tipo de documento', max_length=20, choices=TIPO_DOC, default='pasaporte')
    numero_documento = models.CharField('Número de documento', max_length=50)
    fecha_nacimiento = models.DateField('Fecha de nacimiento', null=True, blank=True)
    nacionalidad = models.CharField('Nacionalidad', max_length=100, blank=True)
    direccion = models.TextField('Dirección', blank=True)
    notas = models.TextField('Notas internas', blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f'{self.nombre} {self.apellido}'

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellido}'
