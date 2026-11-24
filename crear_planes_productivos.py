"""Creacion supervisada de planes; nunca crea suscripciones ni pagos."""
import os, json
from urllib.request import Request, urlopen
from preflight_planes_productivos import inventario, SPECS, consultar

def crear(token, seller, get=consultar, post=None):
    if post is None:
        def post(payload):
            req = Request("https://api.mercadopago.com/preapproval_plan",
                data=json.dumps(payload).encode(), method="POST",
                headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
            with urlopen(req, timeout=20) as r:
                return json.load(r)
    output = {}
    for name, (amount, frequency) in SPECS.items():
        candidates = inventario(token, seller, get)["candidates"][name]
        reason = "TAPPAD Radar - Alertas " + name.capitalize()
        if candidates:
            if len(candidates) != 1 or candidates[0]["reason"] != reason or candidates[0]["status"] != "active":
                raise ValueError("plan_existente_requiere_revision_"+name)
            pid = candidates[0]["id"]
        else:
            row = post({"reason":reason,"auto_recurring":{"frequency":frequency,"frequency_type":"months","transaction_amount":amount,"currency_id":"MXN"},"back_url":"https://tappad112188.github.io/tappad-radar-mvp/"})
            pid = row.get("id")
        if not isinstance(pid,str) or not pid.isascii() or not pid.isalnum():
            raise ValueError("id_plan_invalido")
        verified = get(token, "/preapproval_plan/"+pid)
        a = verified.get("auto_recurring") or {}
        if verified.get("id") != pid or verified.get("status") != "active" or verified.get("reason") != reason or a.get("transaction_amount") != amount or a.get("frequency") != frequency or a.get("frequency_type") != "months" or a.get("currency_id") != "MXN":
            raise ValueError("plan_no_verificado_"+name)
        output[name] = pid
    return {"planes_verificados":output,"suscripciones_creadas":0,"cobros":0}

if __name__ == "__main__":
    if os.environ.get("CONFIRMAR") != "CREAR_PLANES":
        raise SystemExit("Confirmacion requerida")
    print(json.dumps(crear(os.environ["TAPPAD_MERCADOPAGO_PROD_ACCESS_TOKEN"],os.environ["TAPPAD_MERCADOPAGO_SELLER_ID"])))
