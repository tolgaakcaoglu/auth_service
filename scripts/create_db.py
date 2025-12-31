import os
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv


def _build_admin_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError("Only postgres URLs are supported")

    admin_db = os.getenv("POSTGRES_ADMIN_DB", "postgres")
    return parsed._replace(path=f"/{admin_db}").geturl()


def _get_target_db(database_url: str) -> str:
    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/")
    if not db_name:
        raise ValueError("DATABASE_URL must include a database name")
    return db_name


def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is not set")

    admin_url = _build_admin_url(database_url)
    target_db = _get_target_db(database_url)

    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
            exists = cur.fetchone() is not None
            if exists:
                print(f"Database already exists: {target_db}")
                return
            cur.execute(f'CREATE DATABASE "{target_db}"')
            print(f"Database created: {target_db}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
