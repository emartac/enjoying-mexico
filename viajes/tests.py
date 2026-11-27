import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente
from hoteles.models import Habitacion, TipoHabitacion
from reservaciones.models import ClienteReservacion, Reservacion
from .models import Viaje, ViajeHabitacion, ViajeHabitacionPrecio


class PreciosPorTipoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('admin', password='x')
        self.client.force_login(self.user)
        self.doble = TipoHabitacion.objects.create(nombre='Doble', capacidad=2)
        self.triple = TipoHabitacion.objects.create(nombre='Triple', capacidad=3)

    def _datos_viaje(self, **extra):
        datos = {
            'nombre': 'Oaxaca', 'destino': 'Oaxaca',
            'fecha_salida': '2027-03-01', 'fecha_regreso': '2027-03-03',
            'capacidad_maxima': '0', 'activo': 'on',
            'abordaje-TOTAL_FORMS': '0', 'abordaje-INITIAL_FORMS': '0',
            'abordaje-MIN_NUM_FORMS': '0', 'abordaje-MAX_NUM_FORMS': '1000',
            f'precios-precio_{self.doble.pk}': '4500',
            f'precios-frecuente_{self.doble.pk}': '4200',
            f'precios-precio_{self.triple.pk}': '4000',
            f'precios-frecuente_{self.triple.pk}': '',
        }
        datos.update(extra)
        return datos

    def test_crear_viaje_guarda_precios_por_tipo(self):
        r = self.client.post(reverse('viajes:crear'), self._datos_viaje())
        self.assertEqual(r.status_code, 302)
        viaje = Viaje.objects.get()
        doble = viaje.precio_de_tipo(self.doble.pk)
        self.assertEqual(doble.precio_por_persona, Decimal('4500'))
        self.assertEqual(doble.precio_frecuente, Decimal('4200'))
        self.assertIsNone(viaje.precio_de_tipo(self.triple.pk).precio_frecuente)

    def test_frecuente_sin_precio_normal_es_error(self):
        datos = self._datos_viaje(**{f'precios-precio_{self.doble.pk}': ''})
        r = self.client.post(reverse('viajes:crear'), datos)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Viaje.objects.exists())
        self.assertContains(r, 'el frecuente solo no basta')

    def test_viaje_de_un_dia_ignora_precios_por_tipo(self):
        datos = self._datos_viaje(fecha_regreso='2027-03-01', precio_por_persona='900')
        r = self.client.post(reverse('viajes:crear'), datos)
        self.assertEqual(r.status_code, 302)
        self.assertFalse(ViajeHabitacionPrecio.objects.exists())

    def test_editar_borra_precio_vacio_y_exige_precio_si_hay_habitaciones(self):
        self.client.post(reverse('viajes:crear'), self._datos_viaje())
        viaje = Viaje.objects.get()
        url = reverse('viajes:editar', args=[viaje.pk])
        # Quitar el precio de Triple (no tiene habitaciones): se borra
        r = self.client.post(url, self._datos_viaje(**{f'precios-precio_{self.triple.pk}': ''}))
        self.assertEqual(r.status_code, 302)
        self.assertIsNone(viaje.precio_de_tipo(self.triple.pk))
        # Con una habitación Doble asignada, no se puede dejar Doble sin precio
        hab = Habitacion.objects.create(nombre_hotel='Mesón', tipo=self.doble, numero='101')
        ViajeHabitacion.objects.create(viaje=viaje, habitacion=hab)
        r = self.client.post(url, self._datos_viaje(**{
            f'precios-precio_{self.doble.pk}': '', f'precios-frecuente_{self.doble.pk}': ''}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'escribe su precio')

    def test_agregar_habitacion_sin_precio(self):
        self.client.post(reverse('viajes:crear'), self._datos_viaje())
        viaje = Viaje.objects.get()
        r = self.client.post(reverse('viajes:habitacion_agregar_ajax', args=[viaje.pk]), {
            'modo': 'nueva', 'nombre_hotel': 'Mesón', 'tipo': self.doble.pk,
            'numero': '101', 'num_camas': '2'})
        self.assertEqual(r.json(), {'ok': True})
        r = self.client.get(reverse('viajes:detalle', args=[viaje.pk]))
        self.assertContains(r, '4500')

    def test_reservacion_en_viaje_de_varios_dias_sin_habitaciones_avisa(self):
        from reservaciones.forms import ReservacionForm
        self.client.post(reverse('viajes:crear'), self._datos_viaje())
        viaje = Viaje.objects.get()
        r = self.client.get(reverse('reservaciones:crear') + f'?viaje={viaje.pk}')
        self.assertContains(r, 'aún no tiene habitaciones')
        self.assertNotContains(r, 'Sin habitación (viaje de un día)')
        form = ReservacionForm({'viaje': viaje.pk, 'estado': 'pendiente'}, viaje_id=viaje.pk)
        self.assertFalse(form.is_valid())
        self.assertIn('habitacion', form.errors)

    def test_reservacion_en_viaje_de_un_dia_no_pide_habitacion(self):
        from reservaciones.forms import ReservacionForm
        datos = self._datos_viaje(fecha_regreso='2027-03-01', precio_por_persona='900')
        self.client.post(reverse('viajes:crear'), datos)
        viaje = Viaje.objects.get()
        form = ReservacionForm({'viaje': viaje.pk, 'estado': 'pendiente'}, viaje_id=viaje.pk)
        self.assertTrue(form.is_valid(), form.errors)

    def test_costo_de_reservacion_usa_precio_del_tipo(self):
        self.client.post(reverse('viajes:crear'), self._datos_viaje())
        viaje = Viaje.objects.get()
        hab = Habitacion.objects.create(nombre_hotel='Mesón', tipo=self.doble, numero='101')
        ViajeHabitacion.objects.create(viaje=viaje, habitacion=hab)
        a = Cliente.objects.create(nombre='Ana', apellido='Pérez', email='a@x.com', telefono='1')
        b = Cliente.objects.create(nombre='Beto', apellido='Ruiz', email='b@x.com', telefono='2')
        res = Reservacion.objects.create(
            viaje=viaje, habitacion=hab,
            fecha_checkin=viaje.fecha_salida, fecha_checkout=viaje.fecha_regreso)
        ClienteReservacion.objects.create(reservacion=res, cliente=a, es_titular=True)
        ClienteReservacion.objects.create(reservacion=res, cliente=b)
        self.assertEqual(res.costo_habitacion, Decimal('9000'))
        # Cada viajero frecuente paga su precio frecuente; los demás el normal
        a.viajero_frecuente = True
        a.save()
        self.assertEqual(res.costo_habitacion, Decimal('8700'))
        # El formulario de reservación muestra el precio junto a la habitación
        r = self.client.get(reverse('reservaciones:crear') + f'?viaje={viaje.pk}')
        self.assertContains(r, '$4,500.00 p/p')
