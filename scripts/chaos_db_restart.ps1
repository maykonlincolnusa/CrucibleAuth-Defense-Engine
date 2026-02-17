param(
    [int]$DowntimeSeconds = 20
)

Write-Host "Stopping DB container..."
docker compose stop db

Write-Host "DB down for $DowntimeSeconds seconds..."
Start-Sleep -Seconds $DowntimeSeconds

Write-Host "Starting DB container..."
docker compose start db

Write-Host "Chaos step completed."
