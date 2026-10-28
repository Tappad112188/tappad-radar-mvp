"""TAPPAD Radar: vista previa conjunta ComprasMX + SECOP Coahuila.
Solo lectura: consulta ComprasMX en Supabase y fichas SECOP locales.
NO envia correo, NO escribe Supabase y NO altera los procesos programados.
Uso: py preparar_prueba_integral_tappad.py
"""
import html, json, os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime

ROOT=Path(__file__).resolve().parent
SECOP=ROOT/"documentos_secop_lote"/"fichas_comerciales_secop.json"
DESTINO=ROOT/"documentos_secop_lote"/"vista_previa_integral_tappad.html"
REPORTE=ROOT/"documentos_secop_lote"/"prueba_integral_tappad.json"

def consulta_comprasmx():
    base=os.environ.get("SUPABASE_URL","").rstrip("/")
    key=os.environ.get("SUPABASE_ADMIN_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not key:
        return [],"Sin credenciales Supabase en este equipo; no se puede consultar ComprasMX"
    resultados=[]
    try:
        for offset in range(0,2000,500):
            params=urlencode({"select":"numero_procedimiento,nombre_procedimiento,descripcion,fuente,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,url_procedimiento,estatus","fuente":"ilike.*compras*","order":"fecha_publicacion.desc.nullslast","limit":500,"offset":offset})
            req=Request(base+"/rest/v1/licitaciones?"+params,headers={"apikey":key,"Authorization":"Bearer "+key})
            with urlopen(req,timeout=35) as response:
                bloque=json.load(response)
            resultados.extend(bloque)
            if len(bloque)<500:break
    except Exception as e:
        return [],"No fue posible consultar ComprasMX: "+str(e).split("?",1)[0][:140]
    return resultados,None

def fecha(v):
    if not v:return "No identificada"
    if isinstance(v,dict):
        v=(v.get("fecha") or "")+(" "+v["hora"] if v.get("hora") else "")
    return str(v).replace("T"," ")[:19] or "No identificada"

def ficha_secop(f):
    c=f.get("calendario") or {}
    return {"fuente":"SECOP Coahuila","numero":f.get("referencia") or f.get("codigo"),"objeto":f.get("objeto"),"publicacion":fecha(f.get("publicacion")),"junta":fecha(c.get("junta_aclaraciones")),"apertura":fecha(c.get("limite_presentacion_propuestas")),"fallo":fecha(c.get("fallo_programado")),"url":None}

def ficha_comprasmx(f):
    return {"fuente":f.get("fuente") or "ComprasMX","numero":f.get("numero_procedimiento"),"objeto":f.get("nombre_procedimiento") or f.get("descripcion"),"publicacion":fecha(f.get("fecha_publicacion")),"junta":fecha(f.get("fecha_junta_aclaraciones")),"apertura":fecha(f.get("fecha_apertura")),"fallo":fecha(f.get("fecha_fallo_programado")),"url":f.get("url_procedimiento")}

def render(f):
    esc=lambda x:html.escape(str(x or "No disponible"))
    filas=[("Publicación",f["publicacion"]),("Junta de aclaraciones",f["junta"]),("Presentación de propuestas",f["apertura"]),("Fallo programado",f["fallo"])]
    tabla="".join("<tr><th>"+esc(k)+"</th><td>"+esc(v)+"</td></tr>" for k,v in filas)
    enlace=f.get("url")
    link='<p><a href="'+esc(enlace)+'">Consultar publicación oficial</a></p>' if enlace and str(enlace).startswith("https://") else "<p>Enlace individual no disponible</p>"
    return '<article><h2>'+esc(f["numero"])+'</h2><p><strong>'+esc(f["fuente"])+'</strong></p><p>'+esc(f["objeto"])+'</p><table>'+tabla+'</table>'+link+'</article>'

def main():
    if not SECOP.exists():raise SystemExit("Falta fichas_comerciales_secop.json; primero ejecutar el proceso SECOP")
    secop=json.loads(SECOP.read_text(encoding="utf-8-sig"))
    locales=[ficha_secop(f) for f in secop.get("fichas",[])]
    remotas,error=consulta_comprasmx()
    compras=[ficha_comprasmx(f) for f in remotas]
    # Prueba controlada: las 5 publicaciones más recientes de ComprasMX.
    compras=compras[:5]
    unicas={}
    for f in locales+compras:
        llave=(f["fuente"].casefold(),str(f["numero"] or "").casefold())
        if llave[1]:unicas[llave]=f
    fichas=list(unicas.values())
    estilo="""<style>body{font-family:Arial,sans-serif;max-width:760px;margin:30px auto;padding:0 16px;color:#1a2d43;background:#f5f7fa}
header{background:#142f4e;color:white;padding:24px;border-radius:12px}article{background:white;padding:22px;margin:18px 0;border-radius:12px;border:1px solid #dce4ed}
table{width:100%;border-collapse:collapse}td,th{padding:10px;text-align:left;border-bottom:1px solid #e2e6ec}
footer{background:#e6eff8;padding:20px;border-radius:12px}small{color:#566}</style>"""
    pagina='<!doctype html><html lang="es"><meta charset="utf-8"><title>Prueba integral TAPPAD Radar</title>'+estilo+'<body><header><h1>TAPPAD Radar</h1><p>Vista previa de oportunidades | ComprasMX y SECOP Coahuila</p></header>'
    pagina+="".join(render(f) for f in fichas)
    pagina+='<footer><h2>¿Deseas participar?</h2><p>TAPPAD Consultoría ofrece asesoría especializada para preparar y presentar propuestas de licitación.</p></footer><p><small>VISTA PREVIA INTERNA. Fechas sujetas a cambios oficiales. Sin correos enviados.</small></p></body></html>'
    DESTINO.write_text(pagina,encoding="utf-8")
    REPORTE.write_text(json.dumps({"secop":len(locales),"comprasmx":len(compras),"total_sin_duplicados":len(fichas),"aviso_comprasmx":error,"envios":0,"escrituras_supabase":0},ensure_ascii=False,indent=2),encoding="utf-8")
    print("SECOP:",len(locales),"| ComprasMX:",len(compras),"| Total:",len(fichas))
    if error:print("AVISO:",error)
    print("Vista previa:",DESTINO)
    print("Sin correos ni escrituras en Supabase. Sin cambios a tareas programadas.")

if __name__=="__main__":main()
