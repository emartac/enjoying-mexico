import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import Reservacion, Pago
from clientes.models import Cliente


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
        else:
            self.fields['habitacion'].queryset = Habitacion.objects.none()
        self.fields['habitacion'].required = False
        self.fields['habitacion'].empty_label = '— Sin habitación (viaje de un día) —'

    def clean(self):
        cleaned_data = super().clean()
        habitacion = cleaned_data.get('habitacion')
        viaje = cleaned_data.get('viaje')
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
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('viaje', css_class='col-md-8'),
                Column('estado', css_class='col-md-4'),
            ),
            'habitacion',
            'precio_personalizado',
            'notas',
            ButtonHolder(Submit('submit', 'Guardar reservación', css_class='btn btn-primary')),
        )


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
    class Meta:
        model = Pago
        fields = ['monto', 'fecha', 'metodo', 'estado', 'referencia', 'notas']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notas': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and 'fecha' not in self.initial:
            self.initial['fecha'] = datetime.date.today()
        self.helper = FormHelper()
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
            ButtonHolder(Submit('submit', 'Guardar pago', css_class='btn btn-success')),
        )
