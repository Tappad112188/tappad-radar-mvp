"""Plantilla HTML de TAPPAD Radar para vista previa, sin envíos."""
from html import escape
from urllib.parse import urlparse
from formato_alertas import fecha_legible, frase_oportunidades


def _texto(valor):
    return escape(str(valor or ""), quote=True)


def _enlace_seguro(valor):
    url = str(valor or "").strip()
    partes = urlparse(url)
    if partes.scheme != "https" or not partes.netloc or partes.username or partes.password:
        return None
    return escape(url, quote=True)


def construir_correo_html(empresa, oportunidades):
    """Genera HTML autocontenido y seguro para un correo de oportunidades."""
    tarjetas = []
    for oportunidad in oportunidades:
        numero = _texto(oportunidad.get("numero_procedimiento") or "Sin número")
        nombre = _texto(oportunidad.get("descripcion") or oportunidad.get("nombre_procedimiento") or "Sin descripción")
        terminos = _texto(", ".join(oportunidad.get("terminos") or []))
        apertura = _texto(fecha_legible(oportunidad.get("fecha_apertura")) if oportunidad.get("fecha_apertura") else "Fecha no disponible, verificar enlace")
        fuente = _texto(oportunidad.get("fuente") or "ComprasMX")
        publicacion = _texto(fecha_legible(oportunidad.get("fecha_publicacion")) if oportunidad.get("fecha_publicacion") else "Fecha no disponible, verificar enlace")
        junta = _texto(fecha_legible(oportunidad.get("fecha_junta_aclaraciones")) if oportunidad.get("fecha_junta_aclaraciones") else "Fecha no disponible, verificar enlace")
        fallo = _texto(fecha_legible(oportunidad.get("fecha_fallo_programado")) if oportunidad.get("fecha_fallo_programado") else "Fecha no disponible, verificar enlace")
        url = _enlace_seguro(oportunidad.get("url_procedimiento"))
        es_secop = str(oportunidad.get("fuente") or "").strip().casefold() == "secop coahuila"
        if not es_secop:
            for clave, valor in (("publicacion", oportunidad.get("fecha_publicacion")), ("junta", oportunidad.get("fecha_junta_aclaraciones")), ("apertura", oportunidad.get("fecha_apertura")), ("fallo", oportunidad.get("fecha_fallo_programado"))):
                if valor and fecha_legible(valor) in ("No disponible", "Fecha por verificar"):
                    if clave == "publicacion": publicacion = _texto("Fecha no disponible, verificar enlace")
                    elif clave == "junta": junta = _texto("Fecha no disponible, verificar enlace")
                    elif clave == "apertura": apertura = _texto("Fecha no disponible, verificar enlace")
                    else: fallo = _texto("Fecha no disponible, verificar enlace")
        def boton_documento(campo, titulo):
            valor = str(oportunidad.get(campo) or "").strip()
            partes = urlparse(valor)
            if (partes.scheme != "https" or partes.hostname != "www.sefincoahuila.gob.mx"
                or partes.username or partes.password or partes.query or partes.fragment
                or not partes.path.lower().startswith("/sistemas/secop/procedimiento/getfile/")
                or not partes.path.rsplit("/", 1)[-1].isdigit()):
                return ""
            destino = _texto(valor)
            return ('<a href="' + destino + '" style="display:inline-block;margin:4px 8px 4px 0;'
                    'background:#116b59;color:#ffffff;padding:12px 18px;'
                    'text-decoration:none;border-radius:6px;font-weight:bold">' + titulo + '</a>')
        if es_secop:
            enlace = (boton_documento("url_bases", "Descargar bases")
                      + boton_documento("url_convocatoria", "Descargar convocatoria"))
            if not enlace:
                enlace = '<span style="color:#6b7280">Documentos pendientes de verificación</span>'
        else:
            enlace = (
                '<a href="' + url + '" style="display:inline-block;background:#116b59;color:#ffffff;'
                'padding:12px 18px;text-decoration:none;border-radius:6px;font-weight:bold">'
                'Consultar procedimiento y documentos</a>'
            ) if url else '<span style="color:#6b7280">Enlace oficial no disponible</span>'
        documentos = oportunidad.get("documentos_disponibles") or []
        if isinstance(documentos, str):
            documentos = []
        nombres = []
        if isinstance(documentos, list):
            for documento in documentos[:30]:
                nombre_doc = documento.get("nombre") or documento.get("tipo") if isinstance(documento, dict) else documento
                if isinstance(nombre_doc, str) and nombre_doc.strip():
                    nombres.append(nombre_doc.strip())
        if not es_secop:
            if nombres:
                items = "".join("<li>" + _texto(n) + "</li>" for n in nombres)
                enlace = ('<p style="font-size:14px;color:#364b59"><b>Documentos disponibles:</b></p>'
                          '<ul style="font-size:14px;color:#364b59">' + items + '</ul>' + enlace)
            enlace += ('<p style="font-size:12px;color:#526476">'
                       'La descarga de archivos puede requerir resolver un CAPTCHA en ComprasMX.</p>')
        tarjetas.append(
            '<tr><td style="padding:0 24px 18px"><table role="presentation" width="100%" '
            'style="border:1px solid #dbe4e7;border-radius:8px;background:#ffffff">'
            '<tr><td style="padding:20px">'
            '<p style="font-size:14px;color:#364b59"><b>Descripción del procedimiento:</b> ' + nombre + '</p>'
            '<p style="font-size:14px;color:#364b59"><b>Número de procedimiento:</b> ' + numero + '</p>'
            '<p style="font-size:14px;color:#364b59"><b>Fecha de publicación:</b> ' + publicacion + '</p>'
            '<p style="font-size:14px;color:#364b59"><b>Fecha de Junta de aclaraciones:</b> ' + junta + '</p>'
            '<p style="font-size:14px;color:#364b59"><b>Fecha de apertura de proposiciones:</b> ' + apertura + '</p>'
            '<p style="font-size:14px;color:#364b59"><b>Fecha de fallo:</b> ' + fallo + '</p>'
            '<p style="font-size:14px;color:#364b59"><b>Enlace a documentos del procedimiento:</b></p>'
            + enlace + '</td></tr></table></td></tr>'
        )
    return (
        '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        '<body style="margin:0;background:#f2f6f8;font-family:Arial,Helvetica,sans-serif;color:#203744">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        'style="background:#f2f6f8;padding:24px 0"><tr><td align="center">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        'style="max-width:640px;background:#ffffff">'
        '<tr><td style="background:#123b52;color:#ffffff;padding:28px 24px">'
        '<img src="cid:tappad-logo" alt="TAPPAD Consultoría" width="165" height="165" style="display:block;border:0;margin:0 0 10px">'
        '<div style="font-size:17px;letter-spacing:1.5px;color:#ffffff;font-weight:bold">TAPPAD CONSULTORÍA</div>'
        '<h1 style="font-size:28px;margin:10px 0 0;color:#ffffff">TAPPAD Radar</h1>'
        '<p style="margin:8px 0 0;color:#e0eef2;font-size:15px">Oportunidades de contratación pública</p>'
        '</td></tr><tr><td style="padding:24px">'
        '<p style="font-size:17px">Hola, <b>' + _texto(empresa) + '</b>:</p>'
        '<p style="font-size:15px;line-height:1.6">' + _texto(frase_oportunidades(len(oportunidades))) + '</p>'
        '<p style="font-size:14px;color:#526476">Consulta los documentos oficiales disponibles. Confirma posibles modificaciones en el portal de origen.</p>'
        '</td></tr>' + "".join(tarjetas) +
        '<tr><td style="padding:8px 24px 22px">'
        '<p style="font-size:14px;line-height:1.6;color:#16354a"><b>¿Te interesa participar?</b> '
        'TAPPAD Consultoría ofrece asesoría especializada para revisar las bases y preparar tu propuesta. '
        'La asesoría es un servicio adicional e independiente de TAPPAD Radar.</p>'
        '</td></tr>'
        '<tr><td style="padding:10px 24px 26px;color:#526476;font-size:12px;line-height:1.6">'
        'La clasificación es orientativa. Verifica la vigencia y el plazo oficial de presentación '
        'de proposiciones antes de tomar decisiones.'
        '<hr style="border:0;border-top:1px solid #dbe4e7;margin:18px 0">'
        '<b>TAPPAD Radar</b> · TAPPAD Consultoría</td></tr>'
        '</table></td></tr></table></body></html>'
    )
