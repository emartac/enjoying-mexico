from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import Cliente


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'nombre', 'apellido', 'email', 'telefono',
            'nacionalidad', 'direccion', 'notas',
        ]
        widgets = {
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
            'nacionalidad',
            'direccion',
            'notas',
            ButtonHolder(Submit('submit', 'Guardar cliente', css_class='btn btn-primary')),
        )
