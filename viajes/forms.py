from django import forms
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, ButtonHolder
from .models import Viaje, ViajeHabitacion, ViajeHabitacionPrecio, PuntoAbordaje


class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = ['nombre', 'destino', 'fecha_salida', 'fecha_regreso', 'capacidad_maxima', 'precio_por_persona', 'precio_frecuente', 'incluye', 'descripcion', 'imagen_pase', 'activo']
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
        self.fields['precio_por_persona'].help_text = (
            'Solo para viajes de un día. En viajes de varios días el precio va por tipo de habitación.')
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
            'imagen_pase',
        )

    def clean_imagen_pase(self):
        imagen = self.cleaned_data.get('imagen_pase')
        # Reducir solo las imágenes recién subidas
        if imagen and hasattr(imagen, 'content_type'):
            from reservaciones.imagenes import comprimir_imagen
            try:
                return comprimir_imagen(imagen, nombre='pase.jpg')
            except Exception:
                raise forms.ValidationError('No se pudo leer la imagen. Usa un archivo PNG o JPG.')
        return imagen


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

class PreciosTipoForm(forms.Form):
    """Una fila por tipo de habitación: precio normal y de viajero frecuente
    (ambos por persona). Dejar el precio vacío = ese tipo no se ofrece."""

    def __init__(self, *args, viaje=None, **kwargs):
        super().__init__(*args, **kwargs)
        from hoteles.models import TipoHabitacion
        self.viaje = viaje
        self.tipos = list(TipoHabitacion.objects.all())
        existentes = {}
        if viaje and viaje.pk:
            existentes = {p.tipo_habitacion_id: p for p in viaje.precios.all()}
        for t in self.tipos:
            p = existentes.get(t.pk)
            attrs = {'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0'}
            self.fields[f'precio_{t.pk}'] = forms.DecimalField(
                required=False, min_value=0, max_digits=10, decimal_places=2,
                initial=p.precio_por_persona if p else None,
                widget=forms.NumberInput(attrs=attrs))
            self.fields[f'frecuente_{t.pk}'] = forms.DecimalField(
                required=False, min_value=0, max_digits=10, decimal_places=2,
                initial=p.precio_frecuente if p else None,
                widget=forms.NumberInput(attrs=attrs))

    def filas(self):
        """Para la plantilla: [(tipo, campo precio, campo frecuente), ...]"""
        return [(t, self[f'precio_{t.pk}'], self[f'frecuente_{t.pk}']) for t in self.tipos]

    def clean(self):
        cleaned = super().clean()
        tipos_con_habitaciones = set()
        if self.viaje and self.viaje.pk:
            tipos_con_habitaciones = set(
                self.viaje.viaje_habitaciones.values_list('habitacion__tipo_id', flat=True))
        for t in self.tipos:
            precio = cleaned.get(f'precio_{t.pk}')
            frecuente = cleaned.get(f'frecuente_{t.pk}')
            if precio is None and frecuente is not None:
                self.add_error(f'precio_{t.pk}',
                               f'Escribe el precio normal de {t.nombre} (el frecuente solo no basta).')
            elif precio is None and t.pk in tipos_con_habitaciones:
                self.add_error(f'precio_{t.pk}',
                               f'Este viaje tiene habitaciones {t.nombre}; escribe su precio.')
        return cleaned

    def save(self, viaje):
        for t in self.tipos:
            precio = self.cleaned_data.get(f'precio_{t.pk}')
            frecuente = self.cleaned_data.get(f'frecuente_{t.pk}')
            if precio is None:
                ViajeHabitacionPrecio.objects.filter(viaje=viaje, tipo_habitacion=t).delete()
            else:
                ViajeHabitacionPrecio.objects.update_or_create(
                    viaje=viaje, tipo_habitacion=t,
                    defaults={'precio_por_persona': precio, 'precio_frecuente': frecuente})


class ViajeHabitacionForm(forms.ModelForm):
    class Meta:
        model = ViajeHabitacion
        fields = ['habitacion']

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
            ButtonHolder(Submit('submit', 'Guardar', css_class='btn btn-primary')),
        )
