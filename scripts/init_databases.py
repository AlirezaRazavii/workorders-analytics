# Create source and dwh databases, then apply their schemas
import psycopg2
from sqlalchemy import create_engine, text

import sql_scripts
from config import (POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER,
                    POSTGRES_PASSWORD, SOURCE_DB, DWH_DB,
                    source_url, dwh_url)


def ensure_database(name):
    # CREATE DATABASE cannot run inside a transaction,
    # so we connect to the default postgres db with autocommit
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname="postgres",
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
            )
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(f'CREATE DATABASE "{name}"')
    finally:
        conn.close()
    return not exists


def apply_schema(engine, statements):
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def main():
    for name in (SOURCE_DB, DWH_DB):
        created = ensure_database(name)
        print(f"database {name}: {'created' if created else 'already exists'}")

    engine = create_engine(source_url())
    apply_schema(engine, sql_scripts.SOURCE_SCHEMA)
    print(f"schema applied on {SOURCE_DB}")

    engine = create_engine(dwh_url())
    apply_schema(engine, sql_scripts.DWH_SCHEMA)
    print(f"schema applied on {DWH_DB}")


if __name__ == "__main__":
    main()