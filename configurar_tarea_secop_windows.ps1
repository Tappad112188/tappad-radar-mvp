# Ejecutar UNA VEZ desde PowerShell del usuario Windows que posee las credenciales SECOP.
# Crea/reemplaza exclusivamente la tarea "TAPPAD Radar - SECOP Coahuila".
# Sin envio comercial: --ciclo-seguro importa, sincroniza y realiza preflight.
$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$commit = '883ef02a4875e0292589d8201acaa666be5de5d7'
$origen = 'https://raw.githubusercontent.com/Tappad112188/tappad-radar-mvp/' + $commit + '/'
foreach ($archivo in @('ejecutar_secop_windows.py','entregar_alertas_secop.py')) {
  $destino = Join-Path $base $archivo
  if (Test-Path -LiteralPath $destino) {
    Copy-Item -LiteralPath $destino -Destination ($destino + '.respaldo_piloto_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
  }
  Invoke-WebRequest -Uri ($origen + $archivo) -OutFile $destino -UseBasicParsing
}
$script = Join-Path $base 'ejecutar_secop_windows.py'
if (-not (Test-Path -LiteralPath $script)) { throw "No se encontro ejecutar_secop_windows.py en $base" }
$py = (Get-Command py.exe -ErrorAction Stop).Source
$nombre = 'TAPPAD Radar - SECOP Coahuila'
$lanzador = Join-Path $base 'lanzar_secop_piloto.ps1'
@'
$ErrorActionPreference = 'Stop'
$env:TAPPAD_PILOTO_REAL = 'SI'
$env:TAPPAD_SECOP_ENVIO_REAL = 'SI'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $base
& py.exe -3 (Join-Path $base 'ejecutar_secop_windows.py') --ciclo-automatico-real
exit $LASTEXITCODE
'@ | Set-Content -LiteralPath $lanzador -Encoding UTF8
$accion = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $lanzador + '"') -WorkingDirectory $base
$horarios = @('08:00','13:00','18:00')
$triggers = @($horarios | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ })
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$existente = Get-ScheduledTask -TaskName $nombre -ErrorAction SilentlyContinue
if ($existente) {
  $respaldo = Join-Path $base ('respaldo_tarea_secop_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.xml')
  Export-ScheduledTask -TaskName $nombre | Set-Content -LiteralPath $respaldo -Encoding UTF8
  Write-Host "Respaldo de tarea anterior: $respaldo"
}
Register-ScheduledTask -TaskName $nombre -Action $accion -Trigger $triggers -Settings $settings -Principal $principal -Description 'TAPPAD Radar SECOP: 08:00, 13:00, 18:00 Coahuila; piloto real restringido a dos destinatarios' -Force | Out-Null
$t = Get-ScheduledTask -TaskName $nombre
Write-Host "Tarea configurada: $nombre | Estado: $($t.State)"
$t.Triggers | ForEach-Object { Write-Host ('Horario local: ' + $_.StartBoundary) }
Write-Host 'Modo: piloto SMTP real (solo clientes 1 y 4). Requiere sesion Windows iniciada y equipo encendido.'
