from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import Hotel, TipoHabitacion, Habitacion


class HotelForm(forms.ModelForm):
    class Meta:
        model = Hotel
        fields = ['nombre', 'ciudad', 'pais', 'estrellas', 'direccion', 'telefono', 'email', 'sitio_web', 'descripcion', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'direccion': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'nombre',
            Row(
                Column('ciudad', css_class='col-md-5'),
                Column('pais', css_class='col-md-5'),
                Column('estrellas', css_class='col-md-2'),
            ),
            'direccion',
            Row(
                Column('telefono', css_class='col-md-4'),
                Column('email', css_class='col-md-4'),
                Column('sitio_web', css_class='col-md-4'),
            ),
            'descripcion',
            'activo',
            ButtonHolder(Submit('submit', 'Guardar hotel', css_class='btn btn-primary')),
        )


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
        fields = ['hotel', 'tipo', 'numero', 'precio_por_noche', 'descripcion', 'disponible']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('hotel', css_class='col-md-6'),
                Column('tipo', css_class='col-md-6'),
            ),
            Row(
                Column('numero', css_class='col-md-4'),
                Column('precio_por_noche', css_class='col-md-4'),
                Column('disponible', css_class='col-md-4 d-flex align-items-center pt-3'),
            ),
            'descripcion',
            ButtonHolder(Submit('submit', 'Guardar habitación', css_class='btn btn-primary')),
        )
