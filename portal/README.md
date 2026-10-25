# TAPPAD Radar — Portal de proveedores (MVP)
Estado: prototipo de acceso y consulta, **no publicado**. No procesa pagos.
## Configuración
1. Copiar config.example.js a config.js e ingresar la clave **pública** publishable/anon de Supabase (nunca la administrativa).
2. Publicar con un alojamiento HTTPS de archivos estáticos y configurar la URL de redirección en Supabase Auth.
3. Crear usuarios con Supabase Auth y vincularlos de forma administrativa a clientes existentes en usuarios_clientes_tappad.
4. Validar el aislamiento entre dos cuentas antes de habilitar altas públicas.
5. Mantener los cobros reales desactivados hasta integrar la pasarela con webhooks verificados del servidor.
## Seguridad
No usar service_role en el navegador. La vinculación de usuarios a empresas es exclusiva del backend administrativo. No se permiten inserciones ni modificaciones de pagos desde el portal.
