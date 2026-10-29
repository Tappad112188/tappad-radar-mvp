"""Auditoria retrospectiva de clasificacion; no modifica notificaciones."""
from diagnosticar_vigencia_v4 import consulta, norm, contiene, RUBROS, objeto_principal

IDS = (1232, 1254, 1440)

def main():
    registros = consulta("licitaciones", "id,numero_procedimiento,nombre_procedimiento,descripcion,fuente", {"id":"in.("+",".join(map(str,IDS))+")"})
    proveedores = consulta("clientes_giros", "cliente_id,giro_id", {"cliente_id":"eq.4"})
    giros = {int(x["giro_id"]) for x in proveedores}
    if {x["id"] for x in registros} != set(IDS):
        raise SystemExit("Faltan registros de auditoria")
    print("AUDITORIA RETROSPECTIVA | SIN SMTP NI ESCRITURAS")
    print("Giros del proveedor 4:", sorted(giros))
    for l in sorted(registros, key=lambda x:x["id"]):
        texto = norm((l.get("nombre_procedimiento") or "")+" "+(l.get("descripcion") or ""))
        objeto = objeto_principal(l)
        rubros = [g for g in giros if any(contiene(texto,k) for k in RUBROS.get(g,()))]
        compatibles = [g for g in rubros if objeto is None or g == objeto]
        print(l["id"], l["numero_procedimiento"], "objeto=",objeto, "rubros=",sorted(rubros), "compatibles=",sorted(compatibles))
        if l["id"] == 1232:
            assert objeto == 7, "Equipo medico debe clasificarse como giro 7"
            assert 3 not in rubros, "Falsa coincidencia de informatica"
            assert not compatibles, "El proveedor 4 no debe recibir esta alerta por giro"
        elif l["id"] in (1254,1440):
            assert objeto == 13, "Obra debe clasificarse como giro 13"
            assert 13 in compatibles, "Obra compatible con giro 13"
    print("AUDITORIA OK: equipo medico excluido; obras compatibles.")
    print("Historial de notificaciones intacto.")

if __name__=="__main__":
    main()
