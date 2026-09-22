-- DWH schema (workorders_dwh) - star schema
-- one fact table + four dimension tables

DROP TABLE IF EXISTS fact_open_work_orders CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS dim_city CASCADE;
DROP TABLE IF EXISTS dim_category CASCADE;
DROP TABLE IF EXISTS dim_status CASCADE;
DROP TABLE IF EXISTS etl_run_log CASCADE;

-- date dimension, smart key YYYYMM (e.g. 140107)
CREATE TABLE dim_date (
    date_id      INTEGER     PRIMARY KEY,
    jalali_year  SMALLINT    NOT NULL,
    jalali_month SMALLINT    NOT NULL,
    year_label   VARCHAR(10) NOT NULL,
    month_name   VARCHAR(20) NOT NULL,
    UNIQUE (jalali_year, jalali_month)
);

-- city dimension, city_id is surrogate key, city_code is natural key
CREATE TABLE dim_city (
    city_id    SERIAL       PRIMARY KEY,
    city_code  INTEGER      NOT NULL UNIQUE,
    city_name  VARCHAR(100) NOT NULL
);

CREATE TABLE dim_category (
    category_id    SERIAL       PRIMARY KEY,
    category_name  VARCHAR(150) NOT NULL UNIQUE,
    category_order SMALLINT     NOT NULL
);

CREATE TABLE dim_status (
    status_id    SERIAL       PRIMARY KEY,
    status_name  VARCHAR(100) NOT NULL UNIQUE,
    status_order SMALLINT     NOT NULL
);

-- fact table
-- measure is a month-end snapshot, so it is additive across
-- city/category/status but NOT across months
CREATE TABLE fact_open_work_orders (
    fact_id     BIGSERIAL   PRIMARY KEY,
    date_id     INTEGER     NOT NULL REFERENCES dim_date(date_id),
    city_id     INTEGER     NOT NULL REFERENCES dim_city(city_id),
    category_id INTEGER     NOT NULL REFERENCES dim_category(category_id),
    status_id   INTEGER     NOT NULL REFERENCES dim_status(status_id),
    open_count  INTEGER     NOT NULL CHECK (open_count >= 0),
    source_name VARCHAR(50) NOT NULL DEFAULT '2016.xlsx',
    loaded_at   TIMESTAMP   NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact UNIQUE (date_id, city_id, category_id, status_id)
);

CREATE INDEX idx_fact_date     ON fact_open_work_orders (date_id);
CREATE INDEX idx_fact_city     ON fact_open_work_orders (city_id);
CREATE INDEX idx_fact_category ON fact_open_work_orders (category_id);
CREATE INDEX idx_fact_status   ON fact_open_work_orders (status_id);

-- ETL run log for tracking each load
CREATE TABLE etl_run_log (
    run_id         BIGSERIAL   PRIMARY KEY,
    started_at     TIMESTAMP   NOT NULL,
    finished_at    TIMESTAMP,
    run_status     VARCHAR(20) NOT NULL,
    rows_extracted INTEGER,
    rows_loaded    INTEGER,
    checks_total   INTEGER,
    checks_failed  INTEGER,
    details        TEXT
);