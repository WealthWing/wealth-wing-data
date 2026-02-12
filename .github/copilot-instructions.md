# AI Coding Assistant Instructions for WealthWing Backend

This guide helps AI agents quickly become productive in the `wealth-wing-data` codebase.

## Architecture Overview

**WealthWing Backend** is an async FastAPI + SQLAlchemy 2.x service for personal finance management:
- **Database**: PostgreSQL via `asyncpg` with Alembic migrations
- **Request Layer**: FastAPI routers → service layer → database models
- **Key Domains**: Transactions, Accounts, Categories, Projects, Subscriptions, Bank CSV Imports
- **Auth**: Cognito middleware validates JWT tokens; routes depend on `get_current_user` for user context

### Core Data Flow

1. **Router** (thin): Extract params, validate user permissions, delegate to service/utilities
2. **Service/Util** (thick): Business logic, data transformation, database queries
3. **Model** (SQLAlchemy): Define schema + relationships; migrations track changes
4. **Importer Pipeline** (`import_manager.py`): Factory selects CSV importer → parses rows → deduplicates fingerprints → creates transactions

## Critical Patterns

### Async/Await Requirements
All database operations are **async**. Use SQLAlchemy 2.x patterns:
```python
# Correct: await db.execute() + .scalars().first()
result = await db.execute(select(Transaction).where(...))
transaction = result.scalars().first()

# Commit is also async
await db.commit()
```
Don't use blocking ORM calls; router handlers are async functions.

### User Context & Permissions
Every request depends on `get_current_user` (FastAPI Dependency) which returns `UserPool` type containing:
- `sub`: user ID (matches `User.uuid`)
- `organization_id`: org scope for multi-tenant filtering
- Email and roles (used by `has_permission()` checks)

Routes validate permissions via `has_permission(current_user, Perm.READ/WRITE)` before responding.

### Fingerprint-Based Deduplication
Bank importers prevent duplicate imports by generating transaction fingerprints:
```python
# In chase_debit.py
fingerprint = generate_fingerprint(date=date, title=title, amount_cents=amount_cents)
# Query existing fingerprints for account, filter new transactions, insert only unique ones
existing_fps = await db.execute(
    select(Transaction.fingerprint).where(
        Transaction.fingerprint.in_(fingerprints),
        Transaction.account_id == import_job.account_id
    )
)
unique_transactions = [t for t, fp in txns_and_fps if fp not in existing_fps]
```
Keep this pattern when adding new importers; don't break the dedup logic.

### CSV Importer Design
Located in `src/services/bank_importers/`:
- **Base class** (`base.py`): Defines `can_handle_file()` static method + instance methods
- **Subclasses** (`chase_debit.py`, `chase_credit.py`): Implement CSV parsing, type mapping, category/project resolution
- **Helpers** (`src/util/transaction.py`, `src/util/category.py`, `src/util/project.py`): 
  - `get_internal_type(type_, description)` → normalize bank "Type" to internal (expense/income/transfer)
  - `get_amount_cents(amount_str)` → parse amount, convert to cents (int)
  - `get_date_from_row(row)` → parse date, return datetime object
  - `get_category_id_from_row(title, category_name, org_id, db)` → match/create category, return UUID
  - `get_project_id_from_row(title, org_id, db)` → match project by title substring, return UUID (optional)

**Adding a new importer**:
1. Create `src/services/bank_importers/new_bank.py`, inherit `BaseBankImporter`
2. Implement `can_handle_file(file_name, file_type, account_type)` → return True only for your CSV format
3. Implement async `parse_csv_transactions(import_job)` → parse CSV, call helpers, return deduplicated Transaction list
4. Register in `import_manager.py` IMPORTERS list

### Query Building & Filtering
Use `QueryService` (injected as dependency) for consistent org-scoped queries:
```python
# In transaction router
base_stmt = query_service.org_filtered_query(
    model=Transaction,
    current_user=current_user,
    ...additional filters...
)
result = await db.execute(base_stmt)
```
This prevents queries from leaking data across organizations.

### Model Relationships
Key models in `src/model/models.py`:
- **User** ↔ **Organization** (many-to-one); user can belong to one org
- **Transaction** ↔ **Account**, **Category**, **Project** (foreign keys)
- **ImportJob** ↔ **User**, **Account** (tracks batch imports)
- All models have `uuid` primary key + `created_at`/`updated_at` timestamps

## Development Workflow

### Starting the Stack
```bash
# Terminal 1: Database
docker-compose up -d

# Terminal 2: API (auto-reload on file changes)
uvicorn main:app --reload --env-file .env
# or: ./run.sh
```
API docs at [http://localhost:5003/docs](http://localhost:5003/docs)

### Database Changes
Always create migrations for schema changes:
```bash
# 1. Update model in src/model/models.py
# 2. Generate migration
alembic revision --autogenerate -m "Description of change"
# 3. Review migration script (alembic/versions/*.py)
# 4. Apply migration
alembic upgrade head
```
Don't skip migrations; they're auditable and required for deployments.

### Testing Changes Locally
- Verify CSV import: Run importer against sample CSV via `/import` endpoint
- Check dedupe: Import same CSV twice, verify transaction count doesn't double
- Validate category/project mapping: Inspect Transaction.category_id and Transaction.project_id in DB
- If tests exist: Run them and report results in PRs

## File Organization Reference

| Path | Purpose |
|------|---------|
| `src/routers/` | FastAPI route handlers; thin, delegate to services |
| `src/services/` | Business logic, data orchestration, importer factory |
| `src/services/bank_importers/` | CSV parsers, bank-specific row mapping |
| `src/util/` | Reusable helpers (transaction types, category matching, etc.) |
| `src/model/models.py` | SQLAlchemy ORM definitions + relationships |
| `src/schemas/` | Pydantic input/output validation models |
| `src/database/connect.py` | Async session manager, `get_db()` dependency |
| `src/middleware/auth.py` | Cognito JWT validation |
| `alembic/versions/` | Migration scripts (don't edit old ones) |

## Common Gotchas

- **Forget await**: DB calls without `await` hang silently. Always `await db.execute()`, `await db.commit()`.
- **Blocking operations**: Don't call sync CSV parsing in a route without wrapping in `run_in_executor()`.
- **Organization leakage**: Always filter queries by `current_user.organization_id` or use `QueryService`.
- **Fingerprint collisions**: If changing fingerprint generation, old imports may lose dedup protection; coordinate with backend deploys.
- **Schema changes without migrations**: Models and DB get out of sync; migrations are mandatory.

## Key Files to Read First
- `AGENTS.md` – High-level conventions for this repo
- `src/services/import_manager.py` – How CSV import flow selects & orchestrates importers
- `src/model/models.py` (lines 1–150) – Core data model & relationships
- `src/routers/transaction.py` (lines 1–50) – Example of router + service injection pattern
- `src/util/transaction.py`, `src/util/category.py` – Reusable transformation helpers

## Questions Before Implementing

When making changes to importers, queries, or migrations, consider:
1. Does this change break existing fingerprint logic or dedup?
2. Is a new database migration needed?
3. Does this query respect organization boundaries?
4. Are async/await patterns used consistently?

## Always follow AGENTS.md in project root.

Critical rules:
- All DB access must be async
- Use QueryService for org scoping
- Preserve fingerprint dedup
- Require Alembic migrations for schema changes

## Important Notes:
- Wen defining shema models using pydantic always make sure you label at the end if it is Request or Response model. This is important for readability and maintainability of the codebase. For example, if you are defining a schema for creating a transaction, you should name it `TransactionCreateRequest` to indicate that it is a request model. Similarly, if you are defining a schema for returning transaction data, you should name it `TransactionResponse` to indicate that it is a response model. This naming convention helps other developers understand the purpose of each schema at a glance and promotes consistency throughout the codebase.