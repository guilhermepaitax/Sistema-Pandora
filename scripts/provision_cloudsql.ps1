param(
    [string]$Project = "pandora-474013",
    [string]$Region = "southamerica-east1",
    [string]$Instance = "pandora-db",
    [string]$DbName = "pandora_app",
    [string]$DbUser = "pandora_user",
    [string]$Password,
    [switch]$AutoPassword,
    [int]$PasswordLength = 24
)

function New-RandomPassword {
    param([int]$Length = 24)
    $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    $out = ''
    for ($i = 0; $i -lt $Length; $i++) { $out += $chars[(Get-Random -Min 0 -Max $chars.Length)] }
    $out
}

if (-not $Password -and $AutoPassword) { $Password = New-RandomPassword -Length $PasswordLength }
if (-not $Password) { Write-Host "Use -Password ou -AutoPassword" -ForegroundColor Red; exit 1 }

$gObj = Get-Command gcloud -ErrorAction SilentlyContinue
if ($gObj) {
    gcloud sql databases describe $DbName --instance=$Instance --project=$Project >$null 2>$null
    if ($LASTEXITCODE -ne 0) { gcloud sql databases create $DbName --instance=$Instance --project=$Project }
    gcloud sql users list --instance=$Instance --project=$Project --format "value(name)" | Select-String -Quiet -SimpleMatch $DbUser >$null 2>$null
    if (-not $?) { gcloud sql users create $DbUser --instance=$Instance --project=$Project --password=$Password }
}
else { Write-Host "(dry-run sem gcloud)" }

$encoded = [System.Uri]::EscapeDataString($Password)
$databaseUrl = "postgres://${DbUser}:${encoded}@/${DbName}?host=/cloudsql/${Project}:${Region}:${Instance}"
Write-Output "DATABASE_URL=$databaseUrl"