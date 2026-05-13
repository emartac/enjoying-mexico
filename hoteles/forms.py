from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import TipoHabitacion, Habitacion


class TipoHabitacionForm(forms.ModelForm):
    class Meta:
        model = TipoHabitacion
        fields = ['nombre', 'capacidad', 'descripcion']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('nombre', css_class='col-md-8'),
                Column('capacidad', css_class='col-md-4'),
            ),
            'descripcion',
            ButtonHolder(Submit('submit', 'Guardar tipo', css_class='btn btn-primary')),
        )


class HabitacionForm(forms.ModelForm):
    class Meta:
        model = Habitacion
        fields = ['nombre_hotel', 'tipo', 'numero', 'num_camas', 'descripcion', 'disponible']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('nombre_hotel', css_class='col-md-6'),
                Column('tipo', css_class='col-md-6'),
            ),
            Row(
                Column('numero', css_class='col-md-4'),
                Column('num_camas', css_class='col-md-4'),
                Column('disponible', css_class='col-md-4 d-flex align-items-center pt-3'),
            ),
            'descripcion',
            ButtonHolder(Submit('submit', 'Guardar habitación', css_class='btn btn-primary')),
        )
