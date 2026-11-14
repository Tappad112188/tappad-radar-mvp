# Aprovisionamiento de credencial privada — pendiente de ejecución humana

El rol `tappad_activador_privado` está creado con `NOLOGIN`, sin `BYPASSRLS`, sin privilegios de escritura directa. Tiene SELECT en las tablas necesarias y EXECUTE en la función privada de activación.

## Credencial (solo propietario del proyecto)

1. Generar una contraseña aleatoria fuerte (al menos 32 caracteres) en un gestor de contraseñas local. No pegarla en ChatGPT, commits, logs ni capturas.
2. En Supabase SQL Editor, ejecutar **localmente** la siguiente instrucción sustituyendo el marcador por la contraseña generada, sin guardar el SQL con contraseña en GitHub:

```sql
ALTER ROLE tappad_activador_privado LOGIN PASSWORD 'REEMPLAZAR_CON_CONTRASENA_ALEATORIA';
```

3. Construir el DSN PostgreSQL usando el host, puerto y modalidad de conexión **exactos** que muestra Supabase en el botón Connect. La contraseña debe codificarse correctamente si se usa URI. Preferir SSL obligatorio y conexión compatible con el rol; comprobar si el pooler permite el rol personalizado. No usar usuario postgres.
4. En GitHub Settings > Environments > activacion-comercial > Environment secrets, crear `TAPPAD_POSTGRES_DSN` con ese DSN. Mantener en el mismo entorno los secretos `TAPPAD_SUPABASE_URL`, `TAPPAD_SUPABASE_SERVICE_ROLE_KEY`, `TAPPAD_MERCADOPAGO_PROD_ACCESS_TOKEN`, `TAPPAD_MERCADOPAGO_SELLER_ID`.
5. **No crear todavía** `TAPPAD_HABILITAR_ACTIVACION_PRODUCCION` con valor `SI`. Sin ese secreto el workflow no realiza escrituras, incluso con confirmación manual. Requiere autorización posterior y prueba integral.
6. La evidencia remota es verificada por el worker Python con API Mercado Pago; la función SQL recibe evidencia JSON del worker, no verifica criptográficamente la respuesta. Proteger el worker, el entorno y sus secretos es una condición de seguridad, no opcional.

No se han creado ni almacenado contraseñas en el repositorio.
