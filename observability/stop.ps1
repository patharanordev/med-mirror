docker compose --project-name ecosystem-observability -f .\docker-compose.yml down -v --remove-orphans;
docker rmi -f $(docker images -f 'dangling=true' -q);