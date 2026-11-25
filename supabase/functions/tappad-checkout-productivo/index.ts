import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import {createClient} from "npm:@supabase/supabase-js@2.57.0";
const cors={"Access-Control-Allow-Origin":"https://tappad112188.github.io","Access-Control-Allow-Headers":"authorization, apikey, content-type, x-client-info","Access-Control-Allow-Methods":"GET,POST,OPTIONS","Vary":"Origin"};
const reply=(v:unknown,s=200)=>new Response(JSON.stringify(v),{status:s,headers:{"content-type":"application/json","cache-control":"no-store",...cors}});
Deno.serve(async req=>{
 if(req.method==="OPTIONS")return new Response(null,{status:204,headers:cors});
 if(!["GET","POST"].includes(req.method))return reply({error:"method_not_allowed"},405);
 const url=Deno.env.get("SUPABASE_URL"),anon=Deno.env.get("SUPABASE_ANON_KEY"),service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
 if(!url||!anon||!service)return reply({error:"configuration_missing"},503);
 const bearer=req.headers.get("authorization")||"";
 if(!bearer.startsWith("Bearer "))return reply({error:"unauthorized"},401);
 const auth=createClient(url,anon,{global:{headers:{Authorization:bearer}}});
 const {data:{user},error:ue}=await auth.auth.getUser();
 if(ue||!user||!user.email_confirmed_at)return reply({error:"verified_buyer_required"},401);
 const db=createClient(url,service);
 const {data:admin,error:ae}=await db.from("administradores_tappad").select("usuario_id").eq("usuario_id",user.id).eq("habilitado",true).maybeSingle();
 if(ae)return reply({error:"admin_check_failed"},500);
 if(admin)return reply({error:"admin_cannot_purchase"},403);
 const {data:links,error:le}=await db.from("usuarios_clientes_tappad").select("cliente_id").eq("usuario_id",user.id);
 if(le||links?.length!==1)return reply({error:"buyer_link_required"},403);
 const clientId=links[0].cliente_id;
 const {data:client,error:ce}=await db.from("clientes").select("correo,activo").eq("id",clientId).maybeSingle();
 if(ce||!client?.activo||String(client.correo).toLowerCase()!==user.email.toLowerCase())return reply({error:"buyer_client_mismatch"},403);
 const token=Deno.env.get("MERCADOPAGO_PROD_ACCESS_TOKEN");
 if(!token)return reply({error:"configuration_missing"},503);
 const mp=async(path:string)=>{const r=await fetch("https://api.mercadopago.com"+path,{headers:{Authorization:"Bearer "+token},signal:AbortSignal.timeout(15000)});if(!r.ok)throw new Error("provider_http_"+r.status);return await r.json();};
 const {data:plans,error:pe}=await db.from("planes_tappad").select("id,codigo,precio_mxn,periodicidad,activo").in("id",[1,3]);
 if(pe)return reply({error:"plan_lookup_failed"},500);
 if(req.method==="GET"){
 try {
 const seller=await mp("/users/me");
 if(!seller.id||seller.site_id!=="MLM"||!Array.isArray(seller.tags)||seller.tags.includes("test_user"))return reply({error:"seller_invalid"},502);
 const {data:maps,error:me}=await db.from("mercadopago_planes_tappad").select("plan_id,mercadopago_plan_id").eq("entorno","produccion").in("plan_id",[1,3]);
 if(me||maps?.length!==2||plans?.length!==2)return reply({error:"mapping_invalid"},409);
 const checks=await Promise.all(plans.map(async plan=>{
 const mapping=maps.find(m=>m.plan_id===plan.id);
 if(!mapping||!/^[a-zA-Z0-9_-]+$/.test(mapping.mercadopago_plan_id))throw new Error("mapping_invalid");
 const remote=await mp("/preapproval_plan/"+mapping.mercadopago_plan_id);
 const a=remote.auto_recurring;
 const valid=remote.id===mapping.mercadopago_plan_id&&remote.status==="active"&&String(remote.collector_id)===String(seller.id)&&a?.currency_id==="MXN"&&Number(a.transaction_amount)===Number(plan.precio_mxn)&&a.frequency_type==="months"&&Number(a.frequency)===(plan.id===1?1:12)&&Number(plan.precio_mxn)===(plan.id===1?449:4490);
 return {plan_id:plan.id,verified:valid};
 }));
 return reply({ok:checks.every(c=>c.verified),checks,checkout_enabled:false,mode:"remote_read_only_preflight"},checks.every(c=>c.verified)?200:502);
 }catch{return reply({error:"provider_verification_failed"},502);}
 }
 return reply({error:"checkout_not_released"},409);
});
