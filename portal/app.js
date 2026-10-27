import { createClient } from "https://esm.sh/@supabase/supabase-js@2.57.0";
const el=id=>document.getElementById(id);
const show=id=>{for(const name of ["setup","auth","reset","panel"])el(name).hidden=name!==id};
const status=s=>{el("status").textContent=s||""};
const item=(container,text)=>{const d=document.createElement("div");d.className="item";d.textContent=text;container.append(d)};
let config;
try {config=await import("./config.js")} catch {show("setup");status("El portal no está configurado.");}
if(config){
 const {SUPABASE_URL:url,SUPABASE_PUBLISHABLE_KEY:key}=config;
 if(!url?.startsWith("https://")||!key||key.includes("REEMPLAZAR")){show("setup");status("Configuración pública incompleta.");}
 else {
  const db=createClient(url,key);
  async function load(user){
   show("panel");el("who").textContent=user.email||"Cuenta autenticada";
   for(const id of ["companies","subscriptions","payments"])el(id).replaceChildren();
   const {data:links,error:linkError}=await db.from("usuarios_clientes_tappad").select("cliente_id,rol");
   if(linkError){status("No se pudieron consultar las empresas vinculadas.");return}
   if(!links?.length){item(el("companies"),"Tu cuenta aún no está vinculada a una empresa. Contacta a TAPPAD.");return}
   for(const link of links)item(el("companies"),"Empresa ID "+link.cliente_id+" · "+link.rol);
   const ids=links.map(x=>x.cliente_id);
   const {data:subs,error:subError}=await db.from("suscripciones_tappad").select("id,cliente_id,estado,inicio,fin_periodo,plan_id").in("cliente_id",ids);
   if(subError)status("No se pudieron consultar las suscripciones.");
   else if(!subs?.length)item(el("subscriptions"),"No hay suscripciones registradas.");
   else for(const s of subs)item(el("subscriptions"),"Empresa "+s.cliente_id+" · Estado: "+s.estado+" · Vencimiento: "+(s.fin_periodo||"No definido"));
   if(subs?.length){
    const {data:pays,error:payError}=await db.from("pagos_tappad").select("suscripcion_id,monto_mxn,estado,fecha_pago").in("suscripcion_id",subs.map(x=>x.id));
    if(payError)status("No se pudo consultar el historial de pagos.");
    else if(!pays?.length)item(el("payments"),"No hay pagos registrados.");
    else for(const p of pays)item(el("payments"),"$"+Number(p.monto_mxn).toFixed(2)+" MXN · "+p.estado+" · "+(p.fecha_pago||"Sin fecha"));
   }else item(el("payments"),"No hay pagos registrados.");
  }
  const recovery=()=>new URLSearchParams(location.hash.slice(1)).get("type")==="recovery";
  db.auth.onAuthStateChange((event)=>{if(event==="PASSWORD_RECOVERY")show("reset")});
  el("forgot").addEventListener("click",async()=>{const email=el("email").value.trim();if(!email){status("Escribe tu correo electrónico para solicitar el restablecimiento.");return}const {error}=await db.auth.resetPasswordForEmail(email,{redirectTo:location.origin+location.pathname});status(error?"No fue posible solicitar el correo de restablecimiento.":"Si la cuenta existe, recibirás instrucciones por correo.")});
  el("reset-form").addEventListener("submit",async e=>{e.preventDefault();const password=el("new-password").value;const {error}=await db.auth.updateUser({password});el("new-password").value="";if(error){status("No fue posible establecer la contraseña.");return}history.replaceState(null,"",location.pathname);status("Contraseña actualizada.");await refresh()});
  async function refresh(){const {data:{user},error}=await db.auth.getUser();if(error||!user){show("auth");return}if(recovery()){show("reset");return}await load(user)}
  el("login").addEventListener("submit",async e=>{e.preventDefault();status("");const email=el("email").value.trim(),password=el("password").value;const {error}=await db.auth.signInWithPassword({email,password});el("password").value="";if(error){status("No se pudo iniciar sesión. Revisa tus credenciales.");return}await refresh()});
  el("logout").addEventListener("click",async()=>{await db.auth.signOut();show("auth");status("")});
  await refresh();
 }
}