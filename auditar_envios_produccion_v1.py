"""TAPPAD Radar: auditoria de seguridad previa a envios reales.
Solo lectura. No envia correo ni escribe en Supabase.
"""
from collections import Counter
from diagnosticar_vigencia_v4 import consulta

def main():
    clientes=consulta("clientes","id,empresa,correo,activo,correos_prueba",{"activo":"eq.true"})
    registros=consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado,intentos")
    pares=Counter((r["cliente_id"],r["licitacion_id"]) for r in registros)
    repetidos=[par for par,cantidad in pares.items() if cantidad>1]
    permitidos={"enviado","pendiente","procesando","error","fallido"}
    estados=Counter(str(r.get("estado")) for r in registros)
    print("AUDITORIA TAPPAD RADAR | SOLO LECTURA")
    print("Proveedores activos:",len(clientes))
    print("Registros de notificacion:",len(registros))
    print("Pares duplicados:",len(repetidos))
    print("Estados registrados:",dict(estados))
    for c in clientes:
        correo=str(c.get("correo") or "").strip()
        valido=("@" in correo and "." in correo.rsplit("@",1)[-1] and " " not in correo)
        pruebas=c.get("correos_prueba") or []
        print(f"Proveedor {c['id']} | correo configurado: {'si' if correo else 'no'} | formato basico: {'valido' if valido else 'REVISAR'} | correos de prueba: {len(pruebas)}")
    if repetidos: raise SystemExit("ERROR: hay pares duplicados")
    if any(e not in permitidos for e in estados): print("AVISO: hay estados no contemplados para el futuro motor")
    print("Sin correos enviados. Sin cambios en Supabase.")

if __name__=="__main__":
    main()
