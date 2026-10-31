# Integración de clasificadores oficiales TAPPAD Radar

Fuentes: SAT c_ClaveProdServ, INEGI SCIAN México 2023, ComprasMX CUCOP.

Reglas: conservar código, descripción, versión, fuente; no inferir correspondencias oficiales entre catálogos; coincidencias propuestas deben conservar evidencia y nivel de confianza; ningún correo automático sin validación; SECOP permanece exclusivamente en Windows local; ComprasMX permanece en GitHub Actions.

Esquema propuesto: catalogos_oficiales_tappad(sistema,clave,descripcion,version,fuente_url,vigente); giros_catalogos_tappad(giro_id,sistema,clave,version,validado); licitaciones_catalogos_tappad(licitacion_id,sistema,clave,version,confianza,estado,evidencia). RLS habilitado y permisos solo para backend autorizado.

Pruebas: clasificación DGA01-LPN-CA-E052-2026 como vehículos tácticos/equipamiento vehicular; no clasificar por mera aparición de 'seguridad' como vigilancia privada; validación humana en baja confianza; pruebas de regresión de giros anteriores.
