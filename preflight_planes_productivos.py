"""Inventario productivo de solo lectura; no crea planes ni cobra."""
import os
from urllib.request import Request, urlopen
import json

SPECS = {"mensual": (449, 1), "anual": (4490, 12)}

def consultar(token, path):
    req = Request("https://api.mercadopago.com" + path,
                  headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    with urlopen(req, timeout=20) as r:
        return json.load(r)

def inventario(token, seller_id, get=consultar):
    seller = get(token, "/users/me")
    if str(seller.get("id")) != seller_id or seller.get("site_id") != "MLM" or "test_user" in (seller.get("tags") or []):
        raise ValueError("vendedor_no_productivo_o_inesperado")
    result = get(token, "/preapproval_plan/search?limit=100&offset=0")
    rows = result.get("results")
    total = result.get("paging", {}).get("total")
    if not isinstance(rows, list) or not isinstance(total, int) or total != len(rows):
        raise ValueError("inventario_incompleto")
    output = {}
    for name, (amount, frequency) in SPECS.items():
        candidates = []
        for row in rows:
            a = row.get("auto_recurring") or {}
            if a.get("transaction_amount") == amount and a.get("frequency") == frequency and a.get("frequency_type") == "months" and a.get("currency_id") == "MXN":
                candidates.append({"id": row.get("id"), "status": row.get("status"), "reason": row.get("reason")})
        output[name] = candidates
    return {"seller_verified": True, "total_plans": total, "candidates": output, "writes": 0}

if __name__ == "__main__":
    print(json.dumps(inventario(os.environ["TAPPAD_MERCADOPAGO_PROD_ACCESS_TOKEN"], os.environ["TAPPAD_MERCADOPAGO_SELLER_ID"]), ensure_ascii=False))
