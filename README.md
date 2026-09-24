# Work Orders Analytics — داشبورد دستورکارهای زخمی

این پروژه گزارش اکسلی «وضعیت دستور کارهای زخمی انتقالی از سال‌های گذشته» را
به یک پایپ‌لاین داده و داشبورد تحلیلی تبدیل می‌کند. خلاصه کوتاه پروژه در
[docs/00_summary.md](docs/00_summary.md) آمده است.

مسیر داده به صورت خلاصه:

1. تحلیل فایل خام و مستند مشکلات کیفیت داده
2. دیتابیس PostgreSQL نرمال (3NF) برای نگهداری داده پاک‌شده
3. دیتابیس PostgreSQL با اسکیمای ستاره‌ای برای تحلیل
4. سرویس ETL بین دو دیتابیس با اعتبارسنجی و لاگ اجرا
5. API فقط‌خواندنی با FastAPI و داشبورد فارسی

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

حجم فعلی داده: ۱۶ شهر، ۷ دسته دستورکار، ۵ وضعیت و ۳ ماه (مهر تا آذر ۱۴۰۱)
که ۱۵۳۶ رکورد در جدول مشاهدات می‌شود. قبل از لود، ۴۳۲ چک روی فایل خام اجرا
می‌شود.

## اجرا با Docker

    docker compose up -d --build
    docker compose exec api python scripts/init_databases.py
    docker compose exec api python scripts/load_excel_to_source.py
    docker compose exec api python scripts/etl_source_to_dwh.py

API روی http://127.0.0.1:8080/docs و دیتابیس روی پورت میزبان 5433 بالا
می‌آید (5432 برای نمونه لوکال آزاد می‌ماند). این دستورها در ویندوز و
لینوکس یکسان‌اند.

## اجرای لوکال

پیش‌نیاز: Python 3.12+ و PostgreSQL در حال اجرا.

    python -m venv venv
    venv\Scripts\activate        # لینوکس: source venv/bin/activate
    pip install -r requirements.txt
    copy .env.example .env       # لینوکس: cp .env.example .env

بعد از کپی، POSTGRES_PASSWORD را در فایل .env تنظیم کنید. ادامه:

    python scripts\init_databases.py
    python scripts\load_excel_to_source.py
    python scripts\etl_source_to_dwh.py
    uvicorn app.main:app --port 8080

داشبورد در پنجره جدا:

    cd frontend
    python -m http.server 5500

و آدرس http://127.0.0.1:5500

خطاهای رایج و جزئیات بیشتر در [docs/04_runbook.md](docs/04_runbook.md).

## API

| متد | مسیر | خروجی |
|-----|------|-------|
| GET | /api/health | سلامت سرویس |
| GET | /api/periods | لیست ماه‌ها |
| GET | /api/cities | لیست شهرها |
| GET | /api/kpis | شاخص‌های ماه: کل، تغییر ماهانه، بزرگ‌ترین دسته و شهر |
| GET | /api/trend | روند کل دستورکارهای باز |
| GET | /api/by-category | سهم دسته‌ها با درصد |
| GET | /api/by-status | سهم وضعیت‌ها با درصد |
| GET | /api/by-city | رتبه‌بندی شهرها |
| GET | /api/city-trend | روند یک شهر |
| GET | /api/matrix | ماتریس شهر × دسته |
| GET | /api/city-status | ماتریس شهر × وضعیت |
| GET | /api/city-detail | تفکیک دسته × وضعیت برای یک شهر |
| GET | /api/etl-status | آخرین اجرای ETL |

پارامترهای query:

- date_id اختیاری است. قالب YYYYMM است، مثل 140107. اگر داده نشود آخرین ماه
  در نظر گرفته می‌شود. مقادیر معتبر این دیتاست 140107 و 140108 و 140109 است؛
  لیست کامل همیشه از GET /api/periods قابل دریافت است.
- city_code در city-trend و city-detail اجباری است و همان «کد امور» فایل
  اکسل است، مثل 2001 برای شهر ۹. لیست کدها از GET /api/cities می‌آید.

مقدار نامعتبر برای هر کدام 404 برمی‌گرداند.

## تست

    pytest

۱۷ تست: تست‌های قراردادی API و تست‌های واحد پارسر اکسل. قبل از اجرای تست‌ها
داده باید لود شده باشد (بالا را ببینید).

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

- [خلاصه پروژه](docs/00_summary.md)
- [تحلیل داده‌های خام](docs/01_data_analysis.md)
- [معماری و مدل داده](docs/02_architecture.md)
- [طراحی سرویس ETL](docs/03_etl.md)
- [راهنمای اجرا](docs/04_runbook.md)