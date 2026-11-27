import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import Reservacion, Pago, ClienteReservacion
from clientes.models import Cliente
from .imagenes import comprimir_comprobante


class ReservacionForm(forms.ModelForm):
    class Meta:
        model = Reservacion
        fields = ['viaje', 'habitacion', 'estado', 'precio_personalizado', 'notas']
        widgets = {
            'notas': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, viaje_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        from viajes.models import ViajeHabitacion
        from hoteles.models import Habitacion
        self._viaje_id = viaje_id or (self.instance.viaje_id if self.instance.pk else None)
        if self._viaje_id:
            ids = ViajeHabitacion.objects.filter(viaje_id=self._viaje_id).values_list('habitacion_id', flat=True)
            self.fields['habitacion'].queryset = Habitacion.objects.filter(pk__in=ids).select_related('tipo')
            from viajes.models import ViajeHabitacionPrecio
            precios = {p.tipo_habitacion_id: p for p in
                       ViajeHabitacionPrecio.objects.filter(viaje_id=self._viaje_id)}

            def etiqueta(h):
                texto = str(h)
                p = precios.get(h.tipo_id)
                if p:
                    texto += f' — ${p.precio_por_persona:,.2f} p/p'
                    if p.precio_frecuente is not None:
                        texto += f' (frecuente ${p.precio_frecuente:,.2f})'
                return texto
            self.fields['habitacion'].label_from_instance = etiqueta
        else:
            self.fields['habitacion'].queryset = Habitacion.objects.none()
        self.fields['habitacion'].required = False
        self.fields['habitacion'].empty_label = '— Sin habitación (viaje de un día) —'

        # Viaje de varios días: la habitación es obligatoria y se explica qué hacer
        # si el viaje todavía no tiene habitaciones asignadas.
        from viajes.models import Viaje
        self._viaje = Viaje.objects.filter(pk=self._viaje_id).first() if self._viaje_id else None
        if self._viaje and not self._viaje.es_viaje_dia:
            self.fields['habitacion'].empty_label = '— Elige una habitación —'
            if not self.fields['habitacion'].queryset.exists():
                from django.urls import reverse
                from django.utils.html import format_html
                self.fields['habitacion'].help_text = format_html(
                    '<span class="text-danger">Este viaje de {} días aún no tiene habitaciones. '
                    'Agrégalas en <a href="{}">el detalle del viaje</a> (sección Habitaciones → Agregar).</span>',
                    self._viaje.duracion_dias + 1, reverse('viajes:detalle', args=[self._viaje.pk]))
        self.helper = FormHelper()
        # El <form> y el botón de guardar están en la plantilla, para poder
        # agregar la sección de clientes antes del botón
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('viaje', css_class='col-md-8'),
                Column('estado', css_class='col-md-4'),
            ),
            'habitacion',
            'precio_personalizado',
            'notas',
        )

    def clean(self):
        cleaned_data = super().clean()
        habitacion = cleaned_data.get('habitacion')
        viaje = cleaned_data.get('viaje')
        if viaje and not viaje.es_viaje_dia and not habitacion:
            self.add_error('habitacion',
                'Este viaje dura más de un día: elige la habitación donde se hospedarán.')
        if habitacion and viaje:
            qs = ClienteReservacion.objects.filter(
                reservacion__habitacion=habitacion,
                reservacion__viaje=viaje,
            ).exclude(reservacion__estado='cancelada')
            if self.instance.pk:
                qs = qs.exclude(reservacion_id=self.instance.pk)
            ocupados = qs.count()
            if ocupados >= habitacion.tipo.capacidad:
                self.add_error('habitacion',
                    f'La habitación {habitacion.numero} ya está llena '
                    f'({ocupados}/{habitacion.tipo.capacidad} lugar(es) ocupados).')
        return cleaned_data


class AgregarClienteForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        label='Cliente',
        empty_label='— Selecciona un cliente —',
    )
    es_titular = forms.BooleanField(required=False, label='Es titular de la reservación')

    def __init__(self, reservacion, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ya_en_reservacion = reservacion.clientes.values_list('pk', flat=True)
        self.fields['cliente'].queryset = Cliente.objects.exclude(pk__in=ya_en_reservacion)
        self.helper = FormHelper()
        self.helper.form_tag = False


class PagoForm(forms.ModelForm):
    TAMANO_MAXIMO_MB = 15

    quitar_comprobante = forms.BooleanField(required=False, label='Quitar el comprobante actual')

    class Meta:
        model = Pago
        fields = ['monto', 'fecha', 'metodo', 'estado', 'referencia', 'notas', 'comprobante']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notas': forms.Textarea(attrs={'rows': 2}),
            # accept="image/*" permite tomar la foto directo con la cámara del celular
            'comprobante': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and 'fecha' not in self.initial:
            self.initial['fecha'] = datetime.date.today()
        tiene_comprobante = bool(self.instance.pk and self.instance.comprobante)
        if not tiene_comprobante:
            del self.fields['quitar_comprobante']
        self.helper = FormHelper()
        # Las plantillas ponen su propia etiqueta <form> (página y modal)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('monto', css_class='col-md-4'),
                Column('fecha', css_class='col-md-4'),
                Column('estado', css_class='col-md-4'),
            ),
            Row(
                Column('metodo', css_class='col-md-6'),
                Column('referencia', css_class='col-md-6'),
            ),
            'notas',
            'comprobante',
            *(['quitar_comprobante'] if tiene_comprobante else []),
            ButtonHolder(Submit('submit', 'Guardar pago', css_class='btn btn-success')),
        )

    def clean_comprobante(self):
        archivo = self.cleaned_data.get('comprobante')
        # Solo se procesa un archivo recién subido (no el que ya estaba guardado)
        if archivo and hasattr(archivo, 'content_type'):
            if archivo.size > self.TAMANO_MAXIMO_MB * 1024 * 1024:
                raise forms.ValidationError(
                    f'La imagen pesa más de {self.TAMANO_MAXIMO_MB} MB. Usa una más ligera.')
            try:
                return comprimir_comprobante(archivo)
            except Exception:
                raise forms.ValidationError('No se pudo leer la imagen. Usa un archivo PNG o JPG.')
        return archivo

    def save(self, commit=True):
        storage = Pago._meta.get_field('comprobante').storage
        anterior = None
        if self.instance.pk:
            anterior = Pago.objects.filter(pk=self.instance.pk).values_list('comprobante', flat=True).first() or None
        nuevo_archivo = 'comprobante' in self.changed_data and self.cleaned_data.get('comprobante')
        if self.cleaned_data.get('quitar_comprobante') and not nuevo_archivo:
            self.instance.comprobante = None
        pago = super().save(commit=commit)
        # Borrar del disco el archivo que fue reemplazado o quitado
        if commit and anterior and anterior != (pago.comprobante.name or None):
            try:
                storage.delete(anterior)
            except OSError:
                pass  # si no se puede borrar, no impedir que se guarde el pago
        return pago
