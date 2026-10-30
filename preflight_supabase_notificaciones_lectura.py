"""Preflight real SOLO LECTURA de Supabase para TAPPAD Radar.

No hace POST/PATCH/DELETE, no llama SMTP, no muestra correos ni secretos.
Se ejecuta con las credenciales de servidor del workflow.
"""
import json
from collections import Counter
from diagnosticar_vigencia_v4 import consulta
from control_notificaciones import autorizar_envio_real


def main():
    config = consulta("configuracion_operativa_tappad", "clave,valor",
                      {"clave": "eq.alertas_automaticas_habilitadas"})
    if len(config) != 1:
        raise SystemExit("ERROR: configuracion de alertas ausente o ambigua")
    valor = str(config[0].get("valor", "")).strip().lower()
    print("Interruptor automatico:", valor)
    if valor != "false":
        raise SystemExit("BLOQUEO: el interruptor debe permanecer apagado para esta prueba")

    registros = consulta("notificaciones_enviadas",
                        "cliente_id,licitacion_id,estado,intentos")
    pares = [(r["cliente_id"], r["licitacion_id"]) for r in registros]
    if len(set(pares)) != len(pares):
        raise SystemExit("ERROR: historial con pares duplicados")
    permitidos = {"pendiente", "procesando", "enviado", "error"}
    estados = Counter(r["estado"] for r in registros)
    if not set(estados).issubset(permitidos):
        raise SystemExit("ERROR: estados inesperados")
    if any(int(r["intentos"]) < 0 for r in registros):
        raise SystemExit("ERROR: intentos negativos")
    print("Historial:", len(registros), "estados:", json.dumps(estados, sort_keys=True))

    licitaciones = consulta("licitaciones", "id,fuente,estatus,fecha_apertura")
    fuentes = Counter(l["fuente"] for l in licitaciones)
    print("Licitaciones:", len(licitaciones), "por fuente:", json.dumps(fuentes, sort_keys=True))
    if not licitaciones:
        raise SystemExit("ERROR: no hay licitaciones para evaluar")
    bloqueadas = Counter()
    for licitacion in licitaciones:
        autorizado, motivo = autorizar_envio_real(
            {"alertas_automaticas_habilitadas": valor}, licitacion)
        if autorizado:
            raise SystemExit("ERROR: se autorizo un envio con interruptor apagado")
        bloqueadas[motivo] += 1
    print("Evaluaciones bloqueadas:", sum(bloqueadas.values()))
    print("PRE-FLIGHT APROBADO: solo GET; 0 escrituras; 0 correos")


if __name__ == "__main__":
    main()
