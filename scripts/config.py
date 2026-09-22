# DB connection settings, loaded from .env
import os

from dotenv import load_dotenv

load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

SOURCE_DB = "workorders_source"
DWH_DB = "workorders_dwh"


def _url(dbname):
    return (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{dbname}"
    )


def source_url():
    return _url(SOURCE_DB)


def dwh_url():
    return _url(DWH_DB)