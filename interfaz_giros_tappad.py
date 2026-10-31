"""Interfaz local de pruebas para preferencias de proveedores TAPPAD Radar.

Ejecutar en PC administrativa: py interfaz_giros_tappad.py
Requiere variables SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
Solo escucha en 127.0.0.1; no es un portal público.
"""
import http.server
import getpass
import json
import os
import secrets
import urllib.parse
import webbrowser
from html import escape

from catalogos_preferencias_backend import buscar_catalogo, guardar_preferencias, _request

TOKEN = secrets.token_urlsafe(32)
PORT = int(os.getenv("TAPPAD_GIROS_PORT", "8765"))
PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TAPPAD Radar | Actividades</title>
<style>
:root{font-family:system-ui,Arial;color:#14283c;background:#f3f6fa}*{box-sizing:border-box}body{margin:0}.wrap{max-width:1050px;margin:auto;padding:32px 18px}header{background:#12344c;color:white;padding:22px 0}header .wrap{padding:0 18px}h1{margin:0;font-size:25px}header p{margin:6px 0 0;color:#c5d6e0}.panel{background:white;border:1px solid #dbe3eb;border-radius:12px;padding:20px;margin:18px 0}h2{margin:0 0 16px;font-size:19px}label{font-weight:650;display:block;margin-bottom:7px}input,select,button{font:inherit;padding:11px;border-radius:8px;border:1px solid #b9c8d4}input{width:100%}button{cursor:pointer;background:#126b84;color:white;border:0}button.secondary{background:#e7eff3;color:#163b50}button:disabled{opacity:.5;cursor:not-allowed}.search{display:grid;grid-template-columns:1fr 180px 110px;gap:10px}.entry{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid #e8edf1}.entry:last-child{border-bottom:0}.meta{font-size:13px;color:#5c7080}.small{font-size:13px;color:#516576}.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}.message{margin:14px 0;font-weight:600}.error{color:#a22525}.ok{color:#126c3b}.pill{display:inline-block;background:#e7f1f6;padding:4px 8px;border-radius:20px;font-size:12px}#results,#selected{max-height:370px;overflow:auto}@media(max-width:650px){.search,.row{grid-template-columns:1fr}}</style></head>
<body><header><div class="wrap"><h1>TAPPAD Radar</h1><p>Registro de actividades comerciales · Modo administrativo de pruebas</p></div></header>
<main class="wrap"><section class="panel"><h2>1. Proveedor</h2><label for="client">Selecciona un proveedor registrado</label><select id="client" style="width:100%"></select><p class="small">Solo se muestran proveedores existentes. Esta interfaz es local, no un portal para clientes.</p></section>
<section class="panel"><h2>2. Buscar en catálogos oficiales</h2><div class="search"><input id="term" placeholder="Ej. limpieza, oficina, 21101" aria-label="Actividad o código"><select id="system" aria-label="Catálogo"><option value="">SAT y CUCOP</option><option>SAT</option><option>CUCOP</option></select><button id="searchBtn">Buscar</button></div><div id="results" aria-live="polite"></div></section>
<section class="panel"><h2>3. Actividad manual</h2><div class="search" style="grid-template-columns:1fr 110px"><input id="manual" placeholder="Describe una actividad que no esté en el catálogo"><button id="manualBtn">Agregar</button></div></section>
<section class="panel"><h2>4. Actividades seleccionadas <span class="pill" id="count">0</span></h2><div id="selected"></div><p class="small">Guardar agrega nuevas actividades; no elimina las previamente registradas.</p><button id="saveBtn">Guardar preferencias</button><div class="message" id="msg" role="status"></div></section></main>
<script>
const token=new URLSearchParams(location.search).get("token")||"";
const selected=new Map();
const el=id=>document.getElementById(id);
const key=r=>[r.origen,r.clave||r.descripcion.toLowerCase(),r.version||""].join("|");
const txt=(tag,value,cls)=>{let e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;return e};
async function api(path,opts={}){const r=await fetch(path,{...opts,headers:{"X-Tappad-Token":token,"Content-Type":"application/json",...(opts.headers||{})}});const d=await r.json();if(!r.ok)throw Error(d.error||"Error de conexión");return d}
function msg(s,ok=false){el("msg").textContent=s;el("msg").className="message "+(ok?"ok":"error")}
function entry(r,action,label){let row=txt("div","","entry"),detail=txt("div","");detail.append(txt("div",r.descripcion));detail.append(txt("div",r.origen+(r.clave?" · "+r.clave:"")+(r.version?" · "+r.version:""),"meta"));let b=txt("button",label,"secondary");b.onclick=action;row.append(detail,b);return row}
function render(){el("selected").replaceChildren();for(const [k,r] of selected){el("selected").append(entry(r,()=>{selected.delete(k);render()},"Quitar"))}el("count").textContent=selected.size;el("saveBtn").disabled=!selected.size}
async function load(){try{let rows=await api("/api/clientes");el("client").replaceChildren();for(let r of rows){let o=document.createElement("option");o.value=r.id;o.textContent=r.empresa+" (ID "+r.id+")";el("client").append(o)}if(!rows.length)msg("No hay proveedores registrados")}catch(e){msg(e.message)}}
el("searchBtn").onclick=async()=>{let term=el("term").value.trim();if(term.length<2){msg("Escribe al menos dos caracteres");return}el("results").replaceChildren(txt("p","Buscando…"));try{let qs=new URLSearchParams({q:term,sistema:el("system").value});let rows=await api("/api/buscar?"+qs);el("results").replaceChildren();if(!rows.length)el("results").append(txt("p","Sin coincidencias"));for(let r of rows){let item={origen:r.sistema,clave:r.clave,descripcion:r.descripcion,version:r.version};el("results").append(entry(item,()=>{selected.set(key(item),item);render()},"Agregar"))}}catch(e){el("results").replaceChildren();msg(e.message)}};
el("term").onkeydown=e=>{if(e.key==="Enter")el("searchBtn").click()};
el("manualBtn").onclick=()=>{let descripcion=el("manual").value.trim();if(!descripcion||descripcion.length>500){msg("La actividad manual debe tener entre 1 y 500 caracteres");return}let r={origen:"MANUAL",clave:null,version:null,descripcion};selected.set(key(r),r);el("manual").value="";render()};
el("saveBtn").onclick=async()=>{let id=Number(el("client").value);if(!id){msg("Selecciona un proveedor");return}el("saveBtn").disabled=true;try{let rows=await api("/api/guardar",{method:"POST",body:JSON.stringify({cliente_id:id,selecciones:[...selected.values()]})});selected.clear();render();msg("Guardado completado. Nuevas actividades: "+rows.length,true)}catch(e){msg(e.message)}finally{render()}};
render();load();
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def send(self, status, payload, content_type="application/json; charset=utf-8"):
        body = payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        return secrets.compare_digest(self.headers.get("X-Tappad-Token", ""), TOKEN)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path)
        if path.path == "/":
            # HTML only after valid one-time URL token.
            qs = urllib.parse.parse_qs(path.query)
            if not secrets.compare_digest(qs.get("token", [""])[0], TOKEN):
                return self.send(403, {"error": "Acceso denegado"})
            return self.send(200, PAGE, "text/html; charset=utf-8")
        if not self.authorized():
            return self.send(403, {"error": "Acceso denegado"})
        try:
            if path.path == "/api/clientes":
                rows = _request("GET", "clientes?select=id,empresa&order=empresa.asc&limit=200")
                return self.send(200, rows)
            if path.path == "/api/buscar":
                args = urllib.parse.parse_qs(path.query)
                rows = buscar_catalogo(args.get("q", [""])[0], args.get("sistema", [""])[0] or None)
                return self.send(200, rows)
            return self.send(404, {"error": "Ruta no encontrada"})
        except (ValueError, KeyError) as exc:
            return self.send(400, {"error": str(exc)})
        except Exception:
            return self.send(500, {"error": "Error interno; revisar terminal"})

    def do_POST(self):
        if not self.authorized():
            return self.send(403, {"error": "Acceso denegado"})
        if urllib.parse.urlsplit(self.path).path != "/api/guardar":
            return self.send(404, {"error": "Ruta no encontrada"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 100000:
                return self.send(413, {"error": "Tamaño inválido"})
            payload = json.loads(self.rfile.read(length))
            cliente_id = payload["cliente_id"]
            # Verificar existencia del proveedor, sin aceptar IDs arbitrarios inexistentes.
            q = urllib.parse.urlencode({"select": "id", "id": "eq." + str(cliente_id), "limit": "1"})
            if not _request("GET", "clientes?" + q):
                return self.send(404, {"error": "Proveedor no encontrado"})
            rows = guardar_preferencias(cliente_id, payload["selecciones"], autorizado=True)
            return self.send(200, rows)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            return self.send(400, {"error": str(exc)})
        except Exception:
            return self.send(500, {"error": "Error interno; revisar terminal"})


def main():
    if not os.environ.get("SUPABASE_URL"):
        os.environ["SUPABASE_URL"] = input("SUPABASE_URL: ").strip()
    if not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = getpass.getpass("SUPABASE_SERVICE_ROLE_KEY (oculta): ").strip()
    if not os.environ["SUPABASE_URL"].startswith("https://") or not os.environ["SUPABASE_SERVICE_ROLE_KEY"]:
        raise SystemExit("URL o clave inválida")
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as server:
        url = f"http://127.0.0.1:{PORT}/?token={TOKEN}"
        print("Interfaz local TAPPAD Radar:", url)
        print("Presiona Ctrl+C para detener el servidor.")
        webbrowser.open(url)
        server.serve_forever()


if __name__ == "__main__":
    main()
