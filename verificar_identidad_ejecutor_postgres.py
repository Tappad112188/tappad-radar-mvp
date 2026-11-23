"""Preflight solo lectura para la identidad del ejecutor comercial.

No imprime DSN, credenciales ni datos de clientes. No modifica la base.
"""
import json
import os


def verificar_identidad(*, dsn, connect=None):
    if not dsn:
        raise RuntimeError("dsn_privado_ausente")
    if connect is None:
        import psycopg
        connect = psycopg.connect
    with connect(dsn) as conn:
        with conn.cursor() as cur:
            # Reproducir la transición del worker sin modificar datos.
            cur.execute("SET LOCAL ROLE tappad_reversion_privada")
            cur.execute("""SELECT current_user, session_user,
                current_setting('search_path'),
                (SELECT rolcanlogin AND NOT rolsuper AND NOT rolbypassrls FROM pg_roles WHERE rolname=session_user),
                (SELECT rolbypassrls FROM pg_roles WHERE rolname=current_user),
                EXISTS (SELECT 1 FROM pg_proc WHERE oid=to_regprocedure('tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)') AND NOT prosecdef),
                COALESCE(has_function_privilege(current_user,
                  to_regprocedure('tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)'),
                  'EXECUTE'),false)""")
            row = cur.fetchone()
    if row is None:
        raise RuntimeError("sin_resultado_identidad")
    role, session, search_path, login, bypass, installed, execute = row
    return {
        "rol_efectivo": role,
        "rol_sesion": session,
        "rol_puede_login": login,
        "rol_bypass_rls": bypass,
        "funcion_reversion_instalada": installed,
        "puede_ejecutar_reversion": execute,
        "apto_para_reversion": bool(installed and execute and bypass is False and login is True
                                   and role == "tappad_reversion_privada"
                                   and session == "tappad_login_reversion"),
    }


if __name__ == "__main__":
    result = verificar_identidad(dsn=os.getenv("TAPPAD_POSTGRES_DSN"))
    print(json.dumps(result, ensure_ascii=False))
    if not result["apto_para_reversion"]:
        raise SystemExit("BLOQUEADO: identidad PostgreSQL no aprobada")
