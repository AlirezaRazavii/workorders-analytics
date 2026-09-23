import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from config import source_url

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_FILE = BASE_DIR / "data" / "2016.xlsx"

# group 3 has a duplicated header in the file (same as the duplicated
# "test 4" title), so its name is set explicitly here
CATEGORY_OVERRIDES = {2: "تعمیرات اساسی"}

# this one is written without a space inside the file
STATUS_FIXES = {"دردست اجرا": "در دست اجرا"}

STATUS_ORDER = [
    "در دست اجرا",
    "تهیه صورت وضعیت",
    "صورت وضعیت نزد مشاور",
    "صورت وضعیت نزد ستاد",
    "صورت وضعیت نزد مالی",
]

GRAND_TOTAL_LABEL = "کل دستورکارهای باز"
MONTHLY_TOTAL_LABEL = "جمع به تفکیک هر واحد"
COMPANY_LABEL = "کل شرکت"

EXPECTED_GROUPS = 8  # 7 categories + 1 grand total group


def normalize(value):
    # trim, collapse inner spaces, arabic yeh/kaf -> persian
    s = str(value).strip().replace("ي", "ی").replace("ك", "ک")
    return " ".join(s.split())


def to_int(value):
    # empty or merged cells read as 0; numbers may arrive as strings
    # with thousand separators (e.g. "1,446") in the aggregate rows
    if pd.isna(value):
        return 0
    if isinstance(value, str):
        value = value.replace(",", "").strip()
        if not value:
            return 0
    return int(float(value))


def parse_groups(raw, status_idx):
    # build the column layout from the status header row: every group
    # ends with a total column and the category name is part of its label
    header = raw.iloc[status_idx]
    total_cols = []
    for col in raw.columns:
        val = header[col]
        if isinstance(val, str):
            label = normalize(val)
            if "مجموع دستورکارهای باز" in label or label == GRAND_TOTAL_LABEL:
                total_cols.append((col, label))

    if len(total_cols) != EXPECTED_GROUPS:
        raise SystemExit(
            f"unexpected header: found {len(total_cols)} groups, "
            f"expected {EXPECTED_GROUPS}"
        )

    groups = []
    first = 4  # columns 0-3 are city, code, year, month
    for idx, (col, label) in enumerate(total_cols):
        if label == GRAND_TOTAL_LABEL:
            name = GRAND_TOTAL_LABEL
        else:
            name = label.replace("مجموع دستورکارهای باز", "").strip()
            name = CATEGORY_OVERRIDES.get(idx, name)
        groups.append({"name": name, "cols": list(range(first, col)), "total": col})
        first = col + 1
    return groups


def parse_rows(raw, status_idx, groups):
    cat_groups = [g for g in groups if g["name"] != GRAND_TOTAL_LABEL]
    grand = groups[-1]
    header = raw.iloc[status_idx]

    records = []
    issues = []
    checks = 0
    monthly_rows = {}  # (year, month) -> monthly aggregate row
    company_rows = {}  # (year, month) -> company aggregate row
    period = None

    for _, row in raw.iloc[status_idx + 1:].iterrows():
        if pd.isna(row[0]):
            continue
        label = normalize(row[0])

        year, month = to_int(row[2]), to_int(row[3])
        if year and month:
            period = (year, month)
        row_period = (year, month) if (year and month) else period

        # aggregate rows are kept aside for validation, not for loading
        if label == MONTHLY_TOTAL_LABEL:
            monthly_rows[row_period] = row
            continue
        if label == COMPANY_LABEL:
            company_rows[row_period] = row
            continue
        if not (year and month):
            continue

        excel_row = int(row.name) + 1  # sheet row number, for traceability
        group_totals = {}

        for g in cat_groups:
            group_sum = 0
            for col in g["cols"]:
                status = normalize(header[col])
                status = STATUS_FIXES.get(status, status)
                count = to_int(row[col])
                group_sum += count
                records.append({
                    "city": label,
                    "city_code": to_int(row[1]),
                    "year": year,
                    "month": month,
                    "category": g["name"],
                    "status": status,
                    "count": count,
                    "excel_row": excel_row,
                })
            group_totals[g["name"]] = group_sum

            # check 1: statuses of a group sum to the group total column
            checks += 1
            if group_sum != to_int(row[g["total"]]):
                issues.append(
                    f"row {excel_row}: group '{g['name']}' "
                    f"sum={group_sum} total={to_int(row[g['total']])}"
                )

        # check 2: sum of all groups equals the grand total column
        checks += 1
        grand_total = to_int(row[grand["total"]])
        if sum(group_totals.values()) != grand_total:
            issues.append(
                f"row {excel_row}: groups sum={sum(group_totals.values())} "
                f"grand={grand_total}"
            )

    return {
        "records": records,
        "issues": issues,
        "checks": checks,
        "monthly_rows": monthly_rows,
        "company_rows": company_rows,
        "cat_groups": cat_groups,
        "grand": grand,
    }


def validate_aggregates(parsed):
    # check 3/4: per month, the sum over the 16 cities must match both
    # aggregate rows of the file. updates checks/issues in place
    by_cat = {}    # (year, month, category) -> count
    by_month = {}  # (year, month) -> count
    for r in parsed["records"]:
        key = (r["year"], r["month"], r["category"])
        by_cat[key] = by_cat.get(key, 0) + r["count"]
        key = (r["year"], r["month"])
        by_month[key] = by_month.get(key, 0) + r["count"]

    def check(year, month, row, col, expected, kind):
        parsed["checks"] += 1
        value = to_int(row[col])
        if value != expected:
            parsed["issues"].append(
                f"{kind} {year}/{month}: expected={expected} file={value}"
            )

    for (year, month), row in parsed["monthly_rows"].items():
        for g in parsed["cat_groups"]:
            expected = by_cat.get((year, month, g["name"]), 0)
            check(year, month, row, g["total"], expected, f"monthly '{g['name']}'")
        check(year, month, row, parsed["grand"]["total"],
              by_month.get((year, month), 0), "monthly grand")

    # in the company row the values sit in merged cells,
    # so they are read from the first column of each group
    for (year, month), row in parsed["company_rows"].items():
        for g in parsed["cat_groups"]:
            expected = by_cat.get((year, month, g["name"]), 0)
            check(year, month, row, g["cols"][0], expected, f"company '{g['name']}'")
        check(year, month, row, parsed["grand"]["cols"][0],
              by_month.get((year, month), 0), "company grand")


def load_to_db(parsed):
    records = parsed["records"]

    unknown = {r["status"] for r in records} - set(STATUS_ORDER)
    if unknown:
        raise SystemExit(f"unknown status labels: {unknown}")

    cities = sorted({(r["city_code"], r["city"]) for r in records})
    categories = [g["name"] for g in parsed["cat_groups"]]

    engine = create_engine(source_url())
    with engine.begin() as conn:
        # observation table is fully reloaded; reference tables are
        # upserted so their ids stay stable across reruns
        conn.execute(text("TRUNCATE TABLE open_work_order RESTART IDENTITY"))

        for code, name in cities:
            conn.execute(text(
                "INSERT INTO region (region_code, region_name) "
                "VALUES (:code, :name) "
                "ON CONFLICT (region_code) DO UPDATE "
                "SET region_name = EXCLUDED.region_name"
            ), {"code": code, "name": name})

        for order, name in enumerate(categories, start=1):
            conn.execute(text(
                "INSERT INTO work_category (category_name, category_order) "
                "VALUES (:name, :order) "
                "ON CONFLICT (category_name) DO UPDATE "
                "SET category_order = EXCLUDED.category_order"
            ), {"name": name, "order": order})

        for order, name in enumerate(STATUS_ORDER, start=1):
            conn.execute(text(
                "INSERT INTO order_status (status_name, status_order) "
                "VALUES (:name, :order) "
                "ON CONFLICT (status_name) DO UPDATE "
                "SET status_order = EXCLUDED.status_order"
            ), {"name": name, "order": order})

        region_map = {
            code: rid for code, rid in
            conn.execute(text("SELECT region_code, region_id FROM region"))
        }
        category_map = {
            name: cid for name, cid in
            conn.execute(text("SELECT category_name, category_id FROM work_category"))
        }
        status_map = {
            name: sid for name, sid in
            conn.execute(text("SELECT status_name, status_id FROM order_status"))
        }

        rows = [
            {
                "region_id": region_map[r["city_code"]],
                "jalali_year": r["year"],
                "jalali_month": r["month"],
                "category_id": category_map[r["category"]],
                "status_id": status_map[r["status"]],
                "order_count": r["count"],
                "source_row": r["excel_row"],
            }
            for r in records
        ]
        conn.execute(text(
            "INSERT INTO open_work_order "
            "(region_id, jalali_year, jalali_month, category_id, status_id, "
            "order_count, source_row) "
            "VALUES (:region_id, :jalali_year, :jalali_month, :category_id, "
            ":status_id, :order_count, :source_row)"
        ), rows)


def main():
    if not EXCEL_FILE.exists():
        raise SystemExit(f"excel file not found: {EXCEL_FILE}")

    print(f"reading {EXCEL_FILE.name}")
    raw = pd.read_excel(EXCEL_FILE, sheet_name=0, header=None)

    # the header row starts with the city column title,
    # the status header row sits right below it
    mask = raw[0].astype(str).str.contains("مدیریت برق شهرستان", regex=False)
    if not mask.any():
        raise SystemExit("header row not found, excel structure changed?")
    status_idx = raw.index[mask][0] + 1

    groups = parse_groups(raw, status_idx)
    parsed = parse_rows(raw, status_idx, groups)
    validate_aggregates(parsed)

    months = sorted({(r["year"], r["month"]) for r in parsed["records"]})
    cities = sorted({r["city"] for r in parsed["records"]})
    print(f"categories : {[g['name'] for g in parsed['cat_groups']]}")
    print(f"periods    : {months}")
    print(f"cities     : {len(cities)}")
    print(f"records    : {len(parsed['records'])}")
    print(f"checks     : {parsed['checks']}, issues: {len(parsed['issues'])}")

    if parsed["issues"]:
        print("data quality issues:")
        for msg in parsed["issues"]:
            print(f"  - {msg}")
        sys.exit(1)

    load_to_db(parsed)
    print(f"loaded {len(parsed['records'])} rows into open_work_order")


if __name__ == "__main__":
    main()