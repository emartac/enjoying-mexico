from fpdf import FPDF
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings


class PDFReservacion(FPDF):
    def __init__(self, reservacion):
        super().__init__()
        self.reservacion = reservacion
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_fill_color(13, 110, 253)
        self.rect(0, 0, 210, 28, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 16)
        self.set_xy(15, 7)
        self.cell(0, 8, 'Confirmacion de Reservacion', ln=False)
        self.set_font('Helvetica', '', 10)
        self.set_xy(15, 17)
        self.cell(0, 6, f'Codigo: {self.reservacion.codigo}  |  {self.reservacion.get_estado_display()}')
        self.set_text_color(0, 0, 0)
        self.ln(20)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        from datetime import datetime
        self.cell(0, 5, f'Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")}  |  Sistema de Reservaciones Turismo', align='C')

    def seccion(self, titulo):
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(233, 236, 239)
        self.set_text_color(13, 110, 253)
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
    pdf.fila_dato('Viaje', reservacion.viaje.nombre)
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
            cr.cliente.email,
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


class PDFPaseAbordaje(FPDF):
    _COLOR = (20, 150, 100)

    def __init__(self, reservacion, cr):
        super().__init__()
        self.reservacion = reservacion
        self.cr = cr
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        r, g, b = self._COLOR
        self.set_fill_color(r, g, b)
        self.rect(0, 0, 210, 36, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 18)
        self.set_xy(15, 5)
        self.cell(0, 10, 'PASE DE ABORDAJE')
        self.set_font('Helvetica', 'B', 13)
        self.set_xy(15, 17)
        self.cell(0, 8, str(self.cr.cliente))
        self.set_font('Helvetica', '', 9)
        self.set_xy(15, 27)
        self.cell(0, 6, f'{self.reservacion.viaje.nombre}  |  {self.reservacion.codigo}')
        self.set_text_color(0, 0, 0)
        self.ln(26)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        from datetime import datetime
        self.cell(0, 5, f'Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")}  |  {self.reservacion.codigo}', align='C')

    def seccion(self, titulo):
        r, g, b = self._COLOR
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(233, 236, 239)
        self.set_text_color(r, g, b)
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
            self.cell(ancho, 6, str(val)[:50], border=1)
        self.ln()


def generar_pase_abordaje(reservacion, cr):
    puntos = list(reservacion.viaje.puntos_abordaje.order_by('hora_abordaje'))

    pdf = PDFPaseAbordaje(reservacion, cr)
    pdf.add_page()

    pdf.seccion('Informacion del Viaje')
    pdf.fila_dato('Viaje', reservacion.viaje.nombre)
    pdf.fila_dato('Destino', reservacion.viaje.destino)
    pdf.fila_dato('Fecha salida', reservacion.viaje.fecha_salida.strftime('%d/%m/%Y'))
    pdf.fila_dato('Fecha regreso', reservacion.viaje.fecha_regreso.strftime('%d/%m/%Y'))
    if reservacion.viaje.incluye:
        pdf.fila_dato('Incluye', reservacion.viaje.incluye[:120])
    pdf.ln(4)

    if puntos:
        pdf.seccion('Puntos de Abordaje')
        pdf.tabla_encabezado(['Punto de abordaje', 'Hora abordaje', 'Hora salida'], [100, 40, 40])
        for p in puntos:
            pdf.tabla_fila([p.punto, p.hora_abordaje.strftime('%H:%M'), p.hora_salida.strftime('%H:%M')], [100, 40, 40])
        pdf.ln(4)

    pdf.seccion('Alojamiento')
    if reservacion.habitacion:
        pdf.fila_dato('Hotel', reservacion.habitacion.nombre_hotel)
        pdf.fila_dato('Tipo de habitacion', reservacion.habitacion.tipo.nombre)
        pdf.fila_dato('Habitacion No.', reservacion.habitacion.numero)
        pdf.fila_dato('Num. camas', str(reservacion.habitacion.num_camas))
    else:
        pdf.fila_dato('Alojamiento', 'Viaje de un dia (sin hospedaje)')
    pdf.ln(4)

    if cr.es_titular:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(13, 110, 253)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 7, '  TITULAR DE LA RESERVACION', ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)

    return bytes(pdf.output())


def enviar_pases_abordaje(request, reservacion):
    clientes_res = list(
        reservacion.clientes_reservacion
        .select_related('cliente')
        .order_by('-es_titular')
    )
    if not clientes_res:
        raise ValueError('La reservación no tiene clientes registrados.')

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
            <h3 style="color:#149664;margin-bottom:6px">Puntos de Abordaje</h3>
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
          <div style="background:#149664;color:white;padding:20px 24px;border-radius:4px 4px 0 0">
            <h1 style="margin:0;font-size:22px">Pase de Abordaje</h1>
            <p style="margin:6px 0 0;font-size:13px">{viaje.nombre} &mdash; {reservacion.codigo}</p>
          </div>
          <div style="padding:20px 24px;border:1px solid #dee2e6;border-top:none">
            <h2 style="color:#149664">Hola, {cr.cliente.nombre}!</h2>
            <p>Adjunto encontrarás tu pase de abordaje para el viaje. Aquí un resumen:</p>
            <h3 style="color:#149664;margin-bottom:6px">Información del Viaje</h3>
            <p><strong>Destino:</strong> {viaje.destino}<br>
               <strong>Salida:</strong> {viaje.fecha_salida.strftime("%d/%m/%Y")}<br>
               <strong>Regreso:</strong> {viaje.fecha_regreso.strftime("%d/%m/%Y")}</p>
            {bloque_puntos}
            <h3 style="color:#149664;margin-bottom:6px">Alojamiento</h3>
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


def enviar_email_reservacion(request, reservacion):
    destinatarios = list(reservacion.clientes.values_list('email', flat=True))
    if not destinatarios:
        raise ValueError('La reservación no tiene clientes registrados.')

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
