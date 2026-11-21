from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import Cliente


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'nombre', 'apellido', 'email', 'telefono',
            'nacionalidad', 'direccion', 'viajero_frecuente', 'es_tingo',
            'no_deseado', 'motivo_no_deseado', 'notas',
        ]
        widgets = {
            'direccion': forms.Textarea(attrs={'rows': 2}),
            'notas': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        datos = super().clean()
        if not datos.get('no_deseado'):
            datos['motivo_no_deseado'] = ''
        return datos

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        return email or None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].help_text = 'Opcional. Obligatorio si será titular de una reservación.'
        self.fields['telefono'].help_text = 'Opcional. Obligatorio si será titular de una reservación.'
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('nombre', css_class='col-md-6'),
                Column('apellido', css_class='col-md-6'),
            ),
            Row(
                Column('email', css_class='col-md-7'),
                Column('telefono', css_class='col-md-5'),
            ),
            'nacionalidad',
            'direccion',
            Row(
                Column('viajero_frecuente', css_class='col-md-4'),
                Column('es_tingo', css_class='col-md-4'),
                Column('no_deseado', css_class='col-md-4'),
            ),
            'motivo_no_deseado',
            'notas',
            ButtonHolder(Submit('submit', 'Guardar cliente', css_class='btn btn-primary')),
        )
