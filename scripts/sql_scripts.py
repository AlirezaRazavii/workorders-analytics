# Read sql files and split them into separate statements
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def read_statements(filename):
    path = SQL_DIR / filename
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("--"):
            lines.append(line)
    statements = "\n".join(lines).split(";")
    return [s.strip() for s in statements if s.strip()]


SOURCE_SCHEMA = read_statements("01_source_schema.sql")
DWH_SCHEMA = read_statements("02_dwh_schema.sql")