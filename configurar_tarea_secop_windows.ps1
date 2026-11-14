# Ejecutar UNA VEZ desde PowerShell del usuario Windows que posee las credenciales SECOP.
# Crea/reemplaza exclusivamente la tarea "TAPPAD Radar - SECOP Coahuila".
# Sin envio comercial: --ciclo-seguro importa, sincroniza y realiza preflight.
$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $base 'ejecutar_secop_windows.py'
if (-not (Test-Path -LiteralPath $script)) { throw "No se encontro ejecutar_secop_windows.py en $base" }
$py = (Get-Command py.exe -ErrorAction Stop).Source
$nombre = 'TAPPAD Radar - SECOP Coahuila'
$accion = New-ScheduledTaskAction -Execute $py -Argument ('-3 "' + $script + '" --ciclo-seguro') -WorkingDirectory $base
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
Register-ScheduledTask -TaskName $nombre -Action $accion -Trigger $triggers -Settings $settings -Principal $principal -Description 'TAPPAD Radar SECOP: 08:00, 13:00, 18:00 Coahuila; ciclo seguro sin SMTP comercial' -Force | Out-Null
$t = Get-ScheduledTask -TaskName $nombre
Write-Host "Tarea configurada: $nombre | Estado: $($t.State)"
$t.Triggers | ForEach-Object { Write-Host ('Horario local: ' + $_.StartBoundary) }
Write-Host 'Modo: ciclo seguro (sin envios SMTP). Requiere sesion Windows iniciada y equipo encendido.'
