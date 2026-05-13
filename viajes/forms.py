from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import Viaje


class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = ['nombre', 'destino', 'fecha_salida', 'fecha_regreso', 'precio_por_persona', 'incluye', 'descripcion', 'activo']
        widgets = {
            'fecha_salida': forms.DateInput(attrs={'type': 'date'}),
            'fecha_regreso': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'incluye': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('nombre', css_class='col-md-8'),
                Column('precio_por_persona', css_class='col-md-4'),
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
            ButtonHolder(Submit('submit', 'Guardar viaje', css_class='btn btn-primary')),
        )
