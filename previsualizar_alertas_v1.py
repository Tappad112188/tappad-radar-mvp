"""TAPPAD Radar — motor de coincidencias v3, SOLO LECTURA.
Consulta Supabase, aplica giros, ubicación, apertura futura y deduplicación.
No envía correos ni modifica registros. La vigencia es provisional mientras
la validación del calendario sea 'pendiente'.
"""
import json, os, re, unicodedata
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def norm(v):
    return "".join(c for c in unicodedata.normalize("NFKD", str(v or "").casefold()) if not unicodedata.combining(c))

def consulta(tabla, columnas, params=None):
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ.get("SUPABASE_ADMIN_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key: raise SystemExit("Falta SUPABASE_ADMIN_KEY o SUPABASE_SERVICE_ROLE_KEY")
    salida, offset = [], 0
    while True:
        p = {"select":columnas,"limit":500,"offset":offset}
        if params: p.update(params)
        url = f"{base}/rest/v1/{tabla}?{urlencode(p)}"
        with urlopen(Request(url,headers={"apikey":key,"Authorization":"Bearer "+key}),timeout=45) as res:
            bloque=json.load(res)
        salida.extend(bloque)
        if len(bloque)<500: return salida
        offset += len(bloque)

# Palabras generales no pueden producir por sí solas una alerta especializada.
GENERICAS={"mantenimiento","servicio","servicios","suministro","adquisicion","equipo","material","materiales","compra","contratacion"}
# Cada giro exige al menos una expresión distintiva del rubro.
RUBROS={
 1:("limpieza","detergente","desinfectante","jabon","escoba"),
 2:("papeleria","oficina","toner","papel","cartucho"),
 3:("computo","computadora","tecnologico","laboratorio","servidor","informatica"),
 4:("mobiliario","escritorio","silla","archivero"),
 5:("medicamento","farmaceutico","farmaco"),
 6:("material medico","hospitalario","quirurgico"),
 7:("equipo medico","ultrasonido","rayos x","electromedico"),
 8:("limpieza","jardineria","aseo"),
 9:("vigilancia","seguridad","guardia"),
 10:("inmueble","edificio","instalacion","infraestructura"),
 11:("vehiculo","automotriz","flotilla"),
 12:("aire acondicionado","climatizacion","hvac","refrigeracion"),
 13:("construccion","obra publica","pozo","pavimentacion","hidraulica"),
 14:("electrico","iluminacion","luminaria"),
 15:("ferreteria","herramienta","tornilleria"),
 16:("uniforme","vestuario","ropa"),
 17:("alimento","abarrote","despensa"),
 18:("capacitacion","curso","taller"),
 19:("consultoria","asesoria","estudio tecnico"),
 20:("transporte","logistica","flete"),
}
def contiene(texto, frase):
    frase=norm(frase)
    return bool(re.search(r"(?<![a-z0-9])"+re.escape(frase)+r"(?![a-z0-9])",texto))

def estado_equivalente(a, b):
    a, b = norm(a).strip(), norm(b).strip()
    alias = {"coahuila de zaragoza": "coahuila", "estado de mexico": "mexico"}
    return bool(a and b and alias.get(a, a) == alias.get(b, b))

def objeto_principal(l):
    t=norm(l.get("nombre_procedimiento"))
    if any(x in t for x in ("acciones en el bachillerato","construccion","obra publica","reposicion del pozo","pavimentacion")): return 13
    if any(x in t for x in ("servicio de limpieza","limpieza y jardineria")): return 8
    return None

def main():
    clientes=consulta("clientes","id,empresa,palabras_clave,activo",{"activo":"eq.true"})
    giros=consulta("clientes_giros","cliente_id,giro_id")
    ubic=consulta("clientes_ubicaciones","cliente_id,estado,municipio")
    catalogo=consulta("giros_comerciales","id,nombre")
    licitaciones=consulta("licitaciones","id,numero_procedimiento,nombre_procedimiento,descripcion,fuente,entidad_federativa,estatus,fecha_apertura,validacion_calendario")
    notificadas=consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado")
    gs=defaultdict(set); us=defaultdict(list)
    for g in giros: gs[g["cliente_id"]].add(g["giro_id"])
    for u in ubic: us[u["cliente_id"]].append(u)
    nombres={g["id"]:g["nombre"] for g in catalogo}
    enviados={(n["cliente_id"],n["licitacion_id"]) for n in notificadas if n["estado"]=="enviado"}
    hoy=datetime.now(ZoneInfo('America/Monterrey')).replace(tzinfo=None)
    print(f"PROVEEDORES ACTIVOS: {len(clientes)} | LICITACIONES: {len(licitaciones)} | NOTIFICACIONES YA ENVIADAS: {len(enviados)}")
    total=0
    borradores=[]
    for c in clientes:
        claves=[norm(x.strip()) for x in re.split(r"[,;\n]",c.get("palabras_clave") or "") if len(x.strip())>=4]
        fuertes=[x for x in claves if x not in GENERICAS]
        hallazgos=[]
        for l in licitaciones:
            if (c["id"],l["id"]) in enviados: continue
            if norm(l.get("estatus")) in {"cancelada","cancelado","concluida","concluido","desierta","adjudicada","adjudicado"}: continue
            apertura=l.get("fecha_apertura")
            if apertura:
                try:
                    if datetime.fromisoformat(apertura.replace("Z","")) < hoy: continue
                except ValueError: continue
            ubicaciones=us[c["id"]]
            entidad=norm(l.get("entidad_federativa"))
            if ubicaciones and (not entidad or not any(estado_equivalente(u.get("estado"),entidad) for u in ubicaciones)): continue
            texto=norm((l.get("nombre_procedimiento") or "")+" "+(l.get("descripcion") or ""))
            rubros=[g for g in gs[c["id"]] if any(contiene(texto,kw) for kw in RUBROS.get(g,(nombres.get(g,""),)))]
            objeto=objeto_principal(l)
            if objeto is not None:
                if gs[c["id"]] and objeto not in gs[c["id"]]: continue
                if objeto==13 and not gs[c["id"]]: continue
                rubros=[g for g in rubros if g==objeto]
            palabras=[x for x in fuertes if contiene(texto,x)]
            # Si hay giros, uno de ellos debe coincidir; además se requiere palabra específica
            # cuando el proveedor tiene palabras clave específicas configuradas.
            if gs[c["id"]] and not rubros: continue
            if fuertes and not palabras and not rubros: continue
            if not rubros and not palabras: continue
            hallazgos.append((l,rubros,palabras))
        print(f"\n{c['empresa']}: {len(hallazgos)} coincidencias filtradas")
        for l,r,p in hallazgos[:20]:
            print(f"  {l['numero_procedimiento']} | {l['fuente']} | calendario={l['validacion_calendario']} | giros={','.join(map(str,r)) or '-'} | claves={','.join(p) or '-'}")
        if len(hallazgos)>20: print(f"  ... {len(hallazgos)-20} adicionales")
        total+=len(hallazgos)
        if hallazgos:
            lineas=["TAPPAD Radar | Vista previa para "+c["empresa"],"",
                    "BORRADOR NO ENVIABLE: calendarios pendientes de verificacion oficial.","",
                    "Oportunidades identificadas: "+str(len(hallazgos)),""]
            for l,r,p in hallazgos:
                lineas += ["Procedimiento: "+str(l.get("numero_procedimiento") or "SIN NUMERO"),
                           "Fuente: "+str(l.get("fuente") or "No indicada"),
                           "Objeto: "+str(l.get("nombre_procedimiento") or "No indicado"),
                           "Apertura registrada: "+str(l.get("fecha_apertura") or "SIN FECHA"),
                           "Validacion de calendario: "+str(l.get("validacion_calendario") or "SIN VALIDACION"),
                           "Estado: REQUIERE REVISION OFICIAL",""]
            borradores.append("\\n".join(lineas))
    print(f"\nTOTAL FILTRADO: {total} | SOLO LECTURA, SIN CORREOS")
    print("Clasificacion principal conservadora; pendientes requieren revision oficial.")

if __name__=="__main__": main()
