"""Envío CONTROLADO de cinco alertas de prueba a dos buzones verificados.
No modifica el estado de proveedores ni el historial de notificaciones.
Requiere SMTP_USER y SMTP_APP_PASSWORD (contraseña de aplicación Gmail).
Por defecto solo muestra la simulación; --enviar realiza 10 entregas SMTP.
"""
import argparse
import os
import smtplib
import ssl
from email.message import EmailMessage

BUZONES = ("tappadcons@gmail.com", "gerardotapia112188@gmail.com")
CASOS = (
    ("[PRUEBA] Hidráulica Sabinas", "SECOP Coahuila", ("CEAS-AI3-CO-E006-2026 — Obras de agua potable y pozos profundos en Sabinas",)),
    ("[PRUEBA] Limpieza Integral 2027", "SECOP Coahuila", ("UTC-LPN-CA-E001-2026 — Servicio de limpieza y jardinería 2027",)),
    ("[PRUEBA] Seguridad Coahuila 2027", "SECOP Coahuila", ("UTC-LPN-CA-E002-2026 — Servicio de seguridad y vigilancia 2027",)),
    ("[PRUEBA] Clima Técnico HVAC", "ComprasMX", (
        "LA-12-NCD-012NCD002-N-89-2026 — Mantenimiento preventivo y correctivo HVAC",
        "LA-50-GYR-050GYR018-N-215-2026 — Mantenimiento mayor y refacciones HVAC",
    )),
    ("[PRUEBA] Equipamiento Tecnológico Federal", "ComprasMX", ("LA-11-M00-011M00994-I-524-2026 — Equipo de alta especialidad",)),
)

def mensaje(remitente, destino, empresa, plataforma, licitaciones):
    correo = EmailMessage()
    correo["From"] = remitente
    correo["To"] = destino
    correo["Subject"] = f"[PRUEBA TAPPAD Radar] {empresa} — {plataforma}"
    aviso = ("SECOP: fechas y documentos pendientes de validación oficial. No constituye una alerta de producción."
             if plataforma == "SECOP Coahuila"
             else "ComprasMX: consultar el expediente oficial antes de tomar decisiones.")
    cuerpo = ("PRUEBA CONTROLADA — TAPPAD Radar\n\n"
              f"Proveedor ficticio: {empresa}\nPlataforma: {plataforma}\n\n"
              "Coincidencias de prueba:\n- " + "\n- ".join(licitaciones) + "\n\n"
              + aviso + "\n\nNo responder: este mensaje es una prueba técnica.")
    correo.set_content(cuerpo)
    return correo

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--enviar", action="store_true", help="Autoriza enviar 10 mensajes de prueba")
    args = parser.parse_args()
    total = len(CASOS) * len(BUZONES)
    print(f"Proveedores: {len(CASOS)} | Buzones: {len(BUZONES)} | Correos: {total}")
    if not args.enviar:
        for empresa, plataforma, licitaciones in CASOS:
            print(f"{empresa} | {plataforma} | {len(licitaciones)} licitacion(es) | {', '.join(BUZONES)}")
        print("SIMULACION: no se enviaron correos. Usa --enviar para el envío real.")
        return
    usuario = os.environ.get("SMTP_USER", "").strip()
    clave = os.environ.get("SMTP_APP_PASSWORD", "").strip()
    if not usuario or not clave:
        raise SystemExit("Faltan SMTP_USER o SMTP_APP_PASSWORD en variables de entorno. No se enviaron correos.")
    enviados = 0
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(usuario, clave)
        for empresa, plataforma, licitaciones in CASOS:
            for destino in BUZONES:
                smtp.send_message(mensaje(usuario, destino, empresa, plataforma, licitaciones))
                enviados += 1
                print(f"ACEPTADO POR SMTP: {empresa} -> {destino}")
    print(f"SMTP aceptó {enviados}/{total} mensajes. Verifica bandeja de entrada y spam; aceptación no garantiza entrega final.")

if __name__ == "__main__":
    main()
