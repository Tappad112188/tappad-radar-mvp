// Piloto exclusivamente de lectura. No contiene operaciones de escritura.
const sid="dbc554730f1141a48cf73881a4e9eb96";
const reply=(status:number,body:unknown)=>new Response(JSON.stringify(body),{status,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}});
Deno.serve(async(req)=>{
 if(req.method!=="POST")return reply(405,{ok:false});
 const secret=Deno.env.get("TAPPAD_CRON_SECRET");
 if(!secret || secret.length<32)return reply(503,{ok:false,estado:"deshabilitado"});
 const supplied=req.headers.get("x-tappad-cron-secret")||"";
 const enc=new TextEncoder();
 const a=new Uint8Array(await crypto.subtle.digest("SHA-256",enc.encode(secret)));
 const b=new Uint8Array(await crypto.subtle.digest("SHA-256",enc.encode(supplied)));
 let diff=0;for(let i=0;i<a.length;i++)diff|=a[i]^b[i];
 if(diff!==0)return reply(403,{ok:false});
 try{
 const token=Deno.env.get("MERCADOPAGO_PROD_ACCESS_TOKEN");
 const seller=Deno.env.get("TAPPAD_MERCADOPAGO_SELLER_ID");
 if(!token||!seller)throw Error("config");
 const get=async(path:string)=>{
 const r=await fetch("https://api.mercadopago.com"+path,{headers:{Authorization:"Bearer "+token},redirect:"error",signal:AbortSignal.timeout(10000)});
 if(!r.ok)throw Error("provider");return await r.json();
 };
 const u=await get("/users/me");
 if(String(u.id)!==seller||u.site_id!=="MLM"||(u.tags||[]).includes("test_user"))throw Error("seller");
 const p=await get("/preapproval/"+sid);
 if(String(p.id)!==sid||String(p.collector_id)!==seller)throw Error("identity");
 if(p.status!=="authorized")return reply(200,{ok:true,modo:"solo_lectura",estado:"esperando_autorizacion"});
 const t=p.auto_recurring;
 if(!t||t.currency_id!=="MXN"||Number(t.transaction_amount)!==449||t.frequency!==1||t.frequency_type!=="months")throw Error("terms");
 const rows=await get("/authorized_payments/search?preapproval_id="+sid+"&limit=100&offset=0");
 if(!Array.isArray(rows.results)||rows.results.length>=100)throw Error("pagination");
 const ids=new Set<string>();
 for(const row of rows.results){
 if(!["processed","approved"].includes(row.status))continue;
 const id=String(row.payment?.id||"");
 if(!/^\d+$/.test(id)||String(row.preapproval_id)!==sid)throw Error("link");
 const pay=await get("/v1/payments/"+id);
 if(String(pay.id)!==id||String(pay.collector_id)!==seller||pay.live_mode!==true|| (pay.preapproval_id && String(pay.preapproval_id)!==sid))throw Error("payment");
 if(pay.status!=="approved")continue;
 if(pay.currency_id!=="MXN"||Number(pay.transaction_amount)!==449||!Number.isFinite(Date.parse(pay.date_approved))||Date.parse(pay.date_approved)>Date.now())throw Error("payment_terms");
 ids.add(id);
 }
 return reply(200,{ok:true,modo:"solo_lectura",estado:"consulta_completada",pagos_verificados:ids.size});
 }catch{return reply(502,{ok:false,estado:"verificacion_detenida"});}
});