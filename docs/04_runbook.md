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

## عیب‌یابی

- خطای اتصال به دیتابیس: سرویس PostgreSQL در حال اجراست؟ مقدارهای .env درست است؟
- خطای bind روی پورت: پروسه‌ی قبلی uvicorn هنوز زنده است؛ با netstat پیدا و
  متوقف کنید، یا پورت دیگری بدهید و مقدار API در frontend/app.js را هماهنگ کنید
- پورت 5432 اشغال: نمونه‌ی لوکال PostgreSQL در حال اجراست؛ برای داکر از
  نگاشت 5433 استفاده می‌شود
- در pgAdmin برای کوئری زدن، Query Tool باید از روی همان دیتابیسی باز شود که
  مورد نظر است (تب هر دیتابیس جدا است)