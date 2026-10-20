"""Priorización conservadora de oportunidades para revisión administrativa.

No envía alertas ni confirma que una licitación admita propuestas.
"""
from clasificador_licitaciones import clasificar_licitacion


def priorizar_oportunidad(coincidencia, licitacion, ahora=None):
    vigencia = clasificar_licitacion(licitacion, ahora=ahora)
    geo = coincidencia.get("categoria")
    estado = vigencia["categoria"]
    if not coincidencia.get("coincidencia_tematica"):
        categoria = "sin_coincidencia"
    elif estado == "concluida":
        categoria = "excluida_concluida"
    elif estado == "potencialmente_abierta" and geo == "dentro_de_cobertura":
        categoria = "candidata_revision"
    elif estado == "potencialmente_abierta" and geo == "fuera_de_cobertura":
        categoria = "exploratoria_fuera_cobertura"
    else:
        categoria = "requiere_revision"
    return {
        "categoria_alerta": categoria,
        "vigencia": estado,
        "cobertura": geo,
        "motivo_vigencia": vigencia["motivo"],
    }
