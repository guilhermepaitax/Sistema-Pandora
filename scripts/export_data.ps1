<#
 Script simples para exportar dados do Django em JSON.
 Uso:
   powershell.exe -ExecutionPolicy Bypass -File scripts/export_data.ps1 -Output data_full.json
#>
param(
    [string]$Output = "data_full.json"
)

Write-Host "[export_data] Gerando dump JSON em $Output"

$env:PYTHONUNBUFFERED = "1"

python manage.py dumpdata --natural-foreign --natural-primary `
    --exclude contenttypes --exclude auth.permission > $Output

if ($LASTEXITCODE -eq 0) {
    Write-Host "[export_data] Dump concluído: $Output"
}
else {
    Write-Host "[export_data] Falhou (código $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
