from io import BytesIO
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
    pdf.fila_dato('Hotel', reservacion.habitacion.nombre_hotel)
    pdf.fila_dato('Habitacion', f'{reservacion.habitacion.tipo.nombre} No. {reservacion.habitacion.numero}')
    pdf.fila_dato('Capacidad', f'{reservacion.habitacion.tipo.capacidad} persona(s)')
    pdf.fila_dato('Check-in', reservacion.fecha_checkin.strftime('%d/%m/%Y'))
    pdf.fila_dato('Check-out', reservacion.fecha_checkout.strftime('%d/%m/%Y'))
    pdf.fila_dato('Noches', str(reservacion.noches))
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
