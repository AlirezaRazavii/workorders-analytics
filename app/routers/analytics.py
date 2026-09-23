from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection, text

from .. import schemas
from ..database import get_conn

router = APIRouter(prefix="/api", tags=["analytics"])


def resolve_date_id(conn: Connection, date_id: int | None) -> int:
    # no date_id given -> fall back to the latest loaded month
    if date_id is None:
        value = conn.execute(text("SELECT MAX(date_id) FROM dim_date")).scalar()
        if value is None:
            raise HTTPException(status_code=503, detail="no data loaded yet")
        return value
    exists = conn.execute(
        text("SELECT 1 FROM dim_date WHERE date_id = :d"), {"d": date_id}
    ).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail=f"unknown date_id: {date_id}")
    return date_id


@router.get("/kpis", response_model=schemas.Kpis)
def kpis(conn: Connection = Depends(get_conn), date_id: int | None = None):
    d = resolve_date_id(conn, date_id)

    row = conn.execute(text(
        "SELECT d.year_label, d.month_name, "
        "COALESCE(SUM(f.open_count), 0) AS total_open, "
        "COUNT(DISTINCT f.city_id) AS active_cities "
        "FROM dim_date d "
        "LEFT JOIN fact_open_work_orders f ON f.date_id = d.date_id "
        "WHERE d.date_id = :d "
        "GROUP BY d.year_label, d.month_name"
    ), {"d": d}).mappings().first()

    prev_id = conn.execute(text(
        "SELECT MAX(date_id) FROM dim_date WHERE date_id < :d"
    ), {"d": d}).scalar()
    prev_total = None
    if prev_id is not None:
        prev_total = conn.execute(text(
            "SELECT COALESCE(SUM(open_count), 0) "
            "FROM fact_open_work_orders WHERE date_id = :d"
        ), {"d": prev_id}).scalar()

    top_category = conn.execute(text(
        "SELECT c.category_name AS label, SUM(f.open_count) AS value "
        "FROM fact_open_work_orders f "
        "JOIN dim_category c ON c.category_id = f.category_id "
        "WHERE f.date_id = :d "
        "GROUP BY c.category_name "
        "ORDER BY value DESC LIMIT 1"
    ), {"d": d}).mappings().first()

    top_city = conn.execute(text(
        "SELECT ci.city_code, ci.city_name, SUM(f.open_count) AS value "
        "FROM fact_open_work_orders f "
        "JOIN dim_city ci ON ci.city_id = f.city_id "
        "WHERE f.date_id = :d "
        "GROUP BY ci.city_code, ci.city_name "
        "ORDER BY value DESC LIMIT 1"
    ), {"d": d}).mappings().first()

    total = row["total_open"]
    mom_change = None
    mom_change_pct = None
    if prev_total is not None:
        mom_change = total - prev_total
        if prev_total > 0:
            mom_change_pct = round(100.0 * mom_change / prev_total, 1)

    return {
        "date_id": d,
        "year_label": row["year_label"],
        "month_name": row["month_name"],
        "total_open": total,
        "prev_total_open": prev_total,
        "mom_change": mom_change,
        "mom_change_pct": mom_change_pct,
        "active_cities": row["active_cities"],
        "top_category": dict(top_category) if top_category else None,
        "top_city": dict(top_city) if top_city else None,
    }


@router.get("/trend", response_model=list[schemas.TrendPoint])
def trend(conn: Connection = Depends(get_conn)):
    rows = conn.execute(text(
        "SELECT d.date_id, d.year_label, d.month_name, "
        "COALESCE(SUM(f.open_count), 0) AS value "
        "FROM dim_date d "
        "LEFT JOIN fact_open_work_orders f ON f.date_id = d.date_id "
        "GROUP BY d.date_id, d.year_label, d.month_name "
        "ORDER BY d.date_id"
    ))
    return [dict(r) for r in rows.mappings()]


@router.get("/by-category", response_model=list[schemas.Slice])
def by_category(conn: Connection = Depends(get_conn), date_id: int | None = None):
    d = resolve_date_id(conn, date_id)
    rows = conn.execute(text(
        "SELECT c.category_name AS label, SUM(f.open_count) AS value, "
        "ROUND(100.0 * SUM(f.open_count) / "
        "NULLIF(SUM(SUM(f.open_count)) OVER (), 0), 1) AS share "
        "FROM fact_open_work_orders f "
        "JOIN dim_category c ON c.category_id = f.category_id "
        "WHERE f.date_id = :d "
        "GROUP BY c.category_name "
        "ORDER BY value DESC"
    ), {"d": d})
    return [dict(r) for r in rows.mappings()]


@router.get("/by-status", response_model=list[schemas.Slice])
def by_status(conn: Connection = Depends(get_conn), date_id: int | None = None):
    d = resolve_date_id(conn, date_id)
    rows = conn.execute(text(
        "SELECT s.status_name AS label, SUM(f.open_count) AS value, "
        "ROUND(100.0 * SUM(f.open_count) / "
        "NULLIF(SUM(SUM(f.open_count)) OVER (), 0), 1) AS share "
        "FROM fact_open_work_orders f "
        "JOIN dim_status s ON s.status_id = f.status_id "
        "WHERE f.date_id = :d "
        "GROUP BY s.status_name, s.status_order "
        "ORDER BY s.status_order"
    ), {"d": d})
    return [dict(r) for r in rows.mappings()]


@router.get("/by-city", response_model=list[schemas.CityValue])
def by_city(conn: Connection = Depends(get_conn), date_id: int | None = None):
    d = resolve_date_id(conn, date_id)
    rows = conn.execute(text(
        "SELECT ci.city_code, ci.city_name, "
        "COALESCE(SUM(f.open_count), 0) AS value "
        "FROM dim_city ci "
        "LEFT JOIN fact_open_work_orders f "
        "ON f.city_id = ci.city_id AND f.date_id = :d "
        "GROUP BY ci.city_code, ci.city_name "
        "ORDER BY value DESC"
    ), {"d": d})
    return [dict(r) for r in rows.mappings()]


@router.get("/city-trend", response_model=list[schemas.TrendPoint])
def city_trend(
    city_code: int = Query(...),
    conn: Connection = Depends(get_conn),
):
    city_id = conn.execute(text(
        "SELECT city_id FROM dim_city WHERE city_code = :code"
    ), {"code": city_code}).scalar()
    if city_id is None:
        raise HTTPException(status_code=404, detail=f"unknown city_code: {city_code}")

    rows = conn.execute(text(
        "SELECT d.date_id, d.year_label, d.month_name, "
        "COALESCE(SUM(f.open_count), 0) AS value "
        "FROM dim_date d "
        "LEFT JOIN fact_open_work_orders f "
        "ON f.date_id = d.date_id AND f.city_id = :city_id "
        "GROUP BY d.date_id, d.year_label, d.month_name "
        "ORDER BY d.date_id"
    ), {"city_id": city_id})
    return [dict(r) for r in rows.mappings()]


def _matrix_rows(conn: Connection, query: str, params: dict):
    rows = {}
    for r in conn.execute(text(query), params).mappings():
        key = (r["city_code"], r["city_name"])
        rows.setdefault(key, {})[r["col_name"]] = r["value"]
    return [
        {
            "city_code": code,
            "city_name": name,
            "values": values,
            "total": sum(values.values()),
        }
        for (code, name), values in rows.items()
    ]


@router.get("/matrix", response_model=list[schemas.MatrixRow])
def matrix(conn: Connection = Depends(get_conn), date_id: int | None = None):
    d = resolve_date_id(conn, date_id)
    query = (
        "SELECT ci.city_code, ci.city_name, ca.category_name AS col_name, "
        "COALESCE(SUM(f.open_count), 0) AS value "
        "FROM dim_city ci "
        "CROSS JOIN dim_category ca "
        "LEFT JOIN fact_open_work_orders f "
        "ON f.city_id = ci.city_id AND f.category_id = ca.category_id "
        "AND f.date_id = :d "
        "GROUP BY ci.city_code, ci.city_name, ca.category_name, ca.category_order "
        "ORDER BY ci.city_code, ca.category_order"
    )
    return _matrix_rows(conn, query, {"d": d})


@router.get("/city-status", response_model=list[schemas.MatrixRow])
def city_status(conn: Connection = Depends(get_conn), date_id: int | None = None):
    d = resolve_date_id(conn, date_id)
    query = (
        "SELECT ci.city_code, ci.city_name, s.status_name AS col_name, "
        "COALESCE(SUM(f.open_count), 0) AS value "
        "FROM dim_city ci "
        "CROSS JOIN dim_status s "
        "LEFT JOIN fact_open_work_orders f "
        "ON f.city_id = ci.city_id AND f.status_id = s.status_id "
        "AND f.date_id = :d "
        "GROUP BY ci.city_code, ci.city_name, s.status_name, s.status_order "
        "ORDER BY ci.city_code, s.status_order"
    )
    return _matrix_rows(conn, query, {"d": d})


@router.get("/city-detail", response_model=list[schemas.DetailRow])
def city_detail(
    city_code: int = Query(...),
    conn: Connection = Depends(get_conn),
    date_id: int | None = None,
):
    d = resolve_date_id(conn, date_id)
    city_id = conn.execute(text(
        "SELECT city_id FROM dim_city WHERE city_code = :code"
    ), {"code": city_code}).scalar()
    if city_id is None:
        raise HTTPException(status_code=404, detail=f"unknown city_code: {city_code}")

    query = (
        "SELECT ca.category_name, ca.category_order, s.status_name AS col_name, "
        "COALESCE(SUM(f.open_count), 0) AS value "
        "FROM dim_category ca "
        "CROSS JOIN dim_status s "
        "LEFT JOIN fact_open_work_orders f "
        "ON f.category_id = ca.category_id AND f.status_id = s.status_id "
        "AND f.city_id = :city_id AND f.date_id = :d "
        "GROUP BY ca.category_name, ca.category_order, "
        "s.status_name, s.status_order "
        "ORDER BY ca.category_order, s.status_order"
    )
    rows = {}
    for r in conn.execute(text(query), {"city_id": city_id, "d": d}).mappings():
        key = (r["category_order"], r["category_name"])
        rows.setdefault(key, {})[r["col_name"]] = r["value"]

    return [
        {
            "category_order": order,
            "category_name": name,
            "values": values,
            "total": sum(values.values()),
        }
        for (order, name), values in rows.items()
    ]