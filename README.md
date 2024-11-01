## WelthWing

## Initialize venv

python3 -m venv venv
source ./venv/bin/activate

deactivate (deactivate venv)

## install dependencies
- pip install -r requirements.txt

***PSQL***
- for psql `psycopg2-binary` is required

***server start***
uvicorn main:app --reload

***ALEMBIC***

- example: `alembic revision -m "Create store table"`

- Apply the Migration: `alembic upgrade head`
- `alembic history`: This shows all the migrations in chronological order. 
