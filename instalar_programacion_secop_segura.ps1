# Instala 3 ejecuciones diarias SECOP en modo seguro, sin SMTP.
$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$dir = Join-Path $env:LOCALAPPDATA 'TAPPAD-Radar-SECOP'
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$cfg = Join-Path $dir 'supabase-secure.xml'
$url = $env:SUPABASE_URL
if (-not $url) { $url = Read-Host 'SUPABASE_URL (https://...supabase.co)' }
if ($url -notmatch '^https://[a-z0-9.-]+\\.supabase\\.co/?$') { throw 'SUPABASE_URL invalida' }
$key = $env:SUPABASE_ADMIN_KEY
if (-not $key) { $key = $env:SUPABASE_SERVICE_ROLE_KEY }
if ($key) {
  $secure = ConvertTo-SecureString -String $key -AsPlainText -Force
} else {
  $secure = Read-Host 'SUPABASE_ADMIN_KEY (se cifra para tu usuario de Windows)' -AsSecureString
}
[pscustomobject]@{Url=$url.TrimEnd('/');Key=$secure} | Export-Clixml -Path $cfg -Force
$runner = Join-Path $dir 'ejecutar_secop_programado.ps1'
$source = @'
$ErrorActionPreference = "Stop"
$cfg = Import-Clixml -Path (Join-Path $env:LOCALAPPDATA "TAPPAD-Radar-SECOP\\supabase-secure.xml")
$env:SUPABASE_URL = $cfg.Url
$env:SUPABASE_ADMIN_KEY = [System.Net.NetworkCredential]::new("",$cfg.Key).Password
$env:TAPPAD_SECOP_ENVIO_REAL = "NO"
Set-Location "__BASE__"
& py ".\\ejecutar_secop_windows.py" --ciclo-seguro
if ($LASTEXITCODE -ne 0) { throw "SECOP fallo con codigo $LASTEXITCODE" }
'@
$source = $source.Replace('__BASE__', $base.Replace("'","''"))
Set-Content -Path $runner -Value $source -Encoding UTF8
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$runner+'"')
$triggers = @(
  (New-ScheduledTaskTrigger -Daily -At '08:00'),
  (New-ScheduledTaskTrigger -Daily -At '13:00'),
  (New-ScheduledTaskTrigger -Daily -At '18:00')
)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'TAPPAD Radar - SECOP ciclo seguro' -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Force | Out-Null
Write-Host 'TAREA CREADA: 08:00, 13:00, 18:00 (hora local Windows). Sin SMTP.'
Write-Host 'Requiere sesion de Windows iniciada y equipo encendido.'
Get-ScheduledTask -TaskName 'TAPPAD Radar - SECOP ciclo seguro' | Select-Object TaskName,State
