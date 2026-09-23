from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection, text

from .. import schemas
from ..database import get_conn

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health(conn: Connection = Depends(get_conn)):
    conn.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/periods", response_model=list[schemas.Period])
def periods(conn: Connection = Depends(get_conn)):
    rows = conn.execute(text(
        "SELECT date_id, jalali_year, jalali_month, year_label, month_name "
        "FROM dim_date ORDER BY date_id"
    ))
    return [dict(r) for r in rows.mappings()]


@router.get("/cities", response_model=list[schemas.CityValue])
def cities(conn: Connection = Depends(get_conn)):
    rows = conn.execute(
        text("SELECT city_code, city_name FROM dim_city ORDER BY city_code"))
    return [{"city_code": r[0], "city_name": r[1], "value": 0} for r in rows]


@router.get("/etl-status", response_model=schemas.EtlRun)
def etl_status(conn: Connection = Depends(get_conn)):
    row = conn.execute(text(
        "SELECT run_id, started_at, finished_at, run_status, "
        "rows_extracted, rows_loaded, checks_total, checks_failed "
        "FROM etl_run_log ORDER BY run_id DESC LIMIT 1"
    )).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="no etl runs recorded")
    return dict(row)