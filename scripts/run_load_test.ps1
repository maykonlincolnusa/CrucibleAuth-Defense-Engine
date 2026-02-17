param(
    [string]$HostUrl = "http://localhost:8000",
    [int]$Users = 100,
    [int]$SpawnRate = 10,
    [int]$DurationSeconds = 120
)

locust `
  -f load/locustfile.py `
  --headless `
  --host $HostUrl `
  --users $Users `
  --spawn-rate $SpawnRate `
  --run-time "${DurationSeconds}s"
