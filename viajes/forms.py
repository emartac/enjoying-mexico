from django import forms
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import Viaje, ViajeHabitacion, ViajeHabitacionPrecio, PuntoAbordaje


class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = ['nombre', 'destino', 'fecha_salida', 'fecha_regreso', 'capacidad_maxima', 'precio_por_persona', 'precio_frecuente', 'incluye', 'descripcion', 'activo']
        widgets = {
            'fecha_salida': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_regreso': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'incluye': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_salida = cleaned_data.get('fecha_salida')
        fecha_regreso = cleaned_data.get('fecha_regreso')
        if fecha_salida and fecha_regreso and fecha_regreso > fecha_salida:
            cleaned_data['precio_por_persona'] = 0
            cleaned_data['precio_frecuente'] = None
        else:
            if not cleaned_data.get('precio_por_persona'):
                cleaned_data['precio_por_persona'] = 0
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['precio_por_persona'].required = False
        self.fields['precio_frecuente'].required = False
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('nombre', css_class='col-md-8'),
                Column('capacidad_maxima', css_class='col-md-4'),
            ),
            'destino',
            Row(
                Column('fecha_salida', css_class='col-md-4'),
                Column('fecha_regreso', css_class='col-md-4'),
                Column('activo', css_class='col-md-4 d-flex align-items-center pt-3'),
            ),
            Row(
                Column('precio_por_persona', css_class='col-md-6'),
                Column('precio_frecuente', css_class='col-md-6'),
            ),
            Row(
                Column('incluye', css_class='col-md-6'),
                Column('descripcion', css_class='col-md-6'),
            ),
        )


PuntoAbordajeFormSet = inlineformset_factory(
    Viaje,
    PuntoAbordaje,
    fields=['punto', 'hora_abordaje', 'hora_salida'],
    extra=0,
    can_delete=True,
    widgets={
        'hora_abordaje': forms.TimeInput(attrs={'type': 'time'}),
        'hora_salida': forms.TimeInput(attrs={'type': 'time'}),
    },
)

PrecioFormSet = inlineformset_factory(
    Viaje,
    ViajeHabitacionPrecio,
    fields=['tipo_habitacion', 'precio_por_persona'],
    extra=2,
    can_delete=True,
)


class ViajeHabitacionForm(forms.ModelForm):
    class Meta:
        model = ViajeHabitacion
        fields = ['habitacion', 'precio_total', 'precio_frecuente']

    def __init__(self, viaje=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from hoteles.models import Habitacion
        qs = Habitacion.objects.select_related('tipo').order_by('nombre_hotel', 'numero')
        if viaje and not self.instance.pk:
            ya_asignadas = viaje.viaje_habitaciones.values_list('habitacion_id', flat=True)
            qs = qs.exclude(pk__in=ya_asignadas)
        self.fields['habitacion'].queryset = qs
        self.fields['habitacion'].label_from_instance = lambda h: f'{h.nombre_hotel} — Hab. {h.numero} ({h.tipo.nombre}, {h.num_camas} cama(s))'
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'habitacion',
            Row(
                Column('precio_total', css_class='col-md-6'),
                Column('precio_frecuente', css_class='col-md-6'),
            ),
            ButtonHolder(Submit('submit', 'Guardar', css_class='btn btn-primary')),
        )


HabitacionFormSet = inlineformset_factory(
    Viaje,
    ViajeHabitacion,
    fields=['habitacion', 'precio_total'],
    extra=2,
    can_delete=True,
)
