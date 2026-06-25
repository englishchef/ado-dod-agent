param(
    [string]$ImageName = "dod-agent:phase10e",
    [string]$Dockerfile = "Dockerfile"
)

$ErrorActionPreference = "Stop"

docker build -f $Dockerfile -t $ImageName .
docker run --rm $ImageName python scripts/smoke_container_readiness.py
docker run --rm $ImageName python scripts/smoke_runtime_config.py --mode container
