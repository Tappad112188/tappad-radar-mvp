"""Borradores TAPPAD Radar desde coincidencias reales de Supabase.
Sin SMTP ni escrituras. Usa plantilla oficial de siete campos ComprasMX.
"""
from pathlib import Path
import re
from diagnosticar_vigencia_v4 import main as generar_diagnostico
from plantilla_correo_html import construir_correo_html

BASE=Path(__file__).resolve().parent

def convertir_bloque(bloque):
    lineas=[x.strip() for x in bloque.splitlines() if x.strip()]
    if not lineas or not lineas[0].startswith("TAPPAD Radar | Vista previa para "):
        return None
    nombre=lineas[0].split("Vista previa para ",1)[1]
    grupos=[]; actual=None
    campos={
        "Procedimiento":"numero_procedimiento",
        "Fuente":"fuente",
        "Objeto":"nombre_procedimiento",
        "Descripcion resumida":"descripcion",
        "Enlace del procedimiento":"url_procedimiento",
        "Publicacion":"fecha_publicacion",
        "Junta de aclaraciones":"fecha_junta_aclaraciones",
        "Presentacion y apertura de propuestas":"fecha_apertura",
        "Fallo programado":"fecha_fallo_programado",
    }
    for linea in lineas:
        if linea.startswith("Procedimiento: "):
            if actual: grupos.append(actual)
            actual={}
        if actual is not None and ": " in linea:
            etiqueta,valor=linea.split(": ",1)
            campo=campos.get(etiqueta)
            if campo:
                actual[campo]=None if valor in ("No especificada","No disponible","Fecha no disponible, verificar enlace") else valor
    if actual: grupos.append(actual)
    if not grupos:return None
    return nombre,grupos,construir_correo_html(nombre,grupos)

def main():
    generar_diagnostico()
    texto=(BASE/"vista_previa_alertas_tappad_v7.txt").read_text(encoding="utf-8")
    bloques=re.split(r"\n={20,}\n",texto)
    salida=BASE/"borradores_gmail_tappad_v3"
    salida.mkdir(exist_ok=True)
    encontrados=0
    for n,b in enumerate(bloques,1):
        resultado=convertir_bloque(b)
        if not resultado:continue
        nombre,grupos,html=resultado
        destino=salida/("correo_proveedor_"+str(n)+".html")
        destino.write_text(html,encoding="utf-8")
        encontrados+=1
        print(f"Proveedor: {nombre} | Oportunidades: {len(grupos)} | Archivo: {destino.name}")
    print(f"BORRADORES HTML: {encontrados} | SIN ENVIOS | SIN CAMBIOS EN SUPABASE")

if __name__=="__main__":main()
