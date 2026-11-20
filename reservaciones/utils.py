from pathlib import Path

from fpdf import FPDF
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings

# Identidad de Enjoying México
ROSA_MARCA = (201, 68, 136)  # #C94488
LOGO_PDF = Path(__file__).resolve().parent / 'assets' / 'logo_pdf.png'


class PDFReservacion(FPDF):
    def __init__(self, reservacion):
        super().__init__()
        self.reservacion = reservacion
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_fill_color(*ROSA_MARCA)
        self.rect(0, 0, 210, 32, 'F')
        # Logo a la izquierda (versión con contorno blanco, se lee sobre el rosa)
        if LOGO_PDF.exists():
            self.image(str(LOGO_PDF), x=12, y=6, w=62)
        # Título y código alineados a la derecha
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 16)
        self.set_xy(80, 8)
        self.cell(115, 8, 'Confirmacion de Reservacion', align='R')
        self.set_font('Helvetica', '', 10)
        self.set_xy(80, 18)
        self.cell(115, 6, f'Codigo: {self.reservacion.codigo}  |  {self.reservacion.get_estado_display()}', align='R')
        self.set_text_color(0, 0, 0)
        self.set_y(40)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        from datetime import datetime
        self.cell(0, 5, f'Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")}  |  Enjoying Mexico', align='C')

    def seccion(self, titulo):
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(246, 228, 238)   # rosa muy claro
        self.set_text_color(*ROSA_MARCA)
        self.cell(0, 7, titulo, ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def fila_dato(self, etiqueta, valor):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(102, 102, 102)
        self.cell(55, 6, etiqueta + ':', ln=False)
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 6, str(valor), ln=True)

    def tabla_encabezado(self, cols, anchos):
        self.set_font('Helvetica', 'B', 9)
        self.set_fill_color(233, 236, 239)
        self.set_text_color(0, 0, 0)
        for col, ancho in zip(cols, anchos):
            self.cell(ancho, 7, col, border=1, fill=True)
        self.ln()

    def tabla_fila(self, vals, anchos):
        self.set_font('Helvetica', '', 9)
        for val, ancho in zip(vals, anchos):
            self.cell(ancho, 6, str(val)[:40], border=1)
        self.ln()


def generar_pdf_reservacion(request, reservacion):
    clientes_res = list(reservacion.clientes_reservacion.select_related('cliente').order_by('-es_titular'))
    pagos = list(reservacion.pagos.order_by('fecha'))

    pdf = PDFReservacion(reservacion)
    pdf.add_page()

    # Viaje
    pdf.seccion('Informacion del Viaje')
    pdf.fila_dato('Destino', reservacion.viaje.destino)
    pdf.fila_dato('Fecha salida', reservacion.viaje.fecha_salida.strftime('%d/%m/%Y'))
    pdf.fila_dato('Fecha regreso', reservacion.viaje.fecha_regreso.strftime('%d/%m/%Y'))
    if reservacion.viaje.incluye:
        pdf.fila_dato('Incluye', reservacion.viaje.incluye[:100])
    pdf.ln(4)

    # Alojamiento
    pdf.seccion('Alojamiento')
    if reservacion.habitacion:
        pdf.fila_dato('Hotel', reservacion.habitacion.nombre_hotel)
        pdf.fila_dato('Habitacion', f'{reservacion.habitacion.tipo.nombre} No. {reservacion.habitacion.numero}')
        pdf.fila_dato('Capacidad', f'{reservacion.habitacion.tipo.capacidad} persona(s)')
    else:
        pdf.fila_dato('Alojamiento', 'Viaje de un dia (sin hospedaje)')
    pdf.fila_dato('Fecha salida', reservacion.fecha_checkin.strftime('%d/%m/%Y'))
    pdf.fila_dato('Fecha regreso', reservacion.fecha_checkout.strftime('%d/%m/%Y'))
    pdf.ln(4)

    # Pasajeros
    pdf.seccion('Pasajeros')
    pdf.tabla_encabezado(['#', 'Nombre', 'Email', 'Titular'], [10, 75, 75, 20])
    for i, cr in enumerate(clientes_res, 1):
        pdf.tabla_fila([
            i,
            str(cr.cliente),
            cr.cliente.email or '-',
            'Si' if cr.es_titular else '',
        ], [10, 75, 75, 20])
    pdf.ln(4)

    # Financiero
    pdf.seccion('Resumen Financiero')
    anchos_fin = [130, 50]
    pdf.tabla_encabezado(['Concepto', 'Monto (MXN)'], anchos_fin)
    pdf.tabla_fila([
        f'Habitacion ({reservacion.num_clientes} persona(s))',
        f'${reservacion.costo_habitacion}',
    ], anchos_fin)

    # Fila total en negrita
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(248, 249, 250)
    pdf.cell(anchos_fin[0], 6, 'TOTAL', border=1, fill=True)
    pdf.cell(anchos_fin[1], 6, f'${reservacion.total}', border=1, fill=True)
    pdf.ln()

    for pago in pagos:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(25, 135, 84)
        pdf.cell(anchos_fin[0], 6,
                 f'Pago ({pago.get_metodo_display()}, {pago.fecha.strftime("%d/%m/%Y")})'
                 + (f' Ref: {pago.referencia}' if pago.referencia else ''),
                 border=1)
        pdf.cell(anchos_fin[1], 6, f'-${pago.monto}', border=1)
        pdf.ln()

    pdf.set_font('Helvetica', 'B', 9)
    color = (220, 53, 69) if float(reservacion.saldo_pendiente) > 0 else (25, 135, 84)
    pdf.set_text_color(*color)
    pdf.cell(anchos_fin[0], 6, 'SALDO PENDIENTE', border=1)
    pdf.cell(anchos_fin[1], 6, f'${reservacion.saldo_pendiente}', border=1)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    if reservacion.notas:
        pdf.ln(4)
        pdf.seccion('Notas')
        pdf.set_font('Helvetica', '', 10)
        pdf.multi_cell(0, 6, reservacion.notas)

    return bytes(pdf.output())


# ── Pase de abordaje (formato vertical, estilo celular) ────────────────────

FUENTES = Path(__file__).resolve().parent / 'assets' / 'fonts'
AZUL_TEXTO = (32, 42, 68)
GRIS = (120, 120, 120)
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
         'septiembre', 'octubre', 'noviembre', 'diciembre']
ANCHO_PASE = 110          # mm
ALTO_FOTO = 58            # mm


def _fecha_larga(f):
    return f'{f.day} de {MESES[f.month - 1]}'.upper()


def texto_rango_fechas(viaje):
    """'25 DE DICIEMBRE', '25 AL 27 DE DICIEMBRE' o '30 DE MAYO AL 1 DE JUNIO'."""
    ini, fin = viaje.fecha_salida, viaje.fecha_regreso
    if not fin or fin == ini:
        return _fecha_larga(ini)
    if (ini.year, ini.month) == (fin.year, fin.month):
        return f'{ini.day} AL {_fecha_larga(fin)}'
    return f'{_fecha_larga(ini)} AL {_fecha_larga(fin)}'


def _hora(h):
    return h.strftime('%I:%M %p').lstrip('0') if h else ''


def codigo_viajero(cr):
    """Código corto por viajero, ej. 'ZA26C26' (viaje + año + id)."""
    viaje = cr.reservacion.viaje
    letras = ''.join(c for c in viaje.nombre.upper() if c.isalpha())[:2] or 'EM'
    return f'{letras}{viaje.fecha_salida:%y}C{cr.pk}'


def _imagen_cubierta(ruta, ancho_mm, alto_mm):
    """Recorta la imagen al tamaño del encabezado (como object-fit: cover)."""
    from io import BytesIO
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(ruta)).convert('RGB')
    img = ImageOps.fit(img, (int(ancho_mm * 10), int(alto_mm * 10)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, 'JPEG', quality=80)
    buf.seek(0)
    return buf


def _qr_png(texto):
    import segno
    from io import BytesIO
    buf = BytesIO()
    segno.make(texto, error='m').save(buf, kind='png', scale=10, border=1, dark='#202a44')
    buf.seek(0)
    return buf


class PDFPaseAbordaje(FPDF):
    def __init__(self, reservacion, cr, alto):
        super().__init__(format=(ANCHO_PASE, alto))
        self.reservacion = reservacion
        self.cr = cr
        self.set_margins(8, 0, 8)
        self.set_auto_page_break(False)
        self.add_font('Poppins', '', str(FUENTES / 'Poppins-Regular.ttf'))
        self.add_font('Poppins', 'B', str(FUENTES / 'Poppins-Bold.ttf'))
        self.add_font('PoppinsSemi', '', str(FUENTES / 'Poppins-SemiBold.ttf'))
        self.add_font('Kaushan', '', str(FUENTES / 'KaushanScript-Regular.ttf'))

    # Bloques de dibujo ------------------------------------------------------
    def encabezado(self, viaje):
        con_foto = False
        if viaje.imagen_pase:
            try:
                self.image(_imagen_cubierta(viaje.imagen_pase.path, ANCHO_PASE, ALTO_FOTO),
                           x=0, y=0, w=ANCHO_PASE, h=ALTO_FOTO)
                con_foto = True
            except Exception:
                pass
        if not con_foto:
            self.set_fill_color(*ROSA_MARCA)
            self.rect(0, 0, ANCHO_PASE, ALTO_FOTO, 'F')

        # Título en letra tipo pincel con sombra; se achica si no cabe y,
        # si aun así es muy largo, se parte en dos líneas
        titulo = viaje.nombre
        disponible = ANCHO_PASE - 12
        tam = 30
        self.set_font('Kaushan', '', tam)
        while self.get_string_width(titulo) > disponible and tam > 20:
            tam -= 1
            self.set_font('Kaushan', '', tam)
        lineas = [titulo]
        if self.get_string_width(titulo) > disponible:
            lineas, actual = [], ''
            for pal in titulo.split():
                prueba = f'{actual} {pal}'.strip()
                if self.get_string_width(prueba) <= disponible or not actual:
                    actual = prueba
                else:
                    lineas.append(actual)
                    actual = pal
            lineas.append(actual)
        alto_linea = tam * 0.42
        y = (ALTO_FOTO * 0.42) - (alto_linea * len(lineas)) / 2
        for linea in lineas:
            for dx, dy, color in ((0.7, 0.9, (40, 40, 40)), (0, 0, (255, 255, 255))):
                self.set_text_color(*color)
                self.set_xy(dx, y + dy)
                self.cell(ANCHO_PASE, alto_linea, linea, align='C')
            y += alto_linea

    def cinta_fecha(self, texto, y):
        self.set_font('PoppinsSemi', '', 10.5)
        ancho = self.get_string_width(texto) + 18
        x0, x1, alto = (ANCHO_PASE - ancho) / 2, (ANCHO_PASE + ancho) / 2, 8
        # Extremos rasgados como en las tarjetas del sitio
        izq = [(x0 + 1.2, y), (x0, y + 1.6), (x0 + 1.4, y + 3.2), (x0 + .3, y + 4.8),
               (x0 + 1.5, y + 6.4), (x0 + .6, y + alto)]
        der = [(x1 - .6, y + alto), (x1 - 1.5, y + 6.4), (x1 - .3, y + 4.8),
               (x1 - 1.4, y + 3.2), (x1, y + 1.6), (x1 - 1.2, y)]
        self.set_fill_color(*ROSA_MARCA)
        self.polygon(izq + der, style='F')
        self.set_text_color(255, 255, 255)
        self.set_xy(x0, y + .4)
        self.cell(ancho, alto - .8, texto, align='C')

    def dato(self, x, y, ancho, etiqueta, valor, tam_valor=10):
        self.set_font('PoppinsSemi', '', 8.5)
        self.set_text_color(*ROSA_MARCA)
        self.set_xy(x, y)
        self.cell(ancho, 5, etiqueta.upper())
        self.set_font('PoppinsSemi', '', tam_valor)
        self.set_text_color(*AZUL_TEXTO)
        self.set_xy(x, y + 6)
        self.multi_cell(ancho, 4.8, str(valor), align='L')
        return self.get_y()

    def dibujar(self):
        res, cr = self.reservacion, self.cr
        viaje = res.viaje
        puntos = list(viaje.puntos_abordaje.order_by('hora_abordaje'))
        col1, col2, ancho1, ancho2 = 8, 64, 52, 38

        self.add_page()
        self.encabezado(viaje)

        # Nombre del viaje y cinta de fechas
        self.set_font('PoppinsSemi', '', 12.5)
        self.set_text_color(*AZUL_TEXTO)
        self.set_xy(6, ALTO_FOTO + 6)
        self.multi_cell(ANCHO_PASE - 12, 6, viaje.nombre.upper(), align='C')
        y = self.get_y() + 3
        self.cinta_fecha(texto_rango_fechas(viaje), y)
        y += 14
        self.set_draw_color(*ROSA_MARCA)
        self.set_line_width(.4)
        self.line(6, y, ANCHO_PASE - 6, y)
        y += 6

        # Viajero / código
        fin1 = self.dato(col1, y, ancho1, 'Viajero', str(cr.cliente))
        if cr.es_titular:
            self.set_font('Poppins', '', 7.5)
            self.set_text_color(*GRIS)
            self.set_xy(col1, fin1)
            self.cell(ancho1, 4, 'Titular de la reservación')
            fin1 += 4
        fin2 = self.dato(col2, y, ancho2, 'Código viajero', codigo_viajero(cr))
        y = max(fin1, fin2) + 6

        # Fecha y abordaje
        if len(puntos) == 1:
            p = puntos[0]
            fin1 = self.dato(col1, y, ancho1, 'Fecha de salida', _fecha_larga(viaje.fecha_salida))
            fin2 = self.dato(col2, y, ancho2, 'Inicio de registro', _hora(p.hora_abordaje))
            y = max(fin1, fin2) + 6
            fin1 = self.dato(col1, y, ancho1, 'Punto de abordaje', p.punto.upper())
            fin2 = self.dato(col2, y, ancho2, 'Salida', _hora(p.hora_salida))
            y = max(fin1, fin2) + 6
        else:
            fin1 = self.dato(col1, y, ancho1, 'Fecha de salida', _fecha_larga(viaje.fecha_salida))
            fin2 = self.dato(col2, y, ancho2, 'Reservación', res.codigo)
            y = max(fin1, fin2) + 6
            self.set_font('PoppinsSemi', '', 8.5)
            self.set_text_color(*ROSA_MARCA)
            self.set_xy(col1, y)
            self.cell(0, 5, 'PUNTOS DE ABORDAJE')
            y += 6
            if not puntos:
                self.set_font('PoppinsSemi', '', 10)
                self.set_text_color(*AZUL_TEXTO)
                self.set_xy(col1, y)
                self.cell(0, 5, 'Por confirmar')
                y += 9
            else:
                anchos = (52, 21, 21)
                self.set_font('Poppins', '', 7)
                self.set_text_color(*GRIS)
                self.set_xy(col1, y)
                for txt, w in zip(('Punto', 'Registro', 'Salida'), anchos):
                    self.cell(w, 4, txt.upper())
                y += 5
                for p in puntos:
                    self.set_font('PoppinsSemi', '', 8.5)
                    self.set_text_color(*AZUL_TEXTO)
                    self.set_xy(col1, y)
                    self.multi_cell(anchos[0] - 2, 4.2, p.punto.upper(), align='L')
                    fin = self.get_y()
                    self.set_xy(col1 + anchos[0], y)
                    self.cell(anchos[1], 4.2, _hora(p.hora_abordaje))
                    self.cell(anchos[2], 4.2, _hora(p.hora_salida))
                    y = max(fin, y + 4.2) + 2.5
                y += 3

        # Alojamiento + QR
        if res.habitacion:
            hab = res.habitacion
            camas = f'{hab.num_camas} cama' + ('s' if hab.num_camas != 1 else '')
            alojamiento = f'{hab.tipo.nombre} con {camas}\n{hab.nombre_hotel}'.upper()
        else:
            alojamiento = 'VIAJE DE UN DÍA\n(SIN HOSPEDAJE)'
        y_qr = y
        fin1 = self.dato(col1, y, 58, 'Tipo de alojamiento', alojamiento, tam_valor=9)
        tam_qr = 30
        contenido_qr = (
            'Enjoying México - Pase de abordaje\n'
            f'Viajero: {cr.cliente}\n'
            f'Código: {codigo_viajero(cr)}\n'
            f'Reservación: {res.codigo}\n'
            f'Viaje: {viaje.nombre}\n'
            f'Salida: {viaje.fecha_salida:%d/%m/%Y}'
        )
        self.image(_qr_png(contenido_qr), x=ANCHO_PASE - 8 - tam_qr, y=y_qr - 1, w=tam_qr, h=tam_qr)
        y = max(fin1, y_qr + tam_qr) + 6

        # Barra de términos
        self.set_fill_color(*ROSA_MARCA)
        self.rect(0, y, ANCHO_PASE, 8, 'F')
        self.set_font('PoppinsSemi', '', 8)
        self.set_text_color(255, 255, 255)
        self.set_char_spacing(1.2)
        self.set_xy(0, y + 1.5)
        self.cell(ANCHO_PASE, 5, 'www.enjoyingmexico.org/terminos', align='C')
        self.set_char_spacing(0)
        y += 13

        # Logo
        if LOGO_PDF.exists():
            self.image(str(LOGO_PDF), x=(ANCHO_PASE - 52) / 2, y=y, w=52)
        return y + 52 * 192 / 600 + 6


def generar_pase_abordaje(reservacion, cr):
    # Primera pasada en una hoja alta para medir; la segunda usa el alto exacto
    medida = PDFPaseAbordaje(reservacion, cr, alto=600)
    alto = medida.dibujar()
    pdf = PDFPaseAbordaje(reservacion, cr, alto=max(alto, 180))
    pdf.dibujar()
    return bytes(pdf.output())


def enviar_pases_abordaje(request, reservacion):
    clientes_res = list(
        reservacion.clientes_reservacion
        .select_related('cliente')
        .order_by('-es_titular')
    )
    if not clientes_res:
        raise ValueError('La reservación no tiene clientes registrados.')
    omitidos = [cr.cliente for cr in clientes_res if not cr.cliente.email]
    clientes_res = [cr for cr in clientes_res if cr.cliente.email]
    if not clientes_res:
        raise ValueError('Ningún viajero de la reservación tiene correo.')

    viaje = reservacion.viaje
    puntos = list(viaje.puntos_abordaje.order_by('hora_abordaje'))

    for cr in clientes_res:
        pdf_bytes = generar_pase_abordaje(reservacion, cr)

        if puntos:
            filas_puntos = ''.join(
                f'<tr>'
                f'<td style="padding:5px 8px;border:1px solid #dee2e6">{p.punto}</td>'
                f'<td style="padding:5px 8px;border:1px solid #dee2e6;text-align:center">{p.hora_abordaje.strftime("%H:%M")}</td>'
                f'<td style="padding:5px 8px;border:1px solid #dee2e6;text-align:center">{p.hora_salida.strftime("%H:%M")}</td>'
                f'</tr>'
                for p in puntos
            )
            bloque_puntos = f'''
            <h3 style="color:#C94488;margin-bottom:6px">Puntos de Abordaje</h3>
            <table style="border-collapse:collapse;width:100%;margin-bottom:16px">
              <thead><tr style="background:#e9ecef">
                <th style="padding:5px 8px;border:1px solid #dee2e6;text-align:left">Punto</th>
                <th style="padding:5px 8px;border:1px solid #dee2e6">Hora abordaje</th>
                <th style="padding:5px 8px;border:1px solid #dee2e6">Hora salida</th>
              </tr></thead>
              <tbody>{filas_puntos}</tbody>
            </table>'''
        else:
            bloque_puntos = '<p style="color:#6c757d">Sin puntos de abordaje registrados.</p>'

        if reservacion.habitacion:
            bloque_alojamiento = (
                f'<p><strong>Hotel:</strong> {reservacion.habitacion.nombre_hotel}<br>'
                f'<strong>Tipo:</strong> {reservacion.habitacion.tipo.nombre} No. {reservacion.habitacion.numero}<br>'
                f'<strong>Camas:</strong> {reservacion.habitacion.num_camas}</p>'
            )
        else:
            bloque_alojamiento = '<p>Viaje de un día (sin hospedaje)</p>'

        cuerpo = f'''<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:#C94488;color:white;padding:20px 24px;border-radius:4px 4px 0 0">
            <h1 style="margin:0;font-size:22px">Pase de Abordaje</h1>
            <p style="margin:6px 0 0;font-size:13px">{viaje.nombre} &mdash; {reservacion.codigo}</p>
          </div>
          <div style="padding:20px 24px;border:1px solid #dee2e6;border-top:none">
            <h2 style="color:#C94488">Hola, {cr.cliente.nombre}!</h2>
            <p>Adjunto encontrarás tu pase de abordaje para el viaje. Aquí un resumen:</p>
            <h3 style="color:#C94488;margin-bottom:6px">Información del Viaje</h3>
            <p><strong>Destino:</strong> {viaje.destino}<br>
               <strong>Salida:</strong> {viaje.fecha_salida.strftime("%d/%m/%Y")}<br>
               <strong>Regreso:</strong> {viaje.fecha_regreso.strftime("%d/%m/%Y")}</p>
            {bloque_puntos}
            <h3 style="color:#C94488;margin-bottom:6px">Alojamiento</h3>
            {bloque_alojamiento}
          </div>
          <div style="background:#f8f9fa;padding:10px 24px;font-size:11px;color:#6c757d;text-align:center;border:1px solid #dee2e6;border-top:none;border-radius:0 0 4px 4px">
            Enjoying Mexico — Sistema de Reservaciones
          </div>
        </div>'''

        msg = EmailMessage(
            subject=f'Pase de abordaje — {viaje.nombre} — {cr.cliente}',
            body=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[cr.cliente.email],
        )
        msg.content_subtype = 'html'
        msg.attach(
            filename=f'pase_{reservacion.codigo}_{cr.cliente.nombre}_{cr.cliente.apellido}.pdf',
            content=pdf_bytes,
            mimetype='application/pdf',
        )
        msg.send()

    return len(clientes_res), omitidos


def enviar_email_reservacion(request, reservacion):
    destinatarios = [e for e in reservacion.clientes.values_list('email', flat=True) if e]
    if not destinatarios:
        raise ValueError('Ningún cliente de la reservación tiene correo.')

    clientes_res = reservacion.clientes_reservacion.select_related('cliente').order_by('-es_titular')
    pagos = reservacion.pagos.order_by('fecha')

    cuerpo_html = render_to_string(
        'reservaciones/email_confirmacion.html',
        {
            'reservacion': reservacion,
            'clientes_res': clientes_res,
            'pagos': pagos,
        },
        request=request,
    )

    pdf_bytes = generar_pdf_reservacion(request, reservacion)

    email = EmailMessage(
        subject=f'Confirmacion de reservacion {reservacion.codigo} - {reservacion.viaje.nombre}',
        body=cuerpo_html,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinatarios,
    )
    email.content_subtype = 'html'
    email.attach(
        filename=f'reservacion_{reservacion.codigo}.pdf',
        content=pdf_bytes,
        mimetype='application/pdf',
    )
    email.send()
