# Actualizacion controlada SECOP: descarga version verificada, respaldo y compilacion.
# No modifica tareas programadas ni ejecuta envios.
$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = 'Tappad112188/tappad-radar-mvp'
$ref = '2e6086a95a67945bdc892d6d127f1437916462d1'
$archivos = @(
 'extractor_secop_hoy_vigentes.py',
 'descargar_documentos_secop_lote.py',
 'auditar_secop_supabase_diario.py',
 'importar_secop_supabase_controlado.py',
 'ejecutar_secop_windows.py',
 'entregar_alertas_secop.py'
)
$marca = Get-Date -Format 'yyyyMMdd_HHmmss'
$respaldo = Join-Path $base ("respaldo_secop_" + $marca)
$temporal = Join-Path $env:TEMP ("tappad_secop_" + $marca)
New-Item -ItemType Directory -Path $respaldo,$temporal -Force | Out-Null
try {
 foreach ($archivo in $archivos) {
  $origen = Join-Path $base $archivo
  if (-not (Test-Path -LiteralPath $origen)) { throw "Falta archivo local: $archivo" }
  Copy-Item -LiteralPath $origen -Destination (Join-Path $respaldo $archivo) -ErrorAction Stop
  $url = "https://raw.githubusercontent.com/$repo/$ref/$archivo"
  Invoke-WebRequest -Uri $url -OutFile (Join-Path $temporal $archivo) -ErrorAction Stop
  if ((Get-Item (Join-Path $temporal $archivo)).Length -lt 100) { throw "Descarga incompleta: $archivo" }
 }
 Push-Location $temporal
 try {
  & py.exe -3 -m py_compile @archivos
  if ($LASTEXITCODE -ne 0) { throw "Error de sintaxis; no se instala" }
 } finally { Pop-Location }
 foreach ($archivo in $archivos) {
  Copy-Item -LiteralPath (Join-Path $temporal $archivo) -Destination (Join-Path $base $archivo) -Force
 }
 Write-Host "ACTUALIZACION INSTALADA. Respaldo: $respaldo"
 Write-Host "No se ejecuto ninguna importacion ni envio."
} catch {
 Write-Warning "Instalacion detenida: $($_.Exception.Message)"
 foreach ($archivo in $archivos) {
  $original = Join-Path $respaldo $archivo
  if (Test-Path -LiteralPath $original) { Copy-Item -LiteralPath $original -Destination (Join-Path $base $archivo) -Force }
 }
 throw
} finally {
 Remove-Item -LiteralPath $temporal -Recurse -Force -ErrorAction SilentlyContinue
}
