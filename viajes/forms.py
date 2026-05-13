from django import forms
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import Viaje, ViajeHabitacion, ViajeHabitacionPrecio


class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = ['nombre', 'destino', 'fecha_salida', 'fecha_regreso', 'capacidad_maxima', 'incluye', 'descripcion', 'activo']
        widgets = {
            'fecha_salida': forms.DateInput(attrs={'type': 'date'}),
            'fecha_regreso': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'incluye': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
                Column('incluye', css_class='col-md-6'),
                Column('descripcion', css_class='col-md-6'),
            ),
        )


PrecioFormSet = inlineformset_factory(
    Viaje,
    ViajeHabitacionPrecio,
    fields=['tipo_habitacion', 'precio_por_persona'],
    extra=2,
    can_delete=True,
)

HabitacionFormSet = inlineformset_factory(
    Viaje,
    ViajeHabitacion,
    fields=['habitacion', 'precio_total'],
    extra=2,
    can_delete=True,
)
