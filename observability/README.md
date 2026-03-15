# Observability

I using Langfuse for observe:

- Tracing
    - By session ID
    - By user ID
- Metrics
- Evals
- User/System prompt
- Chat history

Please refer to [Langfuse](https://langfuse.com/) for more information.

## Usage

Please create container network name `commonnet` then start the containers.

```bash
docker network create commonnet
docker compose --project-name ecosystem-observability -f .\docker-compose.yml down -v --remove-orphans;
docker rmi -f $(docker images -f 'dangling=true' -q);
docker compose --project-name ecosystem-observability -f .\docker-compose.yml up --build -d;
```

Or just run the script `start.ps1` for winOS.