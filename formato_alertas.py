"""Formato de fechas de ComprasMX para mensajes en español.

Las fechas sin zona horaria se muestran tal como están registradas;
no se convierten ni se les atribuye una zona horaria.
"""
from datetime import date, datetime

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def fecha_legible(valor):
    if not valor:
        return "No disponible"
    try:
        if isinstance(valor, datetime):
            fecha = valor
        elif isinstance(valor, date):
            fecha = datetime.combine(valor, datetime.min.time())
        else:
            fecha = datetime.fromisoformat(str(valor).strip().replace("Z", "+00:00"))
    except (ValueError, TypeError, OverflowError):
        return "Fecha por verificar"
    resultado = f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"
    if fecha.hour or fecha.minute or fecha.second:
        hora = fecha.hour % 12 or 12
        resultado += f", {hora}:{fecha.minute:02d} {'a. m.' if fecha.hour < 12 else 'p. m.'}"
    return resultado


def frase_oportunidades(cantidad):
    if cantidad == 1:
        return "Identificamos una oportunidad potencialmente relevante para tu empresa."
    return f"Identificamos {cantidad} oportunidades potencialmente relevantes para tu empresa."
