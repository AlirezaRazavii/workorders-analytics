# Work Orders Analytics — داشبورد تحلیلی دستورکارهای زخمی

پروژه‌ی تحلیل داده، انتقال داده (ETL) و داشبورد تحلیلی برای گزارش
«وضعیت دستور کارهای زخمی انتقالی از سال‌های گذشته» (فایل data/2016.xlsx).

بخش‌های پروژه:

1. تحلیل داده خام و مستندسازی مشکلات کیفیت داده
2. دیتابیس PostgreSQL نرمال‌شده (3NF) به‌عنوان مبدا
3. دیتابیس PostgreSQL با اسکیمای ستاره‌ای (Star Schema) به‌عنوان مقصد
4. سرویس ETL با اعتبارسنجی چندلایه و لاگ اجرا
5. API فقط‌خواندنی با FastAPI و داشبورد تحلیلی

## معماری

    data/2016.xlsx
        |  scripts/load_excel_to_source.py  (پارس + اعتبارسنجی + بارگذاری)
        v
    PostgreSQL  workorders_source   (مدل نرمال 3NF)
        |  scripts/etl_source_to_dwh.py  (سرویس ETL + لاگ اجرا)
        v
    PostgreSQL  workorders_dwh      (اسکیمای ستاره‌ای)
        |  FastAPI  (فقط SELECT)
        v
    frontend/  (داشبورد: HTML/CSS/JS + Chart.js)

نمونه اعداد پروژه: ۱۶ شهر، ۷ دسته دستورکار، ۵ وضعیت، ۳ ماه (مهر تا آذر ۱۴۰۱)،
۱۵۳۶ رکورد در جدول مشاهدات و ۴۳۲ چک اعتبارسنجی روی داده‌ی خام.

## اجرا با Docker

    docker compose up -d --build
    docker compose exec api python scripts/init_databases.py
    docker compose exec api python scripts/load_excel_to_source.py
    docker compose exec api python scripts/etl_source_to_dwh.py

- API: http://127.0.0.1:8080/docs
- PostgreSQL روی پورت میزبان 5433 (تا با نمونه‌ی لوکال تداخل نکند)

## اجرای لوکال

پیش‌نیاز: Python 3.12+ و PostgreSQL در حال اجرا

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env
    python scripts\init_databases.py
    python scripts\load_excel_to_source.py
    python scripts\etl_source_to_dwh.py
    uvicorn app.main:app --port 8080

مقدار POSTGRES_PASSWORD در فایل .env باید تنظیم شود.

برای داشبورد، در پنجره‌ای جدا:

    cd frontend
    python -m http.server 5500

سپس http://127.0.0.1:5500

## API

| متد | مسیر | خروجی |
|-----|------|-------|
| GET | /api/health | سلامت سرویس |
| GET | /api/periods | لیست ماه‌ها |
| GET | /api/cities | لیست شهرها |
| GET | /api/kpis?date_id= | شاخص‌های ماه: کل، تغییر ماهانه، بزرگ‌ترین دسته و شهر |
| GET | /api/trend | روند کل دستورکارهای باز |
| GET | /api/by-category?date_id= | سهم دسته‌ها با درصد |
| GET | /api/by-status?date_id= | سهم وضعیت‌ها با درصد |
| GET | /api/by-city?date_id= | رتبه‌بندی شهرها |
| GET | /api/city-trend?city_code= | روند یک شهر |
| GET | /api/matrix?date_id= | ماتریس شهر × دسته |
| GET | /api/city-status?date_id= | ماتریس شهر × وضعیت |
| GET | /api/city-detail?city_code=&date_id= | تفکیک دسته × وضعیت برای یک شهر |
| GET | /api/etl-status | آخرین اجرای ETL |

پارامتر date_id اختیاری است (قالب YYYYMM مثل 140107)؛ بدون آن آخرین ماه در نظر گرفته می‌شود.

## تست

    pytest

۱۷ تست: تست‌های قراردادی API و تست‌های واحد پارسر اکسل.

## ساختار پروژه

    app/          سرویس API (FastAPI)
      routers/    اندپوینت‌ها در دو ماژول meta و analytics
    scripts/      اسکریپت‌های راه‌اندازی دیتابیس و ETL
    sql/          اسکیمای مبدا و مقصد
    data/         فایل اکسل خام
    frontend/     داشبورد
    tests/        تست‌های pytest
    docs/         مستندات

## مستندات

- [تحلیل داده‌های خام](docs/01_data_analysis.md)
- [معماری و مدل داده](docs/02_architecture.md)
- [طراحی سرویس ETL](docs/03_etl.md)
- [راهنمای اجرا](docs/04_runbook.md)