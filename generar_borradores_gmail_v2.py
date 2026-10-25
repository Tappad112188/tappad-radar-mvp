"""TAPPAD Radar: generar borradores HTML de correo, SIN ENVIO.
Reutiliza el diagnostico v4 (incluidos filtros de vigencia y duplicados).
No escribe en Supabase, no usa SMTP y no envia correos.
"""
from pathlib import Path
from html import escape
import re
from diagnosticar_vigencia_v4 import main as generar_diagnostico

BASE=Path(__file__).resolve().parent

def enlace(texto):
    t=texto.strip()
    if t.startswith(("https://","http://")):
        u=escape(t,quote=True)
        return '<a href="'+u+'">'+escape(t)+'</a>'
    return escape(t)

def convertir_bloque(bloque):
    lineas=[x.strip() for x in bloque.splitlines() if x.strip()]
    if not lineas: return None
    nombre=lineas[0].replace("TAPPAD Radar | Vista previa para ","",1)
    grupos=[]; actual=None
    for linea in lineas:
        if linea.startswith("Procedimiento: "):
            if actual: grupos.append(actual)
            actual={"Procedimiento":linea.split(": ",1)[1]}
        elif actual and ": " in linea:
            k,v=linea.split(": ",1)
            actual[k]=v
    if actual: grupos.append(actual)
    if not grupos: return None
    css="font-family:Arial,Helvetica,sans-serif;color:#172b4d;line-height:1.5;max-width:780px;margin:auto"
    html=['<!doctype html><html lang="es"><head><meta charset="utf-8"></head><body>',
          '<div style="'+css+'"><h1 style="color:#143b62">TAPPAD Radar</h1>',
          '<p>Oportunidades de licitacion identificadas para <strong>'+escape(nombre)+'</strong>.</p>',
          '<p><strong>'+str(len(grupos))+(' oportunidad</strong>' if len(grupos)==1 else ' oportunidades</strong>')+'. La fecha limite de presentacion de propuestas coincide con el acto de apertura.</p>']
    for i,g in enumerate(grupos,1):
        html.append('<section style="border:1px solid #d8e0e8;border-radius:8px;padding:18px;margin:18px 0">')
        html.append('<h2 style="font-size:18px;margin:0 0 10px">'+str(i)+'. '+escape(g.get("Objeto","Procedimiento"))+'</h2>')
        html.append('<p><strong>Numero:</strong> '+escape(g.get("Procedimiento",""))+'<br><strong>Fuente:</strong> '+escape(g.get("Fuente",""))+'</p>')
        descripcion=g.get("Descripcion resumida","")
        if descripcion and descripcion.casefold().strip(' .') != g.get('Objeto','').casefold().strip(' .'): html.append('<p>'+escape(descripcion)+'</p>')
        for k in ("Publicacion","Junta de aclaraciones","Presentacion y apertura de propuestas","Fallo programado"):
            if k=="Presentacion y apertura de propuestas":
                html.append('<div style="background:#eaf3fb;border-left:4px solid #143b62;padding:10px;margin:10px 0"><strong>Fecha limite de presentacion y apertura:</strong> '+escape(g.get(k,"No especificada"))+'</div>')
            else:
                html.append('<div><strong>'+escape(k)+':</strong> '+escape(g.get(k,"No especificada"))+'</div>')
        url=g.get("Enlace del procedimiento","")
        if url.startswith(("http://","https://")):
            html.append('<p><strong>Consultar procedimiento:</strong> '+enlace(url)+'</p>')
        docs=g.get("Documentos de referencia","")
        if docs and docs!="No registrados":
            html.append('<p><strong>Documentos de referencia:</strong></p><ul>')
            for item in docs.split("; "):
                tipo,sep,url=item.partition(": ")
                html.append('<li>'+escape(tipo)+': '+enlace(url if sep else item)+'</li>')
            html.append('</ul>')
        html.append('</section>')
    html.append('<p style="font-size:12px;color:#58677b">Aviso informativo. Consulta la plataforma de origen para conocer cambios en cada procedimiento.</p>')
    html.append('</div></body></html>')
    return nombre,grupos,"\n".join(html)

def main():
    generar_diagnostico()
    archivo=BASE/"vista_previa_alertas_tappad_v7.txt"
    texto=archivo.read_text(encoding="utf-8")
    bloques=re.split(r"\n={20,}\n",texto)
    salida=BASE/"borradores_gmail_tappad_v2"
    salida.mkdir(exist_ok=True)
    encontrados=0
    for n,b in enumerate(bloques,1):
        resultado=convertir_bloque(b)
        if not resultado: continue
        nombre,grupos,html=resultado
        destino=salida/("correo_proveedor_"+str(n)+".html")
        destino.write_text(html,encoding="utf-8")
        encontrados+=1
        print(f"Proveedor: {nombre} | Oportunidades: {len(grupos)} | Archivo: {destino.name}")
    print(f"BORRADORES HTML: {encontrados} | SIN ENVIOS | SIN CAMBIOS EN SUPABASE")
    print(f"Carpeta: {salida}")

if __name__=="__main__":
    main()
