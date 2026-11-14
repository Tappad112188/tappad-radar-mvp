# Despliegue seguro del worker comercial — estado BLOQUEADO

## Diagnóstico verificado (2026-11-14)
- Existe rol `tappad_activador_privado` con NOLOGIN y NOINHERIT.
- `tappad_internal.tappad_aplicar_activacion_comercial` es SECURITY INVOKER.
- No hay credencial de login dedicada, servicio privado desplegado ni pagos productivos conciliados.
- **No** convertir el rol a LOGIN ni habilitar `TAPPAD_HABILITAR_ACTIVACION_PRODUCCION` antes de validar permisos y credenciales en un entorno privado.

## Identidad recomendada
1. Aprovisionar un rol de inicio de sesión separado, con contraseña generada por el gestor de secretos del entorno de ejecución; nunca registrar la contraseña en GitHub ni en SQL versionado.
2. Mantener `tappad_activador_privado` como rol sin login; no concederle `BYPASSRLS`, `CREATEROLE`, `CREATEDB`, ni acceso a schemas ajenos.
3. Revisar privilegios mínimos sobre `pagos_tappad`, `suscripciones_tappad`, `planes_tappad`, `acceso_comercial_tappad`, `activaciones_comerciales_tappad` y secuencia de activaciones. Dado que la función es SECURITY INVOKER, el ejecutor necesitará permisos efectivos sobre las tablas afectadas: **no basta conceder EXECUTE**. No asignar permisos amplios sin pruebas de aislamiento.
4. La identidad dedicada no debe ser accesible desde navegador, scripts de clientes, el equipo Windows del usuario ni workflows de GitHub compartidos.
5. Mantener el vendedor esperado como secreto separado y validar coincidencia con la API de Mercado Pago.

## Despliegue privado
- Ejecutar `worker_activacion_comercial.py` como job privado con egress HTTPS a Mercado Pago y Supabase, y TLS a PostgreSQL.
- Variables privadas: `TAPPAD_SUPABASE_URL`, `TAPPAD_SUPABASE_SERVICE_ROLE_KEY`, `TAPPAD_MERCADOPAGO_PROD_ACCESS_TOKEN`, `TAPPAD_MERCADOPAGO_SELLER_ID`, `TAPPAD_POSTGRES_DSN`.
- Arrancar exclusivamente sin `--activar` y con `TAPPAD_HABILITAR_ACTIVACION_PRODUCCION=NO`.
- No habilitar un cron de escritura mientras no existan permisos probados, alertas, control de concurrencia y revisión de renovaciones.

## Validación de salida
- Pruebas unitarias y de integración en staging; comprobar que una identidad no autorizada no puede ejecutar la función ni modificar tablas.
- Confirmar pagos productivos legítimos, importes, moneda, seller, suscripción, periodos, duplicados, reversos, vencimientos y reintentos.
- Verificar rollback de una transacción fallida y ausencia de activación por un pago de prueba.
- Solo después de aprobación explícita habilitar ejecución real en un worker privado.

## Riesgo pendiente
La función SQL actual confía en evidencia JSON presentada por el worker y no autentica criptográficamente la evidencia dentro de PostgreSQL. El aislamiento del worker y sus secretos es un requisito de seguridad, no un detalle opcional.
