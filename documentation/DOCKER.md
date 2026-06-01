# Docker Setup

This repo can run the FastAPI app and PostgreSQL together with Docker Compose.

## Local Run

1. Create a local environment file:

   ```sh
   cp .env.example .env
   ```

2. Start the stack:

   ```sh
   docker compose up --build
   ```

3. Open the API docs:

   ```text
   http://localhost:5003/docs
   ```

4. Stop the stack:

   ```sh
   docker compose down
   ```

## Services

- `api`: FastAPI app running `uvicorn main:app` on container port `5003`.
- `postgres`: PostgreSQL 17 on container port `5432`, mapped to `localhost:5435` by default.

## Image Design

The API image uses a multi-stage Dockerfile:

- `builder`: creates a Python virtual environment and installs dependencies.
- `runtime`: copies only the virtual environment, app source, Alembic files, and entrypoint.

The runtime container runs as a non-root user and includes an HTTP healthcheck for
`/health/ping`.

## Environment

For Docker Compose, the application connects to Postgres through the Compose service name:

```env
DB_URL=postgresql+asyncpg://ed:123123@postgres:5432/ww-db
```

For running the API directly on your machine while Postgres is in Docker, use localhost:

```env
DB_URL=postgresql+asyncpg://ed:123123@localhost:5435/ww-db
```

## Migrations

The API container runs `alembic upgrade head` on startup when `RUN_MIGRATIONS=true`.
That is enabled by default for local Compose.

Run migration commands manually with:

```sh
docker compose run --rm api alembic current
docker compose run --rm api alembic upgrade head
```

For AWS deployments, keep the same image but decide whether migrations run during
app startup, as a one-off task, or in a deployment pipeline by setting
`RUN_MIGRATIONS`.
