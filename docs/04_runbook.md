# راهنمای اجرا

## پیش‌نیازها

- Python 3.12+
- PostgreSQL (لوکال) یا Docker
- فایل .env در ریشه (از .env.example کپی و POSTGRES_PASSWORD تنظیم شود)

## اجرای لوکال

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    python scripts\init_databases.py
    python scripts\load_excel_to_source.py
    python scripts\etl_source_to_dwh.py
    uvicorn app.main:app --port 8080

داشبورد (پنجره جدا):

    cd frontend
    python -m http.server 5500

آدرس داشبورد: http://127.0.0.1:5500

## تست‌ها

    pytest

تست‌های API به دیتابیس dwh وصل می‌شوند؛ PostgreSQL باید در حال اجرا باشد.

## اجرا با Docker

    docker compose up -d --build
    docker compose exec api python scripts/init_databases.py
    docker compose exec api python scripts/load_excel_to_source.py
    docker compose exec api python scripts/etl_source_to_dwh.py

- API: http://127.0.0.1:8080/docs
- دیتابیس: پورت میزبان 5433
- داشبورد مثل حالت لوکال با http.server سرو می‌شود و به همان پورت API وصل است

پایان کار:

    docker compose down
    docker compose down -v

دستور اول فقط توقف می‌کند (داده‌ها در volume می‌مانند)، دستور دوم داده‌ها را هم حذف می‌کند.
