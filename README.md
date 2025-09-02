# WealthWing Backend (FastAPI + SQLAlchemy, Async)

FastAPI backend for **WealthWing** — personal finance & docs.  
Async stack with PostgreSQL (`asyncpg`), SQLAlchemy 2.0, Alembic, and Uvicorn. Optional AWS Cognito/S3 hooks.

## ✨ Features

- Async PostgreSQL via `asyncpg`
- SQLAlchemy 2.0 + Alembic migrations
- OpenAPI docs at `/docs` and `/redoc`
- Health & DB connectivity endpoints
- Clean module layout (routers/schemas/services)

## Quick Start (Docker Compose)

1. **Clone the repository:**
   ```sh
   git clone <your-repo-url>
   cd wealth-wing-data
   ```

2. **Copy and edit the `.env` file:**
   - Set your secrets and database URL as needed. Example:
     ```env
     SQLALCHEMY_DATABASE_URL=postgresql+asyncpg://amin:123123@postgres:5432/ww-db
     ```

3. **Start the backend and database:**
   ```sh
   docker-compose up --build
   ```
   - The API will be available at [http://localhost:5003/docs](http://localhost:5003/docs)
   - The database will be available on port 5434 (for local tools like DBeaver)

4. **Stop the services:**
   ```sh
   docker-compose down
   ```

---

## Local Development (without Docker)

1. **Create and activate a virtual environment:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```sh
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL locally**
   - See [documentation/DOCKER.md](documentation/DOCKER.md) for details.
   - Example connection string for local dev:
     ```env
     SQLALCHEMY_DATABASE_URL=postgresql+asyncpg://admin:123123@localhost:5434/ww-db
     ```

4. **Run database migrations:**
   ```sh
   alembic upgrade head
   ```

5. **Start the server:**
   ```sh
   uvicorn src.main:api --reload --port 5003
   ```
   - Visit [http://localhost:5003/docs](http://localhost:5003/docs) for the API docs.

---

## Database

- The backend uses PostgreSQL. You can run it via Docker Compose or install it locally.
- Database migrations are managed with Alembic. See [documentation/ALEMBIC.md](documentation/ALEMBIC.md) for migration commands.

---

## Health Check

- `GET /ping` — Returns `{ "message": "healthy" }` if the API is running.
- `GET /test_db_connection` — Checks DB connectivity.

---

## Notes

- For production, set strong credentials and review all environment variables.
- Remove any sensitive keys from `.env` before sharing or deploying publicly.
- For async support, the backend uses `asyncpg`.


