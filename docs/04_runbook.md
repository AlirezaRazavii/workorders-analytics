# راهنمای اجرا

## پیش‌نیازها

- Python 3.12+
- PostgreSQL لوکال یا Docker
- فایل .env در ریشه پروژه

## اجرای لوکال

اول محیط را آماده کنید:

    python -m venv venv
    venv\Scripts\activate        # لینوکس: source venv/bin/activate
    pip install -r requirements.txt

بعد فایل .env را بسازید و پسورد دیتابیس را داخلش بگذارید:

    copy .env.example .env       # لینوکس: cp .env.example .env

این گام را حتما قبل از ادامه انجام دهید، وگرنه خطای اتصال دیتابیس می‌گیرید.

ساخت دیتابیس‌ها و لود داده:

    python scripts\init_databases.py
    python scripts\load_excel_to_source.py
    python scripts\etl_source_to_dwh.py

اجرای API:

    uvicorn app.main:app --port 8080

داشبورد در پنجره جدا:

    cd frontend
    python -m http.server 5500

آدرس داشبورد http://127.0.0.1:5500 است.

## تست‌ها

    pytest

دو نکته: PostgreSQL باید در حال اجرا باشد و داده باید لود شده باشد. یعنی
اگر دیتابیس تازه ساخته‌اید، اول سه اسکریپت بالا را اجرا کنید بعد pytest،
وگرنه تست‌های API خطای اتصال یا 404 می‌گیرند.

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

دستور اول فقط کانتینرها را متوقف می‌کند و داده‌ها در volume می‌مانند.
دستور دوم داده‌ها را هم پاک می‌کند.
