from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import Cliente


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'nombre', 'apellido', 'email', 'telefono',
            'tipo_documento', 'numero_documento', 'fecha_nacimiento',
            'nacionalidad', 'direccion', 'notas',
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'direccion': forms.Textarea(attrs={'rows': 2}),
            'notas': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
            Row(
                Column('tipo_documento', css_class='col-md-4'),
                Column('numero_documento', css_class='col-md-4'),
                Column('fecha_nacimiento', css_class='col-md-4'),
            ),
            Row(
                Column('nacionalidad', css_class='col-md-5'),
                Column('direccion', css_class='col-md-7'),
            ),
            'notas',
            ButtonHolder(Submit('submit', 'Guardar cliente', css_class='btn btn-primary')),
        )
