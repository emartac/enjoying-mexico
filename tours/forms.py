from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Fieldset, Submit, ButtonHolder, HTML
from .models import Tour, DiaItinerario


class TourForm(forms.ModelForm):
    class Meta:
        model = Tour
        fields = [
            'titulo', 'duracion',
            'inicio_registro', 'hora_salida', 'hora_regreso', 'lugar_salida',
            'titulo_descripcion', 'descripcion',
            'costo', 'costo_frecuente',
            'incluye', 'no_incluye',
            'imagen_principal', 'imagen_index',
            'imagen_incluye', 'imagen_itinerario',
            'pdf_info',
            'activo',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'lugar_salida': forms.Textarea(attrs={'rows': 3}),
            'incluye': forms.Textarea(attrs={'rows': 5}),
            'no_incluye': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['costo_frecuente'].required = False
        self.fields['imagen_incluye'].required = False
        self.fields['imagen_itinerario'].required = False
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset('Información general',
                Row(Column('titulo', css_class='col-md-8'),
                    Column('duracion', css_class='col-md-4')),
                Row(Column('inicio_registro', css_class='col-md-4'),
                    Column('hora_salida', css_class='col-md-4'),
                    Column('hora_regreso', css_class='col-md-4')),
                'lugar_salida',
            ),
            Fieldset('Descripción',
                'titulo_descripcion',
                'descripcion',
            ),
            Fieldset('Costos',
                Row(Column('costo', css_class='col-md-6'),
                    Column('costo_frecuente', css_class='col-md-6')),
            ),
            Fieldset('Contenido',
                Row(Column('incluye', css_class='col-md-6'),
                    Column('no_incluye', css_class='col-md-6')),
            ),
            Fieldset('Imágenes y archivos',
                Row(Column('imagen_principal', css_class='col-md-6'),
                    Column('imagen_index', css_class='col-md-6')),
                Row(Column('imagen_incluye', css_class='col-md-6'),
                    Column('imagen_itinerario', css_class='col-md-6')),
                'pdf_info',
            ),
            'activo',
        )


class DiaItinerarioForm(forms.ModelForm):
    class Meta:
        model = DiaItinerario
        fields = ['dia', 'titulo', 'actividades']
        widgets = {
            'actividades': forms.Textarea(attrs={'rows': 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
