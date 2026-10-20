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
        nombre = _texto(oportunidad.get("nombre_procedimiento") or "Sin título")
        terminos = _texto(", ".join(oportunidad.get("terminos") or []))
        apertura = _texto(fecha_legible(oportunidad.get("fecha_apertura")))
        url = _enlace_seguro(oportunidad.get("url_procedimiento"))
        enlace = (
            '<a href="' + url + '" style="display:inline-block;background:#116b59;color:#ffffff;'
            'padding:12px 18px;text-decoration:none;border-radius:6px;font-weight:bold">'
            'Consultar procedimiento</a>'
        ) if url else '<span style="color:#6b7280">Enlace oficial no disponible</span>'
        tarjetas.append(
            '<tr><td style="padding:0 24px 18px"><table role="presentation" width="100%" '
            'style="border:1px solid #dbe4e7;border-radius:8px;background:#ffffff">'
            '<tr><td style="padding:20px">'
            '<div style="font-size:12px;color:#526476;font-weight:bold">PROCEDIMIENTO ' + numero + '</div>'
            '<h2 style="font-size:17px;line-height:1.4;color:#16354a;margin:10px 0">' + nombre + '</h2>'
            '<p style="font-size:14px;color:#364b59"><b>Coincidencia:</b> ' + terminos + '</p>'
            '<p style="font-size:14px;color:#364b59"><b>Fecha de apertura registrada:</b> ' + apertura + '</p>'
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
        '<img src="https://raw.githubusercontent.com/Tappad112188/tappad-radar-mvp/desarrollo-registro-proveedores/assets/isotipo_tappad.svg" alt="TAPPAD Consultoría" width="110" height="110" style="display:block;border:0;margin:0 0 10px">'
        '<div style="font-size:22px;letter-spacing:0.7px;color:#ffffff;font-weight:bold">TAPPAD CONSULTORÍA</div>'
        '<h1 style="font-size:28px;margin:10px 0 0;color:#ffffff">TAPPAD Radar</h1>'
        '<p style="margin:8px 0 0;color:#e0eef2;font-size:15px">Oportunidades de contratación pública</p>'
        '</td></tr><tr><td style="padding:24px">'
        '<p style="font-size:17px">Hola, <b>' + _texto(empresa) + '</b>:</p>'
        '<p style="font-size:15px;line-height:1.6">' + _texto(frase_oportunidades(len(oportunidades))) + '</p>'
        '<p style="font-size:14px;color:#526476">Consulta el expediente oficial antes de participar.</p>'
        '</td></tr>' + "".join(tarjetas) +
        '<tr><td style="padding:10px 24px 26px;color:#526476;font-size:12px;line-height:1.6">'
        'La clasificación es orientativa. Verifica la vigencia y el plazo oficial de presentación '
        'de proposiciones antes de tomar decisiones.'
        '<hr style="border:0;border-top:1px solid #dbe4e7;margin:18px 0">'
        '<b>TAPPAD Radar</b> · TAPPAD Consultoría</td></tr>'
        '</table></td></tr></table></body></html>'
    )
