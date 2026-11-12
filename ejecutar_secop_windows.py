"""Pipeline SECOP: preparacion por defecto; registro opt-in sin correos."""
import argparse
import json
import subprocess
import sys
try:
    import msvcrt
except ImportError:
    msvcrt = None  # Windows-only; permite probar auditoria en Linux
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

BASE = Path(__file__).resolve().parent
LOG = BASE / "secop_ejecucion_windows.log"
LOCK = BASE / "secop_ejecucion_windows.lock"
PASOS = (
    "descargar_documentos_secop_lote.py",
    "auditar_modificaciones_secop.py",
    "generar_fichas_secop_v3.py",
    "generar_fichas_comerciales_secop.py",
    "revisar_calendarios_secop.py",
    "validar_calendarios_secop_automatico.py",
    "preparar_importacion_secop_supabase.py",
    "auditar_secop_supabase_diario.py",
)

def ejecutar(nombre, log):
    print("Ejecutando:", nombre, flush=True)
    log.write("PASO " + nombre + "\n")
    log.flush()
    try:
        resultado = subprocess.run(
            [sys.executable, str(BASE / nombre)], cwd=str(BASE),
            stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False
        )
    except subprocess.TimeoutExpired:
        log.write("ERROR tiempo agotado: " + nombre + "\n")
        raise SystemExit(124)
    if resultado.returncode:
        log.write("ERROR " + nombre + " codigo=" + str(resultado.returncode) + "\n")
        raise SystemExit(resultado.returncode)

def auditoria_autoriza_registro(resultado, fecha, total, ids_esperados=None):
    return (resultado.get("fecha_consulta") == fecha
            and resultado.get("consulta_supabase") == "realizada"
            and resultado.get("total") == total
            and resultado.get("estado") == "SOLO_LECTURA"
            and resultado.get("importacion_habilitada") is False
            and resultado.get("notificaciones_habilitadas") is False
            and isinstance(resultado.get("nuevos"), list)
            and isinstance(resultado.get("existentes"), list)
            and len(resultado["nuevos"]) + len(resultado["existentes"]) == total
            and (ids_esperados is None or (
                len(ids_esperados) == total
                and len(set(ids_esperados)) == total
                and all(isinstance(uid, str) and uid.startswith("secop-coahuila:") for uid in ids_esperados)
                and set(resultado["nuevos"] + resultado["existentes"]) == set(ids_esperados)
                and len(set(resultado["nuevos"] + resultado["existentes"])) == total)))

def ejecutar_importador(log):
    nombre = "importar_secop_supabase_controlado.py"
    print("Registrando pendientes SECOP (sin correos):", flush=True)
    log.write("PASO " + nombre + " --importar --registrar_pendientes\n")
    log.flush()
    resultado = subprocess.run(
        [sys.executable, str(BASE / nombre), "--importar", "--registrar_pendientes"],
        cwd=str(BASE), stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False
    )
    if resultado.returncode:
        raise SystemExit("Importacion SECOP detenida; revisar log")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registrar-pendientes", action="store_true",
                        help="Registrar nuevos procedimientos SECOP con calendario pendiente; sin correos")
    parser.add_argument("--sincronizar-calendarios", action="store_true",
                        help="Sincronizar fechas preliminares de registros SECOP existentes; sin correos")
    parser.add_argument("--simular-alertas", action="store_true",\n                        help="Calcular coincidencias SECOP sin enviar correos ni escribir en Supabase")\n    args = parser.parse_args()
    if msvcrt is None:
        raise SystemExit("Este ejecutor SECOP requiere Windows")
    with LOCK.open("a+b") as candado:
        try:
            msvcrt.locking(candado.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise SystemExit("Ya existe otra ejecución SECOP activa.")
        try:
            with LOG.open("a", encoding="utf-8") as log:
                log.write("\nINICIO " + datetime.now().isoformat(timespec="seconds") + "\n")
                ejecutar("extractor_secop_hoy_vigentes.py", log)
                fuente = BASE / "secop_hoy_vigentes.json"
                datos = json.loads(fuente.read_text(encoding="utf-8-sig"))
                if (datos.get("fecha_consulta") != datetime.now(ZoneInfo("America/Monterrey")).date().isoformat()
                    or not datos.get("filtros_aplicados") or datos.get("errores") or datos.get("error")
                    or datos.get("coincide_total") is False):
                    raise SystemExit("Extracción inválida; revisar el reporte.")
                if any(r.get("fecha_publicacion") != datos["fecha_consulta"] or str(r.get("estatus","")).casefold() != "vigente" for r in datos.get("registros", [])):
                    raise SystemExit("Lote contiene publicaciones fuera de hoy o no vigentes")
                if not datos.get("registros"):
                    log.write("SIN PROCEDIMIENTOS HOY: no reutilizar documentos anteriores.\n")
                    print("Sin procedimientos nuevos vigentes hoy. Sin cambios.")
                    return
                for paso in PASOS:
                    ejecutar(paso, log)
                if args.registrar_pendientes:
                    auditoria = BASE / "documentos_secop_lote" / "auditoria_supabase_secop.json"
                    resultado = json.loads(auditoria.read_text(encoding="utf-8-sig"))
                    lote = json.loads((BASE / "documentos_secop_lote" / "secop_importacion_pendiente_revision.json").read_text(encoding="utf-8-sig"))
                    ids_esperados = [r.get("uuid_procedimiento") for r in lote.get("registros", [])]
                    if not auditoria_autoriza_registro(resultado, datos["fecha_consulta"], len(datos["registros"]), ids_esperados):
                        raise SystemExit("Auditoria Supabase no confirmada; registro bloqueado")
                    ejecutar_importador(log)
                if args.sincronizar_calendarios:
                    validaciones = json.loads((BASE / "documentos_secop_lote" / "validacion_automatica_secop.json").read_text(encoding="utf-8-sig"))
                    for ficha in validaciones.get("resultados", []):
                        if ficha.get("estado") != "APTO_PRELIMINAR":
                            continue
                        nombre = "sincronizar_calendarios_secop_supabase.py"
                        codigo = ficha.get("referencia")
                        if not codigo:
                            raise SystemExit("Validacion SECOP sin referencia")
                        log.write("PASO " + nombre + " --codigo " + codigo + " --aplicar\\n")
                        log.flush()
                        resultado_sync = subprocess.run(
                            [sys.executable, str(BASE / nombre), "--codigo", codigo, "--aplicar"],
                            cwd=str(BASE), stdout=log, stderr=subprocess.STDOUT, timeout=180, check=False
                        )
                        if resultado_sync.returncode:
                            raise SystemExit("Sincronizacion SECOP detenida: " + codigo)
                if args.simular_alertas:\n                    ejecutar("motor_alertas_secop.py", log)\n                log.write("FIN OK " + datetime.now().isoformat(timespec="seconds") + "\n")
            print("Lote preparado para revisión:", BASE / "documentos_secop_lote" / "secop_importacion_pendiente_revision.json")
            print("Registro de pendientes solicitado." if args.registrar_pendientes else "Sin importación a Supabase y sin correos.")
        finally:
            msvcrt.locking(candado.fileno(), msvcrt.LK_UNLCK, 1)

if __name__ == "__main__":
    main()
