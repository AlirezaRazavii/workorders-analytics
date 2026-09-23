# ETL service: build the star schema in workorders_dwh
# from the normalized tables in workorders_source.
#
#   extract   -> read joined records from the source db
#   transform -> build dimension rows, map natural keys to surrogate keys
#   load      -> upsert dimensions, full reload of the fact table
#   validate  -> compare source and dwh counts and totals
#
# Every run is recorded in etl_run_log.
#
# Run from the project root:
#   python scripts\etl_source_to_dwh.py

import sys
from datetime import datetime

from sqlalchemy import create_engine, text

from config import source_url, dwh_url

JALALI_MONTHS = {
    1: "فروردین", 2: "اردیبهشت", 3: "خرداد",
    4: "تیر", 5: "مرداد", 6: "شهریور",
    7: "مهر", 8: "آبان", 9: "آذر",
    10: "دی", 11: "بهمن", 12: "اسفند",
}

SOURCE_NAME = "2016.xlsx"


# ---------- run log ----------

def start_run(engine):
    with engine.begin() as conn:
        return conn.execute(text(
            "INSERT INTO etl_run_log (started_at, run_status) "
            "VALUES (:ts, 'running') RETURNING run_id"
        ), {"ts": datetime.now()}).scalar()


def finish_run(engine, run_id, status, extracted, loaded,
               checks_total, checks_failed, details):
    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE etl_run_log SET "
            "finished_at = :ts, run_status = :status, "
            "rows_extracted = :extracted, rows_loaded = :loaded, "
            "checks_total = :checks_total, checks_failed = :checks_failed, "
            "details = :details "
            "WHERE run_id = :run_id"
        ), {
            "ts": datetime.now(), "status": status,
            "extracted": extracted, "loaded": loaded,
            "checks_total": checks_total, "checks_failed": checks_failed,
            "details": details, "run_id": run_id,
        })


# ---------- extract ----------

def extract():
    engine = create_engine(source_url())
    query = text(
        "SELECT r.region_code, r.region_name, "
        "o.jalali_year, o.jalali_month, "
        "c.category_name, c.category_order, "
        "s.status_name, s.status_order, o.order_count "
        "FROM open_work_order o "
        "JOIN region r ON r.region_id = o.region_id "
        "JOIN work_category c ON c.category_id = o.category_id "
        "JOIN order_status s ON s.status_id = o.status_id"
    )
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(query).mappings()]


# ---------- transform ----------

def build_dimensions(rows):
    periods = sorted({(r["jalali_year"], r["jalali_month"]) for r in rows})
    cities = sorted({(r["region_code"], r["region_name"]) for r in rows})
    categories = sorted({(r["category_name"], r["category_order"]) for r in rows})
    statuses = sorted({(r["status_name"], r["status_order"]) for r in rows})

    dim_date = [
        {
            "date_id": year * 100 + month,
            "jalali_year": year,
            "jalali_month": month,
            "year_label": str(year),
            "month_name": JALALI_MONTHS[month],
        }
        for year, month in periods
    ]
    dim_city = [
        {"city_code": code, "city_name": name} for code, name in cities
    ]
    dim_category = [
        {"category_name": name, "category_order": order}
        for name, order in categories
    ]
    dim_status = [
        {"status_name": name, "status_order": order}
        for name, order in statuses
    ]
    return dim_date, dim_city, dim_category, dim_status


# ---------- load ----------

def load_dwh(rows):
    dim_date, dim_city, dim_category, dim_status = build_dimensions(rows)
    engine = create_engine(dwh_url())

    with engine.begin() as conn:
        # dimensions are upserted so surrogate keys stay stable,
        # the fact table gets a full reload on every run
        for d in dim_date:
            conn.execute(text(
                "INSERT INTO dim_date (date_id, jalali_year, jalali_month, "
                "year_label, month_name) "
                "VALUES (:date_id, :jalali_year, :jalali_month, "
                ":year_label, :month_name) "
                "ON CONFLICT (date_id) DO UPDATE SET "
                "year_label = EXCLUDED.year_label, "
                "month_name = EXCLUDED.month_name"
            ), d)

        for c in dim_city:
            conn.execute(text(
                "INSERT INTO dim_city (city_code, city_name) "
                "VALUES (:city_code, :city_name) "
                "ON CONFLICT (city_code) DO UPDATE "
                "SET city_name = EXCLUDED.city_name"
            ), c)

        for c in dim_category:
            conn.execute(text(
                "INSERT INTO dim_category (category_name, category_order) "
                "VALUES (:category_name, :category_order) "
                "ON CONFLICT (category_name) DO UPDATE "
                "SET category_order = EXCLUDED.category_order"
            ), c)

        for s in dim_status:
            conn.execute(text(
                "INSERT INTO dim_status (status_name, status_order) "
                "VALUES (:status_name, :status_order) "
                "ON CONFLICT (status_name) DO UPDATE "
                "SET status_order = EXCLUDED.status_order"
            ), s)

        # natural key -> surrogate key maps for the fact insert
        date_keys = {(y, m): did for did, y, m in conn.execute(text(
            "SELECT date_id, jalali_year, jalali_month FROM dim_date"))}
        city_keys = {code: cid for code, cid in conn.execute(text(
            "SELECT city_code, city_id FROM dim_city"))}
        category_keys = {name: cid for name, cid in conn.execute(text(
            "SELECT category_name, category_id FROM dim_category"))}
        status_keys = {name: sid for name, sid in conn.execute(text(
            "SELECT status_name, status_id FROM dim_status"))}

        conn.execute(
            text("TRUNCATE TABLE fact_open_work_orders RESTART IDENTITY"))

        facts = [
            {
                "date_id": date_keys[(r["jalali_year"], r["jalali_month"])],
                "city_id": city_keys[r["region_code"]],
                "category_id": category_keys[r["category_name"]],
                "status_id": status_keys[r["status_name"]],
                "open_count": r["order_count"],
                "source_name": SOURCE_NAME,
            }
            for r in rows
        ]
        conn.execute(text(
            "INSERT INTO fact_open_work_orders "
            "(date_id, city_id, category_id, status_id, open_count, source_name) "
            "VALUES (:date_id, :city_id, :category_id, :status_id, "
            ":open_count, :source_name)"
        ), facts)

    return {
        "dates": len(dim_date),
        "cities": len(dim_city),
        "categories": len(dim_category),
        "statuses": len(dim_status),
        "facts": len(facts),
    }


# ---------- validate ----------

def validate():
    src = create_engine(source_url())
    dwh = create_engine(dwh_url())
    issues = []
    checks = 0

    with src.connect() as c1, dwh.connect() as c2:
        src_count = c1.execute(
            text("SELECT COUNT(*) FROM open_work_order")).scalar()
        fct_count = c2.execute(
            text("SELECT COUNT(*) FROM fact_open_work_orders")).scalar()
        src_sum = c1.execute(
            text("SELECT COALESCE(SUM(order_count), 0) FROM open_work_order")).scalar()
        fct_sum = c2.execute(
            text("SELECT COALESCE(SUM(open_count), 0) FROM fact_open_work_orders")).scalar()

        checks += 1
        if src_count != fct_count:
            issues.append(f"row count: source={src_count} dwh={fct_count}")
        checks += 1
        if src_sum != fct_sum:
            issues.append(f"total sum: source={src_sum} dwh={fct_sum}")

        # per month totals must match
        src_months = {r[0]: r[1] for r in c1.execute(text(
            "SELECT jalali_year * 100 + jalali_month, SUM(order_count) "
            "FROM open_work_order GROUP BY 1"))}
        fct_months = {r[0]: r[1] for r in c2.execute(text(
            "SELECT date_id, SUM(open_count) "
            "FROM fact_open_work_orders GROUP BY 1"))}
        for period in src_months:
            checks += 1
            if src_months.get(period) != fct_months.get(period):
                issues.append(
                    f"month {period}: source={src_months.get(period)} "
                    f"dwh={fct_months.get(period)}")

        # dimension sizes must match the distinct source values
        pairs = [
            ("SELECT COUNT(DISTINCT (jalali_year, jalali_month)) "
             "FROM open_work_order",
             "SELECT COUNT(*) FROM dim_date"),
            ("SELECT COUNT(DISTINCT region_id) FROM open_work_order",
             "SELECT COUNT(*) FROM dim_city"),
            ("SELECT COUNT(DISTINCT category_id) FROM open_work_order",
             "SELECT COUNT(*) FROM dim_category"),
            ("SELECT COUNT(DISTINCT status_id) FROM open_work_order",
             "SELECT COUNT(*) FROM dim_status"),
        ]
        for src_q, dwh_q in pairs:
            checks += 1
            a = c1.execute(text(src_q)).scalar()
            b = c2.execute(text(dwh_q)).scalar()
            if a != b:
                issues.append(f"dimension size: source={a} dwh={b}")

    return checks, issues


def main():
    dwh = create_engine(dwh_url())
    run_id = start_run(dwh)

    try:
        rows = extract()
        stats = load_dwh(rows)
        checks, issues = validate()

        status = "success" if not issues else "failed"
        finish_run(dwh, run_id, status, len(rows), stats["facts"],
                   checks, len(issues), "; ".join(issues) or None)

        print(f"extracted  : {len(rows)} rows")
        print(f"dimensions : {stats['dates']} dates, {stats['cities']} cities, "
              f"{stats['categories']} categories, {stats['statuses']} statuses")
        print(f"facts      : {stats['facts']} rows")
        print(f"checks     : {checks}, failed: {len(issues)}")
        print(f"run log    : run_id={run_id} status={status}")

        if issues:
            for msg in issues:
                print(f"  - {msg}")
            sys.exit(1)

    except Exception as exc:
        finish_run(dwh, run_id, "failed", None, None, None, None, str(exc))
        raise


if __name__ == "__main__":
    main()