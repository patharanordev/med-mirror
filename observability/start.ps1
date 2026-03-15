$NetworkName = "commonnet"

# Verify if the network was successfully created
try {
    docker network create $NetworkName
    Write-Host "Network $NetworkName created successfully."
}
catch {
    Write-Host "Failed to create network $NetworkName. Exiting."
    exit 1
}

docker compose --project-name ecosystem-observability -f .\docker-compose.yml down -v --remove-orphans;
docker rmi -f $(docker images -f 'dangling=true' -q);
docker compose --project-name ecosystem-observability -f .\docker-compose.yml up --build -d;
