"""Reducción de imágenes de comprobantes para ahorrar espacio en el servidor."""
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

LADO_MAXIMO = 1600   # px: suficiente para leer un comprobante bancario
CALIDAD_JPG = 72     # calidad media-alta; el texto sigue siendo legible


def comprimir_comprobante(archivo):
    """Devuelve un ContentFile JPG reducido a partir de una imagen subida (PNG, JPG, etc.)."""
    imagen = Image.open(archivo)
    imagen = ImageOps.exif_transpose(imagen)  # respeta la rotación de fotos de celular

    if imagen.mode in ('RGBA', 'LA', 'P'):
        # JPG no admite transparencia: se pone fondo blanco
        imagen = imagen.convert('RGBA')
        fondo = Image.new('RGB', imagen.size, (255, 255, 255))
        fondo.paste(imagen, mask=imagen.split()[-1])
        imagen = fondo
    else:
        imagen = imagen.convert('RGB')

    imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)

    salida = BytesIO()
    imagen.save(salida, 'JPEG', quality=CALIDAD_JPG, optimize=True, progressive=True)
    return ContentFile(salida.getvalue(), name='comprobante.jpg')
