# More.Tech 2022 Datacats Backend

## It (somewhat) works! I guess

## Quick start (Docker)

Write your `.env` file to `/` (example: `/env_example`).

Start services listed in `/docker-compose.yml`: `[sudo] docker compose up -d`.

Audit logs with `docker compose logs [-f] [service-name]`.

## Quick start (without Docker)

Start all required services (PostgreSQL, Selenium) and write your `.env` file to `/src` (example: `/env_example`).

Run `/setup/no-docker.sh` from this repository's root (`./setup/no-docker.sh`)
If you run into a permission error, execute `chmod u+x ./setup/no-docker.sh`

Install all Python 3 dependencies listed in `/src/requirements.txt`.

Start the server using `uvicorn api:app` (or `uvicorn api:app --reload` if testing).
